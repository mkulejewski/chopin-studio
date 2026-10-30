import io
import json
import time
import uuid
import zipfile
from pathlib import Path

import mido
import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.store import Store
from chopin.organisation import Recognizer,organise,performance_notes
from chopin.extraction import segment_midi
from chopin.symbolic import unpack_xml,import_reference

PITCHES=[60,64,67,62,69,65,71,63,68,66,73,70,72,75,74,77,76,79,78,81]

def reference(store,piece='n9-1',pitches=PITCHES,quality='verified'):
    notes=[{'pitch':p,'onset':i,'duration':.5,'measure':i//4+1,'voice':'1','staff':1,'grace':False} for i,p in enumerate(pitches)]
    ident=uuid.uuid4().hex
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',(ident,piece,ident+'.musicxml','Synthetic test fixture','Original test data','Synthetic',quality,json.dumps(notes),'2026-10-30'))
    return ident,notes


def make_session(store,pitches=PITCHES,repeats=1,gap=10):
    ident=uuid.uuid4().hex;folder=store.root/'sessions'/ident;folder.mkdir()
    events=[]
    for repeat in range(repeats):
        base=repeat*(len(pitches)*.3+gap)
        for i,pitch in enumerate(pitches):
            events += [{'t':base+i*.3,'message':mido.Message('note_on',note=pitch,velocity=80).dict()},
                       {'t':base+i*.3+.2,'message':mido.Message('note_off',note=pitch).dict()}]
    duration=events[-1]['t']+.1 if events else 1
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute('INSERT INTO sessions(id,name,started,status,duration,events) VALUES(?,?,?,?,?,?)',(ident,'synthetic','2026-10-30','saved',duration,len(events)))
    return ident


def wait_job(client,ident):
    for _ in range(300):
        job=next(j for j in client.get('/api/jobs').json() if j['id']==ident)
        if job['status'] in ('done','failed','cancelled'):return job
        time.sleep(.02)
    raise AssertionError('Job did not finish')


def test_personal_repertoire_migrates_once_and_preserves_edits(tmp_path):
    s=Store(tmp_path)
    assert len(s.query('SELECT id FROM pieces'))==44
    n=s.query("SELECT * FROM pieces WHERE id='n9-1'")[0]
    assert n['mastery']==3 and n['liking']==2
    assert n['catalogue_path']=='Chopin/Nocturnes/Op 9 No 1'
    assert s.query("SELECT preferred_edition FROM pieces WHERE id='p28-15'")[0]['preferred_edition']=='Schott Music'
    assert s.query("SELECT forgotten FROM pieces WHERE id='w70-1'")[0]['forgotten']==1
    assert s.query("SELECT liking FROM pieces WHERE id='p53'")[0]['liking']==3
    s.execute("UPDATE pieces SET mastery=2,notes='my edit' WHERE id='n9-1'");s.db.close()
    s=Store(tmp_path)
    assert s.query("SELECT mastery FROM pieces WHERE id='n9-1'")[0]['mastery']==2


def test_subsequence_recognition_tempo_invariant_wrong_notes_and_unknown(tmp_path):
    s=Store(tmp_path);_,notes=reference(s);reference(s,'w64-2',[50,54,59,55,51,58,53,57,52,56]*2)
    r=Recognizer(s.query('SELECT * FROM symbolic_scores'))
    excerpt=[{**n,'onset':(i*.7)**1.1} for i,n in enumerate(notes[4:18])]
    excerpt[5]={**excerpt[5],'pitch':64}
    match=r.match(excerpt)
    assert match['piece_id']=='n9-1'
    assert match['first_measure']>=1
    assert r.match([{'pitch':40+i%2,'onset':i*.2} for i in range(30)]).get('piece_id') is None
    assert r.match(excerpt[:3])['label']=='Unknown piece'


def test_multi_attempt_segmentation_and_repeat_grouping(tmp_path):
    s=Store(tmp_path);reference(s);ident=make_session(s,repeats=3,gap=25)
    segments=organise(s,ident)
    assert len(segments)==3
    assert all(r['piece_id']=='n9-1' for r in segments)
    assert len({r['group_id'] for r in segments})==1
    assert segments[0]['group_id'] is not None
    assert segments[1]['start']>segments[0]['end']


def test_slow_expressive_pause_not_force_split(tmp_path):
    s=Store(tmp_path);reference(s);ident=make_session(s)
    path=s.root/'sessions'/ident/'events.jsonl';events=[json.loads(line) for line in path.read_text().splitlines()]
    for i,e in enumerate(events):
        if i>=20:e['t']+=2.5
    path.write_text(''.join(json.dumps(e)+'\n' for e in events))
    s.execute('UPDATE sessions SET duration=duration+2.5 WHERE id=?',(ident,))
    assert len(organise(s,ident))==1


def test_cut_initialises_active_notes_and_pedal_and_preserves_source(tmp_path):
    s=Store(tmp_path);ident=make_session(s,pitches=[60,62])
    path=s.root/'sessions'/ident/'events.jsonl'
    events=[{'t':0,'message':mido.Message('control_change',control=64,value=43).dict()},
            {'t':.1,'message':mido.Message('note_on',note=60,velocity=83).dict()},
            {'t':2,'message':mido.Message('note_off',note=60).dict()}]
    path.write_text(''.join(json.dumps(e)+'\n' for e in events));original=path.read_bytes()
    result=segment_midi(s,{'id':uuid.uuid4().hex,'session_id':ident,'start':1,'end':1.5})
    messages=list(mido.MidiFile(result));assert next(m for m in messages if m.type=='control_change').value==43
    assert next(m for m in messages if m.type=='note_on').velocity==83
    assert any(m.type=='note_off' and m.note==60 for m in messages)
    assert path.read_bytes()==original


def test_mxl_path_traversal_entity_and_zip_bomb_rejected():
    with pytest.raises(Exception):unpack_xml(b'<!DOCTYPE score-partwise [<!ENTITY secret SYSTEM "file:///etc/passwd">]><score-partwise>&secret;</score-partwise>','.xml')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:
        archive.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="../escape.xml"/></rootfiles></container>')
        archive.writestr('../escape.xml','<score-partwise/>')
    with pytest.raises(ValueError,match='Unsafe'):unpack_xml(buffer.getvalue(),'.mxl')


def test_timeline_edits_undo_analysis_and_local_report(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        store=app.state.store;reference(store);ident=make_session(store)
        original=(store.root/'sessions'/ident/'events.jsonl').read_bytes()
        job=client.post(f'/api/sessions/{ident}/organise').json()['job_id']
        assert wait_job(client,job)['status']=='done'
        segments=client.get(f'/api/sessions/{ident}/segments').json();assert segments
        row=segments[0];boundary=(row['start']+row['end'])/2
        edited=[{**row,'end':boundary},{**row,'id':uuid.uuid4().hex,'start':boundary}]
        result=client.put(f'/api/sessions/{ident}/segments',json={'segments':edited,'expected_revision':1})
        assert result.status_code==200 and len(result.json())==2
        assert client.put(f'/api/sessions/{ident}/segments',json={'segments':edited,'expected_revision':1}).status_code==409
        restored=client.post(f'/api/sessions/{ident}/segments/undo');assert len(restored.json())==1
        segment_id=restored.json()[0]['id']
        assert client.get(f'/api/segments/{segment_id}/midi').content.startswith(b'MThd')
        job=client.post(f'/api/segments/{segment_id}/analyse').json()['job_id'];outcome=wait_job(client,job)
        assert outcome['status']=='done',outcome
        result=json.loads(outcome['result']);assert result['accuracy'] is None
        assert result['alignment']
        job=client.post(f'/api/sessions/{ident}/teacher',json={'provider':'local'}).json()['job_id']
        assert wait_job(client,job)['status']=='done'
        report=client.get(f'/api/sessions/{ident}/reports').json()[0]
        assert report['provider']=='local' and segment_id in report['text']
        assert (store.root/'sessions'/ident/'events.jsonl').read_bytes()==original


def test_cloud_requires_key_without_uploading(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        ident=make_session(app.state.store)
        job=client.post(f'/api/sessions/{ident}/teacher',json={'provider':'openai'}).json()['job_id']
        assert 'not configured' in wait_job(client,job)['error']


def test_optional_real_fluidsynth_render_and_cancel(tmp_path):
    import shutil
    from chopin.jobs import Jobs
    font=Path('/usr/share/sounds/sf2/TimGM6mb.sf2')
    if not shutil.which('fluidsynth') or not font.exists():pytest.skip('Optional FluidSynth/soundfont not installed')
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        store=app.state.store;ident=make_session(store,pitches=[60,64,67])
        row={'id':uuid.uuid4().hex,'session_id':ident,'start':0,'end':.8,'label':'Synthetic','kind':'unknown'}
        store.execute('INSERT INTO segments(id,session_id,start,end,label,kind) VALUES(?,?,?,?,?,?)',tuple(row.values()))
        response=client.post(f'/api/segments/{row["id"]}/render',json={'soundfont':str(font),'format':'flac'})
        job=response.json()['job_id'];outcome=wait_job(client,job)
        assert outcome['status']=='done',outcome
        assert client.get(f'/api/audio/{job}').content.startswith(b'fLaC')
        job=client.post(f'/api/segments/{row["id"]}/render',json={'soundfont':str(font)}).json()['job_id']
        client.post(f'/api/jobs/{job}/cancel')
        assert wait_job(client,job)['status']=='cancelled'


def test_live_piece_recognition_independent_of_recording(tmp_path):
    from chopin.recorder import Recorder
    from chopin.live import LiveFollowing
    store=Store(tmp_path);reference(store,pitches=PITCHES*8)
    recorder=Recorder(store);following=LiveFollowing(store,recorder)
    store.set_setting('live_enabled',True)
    try:
        for batch in range(4):
            for pitch in PITCHES:
                recorder.receive(mido.Message('note_on',note=pitch,velocity=80))
                time.sleep(.06)
            time.sleep(1.15)
        assert following.state.get('piece_id')=='n9-1',following.state
        assert following.state['enabled']
        assert recorder.active is None
        assert not following.state.get('page_request')  # no page map / auto-turn disabled
        store.set_setting('live_enabled',False);time.sleep(.3)
        assert following.state['enabled'] is False
    finally:following.close()


def test_reference_parser_uses_real_musicxml_and_preserves_measures(tmp_path):
    store=Store(tmp_path)
    notes=''.join(f'<note><pitch><step>{step}</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>' for step in ['C','D','E','F'])
    xml=f'<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>{notes}</measure></part></score-partwise>'.encode()
    ref=import_reference(store,'n9-1',xml,'.musicxml')
    row=store.query('SELECT * FROM symbolic_scores WHERE id=?',(ref,))[0]
    data=json.loads(row['notes'])
    assert [n['pitch'] for n in data]==[60,62,64,65]
    assert [n['onset'] for n in data]==[0,1,2,3]
    assert all(n['measure']==1 for n in data)
    assert row['quality']=='provisional'


def test_gesture_and_live_settings_do_not_reconnect_piano(tmp_path,monkeypatch):
    import threading
    class FakeInput:
        def __init__(self,recorder):self.reconnect=threading.Event();self.devices=[];self.connected=None;self.error=None
        def close(self):pass
    import chopin.app
    monkeypatch.setattr(chopin.app,'MidiInput',FakeInput)
    # The constructor is tracked to observe the actual reconnection request.
    instances=[]
    def factory(recorder):
        value=FakeInput(recorder);instances.append(value);return value
    monkeypatch.setattr(chopin.app,'MidiInput',factory)
    with TestClient(chopin.app.create_app(tmp_path,hardware=True)) as client:
        settings=client.get('/api/settings').json()
        assert client.put('/api/settings',json={**settings,'live_enabled':True,'swipe':False}).status_code==200
        assert not instances[0].reconnect.is_set()
        assert client.put('/api/settings',json={**settings,'preferred_device':'CASIO'}).status_code==200
        assert instances[0].reconnect.is_set()


def test_private_ai_config_never_echoes_key_or_calls_cloud(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        assert not client.get('/api/ai/config').json()['configured']
        secret='sk-synthetic-test-key-not-a-real-secret'
        response=client.put('/api/ai/config',json={'api_key':secret})
        assert response.status_code==200
        assert secret not in response.text and secret not in client.get('/api/ai/config').text
        assert (tmp_path/'openai-key').stat().st_mode & 0o777==0o600
        assert client.put('/api/ai/config',json={'api_key':'too-short'}).status_code==422


def test_bundle_and_report_revisions_retain_originals(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        ident=make_session(app.state.store)
        from chopin.midi_files import export_midi
        folder=tmp_path/'sessions'/ident;export_midi(folder/'events.jsonl',folder/'original.mid')
        original=(folder/'original.mid').read_bytes()
        job=client.post(f'/api/sessions/{ident}/teacher',json={'provider':'local'}).json()['job_id']
        assert wait_job(client,job)['status']=='done'
        report=client.get(f'/api/sessions/{ident}/reports').json()[0]
        assert client.post(f'/api/reports/{report["id"]}/revision',json={'text':'My own interpretation'}).status_code==200
        rows=client.get(f'/api/sessions/{ident}/reports').json();assert len(rows)==2
        bundle=client.get(f'/api/sessions/{ident}/bundle')
        with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
            assert archive.read('original.mid')==original
            assert len([name for name in archive.namelist() if name.startswith('reports/')])==2
            assert not any('key' in name for name in archive.namelist())


def test_openai_adapter_schema_and_evidence_validation_without_network(tmp_path,monkeypatch):
    import sys,types
    from chopin.teacher import create_report
    store=Store(tmp_path);ident=make_session(store);reference(store);segments=organise(store,ident)
    calls=[]
    class Responses:
        def create(self,**kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(output_text=json.dumps({'summary':'A cautious interpretation','findings':[{'interpretation':'Review this candidate activity','evidence_ids':[segments[0]['id']]}],'practice_priorities':['Check against the printed edition'],'limitations':['Synthetic contract test, not a real cloud response']}))
    monkeypatch.setenv('OPENAI_API_KEY','sk-synthetic-only')
    monkeypatch.setitem(sys.modules,'openai',types.SimpleNamespace(OpenAI=lambda **kwargs:types.SimpleNamespace(responses=Responses())))
    result=create_report(store,ident,'openai','Why this passage?','test-model')
    assert result['provider']=='openai' and segments[0]['id'] in result['text']
    assert calls[0]['store'] is False and calls[0]['text']['format']['type']=='json_schema'
    assert 'sk-synthetic-only' not in calls[0]['input']
    class BadResponses:
        def create(self,**kwargs):
            return types.SimpleNamespace(output_text=json.dumps({'summary':'Bad evidence','findings':[{'interpretation':'Invented','evidence_ids':['does-not-exist']}],'practice_priorities':[],'limitations':[]}))
    monkeypatch.setitem(sys.modules,'openai',types.SimpleNamespace(OpenAI=lambda **kwargs:types.SimpleNamespace(responses=BadResponses())))
    with pytest.raises(ValueError,match='unknown evidence'):create_report(store,ident,'openai','Explain','test-model')
    assert len(store.query('SELECT * FROM reports'))==1


def test_schema_one_upgrade_preserves_history_and_originals(tmp_path):
    import sqlite3
    from chopin import store as module
    db=sqlite3.connect(tmp_path/'studio.sqlite3')
    db.executescript((Path(module.__file__).parent/'migrations/001_initial.sql').read_text())
    db.execute("INSERT INTO sessions(id,name,started,status) VALUES('kept','Original history','2026-01-01','imported')");db.commit();db.close()
    folder=tmp_path/'sessions'/'kept';folder.mkdir(parents=True);(folder/'original.mid').write_bytes(b'immutable original fixture')
    upgraded=Store(tmp_path)
    assert upgraded.query('PRAGMA user_version')[0]['user_version']==2
    assert upgraded.query("SELECT name FROM sessions WHERE id='kept'")[0]['name']=='Original history'
    assert (folder/'original.mid').read_bytes()==b'immutable original fixture'


def test_practice_restarts_combined_with_configurable_separation(tmp_path):
    s=Store(tmp_path);reference(s);ident=make_session(s,repeats=3,gap=10)
    assert len(organise(s,ident))==1
    s.set_setting('separation_cooldown',5)
    assert len(organise(s,ident,force=True))==3


def test_automatic_scoring_notes_production_flag_and_preanalysis(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        s=app.state.store;reference(s);ident=make_session(s)
        s.execute("UPDATE pieces SET mastery=1,notes='My fingering and interpretation' WHERE id='n9-1'")
        job=client.post(f'/api/sessions/{ident}/organise').json()['job_id']
        assert wait_job(client,job)['status']=='done'
        rows=client.get(f'/api/sessions/{ident}/analyses').json();assert len(rows)==1
        assessment=rows[0]['result']['assessment']
        assert assessment['precision_score']==100 and assessment['audio_candidate']
        assert assessment['piece_level']=='concert'
        assert (s.root/'reports'/(rows[0]['id']+'.json')).exists()
        piece=client.get('/api/pieces/n9-1/assessment').json()
        assert piece['personal_level']==1 and piece['personal_notes']=='My fingering and interpretation'
        assert piece['revision_suggestion'] and piece['latest_performance']['session_id']==ident
        payload=client.get(f'/api/sessions/{ident}/preanalysis').json()
        assert payload['schema_version']=='practice-preanalysis-v1'
        assert payload['piece_assessments']['n9-1']['revision_suggestion']
        progress=next(r for r in client.get('/api/progress').json() if r['id']=='n9-1')
        assert progress['machine']['automatic_level']['assessment']['piece_level']=='concert'
        # A later partial performance stays visible without replacing the whole-piece level.
        partial=make_session(s,pitches=PITCHES[:12])
        s.execute('UPDATE sessions SET started=? WHERE id=?',('2026-10-31',partial))
        job=client.post(f'/api/sessions/{partial}/organise').json()['job_id']
        assert wait_job(client,job)['status']=='done'
        piece=client.get('/api/pieces/n9-1/assessment').json()
        assert piece['latest_performance']['session_id']==partial
        assert piece['automatic_level']['session_id']==ident
        assert not piece['latest_performance']['assessment']['audio_candidate']


@pytest.mark.parametrize('quality,error', [('provisional',None),('verified','Capture failure')])
def test_untrusted_reference_or_capture_cannot_flag_for_production(tmp_path,quality,error):
    from chopin.organisation import analyse_segment
    s=Store(tmp_path);reference(s,quality=quality);ident=make_session(s)
    s.execute('UPDATE sessions SET error=? WHERE id=?',(error,ident))
    result=analyse_segment(s,organise(s,ident)[0])['assessment']
    assert not result['audio_candidate'] and result['piece_level'] is None


@pytest.mark.parametrize('pitches', [PITCHES[:9]+PITCHES[10:],PITCHES[:9]+[44]+PITCHES[9:],PITCHES[:9]+[44]+PITCHES[10:]])
def test_pitch_score_penalises_missing_extra_and_wrong_notes(tmp_path,pitches):
    from chopin.organisation import analyse_segment
    s=Store(tmp_path);reference(s);ident=make_session(s,pitches=pitches)
    assessment=analyse_segment(s,organise(s,ident)[0])['assessment']
    assert assessment['precision_score']<100
    assert not assessment['audio_candidate']


def test_live_requests_survive_polling_and_reset_after_idle(tmp_path,monkeypatch):
    from chopin.recorder import Recorder
    from chopin.live import LiveFollowing
    s=Store(tmp_path);reference(s);recorder=Recorder(s);live=LiveFollowing(s,recorder);live.close()
    s.set_setting('live_enabled',True);s.set_setting('live_auto_turn',True)
    s.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',1,2))
    now=[100.0];monkeypatch.setattr('chopin.live.time.monotonic',lambda:now[0])
    try:
        for batch in range(4):
            now[0]+=1
            for i,pitch in enumerate(PITCHES[:12]):
                recorder.live_queue.put({'t':now[0]+i*.01,'message':mido.Message('note_on',note=pitch,velocity=80).dict()})
            # Isolate lifecycle/polling behavior from the recognition algorithm.
            monkeypatch.setattr(Recognizer,'match',lambda self,notes: {'piece_id':'n9-1','last_measure':3,'confidence':.99,'quality':'verified','label':'Identified'})
            live.tick()
        request=live.state['page_request'].copy()
        now[0]+=1;live.tick()
        assert live.state['page_request']==request
        # A new recognition update must retain the outstanding page request too.
        recorder.live_queue.put({'t':now[0],'message':mido.Message('note_on',note=60,velocity=80).dict()})
        live.tick();assert live.state['page_request']==request
        now[0]+=15;live.tick()
        assert not live.state.get('page_request') and live.last_page is None
        s.set_setting('live_enabled',False);live.tick()
        assert not live.state['enabled'] and not live.window
    finally:s.db.close()


def test_live_provisional_position_visible_without_auto_turn(tmp_path,monkeypatch):
    from chopin.recorder import Recorder
    from chopin.live import LiveFollowing
    s=Store(tmp_path);reference(s,quality='provisional');r=Recorder(s);live=LiveFollowing(s,r);live.close()
    s.set_setting('live_enabled',True);s.set_setting('live_auto_turn',True)
    now=[100.0];monkeypatch.setattr('chopin.live.time.monotonic',lambda:now[0])
    monkeypatch.setattr(Recognizer,'match',lambda self,notes: {'piece_id':'n9-1','last_measure':3,'confidence':.84,'quality':'provisional','label':'Probable'})
    for _ in range(3):
        now[0]+=1;r.live_queue.put({'t':now[0],'message':mido.Message('note_on',note=60,velocity=80).dict()});live.tick()
    assert live.state['stable'] and live.state['measure']==3 and not live.state.get('page_request')


def test_ap470_wav_import_playback_and_recording_guard(tmp_path,monkeypatch):
    import wave
    from chopin import hardware_audio
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        s=app.state.store;ident=make_session(s);row=organise(s,ident)[0]
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as output:
            output.setnchannels(2);output.setsampwidth(2);output.setframerate(44100);output.writeframes(b'\x00'*400)
        result=client.post(f'/api/segments/{row["id"]}/audio',files={'file':('TAKE01.WAV',buffer.getvalue(),'audio/wav')})
        assert result.status_code==200
        job=next(j for j in client.get('/api/jobs').json() if j['kind']=='render')
        assert client.get('/api/audio/'+job['id']).content==buffer.getvalue()
        assert client.post(f'/api/segments/{row["id"]}/audio',files={'file':('bad.wav',b'bad')}).status_code==400
        calls=[]
        def fake_play(store,segment,port,device,cancel,job):
            calls.append((port,device,app.state.recorder.hardware_playback))
            with pytest.raises(ValueError):app.state.recorder.start()
            return {'filename':None,'engine':'AP-470 physical piano','session_id':ident,'format':'playback'}
        monkeypatch.setattr(hardware_audio,'play',fake_play)
        job=client.post(f'/api/segments/{row["id"]}/ap470',json={'port':'Synthetic AP-470'}).json()['job_id']
        assert wait_job(client,job)['status']=='done'
        assert calls==[('Synthetic AP-470','',True)] and not app.state.recorder.hardware_playback
        assert client.get('/api/audio/'+job).status_code==404
        app.state.recorder.start()
        assert client.post(f'/api/segments/{row["id"]}/ap470',json={'port':'Synthetic AP-470'}).status_code==400
        app.state.recorder.stop()


def test_hardware_playback_releases_controllers_after_cancellation(tmp_path,monkeypatch):
    import threading
    from chopin.hardware_audio import play
    s=Store(tmp_path);ident=make_session(s);row=organise(s,ident)[0];messages=[]
    class Port:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def send(self,message):messages.append(message)
    monkeypatch.setattr(mido,'open_output',lambda name:Port())
    cancel=threading.Event();cancel.set()
    with pytest.raises(InterruptedError):play(s,row,'fake','',cancel,uuid.uuid4().hex)
    assert any(m.type=='control_change' and m.control==64 and m.value==0 for m in messages)
    assert any(m.type=='control_change' and m.control==120 for m in messages)
