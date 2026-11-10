import asyncio
import json
import logging
import os
import shutil
import threading
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

import mido
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader

from .midi_files import export_midi, journal_events, midi_events, midicsv_events
from . import lifecycle
from .recorder import MidiInput, Recorder
from .store import Store, data_root

log = logging.getLogger(__name__)
MAX_IMPORT = 50 * 1024 * 1024


class PieceUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=80)
    opus: str = Field(max_length=80)
    musical_key: str = Field(max_length=80)
    volume_id: str
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)
    printed_page: str = Field(default='', max_length=40)
    favourite: bool = False
    practice_status: str = Field(default='To explore', max_length=80)
    notes: str = Field(default='', max_length=10000)
    mastery: float | None = Field(default=None, ge=1, le=3)
    liking: int = Field(default=0,ge=0,le=3)
    forgotten: bool = False
    intent: str = Field(default='To explore',max_length=80)
    preferred_edition: str = Field(default='Paderewski',max_length=200)


class ViewUpdate(BaseModel):
    page: int = Field(ge=1)
    zoom: float = Field(ge=.5, le=4)
    two_pages: bool = False
    crop: float = Field(default=0, ge=0, le=.15)


class Settings(BaseModel):
    preferred_device: str = Field(default='', max_length=200)
    pedal_enabled: bool = False
    pedal_controller: Literal[64,66,67] = 66
    separation_cooldown: float = Field(default=20,ge=5,le=300)
    swipe: bool = True
    pinch: bool = True
    double_tap: bool = True
    tap_overlay: bool = False
    auto_hide: bool = False
    live_enabled: bool = False
    live_auto_turn: bool = False
    live_allow_provisional: bool = False
    live_piece_id: str | None = None
    soundfont: str = ''


class RecordingOptions(BaseModel):
    midi_enabled: bool = True
    microphone_enabled: bool = False
    microphone_device: str = Field(default='default', min_length=1, max_length=300)


