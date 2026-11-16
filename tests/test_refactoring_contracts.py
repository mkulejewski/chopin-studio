"""Compatibility characterizations captured before domain/router extraction."""
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.assessment import piece_assessment
from chopin.organisation import analyse_segment, organise, performance_notes
from chopin.progress import current_analyses
from chopin.retention import current_analysis
from chopin.store import Store
from test_practice import make_session, reference


def test_openapi_contract(tmp_path):
    with TestClient(create_app(tmp_path, hardware=False)) as client:
        expected = json.loads((Path(__file__).parent / 'fixtures/api_contract.json').read_text())
        assert client.get('/openapi.json').json() == expected
        assert {'active', 'saving', 'shutting_down', 'notes', 'pedals', 'devices'} <= client.get('/api/status').json().keys()
        assert {'pieces', 'volumes'} == client.get('/api/library').json().keys()
        assert client.get('/api/sessions').json() == []
        assert client.get('/api/recordings').json()['takes'] == []
        assert len(client.get('/api/progress').json()) == 44


@pytest.fixture
def saved_analysis(tmp_path):
    store = Store(tmp_path)
    reference(store)
    sid = make_session(store)
    segment = organise(store, sid)[0]
    result = analyse_segment(store, segment)
    result['segment_snapshot'] = {k: segment[k] for k in ('piece_id', 'start', 'end', 'revision', 'complete', 'discarded')}
    store.execute('INSERT INTO analyses VALUES(?,?,?,?,?,?)', ('original', sid, segment['id'], 'test', '2026-11-16', json.dumps(result)))
    yield store, segment, result
    store.db.close()


@pytest.mark.parametrize('field,value', [('piece_id', 'n9-2'), ('start', .1), ('end', 2), ('revision', 2), ('complete', 0), ('discarded', 1)])
def test_snapshot_changes_withhold_current_evidence_without_changing_history(saved_analysis, field, value):
    store, segment, result = saved_analysis
    original = store.query('SELECT * FROM analyses')
    store.execute(f'UPDATE segments SET {field}=? WHERE id=?', (value, segment['id']))
    changed = store.query('SELECT * FROM segments WHERE id=?', (segment['id'],))[0]
    assert current_analysis(store, changed) == {}
    assert list(current_analyses(store, 'n9-1')) == []
    assert piece_assessment(store, 'n9-1')['latest_performance'] is None
    assert store.query('SELECT * FROM analyses') == original


def test_newer_stale_analysis_does_not_hide_older_current_result(saved_analysis):
    store, segment, result = saved_analysis
    wrong = {**result, 'segment_snapshot': {**result['segment_snapshot'], 'revision': 99}}
    store.execute('INSERT INTO analyses VALUES(?,?,?,?,?,?)', ('new', segment['session_id'], segment['id'], 'test', '2026-11-17', json.dumps(wrong)))
    assert current_analysis(store, segment) == json.loads(json.dumps(result))
    assert [row['id'] for row, _ in current_analyses(store, 'n9-1')] == ['original']
    assert piece_assessment(store, 'n9-1')['latest_performance']['analysis_id'] == 'original'


def test_performance_projection_preserves_source_unknown_fields():
    events = [{'t': 0, 'sequence': 99, 'custom': {'x': 'kept'}, 'message': {'type': 'note_on', 'channel': 2, 'note': 60, 'velocity': 87}},
              {'t': 1, 'message': {'type': 'note_off', 'channel': 2, 'note': 60, 'velocity': 31}}]
    original = json.dumps(events)
    note = performance_notes(iter(events))[0]
    assert (note['pitch'], note['duration'], note['release_velocity'], note['channel']) == (60, 1, 31, 2)
    assert json.dumps(events) == original


def test_legacy_database_initialization_preserves_user_fields_and_pages(tmp_path):
    db = sqlite3.connect(tmp_path / 'studio.sqlite3')
    migration = Path(__file__).parents[1] / 'backend/chopin/migrations/001_initial.sql'
    db.executescript(migration.read_text())
    db.execute("INSERT INTO volumes(id,title,source,edition) VALUES('nocturnes','My volume','synthetic','test')")
    db.execute("INSERT INTO pieces(id,title,genre,opus,musical_key,volume_id,start_page,end_page,notes) VALUES('n9-1','My title','Nocturnes','9 No. 1','B-flat minor','nocturnes',10,14,'My notes')")
    db.commit()
    db.close()
    store = Store(tmp_path)
    row = store.query("SELECT * FROM pieces WHERE id='n9-1'")[0]
    assert (row['title'], row['start_page'], row['end_page'], row['notes']) == ('My title', 10, 14, 'My notes')
    assert len(store.query('SELECT id FROM pieces')) == 44
    assert len(store.query('SELECT id FROM volumes')) == 11
    store.execute("UPDATE pieces SET mastery=1,notes='later',volume_id='schott' WHERE id='n9-1'")
    store.db.close()
    reopened = Store(tmp_path)
    row = reopened.query("SELECT * FROM pieces WHERE id='n9-1'")[0]
    assert (row['mastery'], row['notes'], row['volume_id']) == (1, 'later', 'schott')
    assert reopened.query('PRAGMA user_version')[0]['user_version'] == 6
    reopened.db.close()
