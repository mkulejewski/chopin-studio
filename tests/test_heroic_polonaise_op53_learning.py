"""Synthetic capture tests; never open the personal library or physical devices."""
import copy
import hashlib

import mido
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.learning import Learning, PitchPrefixMatcher, evaluate, lesson, stages
from chopin.store import Store


def select(client, piece='p53'):
    response = client.post('/api/learning/selection', json={'piece_id': piece})
    assert response.status_code == 200, response.text
    return client.get('/api/learning/'+piece).json()


def advance(client, snapshot, piece='p53'):
    response = client.post('/api/learning/'+piece+'/advance', json={
        'stage_id': snapshot['target']['id'], 'generation': snapshot['profile']['generation']})
    assert response.status_code == 200, response.text
    return response.json()


def test_heroic_form_boundaries_and_non_linear_progression():
    bundle = lesson('p53')
    assert bundle['source']['pdf_pages'] == [60, 73]
    assert [m['number'] for m in bundle['measures']] == list(range(1, 182))
    assert [m for c in bundle['chunks'] for m in range(c['start'], c['end']+1)] == list(range(1, 182))
    assert len(bundle['chunks']) == 82
    assert [m['key_fifths'] for m in bundle['measures'][80:120]] == [4]*40
    assert bundle['measures'][120]['key_fifths'] == -4
    # Review pages by printed bar labels, avoiding the reference's extra ordinal.
    assert [(bundle['measures'][m-1]['pdf_page']) for m in (1,17,31,120,130,143,168,181)] == [60,61,62,69,70,71,73,73]
    plan = stages(bundle['chunks'], bundle)
    assert plan[0]['start'] == 17
    coda = [t for t in plan if t['kind'] == 'visible' and t['start'] >= 169]
    assert [t['start'] for t in coda] == [181,179,177,175,173,171,169]
    assert any(t['kind']=='connection' and t['start']==179 and t['end']==181 for t in plan)
    # The trio is acquired independently, not as a 1–100 prefix every time.
    assert not any(t['kind']=='cumulative' for t in plan)
    for t in plan:
        if t['kind']=='connection':
            section = bundle['sections'][bundle['chunks'][t['chunk']]['section']]
            assert section['start'] <= t['start'] <= t['end'] <= section['end']
    assert [t['start'] for t in plan if t['kind']=='transition'] == [13,29,45,61,77,97,117,125,149,165]
    assert plan[-1]['start'] == 1 and plan[-1]['end'] == 181


def test_provisional_bundle_never_supplies_a_pass_or_inherits_aeolian_trill():
    bundle = copy.deepcopy(lesson('p53'))
    bundle['reference_status'] = 'provisional'
    assert not evaluate(bundle, {'start':17,'end':18}, [60])['passed']
    # A reviewed unrelated lesson cannot inherit the etude's D/Eb leniency.
    synthetic = {'piece_id':'p53', 'measures':[{'number':48, 'staves':[
        [['0',[60]]], [['3',[39]]]]}]}
    matcher = PitchPrefixMatcher(synthetic, {'start':48,'end':48})
    matcher.feed([60,38,39])
    assert matcher.mistaken
    assert not evaluate(synthetic, {'start':48,'end':48}, [60,38,39])['passed']