class Simulation(BaseModel):
    session_id: str | None = None
    speed: float = Field(default=1, ge=.25, le=8)


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

    @asynccontextmanager
    async def lifespan(app):
        for session in store.query("SELECT id FROM sessions WHERE status IN ('saved','imported','recovered','incomplete')"):
            if not store.setting('organised:'+session['id'],False):jobs.organise(session['id'])
        watcher = asyncio.create_task(watch_idle())
        try:
            yield
        finally:
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
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': str(exc)}, status_code=400)

    def session_folder(ident):
        if not store.query('SELECT id FROM sessions WHERE id=?', (ident,)):
            raise HTTPException(404, 'Session not found')
        return store.root / 'sessions' / ident

    async def save_upload(file, folder, suffix):
        target = folder / (uuid.uuid4().hex + suffix)
        size = 0
        try:
            with target.open('xb') as out:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_IMPORT:
                        raise ValueError('Import exceeds the 50 MiB safety limit')
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if not size:
                raise ValueError('File is empty')
            return target
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

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

    @app.post('/api/record/start')
    def start(options: RecordingOptions = RecordingOptions()):
        return {'id': recorder.start(simulated=simulation['running'], **options.model_dump())}

    @app.post('/api/record/stop')
    def stop():
        ident = recorder.stop()
        jobs.organise(ident)
        return {'id': ident}

    @app.get('/api/sessions')
    def sessions():
        return store.query('SELECT * FROM sessions ORDER BY started DESC')

    @app.get('/api/sessions/{ident}/microphone')
    def microphone_download(ident: str):
        folder = session_folder(ident)
        from .microphone import audio_layout
        path,_ = audio_layout(folder)
        if recorder.active == ident or recorder.saving or path is None:
            raise HTTPException(409, 'No finished microphone recording is available')
        return FileResponse(path, media_type='audio/flac', filename=ident + '__microphone.flac')

    @app.get('/api/sessions/{ident}/recording')
    def recording_info(ident: str):
        from .microphone import metadata
        from .retention import locked
        return {'microphone': metadata(session_folder(ident)), 'timeline_locked': locked(store,ident)}

    @app.get('/api/sessions/{ident}/midi')
    def download(ident: str):
        folder = session_folder(ident)
        if not (folder / 'original.mid').exists():
            raise HTTPException(409, 'Session has not finished saving')
        name = store.query('SELECT name FROM sessions WHERE id=?', (ident,))[0]['name']
        return FileResponse(folder / 'original.mid', media_type='audio/midi', filename=name + '.mid')

    @app.get('/api/sessions/{ident}/summary')
    def summary(ident: str):
        folder = session_folder(ident)
        notes, velocities, pedals, markers = 0, [], [], []
        # Bound graph sampling; use online aggregation rather than retaining an entire session.
        bins = {}
        session = store.query('SELECT * FROM sessions WHERE id=?', (ident,))[0]
        width = max(1, session['duration'] / 240)
        active_seconds = set()
        for event in journal_events(folder / 'events.jsonl'):
            msg = event.get('message', {})
            if msg.get('type') == 'note_on' and msg.get('velocity', 0):
                notes += 1
                index = int(event['t'] / width)
                bucket = bins.setdefault(index, [0, 0, 127, 0])
                bucket[0] += msg['velocity']
                bucket[1] += 1
                bucket[2] = min(bucket[2], msg['velocity'])
                bucket[3] = max(bucket[3], msg['velocity'])
                active_seconds.add(int(event['t']))
            if msg.get('type') == 'control_change' and msg.get('control') == 64:
                if len(pedals) < 2000:
                    pedals.append({'t': event['t'], 'value': msg['value']})
            if event.get('kind') and event['kind'] not in ('start', 'stop'):
                if len(markers) < 1000:
                    markers.append(event)
        graph = [{'t': index * width, 'mean': b[0] / b[1], 'min': b[2], 'max': b[3], 'notes': b[1]} for index, b in sorted(bins.items())]
        return {'version': 1, 'notes': notes, 'note_active_seconds': len(active_seconds), 'velocity': graph,
                'pedals': pedals, 'markers': markers, 'pedals_truncated': len(pedals) == 2000,
                'notice': 'Descriptive MIDI measurements only. No symbolic reference is aligned; accuracy, measures and musical quality are not evaluated.'}

    @app.post('/api/import/midi')
    async def import_midi(file: UploadFile):
        suffix = Path(file.filename or '').suffix.lower()
        if suffix not in ('.mid', '.midi', '.csv'):
            raise ValueError('Choose a .mid, .midi or midicsv .csv file')
        original = await save_upload(file, store.root / 'imports', suffix)
        ident = uuid.uuid4().hex
        folder = store.root / 'sessions' / ident
        folder.mkdir()
        count, duration = 0, 0.0
        try:
            parser = midicsv_events if suffix == '.csv' else midi_events
            with (folder / 'events.jsonl').open('x') as journal:
                for event in parser(original):
                    journal.write(json.dumps(event) + '\n')
                    count += 1
                    duration = max(duration, event['t'])
                journal.flush()
                os.fsync(journal.fileno())
            if not count:
                raise ValueError('No supported MIDI events found')
            if suffix == '.csv':
                export_midi(folder / 'events.jsonl', folder / 'original.mid', duration)
                shutil.move(original, folder / 'source.csv')
            else:
                # Byte-for-byte original, including all metadata and tempo maps.
                shutil.move(original, folder / 'original.mid')
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            name = 'Imported_' + Path(file.filename or 'recording').stem[:100] + '_' + ident[:6]
            store.execute('INSERT INTO sessions(id,name,started,status,duration,events,source) VALUES(?,?,?,?,?,?,?)',
                          (ident, name, now, 'imported', duration, count, 'midicsv' if suffix == '.csv' else 'midi'))
        except Exception as exc:
            shutil.rmtree(folder)
            original.unlink(missing_ok=True)
            if isinstance(exc, ValueError):
                raise
            raise ValueError(f'Cannot read MIDI: {exc}') from exc
        jobs.organise(ident)
        return {'id': ident}

    @app.get('/api/library')
    def library():
        return {'pieces': store.query("SELECT p.*, (SELECT COUNT(*) FROM symbolic_scores s WHERE s.piece_id=p.id) AS reference_count FROM pieces p ORDER BY genre, opus"), 'volumes': store.query('SELECT * FROM volumes')}

    @app.put('/api/pieces/{ident}')
    def update_piece(ident: str, piece: PieceUpdate):
        volume = store.query('SELECT * FROM volumes WHERE id=?', (piece.volume_id,))
        if not volume or not store.query('SELECT id FROM pieces WHERE id=?', (ident,)):
            raise HTTPException(404, 'Piece or volume not found')
        if bool(piece.start_page) != bool(piece.end_page):
            raise ValueError('Set both page bounds, or leave both empty')
        if piece.start_page and (piece.end_page < piece.start_page or (volume[0]['pages'] and piece.end_page > volume[0]['pages'])):
            raise ValueError('Page range must be ordered and within the PDF')
        fields = piece.model_dump()
        from .catalogue import catalogue_path
        fields['catalogue_path'] = catalogue_path(piece.genre,piece.opus)
        store.execute('UPDATE pieces SET ' + ','.join(k + '=?' for k in fields) + ' WHERE id=?', (*fields.values(), ident))
        return {'ok': True}

    @app.put('/api/pieces/{ident}/view')
    def update_view(ident: str, view: ViewUpdate):
        store.execute('UPDATE pieces SET view=? WHERE id=?', (view.model_dump_json(), ident))
        return {'ok': True}

    @app.post('/api/volumes/{ident}/pdf')
    async def import_pdf(ident: str, file: UploadFile):
        if not store.query('SELECT id FROM volumes WHERE id=?', (ident,)):
            raise HTTPException(404, 'Volume not found')
        target = await save_upload(file, store.root / 'scores', '.pdf')
        try:
            if target.open('rb').read(5) != b'%PDF-':
                raise ValueError('Not a PDF document')
            reader = PdfReader(target)
            if reader.is_encrypted:
                raise ValueError('Encrypted PDFs are unsupported; import a permitted unlocked copy')
            pages = len(reader.pages)
            if not pages:
                raise ValueError('PDF has no pages')
            store.execute('UPDATE volumes SET filename=?,pages=? WHERE id=?', (target.name, pages, ident))
        except Exception as exc:
            target.unlink(missing_ok=True)
            raise ValueError(f'Cannot import PDF: {exc}') from exc
        return {'pages': pages}

    @app.get('/api/volumes/{ident}/pdf')
    def pdf(ident: str):
        row = store.query('SELECT filename FROM volumes WHERE id=?', (ident,))
        if not row or not row[0]['filename']:
            raise HTTPException(404, 'Import this volume first')
        return FileResponse(store.root / 'scores' / row[0]['filename'], media_type='application/pdf')

    @app.get('/api/settings')
    def get_settings():
        return {key: store.setting(key, value) for key, value in Settings().model_dump().items()}

    @app.put('/api/settings')
    def save_settings(settings: Settings):
        previous_device = store.setting('preferred_device', '')
        for key, value in settings.model_dump().items():
            store.set_setting(key, value)
        recorder.pedal_enabled = settings.pedal_enabled
        recorder.pedal_controller = settings.pedal_controller
        recorder.pedal_down = None
        if midi and previous_device != settings.preferred_device:
            midi.reconnect.set()
        return {'ok': True}

    @app.post('/api/devices/reconnect')
    def reconnect():
        if midi:
            midi.reconnect.set()
        return {'ok': True}

    @app.get('/api/page-commands')
    def page_commands(after: float = 0):
        return recorder.commands(after)

    @app.post('/api/simulation/start')
    def simulate(config: Simulation):
        if simulation['running']:
            raise ValueError('Simulation is already running')
        if midi and midi.connected:
            raise ValueError('Disconnect the piano before simulated input to avoid mixing performances')
        path = session_folder(config.session_id) / 'events.jsonl' if config.session_id else None
        simulation['running'] = True
        simulation['cancel'].clear()
        with recorder.lock:
            if recorder.active:
                recorder.simulated_recording = True
        recorder.mark('simulation_started', {'source_session': config.session_id})

        def run():
            try:
                if path:
                    events = journal_events(path)
                else:
                    # Synthetic scale only; never pretend this is a Chopin reference.
                    events = ({'t': i * .35 + off, 'message': mido.Message(kind, note=note, velocity=velocity).dict()}
                              for i, note in enumerate([60, 62, 64, 65, 67, 69, 71, 72] * 3)
                              for off, kind, velocity in [(0, 'note_on', 64 + i % 20), (.25, 'note_off', 0)])
                epoch = time.monotonic()
                for event in events:
                    if 'message' not in event:
                        continue
                    delay = max(0, event['t'] / config.speed - (time.monotonic() - epoch))
                    if simulation['cancel'].wait(delay):
                        break
                    recorder.receive(mido.Message.from_dict(event['message']))
                for channel in range(16):
                    recorder.receive(mido.Message('control_change', channel=channel, control=123, value=0))
            except Exception:
                log.exception('Simulation failed')
            finally:
                simulation['running'] = False
                recorder.mark('simulation_ended', {})
        threading.Thread(target=run, daemon=True, name='midi-simulation').start()
        return {'ok': True}

    @app.post('/api/simulation/stop')
    def stop_simulation():
        simulation['cancel'].set()
        return {'ok': True}

    attach_practice_routes(app, store, recorder, jobs, live, save_upload)

    dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    if dist.exists():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
