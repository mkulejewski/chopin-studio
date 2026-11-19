"""Synthetic acoustic fixtures: no test opens the user's microphone."""
import json
import time
from types import SimpleNamespace

import mido
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.microphone import RATE, analyse_audio, audio_ranges, export_audio, finalise, metadata, write_metadata
from chopin.organisation import analyse_segment, organise
from chopin.recorder import Recorder
from chopin.store import Store


def recording(store, times, duration=12, delay=.13):
    recorder = Recorder(store)
    ident = recorder.start()
    recorder.stop()
    folder = store.root / 'sessions' / ident
    data = np.zeros(round(duration * RATE))
    for onset in times:
        left = round((onset + delay) * RATE)
        length = min(round(.25 * RATE), len(data) - left)
        if length > 0:
            t = np.arange(length) / RATE
            data[left:left + length] += .5 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 22)
    sf.write(folder / 'microphone.flac', data, RATE, subtype='PCM_16')
    write_metadata(folder, {'offset_seconds': 0, 'filename': 'microphone.flac', 'duration': duration})
    store.execute('UPDATE sessions SET duration=? WHERE id=?', (duration, ident))
    return ident, folder


def test_acoustic_alignment_and_quality(tmp_path):
    store = Store(tmp_path)
    times = [1, 1.63, 2.48, 3.7, 4.26, 5.83, 6.6, 7.9, 8.5]
    ident, folder = recording(store, times)
    notes = [{'onset': t, 'velocity': 80} for t in times]
    result = analyse_audio(folder, {'start': 0, 'end': 10}, notes)
    assert result['available']
    assert result['clipped_sample_fraction'] == 0
    assert result['peak_dbfs'] == pytest.approx(-6, abs=1)
    assert result['correlation']['status'] == 'estimated'
    assert result['correlation']['audio_minus_midi_seconds'] == pytest.approx(.13, abs=.025)
    assert result['correlation']['matched_groups'] >= 8
    assert result['correlation']['median_absolute_residual_ms'] < 15
    assert all(abs(e['residual_ms']) <= 45 for e in result['correlation']['events'])
    # An explicit capture fault prevents a misleading alignment claim.
    info = metadata(folder)
    info['capture_error'] = 'overrun'
    write_metadata(folder, info)
    assert analyse_audio(folder, {'start': 0, 'end': 10}, notes)['correlation']['status'] == 'unavailable'


def test_audio_only_splitting_and_exact_cuts(tmp_path):
    store = Store(tmp_path)
    ident, folder = recording(store, [1, 2, 28, 29], duration=34, delay=0)
    ranges = audio_ranges(folder, 34, 20)
    assert len(ranges) == 2
    segments = organise(store, ident)
    assert len(segments) == 2
    assert all(s['piece_id'] is None for s in segments)
    result = analyse_segment(store, segments[0])
    assert result['audio']['available'] and result['notes'] == 0
    assert result['audio']['correlation']['status'] == 'unavailable'
    segment = {**segments[0], 'start': .5, 'end': 3.0}
    path = export_audio(store, segment)
    with sf.SoundFile(path) as clip:
        assert len(clip) == round(2.5 * RATE)
        assert clip.samplerate == RATE
    # A revision to the boundary must produce a different clip.
    changed = export_audio(store, {**segment, 'end': 2.0})
    assert changed != path
    assert sf.info(changed).frames == round(1.5 * RATE)
    assert sf.info(folder / 'microphone.flac').frames == round(34 * RATE)


def test_raw_crash_recovery_keeps_audio_duration(tmp_path):
    store = Store(tmp_path)
    ident = 'a' * 32
    folder = tmp_path / 'sessions' / ident
    folder.mkdir()
    store.execute('INSERT INTO sessions(id,name,started,status) VALUES(?,?,?,?)', (ident, 'interrupted', '2026-11-09T10:00:00Z', 'recording'))
    (folder / 'events.jsonl').write_text(json.dumps({'kind': 'start', 't': 0}) + '\n')
    (folder / 'microphone.pcm').write_bytes(np.ones(RATE * 2, dtype='<i2').tobytes())
    write_metadata(folder, {'offset_seconds': .1})
    Recorder(store)
    assert metadata(folder)['duration'] == 2
    assert sf.info(folder / 'microphone.flac').frames == RATE * 2
    assert not (folder / 'microphone.pcm').exists()
    row = store.query('SELECT * FROM sessions')[0]
    assert row['status'] == 'recovered'
    assert row['duration'] == pytest.approx(2.1)


