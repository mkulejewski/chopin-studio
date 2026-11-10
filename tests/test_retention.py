import json
import time
import uuid
from datetime import datetime, timezone

import mido
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.microphone import compact_audio, audio_blocks, metadata, write_metadata, export_audio
from chopin.midi_files import export_midi, journal_events
from chopin.recorder import Recorder
from chopin.retention import catalogue, delete_take, delete_session, recover_deletions
from chopin.store import Store


def fixture_session(store, duration=3):
    recorder=Recorder(store)
    ident=recorder.start()
    recorder.stop()
    folder=store.root/'sessions'/ident
    events=[]
    for t in (.2,1.2,2.2):
        for offset,msg in [(0,mido.Message('note_on',note=60)),(.1,mido.Message('note_off',note=60))]:
            events.append({'t':t+offset,'message':msg.dict()})
    events.append({'t':duration,'kind':'stop'})
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    export_midi(folder/'events.jsonl',folder/'original.mid',duration)
    store.execute('UPDATE sessions SET duration=?,events=6 WHERE id=?',(duration,ident))
    samples=np.arange(round(duration*1000),dtype='int16')-1000
    sf.write(folder/'microphone.flac',samples,1000,subtype='PCM_16')
    write_metadata(folder,{'filename':'microphone.flac','offset_seconds':0,'duration':duration})
    store.set_setting('organised:'+ident,True)
    return ident,folder,samples


def take(store,session,start=0,end=1,complete=True,piece='n9-1'):
    ident=uuid.uuid4().hex
    store.execute('INSERT INTO segments(id,session_id,start,end,piece_id,label,kind,complete) VALUES(?,?,?,?,?,?,?,?)',
                  (ident,session,start,end,piece,'Test','complete' if complete else 'partial',int(complete)))
    return store.query('SELECT * FROM segments WHERE id=?',(ident,))[0]


def score(store,row,value):
    result={'segment_snapshot':{k:row[k] for k in ('piece_id','start','end','revision','discarded','complete')},
            'assessment':{'precision_score':value,'reference_quality':'verified','level':'good'}}
    store.execute('INSERT INTO analyses(id,session_id,segment_id,version,created,result) VALUES(?,?,?,?,?,?)',
                  (uuid.uuid4().hex,row['session_id'],row['id'],'test',datetime.now(timezone.utc).isoformat(),json.dumps(result)))


def test_two_best_eligible_takes_and_manual_choices(tmp_path):
    store=Store(tmp_path);session,_,_=fixture_session(store)
    takes=[take(store,session) for _ in range(4)]
    for row,value in zip(takes,[94,98,96,97]):score(store,row,value)
    partial=take(store,session,complete=False);score(store,partial,100)
    decisions={r['id']:r for r in catalogue(store)}
    assert {r['id'] for r in decisions.values() if r['action']=='keep'}=={takes[1]['id'],takes[3]['id']}
    assert not decisions[partial['id']]['eligible']
    store.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(takes[0]['id'],))
    assert {r['id'] for r in catalogue(store) if r['action']=='keep'}=={takes[0]['id'],takes[1]['id']}
    # Recommendations never remove any recording bytes.
    assert (tmp_path/'sessions'/session/'microphone.flac').exists()
    assert len(catalogue(store))==5


def test_near_complete_buffer_and_manual_complete(tmp_path):
    store=Store(tmp_path);session,_,_=fixture_session(store)
    ref=uuid.uuid4().hex
    notes=[{'pitch':60+i,'onset':i,'duration':.5,'measure':i+1} for i in range(20)]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',(ref,'n9-1','test.musicxml','local','private','test','verified',json.dumps(notes),'2026-11-09'))
    row=take(store,session,complete=False)
    match={'reference_id':ref,'confidence':.8,'reference_start':2,'reference_end':18,'pairs':[[i,i+2] for i in range(16)]}
    store.execute('UPDATE segments SET details=? WHERE id=?',(json.dumps({'match':match}),row['id']))
    candidate=catalogue(store)[0]
    assert candidate['eligible'] and 'Near-complete' in candidate['eligibility_reason']
    match['pairs']=match['pairs'][:8]
    store.execute('UPDATE segments SET details=? WHERE id=?',(json.dumps({'match':match}),row['id']))
    assert not catalogue(store)[0]['eligible']
    store.execute("UPDATE segments SET complete=1,kind='complete' WHERE id=?",(row['id'],))
    assert catalogue(store)[0]['eligible']


