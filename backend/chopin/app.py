from .api.uploads import save_upload as save_upload, MAX_IMPORT as MAX_IMPORT
from .api.models import (PieceUpdate as PieceUpdate, ViewUpdate as ViewUpdate, Settings as Settings, RecordingOptions as RecordingOptions, Simulation as Simulation)
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from .practice_api import attach_practice_routes
from .api.score_certification import certification_router
from .studio import ShutdownBlocked, Studio, StudioPlatform

log = logging.getLogger(__name__)


def create_app(root=None, hardware=True, shutdown=None, *, platform: StudioPlatform | None = None):
    idle = None
    if platform is None:
        from .platform.linux import lifecycle
        from .platform.linux.paths import data_root
        from .platform.linux.runtime import adapters

        root = data_root() if root is None else root
        platform = adapters(hardware=hardware)
        idle = lifecycle.IdleShutdown()
    if root is None:
        raise ValueError('Supply an app-private data directory when using custom platform adapters')

    studio = Studio(Path(root), platform)
    store, recorder, jobs, live = studio.store, studio.recorder, studio.jobs, studio.live
    midi, simulation = studio.midi, studio.simulation

    @asynccontextmanager
    async def lifespan(app):
        stop = asyncio.Event()

        async def wait(interval):
            try:
                await asyncio.wait_for(stop.wait(), interval)
                return False
            except TimeoutError:
                return True

        async def watch_devices():
            interval = lifecycle.POLL_INTERVAL if idle else 1
            while await wait(interval) and not studio.shutting_down:
                await asyncio.to_thread(studio.check_disconnect)
                if idle is None or shutdown is None:
                    continue
                if recorder.active and recorder.microphone is not None:
                    idle.frontend_open()
                elif idle.expired(midi.connected if midi else None):
                    try:
                        prepared = await asyncio.to_thread(studio.prepare_shutdown)
                    except ShutdownBlocked:
                        continue
                    if prepared:
                        log.info('Shutting down after five minutes without a piano or frontend')
                        await asyncio.to_thread(finish_shutdown)
                    return

        async def watch_learning():
            while await wait(.5) and not studio.shutting_down:
                await asyncio.to_thread(studio.tick_learning)

        watchers = []
        try:
            studio.start()
            watchers = [asyncio.create_task(watch_devices()), asyncio.create_task(watch_learning())]
            yield
        finally:
            stop.set()
            try:
                await asyncio.gather(*watchers)
            finally:
                await asyncio.to_thread(studio.close)

    app = FastAPI(title='Chopin Studio', lifespan=lifespan)
    app.state.studio = studio
    app.state.store, app.state.recorder = store, recorder
    app.state.jobs, app.state.live = jobs, live

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
        if studio.shutting_down and request.url.path != '/api/status':
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
        if idle and request.headers.get('x-chopin-frontend') == '1':
            idle.frontend_open()
        certification = studio.certification.active
        return {**recorder.status(), 'certification_piece_id': certification[0] if certification else None, 'devices': midi.devices if midi else [], 'connected': midi.connected if midi else None,
                'device_error': midi.error if midi else None, 'simulation': simulation.running,
                'shutting_down': studio.shutting_down}

    def finish_shutdown():
        studio.finish_shutdown()
        shutdown()

    @app.post('/api/shutdown')
    async def shutdown_service(request: Request, tasks: BackgroundTasks):
        # A custom header cannot be sent by a cross-site form or no-CORS fetch.
        if request.headers.get('x-chopin-shutdown') != '1':
            raise HTTPException(403, 'Use the shutdown button in Chopin Studio')
        if shutdown is None:
            raise HTTPException(503, 'Shutdown is unavailable in this server configuration')
        try:
            if await asyncio.to_thread(studio.prepare_shutdown):
                tasks.add_task(finish_shutdown)
        except ShutdownBlocked as exc:
            raise HTTPException(409, str(exc)) from exc
        return {'ok': True}


    from .api import capture, library, settings
    stage_upload = partial(save_upload, files=store.files)
    app.include_router(capture.router(studio, session_folder, stage_upload))
    app.include_router(library.router(store, stage_upload))
    app.include_router(settings.router(store, recorder, midi, simulation, session_folder))
    attach_practice_routes(app, store, recorder, jobs, live, stage_upload)
    from .learning_api import attach_learning_routes
    attach_learning_routes(app, studio.learning)
    app.include_router(certification_router(studio))

    dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    if dist.exists():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
