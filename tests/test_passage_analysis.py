import json
from collections import Counter
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from chopin.app import create_app
from chopin.organisation import performance_notes, Recognizer, passage_restarts, analyse_segment, organise
from chopin.passages import passage_analysis, compare_passages
from chopin.progress import piece_progress
from chopin.store import Store
from test_practice import reference, make_session


def event(t, kind, **kw):
    return {'t':t,'message':{'type':kind,'channel':kw.pop('channel',0),**kw}}


def test_cc88_order_channels_one_shot_release_and_compatibility():
    events=[event(0,'control_change',control=88,value=23),
            event(.001,'note_on',note=60,velocity=70),
            event(.002,'note_on',note=61,velocity=71),
            event(.3,'control_change',control=88,value=17),
            event(.301,'note_off',note=60,velocity=42),
            event(.4,'control_change',control=88,value=18),
            event(.401,'note_on',note=61,velocity=0),
            event(.5,'control_change',control=88,value=55,channel=1),
            event(.501,'note_on',note=62,velocity=90,channel=0),
            event(.502,'note_on',note=63,velocity=91,channel=1)]
    original=json.dumps(events); diagnostics=Counter()
    notes=performance_notes(events,diagnostics)
    assert notes[0]['velocity']==70 and notes[0]['velocity_14']==70*128+23
    assert notes[0]['release_velocity']==42 and notes[0]['release_velocity_14']==42*128+17
    assert notes[1]['velocity_14'] is None
    assert notes[1]['release_source']=='note_on_zero' and notes[1]['release_velocity'] is None
    assert notes[2]['velocity_14'] is None and notes[3]['velocity_14']==91*128+55
    assert diagnostics['paired_prefixes']==4 and json.dumps(events)==original


@pytest.mark.parametrize('middle', [event(.01,'control_change',control=64,value=127), {'t':.01,'kind':'capture_loss'}])
def test_intervening_messages_and_capture_loss_withhold_prefix(middle):
    d=Counter(); notes=performance_notes([event(0,'control_change',control=88,value=19),middle,event(.02,'note_on',note=60,velocity=80)],d)
    assert notes[0]['velocity_14'] is None and d['interrupted_prefixes']==1


def test_realtime_allowed_stale_or_reversed_order_not_paired():
    from chopin.velocity import velocity_events
    realtime={'t':.01,'message':{'type':'clock'}}
    notes=performance_notes([event(0,'control_change',control=88,value=0),realtime,event(.02,'note_on',note=60,velocity=80)])
    assert notes[0]['velocity_14']==80*128
    for t in (-.01,2):
        d=Counter(); result=list(velocity_events([event(0,'control_change',control=88,value=19),event(t,'note_on',note=60,velocity=80)],d))
        assert result[-1]['velocity_14'] is None
        assert d['out_of_order_events']+d['stale_prefixes']==1


def score_groups():
    groups=[]
    for i in range(10):
        groups.append(dict(beat=i,measure=i//4+1,time=i*.5,expected=[48,60,72],observed=[48,60,72],
          score_notes=[dict(pitch=p,duration=1,part=0,staff=staff,voice=voice,dynamic='p') for p,staff,voice in [(48,2,'2'),(60,1,'2'),(72,1,'1')]],
          played_notes=[dict(pitch=p,onset=i*.5,duration=.4,velocity=v,channel=0,released=True,release_velocity=30+i,release_velocity_14=None) for p,v in [(48,50),(60,55),(72,80)]]))
    return groups


def test_synchronized_metrics_pedal_inheritance_duration_roles_and_gates():
    target={'roles':{'0:2:2':'bass','0:1:2':'inner','0:1:1':'melody'},'melody_min_gap':20,'release_calibrated':True}
    analysis=dict(reference_id='r',reference_quality='verified',match={'confidence':.95},assessment={'capture_ok':True})
    events=[event(-1,'control_change',control=64,value=81),event(2,'control_change',control=64,value=0)]
    result=passage_analysis(score_groups(),events,{'start':0,'end':5},analysis,target)
    assert result['points'][0]['bpm']==120
    assert result['points'][0]['duration_ratio']==.8
    assert result['points'][0]['pedal']==81 and result['points'][4]['pedal']==0
    assert result['points'][0]['dynamics']==['p']
    assert all(v['status']=='meets_target' for v in result['points'][0]['voicing'])
    assert result['release']['status']=='calibrated'
    analysis['reference_quality']='provisional'
    result=passage_analysis(score_groups(),events,{},analysis,target)
    assert all(v['status']=='descriptive' for v in result['points'][0]['voicing'])
    groups=score_groups(); groups[2]['time']=None; groups[1]['played_notes'][0]['released']=False
    result=passage_analysis(groups,[],{},analysis,target)
    assert result['points'][0]['pedal'] is None
    assert result['points'][2]['bpm'] is None
    assert result['points'][1]['notes'][0]['duration_ratio'] is None