def test_profiles_capture_and_last_viewed_piece_survive_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(Learning, 'source_status', lambda self: (True, 'Synthetic scan'))
    app = create_app(tmp_path, hardware=False)
    with TestClient(app) as client:
        aeolian = client.get('/api/learning/e25-1').json()
        config = {**aeolian['profile']['config'], 'visible':2, 'auto_continue':False}
        client.put('/api/learning/e25-1', json={'config':config})
        aeolian = advance(client, aeolian, 'e25-1')
        heroic = select(client)
        assert heroic['target']['start'] == 17 and heroic['automatic_ready']
        counterpart = client.get('/api/learning/p53/reference').json()
        assert counterpart['piece_id'] == 'p53' and counterpart['reference_status'] == 'model-reviewed'
        engraving = client.get('/api/learning/p53/reference?format=musicxml')
        assert engraving.status_code == 200
        assert engraving.headers['content-type'].startswith('application/vnd.recordare.musicxml+xml')
        assert 'unmeasured pitch/attack study' in engraving.text
        assert heroic['profile']['config']['visible'] == 3
        config = {**heroic['profile']['config'], 'visible':1, 'hidden':1, 'auto_continue':False, 'auto_restart_on_mistake':False}
        client.put('/api/learning/p53', json={'config':config})
        started = client.post('/api/learning/p53/start').json()
        recorder = app.state.recorder
        recorder.receive(mido.Message('note_on', note=1, velocity=64))
        recorder.receive(mido.Message('note_off', note=1))
        app.state.learning.tick()
        assert app.state.learning.active['id'] == started['active']['id']  # Manual finishing preserves this failed take for review.
        finished = client.post('/api/learning/p53/finish').json()
        result = finished['history'][0]['result']
        assert result['capture_ok'] and not result['passed']
        assert result['error_count'] > 0
        accepted = client.post('/api/learning/p53/attempts/'+finished['history'][0]['id']+'/accept').json()
        assert accepted['profile']['stage_index'] == 1
        assert accepted['history'][0]['result']['manual_accepted']
        assert not accepted['history'][0]['result']['passed']
        client.put('/api/learning/p53/hand', json={'hand':'left'})
        left = client.get('/api/learning/p53').json()
        left = advance(client, left)
        left = advance(client, left)
        # Switching while recording saves an ungraded take for the right piece.
        recording = client.post('/api/learning/p53/start').json()['active']
        restored = select(client, 'e25-1')
        assert restored['profile']['stage_index'] == aeolian['profile']['stage_index']
        assert restored['profile']['config']['visible'] == 2
        assert client.post('/api/learning/p53/start').status_code == 409
        restored = select(client)
        assert restored['profile']['hand'] == 'left' and restored['profile']['stage_index'] == 2
        assert restored['history'][0]['id'] == recording['id']
        assert restored['history'][0]['status'] == 'paused'
        assert restored['history'][0]['result']['capture_ok']
        assert client.get('/api/learning').json()['selected_piece'] == 'p53'
    app = create_app(tmp_path, hardware=False)
    with TestClient(app) as client:
        assert app.state.learning.piece_id == 'p53'
        snap = client.get('/api/learning/p53').json()
        assert snap['profile']['stage_index'] == 2 and snap['profile']['hand'] == 'left'
        assert snap['active'] is None and snap['pending_at'] is None
        client.put('/api/learning/p53/hand', json={'hand':'both'})
        assert client.get('/api/learning/p53').json()['profile']['stage_index'] == 1
        restored = select(client, 'e25-1')
        assert restored['profile']['stage_index'] == 1


def test_coda_review_includes_only_learned_tail_and_current_chunk(tmp_path, monkeypatch):
    monkeypatch.setattr(Learning, 'source_status', lambda self: (True, 'Synthetic scan'))
    app = create_app(tmp_path, hardware=False)
    with TestClient(app) as client:
        select(client)
        learning = app.state.learning
        profile = learning.profile()
        plan = stages(profile['chunks'], learning.lesson())
        index = next(i for i,t in enumerate(plan) if t['kind']=='visible' and t['start']==179)
        profile.update(stage_index=index, completed=[t['id'] for t in plan[:index]])
        learning.save(profile)
        snap = learning.snapshot()
        assert snap['review']['learned_start'] == snap['review']['learned_end'] == 181
        assert snap['review']['current_start'] == 179 and snap['review']['current_end'] == 181
        review = client.post('/api/learning/p53/review').json()
        assert review['target']['start'] == 181 and review['target']['end'] == 181
        client.post('/api/learning/p53/pause')
        client.post('/api/learning/p53/review/leave')
        review = client.post('/api/learning/p53/review', json={'include_current':True}).json()
        assert review['target']['start'] == 179 and review['target']['end'] == 181
        assert review['profile']['stage_index'] == index
        client.post('/api/learning/p53/pause')
        client.post('/api/learning/p53/review/leave')
        profile.update(stage_index=len(plan), completed=[t['id'] for t in plan])
        learning.save(profile)
        snap = learning.snapshot()
        assert snap['review']['current_start'] == 155
        assert snap['review']['current_end'] == 168


