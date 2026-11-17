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
from chopin.learning import Learning, PitchPrefixMatcher, evaluate, lesson, reference_groups, stages
from chopin.store import Store


def attacks(bundle, start, end, variants=(), hand='both'):
    groups = reference_groups(bundle, start, end, variants, hand)
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


@pytest.mark.parametrize(('piece', 'stem'), [
    ('e25-1', 'aeolian_harp_etude_op25_no1'),
    ('p53', 'heroic_polonaise_op53'),
    ('n15-1', 'nocturne_op15_no1'),
])
def test_reference_downloads_use_descriptive_piece_filenames(app, piece, stem):
    with TestClient(app) as client:
        assert client.post('/api/learning/selection', json={'piece_id': piece}).status_code == 200
        for format, suffix in [('json', 'learning.json'), ('musicxml', 'attacks.musicxml')]:
            response = client.get(f'/api/learning/{piece}/reference', params={'format': format})
            assert response.status_code == 200
            assert response.headers['content-disposition'] == (
                f'attachment; filename="{stem}_paderewski_{suffix}"'
            )
            if format == 'json':
                assert response.json()['piece_id'] == piece
            else:
                assert 'score-partwise' in response.text


def complete(client, app, pitches=None):
    snap = client.post('/api/learning/e25-1/start').json()
    target = snap['active']['target']
    play(app.state.recorder, attacks(lesson(), target['start'], target['end'], target['variants'], target.get('hand', 'both')) if pitches is None else pitches)
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
    assert len(b['corrections']) == 31
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
        saved_profile = result['profile']
        root = app.state.store.root
    # A new process opens cumulative review without changing the saved stage or recording.
    second = create_app(root, hardware=False)
    with TestClient(second) as client:
        result = client.get('/api/learning/e25-1').json()
        assert result['learning_target']['start'] == 3 and result['progress']['completed'] == 2
        assert result['review']['active'] and result['target']['kind'] == 'review'
        assert (result['target']['start'], result['target']['end']) == (0, 2)
        assert result['profile'] == saved_profile
        assert result['active'] is None and result['pending_at'] is None
        assert len(result['history']) == 2
        assert client.get('/api/learning/e25-1').json()['target'] == result['target']
        resumed = client.post('/api/learning/e25-1/review/leave').json()
        assert resumed['profile'] == result['profile']
        assert not resumed['review']['active'] and resumed['target']['start'] == 3
        assert not client.get('/api/learning/e25-1').json()['review']['active']


@pytest.mark.parametrize('learned_chunks', [0, 2, 35])
def test_startup_review_range_and_explicit_start_preserve_saved_progress(app, learned_chunks):
    learning = app.state.learning
    profile = learning.profile()
    sequence = stages(profile['chunks'])
    hidden = [i for i, target in enumerate(sequence) if target['kind'] == 'hidden']
    profile['stage_index'] = hidden[learned_chunks-1]+1 if learned_chunks else 0
    if learned_chunks == len(profile['chunks']):
        profile['stage_index'] = len(sequence)
    profile['completed'] = [t['id'] for t in sequence[:profile['stage_index']]]
    profile['streak'] = 2
    learning.save(profile)
    with TestClient(app) as client:
        state = client.get('/api/learning/e25-1').json()
        assert state['profile'] == profile
        assert state['active'] is None and state['pending_at'] is None
        assert app.state.recorder.active is None
        if not learned_chunks:
            assert not state['review']['active']
            assert state['target']['kind'] == 'visible'
            return
        assert state['review']['active']
        assert state['target']['start'] == 0
        assert state['target']['end'] == profile['chunks'][learned_chunks-1]['end']
        started = client.post('/api/learning/e25-1/start').json()
        assert started['active']['target']['kind'] == 'review'
        assert started['profile'] == profile
        resumed = client.post('/api/learning/e25-1/review/leave').json()
        assert not resumed['review']['active'] and resumed['profile'] == profile
        assert resumed['target'] == state['learning_target']
        assert not client.get('/api/learning/e25-1').json()['review']['active']


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


@pytest.mark.parametrize('hand', ['both', 'right', 'left'])
def test_restart_prefix_accepts_correct_partial_passages_and_personal_rules(hand):
    bundle = lesson()
    variants = [{'note_id': 'm0:s1:g0:n0', 'action': 'replace', 'pitch': 76}]
    target = {'start': 0, 'end': 49, 'hand': hand, 'variants': variants}
    matcher = PitchPrefixMatcher(bundle, target)
    for pitch in attacks(bundle, 0, 49, variants, hand):
        matcher.feed([pitch])
        assert not matcher.mistaken
    assert not matcher.uncertain
    matcher.feed([1])
    assert matcher.mistaken


