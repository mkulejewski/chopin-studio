"""Synthetic MIDI and waveforms only: never opens a microphone or piano."""
import json
import uuid
from datetime import datetime, timezone

import mido
import numpy as np
import pytest
import soundfile as sf

from chopin.store import Store
from chopin.recorder import Recorder
from chopin.microphone import analyse_audio, metadata, write_metadata, audio_blocks
from chopin.headphone_audio import needs_review, mark_reviewed
from chopin.midi_files import export_midi
from chopin.jobs import Jobs
from chopin.retention import catalogue, discard_unheard_microphone, recover_deletions

RATE = 16000


def fixture(tmp_path, sound='silence', duration=8, pitches=None, start=0, end=None, delay=.1):
    store = Store(tmp_path)
    recorder = Recorder(store)
    session = recorder.start()
    recorder.stop()
    folder = store.root/'sessions'/session
    pitches = pitches or [60, 64, 67, 72, 65, 69, 62, 67, 71, 74]
    times = np.linspace(.5, duration-1, len(pitches))
    notes = [{'pitch': pitch, 'onset': float(at), 'duration': .3, 'velocity': 80} for at,pitch in zip(times,pitches)]
    rng = np.random.default_rng(123)
    data = rng.normal(0, .00003, round(duration*RATE))
    if sound == 'noise':
        data = rng.normal(0, .008, len(data))
    elif sound == 'loud_noise':
        data = rng.normal(0, .1, len(data))
    elif sound in ('piano', 'quiet_piano'):
        amplitude = .15 if sound == 'piano' else .0002
        for note in notes:
            begin = round((note['onset']+delay)*RATE)
            size = min(round(.5*RATE), len(data)-begin)
            t = np.arange(size)/RATE
            f = 440*2**((note['pitch']-69)/12)
            data[begin:begin+size] += amplitude*(np.sin(2*np.pi*f*t)+.3*np.sin(4*np.pi*f*t))*np.exp(-t*8)
    elif sound == 'clacks':
        for at in times:
            begin = round(at*RATE)
            data[begin:begin+40] += rng.normal(0, .05, 40)
    sf.write(folder/'microphone.flac', data, RATE, subtype='PCM_16')
    write_metadata(folder, {'filename': 'microphone.flac', 'offset_seconds': 0, 'duration': duration})
    events = []
    for note in notes:
        events.extend([{'t': note['onset'], 'message': mido.Message('note_on', note=note['pitch'], velocity=80).dict()},
                       {'t': note['onset']+.3, 'message': mido.Message('note_off', note=note['pitch']).dict()}])
    events.sort(key=lambda e: e['t'])
    events.append({'t': duration, 'kind': 'stop'})
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    export_midi(folder/'events.jsonl', folder/'original.mid', duration)
    store.execute("UPDATE sessions SET duration=?,status='saved',error=NULL WHERE id=?", (duration,session))
    ident = uuid.uuid4().hex
    store.execute("INSERT INTO segments(id,session_id,start,end,piece_id,label,kind,complete) VALUES(?,?,?,?,?,'Test','complete',1)",
                  (ident,session,start,end or duration,'n9-1'))
    row = store.query('SELECT * FROM segments WHERE id=?', (ident,))[0]
    return store, session, folder, row, notes


@pytest.mark.parametrize('sound', ['silence', 'noise', 'clacks'])
def test_sustained_midi_without_piano_is_detected(tmp_path, sound):
    _,_,folder,row,notes = fixture(tmp_path, sound)
    presence = analyse_audio(folder,row,notes)['piano_presence']
    assert presence['status'] == 'inaudible', presence
    assert presence['auto_discard']
    assert presence['checked_groups'] >= 8
    assert presence['tonal_groups'] == 0


@pytest.mark.parametrize('sound', ['piano', 'quiet_piano', 'loud_noise'])
def test_audible_quiet_piano_and_uncertain_loud_background_are_not_discarded(tmp_path, sound):
    _,_,folder,row,notes = fixture(tmp_path, sound)
    presence = analyse_audio(folder,row,notes)['piano_presence']
    assert not presence['auto_discard'], presence
    assert presence['status'] == ('uncertain' if sound == 'loud_noise' else 'audible')


def test_no_midi_short_midi_capture_errors_and_missing_coverage_are_protected(tmp_path):
    _,_,folder,row,notes = fixture(tmp_path)
    assert not analyse_audio(folder,row,[])['piano_presence']['auto_discard']
    assert not analyse_audio(folder,row,notes[:4])['piano_presence']['auto_discard']
    info = metadata(folder)
    write_metadata(folder,{**info,'capture_error':'overrun'})
    assert not analyse_audio(folder,row,notes)['piano_presence']['auto_discard']
    write_metadata(folder,{**info,'offset_seconds':3})
    assert not analyse_audio(folder,row,notes)['piano_presence']['auto_discard']


