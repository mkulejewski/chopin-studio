import copy
import hashlib
import json
import time
from collections import Counter
from fractions import Fraction

import mido
import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.learning import Learning, evaluate, lesson, reference_groups, stages
from chopin.store import Store


def attacks(bundle, start, end, variants=()):
    groups = reference_groups(bundle, start, end, variants)
    # Independent chronological traversal, with one physical attack per unison.
    return [pitch for _, pitch in sorted({(g['position'], n['pitch']) for staff in groups for g in staff for n in g['notes']})]


def play(recorder, pitches):
    for pitch in pitches:
        recorder.receive(mido.Message('note_on', note=pitch, velocity=64))
        recorder.receive(mido.Message('note_off', note=pitch, velocity=0))


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(Learning, 'source_status', lambda self: (True, 'Synthetic test edition'))
    return create_app(tmp_path, hardware=False)


def configure(client, **changes):
    config = {'visible': 1, 'hidden': 1, 'connections': 1, 'auto_continue': False, 'auto_finish': False, **changes}
    result = client.put('/api/learning/e25-1', json={'config': config})
    assert result.status_code == 200, result.text
    return result.json()


def complete(client, app, pitches=None):
    snap = client.post('/api/learning/e25-1/start').json()
    target = snap['target']
    play(app.state.recorder, attacks(lesson(), target['start'], target['end'], snap['profile']['variants']) if pitches is None else pitches)
    response = client.post('/api/learning/e25-1/finish')
    assert response.status_code == 200, response.text
    return response.json()


def test_bundle_complete_numbering_counts_and_documented_corrections():
    b = lesson()
    assert [m['number'] for m in b['measures']] == list(range(50))
    assert b['analysis_status'] == 'model-reviewed'
    assert len(b['chunks']) == 35
    assert [m for c in b['chunks'] for m in range(c['start'], c['end']+1)] == list(range(50))
    assert b['source']['reference_sha256'] == '81c15b3e01ab1db8074974cf2b3c1df351d97fbf4345324e45931ea18c8b64d1'
    assert len(b['corrections']) == 29
    notes = reference_groups(b, 0, 49)
    assert len(attacks(b, 0, 49)) == 2209
    # Hand-checked scan landmarks, independent of the XML builder's correction loop.
    def pitches(staff, measure):
        return [n['pitch'] for g in notes[staff-1] if g['position'][0] == measure for n in g['notes']]
    assert pitches(1, 0) == [75]  # Eb5 pickup, lower staff rests.
    assert pitches(2, 0) == []
    assert pitches(2, 15)[15] == pitches(2, 15)[21] == 62  # D4 natural.
    assert pitches(2, 16)[-6:] == [36, 43, 48, 55, 48, 43]
    assert pitches(1, 22)[9] == 62
    assert pitches(1, 22)[19] == pitches(1, 22)[22] == 67
    assert pitches(2, 22)[20] == pitches(2, 22)[22] == 55
    for measure in (23, 24):
        assert pitches(1, measure)[3] == pitches(1, measure)[21] == 64
        assert pitches(1, measure)[9] == 62
        assert pitches(2, measure)[15] == pitches(2, measure)[21] == 62
    assert pitches(2, 23)[9] == 59
    assert pitches(1, 25)[3] == pitches(1, 25)[9] == 64
    assert pitches(1, 25)[21] == 68
    assert [pitches(2, 25)[i] for i in (2, 4, 8, 10)] == [57]*4
    assert pitches(2, 25)[18] == 44
    assert pitches(1, 33)[12] == 81
    assert pitches(1, 34)[15] == 69
    assert pitches(1, 48) == [68, 92, 87, 80, 72, 63]
    assert pitches(2, 48) == [56, 60, 51, 44, 39]
    assert pitches(1, 49) == [68, 60]
    assert pitches(2, 49) == [51, 44, 32]
    assert len({n['id'] for staff in notes for g in staff for n in g['notes']}) == sum(len(g['notes']) for staff in notes for g in staff)