def test_restart_prefix_allows_rolled_chords_hand_order_and_local_trill():
    bundle = {'measures': [{'number': 48, 'staves': [
        [['0', [60, 64]], ['1', [67]]],
        [['0', [48]], ['3', [39]]],
    ]}]}
    bundle['ornaments'] = [{'measure': 48, 'staff': 2, 'pitches': [38, 39]}]
    target = {'start': 48, 'end': 48}
    matcher = PitchPrefixMatcher(bundle, target)
    matcher.feed([64, 48, 60, 38, 39, 38, 39, 67])
    assert not matcher.mistaken and not matcher.uncertain
    matcher = PitchPrefixMatcher(bundle, target)
    matcher.feed([67])  # A later note played before its preceding chord.
    assert matcher.mistaken
    matcher = PitchPrefixMatcher(bundle, target)
    matcher.feed([60, 67])  # The other chord note has been skipped.
    assert matcher.mistaken


def test_restart_prefix_declines_ambiguous_paths_over_limit():
    bundle = {'measures': [{'number': 1, 'staves': [
        [['0', [60]], ['1', [60]]], [['0', [48]], ['2', [60]]],
    ]}]}
    matcher = PitchPrefixMatcher(bundle, {'start': 1, 'end': 1}, max_states=1)
    matcher.feed([48, 60])
    assert matcher.uncertain
    matcher.feed([1])
    assert not matcher.mistaken


def tick_after_journal(app):
    deadline = time.monotonic() + 2
    while not app.state.recorder.queue.empty() and time.monotonic() < deadline:
        time.sleep(.01)
    # The writer can have dequeued its last item without writing it yet.
    time.sleep(.03)
    app.state.learning.tick()


@pytest.mark.parametrize('kind', ['visible', 'hidden', 'review'])
def test_auto_restart_waits_for_release_saves_midi_and_preserves_assignment(app, kind):
    with TestClient(app) as client:
        configure(client, visible=3, hidden=3, auto_restart_on_mistake=True)
        controller, recorder = app.state.learning, app.state.recorder
        profile = controller.profile()
        profile['streak'] = 1
        profile['stage_index'] = 1 if kind == 'hidden' else 0
        controller.save(profile)
        if kind == 'review':
            controller.review_target = controller.review_assignment(profile, 0, 2)
        state = client.post('/api/learning/e25-1/start').json()
        original = state['active']
        before = state['profile']
        play(recorder, attacks(lesson(), 0, 2)[:3])
        tick_after_journal(app)
        assert controller.active['id'] == original['id']  # Incomplete is fine.
        recorder.receive(mido.Message('note_on', note=1, velocity=64))
        tick_after_journal(app)
        assert controller.active['id'] == original['id']  # Held keys stay in this take.
        recorder.receive(mido.Message('note_off', note=1))
        deadline = time.monotonic() + 2
        while controller.active['id'] == original['id'] and time.monotonic() < deadline:
            tick_after_journal(app)
        state = controller.snapshot()
        assert state['active']['id'] != original['id']
        assert state['active']['target'] == original['target']
        assert state['profile'] == before and state['pending_at'] is None
        old = next(h for h in state['history'] if h['id'] == original['id'])
        assert old['status'] == 'restarted'
        assert old['result']['auto_restarted'] and old['result']['capture_ok']
        assert not old['result']['passed'] and old['result']['errors'] == []
        assert client.get(f"/api/sessions/{original['session_id']}/midi").status_code == 200
        observed, _ = controller._observed(original['session_id'])
        assert observed == attacks(lesson(), 0, 2)[:3] + [1]
        next_id = state['active']['id']
        tick_after_journal(app)
        assert controller.active['id'] == next_id  # No repeated restart from stale notes.
        play(recorder, attacks(lesson(), 0, 2))
        state = client.post('/api/learning/e25-1/finish').json()
        assert state['history'][0]['result']['passed']
        assert state['profile']['streak'] == (1 if kind == 'review' else 2)


