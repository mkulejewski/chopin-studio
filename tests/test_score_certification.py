import time

import mido
import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.certification_matching import written_attacks
from chopin.learning_definition import BUNDLES, lesson
from chopin.learning_profiles import load_profile, save_profile
from chopin.learning_source import LearningSource
from chopin.score_certification import build_review


def synthetic_score(pitches):
    return {'measures': [
        {'number': number, 'pdf_page': number, 'staves': [[[str(i), notes] for i, notes in enumerate(groups)], []]}
        for number, groups in enumerate(pitches, 1)
    ]}


@pytest.mark.parametrize('piece', BUNDLES)
def test_whole_reference_with_reversed_chord_order(piece):
    bundle = lesson(piece)
    pitches = [note['pitch'] for _, notes in written_attacks(bundle) for note in reversed(notes)]
    measures = bundle['measures']
    review = build_review(bundle, pitches, measures[0]['number'], measures[-1]['number'])
    assert review['matched_count'] == len(pitches)
    assert review['missing_count'] == review['extra_count'] == 0
    assert len(review['measures']) == len(measures)


def test_long_omission_resynchronizes_and_isolated_changes_have_proposals():
    bundle = synthetic_score([[[60], [61], [62], [63], [64], [65], [66], [67], [68], [69]]])
    review = build_review(bundle, [60, 95, 62, 68, 69], 1, 1)
    rows = review['measures'][0]['attacks']
    assert (review['matched_count'], review['missing_count'], review['extra_count']) == (4, 6, 1)
    assert rows[1]['suggestion'] == 'replace'
    assert rows[1]['extra'] == [{'pitch': 95, 'played_index': 1}]
    assert all('suggestion' not in row for row in rows[3:8])
    assert rows[-1]['expected'][0]['played_index'] == 4


def test_pause_retains_the_discrepancies_before_cutoff_and_final_extra():
    bundle = synthetic_score([[[60], [61]], [[62], [63], [64]], [[65]]])
    review = build_review(bundle, [60, 62, 63, 90], 1, 3, through_pause=True)
    assert [m['number'] for m in review['measures']] == [1, 2]
    assert review['pause_endpoint'] == {'measure': 2, 'attack': 2, 'partial_measure': True, 'partial_attack': False}
    assert (review['matched_count'], review['missing_count'], review['extra_count']) == (3, 1, 1)
    with pytest.raises(ValueError, match='No matching attack'):
        build_review(bundle, [99], 1, 3, through_pause=True)



def test_pause_inside_chord_leaves_remaining_keys_outside_review():
    bundle = synthetic_score([[[60], [62, 65, 69]], [[71]]])
    review = build_review(bundle, [60, 69], 1, 2, through_pause=True)
    assert review['pause_endpoint'] == {
        'measure': 1, 'attack': 2, 'partial_measure': True, 'partial_attack': True,
    }
    assert review['matched_count'] == 2
    assert review['missing_count'] == 0


def play(recorder, pitches):
    for pitch in pitches:
        recorder.receive(mido.Message('note_on', note=pitch, velocity=70))
        recorder.receive(mido.Message('note_on', note=pitch, velocity=0))


