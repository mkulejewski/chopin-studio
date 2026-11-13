"""Incremental, best-effort staff alignment for Learning's live display.

This is display evidence only. The complete-attempt evaluator remains the pass
boundary. Capture is read from the authoritative MIDI journal, never live_queue.
"""
from fractions import Fraction
from .learning import reference_groups, _choices, _consume, ornament_position


def _location(groups, state, pitch):
    possible = [(abs(n['pitch']-pitch), g['position'], staff)
                for staff in (0, 1) for bit, n in _choices(groups, state, staff)
                for g in [groups[staff][state[staff*2]]]]
    if possible:
        _, position, staff = min(possible)
        return position, staff+1
    completed = [(g['position'], staff+1) for staff in (0, 1) for g in groups[staff]]
    return max(completed, default=((0, Fraction(0)), 1))


class LiveStaffMatcher:
    def __init__(self, bundle, target):
        self.bundle = bundle
        self.target = target
        self.beats_per_measure = bundle.get('beats_per_measure', 4)
        self.groups = reference_groups(bundle, target['start'], target['end'], target.get('variants', []), target.get('hand', 'both'))
        self.beam = {(0, 0, 0, 0): (0, None)}
        self.count = 0
        self.pruned = False

    def feed(self, pitches):
        for pitch in pitches:
            candidates = {}
            def offer(state, cost, history):
                if state not in candidates or cost < candidates[state][0]:
                    candidates[state] = (cost, history)
            for state, (cost, history) in self.beam.items():
                position, staff = _location(self.groups, state, pitch)
                offer(state, cost+1, (history, {'kind': 'extra', 'pitch': pitch,
                    'position': position, 'staff': staff, 'played_index': self.count}))
                for hand in (0, 1):
                    ornament = ornament_position(self.bundle, self.groups, state, hand, pitch)
                    if ornament is not None:
                        offer(state, cost, (history, {'kind': 'ornament', 'pitch': pitch,
                            'position': ornament, 'staff': hand+1, 'played_index': self.count}))
                    frontier = [(state, 0, history)]
                    for skip in range(3):
                        following = []
                        for cursor, skipped, trail in frontier:
                            for bit, note in _choices(self.groups, cursor, hand):
                                position = self.groups[hand][cursor[hand*2]]['position']
                                advanced = _consume(self.groups, cursor, hand, bit, note)
                                if note['pitch'] == pitch:
                                    offer(advanced, cost+skipped, (trail, {'kind': 'matched', **note,
                                        'position': position, 'played_index': self.count}))
                                if skip < 2:
                                    following.append((advanced, skipped+1, (trail,
                                        {'kind': 'missing', **note, 'position': position})))
                        frontier = following
            ranked = sorted(candidates.items(), key=lambda item: (item[1][0], -sum(item[0][::2])))
            if len(ranked) > 48 and ranked[48][1][0] == 0:
                self.pruned = True
            self.beam = dict(ranked[:48])
            self.count += 1

    def evidence(self, finished=False):
        candidates = []
        for state, (cost, history) in self.beam.items():
            tail = []
            if finished:
                cursor = state
                for staff in (0, 1):
                    while _choices(self.groups, cursor, staff):
                        bit, note = _choices(self.groups, cursor, staff)[0]
                        tail.append({'kind': 'missing', **note,
                            'position': self.groups[staff][cursor[staff*2]]['position']})
                        cursor = _consume(self.groups, cursor, staff, bit, note)
            candidates.append((cost+len(tail), -sum(state[::2]), history, tail))
        _, _, history, tail = min(candidates, key=lambda item: item[:2])
        events = []
        while history:
            history, event = history
            events.append(event)
        events.reverse()
        return events+tail

    def comparison(self, finished=False, first_measure=None):
        events = self.evidence(finished)
        first_available = min((g['position'][0] for staff in self.groups for g in staff), default=self.target['start'])
        latest = next((e['position'][0] for e in reversed(events) if 'played_index' in e), first_available)
        first = (max(self.target['start'], latest) if first_measure is None else
                 max(self.target['start'], min(self.target['end'], first_measure)))
        last = first
        by_position = {}
        for staff in self.groups:
            for index, group in enumerate(staff):
                measure, beat = group['position']
                if not first <= measure <= last:
                    continue
                # Reference timings only support engraving, not rhythm judgement.
                following = staff[index+1]['position'] if index+1 < len(staff) else (measure+1, Fraction(0))
                gap = float((following[0]-measure)*self.beats_per_measure+following[1]-beat)
                duration = min(1, max(1/12, gap))
                row = by_position.setdefault(group['position'], {
                    'measure': measure, 'beat': (measure-1)*self.beats_per_measure+float(beat) if measure else -1+float(beat),
                    'time': None, 'expected': [], 'observed': [], 'score_notes': [],
                    'live_missing': [], 'live_neutral': []})
                for note in group['notes']:
                    row['expected'].append(note['pitch'])
                    row['score_notes'].append({'pitch': note['pitch'], 'duration': duration,
                        'spelling': note.get('spelling'), 'staff': note['staff'], 'display_staff': note['staff'], 'voice': str(note['staff']),
                        'measure_start': (measure-1)*self.beats_per_measure if measure else -1, 'beat_group_size': 1})
        for event in events:
            measure, beat = event['position']
            if not first <= measure <= last:
                continue
            row = by_position.setdefault(event['position'], {
                'measure': measure, 'beat': (measure-1)*self.beats_per_measure+float(beat) if measure else -1+float(beat),
                'time': None, 'expected': [], 'observed': [], 'score_notes': [], 'live_missing': [], 'live_neutral': []})
            if event['kind'] == 'missing':
                row['live_missing'].append(event['pitch'])
            else:
                row['observed'].append(event['pitch'])
                if event['kind'] == 'ornament':
                    row['live_neutral'].append(event['pitch'])
        for row in by_position.values():
            row['observed'] = sorted(set(row['observed']))
            row['live_missing'] = sorted(set(row['live_missing']))
        return {'groups': [by_position[p] for p in sorted(by_position)], 'first_measure': first,
                'last_measure': last, 'range_start': self.target['start'], 'range_end': self.target['end'],
                'uncertain': self.pruned}


def played_only(projection):
    """Keep engraving context for sounded pitches, without revealing other notes.

    Alignment supplies rhythm/staff hints only. Hidden recall never shows missing
    or pending notes, or grades pitch differences in the live display.
    """
    groups = []
    for row in projection['groups']:
        if not row['observed']:
            continue
        notes = []
        for pitch in row['observed']:
            exact = next((n for n in row['score_notes'] if n['pitch'] == pitch), None)
            nearest = min(row['score_notes'], key=lambda n: abs(n['pitch']-pitch), default=None)
            source = exact or nearest
            notes.append({**(source or {'duration': .25, 'staff': 2 if pitch < 60 else 1}),
                          'pitch': pitch, 'spelling': exact.get('spelling') if exact else None})
        groups.append({**row, 'expected': [], 'score_notes': notes,
                       'live_missing': [], 'live_neutral': row['observed'][:]})
    return {**projection, 'groups': groups}
