"""Explicit shutdown must save recordings and stop the real server gracefully."""
import os
import socket
import subprocess
import sys
import time

import httpx
import mido
from fastapi.testclient import TestClient

from chopin.app import create_app


def test_shutdown_requires_explicit_header_and_saves(tmp_path):
    calls = []
    app = create_app(tmp_path, hardware=False, shutdown=lambda: calls.append('exit'))
    with TestClient(app) as client:
        ident = client.post('/api/record/start').json()['id']
        app.state.recorder.receive(mido.Message('note_on', note=60, velocity=80))
        assert client.post('/api/shutdown').status_code == 403
        assert client.post('/api/shutdown', headers={'X-Chopin-Shutdown': '1', 'Origin': 'https://example.com'}).status_code == 403
        assert app.state.recorder.active == ident
        assert not calls
        response = client.post('/api/shutdown', headers={'X-Chopin-Shutdown': '1'})
        assert response.status_code == 200
        assert calls == ['exit']
        assert (tmp_path / 'sessions' / ident / 'original.mid').exists()
        assert app.state.store.query('SELECT status FROM sessions')[0]['status'] == 'saved'
        assert client.get('/api/status').json()['shutting_down']
        assert client.post('/api/record/start').status_code == 503


def test_save_failure_leaves_backend_running(tmp_path, monkeypatch):
    calls = []
    app = create_app(tmp_path, hardware=False, shutdown=lambda: calls.append('exit'))
    with TestClient(app) as client:
        client.post('/api/record/start')
        original = app.state.recorder.stop
        def fail():
            raise OSError('disk full')
        monkeypatch.setattr(app.state.recorder, 'stop', fail)
        assert client.post('/api/shutdown', headers={'X-Chopin-Shutdown': '1'}).status_code == 409
        assert not calls
        assert not client.get('/api/status').json()['shutting_down']
        monkeypatch.setattr(app.state.recorder, 'stop', original)


def test_real_server_shutdown_and_restart(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'CHOPIN_PORT': str(port), 'CHOPIN_DATA_DIR': str(tmp_path / 'data'),
           'CHOPIN_NO_HARDWARE': '1', 'XDG_STATE_HOME': str(tmp_path / 'state')}
    with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=1) as client:
        for attempt in range(2):
            process = subprocess.Popen([sys.executable, '-m', 'chopin'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        if client.get('/api/status').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise AssertionError('Server did not start')
                    time.sleep(.05)
                if attempt == 0:
                    ident = client.post('/api/record/start').json()['id']
                else:
                    assert client.get('/api/sessions').json()[0]['status'] == 'saved'
                    assert client.get(f'/api/sessions/{ident}/midi').content.startswith(b'MThd')
                assert client.post('/api/shutdown', headers={'X-Chopin-Shutdown': '1'}).status_code == 200
                assert process.wait(timeout=10) == 0
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
                process.stderr.close()
