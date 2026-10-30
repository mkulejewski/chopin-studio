import json
import logging
import os
import queue
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

import mido

from .midi_files import export_midi, journal_events

log = logging.getLogger(__name__)


class Recorder:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.active = None
        self.saving = False
        self.event_times = deque(maxlen=4096)
        self.error = None
        self.events = 0
        self.recent = deque(maxlen=24)
        self.notes = {}
        self.pedals = {'64': 0, '66': 0, '67': 0}
        self.last_event = None
        self.page_commands = deque(maxlen=40)
        self.pedal_down = None
        self.last_release = -10.0
        self.live_queue = queue.Queue(maxsize=4096)
        self.live_overflow = False
        self.recover()

    def recover(self):
        for session in self.store.query("SELECT * FROM sessions WHERE status IN ('recording','saving')"):
            folder = self.store.root / 'sessions' / session['id']
            try:
                count, duration = 0, 0.0
                for item in journal_events(folder / 'events.jsonl'):
                    duration = max(duration, item.get('t', 0))
                    count += int('message' in item)
                export_midi(folder / 'events.jsonl', folder / 'original.mid', duration)
                self.store.execute("UPDATE sessions SET status='recovered', events=?,duration=?,error=? WHERE id=?",
                                   (count, duration, 'Recording was interrupted. Recovery ends at the last durable journal event.', session['id']))
            except Exception as exc:
                self.store.execute("UPDATE sessions SET status='recovery_failed',error=? WHERE id=?", (str(exc), session['id']))
                log.exception('Session recovery failed')

    def start(self):
        with self.lock:
            if self.active or self.saving:
                raise ValueError('A session is already recording')
            ident = uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            name = now.astimezone().strftime('%Y-%m-%d_%H-%M') + '_session_' + ident[:6]
            folder = self.store.root / 'sessions' / ident
            folder.mkdir()
            self.queue = queue.Queue(maxsize=65536)
            self.epoch = time.monotonic_ns()
            self.events = 0
            self.error = None
            self.duration = 0.0
            self.loss_info = None
            self.reported_losses = 0
            # Open the journal before declaring a recording active.
            self.journal = (folder / 'events.jsonl').open('x', buffering=1)
            self.journal.write(json.dumps({'kind': 'start', 't': 0, 'started': now.isoformat(), 'version': 1}) + '\n')
            self.journal.flush()
            os.fsync(self.journal.fileno())
            self.store.execute('INSERT INTO sessions(id,name,started,status) VALUES(?,?,?,?)', (ident, name, now.isoformat(), 'recording'))
            self.active = ident
            self.worker = threading.Thread(target=self._write, name='midi-journal', daemon=True)
            self.worker.start()
            self.mark('device_status', {'connected': getattr(self, 'device_connected', False)})
            return ident

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
                    item = self.queue.get(timeout=.2)
                except queue.Empty:
                    self._write_loss_marker()
                    self.journal.flush()
                    os.fsync(self.journal.fileno())
                    last_sync = time.monotonic()
                    continue
                if item is None:
                    break
                self.journal.write(json.dumps(item, separators=(',', ':')) + '\n')
                self.events += int('message' in item)
                self.duration = max(self.duration, item['t'])
                if time.monotonic() - last_sync >= .25:
                    self._write_loss_marker()
                    self.journal.flush()
                    os.fsync(self.journal.fileno())
                    last_sync = time.monotonic()
            self._write_loss_marker()
            self.journal.flush()
            os.fsync(self.journal.fileno())
        except Exception as exc:
            self.error = f'Journal failure: {exc}. Stop and check storage. Previously saved data is recoverable.'
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
        now = time.monotonic_ns()
        with self.lock:
            self.last_event = now
            self.event_times.append(now)
            self.recent.append({'at': time.time(), 'message': str(message)})
            if message.type == 'note_on' and message.velocity:
                self.notes[f'{message.channel}:{message.note}'] = message.velocity
            elif message.type in ('note_off', 'note_on'):
                self.notes.pop(f'{message.channel}:{message.note}', None)
            if message.type == 'control_change' and str(message.control) in self.pedals:
                self.pedals[str(message.control)] = message.value
            command = self._pedal(message, now / 1e9)
            try:
                self.live_queue.put_nowait({'t': now / 1e9, 'message': message.copy(time=0).dict()})
            except queue.Full:
                self.live_overflow = True
            if self.active:
                self._enqueue({'t': (now - self.epoch) / 1e9, 'message': message.copy(time=0).dict(), 'application_command': command})

    def _pedal(self, msg, now):
        if msg.type != 'control_change' or msg.control != 66 or not self.store.setting('pedal_enabled', False):
            return False
        if msg.value >= 64 and self.pedal_down is None:
            self.pedal_down = now
        elif msg.value < 64 and self.pedal_down is not None:
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
        with self.lock:
            snapshot = list(self.page_commands)
        return [x for x in snapshot if x['id'] > after and (not x['pending'] or now - x['id'] >= .4)]

    def mark(self, kind, details):
        with self.lock:
            if self.active:
                self._enqueue({'t': (time.monotonic_ns() - self.epoch) / 1e9, 'kind': kind, **details})

    def stop(self):
        with self.lock:
            if not self.active:
                raise ValueError('No session is recording')
            ident = self.active
            duration = (time.monotonic_ns() - self.epoch) / 1e9
            self._enqueue({'t': duration, 'kind': 'stop', 'error': self.error})
            self.active = None
            self.saving = True
            self.store.execute("UPDATE sessions SET status='saving' WHERE id=?", (ident,))
        # Callbacks no longer enqueue. Avoid a blocking sentinel on a failed writer.
        while self.worker.is_alive():
            try:
                self.queue.put(None, timeout=.2)
                break
            except queue.Full:
                continue
        self.worker.join(timeout=10)
        if self.worker.is_alive():
            raise RuntimeError('Journal is still saving. Do not shut down; inspect storage.')
        folder = self.store.root / 'sessions' / ident
        try:
            export_midi(folder / 'events.jsonl', folder / 'original.mid', duration)
            status = 'incomplete' if self.error else 'saved'
            self.store.execute('UPDATE sessions SET status=?,duration=?,events=?,error=? WHERE id=?',
                               (status, duration, self.events, self.error, ident))
        except Exception as exc:
            self.store.execute("UPDATE sessions SET status='saving',error=? WHERE id=?", (str(exc), ident))
            raise
        self.saving = False
        return ident

    def status(self):
        with self.lock:
            return {'active': self.active, 'saving': self.saving,
                    'event_rate': sum(t >= time.monotonic_ns() - 1_000_000_000 for t in self.event_times),
                    'duration': (time.monotonic_ns() - self.epoch) / 1e9 if self.active else 0,
                    'events': self.events, 'error': self.error, 'notes': dict(self.notes), 'pedals': dict(self.pedals),
                    'recent': list(self.recent), 'queue_depth': self.queue.qsize() if self.active else 0,
                    'last_event_age': (time.monotonic_ns() - self.last_event) / 1e9 if self.last_event else None}



