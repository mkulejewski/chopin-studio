"""Disconnection grace uses a virtual clock and a simulated MIDI device."""
import asyncio
import threading
import time
from types import SimpleNamespace

import mido
import pytest
from fastapi.testclient import TestClient

import chopin.app as app_module
import chopin.recorder as recorder_module
from chopin import lifecycle
from chopin.app import create_app
from chopin.midi_files import journal_events


@pytest.fixture
def piano_app(tmp_path, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(recorder_module, 'time', SimpleNamespace(
        monotonic=lambda: now[0], monotonic_ns=time.monotonic_ns, time=time.time,
    ))
    monkeypatch.setattr(lifecycle, 'POLL_INTERVAL', .01)
    midi = SimpleNamespace(connected='CASIO USB-MIDI', devices=['CASIO USB-MIDI'],
                           error=None, close=lambda: None)
    def create_midi(recorder):
        recorder.set_device_connected(True)
        midi.recorder = recorder
        return midi
    monkeypatch.setattr(app_module, 'MidiInput', create_midi)
    app = create_app(tmp_path, hardware=True)  # Also works without a shutdown callback.
    with TestClient(app) as client:
        def connect(connected):
            midi.connected = 'CASIO USB-MIDI' if connected else None
            midi.recorder.set_device_connected(connected)
            midi.recorder.mark('device_connected' if connected else 'device_disconnected', {})
        yield client, app.state.recorder, connect, now


def tick(client):
    client.portal.call(asyncio.sleep, .04)


def test_disconnect_stops_and_saves_at_fifteen_seconds(piano_app, tmp_path):
    client, recorder, connect, now = piano_app
    ident = client.post('/api/record/start').json()['id']
    recorder.receive(mido.Message('note_on', note=60, velocity=80))
    now[0] = 10
    connect(False)
    now[0] = 24.99
    connect(False)  # Repeated discovery failures must not restart the grace.
    tick(client)
    assert recorder.active == ident
    now[0] = 25
    tick(client)
    assert recorder.active is None
    assert not recorder.saving
    assert client.get('/api/status').json()['shutting_down'] is False
    assert client.get('/api/sessions').json()[0]['status'] == 'saved'
    assert client.get(f'/api/sessions/{ident}/midi').content.startswith(b'MThd')
    markers = list(journal_events(tmp_path / 'sessions' / ident / 'events.jsonl'))
    assert any(x.get('reason') == 'piano_disconnected' for x in markers)
    assert client.get('/api/jobs').json()  # Normal post-save processing was queued.


def test_reconnect_cancels_grace_and_next_disconnect_gets_full_grace(piano_app):
    client, recorder, connect, now = piano_app
    ident = client.post('/api/record/start').json()['id']
    connect(False)
    now[0] = 14.9
    connect(True)
    now[0] = 100
    tick(client)
    assert recorder.active == ident
    connect(False)
    now[0] = 114.9
    tick(client)
    assert recorder.active == ident
    now[0] = 115
    tick(client)
    assert recorder.active is None
    connect(True)
    tick(client)
    assert recorder.active is None  # Reconnecting does not create a new session.


def test_manual_stop_and_new_session_do_not_inherit_old_deadline(piano_app):
    client, recorder, connect, now = piano_app
    client.post('/api/record/start')
    connect(False)
    assert client.post('/api/record/stop').status_code == 200
    ident = client.post('/api/record/start').json()['id']
    now[0] = 30
    tick(client)
    assert recorder.active == ident  # No disconnection occurred in this session.


@pytest.mark.parametrize('simulation_first', [False, True])
def test_simulated_recordings_are_exempt(piano_app, simulation_first):
    client, recorder, connect, now = piano_app
    if simulation_first:
        connect(False)
        assert client.post('/api/simulation/start', json={'speed': .25}).status_code == 200
        ident = client.post('/api/record/start').json()['id']
        # Even a subsequent real connection/disconnection cannot change its source.
        connect(True)
        connect(False)
    else:
        ident = client.post('/api/record/start').json()['id']
        connect(False)
        assert client.post('/api/simulation/start', json={'speed': .25}).status_code == 200
    now[0] = 30
    tick(client)
    assert recorder.active == ident
    client.post('/api/simulation/stop')
    now[0] = 60
    tick(client)
    assert recorder.active == ident


def test_save_failure_is_visible_and_service_keeps_running(piano_app, monkeypatch):
    client, recorder, connect, now = piano_app
    client.post('/api/record/start')
    connect(False)
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(recorder_module, 'export_midi', fail)
    now[0] = 15
    tick(client)
    status = client.get('/api/status').json()
    assert status['saving']
    assert 'disk full' in status['error']
    assert not status['shutting_down']
    assert client.get('/api/sessions').json()[0]['status'] == 'saving'


def test_midi_discovery_reports_disconnect_and_reconnect(monkeypatch):
    devices = iter([['CASIO USB-MIDI'], [], ['CASIO USB-MIDI']])
    monkeypatch.setattr(mido, 'get_input_names', lambda: next(devices))
    monkeypatch.setattr(mido, 'open_input', lambda *args, **kwargs: SimpleNamespace(close=lambda: None))
    transitions = []
    recorder = SimpleNamespace(
        store=SimpleNamespace(setting=lambda key, default: default),
        set_device_connected=transitions.append, mark=lambda *args: None, receive=lambda msg: None,
    )
    midi = recorder_module.MidiInput.__new__(recorder_module.MidiInput)
    midi.recorder, midi.port, midi.connected = recorder, None, None
    midi.reconnect = threading.Event()
    steps = [0]
    def advance(seconds):
        steps[0] += 1
    midi.closed = SimpleNamespace(is_set=lambda: steps[0] == 3, wait=advance)
    midi.run()
    assert transitions == [False, True, False, False, True]
    assert midi.error is None
    midi.port.close()
