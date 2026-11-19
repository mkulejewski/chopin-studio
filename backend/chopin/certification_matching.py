"""Whole-score pitch alignment for a deliberate read-through in written order."""

from array import array
from collections import defaultdict

from .learning_matching import reference_groups


MAX_ATTACKS = 12000
FROM_LEFT = 65535


def written_attacks(bundle, corrections=()):
    measures = bundle['measures']
    grouped = defaultdict(dict)
    for staff in reference_groups(bundle, measures[0]['number'], measures[-1]['number'], corrections):
        for group in staff:
            for note in group['notes']:
                grouped[group['position']].setdefault(note['pitch'], note)
    return [(position, list(notes.values())) for position, notes in sorted(grouped.items())]


def match_attacks(attacks, played):
    """Maximize the number of pitch matches across ordered, unordered-within-chord attacks.

    A row is the best match count for each played prefix. For a chord ending at
    a given prefix, only the latest occurrence of each chord pitch matters.
    Starting any earlier without adding a distinct pitch cannot improve the
    score because the preceding row is monotone. Store only traceback choices
    and two score rows. No MIDI timestamps or chord time windows are used.
    """
    previous = [0] * (len(played) + 1)
    trace = []
    for _, notes in attacks:
        pitches = {note['pitch'] for note in notes}
        latest = {}
        current = [0] * (len(played) + 1)
        choices = array('H', [0]) * (len(played) + 1)
        for end, pitch in enumerate(played, 1):
            best = previous[end]
            if current[end - 1] > best:
                best = current[end - 1]
                choices[end] = FROM_LEFT
            if pitch in pitches:
                latest.pop(pitch, None)
                latest[pitch] = end - 1
                for count, start in enumerate(reversed(latest.values()), 1):
                    score = previous[start] + count
                    if score > best:
                        best = score
                        choices[end] = start + 1
            current[end] = best
        previous = current
        trace.append(choices)

    matches = [{} for _ in attacks]
    end = len(played)
    for index in reversed(range(len(attacks))):
        choices = trace[index]
        while choices[end] == FROM_LEFT:
            end -= 1
        start = choices[end] - 1
        if start >= 0:
            pitches = {note['pitch'] for note in attacks[index][1]}
            for cursor in range(start, end):
                if played[cursor] in pitches:
                    matches[index][played[cursor]] = cursor
            end = start
    return matches


def compare(bundle, played, corrections=(), *, through_pause=False):
    attacks = written_attacks(bundle, corrections)
    matches = match_attacks(attacks, played)
    endpoint = None
    if through_pause:
        last = next((i for i in reversed(range(len(matches))) if matches[i]), None)
        if last is None:
            raise ValueError('No matching attack could establish a pause point.')
        (measure, beat), chord = attacks[last]
        covered_chord = [note for note in chord if note['pitch'] in matches[last]]
        partial_attack = len(covered_chord) < len(chord)
        endpoint = {
            'measure': measure,
            'attack': sum(position[0] == measure for position, _ in attacks[:last + 1]),
            'partial_measure': partial_attack or (
                last + 1 < len(attacks) and attacks[last + 1][0][0] == measure
            ),
            'partial_attack': partial_attack,
        }
        attacks = [*attacks[:last], ((measure, beat), covered_chord)]
        matches = matches[:last + 1]
    measures = {
        m['number']: {
            'number': m['number'], 'pdf_page': m['pdf_page'],
            'key_fifths': m.get('key_fifths', bundle.get('key_fifths', 0)),
            'attacks': [],
        }
        for m in bundle['measures']
        if endpoint is None or m['number'] <= endpoint['measure']
    }
    rows = []
    for ((measure, beat), notes), matched in zip(attacks, matches):
        row = {'beat': str(beat), 'expected': [
            {**note, 'played_index': matched.get(note['pitch'])} for note in notes
        ], 'extra': []}
        measures[measure]['attacks'].append(row)
        rows.append(row)

    if not rows and played:
        row = {'beat': '0', 'expected': [], 'extra': []}
        next(iter(measures.values()))['attacks'].append(row)
        rows.append(row)

    # Place extra notes using the surrounding matched attacks. The original
    # played index remains available when the inferred location is ambiguous.
    anchors = sorted((index, group) for group, matched in enumerate(matches)
                     for index in matched.values())
    prior_index, prior_group = -1, -1
    for next_index, next_group in [*anchors, (len(played), len(rows))]:
        group = min(prior_group + 1, next_group, len(rows) - 1)
        if prior_group >= 0 and next_group == prior_group + 1:
            prior = rows[prior_group]
            if any(note['played_index'] is None for note in prior['expected']):
                group = prior_group
        for index in range(prior_index + 1, next_index):
            rows[group]['extra'].append({'pitch': played[index], 'played_index': index})
        prior_index, prior_group = next_index, next_group

    matched_count = len(anchors)
    missing_count = sum(len(row['expected']) for row in rows) - matched_count
    return {'measures': list(measures.values()), 'pause_endpoint': endpoint, 'matched_count': matched_count,
            'missing_count': missing_count, 'extra_count': len(played) - matched_count,
            'played_count': len(played)}


def suggest_fixes(result):
    """Only propose a specific edit for an isolated difference near matched notes."""
    rows = [row for measure in result['measures'] for row in measure['attacks']]

    def clean(row):
        return not row['extra'] and all(note['played_index'] is not None for note in row['expected'])

    for i, row in enumerate(rows):
        missing = [note for note in row['expected'] if note['played_index'] is None]
        extra = row['extra']
        if len(missing) > 1 or len(extra) > 1 or not (missing or extra):
            continue
        left = i > 0 and clean(rows[i - 1])
        right = i + 1 < len(rows) and clean(rows[i + 1])
        shared = any(note['played_index'] is not None for note in row['expected'])
        if (left and right) or (shared and (left or right)):
            action = 'replace' if missing and extra else 'remove' if missing else 'add'
            if not (missing and extra and missing[0]['pitch'] == extra[0]['pitch']):
                row['suggestion'] = action
