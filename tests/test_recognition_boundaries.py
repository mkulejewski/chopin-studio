"""Piece identity on both sides of a rest determines short silence boundaries."""
import json
import random
import pytest

from chopin.organisation import Recognizer, candidate_ranges, opening_restarts, organise
from chopin.store import Store
from chopin.segmentation import performance_restarts, likely_complete


def references():
    rng=random.Random(321)
    return [dict(id=pid,piece_id=pid,quality='verified',
                 notes=[dict(pitch=rng.randrange(lo,hi),onset=i,duration=.4,measure=i//4+1)
                        for i in range(96)])
            for pid,lo,hi in [('n9-2',40,65),('n-b49',66,90)]]


def test_short_silence_between_different_works_preserves_entire_coda():
    refs=references();left=[{**n,'onset':n['onset']*.5} for n in refs[0]['notes']]
    # A held last chord followed by 13 seconds of silence is below the old 20s threshold.
    left[-1]['duration']=6
    end=left[-1]['onset']+6
    right=[{**n,'onset':end+13+n['onset']*.5} for n in refs[1]['notes']]
    ranges=candidate_ranges(left+right,right[-1]['onset']+1,20,Recognizer(refs))
    assert len(ranges)==2
    assert ranges[0][1]>=end
    assert ranges[1][0]==right[0]['onset']


def test_short_rest_inside_same_piece_does_not_split():
    ref=references()[0]
    played=[{**n,'onset':n['onset']*.5+(10 if i>=48 else 0)} for i,n in enumerate(ref['notes'])]
    assert len(candidate_ranges(played,played[-1]['onset']+1,20,Recognizer([ref])))==1


def test_opening_restarts_split_short_aborts_and_export_only_final_take(tmp_path):
    import numpy as np
    import soundfile as sf
    from chopin.microphone import RATE, export_audio, write_metadata
    from chopin.retention import eligibility
    store=Store(tmp_path);ref=references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'test.xml','local','test','test','verified',json.dumps(ref['notes']),'today'))
    # Two aborted openings, including one too short for whole-piece recognition.
    # No silence boundary separates these runs.
    sequence=ref['notes'][:18]+ref['notes'][:6]+ref['notes']
    played=[{**n,'onset':1+i*.5,'duration':.2} for i,n in enumerate(sequence)]
    folder=tmp_path/'sessions'/'restarts';folder.mkdir()
    events=[]
    for n in played:
        events.extend([dict(t=n['onset'],message=dict(type='note_on',note=n['pitch'],velocity=80)),
                       dict(t=n['onset']+.2,message=dict(type='note_off',note=n['pitch']))])
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute("INSERT INTO sessions(id,name,started,status,duration,events) VALUES('restarts','test','today','saved',62,240)")
    samples=(np.arange(62*RATE)%30000).astype('int16')
    sf.write(folder/'microphone.flac',samples,RATE,subtype='PCM_16')
    write_metadata(folder,{'offset_seconds':0,'filename':'microphone.flac','duration':62})
    rows=organise(store,'restarts')
    assert [r['start'] for r in rows]==[1,10,13]
    assert [r['kind'] for r in rows]==['partial','partial','complete']
    assert [r['complete'] for r in rows]==[0,0,1]
    assert all(r['piece_id']==ref['piece_id'] for r in rows)
    assert [eligibility(store,r,{})[0] for r in rows]==[False,False,True]
    clip=export_audio(store,rows[-1])
    decoded,rate=sf.read(clip,dtype='int16')
    np.testing.assert_array_equal(decoded,samples[13*RATE:round(rows[-1]['end']*RATE)])
    assert rate==RATE and sf.info(folder/'microphone.flac').frames==len(samples)
    store.db.close()


def test_written_opening_repeat_and_later_theme_return_are_not_aborted_starts():
    ref=references()[0]
    # A written repeat near the opening is ambiguous and must stay intact.
    written={**ref,'notes':ref['notes'][:18]+ref['notes'][:6]+ref['notes'][18:]}
    written['notes']=[{**n,'onset':i} for i,n in enumerate(written['notes'])]
    rec=Recognizer([written]);played=written['notes']
    assert opening_restarts(played,rec,rec.match(played))==[]
    # A return after substantial score progress is not an aborted introduction.
    rec=Recognizer([ref]);sequence=ref['notes'][:72]+ref['notes'][:24]
    played=[{**n,'onset':i} for i,n in enumerate(sequence)]
    assert opening_restarts(played,rec,rec.match(played))==[]


