"""Isolated scan-study tests: no personal library and no physical devices."""
from collections import Counter
import copy
from fractions import Fraction
import hashlib
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient
import mido

from chopin.app import create_app
from chopin.learning import Learning, evaluate, lesson, reference_groups, stages
from chopin.store import Store
from chopin.learning_score import attack_score_xml


def test_nocturne_form_pages_and_section_connections():
    b=lesson('n15-1')
    assert b['source']['volume_id']=='nocturnes'
    assert b['source']['pdf_pages']==[22,25]
    assert [m['number'] for m in b['measures']]==list(range(75))
    assert [n for c in b['chunks'] for n in range(c['start'],c['end']+1)]==list(range(75))
    assert len(b['chunks'])==37
    assert [b['measures'][n]['pdf_page'] for n in (0,24,25,36,37,49,50,74)]==[22,22,23,23,24,24,25,25]
    assert b['measures'][36]['time_signature']==b['measures'][48]['time_signature']==[6,8]
    plan=stages(b['chunks'],b)
    assert plan[0]['start']==0 and plan[0]['end']==2
    assert [t['start'] for t in plan if t['kind']=='visible' and t['start']>=71]==[73,71]
    assert any(t['kind']=='connection' and (t['start'],t['end'])==(71,74) for t in plan)
    for t in plan:
        if t['kind']=='connection':
            section=b['sections'][b['chunks'][t['chunk']]['section']]
            assert section['start']<=t['start']<=t['end']<=section['end']
    assert len([t for t in plan if t['kind']=='transition'])==11
    assert (plan[-1]['start'],plan[-1]['end'])==(0,74)


def test_reviewed_export_and_scan_landmarks():
    b=lesson('n15-1')
    root=ET.fromstring(attack_score_xml(b))
    assert 'PROVISIONAL' not in root.findtext('work/work-title')
    assert b['reference_status']=='model-reviewed'
    assert not b['review_gaps']
    assert len(b['measure_reviews'])==75
    assert all(r['status']=='model-reviewed' for r in b['measure_reviews'])
    assert all(m['review_status']=='model-reviewed' for m in b['measures'])
    assert len(root.findall('part/measure'))==75
    for m,bar in zip(b['measures'],root.findall('part/measure')):
        expected=Counter((s+1,n['step'],n['alter'],n['octave']) for s in (0,1) for group in m['spellings'][s] for n in group)
        actual=Counter((int(n.findtext('staff')),n.findtext('pitch/step'),int(n.findtext('pitch/alter')),int(n.findtext('pitch/octave'))) for n in bar.findall('note') if n.find('pitch') is not None)
        assert actual==expected,m['number']
    assert all(m['staves'][1] for m in b['measures'] if m['number'] not in (0,36))
    # Sparse held basses do not become repeated key attacks.
    assert b['measures'][30]['staves'][1][0][1]==[56]  # Ab3; tied Db3 continues.
    assert b['measures'][32]['staves'][1][0][1]==[58]  # Bb3; same tied Db3.
    assert b['measures'][43]['staves'][0][1][1]==[62,70]  # Printed D natural4 / Bb4.
    run=b['measures'][68]['grace_notes']
    assert [g['spellings'][0] for g in run]==[
        {'step':step,'alter':alter,'octave':5} for step,alter in
        [('E',0),('F',0),('E',0),('D',0),('E',0),('E',0),('G',1),('F',0),('D',0)]]
    assert len([g for g in b['measures'][73]['grace_notes'] if g['staff']==2])==5
    assert len([g for g in b['measures'][74]['grace_notes'] if g['staff']==2])==3
    assert b['measures'][74]['grace_notes'][3]['staff']==1
    assert run[5]['nested_grace']


def test_draft_cannot_grant_automatic_pass_even_for_its_own_inventory():
    b=copy.deepcopy(lesson('n15-1'))
    b['reference_status']='provisional'
    groups=reference_groups(b,0,2)
    notes=[n['pitch'] for staff in groups for group in staff for n in group['notes']]
    result=evaluate(b,{'start':0,'end':2},notes)
    assert result['uncertain'] and not result['passed']
    assert 'provisional' in result['notice']


def test_exact_scan_gate_and_safe_manual_progress(tmp_path,monkeypatch):
    import copy
    import chopin.learning as module
    original=module.lesson
    b=copy.deepcopy(original('n15-1'))
    fixture=b'Synthetic PDF fixture'
    b['source']['pdf_sha256']=hashlib.sha256(fixture).hexdigest()
    monkeypatch.setattr(module,'lesson',lambda piece_id='e25-1': b if piece_id=='n15-1' else original(piece_id))
    app=create_app(tmp_path,hardware=False)
    (tmp_path/'scores'/'synthetic.pdf').write_bytes(fixture)
    app.state.store.execute("UPDATE volumes SET filename='synthetic.pdf' WHERE id='nocturnes'")
    with TestClient(app) as client:
        assert 'n15-1' in [x['piece_id'] for x in client.get('/api/learning').json()['pieces']]
        other=client.get('/api/learning/e25-1').json()['profile']
        assert client.post('/api/learning/selection',json={'piece_id':'n15-1'}).status_code==200
        snap=client.get('/api/learning/n15-1').json()
        assert snap['ready'] and snap['automatic_ready']
        assert snap['target_page']==22
        assert client.get('/api/learning/n15-1/reference?format=musicxml').status_code==200
        config={**snap['profile']['config'],'auto_continue':False,'auto_restart_on_mistake':False}
        client.put('/api/learning/n15-1',json={'config':config})
        started=client.post('/api/learning/n15-1/start').json()
        app.state.recorder.receive(mido.Message('note_on',note=1,velocity=64))
        app.state.recorder.receive(mido.Message('note_off',note=1))
        app.state.learning.tick()
        assert app.state.learning.active['id']==started['active']['id']
        finished=client.post('/api/learning/n15-1/finish').json()
        assert not finished['history'][0]['result']['passed']
        assert finished['profile']['stage_index']==0
        response=client.post('/api/learning/n15-1/advance',json={'stage_id':finished['target']['id'],'generation':finished['profile']['generation']})
        assert response.status_code==200,response.text
        assert response.json()['profile']['stage_index']==1
        client.post('/api/learning/selection',json={'piece_id':'e25-1'})
        assert client.get('/api/learning/e25-1').json()['profile']==other
        client.post('/api/learning/selection',json={'piece_id':'n15-1'})
        assert client.get('/api/learning/n15-1').json()['profile']['stage_index']==1
        (tmp_path/'scores'/'synthetic.pdf').write_bytes(b'Changed edition')
        assert not client.get('/api/learning/n15-1').json()['ready']


