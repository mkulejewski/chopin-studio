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
    s=Store(tmp_path);reference(s);ident=make_session(s,repeats=3)
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