def test_auto_restart_is_opt_in_and_old_profiles_default_to_disabled(app):
    with TestClient(app) as client:
        state = configure(client)
        assert state['profile']['config']['auto_restart_on_mistake'] is False
        profile = app.state.learning.profile()
        profile['config'].pop('auto_restart_on_mistake')
        app.state.learning.save(profile)
        assert client.get('/api/learning/e25-1').json()['profile']['config']['auto_restart_on_mistake'] is False
        original = client.post('/api/learning/e25-1/start').json()['active']
        play(app.state.recorder, [1])
        tick_after_journal(app)
        assert app.state.learning.active['id'] == original['id']
        client.post('/api/learning/e25-1/pause')
        state = configure(client, auto_restart_on_mistake=True)
        assert state['profile']['config']['auto_restart_on_mistake'] is True
        assert Learning(app.state.store, app.state.recorder).profile()['config']['auto_restart_on_mistake'] is True


@pytest.mark.parametrize('fault', ['recorder', 'journal', 'edition'])
def test_auto_restart_declines_capture_faults_and_unreviewed_edition(app, monkeypatch, fault):
    with TestClient(app) as client:
        configure(client, auto_restart_on_mistake=True)
        controller, recorder = app.state.learning, app.state.recorder
        original = client.post('/api/learning/e25-1/start').json()['active']
        if fault == 'recorder':
            recorder.error = 'Synthetic capture fault'
        elif fault == 'journal':
            recorder.mark('capture_loss', {'lost_events_total': 1})
        else:
            monkeypatch.setattr(Learning, 'source_status', lambda self: (False, 'Edition changed'))
        play(recorder, [1])
        if fault == 'edition':
            with pytest.raises(ValueError, match='Edition changed'):
                tick_after_journal(app)
        else:
            tick_after_journal(app)
        assert controller.active['id'] == original['id']


def test_auto_restart_does_not_open_new_take_after_save_reports_capture_fault(app, monkeypatch):
    with TestClient(app) as client:
        configure(client, auto_restart_on_mistake=True)
        controller, recorder = app.state.learning, app.state.recorder
        original = client.post('/api/learning/e25-1/start').json()['active']
        stop = recorder.stop
        def failed_capture():
            recorder.error = 'Synthetic fault found while saving'
            return stop()
        monkeypatch.setattr(recorder, 'stop', failed_capture)
        play(recorder, [1])
        tick_after_journal(app)
        state = controller.snapshot()
        assert state['active'] is None and recorder.active is None
        assert state['history'][0]['id'] == original['id']
        assert not state['history'][0]['result']['capture_ok']
        assert client.get(f"/api/sessions/{original['session_id']}/midi").status_code == 200


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


def test_restarting_a_hidden_take_keeps_stage_streak_and_peek_assistance(app):
    with TestClient(app) as client:
        configure(client, hidden=3)
        complete(client, app)
        assert complete(client, app)['profile']['streak'] == 1
        state = client.post('/api/learning/e25-1/start').json()
        client.post('/api/learning/e25-1/peek')
        state = client.post('/api/learning/e25-1/restart-take', json={'attempt_id': state['active']['id']}).json()
        assert state['active']['target']['kind'] == 'hidden'
        assert state['active']['assisted']
        assert state['profile']['streak'] == 1 and state['profile']['stage_index'] == 1
        play(app.state.recorder, attacks(lesson(), state['target']['start'], state['target']['end']))
        finished = client.post('/api/learning/e25-1/finish').json()
        assert finished['history'][0]['result']['assisted']
        assert not finished['history'][0]['result']['passed']
        assert finished['profile']['stage_index'] == 1
        fresh = client.post('/api/learning/e25-1/start').json()
        assert not fresh['active']['assisted']


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


def test_live_staves_incremental_matches_expected_chunk_and_no_future_missing(app):
    with TestClient(app) as client:
        configure(client)
        state = client.post('/api/learning/e25-1/start').json()
        ident = state['active']['id']
        url = f'/api/learning/e25-1/attempts/{ident}/staves'
        initial = client.get(url).json()
        assert initial['expected_visible'] and initial['played_attacks'] == 0
        assert all(not g['live_missing'] for g in initial['groups'])
        assert {g['measure'] for g in initial['groups']} == {0}
        notes = attacks(lesson(), 0, 2)
        play(app.state.recorder, notes[:24])
        deadline = time.monotonic()+3
        while time.monotonic() < deadline:
            projection = client.get(url).json()
            if projection['played_attacks'] == 24:
                break
            time.sleep(.02)
        assert projection['played_attacks'] == 24
        assert sum(len(g['observed']) for g in projection['groups']) > 0
        assert app.state.learning.staff_matcher.count == 24
        assert client.get(url).json()['played_attacks'] == 24
        assert app.state.learning.staff_matcher.count == 24  # Polling cannot duplicate input.
        play(app.state.recorder, notes[24:])
        result = client.post('/api/learning/e25-1/finish').json()
        assert result['history'][0]['result']['passed']
        final = client.get(url+'?first_measure=0').json()
        assert not final['active'] and final['expected_visible']
        assert all(not g['live_missing'] for g in final['groups'])
        assert final['played_attacks'] == len(notes)
        assert client.get(url+'?first_measure=49').json()['last_measure'] == 2
        assert {g['measure'] for g in client.get(url+'?first_measure=1').json()['groups']} == {1}
        assert projection['first_measure'] == projection['last_measure']