def test_heroic_uses_its_own_scan_hash_and_reviewed_reference_gate(tmp_path, monkeypatch):
    import chopin.learning as module
    original = module.lesson
    bundle = copy.deepcopy(original('p53'))
    pdf = b'Synthetic score fixture; not a published score'
    bundle['source']['pdf_sha256'] = hashlib.sha256(pdf).hexdigest()
    monkeypatch.setattr(module, 'lesson', lambda piece_id='e25-1': bundle if piece_id=='p53' else original())
    store = Store(tmp_path)
    learning = Learning(store, None, 'p53')
    assert not learning.source_status()[0]
    (tmp_path/'scores'/'synthetic.pdf').write_bytes(pdf)
    store.execute("UPDATE volumes SET filename='synthetic.pdf' WHERE id='polonaises'")
    assert learning.source_status()[0] and learning.automatic_ready()
    (tmp_path/'scores'/'synthetic.pdf').write_bytes(b'Changed edition')
    assert not learning.source_status()[0]
    store.db.close()


def observed_attacks(bundle, start, end, hand='both'):
    from chopin.learning import reference_groups
    return [pitch for _,pitch in sorted({(g['position'],n['pitch'])
            for staff in reference_groups(bundle,start,end,hand=hand) for g in staff for n in g['notes']})]


def test_reviewed_scan_landmarks_and_required_grace_notes():
    from fractions import Fraction
    from chopin.learning import reference_groups
    b=lesson('p53')
    assert b['reference_status']=='model-reviewed' and b['revision']=='paderewski-attacks-v1'
    assert len(b['review_pages'])==14 and all(p['status']=='model-reviewed' for p in b['review_pages'])
    assert not b['review_gaps']
    assert len(observed_attacks(b,1,181))==5892
    def chord(measure,staff,beat):
        return {n['pitch'] for g in reference_groups(b,measure,measure,hand='right' if staff==1 else 'left')[staff-1]
                if g['position']==(measure,Fraction(beat)) for n in g['notes']}
    # Direct scan landmarks, including every category that the draft got wrong.
    assert chord(5,1,'7/4')=={59,54}  # B3/F#3, not Bb3/F#3.
    assert chord(5,1,'9/4')=={61,56}  # C#4/G#3.
    assert chord(31,1,0)=={82,70} and chord(31,2,0)==set()
    assert chord(35,1,'5/2')=={90,82,75}  # Gb6/Bb5/Eb5.
    assert chord(37,2,1)=={70,61,58}
    assert chord(39,1,1)=={94,82}  # Bb6/Bb5 under ottava.
    assert chord(49,1,'23/8')=={72,65} and chord(50,1,0)=={72}  # F4 tied.
    assert chord(52,2,'9/8')=={64} and chord(52,2,'11/8')=={71}
    assert chord(83,1,'1/4')==set() and chord(83,2,'1/4')=={51,39}
    assert chord(91,1,0)=={66,59,57} and chord(91,2,0)=={52,40}
    assert chord(119,1,'5/2')=={77,70,68,65}
    assert chord(120,1,0)=={75,67,63}
    assert b['measures'][119]['key_changes']==[{'beat':'1/2','fifths':-4}]
    assert len(b['measures'][161]['staves'][1])==9  # Recovered complete accompaniment.
    for m in (33,34,65,66,155,156):
        grace=b['measures'][m-1]['grace_notes']
        assert grace[0]['spellings']==[{'step':'F','alter':0,'octave':4}]
    assert chord(62,1,2)==set() and chord(62,1,'127/64')=={61}
    for index in (1,2,3,4):
        assert len(b['measures'][178]['staves'][0][index][1])==4


def test_reviewed_full_piece_and_hands_match_with_strict_boundaries():
    b=lesson('p53')
    notes=observed_attacks(b,1,181)
    assert evaluate(b,{'start':1,'end':181},notes)['passed']
    # This is a matching integration check, not independent proof of transcription.
    for hand in ('right','left'):
        target={'start':17,'end':18,'hand':hand}
        assigned=observed_attacks(b,17,18,hand)
        assert evaluate(b,target,assigned)['passed']
        assert not evaluate(b,target,assigned[:-1])['passed']
    # A real printed grace in 18 cannot be silently omitted.
    from fractions import Fraction
    from chopin.learning import reference_groups
    grace=b['measures'][17]['grace_notes'][0]
    position=(18,Fraction(grace['attack_beat']))
    ordered=sorted({(g['position'],n['pitch']) for st in reference_groups(b,17,18) for g in st for n in g['notes']})
    no_grace=[pitch for pos,pitch in ordered if pos!=position]
    assert not evaluate(b,{'start':17,'end':18},no_grace)['passed']


