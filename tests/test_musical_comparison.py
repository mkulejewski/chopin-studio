import copy

from chopin.musical_comparison import musical_review


def passage(expected=None, actual=None):
    groups = [dict(measure=i//4+1, beat=i, time=i*.5, expected=[60,64,67], observed=[60,64,67],
                   score_notes=[dict(pitch=p,duration=1,staff=1) for p in [60,64,67]]) for i in range(11)]
    groups[5]['expected'] = expected if expected is not None else [60,64,67]
    groups[5]['observed'] = actual if actual is not None else [60,64,67]
    return groups


def judgments(groups, index=5):
    return [j for side in groups[index]['musical_context'].values() for j in side.values()]


def test_octave_redistribution_is_blue_on_both_layers():
    groups=passage(actual=[48,64,67])
    review=musical_review(groups,'verified',.99)
    assert review['red_pitch_differences']==0
    assert review['blue_pitch_differences']==2
    assert {j['reason'] for j in judgments(groups)}=={'octave_or_doubling'}


def test_reduced_chord_is_a_possible_adaptation_not_an_accepted_correct_note():
    groups=passage(actual=[60,67])
    before=copy.deepcopy(groups)
    review=musical_review(groups,'verified',.99)
    assert review['red_pitch_differences']==0
    assert judgments(groups)[0]['reason']=='possible_chord_reduction'
    assert groups[5]['expected']==before[5]['expected'] and groups[5]['observed']==before[5]['observed']
    assert 'accidental omission' in judgments(groups)[0]['explanation']


def test_unrelated_wrong_chord_is_red_only_with_verified_reference_and_context():
    groups=passage(actual=[61,65,68])
    review=musical_review(groups,'verified',.99)
    assert review['red_pitch_differences']==6
    assert {j['reason'] for j in judgments(groups)}=={'likely_wrong_chord'}
    for quality, confidence in [('provisional',.99),('verified',.7)]:
        other=passage(actual=[61,65,68])
        assert musical_review(other,quality,confidence)['red_pitch_differences']==0


def test_unrelated_substitution_between_anchors_is_likely_error():
    groups=passage(expected=[60],actual=[66])
    assert musical_review(groups,'verified',.99)['red_pitch_differences']==2
    assert {j['reason'] for j in judgments(groups)}=={'likely_wrong_pitch'}


def test_nearby_accidental_and_short_ornament_stay_blue():
    groups=passage(expected=[60],actual=[61])
    assert musical_review(groups,'verified',.99)['red_pitch_differences']==0
    assert judgments(groups)[0]['reason']=='nearby_pitch_or_variant'
    groups=passage(actual=[60,64,66,67])
    groups[5]['played_notes']=[dict(pitch=66,duration=.08)]
    assert musical_review(groups,'verified',.99)['red_pitch_differences']==0
    assert judgments(groups)[0]['reason']=='possible_ornament'


def test_missing_alignment_grace_notes_and_passage_edges_do_not_support_red():
    groups=passage(actual=[61,65,68]);groups[5]['time']=None
    assert musical_review(groups,'verified',.99)['red_pitch_differences']==0
    groups=passage(actual=[61,65,68]);groups[4]['score_notes'][0]['grace']=True
    assert musical_review(groups,'verified',.99)['red_pitch_differences']==0
    groups=passage();groups[0]['observed']=[61,65,68]
    assert musical_review(groups,'verified',.99)['red_pitch_differences']==0


def test_uniform_tempo_scaling_and_smooth_rubato_are_not_errors():
    for times in [[i*2 for i in range(11)], [0,.45,.92,1.43,1.98,2.58,3.23,3.93,4.68,5.48,6.33]]:
        groups=passage()
        for group, time in zip(groups,times):group['time']=time
        assert not musical_review(groups,'verified',.99)['timing_flags']


def test_isolated_gross_timing_change_is_blue_until_intent_can_be_checked():
    groups=passage()
    for group in groups[5:]:group['time']+=8
    review=musical_review(groups,'verified',.99)
    assert len(review['timing_flags'])==1
    assert review['timing_flags'][0]['severity']=='review'
    assert review['timing_flags'][0]['ratio']==17
    assert not review['red_pitch_differences']