def test_hidden_live_staves_keep_engraving_but_do_not_disclose_unplayed_notes(app):
    with TestClient(app) as client:
        configure(client)
        complete(client, app)
        state = client.post('/api/learning/e25-1/start').json()
        ident = state['active']['id']
        play(app.state.recorder, [70, 1, 100])
        url = f'/api/learning/e25-1/attempts/{ident}/staves'
        time.sleep(.05)
        hidden = client.get(url).json()
        assert not hidden['expected_visible']
        assert hidden['played_attacks'] == 3
        assert all(g['expected'] == [] for g in hidden['groups'])
        assert all(g['observed'] and g['live_neutral'] == g['observed'] for g in hidden['groups'])
        assert all(sorted(n['pitch'] for n in g['score_notes']) == g['observed'] for g in hidden['groups'])
        # Like the visible view, hidden notation follows the latest measure.
        assert {p for g in hidden['groups'] for p in g['observed']} <= {70, 1, 100}
        assert any(100 in g['observed'] for g in hidden['groups'])
        assert all(not g.get('live_missing') for g in hidden['groups'])
        client.post('/api/learning/e25-1/peek')
        assert client.get(url).json()['expected_visible']
        assert not client.get(url+'?show_expected=false').json()['expected_visible']
        client.post('/api/learning/e25-1/finish')
        assert client.get(url).json()['expected_visible']
        assert client.get('/api/learning/e25-1/attempts/missing/staves').status_code == 400


def test_live_staff_matcher_marks_missing_and_extra_pitches_in_correct_staves():
    from chopin.learning_staves import LiveStaffMatcher
    target = {'start': 0, 'end': 2}
    notes = attacks(lesson(), 0, 2)
    matcher = LiveStaffMatcher(lesson(), target)
    matcher.feed(notes[:12])
    matcher.feed([1]+notes[13:])
    windows = [matcher.comparison(finished=True, first_measure=m) for m in range(3)]
    assert all({g['measure'] for g in window['groups']} == {m} for m, window in enumerate(windows))
    groups = [g for window in windows for g in window['groups']]
    assert any(1 in g['observed'] for g in groups)
    assert any(g['live_missing'] for g in groups)
    assert all(n['display_staff'] in (1, 2) for g in groups for n in g['score_notes'])
    baseline = LiveStaffMatcher(lesson(), target)
    baseline.feed(notes)
    assert all(not g['live_missing'] for g in baseline.comparison(True, 0)['groups'])


def test_completed_chunk_map_review_targets_selected_chunk_and_preserves_interrupted_streak(app):
    with TestClient(app) as client:
        configure(client)
        for _ in range(4):
            complete(client, app)
        configure(client, connections=3)
        before = complete(client, app)
        assert before['target']['kind'] == 'connection' and before['profile']['streak'] == 1
        active = client.post('/api/learning/e25-1/start').json()['active']
        assert client.post('/api/learning/e25-1/review', json={'chunk_index': 2}).status_code == 400
        assert client.get('/api/learning/e25-1').json()['active']['id'] == active['id']
        play(app.state.recorder, [1, 2])
        review = client.post('/api/learning/e25-1/review', json={'chunk_index': 1}).json()
        assert review['target']['kind'] == 'review'
        assert (review['target']['start'], review['target']['end']) == (3, 4)
        assert review['profile'] == before['profile']
        abandoned = next(h for h in review['history'] if h['id'] == active['id'])
        assert abandoned['result']['suspended_for_review'] and not abandoned['result']['passed']
        restored = client.post('/api/learning/e25-1/review/leave').json()
        assert restored['target'] == before['target'] and restored['profile'] == before['profile']