def test_independent_sources_and_capture_failure(tmp_path):
    class FakeMicrophone:
        def __init__(self, folder, device, epoch):
            self.folder = folder

            assert device == 'default'
        def running(self):return True
        def stop(self):
            return {'duration': 1}
    source = SimpleNamespace(start=FakeMicrophone)
    recorder = Recorder(Store(tmp_path), source)
    with pytest.raises(ValueError, match='Enable MIDI'):
        recorder.start(midi_enabled=False)
    ident = recorder.start(midi_enabled=False, microphone_enabled=True)
    recorder.receive(mido.Message('note_on', note=60))
    recorder.device_disconnected_at = time.monotonic() - 30
    assert recorder.stop_if_disconnected() is None
    assert recorder.status()['microphone_enabled']
    recorder.stop()
    assert recorder.events == 0
    recorder.start(midi_enabled=True, microphone_enabled=True)
    recorder.receive(mido.Message('note_on', note=60))
    recorder.stop()
    assert recorder.events == 1
    def failure(*args):
        raise ValueError('input failed')
    source.start = failure
    before = len(list((tmp_path / 'sessions').iterdir()))
    with pytest.raises(ValueError, match='input failed'):
        recorder.start(microphone_enabled=True)
    assert not recorder.active
    assert len(list((tmp_path / 'sessions').iterdir())) == before


def test_audio_routes_and_shared_download_names(tmp_path):
    app = create_app(tmp_path, hardware=False)
    with TestClient(app) as client:
        assert client.post('/api/record/start', json={'midi_enabled': False, 'microphone_enabled': False}).status_code == 400
        ident, folder = recording(app.state.store, [1, 2, 3])
        segments = organise(app.state.store, ident)
        segment = segments[0]
        response = client.get(f"/api/segments/{segment['id']}/microphone")
        assert response.status_code == 200 and response.content[:4] == b'fLaC'
        audio_name = response.headers['content-disposition'].split('__microphone.flac')[0]
        midi = client.get(f"/api/segments/{segment['id']}/midi")
        assert midi.headers['content-disposition'].split('__midi.mid')[0] == audio_name
        assert client.get(f'/api/sessions/{ident}/microphone').content[:4] == b'fLaC'
        assert client.get(f'/api/sessions/{ident}/recording').json()['microphone']['filename']
        assert client.get('/api/segments/missing/microphone').status_code == 404
        assert client.get('/api/sessions/missing/recording').status_code == 404


def test_low_evidence_and_periodic_alignment_withheld(tmp_path):
    store = Store(tmp_path)
    times = list(np.arange(1., 9., .25))
    _, folder = recording(store, times)
    result = analyse_audio(folder, {'start': 0, 'end': 10}, [{'onset': t, 'velocity': 70} for t in times])
    assert result['correlation']['status'] == 'uncertain'
    assert analyse_audio(folder, {'start': 20, 'end': 30}, [])['available'] is False


def test_finalisation_failure_retains_source(tmp_path, monkeypatch):
    raw = tmp_path / 'microphone.pcm'
    raw.write_bytes(b'\0\0' * RATE)
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(sf, 'SoundFile', fail)
    with pytest.raises(OSError):finalise(tmp_path, {'offset_seconds': 0})
    assert raw.exists()


