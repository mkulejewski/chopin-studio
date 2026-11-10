import json
import queue
from types import SimpleNamespace

import pytest

from chopin.live import LiveFollowing
from chopin.organisation import Recognizer, analyse_segment
from chopin.store import Store
from chopin.tempo import infer_tempo


def score(quality='verified'):
    pitches = [36, 43, 40, 45, 38, 47, 41, 44, 39, 46, 42, 48]
    notes = [dict(pitch=p, onset=i*2, duration=1, measure=i//2+1)
             for i, p in enumerate(pitches)]
    return dict(id='reference', piece_id='n9-1', notes=notes, quality=quality)


def test_bass_tempo_ignores_right_hand_ornaments_and_missing_bass_note():
    row = score()
    observed = []
    for i, n in enumerate(row['notes']):
        if i != 5:
            observed.append({**n, 'onset':10+n['onset']*.5})
        observed.extend(dict(pitch=70+j, onset=10+n['onset']*.5+j*.08)
                        for j in range(1, 5))
    observed.sort(key=lambda n:n['onset'])
    ref = Recognizer([row]).references[0]
    # Isolate bass timing from the right-hand retrieval path.
    match = dict(reference_id='reference', reference_start=0, reference_end=12, pairs=[])
    tempo = infer_tempo(observed, ref, match)
    assert tempo['method'] == 'bass notes'
    assert tempo['bpm'] == pytest.approx(120)
    assert tempo['anchors'] >= 10
    assert len(tempo['curve']) >= 8


def test_tempo_uses_matched_score_beats_not_note_frequency():
    row=score()
    row['notes']=[{**n,'pitch':n['pitch']+36} for n in row['notes']]
    observed=[{**n,'onset':5+n['onset']*.75} for n in row['notes']]
    recognizer=Recognizer([row]);match=recognizer.match(observed)
    tempo=infer_tempo(observed,recognizer.references[0],match)
    assert tempo['method']=='matched score notes'
    assert tempo['bpm']==pytest.approx(80)
    assert infer_tempo(observed[:2],recognizer.references[0],{**match,'pairs':match['pairs'][:2]})['bpm'] is None


def test_local_tempo_tracks_rubato_and_does_not_bridge_long_pause():
    row=score();observed=[];at=0
    for i,n in enumerate(row['notes']):
        if i:at+=1 if i<6 else 2
        observed.append({**n,'onset':at})
    recognizer=Recognizer([row]);match=recognizer.match(observed)
    tempo=infer_tempo(observed,recognizer.references[0],match)
    assert tempo['curve'][0]['bpm']==120
    assert tempo['curve'][-1]['bpm']==60
    assert infer_tempo([{**n,'onset':i*12} for i,n in enumerate(row['notes'])],recognizer.references[0],match)['bpm'] is None


def test_provisional_navigation_is_explicit_and_does_not_certify_score():
    row=score('provisional');observed=[{**n,'onset':n['onset']*.5} for n in row['notes']]
    assert Recognizer([row]).match(observed)['confidence']==.84
    nav=Recognizer([row],navigation=True).match(observed)
    assert nav['confidence']==1 and nav['quality']=='provisional'


def test_dense_live_chords_can_recognise_and_turn_across_mapped_pages(tmp_path,monkeypatch):
    store=Store(tmp_path);row=score();notes=[]
    for n in row['notes']:
        notes.extend({**n,'pitch':n['pitch']+offset} for offset in range(9))
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  ('reference','n9-1','reference.musicxml','test','test','test','verified',json.dumps(notes),'today'))
    store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',1,4))
    store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',5,5))
    store.set_setting('live_enabled',True);store.set_setting('live_auto_turn',True)
    recorder=SimpleNamespace(live_queue=queue.Queue(),live_overflow=False)
    live=LiveFollowing(store,recorder);live.close()
    now=[100.0];monkeypatch.setattr('chopin.live.time.monotonic',lambda:now[0])
    try:
        for i in range(12):
            now[0]+=1
            for n in notes[i*9:(i+1)*9]:
                recorder.live_queue.put({'t':now[0],'message':{'type':'note_on','note':n['pitch'],'velocity':80}})
            live.tick()
        assert live.state['stable']
        assert live.state['page_request']['page']==5
        assert live.state['tempo']['bpm']==120
        request=live.state['page_request'].copy()
        now[0]+=.2;live.tick()
        assert live.state['page_request']==request
    finally:store.db.close()