def test_take_comparison_uses_shared_reference_and_score_beats_not_elapsed_time():
    a=passage_analysis(score_groups(),[],{},dict(reference_id='r'))
    gs=score_groups()[4:]
    for g in gs:g['time']+=23
    b=passage_analysis(gs,[],{},dict(reference_id='r'))
    result=compare_passages({'passages':a},{'passages':b})
    assert len(result['points'])==6 and result['points'][0]['beat']==4
    assert result['points'][0]['left']['time']==2 and result['points'][0]['right']['time']==25
    assert result['points'][0]['delta']['velocity']==0
    b['reference_id']='other'
    assert compare_passages({'passages':a},{'passages':b})['status']=='unavailable'


def test_analysis_integration_and_progress_avoids_reanalysis_duplicates_and_stale_edits(tmp_path):
    s=Store(tmp_path); reference(s); sid=make_session(s); seg=organise(s,sid)[0]
    raw=(tmp_path/'sessions'/sid/'events.jsonl').read_bytes()
    result=analyse_segment(s,seg)
    assert (tmp_path/'sessions'/sid/'events.jsonl').read_bytes()==raw
    assert result['passages']['points'][0]['velocity']==80
    result['segment_snapshot']={k:seg[k] for k in ('piece_id','start','end','revision','complete','discarded')}
    for ident in ('a','b'):
        s.execute('INSERT INTO analyses VALUES(?,?,?,?,?,?)',(ident,sid,seg['id'],'test','2026-11-15',json.dumps(result)))
    progress=piece_progress(s,'n9-1')
    assert progress['measures'][0]['attempts']==1
    s.execute('UPDATE segments SET revision=revision+1 WHERE id=?',(seg['id'],))
    assert piece_progress(s,'n9-1')['measures']==[]
    s.db.close()


def test_objectives_time_revision_overlap_rebuild_and_recall(tmp_path):
    app=create_app(tmp_path,hardware=False);s=app.state.store
    reference(s); sid=make_session(s);seg=organise(s,sid)[0]
    with TestClient(app) as client:
        payload=dict(title='Keep melody above inner voice',category='voicing',first_measure=1,last_measure=2)
        response=client.post('/api/pieces/n9-1/objectives',json=payload)
        assert response.status_code==200
        ident=response.json()['id']
        for start,end in [(0,2),(1,3)]:
            assert client.post(f'/api/objectives/{ident}/time',json=dict(segment_id=seg['id'],start=start,end=end)).status_code==200
        assert piece_progress(s,'n9-1')['objectives'][0]['seconds']==3
        organise(s,sid,force=True)
        assert piece_progress(s,'n9-1')['objectives'][0]['seconds']==3
        assert client.put(f'/api/objectives/{ident}',json={**payload,'completed':True,'revision':1}).status_code==200
        assert client.put(f'/api/objectives/{ident}',json={**payload,'revision':1}).status_code==409
        assert client.post(f'/api/objectives/{ident}/time',json=dict(segment_id=seg['id'],start=0,end=99)).status_code in (404,422)
        assert client.put('/api/settings',json={'live_auto_open':True}).status_code==200
        assert client.get('/api/settings').json()['live_auto_open'] is True
        assert client.put('/api/pieces/n9-1/voicing',json={'roles':{'0:1:1':'melody'},'melody_min_gap':10}).status_code==200
        assert client.get('/api/pieces/n9-1/voicing').json()['melody_min_gap']==10
        target=json.dumps(dict(kind='hidden',start=1,end=2,hand='left'))
        for i,date in enumerate(['2026-11-01T12:00:00+00:00','2026-11-10T12:00:00+00:00']):
            s.execute('INSERT INTO learning_attempts VALUES(?,?,?,?,?,?,?,?)',(str(i),'n9-1',sid,'r','evaluated',date,target,json.dumps(dict(passed=True,capture_ok=True))))
        retention=piece_progress(s,'n9-1',datetime(2026,11,15,tzinfo=timezone.utc))['retention'][0]
        assert retention['passes']==2 and retention['longest_successful_gap_days']==9 and not retention['review_due']


def test_unique_short_attempt_repeated_theme_uncertainty_and_midpiece_restart():
    from test_recognition_boundaries import references
    ref=references()[0];r=Recognizer([ref])
    assert r.match(ref['notes'][30:36])['piece_id']==ref['piece_id']
    assert r.match(ref['notes'][30:35]).get('piece_id') is None
    repeated={**ref,'notes':ref['notes'][:30]+ref['notes'][10:22]+ref['notes'][30:]}
    repeated['notes']=[{**n,'onset':i} for i,n in enumerate(repeated['notes'])]
    match=Recognizer([repeated]).match(ref['notes'][10:18])
    assert match['piece_id']==ref['piece_id'] and match['location_ambiguous']
    sequence=ref['notes'][30:48]+ref['notes'][30:55]
    notes=[{**n,'onset':i*.5} for i,n in enumerate(sequence)]
    assert passage_restarts(notes,r,r.match(notes))==[9]
    assert passage_restarts(repeated['notes'],Recognizer([repeated]),Recognizer([repeated]).match(repeated['notes']))==[]