def test_measure_six_restores_e_flat_after_earlier_e_natural():
    from chopin.learning_staves import LiveStaffMatcher
    b = lesson()
    upper = b['measures'][6]['staves'][0]
    assert [upper[i][1][0] for i in (8, 11, 20, 23)] == [76, 76, 75, 75]
    target = {'start': 6, 'end': 6}
    correct = attacks(b, 6, 6)
    assert evaluate(b, target, correct)['passed']
    old = copy.deepcopy(b)
    for i in (20, 23):
        old['measures'][6]['staves'][0][i][1] = [76]
    assert not evaluate(b, target, attacks(old, 6, 6))['passed']
    matcher = LiveStaffMatcher(b, target)
    matcher.feed(correct)
    projection = matcher.comparison(True, 6)
    assert not any(g['live_missing'] for g in projection['groups'])
    spelled = [n['spelling'] for g in projection['groups'] for n in g['score_notes']]
    assert {'step': 'C', 'alter': -1, 'octave': 5} in spelled
    assert {'step': 'E', 'alter': -1, 'octave': 5} in spelled


def test_hidden_live_engraving_retains_only_sounded_score_notes_and_rhythm():
    from chopin.learning_staves import LiveStaffMatcher, played_only
    matcher = LiveStaffMatcher(lesson(), {'start': 0, 'end': 2})
    assert played_only(matcher.comparison())['groups'] == []
    matcher.feed(attacks(lesson(), 0, 2)[:12])
    visible = matcher.comparison()
    hidden = played_only(visible)
    assert hidden['groups']
    for group in hidden['groups']:
        source = next(g for g in visible['groups'] if g['beat'] == group['beat'])
        assert not group['expected'] and not group['live_missing']
        assert {n['pitch'] for n in group['score_notes']} == set(group['observed'])
        for note in group['score_notes']:
            assert note in source['score_notes']
    assert any(n['duration'] < 1 for g in hidden['groups'] for n in g['score_notes'])


def test_reference_correction_is_separate_durable_and_frozen_in_old_takes(app):
    with TestClient(app) as client:
        configure(client)
        base = '/api/learning/e25-1'
        original = lesson()['measures'][0]['staves'][0][0][1][0]
        payload = {'note_id': 'm0:s1:g0:n0', 'replacement': 'E5', 'reason': 'Printed note checked by pianist'}
        response = client.post(base+'/corrections', json=payload)
        assert response.status_code == 200, response.text
        profile = response.json()['profile']
        assert profile['variants'] == []
        assert profile['corrections'][0]['pitch'] == 76
        assert profile['corrections'][0]['spelling'] == {'step': 'E', 'alter': 0, 'octave': 5}
        assert Learning(app.state.store, app.state.recorder).profile()['corrections'] == profile['corrections']
        started = client.post(base+'/start').json()
        old_target = copy.deepcopy(started['active']['target'])
        assert client.post(base+'/corrections', json=payload).status_code == 400
        projection = client.get(base+f"/attempts/{started['active']['id']}/staves").json()
        assert projection['groups'][0]['expected'] == [76]
        play(app.state.recorder, attacks(lesson(), 0, 2, old_target['variants']))
        finished = client.post(base+'/finish').json()
        assert finished['history'][0]['result']['passed']
        assert finished['history'][0]['result']['correction_count'] == 1
        assert finished['history'][0]['result']['variant_count'] == 0
        take_id = finished['history'][0]['id']
        undone = client.post(base+'/corrections', json={**payload, 'action': 'revoke'}).json()
        assert undone['profile']['corrections'] == []
        assert undone['profile']['stage_index'] == 0
        old_take = next(row for row in undone['history'] if row['id'] == take_id)
        assert old_take['target'] == old_target
        assert old_take['result']['passed']
        assert original == 75 == lesson()['measures'][0]['staves'][0][0][1][0]


def test_reference_correction_validates_note_and_does_not_overwrite_personal_rule(app):
    with TestClient(app) as client:
        base = '/api/learning/e25-1'
        payload = {'note_id': 'm0:s1:g0:n0', 'replacement': 'Cb5', 'reason': 'Test spelling'}
        assert client.post(base+'/corrections', json={**payload, 'replacement': 'garbage'}).status_code == 400
        assert client.post(base+'/corrections', json={**payload, 'replacement': 'G#9'}).status_code == 400
        assert client.post(base+'/corrections', json={**payload, 'note_id': 'unknown'}).status_code == 400
        fixed = client.post(base+'/corrections', json=payload).json()['profile']['corrections'][0]
        assert fixed['pitch'] == 71 and fixed['spelling'] == {'step': 'C', 'alter': -1, 'octave': 5}
        client.post(base+'/corrections', json={**payload, 'action': 'revoke'})
        assert client.post(base+'/variants', json={'note_id': payload['note_id'], 'action': 'omit', 'reason': 'My adaptation'}).status_code == 200
        assert client.post(base+'/corrections', json=payload).status_code == 400
        assert len(client.get(base).json()['profile']['variants']) == 1


