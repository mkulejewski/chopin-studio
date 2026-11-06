"""Conservative, deterministic explanations of score-relative differences.

This is an explainable triage, not a model of musical intent. Blue differences
remain differences; neither suspected adaptations nor uncertain editions are
silently forgiven. Technical pitch scores are never changed by this module.
"""
from collections import Counter
from statistics import median

VERSION = 'musical-context-v1'


def pitch_classes(pitches):
    return {p % 12 for p in pitches}


def _anchor(group):
    expected = pitch_classes(group['expected'])
    played = pitch_classes(group['observed'])
    return (group.get('time') is not None and expected and played == expected
            and not any(n.get('grace') for n in group.get('score_notes', [])))


def _supported_context(groups, index):
    # At least two good anchors on each side, without stepping over an
    # unlocated score group. Passage edges and repeat ambiguities stay blue.
    before = groups[max(0, index-3):index]
    after = groups[index+1:index+4]
    local = before+[groups[index]]+after
    times = [g.get('time') for g in local]
    continuous = (all(t is not None for t in times)
                  and all(0 < right-left <= 8 for left, right in zip(times, times[1:])))
    return (continuous and len(before) >= 2 and len(after) >= 2
            and all(g.get('time') is not None for g in before+after)
            and sum(bool(_anchor(g)) for g in before) >= 2
            and sum(bool(_anchor(g)) for g in after) >= 2)


def _timing_flags(groups):
    intervals = []
    for i, (left, right) in enumerate(zip(groups, groups[1:])):
        if not (_anchor(left) and _anchor(right)):
            continue
        beat = (right.get('beat') or 0)-(left.get('beat') or 0)
        elapsed = right['time']-left['time']
        if beat > 0 and elapsed > 0:
            intervals.append((i, elapsed/beat))
    flags = []
    for index, value in intervals:
        neighbours = [v for j, v in intervals if 0 < abs(index-j) <= 4]
        if len(neighbours) < 4:
            continue
        baseline = median(neighbours)
        # Smooth tempo changes and uniformly slower practice are deliberately
        # unflagged. Even an isolated large change may be a fermata or pause.
        if max(neighbours)/min(neighbours) <= 1.8 and (value/baseline > 4 or value/baseline < .25):
            group = groups[index+1]
            flags.append({'group_index': index+1, 'measure': group['measure'], 'time': group['time'],
                          'severity': 'review', 'reason': 'timing_discontinuity',
                          'ratio': round(value/baseline, 3),
                          'explanation': 'Large isolated timing change relative to nearby score beats. Check a pause, fermata, alignment or intentional phrasing before treating it as a rhythm error.'})
    return flags


def musical_review(groups, reference_quality, alignment_confidence):
    """Attach per-pitch reasoning to saved groups; return a separate summary."""
    counts = Counter()
    trusted = reference_quality == 'verified' and alignment_confidence >= .85
    for index, group in enumerate(groups):
        expected = set(group['expected']); played = set(group['observed'])
        missing = expected-played; extra = played-expected
        wanted_classes = pitch_classes(expected); played_classes = pitch_classes(played)
        common_classes = wanted_classes & played_classes
        neighbours = groups[max(0, index-2):index]+groups[index+1:index+3]
        nearby_classes = set().union(*(pitch_classes(g['expected']) for g in neighbours))
        grace = any(n.get('grace') for g in [group]+neighbours for n in g.get('score_notes', []))
        supported = trusted and _supported_context(groups, index)
        wrong_chord = (len(wanted_classes) >= 3 and len(played_classes) >= 3
                       and len(played_classes-wanted_classes) >= 2
                       and len(common_classes)/len(wanted_classes) <= .34)
        context = {'expected': {}, 'observed': {}}
        for side, pitches in [('expected', missing), ('observed', extra)]:
            for pitch in sorted(pitches):
                other = played if side == 'expected' else expected
                other_classes = pitch_classes(other)
                reason = 'uncertain_difference'
                explanation = 'Edition, voice allocation, alignment or performance intent may explain this difference.'
                severity = 'review'
                if pitch % 12 in other_classes:
                    reason = 'octave_or_doubling'
                    explanation = 'The same pitch class is present in another octave. Possible octave redistribution or chord doubling; intent is not inferred.'
                elif side == 'expected' and played and played_classes <= wanted_classes:
                    reason = 'possible_chord_reduction'
                    explanation = 'The played chord retains reference pitch classes while omitting this tone. Possible hand-span reduction; an accidental omission is also possible.'
                elif grace:
                    reason = 'ornament_context'
                    explanation = 'Grace-note material occurs nearby. Ornament realisation or an edition difference needs review.'
                elif group.get('time') is None:
                    reason = 'unaligned_score_group'
                    explanation = 'No recording onset was aligned here. A skipped repeat, omission or alignment error cannot be distinguished.'
                elif not trusted:
                    reason = 'unverified_reference_or_alignment'
                    explanation = 'The reference is unverified or alignment confidence is below 0.85. A strict difference cannot establish a musical error.'
                elif not supported:
                    reason = 'insufficient_local_anchors'
                    explanation = 'Too few reliable matched groups surround this difference to make a red musical judgement.'
                elif wrong_chord:
                    severity = 'error'; reason = 'likely_wrong_chord'
                    explanation = 'Several chord pitch classes differ with little harmonic overlap, between stable matched anchors in a verified reference. Likely chord error; edition or intentional reharmonisation still requires human judgement.'
                elif (side == 'observed' and pitch % 12 in nearby_classes) or (side == 'expected' and extra and pitch_classes(extra) <= nearby_classes):
                    reason = 'possible_displaced_or_edition_note'
                    explanation = 'This pitch class occurs in nearby reference material. Displacement, voicing or an edition variant remains plausible.'
                elif side == 'observed' and any(abs(n.get('duration', 1)) <= .18 and n['pitch'] == pitch for n in group.get('played_notes', [])) and expected & played:
                    reason = 'possible_ornament'
                    explanation = 'A brief extra pitch accompanies retained reference tones. Possible ornament or incidental key strike; review in context.'
                elif other and min(min((pitch-q) % 12, (q-pitch) % 12) for q in other) <= 2:
                    reason = 'nearby_pitch_or_variant'
                    explanation = 'A nearby pitch substitution may be an accidental, ornament or edition variant. It is retained for review.'
                elif extra and missing:
                    severity = 'error'; reason = 'likely_wrong_pitch'
                    explanation = 'An unrelated pitch substitutes for reference material between stable matched anchors in a verified reference. Likely pitch error; this is not proof of intent.'
                item = {'severity': severity, 'reason': reason, 'explanation': explanation}
                context[side][str(pitch)] = item
                counts[severity] += 1; counts[reason] += 1
        group['musical_context'] = context
    timing = _timing_flags(groups)
    for flag in timing:
        groups[flag['group_index']]['timing_review'] = flag
    return {'version': VERSION, 'reference_quality': reference_quality,
            'alignment_confidence': alignment_confidence,
            'red_pitch_differences': counts['error'], 'blue_pitch_differences': counts['review'],
            'reasons': dict(counts), 'timing_flags': timing,
            'notice': 'Algorithmic triage only. Blue includes plausible adaptations and uncertainty, not confirmed mistakes. Red means likely pitch/chord error under verified-reference and stable-context checks, not proof that all editions or musical intentions are excluded. Timing flags remain blue because MIDI alone cannot rule out pauses, fermatas or intentional phrasing.'}