def test_measure_voicing_covers_arpeggios_below_target_and_constant_release():
    groups=score_groups()
    for i,g in enumerate(groups):
        pitch=[48,60,72][i%3]
        g['expected']=[pitch];g['observed']=[pitch]
        g['score_notes']=[n for n in g['score_notes'] if n['pitch']==pitch]
        g['played_notes']=[{**n,'velocity':70 if pitch==72 else 80,'release_velocity':64} for n in g['played_notes'] if n['pitch']==pitch]
    result=passage_analysis(groups,[],{'end':5},dict(reference_id='r',reference_quality='verified',match={'confidence':.95},assessment={'capture_ok':True}),
       dict(roles={'0:2:2':'bass','0:1:2':'inner','0:1:1':'melody'},melody_min_gap=10,release_calibrated=True))
    assert all(not p['voicing'] for p in result['points'])
    assert result['measures'][0]['voicing'][0]['status']=='below_target'
    assert result['release']['status']=='insufficient_variation'


def test_musicxml_printed_dynamics_retained_without_invented_velocity(tmp_path):
    from chopin.symbolic import parse_musicxml
    path=tmp_path/'dynamics.musicxml'
    path.write_text('''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Piano</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><direction-type><dynamics><p/></dynamics></direction-type></direction><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>''')
    notes=parse_musicxml(path)
    assert notes[0]['dynamic']=='p' and notes[0].get('dynamic_velocity') is None


def test_repeated_theme_with_wrong_note_keeps_alternative_locations():
    from test_recognition_boundaries import references
    ref=references()[0]
    repeated={**ref,'notes':ref['notes'][:30]+ref['notes'][10:22]+ref['notes'][30:]}
    repeated['notes']=[{**n,'onset':i} for i,n in enumerate(repeated['notes'])]
    query=[dict(n) for n in ref['notes'][10:22]]
    query[5]['pitch']=100
    match=Recognizer([repeated]).match(query)
    assert match['piece_id']==ref['piece_id'] and match['location_ambiguous']


def test_piece_time_unions_learning_and_practice_and_keeps_personal_mastery(tmp_path):
    from chopin.progress import piece_time
    s=Store(tmp_path);reference(s);sid=make_session(s);seg=organise(s,sid)[0]
    before=s.query("SELECT mastery,notes FROM pieces WHERE id='n9-1'")[0]
    s.execute('INSERT INTO learning_attempts VALUES(?,?,?,?,?,?,?,?)',('a','n9-1',sid,'r','evaluated','2026-11-15',json.dumps(dict(kind='visible',start=1,end=2)),json.dumps(dict(passed=True,capture_ok=True))))
    duration=s.query('SELECT duration FROM sessions WHERE id=?',(sid,))[0]['duration']
    assert piece_time(s,'n9-1')==duration
    assert piece_progress(s,'n9-1')['retention']==[]
    assert s.query("SELECT mastery,notes FROM pieces WHERE id='n9-1'")[0]==before
    s.db.close()


def test_clipped_midi_never_replays_stale_cc88_and_keeps_valid_boundary_prefix(tmp_path):
    from chopin.extraction import segment_midi
    from chopin.midi_files import midi_events
    s=Store(tmp_path);sid='clip';folder=tmp_path/'sessions'/sid;folder.mkdir()
    events=[event(0,'control_change',control=88,value=31),event(.01,'note_on',note=60,velocity=80),event(.2,'note_off',note=60,velocity=20),
            event(1,'note_on',note=61,velocity=90),event(1.2,'note_off',note=61,velocity=21),
            event(2,'control_change',control=88,value=12),event(2.01,'note_on',note=62,velocity=100),event(2.2,'note_off',note=62,velocity=22)]
    raw=''.join(json.dumps(e)+'\n' for e in events);(folder/'events.jsonl').write_text(raw)
    notes=performance_notes(midi_events(segment_midi(s,dict(id='clip',session_id=sid,start=1,end=2.3))))
    assert notes[0]['pitch']==61 and notes[0]['velocity_14'] is None
    assert notes[1]['pitch']==62 and notes[1]['velocity_14']==100*128+12
    # Prefix lies just outside the cut, but its target note is inside it.
    notes=performance_notes(midi_events(segment_midi(s,dict(id='boundary',session_id=sid,start=2.005,end=2.3))))
    assert notes[0]['velocity_14']==100*128+12
    # An initialized held note retains its own prefix, not the most recent CC88.
    notes=performance_notes(midi_events(segment_midi(s,dict(id='held',session_id=sid,start=.1,end=.3))))
    assert notes[0]['velocity_14']==80*128+31
    assert (folder/'events.jsonl').read_text()==raw
    s.db.close()