def test_live_explains_provisional_block_then_allows_opt_in(tmp_path,monkeypatch):
    store=Store(tmp_path);row=score('provisional')
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  ('reference','n9-1','reference.musicxml','test','test','test','provisional',json.dumps(row['notes']),'today'))
    store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',1,4))
    store.set_setting('live_enabled',True);store.set_setting('live_auto_turn',True)
    recorder=SimpleNamespace(live_queue=queue.Queue(),live_overflow=False)
    live=LiveFollowing(store,recorder);live.close()
    now=[100.0];monkeypatch.setattr('chopin.live.time.monotonic',lambda:now[0])
    try:
        for i,n in enumerate(row['notes']):
            now[0]+=1
            recorder.live_queue.put({'t':now[0],'message':{'type':'note_on','note':n['pitch'],'velocity':80}})
            live.tick()
        assert not live.state.get('page_request')
        assert 'Provisional reference' in live.state['turn_status']
        store.set_setting('live_allow_provisional',True)
        live.signature=None
        for n in row['notes']:
            now[0]+=1
            recorder.live_queue.put({'t':now[0],'message':{'type':'note_on','note':n['pitch'],'velocity':80}})
            live.tick()
        assert live.state['page_request']['page']==4
        assert 'Only the opening page' in live.state['turn_status']
        assert store.query('SELECT quality FROM symbolic_scores')[0]['quality']=='provisional'
    finally:store.db.close()


def test_saved_analysis_includes_inferred_tempo(tmp_path):
    store=Store(tmp_path);row=score();session='take'
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  ('reference','n9-1','reference.musicxml','test','test','test','verified',json.dumps(row['notes']),'today'))
    folder=store.root/'sessions'/session;folder.mkdir()
    events=[]
    for n in row['notes']:
        events.extend([{'t':n['onset']*.5,'message':{'type':'note_on','note':n['pitch'],'velocity':80}},
                       {'t':n['onset']*.5+.2,'message':{'type':'note_off','note':n['pitch']}}])
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute('INSERT INTO sessions(id,name,started,status,duration,events) VALUES(?,?,?,?,?,?)',
                  (session,'take','today','saved',12,len(events)))
    result=analyse_segment(store,dict(id='segment',session_id=session,piece_id='n9-1',start=0,end=12,complete=0))
    assert result['tempo']['bpm']==120
    assert result['tempo']['method']=='bass notes'
    assert result['tempo_curve']==result['tempo']['curve']
    store.db.close()