@pytest.mark.parametrize('before, shutdown, exited, timed_out, has_error', [
    ('', 'Aborted by signal Interrupt...\n', False, False, False),
    ('', 'arecord: pcm_read:2240: read error: Interrupted system call\n', False, False, False),
    ('', 'arecord: pcm_read:999: read error: Interrupted system call\n', False, False, False),
    ('arecord: pcm_read:2240: read error: Interrupted system call\n', '', False, False, True),
    ('', 'arecord: pcm_read:2240: read error: Input/output error\n', False, False, True),
    ('', 'arecord: pcm_read:2240: read error: Interrupted system call\noverrun!!!\n', False, False, True),
    ('arecord: pcm_read:2240: read error: Interrupted system call\n', '', True, False, True),
    ('', '', True, False, True),
    ('', 'arecord: pcm_read:2240: read error: Interrupted system call\n', False, True, True),
])
def test_capture_process_flags_clean_stop_and_failure(tmp_path, monkeypatch, before, shutdown, exited, timed_out, has_error):
    import subprocess
    from chopin.platform.linux.microphone import Microphone
    monkeypatch.setattr('chopin.platform.linux.microphone.shutil.which', lambda name: '/usr/bin/arecord')
    monkeypatch.setattr('chopin.platform.linux.microphone.time.sleep', lambda seconds: None)
    class Process:
        def __init__(self, command, **kwargs):
            assert 'microphone_capture.py' in command[1]
            assert command[3] == '/usr/bin/arecord'
            assert command[command.index('-t') + 1] == 'raw'
            assert command[command.index('-c') + 1] == '1'
            assert command[command.index('-D') + 1] == 'default'
            self.exited = False
            self.pid = 12345
            self.stderr = kwargs['stderr']
            (tmp_path / 'microphone.pcm').write_bytes(b'\0\0' * RATE)
        def poll(self):return 0 if self.exited else None
        def send_signal(self, signal):
            self.stderr.write(shutdown)
            self.stderr.flush()
            self.exited = True
        def wait(self, timeout=None):
            if timed_out and timeout is not None:
                raise subprocess.TimeoutExpired('capture', timeout)
            return 0
    monkeypatch.setattr('chopin.platform.linux.microphone.subprocess.Popen', Process)
    killed = []
    monkeypatch.setattr('chopin.platform.linux.microphone.os.killpg', lambda pid, sig: killed.append(pid))
    capture = Microphone(tmp_path, 'default', time.monotonic_ns())
    capture.errors.write(before)
    capture.errors.flush()
    capture.process.exited = exited
    result = capture.stop()
    assert bool(result['capture_error']) == has_error
    if 'overrun' in shutdown:
        assert 'overrun!!!' in result['capture_error']
    assert bool(killed) == timed_out
    assert (tmp_path / 'microphone.log').read_text() == before + ('' if exited else shutdown)
    assert result['duration'] == 1
    assert (tmp_path / 'microphone.flac').exists()
    assert not (tmp_path / 'microphone.pcm').exists()


def test_microphone_save_failure_does_not_lose_midi(tmp_path):
    class FailedMicrophone:
        def __init__(self, folder, device, epoch):

            (folder / 'microphone.pcm').write_bytes(b'\0\0' * RATE)
            write_metadata(folder, {'offset_seconds': 0})
        def stop(self):raise OSError('disk full')
    store = Store(tmp_path)
    recorder = Recorder(store, SimpleNamespace(start=FailedMicrophone))
    ident = recorder.start(microphone_enabled=True)
    recorder.receive(mido.Message('note_on', note=60))
    recorder.stop()
    folder = tmp_path / 'sessions' / ident
    assert (folder / 'original.mid').exists()
    assert store.query('SELECT * FROM sessions')[0]['status'] == 'incomplete'
    assert recorder.events == 1
    # Startup retries an incomplete conversion while retaining MIDI.
    Recorder(store)
    assert sf.info(folder / 'microphone.flac').frames == RATE
    assert store.query('SELECT * FROM sessions')[0]['status'] == 'recovered'


def test_capture_supervisor_survives_starting_thread_exit():
    import os
    import signal
    import subprocess
    import sys
    import threading
    from pathlib import Path
    from chopin.platform.linux import microphone_capture
    child = []
    def launch():
        child.append(subprocess.Popen([sys.executable, str(Path(microphone_capture.__file__)), str(os.getpid()),
                                       sys.executable, '-c', 'import time; time.sleep(60)'],
                                      start_new_session=True, stderr=subprocess.DEVNULL))
    worker = threading.Thread(target=launch)
    worker.start()
    worker.join()
    process = child[0]
    try:
        time.sleep(.4)
        assert process.poll() is None
        process.send_signal(signal.SIGINT)
        process.wait(5)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def test_capture_supervisor_stops_when_backend_exits(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    from chopin.platform.linux import microphone_capture
    marker = tmp_path / 'capture.pid'
    engine = f'import os,time; from pathlib import Path; Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(60)'
    parent_code = ('import os,subprocess,sys,time; '
                   'p=subprocess.Popen([sys.executable,sys.argv[1],str(os.getpid()),sys.executable,"-c",sys.argv[2]],start_new_session=True); '
                   'print(p.pid,flush=True); time.sleep(60)')
    parent = subprocess.Popen([sys.executable, '-c', parent_code, str(Path(microphone_capture.__file__)), engine],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    supervisor = int(parent.stdout.readline())
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        assert marker.exists()
        engine_pid = int(marker.read_text())
        parent.terminate()
        parent.wait(5)
        def running(pid):
            path = Path(f'/proc/{pid}/stat')
            return path.exists() and path.read_text().split()[2] != 'Z'
        while (running(supervisor) or running(engine_pid)) and time.monotonic() < deadline:
            time.sleep(.02)
        assert not running(supervisor)
        assert not running(engine_pid)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()
        try:os.killpg(supervisor, 9)
        except ProcessLookupError:pass