def test_separate_opening_evidence_and_keep_flag_survive_rebuild(tmp_path):
    store=Store(tmp_path);ref=references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'test.xml','local','test','test','verified',json.dumps(ref['notes']),'today'))
    folder=tmp_path/'sessions'/'test';folder.mkdir()
    events=[]
    for n in ref['notes']:
        t=n['onset']*.5
        events.extend([dict(t=t,message=dict(type='note_on',note=n['pitch'],velocity=80)),
                       dict(t=t+.2,message=dict(type='note_off',note=n['pitch']))])
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute("INSERT INTO sessions(id,name,started,status,duration,events) VALUES('test','test','today','saved',49,192)")
    first=organise(store,'test')[0]
    assert first['first_measure']==1
    assert json.loads(first['details'])['match']['opening_evidence']['first_measure']==1
    store.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(first['id'],))
    store.execute("UPDATE segments SET kind='full_exercise',complete=1 WHERE id=?",(first['id'],))
    rebuilt=organise(store,'test',True)[0]
    assert rebuilt['kind']=='full_exercise' and rebuilt['complete']==1
    assert store.query('SELECT choice FROM recording_choices WHERE segment_id=?',(rebuilt['id'],))[0]['choice']=='keep'
    store.db.close()


def test_recorded_open_score_context_only_fills_unknown_identity(tmp_path):
    store=Store(tmp_path)
    ref=references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'test.xml','local','test','test','verified',json.dumps(ref['notes']),'today'))
    for session,played,changed,expected in [
        ('unknown',[dict(pitch=100,onset=i,duration=.2) for i in range(12)],False,'n72-1'),
        ('other',ref['notes'],False,'n9-2'),
        ('mixed',[dict(pitch=100,onset=i,duration=.2) for i in range(12)],True,None),
    ]:
        folder=tmp_path/'sessions'/session;folder.mkdir()
        events=[dict(t=0,kind='piece_context',piece_id='n72-1')]
        if changed:events.append(dict(t=5,kind='piece_context',piece_id='n9-1'))
        for n in played:
            t=n['onset']+.5
            events.extend([dict(t=t,message=dict(type='note_on',note=n['pitch'],velocity=80)),
                           dict(t=t+.2,message=dict(type='note_off',note=n['pitch']))])
        events.sort(key=lambda e:e['t'])
        (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
        store.execute('INSERT INTO sessions(id,name,started,status,duration,events) VALUES(?,?,?,?,?,?)',
                      (session,session,'today','saved',100,len(events)))
        row=organise(store,session)[0]
        assert row['piece_id']==expected
        if session=='unknown':
            assert not row['complete'] and row['confidence']==0
            assert json.loads(row['details'])['match']['assumed']
            from chopin.retention import eligibility
            assert not eligibility(store,row,{'match':{'confidence':1}})[0]
    store.db.close()


def test_full_takes_and_later_retries_returning_to_opening_are_separate():
    ref = references()[0]
    rec = Recognizer([ref])
    runs = [ref['notes'], ref['notes'][:40], ref['notes']]
    played = [{**note, 'onset': i*.5, 'duration': .2}
              for i, note in enumerate(sum(runs, []))]
    cuts = performance_restarts(played, rec, rec.match(played))
    assert cuts == [48, 68]
    points = [0, *cuts, played[-1]['onset']+1]
    complete = [likely_complete(rec.match([n for n in played if a<=n['onset']<b]), rec.references[0]['groups'])
                for a,b in zip(points, points[1:])]
    assert complete == [True, False, True]


def test_complete_take_before_a_restart_is_not_marked_aborted(tmp_path):
    store = Store(tmp_path)
    ref = references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'synthetic.xml','local','synthetic','test','verified',json.dumps(ref['notes']),'today'))
    folder = tmp_path/'sessions'/'double'
    folder.mkdir()
    events = []
    for i,note in enumerate(ref['notes']*2):
        events.extend([dict(t=i*.5,message=dict(type='note_on',note=note['pitch'],velocity=80)),
                       dict(t=i*.5+.2,message=dict(type='note_off',note=note['pitch']))])
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute("INSERT INTO sessions(id,name,started,status,duration,events) VALUES('double','test','today','saved',97,384)")
    rows = organise(store,'double')
    assert len(rows) == 2
    assert all(row['kind']=='complete' and row['complete'] for row in rows)
    assert json.loads(rows[0]['details'])['ended_by_restart']
    assert not json.loads(rows[0]['details'])['aborted_by_restart']
    assert rows[0]['group_id'] == rows[1]['group_id'] is not None
    store.db.close()


