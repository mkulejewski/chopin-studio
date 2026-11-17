import copy

from chopin.analysis_selection import reference_identity
from chopin.performance_quality import quality, source_annotations


def evidence(pitch_score=100, *, jitter=0, dynamics=True, rubato=False, quality_label='provisional'):
    notes = [dict(pitch=60+i%12,onset=i,duration=.5,measure=i//5+1,staff=1,part=0,voice='1',
                  dynamic='p' if i<50 else 'f') for i in range(100)]
    reference = dict(id='reference',piece_id='n9-1',quality=quality_label,edition='Synthetic',notes=notes)
    comparison = []
    clock = 0
    for i,note in enumerate(notes):
        wrong = i < 100-pitch_score
        played_pitch = note['pitch']+1 if wrong else note['pitch']
        comparison.append(dict(measure=note['measure'],beat=i,time=clock,expected=[note['pitch']],
                               observed=[played_pitch],score_notes=[dict(note)],
                               played_notes=[dict(pitch=played_pitch,velocity=(60 if i<50 or not dynamics else 80))]))
        clock += (.2*(1+.03*(i%5))*(1+(i//5)*.02) if rubato else .2) * (1+jitter*(1 if i%2 else -1))
    result = dict(reference_id=reference['id'],reference_revision=reference_identity(reference).revision,
                  notes=100,matched_pitch_count=pitch_score,note_comparison=comparison,
                  assessment=dict(capture_ok=True),match=dict(confidence=.84,query_coverage=1,
                  reference_start=0,reference_end=100,pairs=[(i,i) for i in range(100)]))
    return result, reference


def test_ranking_combines_notes_timing_and_written_dynamic_contrasts():
    controlled, reference = evidence(95)
    erratic, _ = evidence(100,jitter=.65,dynamics=False)
    best = quality(controlled,reference)
    other = quality(erratic,reference)
    assert best['status'] == other['status'] == 'available'
    assert best['score'] > other['score']
    assert best['components']['notes'] < other['components']['notes']
    assert best['components']['timing'] > other['components']['timing']
    assert best['components']['dynamics'] > other['components']['dynamics']


def test_smooth_rubato_and_different_measure_tempos_do_not_lose_timing_score():
    straight, reference = evidence()
    rubato, _ = evidence(rubato=True)
    assert quality(straight,reference)['components']['timing'] == 100
    assert quality(rubato,reference)['components']['timing'] > 99


def test_missing_dynamics_or_stale_partial_or_unhealthy_evidence_has_no_score():
    base,reference = evidence()
    for kind in ('dynamics','stale','partial','capture'):
        result = copy.deepcopy(base)
        if kind=='dynamics':
            for p in result['note_comparison']: p['score_notes'][0].pop('dynamic')
        elif kind=='stale': result['reference_revision'] = 'old'
        elif kind=='partial': result['match']['reference_end'] = 50
        else: result['assessment']['capture_ok'] = False
        assert quality(result,reference)['score'] is None


def test_native_dynamic_annotations_fill_only_missing_source_labels():
    result,reference = evidence()
    for p in result['note_comparison']: p['score_notes'][0].pop('dynamic')
    annotations = [dict(measure=1,beat=0,staff=1,dynamic='p'),dict(measure=11,beat=0,staff=1,dynamic='f')]
    assert quality(result,reference,annotations)['components']['dynamics'] > 99


def test_fermata_measures_are_exempt_from_timing_ranking():
    result,reference = evidence()
    for p in result['note_comparison'][:5]: p['time'] *= 5 if p['beat']>2 else 1
    assert quality(result,reference,timing_exempt={1})['components']['timing'] == 100


def test_whole_piece_pitch_denominator_includes_unmatched_reference_notes():
    result,reference = evidence()
    result['matched_pitch_count']=80
    assert quality(result,reference)['components']['notes'] == 80


def test_source_exemptions_follow_pickup_ordinals_and_require_valid_notation(tmp_path):
    path=tmp_path/'score.musicxml'
    path.write_text('<score-partwise><part><measure number="0"><note><notations><fermata/></notations></note></measure>'
                    '<measure number="1"><direction><direction-type><words>rit.</words></direction-type></direction></measure>'
                    '</part></score-partwise>')
    stat=path.stat()
    annotations,exempt=source_annotations(str(path),stat.st_mtime_ns,stat.st_size)
    assert annotations == [] and exempt == {1,2}
    path.write_text('<not-valid-xml')
    stat=path.stat()
    try:
        source_annotations(str(path),stat.st_mtime_ns,stat.st_size)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid source must not silently supply timing exemptions')


def test_reviewed_cadenza_exemption_requires_the_exact_derived_score(tmp_path):
    import hashlib
    import json
    path=tmp_path/'score.musicxml'
    path.write_text('<score-partwise><part><measure number="1"/><measure number="2"/></part></score-partwise>')
    sidecar=path.with_suffix('.review.json')
    sidecar.write_text(json.dumps({'derived_musicxml_sha256':'different score','timing_exempt_measure_ordinals':[2]}))
    stat=path.stat();source_annotations.cache_clear()
    assert source_annotations(str(path),stat.st_mtime_ns,stat.st_size)[1]==set()
    sidecar.write_text(json.dumps({'status':'model-reviewed','open_issues':[],'derived_musicxml_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'timing_exempt_measure_ordinals':[2]}))
    source_annotations.cache_clear()
    assert source_annotations(str(path),stat.st_mtime_ns,stat.st_size)[1]=={2}
