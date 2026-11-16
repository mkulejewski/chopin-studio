from .api.uploads import save_upload as save_upload, MAX_IMPORT as MAX_IMPORT
from .api.models import (PieceUpdate as PieceUpdate, ViewUpdate as ViewUpdate, Settings as Settings, RecordingOptions as RecordingOptions, Simulation as Simulation)
import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from . import lifecycle
from .recorder import MidiInput, Recorder
from .store import Store, data_root

log = logging.getLogger(__name__)


def create_app(root=None, hardware=True, shutdown=None):
    store = Store(Path(root) if root else data_root())
    recorder = Recorder(store)
    from .jobs import Jobs
    from .live import LiveFollowing
    from .practice_api import attach_practice_routes
    jobs = Jobs(store)
    live = LiveFollowing(store, recorder)
    midi = MidiInput(recorder) if hardware else None
    simulation = {'running': False, 'cancel': threading.Event()}
    idle = lifecycle.IdleShutdown()

    async def watch_idle():
        while True:
            await asyncio.sleep(lifecycle.POLL_INTERVAL)
            if app.state.shutting_down:
                continue
            if midi:
                try:
                    ident = recorder.stop_if_disconnected()
                    if ident:
                        if app.state.learning.active and app.state.learning.active['session_id'] == ident:
                            app.state.learning.finish(aborted=True)
                        else:
                            jobs.organise(ident)
                        log.info('Saved recording %s after piano disconnection', ident)
                except Exception:
                    log.exception('Cannot finish recording after piano disconnection')
            if recorder.active and recorder.microphone is not None:
                idle.frontend_open()  # An intentional microphone session keeps recording without a window.
                continue
            if shutdown is None or not idle.expired(midi.connected if midi else None):
                continue
            try:
                prepare_shutdown()
            except HTTPException:
                # Saving or a storage failure must keep the backend alive.
                continue
            log.info('Shutting down after five minutes without a piano or frontend')
            finish_shutdown()
            return

    async def watch_learning():
        while True:
            await asyncio.sleep(.5)
            try:
                await asyncio.to_thread(app.state.learning.tick)
            except Exception as exc:
                app.state.learning.pending = None
                app.state.learning.error = 'Automatic Learning paused: '+str(exc)+'. Finish or pause the attempt before continuing.'
                log.exception('Learning controller paused after an error')

    @asynccontextmanager
    async def lifespan(app):
        from .headphone_audio import needs_review as headphone_review_needed
        for session in store.query("SELECT id FROM sessions WHERE status IN ('saved','imported','recovered','incomplete') AND source<>'learning'"):
            if not store.setting('organised:'+session['id'],False) or headphone_review_needed(store.root/'sessions'/session['id']):
                jobs.organise(session['id'])
        watcher = asyncio.create_task(watch_idle())
        learning_watcher = asyncio.create_task(watch_learning())
        try:
            yield
        finally:
            learning_watcher.cancel()
            with suppress(asyncio.CancelledError):
                await learning_watcher
            app.state.learning.pause()
            if watcher:
                watcher.cancel()
                with suppress(asyncio.CancelledError):
                    await watcher
        simulation['cancel'].set()
        if midi:
            midi.close()
        if recorder.active:
            recorder.mark('shutdown', {})
            jobs.organise(recorder.stop())
        live.close()
        jobs.pool.submit(lambda: None).result()
        jobs.close()
        from .retention import automatic_cleanup
        automatic_cleanup(store, shutdown=True)
        store.db.close()

    app = FastAPI(title='Chopin Studio', lifespan=lifespan)
    app.state.store, app.state.recorder = store, recorder
    app.state.jobs, app.state.live = jobs, live
    app.state.shutting_down = False

    @app.middleware('http')
    async def local_only(request: Request, call_next):
        # Prevent DNS rebinding and cross-origin writes to the local service.
        host = request.headers.get('host', '').split(':')[0]
        origin = request.headers.get('origin')
        allowed_hosts = {'127.0.0.1', 'localhost', 'testserver'}
        if host not in allowed_hosts:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Local host required'}, status_code=403)
        if origin and origin not in {f'http://{h}:{p}' for h in ('localhost', '127.0.0.1') for p in (int(os.environ.get('CHOPIN_PORT', '8765')), 5173)}:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Untrusted origin'}, status_code=403)
        if app.state.shutting_down and request.url.path != '/api/status':
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Chopin Studio is shutting down'}, status_code=503)
        response = await call_next(request)
        if response.headers.get('content-type', '').startswith('text/html'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': str(exc)}, status_code=400)

    def session_folder(ident):
        if not store.query('SELECT id FROM sessions WHERE id=?', (ident,)):
            raise HTTPException(404, 'Session not found')
        return store.root / 'sessions' / ident


    @app.get('/api/status')
    async def status(request: Request):
        if request.headers.get('x-chopin-frontend') == '1':
            idle.frontend_open()
        return {**recorder.status(), 'devices': midi.devices if midi else [], 'connected': midi.connected if midi else None,
                'device_error': midi.error if midi else None, 'simulation': simulation['running'],
                'shutting_down': app.state.shutting_down}

    def prepare_shutdown():
        if shutdown is None:
            raise HTTPException(503, 'Shutdown is unavailable in this server configuration')
        if recorder.saving:
            raise HTTPException(409, 'A recording is still saving. Wait before shutting down.')
        simulation['cancel'].set()
        app.state.learning.pause()
        # Finish saving before acknowledging; a save failure leaves the service up.
        if recorder.active:
            recorder.mark('shutdown', {})
            try:
                jobs.organise(recorder.stop())
            except Exception as exc:
                log.exception('Cannot save recording before shutdown')
                raise HTTPException(409, 'Could not finish saving. The backend is still running; check storage before shutting down.') from exc
        app.state.shutting_down = True

    def finish_shutdown():
        # Acknowledge the durable save first; organisation can require cold imports.
        # The process stays alive until the final audio shortlist is cleaned up.
        jobs.pool.submit(lambda: None).result()
        from .retention import automatic_cleanup
        automatic_cleanup(store, shutdown=True)
        shutdown()

    @app.post('/api/shutdown')
    async def shutdown_service(request: Request, tasks: BackgroundTasks):
        # A custom header cannot be sent by a cross-site form or no-CORS fetch.
        if request.headers.get('x-chopin-shutdown') != '1':
            raise HTTPException(403, 'Use the shutdown button in Chopin Studio')
        prepare_shutdown()
        tasks.add_task(finish_shutdown)
        return {'ok': True}


    from .api import capture, library, settings
    app.include_router(capture.router(app, store, recorder, jobs, simulation, session_folder, save_upload))
    app.include_router(library.router(store, save_upload))
    app.include_router(settings.router(store, recorder, midi, simulation, session_folder))
    attach_practice_routes(app, store, recorder, jobs, live, save_upload, hardware=hardware)
    from .learning_api import attach_learning_routes
    attach_learning_routes(app, store, recorder)

    dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    if dist.exists():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