def test_written_theme_return_is_not_a_new_performance():
    ref = references()[0]
    repeated = {**ref, 'notes':ref['notes'][:72]+ref['notes'][:24]+ref['notes'][72:]}
    repeated['notes'] = [{**n,'onset':i} for i,n in enumerate(repeated['notes'])]
    rec = Recognizer([repeated])
    assert performance_restarts(repeated['notes'],rec,rec.match(repeated['notes'])) == []


def test_provisional_score_cap_does_not_make_different_strength_matches_tie():
    ref = references()[0]
    ref = {**ref, 'quality':'provisional'}
    other = {**ref,'id':'other','piece_id':'n9-1',
             'notes':[{**n,'pitch':n['pitch']+(1 if i%8==0 else 0)} for i,n in enumerate(ref['notes'])]}
    match = Recognizer([other,ref]).match(ref['notes'][20:52])
    assert match['piece_id'] == ref['piece_id']
    assert match['confidence'] == .84  # Assessment safeguard unchanged.
    assert match['identity_similarity'] == 1
    assert match['candidates'][1]['confidence'] == .84


def test_whole_take_alignment_preserves_ornamented_opening_and_ending():
    ref = references()[0]
    sequence = []
    for i,note in enumerate(ref['notes']):
        if i%5 == 0:
            sequence.append({**note,'pitch':100})
        sequence.append(note)
    played = [{**n,'onset':i*.3} for i,n in enumerate(sequence)]
    rec = Recognizer([ref])
    match = rec.match(played)
    assert match['alignment_method'] == 'window-supported-monotonic-span'
    assert match['reference_start'] == 0 and match['reference_end'] == 96
    assert likely_complete(match,rec.references[0]['groups'])


