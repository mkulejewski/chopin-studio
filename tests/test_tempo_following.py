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