def test_ornament_allowance_is_local_and_staff_display_uses_its_position():
    from fractions import Fraction
    from chopin.learning_staves import LiveStaffMatcher
    b=lesson('p53')
    notes=observed_attacks(b,25,25)
    index=notes.index(67)
    expanded=notes[:index+1]+[68,67,68,67]+notes[index+1:]
    assert evaluate(b,{'start':25,'end':25},expanded)['passed']
    assert not evaluate(b,{'start':25,'end':25},[68]+notes)['passed']
    matcher=LiveStaffMatcher(b,{'start':25,'end':25})
    matcher.feed(expanded)
    ornament=[e for e in matcher.evidence(True) if e['kind']=='ornament']
    assert ornament and all(e['staff']==1 and e['position'][0]==25 for e in ornament)
    projection=matcher.comparison(True)
    assert all(g['beat'] < 25*3 for g in projection['groups'])
    # Trills around a held Db5 can continue after the required small Db4.
    notes=observed_attacks(b,62,62)
    # The small Db4 ends the right-hand inventory; left-hand accompaniment
    # can finish before or after the trill because staff coordination is flexible.
    assert 61 in notes
    assert evaluate(b,{'start':62,'end':62},notes+[75,73,75,73])['passed']
    assert not evaluate(b,{'start':62,'end':62},[n for n in notes if n!=61]+[75,73,75,73])['passed']
    limited={**b,'attack_limit':2}
    assert evaluate(limited,{'start':62,'end':62},notes)['uncertain']


def test_scan_study_history_is_retained_without_promoting_old_progress(tmp_path):
    import json
    store=Store(tmp_path)
    old={'config':{'visible':5,'auto_continue':False}, 'chunks':lesson('p53')['chunks'],
         'variants':[{'note_id':'old-note','reason':'Personal edition'}], 'corrections':[],
         'stage_index':18,'streak':2,'completed':['old-stage'], 'generation':3,
         'hand':'left','hand_progress':{'both':{'stage_index':9,'completed':['manual']}}}
    store.execute('INSERT INTO learning_profiles VALUES(?,?,?)',
                  ('p53','paderewski-plan-v1-draft-attacks-v1',json.dumps(old)))
    learning=Learning(store,None,'p53')
    profile=learning.profile()
    assert profile['stage_index']==0 and profile['streak']==0 and not profile['completed']
    assert profile['hand']=='left' and profile['config']['visible']==5
    assert profile['previous_profile']['state']==old
    learning.save(profile)
    assert learning.profile()['previous_profile']['state']==old
    store.db.close()


def test_musicxml_export_preserves_required_attacks_graces_and_midbar_key():
    from collections import Counter
    import xml.etree.ElementTree as ET
    from chopin.learning_score import attack_score_xml
    b=lesson('p53')
    root=ET.fromstring(attack_score_xml(b))
    measures=root.findall('part/measure')
    assert len(measures)==181
    assert root.findtext('work/work-title').endswith('unmeasured pitch/attack study')
    for source,bar in zip(b['measures'],measures):
        wanted=Counter((staff,n['step'],n['alter'],n['octave']) for staff in (1,2)
                       for chord in source['spellings'][staff-1] for n in chord)
        actual=Counter((int(n.findtext('staff')), n.findtext('pitch/step'),int(n.findtext('pitch/alter') or 0),int(n.findtext('pitch/octave')))
                       for n in bar.findall('note') if n.find('pitch') is not None and n.find('notehead') is None)
        assert actual==wanted,source['number']
    assert [k.findtext('fifths') for k in measures[119].findall('attributes/key')]==['4','-4','-4']
    assert measures[17].find('note/grace') is not None
    assert measures[61].find('note/notations/ornaments/trill-mark') is not None
