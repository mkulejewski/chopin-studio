"""Exercise the five-minute policy with a virtual clock, without real MIDI."""
import asyncio
import threading

import mido
from fastapi.testclient import TestClient

from chopin.platform.linux import lifecycle
from chopin.midi_input import MidiInput
from chopin.studio import StudioPlatform
from platform_fixtures import SyntheticMidi
from chopin.app import create_app


def test_idle_timer_requires_both_absent_for_five_minutes():
    now = [0.0]
    idle = lifecycle.IdleShutdown(clock=lambda: now[0])
    now[0] = 299
    assert not idle.expired(False)
    now[0] = 300
    assert idle.expired(False)
    idle.frontend_open()
    now[0] = 599
    assert not idle.expired(False)
    now[0] = 600
    assert idle.expired(False)
    assert not idle.expired('CASIO USB-MIDI')
    now[0] = 1000
    assert not idle.expired('CASIO USB-MIDI')
    now[0] = 1200
    assert not idle.expired(False)  # Disconnect starts a fresh grace period.
    now[0] = 1499
    assert not idle.expired(False)
    now[0] = 1500
    assert idle.expired(False)


def virtual_clock(monkeypatch):
    now = [0.0]
    original = lifecycle.IdleShutdown
    monkeypatch.setattr(lifecycle, 'IdleShutdown', lambda: original(clock=lambda: now[0]))
    monkeypatch.setattr(lifecycle, 'POLL_INTERVAL', .01)
    return now


def tick(client):
    # Let the real lifespan task evaluate the virtual clock on its event loop.
    client.portal.call(asyncio.sleep, .03)


def test_frontend_heartbeat_then_idle_shutdown_saves_recording(tmp_path, monkeypatch):
    now = virtual_clock(monkeypatch)
    exited = threading.Event()
    app = create_app(tmp_path, hardware=False, shutdown=exited.set)
    with TestClient(app) as client:
        ident = client.post('/api/record/start').json()['id']
        app.state.recorder.receive(mido.Message('note_on', note=60, velocity=80))
        now[0] = 299
        # Foreign origins cannot keep the backend alive.
        assert client.get('/api/status', headers={
            'X-Chopin-Frontend': '1', 'Origin': 'https://example.com',
        }).status_code == 403
        assert client.get('/api/status', headers={'X-Chopin-Frontend': '1'}).status_code == 200
        now[0] = 300
        tick(client)
        assert not exited.is_set()
        now[0] = 598
        # Launcher / health checks are not frontend presence.
        assert client.get('/api/status').status_code == 200
        tick(client)
        assert not exited.is_set()
        now[0] = 599
        assert exited.wait(2)
        assert client.get('/api/status').json()['shutting_down']
        assert (tmp_path / 'sessions' / ident / 'original.mid').exists()
        assert app.state.store.query('SELECT status FROM sessions')[0]['status'] == 'saved'


def test_idle_shutdown_without_frontend_ever_opened(tmp_path, monkeypatch):
    now = virtual_clock(monkeypatch)
    exited = threading.Event()
    with TestClient(create_app(tmp_path, hardware=False, shutdown=exited.set)) as client:
        now[0] = 299
        tick(client)
        assert not exited.is_set()
        now[0] = 300
        assert exited.wait(2)


def test_connected_piano_prevents_shutdown_and_disconnect_resets_timer(tmp_path, monkeypatch):
    now = virtual_clock(monkeypatch)
    exited = threading.Event()
    driver = SyntheticMidi('CASIO USB-MIDI')
    monkeypatch.setattr('chopin.platform.linux.runtime.adapters', lambda **_: StudioPlatform(midi_input=driver))
    monkeypatch.setattr(MidiInput, 'start', MidiInput.poll)
    with TestClient(create_app(tmp_path, hardware=True, shutdown=exited.set)) as client:
        now[0] = 1000
        tick(client)
        assert not exited.is_set()
        driver.ports.clear()
        client.app.state.studio.midi.poll()
        tick(client)
        now[0] = 1299
        tick(client)
        assert not exited.is_set()
        now[0] = 1300
        assert exited.wait(2)


def test_idle_shutdown_waits_for_saving_and_survives_save_failure(tmp_path, monkeypatch):
    now = virtual_clock(monkeypatch)
    exited = threading.Event()
    app = create_app(tmp_path, hardware=False, shutdown=exited.set)
    with TestClient(app) as client:
        client.post('/api/record/start')
        recorder = app.state.recorder
        original = recorder.stop
        recorder.saving = True
        now[0] = 300
        tick(client)
        assert not exited.is_set()
        recorder.saving = False
        def fail():
            raise OSError('disk full')
        monkeypatch.setattr(recorder, 'stop', fail)
        tick(client)
        assert not exited.is_set()
        assert not client.get('/api/status').json()['shutting_down']
        monkeypatch.setattr(recorder, 'stop', original)
        assert exited.wait(2)