def test_builder_rejects_unknown_input(tmp_path):
    path=Path(__file__).resolve().parents[1]/'scripts/nocturne_op15_no1_learning_builder.py'
    spec=importlib.util.spec_from_file_location('nocturne_builder',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (tmp_path/'references').mkdir()
    (tmp_path/'references'/module.REFERENCE).write_text('<score-partwise/>')
    import pytest
    with pytest.raises(ValueError,match='Unrecognized input'):
        module.build(tmp_path)


def observed(bundle,start,end,hand='both'):
    return [pitch for _,pitch in sorted({(g['position'],n['pitch'])
            for staff in reference_groups(bundle,start,end,hand=hand) for g in staff for n in g['notes']})]


def test_reviewed_whole_piece_each_hand_and_required_small_notes():
    b=lesson('n15-1')
    notes=observed(b,0,74)
    assert len(notes)==1801
    assert evaluate(b,{'start':0,'end':74},notes)['passed']
    for hand in ('right','left'):
        target={'start':0,'end':74,'hand':hand}
        notes=observed(b,0,74,hand)
        assert evaluate(b,target,notes)['passed']
        assert not evaluate(b,target,notes[:-1])['passed']
    # The tiny repeated E and G-sharp are direct printed landmarks, not optional.
    notes=observed(b,68,68,'right')
    assert notes==[77,86,76,77,76,74,76,76,80,77,74]
    assert not evaluate(b,{'start':68,'end':68,'hand':'right'},notes[:7]+notes[8:])['passed']
    wrong=notes.copy();wrong[8]=79
    assert not evaluate(b,{'start':68,'end':68,'hand':'right'},wrong)['passed']
    assert observed(b,74,74,'left')==[41,48,57]
    assert observed(b,74,74,'right')==[60,65,69,72,77]


def test_authoritative_capture_grants_reviewed_pass(tmp_path,monkeypatch):
    monkeypatch.setattr(Learning,'source_status',lambda self:(True,'Synthetic exact-scan fixture'))
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        client.post('/api/learning/selection',json={'piece_id':'n15-1'})
        snap=client.get('/api/learning/n15-1').json()
        config={**snap['profile']['config'],'visible':1,'hidden':1,'auto_continue':False,'auto_finish':False}
        client.put('/api/learning/n15-1',json={'config':config})
        client.post('/api/learning/n15-1/start')
        for pitch in observed(lesson('n15-1'),0,2):
            app.state.recorder.receive(mido.Message('note_on',note=pitch,velocity=64))
            app.state.recorder.receive(mido.Message('note_off',note=pitch))
        finished=client.post('/api/learning/n15-1/finish').json()
        assert finished['history'][0]['result']['capture_ok']
        assert finished['history'][0]['result']['passed']
        assert finished['profile']['stage_index']==1


def test_scan_review_ledger_detects_inventory_drift():
    import json
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('nocturne_builder',root/'scripts/nocturne_op15_no1_learning_builder.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    b=copy.deepcopy(lesson('n15-1'))
    review=json.loads((root/'data/nocturne_op15_no1_scan_review.json').read_text())
    module.validate_review(b['measures'],review)
    b['measures'][68]['staves'][0][-3][1][0]=79  # Reintroduce G-natural instead of G-sharp.
    import pytest
    with pytest.raises(ValueError,match='measure 68'):
        module.validate_review(b['measures'],review)


def test_old_scan_study_progress_is_archived_not_promoted(tmp_path):
    import json
    store=Store(tmp_path)
    old={'config':{'visible':5},'chunks':lesson('n15-1')['chunks'],'stage_index':6,
         'streak':2,'completed':['manual-stage'],'hand':'left','variants':[], 'generation':2}
    store.execute('INSERT INTO learning_profiles VALUES(?,?,?)',
                  ('n15-1','paderewski-scan-study-v1',json.dumps(old)))
    learning=Learning(store,None,'n15-1')
    fresh=learning.profile()
    assert fresh['stage_index']==0 and not fresh['completed'] and fresh['streak']==0
    assert fresh['previous_profile']['state']==old
    assert fresh['config']['visible']==5 and fresh['hand']=='left'
    learning.save(fresh)
    assert learning.profile()['previous_profile']['state']==old
    store.db.close()
