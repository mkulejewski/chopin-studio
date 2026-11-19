import json
import logging
import queue
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone

from .domain_types import CaptureStatus
from .midi_files import export_midi, journal_events
from .platform.interfaces import MidiEvent, MicrophoneInput

log = logging.getLogger(__name__)
DISCONNECT_GRACE = 15


class Recorder:
    def __init__(self, store, microphone_input: MicrophoneInput | None = None):
        self.store = store
        self.lock = threading.RLock()
        # Device callbacks never acquire the lifecycle lock (database, I/O, joins).
        self.input_lock = threading.RLock()
        self.microphone_input = microphone_input
        self.active = None
        self.context_piece_id = None
        self.microphone = None
        self.midi_enabled = True
        self.saving = False
        self.hardware_playback = False
        self.device_connected = False
        self.device_disconnected_at = None
        self.simulated_recording = False
        self.event_times = deque(maxlen=4096)
        self.error = None
        self.events = 0
        self.recent = deque(maxlen=24)
        self.notes = {}
        self.pedals = {'64': 0, '66': 0, '67': 0}
        self.last_event = None
        self.page_commands = deque(maxlen=40)
        self.pedal_enabled = store.setting('pedal_enabled', False)
        self.pedal_controller = store.setting('pedal_controller',66)
        self.pedal_down = None
        self.last_release = -10.0
        self.learning_pedal_owner = None
        self.learning_pedal_until = 0
        self.learning_pedal_down = None
        self.learning_pedal_commands = deque(maxlen=40)
        self.live_queue = queue.Queue(maxsize=4096)
        self.live_overflow = False
        self.recover()

    def recover(self):
        from .retention import recover_deletions
        recover_deletions(self.store)
        for session in self.store.query("SELECT * FROM sessions WHERE status IN ('recording','saving','incomplete')"):
            folder = self.store.root / 'sessions' / session['id']
            if session['status'] == 'incomplete' and not (folder / 'microphone.pcm').exists():
                continue
            try:
                from .microphone import metadata, finalise
                audio = metadata(folder)
                recovery_notice = 'Recording was interrupted. MIDI recovery ends at the last durable journal event.'
                if audio:
                    audio['capture_error'] = 'Application interrupted; audio recovered without a clean stop.'
                    try:
                        audio = finalise(folder, audio, files=self.store.files)
                        from .microphone import write_metadata
                        write_metadata(folder, audio, files=self.store.files)
                    except Exception as exc:
                        recovery_notice += f' Microphone recovery failed: {exc}; retained PCM can be retried at startup.'
                        log.exception('Microphone recovery failed; recovering MIDI independently')
                count, duration = 0, (audio.get('duration', 0) + audio.get('offset_seconds', 0)) if audio else 0.0
                for item in journal_events(folder / 'events.jsonl'):
                    duration = max(duration, item.get('t', 0))
                    count += int('message' in item)
                export_midi(folder / 'events.jsonl', folder / 'original.mid', duration, files=self.store.files)
                self.store.execute("UPDATE sessions SET status=?, events=?,duration=?,error=? WHERE id=?",
                                   ('incomplete' if (folder / 'microphone.pcm').exists() else 'recovered', count, duration, recovery_notice, session['id']))
            except Exception as exc:
                self.store.execute("UPDATE sessions SET status='recovery_failed',error=? WHERE id=?", (str(exc), session['id']))
                log.exception('Session recovery failed')

    def start(self, simulated=False, midi_enabled=True, microphone_enabled=False, microphone_device="default"):
        if not midi_enabled and not microphone_enabled:
            raise ValueError("Enable MIDI or microphone recording before starting.")
        with self.lock:
            if self.active or self.saving or self.hardware_playback:
                raise ValueError('A session is already recording')
            ident = uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            name = now.astimezone().strftime('%Y-%m-%d_%H-%M') + '_session_' + ident[:6]
            folder = self.store.root / 'sessions' / ident
            folder.mkdir()
            self.queue = queue.Queue(maxsize=65536)
            self._stop_writer = threading.Event()
            self.epoch = time.monotonic_ns()
            self.microphone = None
            if microphone_enabled:
                try:
                    if self.microphone_input is None:
                        raise ValueError("Microphone capture is unavailable on this host.")
                    self.microphone = self.microphone_input.start(folder, microphone_device, self.epoch)
                except Exception:
                    # Failed starts must not appear as successful recordings.
                    import shutil
                    shutil.rmtree(folder)
                    raise
            self.events = 0
            self.error = None
            self.duration = 0.0
            self.loss_info = None
            self.reported_losses = 0
            try:
                # Open the journal before declaring a recording active.
                self.journal = (folder / 'events.jsonl').open('x', buffering=1)
                self.journal.write(json.dumps({'kind': 'start', 't': 0, 'started': now.isoformat(), 'version': 1, 'midi_enabled': midi_enabled, 'microphone_enabled': microphone_enabled}) + '\n')
                self.store.files.sync(self.journal)
                self.store.files.sync_directory(folder)
                self.store.files.sync_directory(folder.parent)
                self.store.execute('INSERT INTO sessions(id,name,started,status) VALUES(?,?,?,?)', (ident, name, now.isoformat(), 'recording'))
            except Exception:
                if hasattr(self, 'journal') and not self.journal.closed:
                    self.journal.close()
                if self.microphone:
                    capture, self.microphone = self.microphone, None
                    try:
                        capture.stop()
                    except Exception:
                        log.exception('Microphone cleanup after failed start; retained audio needs inspection')
                raise
            self.worker = threading.Thread(target=self._write, name='midi-journal', daemon=True)
            self.worker.start()
            with self.input_lock:
                self.active = ident
                self.midi_enabled = midi_enabled
                self.device_disconnected_at = None
                self.simulated_recording = simulated
                self.mark('piece_context', {'piece_id': self.context_piece_id})
                self.mark('device_status', {'connected': self.device_connected})
            return ident

    def set_device_connected(self, connected):
        with self.input_lock:
            if connected:
                self.device_disconnected_at = None
            elif self.device_connected:
                self.device_disconnected_at = time.monotonic()
            self.device_connected = bool(connected)

    def device_status(self, port, *, connected, error=None):
        with self.input_lock:
            self.set_device_connected(connected)
            details = {'device': port}
            if error:
                details['error'] = error
            self.mark('device_connected' if connected else 'device_disconnected', details)

    def input_failed(self, error):
        with self.input_lock:
            if self.active and self.midi_enabled:
                self.error = f'MIDI input callback failed: {error}. Session is incomplete.'
                self.mark('device_error', {'error': self.error})

    def stop_if_disconnected(self):
        with self.lock:
            with self.input_lock:
                if (not self.active or self.saving or not self.midi_enabled or self.microphone is not None or self.simulated_recording or
                        self.device_connected or self.device_disconnected_at is None or
                        time.monotonic() - self.device_disconnected_at < DISCONNECT_GRACE):
                    return None
                self.mark('auto_stop', {'reason': 'piano_disconnected', 'grace_seconds': DISCONNECT_GRACE})
            try:
                return self.stop()
            except Exception as exc:
                self.error = f'Could not save after piano disconnection: {exc}. Check storage.'
                raise

    def _write_loss_marker(self):
        info = self.loss_info
        if info and info[2] != self.reported_losses:
            self.journal.write(json.dumps({"kind": "capture_loss", "t": info[1], "start": info[0], "lost_events_total": info[2]}) + "\n")
            self.reported_losses = info[2]

    def _write(self):
        last_sync = time.monotonic()
        try:
            while True:
                try:
                    item = self.queue.get_nowait() if self._stop_writer.is_set() else self.queue.get(timeout=.2)
                except queue.Empty:
                    if self._stop_writer.is_set() and self.queue.empty():
                        break
                    self._write_loss_marker()
                    self.store.files.sync(self.journal)
                    last_sync = time.monotonic()
                    continue
                if item is None:
                    break
                self.journal.write(json.dumps(item, separators=(',', ':')) + '\n')
                self.events += int('message' in item)
                self.duration = max(self.duration, item['t'])
                if time.monotonic() - last_sync >= .25:
                    self._write_loss_marker()
                    self.store.files.sync(self.journal)
                    last_sync = time.monotonic()
            self._write_loss_marker()
            self.store.files.sync(self.journal)
        except Exception as exc:
            self.error = f'Journal failure: {exc}. Stop and check storage. Previously saved data is recoverable.'
            if isinstance(exc, OSError):
                try:
                    free = self.store.files.free_bytes(self.store.root)
                    self.error += f' {free:,} bytes available.'
                except OSError:
                    pass  # The original storage error remains the actionable diagnostic.
            log.exception('Recording persistence failed')
        finally:
            self.journal.close()

    def _enqueue(self, event):
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            previous = getattr(self, 'loss_info', None)
            self.loss_info = (previous[0] if previous else event['t'], event['t'], previous[2] + 1 if previous else 1)
            self.error = 'Capture queue overflow: events lost. Session is incomplete; check disk speed.'

    def receive(self, message):
        """Compatibility entry point for the portable Mido codec and local replay."""
        self.receive_event(MidiEvent(time.monotonic_ns(), message.copy(time=0).dict(), str(message)))

    def receive_event(self, event: MidiEvent):
        now = event.timestamp_ns
        message = event.message
        kind = message['type']
        with self.input_lock:
            if self.hardware_playback:
                return
            self.last_event = now
            self.event_times.append(now)
            display = event.display
            if not display:
                display = f"sysex ({len(message['data'])} data bytes)" if kind == 'sysex' else str(message)
            self.recent.append({'at': time.time(), 'message': display})
            if kind == 'note_on' and message['velocity']:
                self.notes[f"{message['channel']}:{message['note']}"] = message['velocity']
            elif kind in ('note_off', 'note_on'):
                self.notes.pop(f"{message['channel']}:{message['note']}", None)
            if kind == 'control_change' and str(message['control']) in self.pedals:
                self.pedals[str(message['control'])] = message['value']
            command = self._pedal(message, now / 1e9)
            try:
                self.live_queue.put_nowait({'t': now / 1e9, 'message': message})
            except queue.Full:
                self.live_overflow = True
            if self.active and self.midi_enabled and now >= self.epoch:
                self._enqueue({'t': (now - self.epoch) / 1e9, 'message': message, 'application_command': command})

    def set_pedal_preferences(self, enabled, controller):
        with self.input_lock:
            self.pedal_enabled = enabled
            self.pedal_controller = controller
            self.pedal_down = None

    def learning_pedal_control(self, owner, enabled):
        with self.input_lock:
            if enabled:
                self.learning_pedal_owner = owner
                self.learning_pedal_until = time.monotonic()+3
                self.learning_pedal_down = None
                self.pedal_down = None
                self.last_release = -10.0
                self.page_commands.clear()  # Discard page gestures queued before entering Learning.
            elif owner == self.learning_pedal_owner:
                self.learning_pedal_owner = None
                self.learning_pedal_until = 0
                self.learning_pedal_down = None
                self.pedal_down = None
                self.last_release = -10.0
            return {'after': time.monotonic()}

    def learning_commands(self, owner, after):
        with self.input_lock:
            if owner != self.learning_pedal_owner:
                return {'enabled': False, 'commands': []}
            self.learning_pedal_until = time.monotonic()+3
            return {'enabled': True, 'commands': [c for c in self.learning_pedal_commands
                    if c['owner'] == owner and c['id'] > after]}

    def _pedal(self, msg, now):
        if not isinstance(msg, dict):
            msg = msg.dict()
        if (msg['type'] == 'control_change' and msg['control'] == 66
                and self.learning_pedal_owner and now < self.learning_pedal_until):
            if msg['value'] >= 64 and self.learning_pedal_down is None:
                self.learning_pedal_down = now
            elif msg['value'] < 64 and self.learning_pedal_down is not None:
                elapsed = now-self.learning_pedal_down
                self.learning_pedal_down = None
                if elapsed >= .06:
                    self.learning_pedal_commands.append({'id': now, 'owner': self.learning_pedal_owner})
            return True
        if msg['type'] != 'control_change' or msg['control'] != self.pedal_controller or not self.pedal_enabled:
            return False
        if msg['value'] >= 64 and self.pedal_down is None:
            self.pedal_down = now
        elif msg['value'] < 64 and self.pedal_down is not None:
            elapsed = now - self.pedal_down
            self.pedal_down = None
            if elapsed < .06:  # contact bounce
                return True
            if elapsed > .8:
                action = 'toggle_controls'
            elif now - self.last_release < .4:
                # First release was delayed, so a double press emits only previous.
                if self.page_commands and self.page_commands[-1].get('pending'):
                    self.page_commands.pop()
                action = 'previous'
            else:
                action = 'next'
            self.page_commands.append({'id': now, 'action': action, 'pending': action == 'next'})
            self.last_release = now
        return True

    def commands(self, after):
        now = time.monotonic()
        with self.input_lock:
            snapshot = list(self.page_commands)
        return [x for x in snapshot if x['id'] > after and (not x['pending'] or now - x['id'] >= .4)]

    def mark(self, kind, details):
        with self.input_lock:
            if self.active:
                self._enqueue({'t': (time.monotonic_ns() - self.epoch) / 1e9, 'kind': kind, **details})

    def stop(self):
        with self.lock:
            if not self.active:
                raise ValueError('No session is recording')
            ident = self.active
            self.store.execute("UPDATE sessions SET status='saving' WHERE id=?", (ident,))
            with self.input_lock:
                duration = (time.monotonic_ns() - self.epoch) / 1e9
                self._enqueue({'t': duration, 'kind': 'stop', 'error': self.error})
                self.active = None
                self.saving = True
        if self.microphone:
            capture = self.microphone
            self.microphone = None
            try:
                audio = capture.stop()
                if audio.get('capture_error'):
                    self.error = '; '.join(filter(None, [self.error, audio['capture_error']]))
            except Exception as exc:
                self.error = '; '.join(filter(None, [self.error, f'Microphone save failed: {exc}. Raw PCM is retained for recovery.']))
        # Callbacks no longer enqueue.
        # The writer drains all queued events and exits when it reaches an empty
        # queue. Its stop signal does not need room in the bounded event queue.
        self._stop_writer.set()
        try:
            self.queue.put_nowait(None)  # Wake an idle writer immediately.
        except queue.Full:
            pass
        self.worker.join(timeout=10)
        if self.worker.is_alive():
            self.error = 'Journal is still saving. Do not shut down; inspect storage.'
            raise RuntimeError(self.error)
        folder = self.store.root / 'sessions' / ident
        try:
            export_midi(folder / 'events.jsonl', folder / 'original.mid', duration, files=self.store.files)
            status = 'incomplete' if self.error else 'saved'
            self.store.execute('UPDATE sessions SET status=?,duration=?,events=?,error=? WHERE id=?',
                               (status, duration, self.events, self.error, ident))
        except Exception as exc:
            self.store.execute("UPDATE sessions SET status='saving',error=? WHERE id=?", (str(exc), ident))
            raise
        self.saving = False
        return ident

    @contextmanager
    def playback(self):
        with self.lock, self.input_lock:
            if self.active or self.saving or self.hardware_playback:
                raise ValueError('Stop recording before hardware playback')
            self.hardware_playback = True
        try:
            yield
        finally:
            with self.input_lock:
                self.hardware_playback = False

    def status(self) -> CaptureStatus:
        capture = self.microphone
        microphone_error = ('Microphone capture stopped unexpectedly; stop the session to save retained audio.'
                            if capture and not capture.running() else None)
        with self.input_lock:
            return {'active': self.active, 'saving': self.saving,
                    'event_rate': sum(t >= time.monotonic_ns() - 1_000_000_000 for t in self.event_times),
                    'duration': (time.monotonic_ns() - self.epoch) / 1e9 if self.active else 0,
                    'events': self.events, 'error': self.error or microphone_error,
                    'midi_enabled': self.midi_enabled, 'microphone_enabled': self.microphone is not None, 'notes': dict(self.notes), 'pedals': dict(self.pedals),
                    'recent': list(self.recent), 'queue_depth': self.queue.qsize() if self.active else 0,
                    'last_event_age': (time.monotonic_ns() - self.last_event) / 1e9 if self.last_event else None}