def test_bass_attack_density_does_not_change_score_relative_tempo():
    # Four quarter notes per measure, first once then twice per measure.
    beats=[0,4,8,12,14,16,18,20,24,28]
    pitches=[36,43,40,45,38,47,41,44,39,46]
    notes=[dict(pitch=p,onset=b,duration=.5,measure=int(b//4)+1) for b,p in zip(beats,pitches)]
    reference=Recognizer([dict(id='bass',piece_id='test',notes=notes,quality='verified')]).references[0]
    match=dict(reference_id='bass',reference_start=0,reference_end=len(notes),pairs=[])
    observed=[{**n,'onset':10+n['onset']*.5} for n in notes]
    tempo=infer_tempo(observed,reference,match)
    assert tempo['bpm']==120
    assert all(p['bpm']==120 for p in tempo['curve'])
    assert tempo['unit']=='quarter notes/min'


def test_live_estimates_missing_notes_then_pauses_until_reacquired(tmp_path,monkeypatch):
    store=Store(tmp_path);row=score()
    row['notes'] += [dict(pitch=50+i,onset=24+i*2,duration=1,measure=7+i//2) for i in range(12)]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  ('reference','n9-1','reference.musicxml','test','test','test','verified',json.dumps(row['notes']),'today'))
    for measure,page in [(1,4),(7,5),(9,6)]:store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',measure,page))
    store.set_setting('live_enabled',True);store.set_setting('live_auto_turn',True)
    recorder=SimpleNamespace(live_queue=queue.Queue(),live_overflow=False)
    live=LiveFollowing(store,recorder);live.close()
    now=[100.0];monkeypatch.setattr('chopin.live.time.monotonic',lambda:now[0])
    def play(pitch):
        now[0]+=1
        recorder.live_queue.put({'t':now[0],'message':{'type':'note_on','note':pitch,'velocity':80}})
        live.tick()
    try:
        for n in row['notes'][:12]:play(n['pitch'])
        assert live.anchor and live.state['stable']
        monkeypatch.setattr(Recognizer,'match',lambda *args,**kwargs:dict(confidence=0,label='Unknown piece'))
        for _ in range(4):play(100)
        assert live.state['estimated'] and live.state['measure']==8
        assert live.state.get('page_request',{}).get('page',4)==4  # Keep the confirmed page during the margin/dwell.
        for _ in range(2):play(100)
        assert live.state['measure']==9
        assert live.state['page_request']['page']==5
        now[0]+=.2;live.tick();request=live.state['page_request'].copy()
        now[0]+=.2;live.tick();assert live.state['page_request']==request
        now[0]+=4;live.tick()
        assert not live.state['stable'] and not live.state.get('page_request')
        assert live.anchor is None
        play(100)
        assert not live.state.get('stable')
    finally:store.db.close()


def test_tempo_withholds_half_double_speed_disagreement():
    notes=[];observed=[]
    for i in range(12):
        notes.extend([dict(pitch=36+i,onset=i,duration=.4,measure=i//4+1),
                      dict(pitch=84+i,onset=2*i,duration=.4,measure=i//2+1)])
        observed.extend([dict(pitch=36+i,onset=i,duration=.4),dict(pitch=84+i,onset=i,duration=.4)])
    notes.sort(key=lambda n:(n['onset'],n['pitch']))
    ref=Recognizer([dict(id='ref',piece_id='test',quality='verified',notes=notes)]).references[0]
    by_beat={g['onset']:i for i,g in enumerate(ref['groups'])}
    match=dict(reference_id='ref',reference_start=0,reference_end=len(ref['groups']),
               confidence=.95,query_coverage=1,pairs=[(i,by_beat[2*i]) for i in range(12)])
    tempo=infer_tempo(observed,ref,match)
    assert tempo['status']=='ambiguous' and tempo['bpm'] is None
    assert not tempo['curve']


def test_local_tempo_outliers_cannot_drive_page_prediction():
    from chopin.tempo import timing_curve
    anchors=[dict(time=i,beat=i,measure=i//4+1) for i in range(20)]
    anchors += [dict(time=20+i*.5,beat=24+2*i,measure=7) for i in range(3)]
    curve,rejected=timing_curve(anchors)
    assert rejected>0
    assert max(p['bpm'] for p in curve)<105


def test_two_page_estimates_keep_two_measure_margin_and_dwell(tmp_path,monkeypatch):
    store=Store(tmp_path)
    store.set_setting('live_auto_turn',True)
    store.execute('UPDATE pieces SET view=? WHERE id=?',(json.dumps({'two_pages':True}),'n9-1'))
    for measure,page in [(1,4),(7,5)]:store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',measure,page))
    live=LiveFollowing(store,SimpleNamespace(live_queue=queue.Queue(),live_overflow=False));live.close()
    row=score();row['notes'] += [dict(pitch=50+i,onset=24+i*2,duration=1,measure=7+i//2) for i in range(12)]
    ref=Recognizer([row]).references[0]
    live.anchor={'time':0,'beat':22,'bpm':120,'reference':ref,'measure':6,
                 'state':dict(piece_id='n9-1',confidence=1,tempo={'bpm':120})}
    try:
        for now in [2,3,4,5,6]:
            live.last_note=now;live.estimate(now)
            assert live.state.get('page_request',{}).get('page',4)==4
        live.last_note=7;live.estimate(7)
        assert live.state['page_request']['page']==5
    finally:store.db.close()


def test_estimates_never_rewind_note_confirmed_page(tmp_path):
    store=Store(tmp_path);store.set_setting('live_auto_turn',True)
    store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',1,4))
    store.execute('INSERT INTO page_maps VALUES(?,?,?)',('n9-1',7,5))
    live=LiveFollowing(store,SimpleNamespace(live_queue=queue.Queue(),live_overflow=False));live.close()
    ref=Recognizer([score()]).references[0]
    live.confirmed_page=('n9-1',5)
    live.anchor={'time':0,'beat':4,'bpm':120,'reference':ref,'measure':2,
                 'state':dict(piece_id='n9-1',confidence=1)}
    try:
        for now in [1,2,3]:
            live.last_note=now;live.estimate(now)
            assert not live.state.get('page_request')
    finally:store.db.close()


def test_open_score_is_fallback_but_does_not_override_another_recognised_piece(tmp_path,monkeypatch):
    store=Store(tmp_path);store.set_setting('live_enabled',True);store.set_setting('live_auto_turn',True)
    recorder=SimpleNamespace(live_queue=queue.Queue(),live_overflow=False)
    live=LiveFollowing(store,recorder);live.close();live.context_piece_id='n72-1'
    now=[100.0];monkeypatch.setattr('chopin.live.time.monotonic',lambda:now[0])
    def play():
        now[0]+=1
        recorder.live_queue.put({'t':now[0],'message':{'type':'note_on','note':40,'velocity':80}})
        live.tick()
    try:
        monkeypatch.setattr(Recognizer,'match',lambda *args,**kwargs:dict(label='Unknown piece',confidence=0))
        play()
        assert live.state['piece_id']=='n72-1' and live.state['assumed']
        assert not live.state['stable'] and live.state['measure'] is None
        assert not live.state.get('page_request')
        monkeypatch.setattr(Recognizer,'match',lambda *args,**kwargs:dict(piece_id='n9-2',confidence=.98,last_measure=3,quality='verified',label='Identified'))
        for _ in range(3):play()
        assert live.state['piece_id']=='n9-2' and not live.state.get('assumed')
        monkeypatch.setattr(Recognizer,'match',lambda *args,**kwargs:dict(label='Unknown piece',confidence=0))
        live.context_piece_id='n9-1';play()
        assert live.state['piece_id']=='n9-1' and live.state['assumed']
        live.context_piece_id=None;play()
        assert not live.state.get('piece_id') and not live.state.get('assumed')
    finally:store.db.close()