def test_learning_pedal_starts_and_restarts_without_losing_streak_or_replaying_commands(app):
    with TestClient(app) as client:
        configure(client, visible=3)
        state = complete(client, app)
        assert state['profile']['streak'] == 1
        base = '/api/learning/e25-1'
        owner = 'learning-pedal-test'
        assert client.post(base+'/pedal-control', json={'owner': owner, 'enabled': True}).status_code == 200
        def pedal():
            now = time.monotonic()
            app.state.recorder._pedal(mido.Message('control_change', control=66, value=127), now-.12)
            app.state.recorder._pedal(mido.Message('control_change', control=66, value=0), now)
            return client.get(base+f'/pedal-commands?owner={owner}').json()['commands'][-1]['id']
        command = pedal()
        body = {'owner': owner, 'command_id': command, 'attempt_id': None, 'target_id': state['target']['id']}
        started = client.post(base+'/pedal-repeat', json=body).json()
        first = started['active']['id']
        assert started['profile']['streak'] == 1
        assert client.post(base+'/pedal-repeat', json=body).json()['active']['id'] == first
        body.update(command_id=pedal(), attempt_id=first)
        repeated = client.post(base+'/pedal-repeat', json=body).json()
        assert repeated['active']['id'] != first
        assert repeated['profile']['streak'] == 1
        assert repeated['target'] == state['target']
        previous = next(row for row in repeated['history'] if row['id'] == first)
        assert previous['result']['restarted'] and previous['result']['aborted']
        assert not app.state.recorder.page_commands
        body.update(command_id=pedal(), attempt_id=repeated['active']['id'])
        client.post(base+'/pedal-control', json={'owner': owner, 'enabled': False})
        assert client.post(base+'/pedal-repeat', json=body).json()['active']['id'] == repeated['active']['id']


@pytest.mark.parametrize('hand,expected', [('both', [48, 72, 60]), ('right', [48, 60]), ('left', [72, 60])])
def test_hand_filter_uses_staff_and_keeps_shared_unisons_in_either_single_hand(hand, expected):
    bundle = {'measures': [{'number': 1, 'staves': [
        [['0', [48]], ['1', [60]]], [['0', [72]], ['1', [60]]],
    ]}]}
    target = {'start': 1, 'end': 1, 'hand': hand}
    assert evaluate(bundle, target, expected)['passed']
    assert not evaluate(bundle, target, expected[:-1])['passed']
    assert not evaluate(bundle, target, expected+[100])['passed']
    if hand != 'both':
        assert not evaluate(bundle, {'start': 1, 'end': 1}, expected)['passed']
        groups = reference_groups(bundle, 1, 1, hand=hand)
        assert not groups[1 if hand == 'right' else 0]
        assert groups[0 if hand == 'right' else 1][-1]['notes'][0]['pitch'] == 60


@pytest.mark.parametrize('hand', ['right', 'left'])
@pytest.mark.parametrize('start,end', [(0, 2), (5, 6), (48, 49)])
def test_actual_hand_passages_match_without_missing_the_other_hand(hand, start, end):
    from chopin.learning_staves import LiveStaffMatcher
    target = {'start': start, 'end': end, 'hand': hand}
    pitches = attacks(lesson(), start, end, hand=hand)
    result = evaluate(lesson(), target, pitches)
    assert result['passed'] and result['hand'] == hand and not result['errors']
    matcher = LiveStaffMatcher(lesson(), target)
    matcher.feed(pitches)
    groups = [g for m in range(start, end+1) for g in matcher.comparison(True, m)['groups']]
    assert not any(g['live_missing'] for g in groups)
    assert all(n['staff'] == (1 if hand == 'right' else 2) for g in groups for n in g['score_notes'])


