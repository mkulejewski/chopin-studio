"""Exercise the portable service boundary and the Linux translation layer."""

import json
import queue
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import mido
import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.midi_files import journal_events, midi_events
from chopin.midi_input import MidiInput, select_input
from chopin.midi_playback import play_messages
from chopin.performance import performance_notes
from chopin.platform.files import LocalFiles
from chopin.platform.interfaces import MidiEvent, MidiPort
from chopin.platform.linux.midi import LinuxMidi
from chopin.recorder import Recorder
from chopin.store import Store
from chopin.studio import Studio, StudioPlatform
from platform_fixtures import SyntheticMidi
from test_practice import PITCHES, reference


def message(kind, **fields):
    return {'type': kind, 'time': 0, **fields}


def test_preference_precedes_default_priority_and_legacy_match():
    ports = [MidiPort('Midi Through:0', automatic=False), MidiPort('USB Keys 20:0'),
             MidiPort('CASIO AP-470 40:0')]
    assert select_input(ports, '') == 'CASIO AP-470 40:0'
    assert select_input(ports, 'usb keys') == 'USB Keys 20:0'
    assert select_input(ports, 'missing') is None
    assert select_input(ports, 'Midi Through') == 'Midi Through:0'
    assert select_input(ports[:2], '') == 'USB Keys 20:0'
    assert select_input(ports[:1], '') is None