def test_automatic_analysis_deletes_only_microphone_and_removes_it_from_quota(tmp_path):
    store,session,folder,row,_ = fixture(tmp_path)
    before = {name:(folder/name).read_bytes() for name in ('events.jsonl','original.mid')}
    jobs = Jobs(store)
    try:
        result = jobs.save_analysis(row,uuid.uuid4().hex)
        assert result['audio']['discarded_for_headphone_play']
        assert not result['audio']['available']
        assert not list(folder.glob('*.flac'))
        assert metadata(folder)['filename'] is None
        assert metadata(folder)['headphone_play'][row['id']]['action'] == 'discarded'
        assert catalogue(store) == []
        assert all((folder/name).read_bytes() == content for name,content in before.items())
        assert store.query('SELECT id FROM sessions WHERE id=?',(session,))
        assert store.query('SELECT id FROM segments WHERE id=?',(row['id'],))
        assert store.query('SELECT id FROM analyses WHERE segment_id=?',(row['id'],))
        repeated = jobs.save_analysis(row,uuid.uuid4().hex)
        assert repeated['audio']['discarded_for_headphone_play']
    finally:
        jobs.close()


def test_manual_keep_is_protected_but_does_not_use_a_shortlist_slot(tmp_path):
    store,_,folder,row,_ = fixture(tmp_path)
    store.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(row['id'],))
    jobs = Jobs(store)
    try:
        jobs.save_analysis(row,uuid.uuid4().hex)
        assert (folder/'microphone.flac').exists()
        take = catalogue(store)[0]
        assert take['action'] == 'keep'
        assert not take['eligible'] and take['headphone_audio_excluded']
    finally:
        jobs.close()


def test_deletion_failure_is_retryable_and_preserves_midi(tmp_path, monkeypatch):
    store,_,folder,row,notes = fixture(tmp_path)
    result = {'audio': analyse_audio(folder,row,notes)}
    from chopin import microphone
    original = microphone.compact_audio
    def fail(*args, **kwargs): raise OSError('disk full')
    monkeypatch.setattr(microphone,'compact_audio',fail)
    with pytest.raises(OSError): discard_unheard_microphone(store,row,result)
    assert (folder/'microphone.flac').exists()
    assert (folder/'original.mid').exists()
    assert store.query("SELECT id FROM recording_deletions WHERE scope='headphone' AND status='pending'")
    monkeypatch.setattr(microphone,'compact_audio',original)
    recover_deletions(store)
    assert not list(folder.glob('*.flac'))
    assert (folder/'original.mid').exists()


def test_changed_audio_or_overlapping_takes_are_not_deleted_on_old_evidence(tmp_path):
    store,session,folder,row,notes = fixture(tmp_path)
    result = {'audio': analyse_audio(folder,row,notes)}
    store.execute("INSERT INTO segments(id,session_id,start,end,label,kind) VALUES(?,?,1,3,'overlap','partial')",(uuid.uuid4().hex,session))
    assert not discard_unheard_microphone(store,row,result)
    store.execute('DELETE FROM segments WHERE id<>?',(row['id'],))
    sf.write(folder/'microphone.flac',np.ones(8*RATE)*.1,RATE)
    assert not discard_unheard_microphone(store,row,result)
    assert (folder/'microphone.flac').exists()


def test_backfill_check_is_idempotent_and_notices_changed_audio(tmp_path):
    _,_,folder,_,_ = fixture(tmp_path)
    assert needs_review(folder)
    mark_reviewed(folder)
    assert not needs_review(folder)
    sf.write(folder/'microphone.flac',np.zeros(RATE),RATE)
    assert needs_review(folder)


def test_mixed_session_compacts_only_the_headphone_take_and_keeps_rendered_audio(tmp_path):
    pitches = [60,64,67,72,65,69,62,67,71,74]*2
    store,session,folder,row,notes = fixture(tmp_path,'piano',duration=16,pitches=pitches,start=8,end=16)
    samples,rate = sf.read(folder/'microphone.flac',dtype='int16')
    samples[8*rate:] = 0
    sf.write(folder/'microphone.flac',samples,rate,subtype='PCM_16')
    other = uuid.uuid4().hex
    store.execute("INSERT INTO segments(id,session_id,start,end,piece_id,label,kind,complete) VALUES(?,?,0,8,'n9-1','audible','complete',1)",(other,session))
    rendered = store.root/'audio'/'rendered.wav'
    rendered.write_bytes(b'explicit MIDI render')
    store.execute("INSERT INTO jobs(id,kind,status,created,result) VALUES(?,'render','done',?,?)",(uuid.uuid4().hex,datetime.now(timezone.utc).isoformat(),json.dumps({'segment_id':row['id'],'session_id':session,'filename':rendered.name})))
    result = {'audio': analyse_audio(folder,row,[n for n in notes if n['onset'] >= 8])}
    assert result['audio']['piano_presence']['auto_discard']
    assert discard_unheard_microphone(store,row,result)
    retained = np.concatenate([block[:,0] for _,block,_ in audio_blocks(folder,dtype='int16')])
    np.testing.assert_array_equal(retained,samples[:8*rate])
    assert rendered.read_bytes() == b'explicit MIDI render'
    assert (folder/'original.mid').exists()