def test_both_hands_default_and_separate_streaks_and_history(app):
    with TestClient(app) as client:
        base = '/api/learning/e25-1'
        assert client.get(base).json()['profile']['hand'] == 'both'
        configure(client, visible=2)
        both = complete(client, app)
        assert both['profile']['stage_index'] == 0 and both['profile']['streak'] == 1
        right = client.put(base+'/hand', json={'hand': 'right'}).json()
        assert right['profile']['stage_index'] == 0 and right['profile']['streak'] == 0
        assert right['history'] == []
        complete(client, app)
        right = complete(client, app)
        assert right['profile']['stage_index'] == 1
        assert all(row['target']['hand'] == 'right' for row in right['history'])
        client.put(base+'/hand', json={'hand': 'left'})
        left = complete(client, app)
        assert left['profile']['stage_index'] == 0 and left['profile']['streak'] == 1
        restored = client.put(base+'/hand', json={'hand': 'both'}).json()
        assert restored['profile']['stage_index'] == both['profile']['stage_index']
        assert restored['profile']['streak'] == both['profile']['streak']
        assert restored['profile']['completed'] == both['profile']['completed']
        assert len(restored['history']) == 1 and restored['history'][0]['target']['hand'] == 'both'
        restored = client.put(base+'/hand', json={'hand': 'right'}).json()
        assert restored['profile']['stage_index'] == 1 and restored['profile']['streak'] == 0
        assert Learning(app.state.store, app.state.recorder).profile()['hand'] == 'right'
        started = client.post(base+'/start').json()
        assert started['active']['target']['hand'] == 'right'
        assert client.put(base+'/hand', json={'hand': 'left'}).status_code == 400
        assert client.put(base+'/hand', json={'hand': 'invalid'}).status_code == 422
        assert client.get(base).json()['active']['id'] == started['active']['id']


def test_both_hands_completed_stages_raise_each_hand_without_lowering_progress(app):
    with TestClient(app) as client:
        base = '/api/learning/e25-1'
        configure(client)
        # Right hand gets ahead independently; neither other mode advances.
        client.put(base+'/hand', json={'hand': 'right'})
        complete(client, app)
        right = complete(client, app)
        assert right['profile']['stage_index'] == 2
        both = client.put(base+'/hand', json={'hand': 'both'}).json()
        assert both['profile']['stage_index'] == 0
        both = complete(client, app)
        assert both['profile']['stage_index'] == 1
        assert both['profile']['hand_progress']['right']['stage_index'] == 2
        assert both['profile']['hand_progress']['left']['stage_index'] == 1
        left = client.put(base+'/hand', json={'hand': 'left'}).json()
        assert left['profile']['completed'] == both['profile']['completed']
        assert left['history'] == []  # No invented separate-hand takes.
        client.put(base+'/hand', json={'hand': 'both'})
        complete(client, app)
        both = complete(client, app)
        assert both['profile']['stage_index'] == 3
        for hand in ('right', 'left'):
            state = client.put(base+'/hand', json={'hand': hand}).json()
            assert state['profile']['stage_index'] == 3
            assert state['profile']['completed'] == both['profile']['completed']
            assert state['review']['learned_end'] is not None
            assert state['learning_target'] == both['learning_target']
        # Reloading and restarting a separate mode still respects the floor.
        reloaded = Learning(app.state.store, app.state.recorder)
        assert reloaded.profile()['stage_index'] == 3
        assert reloaded.restart()['profile']['stage_index'] == 3


@pytest.mark.parametrize('hand', ['both', 'right', 'left'])
def test_existing_profiles_inherit_both_hands_progress_on_load(app, hand):
    learning = app.state.learning
    profile = learning.profile()
    completed = [t['id'] for t in stages(profile['chunks'])[:3]]
    both = {'stage_index': 3, 'streak': 2, 'completed': completed}
    profile.update(hand=hand)
    if hand == 'both':
        profile.update(both)
    else:
        profile['hand_progress']['both'] = both
    # Simulate a saved profile from before inheritance existed.
    app.state.store.execute('INSERT OR REPLACE INTO learning_profiles VALUES(?,?,?)',
                           ('e25-1', lesson()['revision'], json.dumps(profile)))
    restored = learning.snapshot()['profile']
    for mode in ('right', 'left'):
        progress = restored if hand == mode else restored['hand_progress'][mode]
        assert progress['stage_index'] == 3
        assert progress['completed'] == completed
        assert progress['streak'] == 0


def test_both_hands_self_assessed_advancement_is_inherited(app):
    learning = app.state.learning
    state = learning.snapshot()
    advanced = learning.advance_stage(state['target']['id'], state['profile']['generation'])
    for hand in ('right', 'left'):
        progress = advanced['profile']['hand_progress'][hand]
        assert progress['stage_index'] == 1
        assert progress['completed'] == advanced['profile']['completed']
        assert 'manual_advances' not in progress


def test_legacy_profile_defaults_to_both_without_resetting_progress(app):
    learning = app.state.learning
    state = learning.profile()
    state.pop('hand')
    state.pop('hand_progress')
    state.update(stage_index=3, streak=2)
    learning.save(state)
    migrated = learning.profile()
    assert migrated['hand'] == 'both'
    assert migrated['stage_index'] == 3 and migrated['streak'] == 2


