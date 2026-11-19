"""Explicit local replay and a synthetic scale, using the shared input boundary."""

import logging
import threading
import time

from .midi_files import journal_events
from .platform.interfaces import MidiEvent

log = logging.getLogger(__name__)


def scale_events():
    for index, note in enumerate([60, 62, 64, 65, 67, 69, 71, 72] * 3):
        for offset, kind, velocity in ((0, 'note_on', 64 + index % 20), (.25, 'note_off', 0)):
            yield {'t': index * .35 + offset, 'message': {
                'type': kind, 'channel': 0, 'note': note, 'velocity': velocity, 'time': 0,
            }}


class MidiSimulation:
    def __init__(self, recorder, midi):
        self.recorder, self.midi = recorder, midi
        self.running = False
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._thread = None

    def start(self, *, path, source_session, speed):
        with self._lock:
            if self.running:
                raise ValueError('Simulation is already running')
            if self.midi and self.midi.connected:
                raise ValueError('Disconnect the piano before simulated input to avoid mixing performances')
            self._cancel.clear()
            self.running = True
            with self.recorder.input_lock:
                if self.recorder.active:
                    self.recorder.simulated_recording = True
            self.recorder.mark('simulation_started', {'source_session': source_session})
            self._thread = threading.Thread(target=self._run, args=(path, speed),
                                            daemon=True, name='midi-simulation')
            self._thread.start()

    def _run(self, path, speed):
        try:
            events = journal_events(path) if path else scale_events()
            epoch = time.monotonic()
            for event in events:
                if 'message' not in event:
                    continue
                if self._cancel.wait(max(0, event['t'] / speed - (time.monotonic() - epoch))):
                    break
                self.recorder.receive_event(MidiEvent(time.monotonic_ns(), event['message']))
            for channel in range(16):
                message = {'type': 'control_change', 'channel': channel, 'control': 123, 'value': 0, 'time': 0}
                self.recorder.receive_event(MidiEvent(time.monotonic_ns(), message))
        except Exception:
            log.exception('Simulation failed')
        finally:
            with self._lock:
                self.recorder.mark('simulation_ended', {})
                self.running = False

    def stop(self):
        self._cancel.set()

    def close(self):
        self.stop()
        if self._thread:
            self._thread.join()
