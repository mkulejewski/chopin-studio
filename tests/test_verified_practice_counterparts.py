import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.store import Store
from chopin.recognition import Recognizer

spec=importlib.util.spec_from_file_location('verified_builder',Path(__file__).resolve().parents[1]/'scripts/build_verified_practice_counterparts.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def candidate(tmp_path):
    path=tmp_path/'derived.musicxml'
    path.write_text('<score-partwise version="4.0"><part-list/><part id="P1"/></score-partwise>')
    evidence=dict(piece_id='p28-4',status='model-reviewed',open_issues=[],
                  derived_musicxml_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  provenance='Synthetic review fixture only',licence='CC0 synthetic',edition='Synthetic',
                  verified_scope=['fixture pitches'],notes=[dict(pitch=60,onset=0,duration=1,measure=1)])
    return path,evidence


def test_install_is_additive_and_preserves_originals_and_user_edits(tmp_path):
    store=Store(tmp_path/'data')
    original=store.root/'references/original.musicxml'
    original.write_bytes(b'original source bytes')
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  ('old','p28-4',original.name,'original','test','original edition','provisional','[]','today'))
    path,evidence=candidate(tmp_path)
    ident=builder.install(store.root,path,evidence)
    assert original.read_bytes()==b'original source bytes'
    assert store.query("SELECT * FROM symbolic_scores WHERE id='old'")[0]['quality']=='provisional'
    assert store.query('SELECT quality FROM symbolic_scores WHERE id=?',(ident,))[0]['quality']=='verified'
    assert builder.install(store.root,path,evidence)==ident
    assert len(store.query('SELECT * FROM symbolic_scores'))==2
    store.execute('UPDATE symbolic_scores SET notes=? WHERE id=?',('[{"pitch":61}]',ident))
    with pytest.raises(ValueError,match='has edits'):
        builder.install(store.root,path,evidence)
    assert json.loads(store.query('SELECT notes FROM symbolic_scores WHERE id=?',(ident,))[0]['notes'])==[{'pitch':61}]
    store.db.close()


def test_unreviewed_or_modified_candidate_cannot_be_installed(tmp_path):
    store=Store(tmp_path/'data');path,evidence=candidate(tmp_path)
    evidence['status']='provisional'
    with pytest.raises(ValueError,match='completed model reviews'):
        builder.install(store.root,path,evidence)
    evidence['status']='model-reviewed';path.write_text('changed after review')
    with pytest.raises(ValueError,match='changed after review'):
        builder.install(store.root,path,evidence)
    assert not store.query('SELECT * FROM symbolic_scores')
    store.db.close()


def test_library_distinguishes_verified_reference_and_exposes_review_scope(tmp_path):
    app=create_app(tmp_path/'data',hardware=False)
    path,evidence=candidate(tmp_path)
    ident=builder.install(app.state.store.root,path,evidence)
    with TestClient(app) as client:
        piece=next(p for p in client.get('/api/library').json()['pieces'] if p['id']=='p28-4')
        assert piece['verified_reference_count']==1 and piece['provisional_reference_count']==0
        assert client.get('/api/references/'+ident).json()['verification']['verified_scope']==['fixture pitches']


def test_equal_identity_evidence_prefers_verified_edition_of_same_piece():
    notes=[dict(pitch=p,onset=i,duration=.5,measure=i//4+1) for i,p in
           enumerate([60,64,67,62,69,65,71,63,68,61,70,66])]
    older=dict(id='old',piece_id='p28-4',quality='provisional',notes=notes)
    reviewed=dict(id='reviewed',piece_id='p28-4',quality='verified',notes=notes)
    assert Recognizer([older,reviewed]).match(notes)['reference_id']=='reviewed'


def test_rebuild_keeps_fractional_tuplets_and_overlapping_independent_voices():
    import xml.etree.ElementTree as ET
    from fractions import Fraction as F
    tree=ET.fromstring('<score-partwise><part-list/><part id="P1"><measure number="0"><attributes><divisions>12</divisions><staves>2</staves></attributes></measure></part></score-partwise>')
    def note(voice,chord=False):
        return ET.fromstring(f'<note>{"<chord/>" if chord else ""}<pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>{voice}</voice><type>eighth</type><staff>1</staff></note>')
    rows=[(0,[{'onset':F(0),'duration':F(1,3),'note':note(1)},
              {'onset':F(1,3),'duration':F(2,3),'note':note(1)},
              {'onset':F(0),'duration':F(1),'note':note(2)},
              {'onset':F(0),'duration':F(1),'note':note(2,True)}])]
    result=ET.fromstring(builder.rebuild_grand_staff(tree,rows,'test',{0:3},{},{}))
    measure=result.find('part/measure');divisions=int(measure.findtext('attributes/divisions'))
    events=builder.measure_events(measure,divisions)
    assert [(e['onset'],e['duration']) for e in events]==[(F(0),F(1,3)),(F(1,3),F(2,3)),(F(0),F(1)),(F(0),F(1))]
    assert measure.findtext('attributes/staves')=='2'


def test_only_narrowed_batch_has_completed_builders_and_full_coverage():
    expected={'p28-4','m68-2','m68-3','m30-2','n-b49','p40-1','p40-2','w64-2','e10-12'}
    assert set(builder.BUILDERS)==expected
    inventory=json.loads((builder.ROOT/'data/library_counterpart_audit.json').read_text())
    assert {w['piece_id'] for w in inventory['works'] if w['in_current_batch']}==expected
    for piece in expected:
        review=json.loads((builder.REVIEW_ROOT/(piece+'.json')).read_text())
        start=review.get('first_printed_measure',0)
        assert review['status']=='model-reviewed' and not review['open_issues']
        assert [m['printed_measure'] for m in review['coverage']]==list(range(start,start+review['measure_count']))
        assert all(m['staves']==[1,2] for m in review['coverage'])