class MidiInput:
    def __init__(self, recorder):
        self.recorder = recorder
        self.port = None
        self.connected = None
        self.devices = []
        self.error = None
        self.closed = threading.Event()
        self.reconnect = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name='midi-discovery')
        self.thread.start()

    def run(self):
        while not self.closed.is_set():
            try:
                self.devices = mido.get_input_names()
                preferred = self.recorder.store.setting('preferred_device', '')
                candidates = [x for x in self.devices if preferred and preferred.lower() in x.lower()]
                if not preferred:
                    candidates = [x for x in self.devices if any(s in x.lower() for s in ('casio', 'ap-470', 'celviano'))]
                desired = candidates[0] if candidates else None
                if self.reconnect.is_set() or (self.connected and self.connected not in self.devices) or (self.connected != desired):
                    if self.port:
                        self.port.close()
                        self.recorder.mark('device_disconnected', {'device': self.connected})
                    self.port, self.connected = None, None
                    self.recorder.device_connected = False
                    self.reconnect.clear()
                if not self.port and desired:
                    self.port = mido.open_input(desired, callback=self.recorder.receive)
                    self.connected = desired
                    self.recorder.device_connected = True
                    self.recorder.mark('device_connected', {'device': desired})
                self.error = None
            except Exception as exc:
                self.error = str(exc)
                if self.connected:
                    self.recorder.mark('device_disconnected', {'device': self.connected, 'error': str(exc)})
                    try:
                        self.port.close()
                    except Exception:
                        pass
                    self.port, self.connected = None, None
                self.recorder.device_connected = False
            self.closed.wait(2)

    def close(self):
        self.closed.set()
        self.thread.join(3)
        if self.port:
            self.port.close()