def test_manual_range_and_correction_snapshot_are_separate_from_learning(tmp_path, monkeypatch):
    monkeypatch.setattr(LearningSource, 'status', lambda self, bundle: (True, 'Synthetic edition'))
    app = create_app(tmp_path, hardware=False)
    store = app.state.store
    bundle = lesson()
    profile = load_profile(store, bundle)
    profile['corrections'] = [
        {'note_id': 'm6:s2:g21:n0', 'action': 'replace', 'pitch': 63, 'measure': 6}
    ]
    profile['variants'] = [
        {'note_id': 'm6:s2:g20:n0', 'action': 'omit', 'pitch': 40, 'measure': 6}
    ]
    save_profile(store, bundle, profile)
    original_profile = store.query('SELECT * FROM learning_profiles')

    base = '/api/score-certification/e25-1'
    with TestClient(app) as client:
        assert client.get('/api/score-certification/n9-1').status_code == 404
        assert client.post(base + '/start', json={'start_measure': 7, 'end_measure': 6}).status_code == 400
        response = client.post(base + '/start', json={
            'start_measure': 6, 'end_measure': 6, 'include_corrections': True,
        })
        assert response.status_code == 200, response.text
        take = response.json()['takes'][0]
        ident = take['id']
        assert take['correction_count'] == 1
        assert client.get('/api/status').json()['certification_piece_id'] == 'e25-1'
        assert client.post('/api/record/start').status_code == 400
        assert client.post('/api/learning/e25-1/start').status_code == 400
        pitches = [
            note['pitch'] for _, notes in written_attacks(
                {**bundle, 'measures': [m for m in bundle['measures'] if m['number'] == 6]},
                profile['corrections'],
            ) for note in reversed(notes)
        ]
        play(app.state.recorder, pitches)
        for _ in range(30):
            live = client.get(f'{base}/{ident}/live').json()
            if live['played_count'] == len(pitches):
                break
            time.sleep(0.02)
        assert live == {'played_count': len(pitches), 'recent': pitches[-8:]}
        assert client.post(f'{base}/{ident}/finish').json()['takes'][0]['status'] == 'saved'
        result = client.get(f'{base}/{ident}/review').json()
        assert [m['number'] for m in result['measures']] == [6]
        assert result['matched_count'] == len(pitches)
        assert result['missing_count'] == result['extra_count'] == 0
        assert client.get(f'/api/sessions/{ident}/midi').content.startswith(b'MThd')
        assert client.get('/api/sessions').json() == []
        assert client.get('/api/recordings/library').json()['sessions'] == []
        assert store.query('SELECT * FROM learning_attempts') == []
        assert store.query('SELECT * FROM learning_profiles') == original_profile

    with TestClient(create_app(tmp_path, hardware=False)) as client:
        assert client.get(f'{base}/{ident}/review').json() == result
        assert client.get(base).json()['takes'][0]['id'] == ident


def test_pause_and_external_stop_have_distinct_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr(LearningSource, 'status', lambda self, bundle: (True, 'Synthetic edition'))
    app = create_app(tmp_path, hardware=False)
    base = '/api/score-certification/e25-1'
    with TestClient(app) as client:
        ident = client.post(base + '/start').json()['takes'][0]['id']
        play(app.state.recorder, [75])
        assert client.post(f'{base}/{ident}/pause').json()['takes'][0]['through_pause']
        result = client.get(f'{base}/{ident}/review').json()
        assert result['pause_endpoint'] == {'measure': 0, 'attack': 1, 'partial_measure': False, 'partial_attack': False}
        assert len(result['measures']) == 1
        assert result['missing_count'] == 0
        assert client.post(f'{base}/{ident}/finish').json()['takes'][0]['through_pause']

        ident = client.post(base + '/start').json()['takes'][0]['id']
        assert client.post('/api/record/stop').json()['id'] == ident
        assert client.get(base).json()['takes'][0]['status'] == 'interrupted'
        assert client.get(f'{base}/{ident}/review').status_code == 400
        assert client.get(f'/api/sessions/{ident}/midi').status_code == 200


def test_interrupted_take_is_retained_on_startup(tmp_path, monkeypatch):
    monkeypatch.setattr(LearningSource, 'status', lambda self, bundle: (True, 'Synthetic edition'))
    app = create_app(tmp_path, hardware=False)
    base = '/api/score-certification/e25-1'
    with TestClient(app) as client:
        ident = client.post(base + '/start').json()['takes'][0]['id']
        play(app.state.recorder, [75])
    with TestClient(create_app(tmp_path, hardware=False)) as client:
        take = client.get(base).json()['takes'][0]
        assert take['status'] == 'interrupted'
        assert client.get(f'/api/sessions/{ident}/midi').status_code == 200