def test_damaged_four_note_fingerprints_search_beyond_first_eight_references():
    rng = random.Random(1729)
    refs = [dict(id=f'ref-{i}',piece_id=f'piece-{i}',quality='verified',
                 notes=[dict(pitch=rng.randrange(40,85),onset=j,duration=.2,measure=j//4+1)
                        for j in range(72)]) for i in range(20)]
    played = [dict(n) for n in refs[-1]['notes'][12:36]]
    for i,note in enumerate(played):
        if i%3 == 1:
            note['pitch'] = 100
    result = Recognizer(refs).match(played)
    assert result['piece_id'] == refs[-1]['piece_id']


def chord_reference():
    rng = random.Random(402)
    chords = [[rng.randrange(60, 85), *([rng.randrange(40, 55)] if i % 3 == 0 else [])]
              for i in range(160)]
    # A written short opening motif must not disable all later restart detection.
    chords[6:12] = [list(chord) for chord in chords[:6]]
    return dict(id='chords', piece_id='n-b49', quality='verified', notes=[
        dict(pitch=pitch, onset=i, duration=.3, measure=i//4+1)
        for i, chord in enumerate(chords) for pitch in chord])


@pytest.mark.parametrize('prior_groups', [24, 48, 160])
@pytest.mark.parametrize('bass_first', [False, True])
def test_rolled_opening_after_early_abort_or_full_take_has_exact_restart(prior_groups, bass_first):
    ref = chord_reference()
    rec = Recognizer([ref])
    rg = rec.references[0]['groups']
    restart = prior_groups * .5 + 1
    played = []
    for take, end in enumerate((prior_groups, len(rg))):
        for i, group in enumerate(rg[:end]):
            for j, pitch in enumerate(sorted(group['pitches'], reverse=not bass_first)):
                played.append(dict(pitch=pitch, duration=.15,
                                   onset=(restart if take else 0) + i*.5
                                   + (.08*j if take and i < 12 else 0)))
    rec_match = rec.match(played)
    assert performance_restarts(played, rec, rec_match) == [restart]
    prior = rec.match([n for n in played if n['onset'] < restart])
    assert likely_complete(prior, rg) == (prior_groups == 160)
    assert likely_complete(rec.match([n for n in played if n['onset'] >= restart]), rg)


def test_ornamented_written_theme_return_keeps_one_performance():
    ref = chord_reference()
    rg = Recognizer([ref]).references[0]['groups']
    written = [set(g['pitches']) for g in rg[:80] + rg[:32] + rg[80:]]
    performed = [set(pitches) for pitches in written]
    # The played return resembles the opening more than its written variant.
    changed = max(written[85])
    written[85].remove(changed)
    written[85].add(changed + 1)
    ref['notes'] = [dict(pitch=pitch, onset=i, duration=.3, measure=i//4+1)
                    for i, pitches in enumerate(written) for pitch in sorted(pitches)]
    played = [dict(pitch=pitch, onset=i*.5, duration=.2)
              for i, pitches in enumerate(performed) for pitch in sorted(pitches)]
    rec = Recognizer([ref])
    assert performance_restarts(played, rec, rec.match(played)) == []


def test_disjoint_repeated_ending_evidence_does_not_extend_partial_measure_label():
    rng = random.Random(712)
    original = [dict(pitch=rng.randrange(40, 85), onset=i, duration=.3, measure=i//4+1)
                for i in range(300)]
    reference = [dict(n) for n in original]
    for j in range(48):
        reference[200+j]['pitch'] = original[62+j]['pitch']
    reference[65]['pitch'] += 1
    match = Recognizer([dict(id='repeat', piece_id='n-b49', quality='verified',
                             notes=reference)]).match(original[:110])
    assert match['ending_evidence']['last_measure'] == 62
    assert match['reference_end'] == 110
    assert match['last_measure'] == 28


def test_rolled_restart_rebuild_preserves_capture_history_and_keep_protection(tmp_path):
    store = Store(tmp_path)
    ref = chord_reference()
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'], ref['piece_id'], 'synthetic.xml', 'local', 'synthetic',
                   'test', 'verified', json.dumps(ref['notes']), 'today'))
    rg = Recognizer([ref]).references[0]['groups']
    events = []
    for i, group in enumerate(rg[:48] + rg):
        for j, pitch in enumerate(sorted(group['pitches'], reverse=True)):
            onset = i*.5 + (.08*j if 48 <= i < 60 else 0)
            events.extend([dict(t=onset, message=dict(type='note_on', note=pitch, velocity=80)),
                           dict(t=onset+.15, message=dict(type='note_off', note=pitch))])
    events.sort(key=lambda event: event['t'])
    folder = tmp_path/'sessions'/'rolled'
    folder.mkdir()
    journal = ''.join(json.dumps(event)+'\n' for event in events)
    (folder/'events.jsonl').write_text(journal)
    original = b'immutable synthetic imported MIDI'
    (folder/'original.mid').write_bytes(original)
    duration = events[-1]['t'] + 1
    store.execute('INSERT INTO sessions(id,name,started,status,duration,events) VALUES(?,?,?,?,?,?)',
                  ('rolled', 'synthetic', 'today', 'saved', duration, len(events)))
    store.execute('INSERT INTO segments(id,session_id,start,end,piece_id,label,kind,complete,revision) VALUES(?,?,?,?,?,?,?,?,?)',
                  ('old', 'rolled', 0, duration, ref['piece_id'], 'Old unsplit take', 'complete', 1, 3))
    store.execute("INSERT INTO recording_choices(segment_id,choice) VALUES('old','keep')")
    rebuilt = organise(store, 'rolled', force=True)
    assert len(rebuilt) == 2
    assert rebuilt[0]['end'] == rebuilt[1]['start'] == 24
    assert [row['kind'] for row in rebuilt] == ['partial', 'complete']
    assert json.loads(rebuilt[0]['details'])['aborted_by_restart']
    assert json.loads(store.query('SELECT snapshot FROM segment_history')[0]['snapshot'])[0]['id'] == 'old'
    assert store.query("SELECT COUNT(*) AS n FROM recording_choices WHERE choice='keep'")[0]['n'] == 2
    assert (folder/'events.jsonl').read_text() == journal
    assert (folder/'original.mid').read_bytes() == original
    store.db.close()