def test_headphone_recording_cannot_displace_two_audible_takes(tmp_path):
    store,_,_,first,_ = fixture(tmp_path,'piano')
    other_store,_,_,second,_ = fixture(tmp_path,'piano')
    other_store.db.close()
    other_store,_,_,silent,_ = fixture(tmp_path)
    other_store.db.close()
    jobs = Jobs(store)
    try:
        jobs.save_analysis(silent,uuid.uuid4().hex)
        kept = {r['id'] for r in catalogue(store) if r['action'] == 'keep'}
        assert kept == {first['id'],second['id']}
        assert silent['id'] not in {r['id'] for r in catalogue(store)}
    finally:
        jobs.close()


def test_capture_integrity_fault_and_keep_during_retry_protect_original(tmp_path, monkeypatch):
    store,session,folder,row,notes = fixture(tmp_path)
    store.execute('UPDATE sessions SET error=? WHERE id=?',('Journal lost events',session))
    jobs = Jobs(store)
    try:
        result = jobs.save_analysis(row,uuid.uuid4().hex)
        assert not result['audio']['piano_presence']['auto_discard']
        assert (folder/'microphone.flac').exists()
    finally:
        jobs.close()
    store.execute('UPDATE sessions SET error=NULL WHERE id=?',(session,))
    result = {'audio': analyse_audio(folder,row,notes)}
    from chopin import microphone
    original = microphone.compact_audio
    monkeypatch.setattr(microphone,'compact_audio',lambda *a, **k: (_ for _ in ()).throw(OSError('full')))
    with pytest.raises(OSError): discard_unheard_microphone(store,row,result)
    store.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(row['id'],))
    monkeypatch.setattr(microphone,'compact_audio',original)
    recover_deletions(store)
    assert (folder/'microphone.flac').exists()
    assert store.query("SELECT id FROM recording_deletions WHERE scope='headphone' AND status='cancelled'")


def test_corrupt_audio_manifest_does_not_crash_startup_review_check(tmp_path):
    _,_,folder,_,_ = fixture(tmp_path)
    (folder/'microphone.json').write_text('{bad')
    assert needs_review(folder)


@pytest.mark.parametrize('delay', [-.35, .45])
def test_quiet_piano_is_kept_despite_uncalibrated_midi_audio_offset(tmp_path, delay):
    _,_,folder,row,notes = fixture(tmp_path,'quiet_piano',delay=delay)
    presence = analyse_audio(folder,row,notes)['piano_presence']
    assert not presence['auto_discard'], presence
    assert presence['tonal_groups'] > 0


def test_existing_audio_is_checked_automatically_once_on_restart(tmp_path):
    import time
    from fastapi.testclient import TestClient
    from chopin.app import create_app
    store,session,folder,_,_ = fixture(tmp_path)
    store.set_setting('organised:'+session,True)
    midi = (folder/'original.mid').read_bytes()
    store.db.close()
    app = create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        for _ in range(150):
            jobs = app.state.store.query("SELECT status,error FROM jobs WHERE kind='organisation'")
            if jobs and all(j['status'] in ('done','failed') for j in jobs):break
            time.sleep(.02)
        assert jobs and all(j['status'] == 'done' for j in jobs), jobs
        assert metadata(folder)['filename'] is None
        assert (folder/'original.mid').read_bytes() == midi
        assert not client.get('/api/recordings').json()['takes']
    again = create_app(tmp_path,hardware=False)
    with TestClient(again):
        assert len(again.state.store.query("SELECT id FROM jobs WHERE kind='organisation'")) == len(jobs)
        assert (folder/'original.mid').read_bytes() == midi


def test_soft_notes_protect_an_otherwise_silent_take(tmp_path):
    _,_,folder,row,notes = fixture(tmp_path)
    notes[-1]['velocity'] = 10
    data = np.zeros(8*RATE)
    last = notes[-1]
    start = round((last['onset']+.1)*RATE)
    t = np.arange(min(RATE//2,len(data)-start))/RATE
    f = 440*2**((last['pitch']-69)/12)
    data[start:start+len(t)] = .0003*np.sin(2*np.pi*f*t)*np.exp(-t*8)
    sf.write(folder/'microphone.flac',data,RATE,subtype='PCM_16')
    presence = analyse_audio(folder,row,notes)['piano_presence']
    assert not presence['auto_discard'], presence
    assert presence['tonal_groups'] > 0