def test_synthetic_capture_reconnect_timestamps_evidence_and_roundtrip(tmp_path):
    driver = SyntheticMidi('Generic USB')
    with studio_scope(tmp_path, StudioPlatform(midi_input=driver)) as studio:
        studio.midi.poll()
        assert studio.midi.devices == ['Generic USB']
        assert studio.midi.connected == 'Generic USB'
        recorder = studio.recorder
        ident = recorder.start()
        first = driver.connections[-1][1]

        raw = [
            message('control_change', channel=3, control=88, value=11),
            message('note_on', channel=3, note=65, velocity=70),
            message('control_change', channel=3, control=64, value=73),
            message('control_change', channel=3, control=66, value=127),
            message('control_change', channel=3, control=67, value=127),
            message('note_off', channel=3, note=65, velocity=53),
            message('sysex', data=[0x43, 1, 2, 3]),
            message('clock'),
        ]
        # Advance the injected clock relative to the session while delivering wire order.
        recorder.epoch -= 1_000_000_000
        for index, msg in enumerate(raw):
            first.receive(MidiEvent(recorder.epoch + 100_000_000 + (index // 2) * 1_000_001, msg))
        capabilities = studio.midi.profile('Generic USB')
        assert capabilities['support']['cc88'] == 'supported'
        assert capabilities['support']['continuous_sustain'] == 'supported'
        assert capabilities['support']['binary_sustain'] == 'unknown'
        assert capabilities['support']['note_off_velocity'] == 'unknown'
        assert capabilities['observed_release_values'] == [53]
        assert capabilities['observed_controllers'] == [64, 66, 67, 88]
        assert capabilities['manufacturer'] is None

        driver.error = 'USB enumeration failed'
        studio.midi.poll()
        assert first.closed and studio.midi.connected is None
        assert studio.midi.error == driver.error
        driver.error = None
        studio.midi.poll()
        assert studio.midi.error is None
        assert studio.midi.connected == 'Generic USB'
        first.receive(MidiEvent(recorder.epoch + 800_000_000, message('clock')))  # stale callback
        assert len(driver.connections) == 2

        recorder.stop()
        folder = tmp_path / 'sessions' / ident
        journal = list(journal_events(folder / 'events.jsonl'))
        captured = [event for event in journal if 'message' in event]
        assert [event['message'] for event in captured] == raw
        assert [event['t'] for event in captured] == [
            (100_000_000 + (index // 2) * 1_000_001) / 1e9 for index in range(len(raw))
        ]
        assert [event['kind'] for event in journal if event.get('device')] == [
            'device_disconnected', 'device_connected',
        ]
        note, = performance_notes(captured)
        assert (note['velocity_14'], note['release_velocity']) == (70 * 128 + 11, 53)
        exported = list(midi_events(folder / 'original.mid'))[:len(raw)]
        assert [event['message'] for event in exported] == raw


@contextmanager
def studio_scope(root, platform):
    studio = Studio(root, platform)
    try:
        yield studio
    finally:
        studio.close()


def test_callback_failure_preserves_the_journal_and_retries(tmp_path):
    driver = SyntheticMidi('USB keyboard')
    with studio_scope(tmp_path, StudioPlatform(midi_input=driver)) as studio:
        studio.midi.poll()
        ident = studio.recorder.start()
        link = driver.connections[-1][1]
        link.report_error('Driver overflow')
        studio.midi.poll()
        assert studio.midi.error == 'Driver overflow'
        assert link.closed
        studio.midi.poll()
        assert studio.midi.connected == 'USB keyboard'
        studio.recorder.stop()
        row, = studio.store.query('SELECT status,error FROM sessions WHERE id=?', (ident,))
        assert row['status'] == 'incomplete'
        assert 'Driver overflow' in row['error']
        assert any(event.get('kind') == 'device_error' for event in
                   journal_events(tmp_path / 'sessions' / ident / 'events.jsonl'))


def test_adapters_and_capability_profiles_at_http_boundary(tmp_path, monkeypatch):
    driver = SyntheticMidi('Generic USB')
    monkeypatch.setattr(MidiInput, 'start', MidiInput.poll)
    with TestClient(create_app(tmp_path, platform=StudioPlatform(midi_input=driver, midi_output=driver))) as client:
        params = {'port': 'Generic USB'}
        profile = client.get('/api/devices/capabilities', params=params).json()
        assert profile['support']['midi_output'] == 'unknown'
        confirmed = {
            'manufacturer': 'User entered', 'confirmed': {'midi_output': 'supported', 'soft_pedal': 'unsupported'},
            'controllers': {'11': 'supported'}, 'release_velocity_range': [5, 78],
        }
        response = client.put('/api/devices/capabilities', params=params, json=confirmed)
        assert response.status_code == 200
        assert response.json()['support']['soft_pedal'] == 'unsupported'
        assert client.get('/api/audio/hardware').json() == {
            'ports': ['MIDI playback'], 'error': None, 'capture_available': False,
        }
        assert client.post('/api/record/start', json={'microphone_enabled': True}).status_code == 400
        assert not list((tmp_path / 'sessions').iterdir())
        assert client.put('/api/devices/capabilities', params=params,
                          json={'controllers': {'128': 'supported'}}).status_code == 422
    with TestClient(create_app(tmp_path, platform=StudioPlatform())) as client:
        profile = client.get('/api/devices/capabilities', params=params).json()
        assert profile['manufacturer'] == confirmed['manufacturer']
        assert profile['support']['midi_output'] == 'supported'
        assert profile['controllers'] == confirmed['controllers']
        assert profile['release_velocity_range'] == [5, 78]


def test_shared_output_sends_and_cleans_up_on_cancellation():
    driver = SyntheticMidi()
    output = driver.open_output('MIDI playback')
    cancel = threading.Event()
    note = message('note_on', channel=10, note=55, velocity=79)

    def stream():
        yield 0, note
        cancel.set()
        yield 0, message('note_on', channel=10, note=56, velocity=79)

    with pytest.raises(InterruptedError):
        play_messages(output, stream(), cancel, tail=0)
    assert driver.output_port == 'MIDI playback'
    assert output.messages[0] == note
    assert len(output.messages) == 1 + 16 * 5
    assert output.messages[-1] == message('control_change', channel=15, control=120, value=0)


def test_linux_translates_mido_without_opening_hardware(monkeypatch):
    driver = LinuxMidi()
    monkeypatch.setattr(mido, 'get_input_names', lambda: ['Midi Through:0', 'USB'])
    monkeypatch.setattr(mido, 'get_output_names', lambda: ['USB out'])
    assert driver.inputs() == [MidiPort('Midi Through:0', automatic=False), MidiPort('USB')]
    assert driver.outputs() == ['USB out']

    class Port:
        messages = []
        closed = False

        def close(self):
            self.closed = True

        def send(self, msg):
            self.messages.append(msg)

    port = Port()

    def open_input(name, callback):
        assert name == 'USB'
        callback(mido.Message('note_off', channel=8, note=61, velocity=51))
        return port

    monkeypatch.setattr(mido, 'open_input', open_input)
    monkeypatch.setattr(mido, 'open_output', lambda name: port)
    before = time.monotonic_ns()
    observed, errors = [], []
    connection = driver.open_input('USB', observed.append, errors.append)
    after = time.monotonic_ns()
    assert before <= observed[0].timestamp_ns <= after
    assert observed[0].message == message('note_off', channel=8, note=61, velocity=51)
    assert errors == []
    output = driver.open_output('USB out')
    output.send(observed[0].message)
    assert port.messages == [mido.Message.from_dict(observed[0].message)]
    output.close()
    connection.close()
    assert port.closed


def test_bounded_input_queue_marks_losses_and_drains_on_stop(tmp_path, monkeypatch):
    import chopin.recorder as recorder_module

    driver = SyntheticMidi('Generic')
    small_queue = SimpleNamespace(
        Queue=lambda maxsize: queue.Queue(maxsize=4 if maxsize == 65536 else maxsize),
        Full=queue.Full, Empty=queue.Empty,
    )
    monkeypatch.setattr(recorder_module, 'queue', small_queue)
    with studio_scope(tmp_path, StudioPlatform(midi_input=driver)) as studio:
        studio.midi.poll()
        writer = studio.recorder._write
        release_writer = threading.Event()

        def paused_writer():
            if release_writer.wait(5):
                writer()

        monkeypatch.setattr(studio.recorder, '_write', paused_writer)
        ident = studio.recorder.start()
        link = driver.connections[-1][1]
        try:
            for note in range(60, 66):
                link.receive(MidiEvent(time.monotonic_ns(), message('note_on', channel=0, note=note, velocity=60)))
            assert studio.recorder.status()['queue_depth'] == 4
            assert 'overflow' in studio.recorder.error.lower()
        finally:
            release_writer.set()
        studio.recorder.stop()
        row, = studio.store.query('SELECT status,events FROM sessions WHERE id=?', (ident,))
        assert row == {'status': 'incomplete', 'events': 2}
        events = list(journal_events(tmp_path / 'sessions' / ident / 'events.jsonl'))
        assert [item['message']['note'] for item in events if 'message' in item] == [60, 61]
        assert max(item['lost_events_total'] for item in events if item.get('kind') == 'capture_loss') >= 4


def test_storage_failure_and_restart_keep_authoritative_midi(tmp_path):
    class FailingFiles(LocalFiles):
        available = 0
        journal_syncs = 0

        def sync(self, stream):
            if str(stream.name).endswith('events.jsonl'):
                self.journal_syncs += 1
                if self.journal_syncs > 1:
                    raise OSError('test disk full')
            super().sync(stream)

        def free_bytes(self, folder):
            return self.available

    store = Store(tmp_path, files=FailingFiles())
    recorder = Recorder(store)
    ident = recorder.start()
    recorder.receive_event(MidiEvent(recorder.epoch + 1, message('note_on', channel=0, note=60, velocity=64)))
    recorder.stop()
    session, = store.query('SELECT status,error,events FROM sessions')
    assert session['status'] == 'incomplete'
    assert 'test disk full' in session['error'] and '0 bytes available' in session['error']
    assert session['events'] == 1
    folder = tmp_path / 'sessions' / ident
    journal = (folder / 'events.jsonl').read_bytes()
    midi = (folder / 'original.mid').read_bytes()
    store.db.close()

    store = Store(tmp_path)
    Recorder(store)
    assert (folder / 'events.jsonl').read_bytes() == journal
    assert (folder / 'original.mid').read_bytes() == midi
    assert store.query('PRAGMA user_version')[0]['user_version'] == 6
    assert store.query('SELECT status FROM sessions')[0]['status'] == 'incomplete'
    store.db.close()


def test_synthetic_practice_analysis_survives_blocked_and_unavailable_jobs(tmp_path):
    driver = SyntheticMidi('Generic')
    gate = threading.Event()
    with studio_scope(tmp_path, StudioPlatform(midi_input=driver)) as studio:
        studio.midi.poll()
        reference(studio.store)
        first_job = studio.jobs.submit('test-blocked', lambda *_: gate.wait(4))
        try:
            ident = studio.start_recording()
            epoch = studio.recorder.epoch
            studio.recorder.epoch = epoch - 10_000_000_000
            connection = driver.connections[-1][1]
            for index, pitch in enumerate(PITCHES):
                for offset, kind in ((0, 'note_on'), (200_000_000, 'note_off')):
                    timestamp = studio.recorder.epoch + index * 300_000_000 + offset
                    connection.receive(MidiEvent(timestamp, message(kind, channel=0, note=pitch, velocity=64)))
            assert studio.stop_recording() == ident
            assert studio.store.query('SELECT status FROM sessions')[0]['status'] == 'saved'
            assert studio.store.query('SELECT status FROM jobs WHERE id=?', (first_job,))[0]['status'] in ('running', 'queued')
        finally:
            gate.set()
        studio.jobs.drain()
        segment, = studio.store.query('SELECT * FROM segments WHERE session_id=?', (ident,))
        assert segment['piece_id'] == 'n9-1'
        result, = studio.store.query('SELECT result FROM analyses WHERE session_id=?', (ident,))
        assert json.loads(result['result'])['notes'] == len(PITCHES)
        job = studio.jobs.render(segment, 'unavailable.sf2')
        studio.jobs.drain()
        assert 'unavailable' in studio.store.query('SELECT error FROM jobs WHERE id=?', (job,))[0]['error']
        with pytest.raises(ValueError, match='unavailable'):
            studio.jobs.playback(studio.recorder, segment, 'missing', '')


def test_learning_evaluates_synthetic_input_and_persists_progress(tmp_path, monkeypatch):
    from chopin.learning import Learning
    from test_learning import attacks

    monkeypatch.setattr(Learning, 'source_status', lambda self: (True, 'Synthetic test edition'))
    driver = SyntheticMidi('Generic')
    with studio_scope(tmp_path, StudioPlatform(midi_input=driver)) as studio:
        studio.midi.poll()
        learning = studio.learning.current
        learning.configure({'visible': 1, 'hidden': 1, 'connections': 1,
                            'auto_continue': False, 'auto_finish': False})
        target = learning.start()['active']['target']
        played = attacks(learning.lesson(), target['start'], target['end'], target['variants'], target['hand'])
        link = driver.connections[-1][1]
        for pitch in played:
            link.receive(MidiEvent(time.monotonic_ns(), message('note_on', channel=0, note=pitch, velocity=64)))
            link.receive(MidiEvent(time.monotonic_ns(), message('note_off', channel=0, note=pitch, velocity=40)))
        result = learning.finish()
        assert result['history'][0]['result']['passed']
        assert result['target']['kind'] == 'hidden'
        assert studio.store.query('SELECT source FROM sessions')[0]['source'] == 'learning'
    with studio_scope(tmp_path, StudioPlatform()) as studio:
        assert studio.learning.current.profile()['stage_index'] == 1


def test_portable_services_import_without_linux_or_web(tmp_path):
    code = """
import sys
from importlib.abc import MetaPathFinder
from pathlib import Path

class BlockHostImports(MetaPathFinder):
    def find_spec(self, name, *args):
        if name.startswith(('chopin.platform.linux', 'chopin.api')) or name in {
            'chopin.app', 'chopin.learning_api', 'chopin.desktop', 'rtmidi', 'fastapi', 'uvicorn',
        }:
            raise AssertionError('Unexpected host dependency: ' + name)

sys.meta_path.insert(0, BlockHostImports())
from chopin import passages, progress, studio, teacher
app = studio.Studio(Path(sys.argv[1]), studio.StudioPlatform())
app.start()
assert app.learning.current.lesson()['piece_id'] == 'e25-1'
app.close()
"""
    subprocess.run([sys.executable, '-c', code, str(tmp_path)], check=True, timeout=20)