def test_compaction_preserves_exact_samples_and_original_times(tmp_path):
    store=Store(tmp_path);session,folder,samples=fixture_session(store)
    compact_audio(folder,1,2,'delete-middle')
    info=metadata(folder)
    decoded,rate=sf.read(folder/info['filename'],dtype='int16')
    np.testing.assert_array_equal(decoded,np.concatenate((samples[:1000],samples[2000:])))
    assert not (folder/'microphone.flac').exists()
    assert len(list(folder.glob('*.flac')))==1
    assert [part['start'] for part in info['spans']]==[0,2]
    block=list(audio_blocks(folder,2,3,dtype='int16'))
    assert block[0][0]==2
    np.testing.assert_array_equal(np.concatenate([b[:,0] for _,b,_ in block]),samples[2000:])
    compact_audio(folder,1,2,'delete-middle')  # Retry is idempotent.
    assert sf.info(folder/metadata(folder)['filename']).frames==2000
    compact_audio(folder,0,1,'delete-first')
    np.testing.assert_array_equal(sf.read(folder/metadata(folder)['filename'],dtype='int16')[0],samples[2000:])


def test_audio_removal_preserves_midi_exports_analyses_and_session_history(tmp_path):
    store=Store(tmp_path);session,folder,samples=fixture_session(store)
    left=take(store,session,0,1);middle=take(store,session,1,2);right=take(store,session,2,3)
    score(store,middle,99)
    cached=store.root/'exports'/middle['id'];cached.mkdir();(cached/'old.flac').write_bytes(b'old')
    (cached/'segment.mid').write_bytes(b'preserved MIDI export')
    (folder/'source.csv').write_bytes(b'preserved import')
    before={name:(folder/name).read_bytes() for name in ('events.jsonl','original.mid','source.csv')}
    session_before=store.query('SELECT * FROM sessions WHERE id=?',(session,))[0]
    delete_take(store,middle)
    assert {r['id'] for r in catalogue(store)}=={left['id'],right['id']}
    assert all((folder/name).read_bytes()==data for name,data in before.items())
    assert store.query('SELECT * FROM sessions WHERE id=?',(session,))[0]==session_before
    assert store.query('SELECT * FROM analyses WHERE segment_id=?',(middle['id'],))
    assert not (cached/'old.flac').exists()
    assert (cached/'segment.mid').read_bytes()==b'preserved MIDI export'
    assert store.query('SELECT discarded FROM segments WHERE id=?',(middle['id'],))[0]['discarded']==0
    clip=export_audio(store,right)
    np.testing.assert_array_equal(sf.read(clip,dtype='int16')[0],samples[2000:])
    deletion=store.query('SELECT * FROM recording_deletions')[0]
    assert deletion['status']=='done' and deletion['scope']=='audio'


def test_whole_session_deletion_includes_empty_and_owned_artifacts(tmp_path):
    store=Store(tmp_path);session,folder,_=fixture_session(store)
    row=take(store,session);score(store,row,99)
    store.execute('INSERT INTO reports VALUES(?,?,?,?,?,?)',('report',session,'local','now','text','{}'))
    report=store.query('SELECT id FROM analyses')[0]['id'];(store.root/'reports'/(report+'.json')).write_text('{}')
    (store.root/'exports'/(session+'.zip')).write_bytes(b'zip')
    (store.root/'audio'/'render.flac').write_bytes(b'audio')
    store.execute('INSERT INTO jobs(id,kind,status,created,result) VALUES(?,?,?,?,?)',('render','render','done','now',json.dumps({'filename':'render.flac','session_id':session,'segment_id':row['id']})))
    other,other_folder,_=fixture_session(store)
    delete_session(store,session)
    assert not folder.exists() and other_folder.exists()
    assert store.query('SELECT * FROM sessions WHERE id=?',(session,))==[]
    assert store.query('SELECT * FROM reports')==[]
    assert not (store.root/'audio'/'render.flac').exists()
    assert not (store.root/'exports'/(session+'.zip')).exists()
    assert store.query('PRAGMA foreign_key_check')==[]
    # Empty/no-MIDI sessions have no takes but must still be deletable.
    delete_session(store,other)
    assert not other_folder.exists()