def test_reference_fix_invalidates_only_affected_hands_including_inactive_progress(app):
    learning = app.state.learning
    state = learning.profile()
    state.update(hand='right', stage_index=5, streak=2)
    state['hand_progress'] = {hand: {'stage_index': 5, 'streak': 2, 'completed': []} for hand in ('both', 'left')}
    learning.save(state)
    fixed = learning.correct_note('m0:s1:g0:n0', 'E5', 'Reference correction')['profile']
    assert fixed['stage_index'] == 0 and fixed['streak'] == 0
    assert fixed['hand_progress']['both']['stage_index'] == 0
    assert fixed['hand_progress']['left']['stage_index'] == 5
    assert fixed['hand_progress']['left']['streak'] == 2


def test_left_hand_shared_unison_can_have_its_own_reference_correction(app, monkeypatch):
    bundle = copy.deepcopy(lesson())
    bundle['measures'][0]['staves'][1] = [['0', [75]]]
    bundle['measures'][0]['spellings'][1] = [[{'step': 'E', 'alter': -1, 'octave': 5}]]
    monkeypatch.setattr('chopin.learning.lesson', lambda: bundle)
    shared_id = 'm0:s2:g0:n0'
    assert not reference_groups(bundle, 0, 0)[1]  # Both hands merge the shared physical key.
    assert reference_groups(bundle, 0, 0, hand='left')[1][0]['notes'][0]['id'] == shared_id
    state = app.state.learning.correct_note(shared_id, 'E4', 'Check this lower-staff occurrence')
    assert state['profile']['corrections'][0]['note_id'] == shared_id
    assert state['profile']['corrections'][0]['staff'] == 2


def test_routine_changes_reset_all_hand_streaks_without_losing_positions(app):
    learning = app.state.learning
    state = learning.profile()
    state.update(stage_index=3, streak=2)
    state['hand_progress'] = {'left': {'stage_index': 5, 'streak': 2, 'completed': []}}
    learning.save(state)
    updated = learning.configure({**state['config'], 'visible': 4})['profile']
    assert updated['stage_index'] == 3 and updated['streak'] == 0
    assert updated['hand_progress']['left']['stage_index'] == 5
    assert updated['hand_progress']['left']['streak'] == 0


@pytest.mark.parametrize('count', [1, 5, 6])
def test_expanding_review_builds_backward_and_preserves_progress(app, count):
    learning = app.state.learning
    profile = learning.profile()
    sequence = stages(profile['chunks'], lesson())
    completed = [t for t in sequence if t['chunk'] < count]
    profile.update(completed=[t['id'] for t in completed], stage_index=len(completed), streak=0)
    learning.save(profile)
    with TestClient(app) as client:
        baseline = client.get('/api/learning/e25-1').json()['profile']
        state = client.post('/api/learning/e25-1/review', json={'mode': 'expanding'}).json()
        for width in range(2, count + 2, 2):
            size = min(width, count)
            assert state['target']['chunk_count'] == size
            assert state['target']['start'] == profile['chunks'][count-size]['start']
            assert state['target']['end'] == profile['chunks'][count-1]['end']
            assert state['profile'] == baseline
            # Failure and peeking must not widen the assignment.
            target = state['target']
            play(app.state.recorder, [1])
            state = client.post('/api/learning/e25-1/finish').json()
            assert state['target'] == target
            state = client.post('/api/learning/e25-1/start').json()
            client.post('/api/learning/e25-1/peek')
            play(app.state.recorder, attacks(lesson(), target['start'], target['end']))
            state = client.post('/api/learning/e25-1/finish').json()
            assert state['target'] == target
            state = client.post('/api/learning/e25-1/start').json()
            play(app.state.recorder, attacks(lesson(), target['start'], target['end']))
            state = client.post('/api/learning/e25-1/finish').json()
            assert state['history'][0]['result']['passed']
            assert state['profile'] == baseline and state['active'] is None and state['pending_at'] is None
            if size < count:
                state = client.post('/api/learning/e25-1/start').json()
        assert state['target']['review_complete']
        state = client.post('/api/learning/e25-1/review/leave').json()
        assert not state['review']['active'] and state['profile'] == baseline
        assert client.post('/api/learning/e25-1/review', json={'mode':'expanding', 'include_current':True}).status_code == 400
        client.post('/api/learning/selection', json={'piece_id':'n15-1'})
        assert client.post('/api/learning/n15-1/review', json={'mode':'expanding'}).status_code == 400
