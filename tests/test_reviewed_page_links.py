import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.apply_reviewed_page_links import apply_plan, plan_links


def library(tmp_path):
    (tmp_path/'scores').mkdir()
    (tmp_path/'references').mkdir()
    (tmp_path/'scores'/'score.pdf').write_bytes(b'exact reviewed scan')
    db=sqlite3.connect(tmp_path/'studio.sqlite3');db.row_factory=sqlite3.Row
    db.executescript('''
      CREATE TABLE volumes(id TEXT PRIMARY KEY, filename TEXT);
      CREATE TABLE pieces(id TEXT PRIMARY KEY,volume_id TEXT,start_page INTEGER,end_page INTEGER,printed_page TEXT,notes TEXT);
      CREATE TABLE symbolic_scores(piece_id TEXT,filename TEXT,notes TEXT,quality TEXT);
      CREATE TABLE page_maps(piece_id TEXT,measure INTEGER,pdf_page INTEGER,PRIMARY KEY(piece_id,measure));
      INSERT INTO volumes VALUES('volume','score.pdf');
      INSERT INTO pieces VALUES('p40-1','volume',26,33,'22','personal note');
      INSERT INTO page_maps VALUES('p40-1',1,26);
    ''')
    manifest={'volumes':{'score.pdf':hashlib.sha256(b'exact reviewed scan').hexdigest()},'works':[
        {'piece_id':'p40-1','filename':'score.pdf','references':[],
         'expected_range':[26,33],'reviewed_range':[28,33],
         'pages':[{'measure':1,'pdf_page':28,'status':'ready'},
                  {'measure':14,'pdf_page':29,'status':'ready'},
                  {'printed_measure':25,'pdf_page':30,'status':'withheld'}]}]}
    return db,manifest


def test_apply_backs_up_and_corrects_only_reviewed_seed_data(tmp_path):
    db,manifest=library(tmp_path);backup=tmp_path/'before.json'
    plan=apply_plan(db,tmp_path,manifest,backup)
    assert len(plan['withheld'])==1
    assert [tuple(r) for r in db.execute('SELECT measure,pdf_page FROM page_maps ORDER BY measure')]==[(1,28),(14,29)]
    assert tuple(db.execute('SELECT start_page,end_page,printed_page,notes FROM pieces').fetchone())==(28,33,'24','personal note')
    assert json.loads(backup.read_text())['page_maps']==[dict(piece_id='p40-1',measure=1,pdf_page=26)]
    assert apply_plan(db,tmp_path,manifest,backup)['changes']==[]


def test_preserves_custom_calibration_and_ranges(tmp_path):
    db,manifest=library(tmp_path)
    db.execute("INSERT INTO page_maps VALUES('p40-1',14,30)");db.commit()
    plan=plan_links(db,tmp_path,manifest)
    assert any('preserving custom link' in s for s in plan['skipped'])
    assert not any(c.get('measure')==14 for c in plan['changes'])
    db.execute('UPDATE pieces SET start_page=27');db.commit()
    assert plan_links(db,tmp_path,manifest)['changes']==[]


def test_changed_pdf_or_new_reference_blocks_application(tmp_path):
    db,manifest=library(tmp_path)
    (tmp_path/'scores'/'score.pdf').write_bytes(b'different edition')
    assert plan_links(db,tmp_path,manifest)['changes']==[]
    (tmp_path/'scores'/'score.pdf').write_bytes(b'exact reviewed scan')
    (tmp_path/'references'/'new.xml').write_text('<score/>')
    db.execute("INSERT INTO symbolic_scores VALUES('p40-1','new.xml','[]','provisional')");db.commit()
    assert plan_links(db,tmp_path,manifest)['changes']==[]
    (tmp_path/'references'/'new.xml').unlink()
    assert plan_links(db,tmp_path,manifest)['changes']==[]


def test_failure_rolls_back_entire_batch(tmp_path):
    db,manifest=library(tmp_path)
    db.execute("CREATE TRIGGER reject_link BEFORE INSERT ON page_maps BEGIN SELECT RAISE(ABORT, 'test failure'); END;")
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):apply_plan(db,tmp_path,manifest,tmp_path/'backup.json')
    assert tuple(db.execute('SELECT start_page,end_page,printed_page FROM pieces').fetchone())==(26,33,'22')
    assert tuple(db.execute('SELECT measure,pdf_page FROM page_maps').fetchone())==(1,26)


def test_reviewed_manifest_covers_pages_and_preserves_numbering_exceptions():
    data=json.loads((Path(__file__).resolve().parents[1]/'data/reviewed_page_links.json').read_text())
    works={w['piece_id']:w for w in data['works']}
    assert len(works)==41
    assert sum(len(w['pages']) for w in works.values())==204
    assert works['n9-1']['pages'][1]['printed_measure']==13
    assert works['n9-1']['pages'][1]['measure']==14
    assert works['m6-1']['pages'][1]['measure']==27
    assert works['m6-1']['pages'][2]['measure']==52
    assert works['w64-2']['pages'][2]['measure']==66
    assert works['p26-2']['reviewed_range']==[17,27]
    assert works['p40-1']['reviewed_range']==[28,33]
    assert works['i66']['reviewed_range']==[33,41]
    from scripts.index_downloaded_scores import RANGES
    for work in works.values():
        start,end=work['reviewed_range']
        assert RANGES[work['piece_id']][1:3]==(start,end)
        assert [p['pdf_page'] for p in work['pages']]==list(range(start,end+1))
        mapped=[p['measure'] for p in work['pages'] if 'measure' in p]
        assert mapped==sorted(set(mapped))
        assert all('measure' not in p for p in work['pages'] if p['status']=='withheld')