def test_explicit_confirmation_audio_only_removal_and_editable_midi_timeline(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        session,folder,_=fixture_session(app.state.store)
        middle=take(app.state.store,session,1,2)
        before=(folder/'original.mid').read_bytes()
        assert client.delete(f'/api/sessions/{session}').status_code==422
        assert client.request('DELETE',f"/api/recordings/{middle['id']}/audio",json={'confirmation':'delete','revision':99}).status_code==409
        response=client.request('DELETE',f"/api/recordings/{middle['id']}/audio",json={'confirmation':'delete','revision':1})
        assert response.status_code==200,response.text
        assert client.get(f"/api/segments/{middle['id']}/microphone").status_code==400
        assert client.get(f"/api/segments/{middle['id']}/midi").status_code==200
        assert client.get(f'/api/sessions/{session}/midi').content==before
        assert client.get(f"/api/segments/{middle['id']}/audio-status").json()['microphone'] is False
        assert client.get(f'/api/sessions/{session}/recording').json()['timeline_locked'] is False
        timeline=client.get(f'/api/sessions/{session}/segments').json()
        assert not timeline[0]['recording_deleted']
        assert client.put(f'/api/sessions/{session}/segments',json={'segments':timeline,'expected_revision':1}).status_code==200
        # A MIDI rebuild stays available and cannot restore erased acoustic samples.
        for _ in range(200):
            if not any(j['status'] in ('queued','running') for j in client.get('/api/jobs').json()):break
            time.sleep(.01)
        assert client.post(f'/api/sessions/{session}/organise?force=true').status_code==200
        for _ in range(200):
            if not any(j['status'] in ('queued','running') for j in client.get('/api/jobs').json()):break
            time.sleep(.01)
        assert client.get(f'/api/sessions/{session}/midi').content==before
        assert client.request('DELETE',f'/api/sessions/{session}',json={'confirmation':'delete'}).status_code==200


def test_export_is_temporary_and_capture_blocks_deletion(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        session,_,_=fixture_session(app.state.store)
        row=take(app.state.store,session)
        response=client.get(f"/api/segments/{row['id']}/microphone")
        assert response.status_code==200 and response.content[:4]==b'fLaC'
        assert not list((tmp_path/'exports').glob('microphone-clip-*.flac'))
        assert client.get(f'/api/sessions/{session}/bundle').status_code==200
        assert not list((tmp_path/'exports').glob('*.zip'))
        app.state.recorder.start()
        assert client.request('DELETE',f'/api/sessions/{session}',json={'confirmation':'delete'}).status_code==409
        app.state.recorder.stop()


def test_ineligible_keep_requires_confirming_completeness(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        session,_,_=fixture_session(app.state.store)
        row=take(app.state.store,session,complete=False)
        assert client.put(f"/api/recordings/{row['id']}",json={'choice':'keep'}).status_code==400
        assert client.put(f"/api/recordings/{row['id']}",json={'choice':'keep','complete':True}).status_code==200
        assert client.get('/api/recordings').json()['takes'][0]['action']=='keep'


def test_failed_session_database_delete_restores_files_and_rows(tmp_path):
    store=Store(tmp_path);session,folder,samples=fixture_session(store);row=take(store,session)
    store.db.execute("CREATE TRIGGER prevent_delete BEFORE DELETE ON sessions BEGIN SELECT RAISE(ABORT,'test rollback'); END")
    store.db.commit()
    with pytest.raises(Exception,match='test rollback'):delete_session(store,session)
    assert folder.exists()
    np.testing.assert_array_equal(sf.read(folder/'microphone.flac',dtype='int16')[0],samples)
    assert store.query('SELECT id FROM segments WHERE id=?',(row['id'],))
    assert not list((store.root/'sessions').glob('.deleting-*'))


def test_interrupted_deletion_resumes_only_explicitly_requested_interval(tmp_path,monkeypatch):
    store=Store(tmp_path);session,folder,samples=fixture_session(store);row=take(store,session,1,2)
    import chopin.microphone as audio
    original=audio.compact_audio
    def failure(*args):raise OSError('disk unavailable')
    monkeypatch.setattr(audio,'compact_audio',failure)
    with pytest.raises(OSError):delete_take(store,row)
    assert store.query('SELECT status FROM recording_deletions')[0]['status']=='pending'
    np.testing.assert_array_equal(sf.read(folder/'microphone.flac',dtype='int16')[0],samples)
    monkeypatch.setattr(audio,'compact_audio',original)
    recover_deletions(store)
    assert store.query('SELECT status FROM recording_deletions')[0]['status']=='done'
    decoded=sf.read(folder/metadata(folder)['filename'],dtype='int16')[0]
    np.testing.assert_array_equal(decoded,np.concatenate([samples[:1000],samples[2000:]]))


def test_audio_manifest_failure_leaves_original_copy(tmp_path,monkeypatch):
    store=Store(tmp_path);_,folder,samples=fixture_session(store)
    def failure(*args):raise OSError('manifest full')
    monkeypatch.setattr('chopin.microphone.write_metadata',failure)
    with pytest.raises(OSError):compact_audio(folder,1,2,'delete')
    assert metadata(folder)['filename']=='microphone.flac'
    np.testing.assert_array_equal(sf.read(folder/'microphone.flac',dtype='int16')[0],samples)
    assert len(list(folder.glob('*.flac')))==1


def test_piece_library_and_comparison_retain_all_midi_regardless_of_audio_flags(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        session,_,_=fixture_session(app.state.store)
        rows=[take(app.state.store,session) for _ in range(3)]
        partial=take(app.state.store,session,complete=False)
        for row,value in zip(rows,[90,95,99]):score(app.state.store,row,value)
        kept=client.get('/api/pieces/n9-1/sessions').json()
        assert {r['id'] for s in kept for r in s['segments']}=={r['id'] for r in rows+[partial]}
        assert len(client.get('/api/performances').json())==4
        all_rows=client.get('/api/pieces/n9-1/sessions?include_flagged=true').json()
        assert len(all_rows[0]['segments'])==4
        assert next(r for r in all_rows[0]['segments'] if r['id']==partial['id'])['audio_retention_action']=='remove'


def test_midi_only_takes_are_never_flagged_or_used_in_audio_shortlist(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        store=app.state.store
        audio_session,_,_=fixture_session(store)
        audio_take=take(store,audio_session,complete=True);score(store,audio_take,80)
        midi_session,folder,_=fixture_session(store)
        (folder/'microphone.flac').unlink()
        midi_takes=[take(store,midi_session,complete=(i%2==0)) for i in range(5)]
        for row in midi_takes:score(store,row,100)
        assert {r['id'] for r in client.get('/api/recordings').json()['takes']}=={audio_take['id']}
        assert client.get('/api/recordings').json()['takes'][0]['action']=='keep'
        assert len([s for s in client.get('/api/pieces/n9-1/sessions').json() if s['id']==midi_session][0]['segments'])==5
        assert len(client.get('/api/performances').json())==6
        row=midi_takes[0]
        assert client.put(f"/api/recordings/{row['id']}",json={'choice':'remove'}).status_code==400
        assert client.request('DELETE',f"/api/recordings/{row['id']}/audio",json={'confirmation':'delete','revision':1}).status_code==400
        assert (folder/'original.mid').exists()


def test_generated_audio_is_flagged_and_deleted_without_touching_midi(tmp_path):
    store=Store(tmp_path);session,folder,_=fixture_session(store)
    (folder/'microphone.flac').unlink()
    row=take(store,session,complete=False)
    rendered=store.root/'audio'/'take.wav';rendered.write_bytes(b'audio')
    store.execute('INSERT INTO jobs(id,kind,status,created,result) VALUES(?,?,?,?,?)',('render','render','done','now',json.dumps({'filename':rendered.name,'session_id':session,'segment_id':row['id']})))
    before=(folder/'original.mid').read_bytes()
    assert catalogue(store)[0]['action']=='remove'
    delete_take(store,row)
    assert not rendered.exists()
    assert (folder/'original.mid').read_bytes()==before
    assert store.query('SELECT id FROM segments WHERE id=?',(row['id'],))
    assert not catalogue(store)


def test_pending_old_cleanup_migrates_to_audio_only(tmp_path):
    import sqlite3
    from pathlib import Path
    from chopin import store as module
    db=sqlite3.connect(tmp_path/'studio.sqlite3')
    for name in ('001_initial.sql','002_practice.sql','003_recording_retention.sql'):
        db.executescript((Path(module.__file__).parent/'migrations'/name).read_text())
    db.execute("INSERT INTO sessions(id,name,started,status) VALUES('session','test','now','saved')")
    db.execute("INSERT INTO recording_deletions VALUES('pending','session','take',1,2,'pending','now')")
    db.execute("INSERT INTO recording_deletions VALUES('old','session','old-take',1,2,'done','now')")
    db.commit();db.close()
    store=Store(tmp_path)
    assert store.query("SELECT scope FROM recording_deletions WHERE id='pending'")[0]['scope']=='audio'
    assert store.query("SELECT scope FROM recording_deletions WHERE id='old'")[0]['scope']=='recording'