@pytest.mark.parametrize('start,end', [(0, 2), (15, 16), (17, 21), (22, 25), (26, 35), (36, 43), (44, 49), (0, 49)])
def test_whole_target_accepts_all_attacks_and_rejects_omissions_restarts_extras(start, end):
    b = lesson()
    expected = attacks(b, start, end)
    target = {'start': start, 'end': end}
    assert evaluate(b, target, expected)['passed']
    for bad in (expected[1:], expected[:-1], expected[:20]+expected, expected[:9]+[1]+expected[9:]):
        assert not evaluate(b, target, bad)['passed']
    wrong = list(expected)
    wrong[len(wrong)//2] = 115
    assert not evaluate(b, target, wrong)['passed']


def test_pitch_only_partial_order_rolled_chords_repeats_and_shared_unisons():
    b = {'measures': [{'number': 1, 'staves': [
        [['0', [60, 64]], ['1', [67]], ['2', [67]]],
        [['0', [48]], ['1', [55]], ['2', [67]]]
    ]}]}
    target = {'start': 1, 'end': 1}
    # No timestamps are passed to the evaluator: pauses and rubato cannot affect it.
    assert evaluate(b, target, [64, 48, 60, 55, 67, 67])['passed']
    assert not evaluate(b, target, [64, 48, 60, 55, 67])['passed']
    assert not evaluate(b, target, [64, 48, 60, 55, 67, 67, 67])['passed']
    assert not evaluate(b, target, [67, 64, 48, 60, 55, 67])['passed']


def test_final_trill_only_accepts_local_pitch_alternatives():
    b = lesson()
    group = reference_groups(b, 48, 49)
    expected = attacks(b, 48, 49)
    # Insert optional lead-in before the required main Eb2.
    index = expected.index(39)
    expanded = expected[:index]+[38, 39, 38, 39, 38]+expected[index:]
    assert evaluate(b, {'start': 48, 'end': 49}, expanded)['passed']
    expanded[index] = 40
    assert not evaluate(b, {'start': 48, 'end': 49}, expanded)['passed']
    assert not evaluate(b, {'start': 0, 'end': 2}, [38]+attacks(b, 0, 2))['passed']


def test_stages_connect_sections_and_end_with_whole_piece():
    plan = stages(lesson()['chunks'])
    assert plan[0]['start'] == 0 and plan[0]['end'] == 2 and plan[0]['kind'] == 'visible'
    assert plan[1]['kind'] == 'hidden'
    assert plan[4]['kind'] == 'connection' and plan[4]['start'] == 0 and plan[4]['end'] == 4
    assert plan[-1]['kind'] == 'cumulative' and (plan[-1]['start'], plan[-1]['end']) == (0, 49)
    assert len({t['id'] for t in plan}) == len(plan)


def test_midi_only_advancement_and_durable_resume(app):
    with TestClient(app) as client:
        configure(client)
        result = complete(client, app)
        assert result['target']['kind'] == 'hidden'
        assert result['history'][0]['result']['passed']
        sid = result['history'][0]['session_id']
        assert client.get('/api/sessions/'+sid+'/midi').status_code == 200
        assert not (app.state.store.root/'sessions'/sid/'microphone.json').exists()
        result = complete(client, app)
        assert result['target']['start'] == 3 and result['target']['kind'] == 'visible'
        root = app.state.store.root
    # A new process loads the saved stage rather than starting again or auto-recording.
    second = create_app(root, hardware=False)
    with TestClient(second) as client:
        result = client.get('/api/learning/e25-1').json()
        assert result['target']['start'] == 3 and result['progress']['completed'] == 2
        assert result['active'] is None and result['pending_at'] is None
        assert len(result['history']) == 2


def test_consecutive_passes_peek_failure_and_no_retroactive_pass(app):
    with TestClient(app) as client:
        configure(client, visible=2)
        assert complete(client, app)['profile']['streak'] == 1
        result = complete(client, app, attacks(lesson(), 0, 2)[:-1])
        assert result['profile']['streak'] == 0
        complete(client, app)
        assert complete(client, app)['target']['kind'] == 'hidden'
        client.post('/api/learning/e25-1/start')
        client.post('/api/learning/e25-1/peek')
        play(app.state.recorder, attacks(lesson(), 0, 2))
        result = client.post('/api/learning/e25-1/finish').json()
        assert result['history'][0]['result']['assisted'] and not result['history'][0]['result']['passed']
        assert result['target']['kind'] == 'hidden'
        assert complete(client, app)['target']['start'] == 3


def test_variants_are_occurrence_specific_revision_bound_and_revocable(app):
    with TestClient(app) as client:
        configure(client)
        result = complete(client, app)
        expected = reference_groups(lesson(), 0, 2)[0][1]['notes'][0]
        variant = {'note_id': expected['id'], 'action': 'omit', 'pitch': 60, 'reason': 'Hand span reduction'}
        result = client.post('/api/learning/e25-1/variants', json=variant).json()
        assert result['profile']['stage_index'] == 0  # Recheck changed chunk.
        assert result['history'][0]['result']['passed']  # Old evidence retained.
        reduced = attacks(lesson(), 0, 2, result['profile']['variants'])
        assert len(reduced) == len(attacks(lesson(), 0, 2))-1
        assert complete(client, app, reduced)['history'][0]['result']['passed']
        result = client.post('/api/learning/e25-1/variants', json={**variant, 'action': 'revoke'}).json()
        assert result['profile']['variants'] == []
        assert not complete(client, app, reduced)['history'][0]['result']['passed']
        replacement = {**variant, 'action': 'replace', 'pitch': 85}
        result = client.post('/api/learning/e25-1/variants', json=replacement).json()
        assert complete(client, app, attacks(lesson(), 0, 2, result['profile']['variants']))['history'][0]['result']['passed']
        assert client.post('/api/learning/e25-1/variants', json={**variant, 'note_id': 'nonexistent'}).status_code == 400
        assert client.post('/api/learning/e25-1/variants', json={**variant, 'reason': ''}).status_code == 422


def test_chunk_edits_validate_coverage_and_preserve_attempts(app):
    with TestClient(app) as client:
        current = configure(client)
        complete(client, app)
        config = current['profile']['config']
        assert client.put('/api/learning/e25-1', json={'config': config, 'chunks': [{'start': 1, 'end': 49}]}).status_code == 400
        assert client.put('/api/learning/e25-1', json={'config': config, 'chunks': [{'start': 0, 'end': 49}]}).status_code == 400
        chunks = copy.deepcopy(current['profile']['chunks'])
        chunks[:1] = [{**chunks[0], 'start': 0, 'end': 0}, {**chunks[0], 'start': 1, 'end': 2}]
        result = client.put('/api/learning/e25-1', json={'config': config, 'chunks': chunks})
        assert result.status_code == 200
        assert result.json()['profile']['stage_index'] == 0
        assert len(result.json()['history']) == 1
        assert result.json()['target']['end'] == 0
        client.post('/api/learning/e25-1/start')
        assert client.put('/api/learning/e25-1', json={'config': config}).status_code == 400
        assert client.post('/api/learning/e25-1/start').status_code == 400
        result = client.post('/api/learning/e25-1/pause').json()
        assert result['history'][0]['result']['aborted']
        assert result['profile']['stage_index'] == 0


def test_capture_loss_and_lost_frontend_do_not_advance(app):
    with TestClient(app) as client:
        configure(client)
        client.post('/api/learning/e25-1/start')
        play(app.state.recorder, attacks(lesson(), 0, 2))
        app.state.recorder.mark('capture_loss', {'lost_events_total': 1})
        result = client.post('/api/learning/e25-1/finish').json()
        assert not result['history'][0]['result']['capture_ok']
        assert result['profile']['stage_index'] == 0
        client.post('/api/learning/e25-1/start')
        app.state.learning.last_frontend = time.monotonic()-20
        app.state.learning.tick()
        result = client.get('/api/learning/e25-1').json()
        assert not result['active'] and result['history'][0]['result']['aborted']


def test_auto_finish_release_gate_and_auto_continue(app):
    with TestClient(app) as client:
        configure(client, auto_finish=True, auto_continue=True)
        client.post('/api/learning/e25-1/start')
        play(app.state.recorder, attacks(lesson(), 0, 2))
        deadline = time.monotonic()+3
        while app.state.learning.completion_at is None and time.monotonic() < deadline:
            time.sleep(.03)
            app.state.learning.tick()
        assert app.state.learning.completion_at is not None
        app.state.learning.completion_at -= 2
        app.state.learning.tick()
        snap = app.state.learning.snapshot()
        assert snap['target']['kind'] == 'hidden' and snap['pending_at']
        app.state.learning.pending = time.time()-1
        app.state.learning.tick()
        assert app.state.learning.active['target']['kind'] == 'hidden'
        result = client.post('/api/learning/e25-1/pause').json()
        assert result['pending_at'] is None


def test_source_hash_gate_unknown_lessons_and_history_survives_midi_deletion(tmp_path):
    app = create_app(tmp_path, hardware=False)
    with TestClient(app) as client:
        assert not client.get('/api/learning/e25-1').json()['ready']
        assert client.post('/api/learning/e25-1/start').status_code == 400
        assert client.get('/api/learning/n9-1').status_code == 404
        path = tmp_path/'scores'/'other.pdf'
        path.write_bytes(b'%PDF-not-the-reviewed-source')
        app.state.store.execute("UPDATE volumes SET filename='other.pdf' WHERE id='etudes'")
        snap = client.get('/api/learning/e25-1').json()
        assert not snap['ready'] and 'differs' in snap['source_notice']
        assert client.get('/api/learning/e25-1/reference').json()['revision'] == lesson()['revision']


def test_repetition_setting_edit_does_not_reset_earlier_progress(app):
    with TestClient(app) as client:
        state = configure(client)
        state = complete(client, app)
        assert state['profile']['stage_index'] == 1
        # Browser sends the unchanged ranges together with settings.
        response = client.put('/api/learning/e25-1', json={
            'config': {**state['profile']['config'], 'hidden': 4},
            'chunks': state['profile']['chunks']})
        assert response.status_code == 200
        assert response.json()['profile']['stage_index'] == 1
        assert response.json()['profile']['config']['hidden'] == 4


def test_delete_learning_midi_preserves_result_and_stops_generic_practice_assessment(app):
    from chopin.retention import delete_session
    with TestClient(app) as client:
        configure(client)
        state = complete(client, app)
        sid = state['history'][0]['session_id']
        assert app.state.store.query('SELECT source FROM sessions WHERE id=?', (sid,))[0]['source'] == 'learning'
        assert not app.state.store.query('SELECT * FROM analyses WHERE session_id=?', (sid,))
        delete_session(app.state.store, sid)
        state = client.get('/api/learning/e25-1').json()
        assert state['history'][0]['session_id'] is None
        assert state['history'][0]['result']['passed']
        assert state['profile']['stage_index'] == 1


def test_generic_stop_pauses_learning_instead_of_awarding_a_pass(app):
    with TestClient(app) as client:
        configure(client)
        client.post('/api/learning/e25-1/start')
        play(app.state.recorder, attacks(lesson(), 0, 2))
        assert client.post('/api/record/stop').status_code == 200
        result = client.get('/api/learning/e25-1').json()
        assert result['profile']['stage_index'] == 0
        assert result['history'][0]['result']['aborted']
        assert result['active'] is None


def test_provisional_model_proposal_cannot_become_a_trusted_lesson(tmp_path, monkeypatch):
    import chopin.learning as module
    b = copy.deepcopy(lesson())
    b['analysis_status'] = 'provisional-algorithmic'
    monkeypatch.setattr(module, 'lesson', lambda: b)
    app = create_app(tmp_path, hardware=False)
    with TestClient(app) as client:
        result = client.get('/api/learning/e25-1').json()
        assert not result['ready'] and 'provisional' in result['source_notice']
        assert client.post('/api/learning/e25-1/start').status_code == 400


def test_memory_judgement_restores_three_take_streak_without_changing_pitch_evidence(app):
    with TestClient(app) as client:
        configure(client, visible=3)
        assert complete(client, app)['profile']['streak'] == 1
        assert complete(client, app)['profile']['streak'] == 2
        played = attacks(lesson(), 0, 2)
        failed = complete(client, app, played[:10]+[1]+played[10:])
        assert failed['profile']['streak'] == 0
        attempt = failed['history'][0]
        original_errors = attempt['result']['errors']
        result = client.post(f"/api/learning/e25-1/attempts/{attempt['id']}/accept")
        assert result.status_code == 200
        state = result.json()
        assert state['target']['kind'] == 'hidden' and state['profile']['stage_index'] == 1
        assert state['profile']['streak'] == 0
        evidence = state['history'][0]['result']
        assert evidence['manual_accepted'] and not evidence['passed']
        assert evidence['errors'] == original_errors
        assert state['profile']['variants'] == []
        again = client.post(f"/api/learning/e25-1/attempts/{attempt['id']}/accept").json()
        assert again['profile']['stage_index'] == 1
        assert again['profile']['streak'] == 0


def test_failed_take_stays_available_for_memory_judgement_and_rejects_stale_changes(app):
    with TestClient(app) as client:
        configure(client, visible=3, auto_continue=True)
        failure = complete(client, app, attacks(lesson(), 0, 2)[:-1])
        assert failure['pending_at'] is None
        attempt = failure['history'][0]['id']
        state = client.post(f'/api/learning/e25-1/attempts/{attempt}/accept').json()
        assert state['profile']['streak'] == 1 and state['pending_at']
        client.post('/api/learning/e25-1/pause')
        failure = complete(client, app, attacks(lesson(), 0, 2)[:-1])
        ident = failure['history'][0]['id']
        client.post('/api/learning/e25-1/restart')
        assert client.post(f'/api/learning/e25-1/attempts/{ident}/accept').status_code == 400


def test_assisted_or_incomplete_capture_cannot_be_mistaken_for_accidental_key_judgement(app):
    with TestClient(app) as client:
        configure(client)
        complete(client, app)
        client.post('/api/learning/e25-1/start')
        client.post('/api/learning/e25-1/peek')
        play(app.state.recorder, attacks(lesson(), 0, 2))
        state = client.post('/api/learning/e25-1/finish').json()
        assert client.post(f"/api/learning/e25-1/attempts/{state['history'][0]['id']}/accept").status_code == 400
        client.post('/api/learning/e25-1/start')
        play(app.state.recorder, attacks(lesson(), 0, 2))
        app.state.recorder.mark('capture_loss', {'lost_events_total': 1})
        state = client.post('/api/learning/e25-1/finish').json()
        assert client.post(f"/api/learning/e25-1/attempts/{state['history'][0]['id']}/accept").status_code == 400


def test_self_assessed_next_stage_without_required_repetitions_is_saved_and_idempotent(app):
    with TestClient(app) as client:
        state = configure(client, visible=3, hidden=3)
        request = {'stage_id': state['target']['id'], 'generation': state['profile']['generation']}
        state = client.post('/api/learning/e25-1/advance', json=request).json()
        assert state['target']['kind'] == 'hidden' and state['profile']['stage_index'] == 1
        assert state['profile']['streak'] == 0 and not state['history']
        assert state['profile']['manual_advances'][0]['stage_id'] == request['stage_id']
        assert client.get('/api/learning/e25-1').json()['profile']['stage_index'] == 1
        assert client.post('/api/learning/e25-1/advance', json=request).json()['profile']['stage_index'] == 1
        client.post('/api/learning/e25-1/restart')
        assert client.post('/api/learning/e25-1/advance', json=request).status_code == 400


def test_next_stage_saves_current_take_as_paused_without_claiming_pitch_success(app):
    with TestClient(app) as client:
        configure(client, visible=3)
        state = client.post('/api/learning/e25-1/start').json()
        play(app.state.recorder, [75, 1, 2])
        state = client.post('/api/learning/e25-1/advance', json={
            'stage_id': state['target']['id'], 'generation': state['profile']['generation']}).json()
        assert state['active'] is None and app.state.recorder.active is None
        assert state['target']['kind'] == 'hidden'
        assert state['history'][0]['result']['aborted']
        assert not state['history'][0]['result']['passed']
        assert state['profile']['manual_advances']


def test_restart_take_is_immediate_unevaluated_and_preserves_correct_streak(app, monkeypatch):
    import chopin.learning as module
    with TestClient(app) as client:
        configure(client, visible=3)
        assert complete(client, app)['profile']['streak'] == 1
        state = client.post('/api/learning/e25-1/start').json()
        original = state['active']
        play(app.state.recorder, [1, 2, 3])
        with monkeypatch.context() as patch:
            def no_evaluation(*args, **kwargs):
                raise AssertionError('Restart must not run the evaluator')
            patch.setattr(module, 'evaluate', no_evaluation)
            response = client.post('/api/learning/e25-1/restart-take', json={'attempt_id': original['id']})
        assert response.status_code == 200
        state = response.json()
        assert state['active']['id'] != original['id']
        assert state['active']['target']['id'] == original['target']['id']
        assert state['profile']['streak'] == 1 and state['profile']['stage_index'] == 0
        assert state['pending_at'] is None
        restarted = next(h for h in state['history'] if h['id'] == original['id'])
        assert restarted['result']['restarted'] and restarted['result']['errors'] == []
        assert not restarted['result']['passed']
        assert client.get(f"/api/sessions/{original['session_id']}/midi").status_code == 200
        retry = client.post('/api/learning/e25-1/restart-take', json={'attempt_id': original['id']}).json()
        assert retry['active']['id'] == state['active']['id']
        assert retry['profile']['streak'] == 1
        play(app.state.recorder, attacks(lesson(), 0, 2))
        assert client.post('/api/learning/e25-1/finish').json()['profile']['streak'] == 2


def test_restarting_a_hidden_take_keeps_stage_and_streak_and_clears_peek(app):
    with TestClient(app) as client:
        configure(client, hidden=3)
        complete(client, app)
        assert complete(client, app)['profile']['streak'] == 1
        state = client.post('/api/learning/e25-1/start').json()
        client.post('/api/learning/e25-1/peek')
        state = client.post('/api/learning/e25-1/restart-take', json={'attempt_id': state['active']['id']}).json()
        assert state['active']['target']['kind'] == 'hidden'
        assert not state['active']['assisted']
        assert state['profile']['streak'] == 1 and state['profile']['stage_index'] == 1


def test_review_covers_learned_prefix_and_never_changes_learning_progress(app):
    with TestClient(app) as client:
        configure(client)
        complete(client, app)
        complete(client, app)
        configure(client, visible=3, auto_continue=True)
        baseline = complete(client, app)
        assert baseline['target']['start'] == 3 and baseline['profile']['streak'] == 1
        profile = baseline['profile']
        state = client.post('/api/learning/e25-1/review').json()
        assert state['active']['target']['kind'] == 'review'
        assert (state['target']['start'], state['target']['end']) == (0, 2)
        assert state['learning_target'] == baseline['target']
        play(app.state.recorder, attacks(lesson(), 0, 2))
        state = client.post('/api/learning/e25-1/finish').json()
        assert state['history'][0]['result']['passed']
        assert state['profile'] == profile and state['pending_at'] is None
        assert state['review']['active']
        state = client.post('/api/learning/e25-1/review/leave').json()
        assert not state['review']['active'] and state['target'] == baseline['target']
        assert state['profile'] == profile


def test_review_failure_restart_pause_and_current_chunk_are_neutral(app):
    with TestClient(app) as client:
        configure(client)
        complete(client, app)
        complete(client, app)
        baseline = client.get('/api/learning/e25-1').json()['profile']
        state = client.post('/api/learning/e25-1/review', json={'include_current': True}).json()
        assert state['target']['end'] == 4
        play(app.state.recorder, [1, 2, 3])
        state = client.post('/api/learning/e25-1/finish').json()
        assert not state['history'][0]['result']['passed']
        assert state['profile'] == baseline
        assert client.post(f"/api/learning/e25-1/attempts/{state['history'][0]['id']}/accept").status_code == 400
        assert client.post('/api/learning/e25-1/advance', json={
            'stage_id': state['target']['id'], 'generation': baseline['generation']}).status_code == 400
        state = client.post('/api/learning/e25-1/start').json()
        state = client.post('/api/learning/e25-1/restart-take', json={'attempt_id': state['active']['id']}).json()
        assert state['active']['target']['kind'] == 'review' and state['profile'] == baseline
        state = client.post('/api/learning/e25-1/review/leave').json()
        assert state['active'] is None and state['profile'] == baseline
        assert state['target']['kind'] == 'visible' and state['target']['start'] == 3


def test_review_initial_chunk_opt_in_and_review_after_full_completion(app):
    with TestClient(app) as client:
        configure(client)
        assert client.post('/api/learning/e25-1/review').status_code == 400
        state = client.post('/api/learning/e25-1/review', json={'include_current': True}).json()
        assert state['target']['end'] == 2
        assert client.post('/api/learning/e25-1/review').status_code == 400  # Do not replace an active take.
        client.post('/api/learning/e25-1/review/leave')
        controller = app.state.learning
        profile = controller.profile()
        sequence = stages(profile['chunks'])
        profile.update(stage_index=len(sequence), completed=[s['id'] for s in sequence])
        controller.save(profile)
        state = client.post('/api/learning/e25-1/review').json()
        assert state['target']['end'] == 49 and state['learning_target'] is None
        play(app.state.recorder, attacks(lesson(), 0, 49))
        state = client.post('/api/learning/e25-1/finish').json()
        assert state['history'][0]['result']['passed'] and state['profile'] == profile
        assert client.post('/api/learning/e25-1/review/leave').json()['target'] is None


def test_sessions_expose_authoritative_learning_piece_without_rewriting_takes(app):
    with TestClient(app) as client:
        configure(client)
        first = complete(client, app)
        sid = first['history'][0]['session_id']
        client.post('/api/learning/e25-1/review', json={'include_current': True})
        client.post('/api/learning/e25-1/finish')
        client.post('/api/learning/e25-1/review/leave')
        rows = client.get('/api/sessions').json()
        assert len(rows) == 2
        assert all(r['learning_piece_id'] == 'e25-1' for r in rows)
        assert all(r['learning_piece_title'] == 'Étude “Aeolian Harp”' for r in rows)
        assert next(r for r in rows if r['id'] == sid)['events'] > 0
        assert client.get(f'/api/sessions/{sid}/midi').status_code == 200
        assert client.get('/api/learning/e25-1').json()['profile'] == first['profile']
