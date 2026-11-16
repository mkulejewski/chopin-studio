"""Score-coordinate performance evidence, with explicit musical target gates."""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from statistics import mean, median

from .domain_types import ScorePosition

VERSION = 'score-passages-v1'


def voice_key(note):
    return f"{note.get('part', 0) or 0}:{note.get('staff', 1) or 1}:{note.get('voice') or ''}"


def average(values):
    values = [v for v in values if v is not None]
    return round(mean(values), 3) if values else None


def passage_analysis(groups, events, segment, analysis, target=None):
    target = target or {}
    pedals = defaultdict(list)
    for event in events:
        msg = event.get('message', {})
        if msg.get('type') == 'control_change' and msg.get('control') in (64, 121):
            pedals[msg.get('channel', 0)].append((event['t'], msg['value'] if msg['control'] == 64 else 0))
    for values in pedals.values(): values.sort()
    pedal_changes=sorted([{'time':e['t'],'channel':e['message'].get('channel',0),'value':e['message']['value']} for e in events if e.get('message',{}).get('type')=='control_change' and e['message'].get('control')==64],key=lambda e:e['time'])
    change_times=[e['time'] for e in pedal_changes]
    pedal_times = {ch: [t for t, _ in values] for ch, values in pedals.items()}
    points = []; by_measure = defaultdict(list)
    trusted = (analysis.get('reference_quality') == 'verified'
               and analysis.get('match', {}).get('confidence', 0) >= .85
               and not analysis.get('match', {}).get('location_ambiguous', False)
               and analysis.get('assessment', {}).get('capture_ok', False))
    for index, group in enumerate(groups):
        t = group['time']; beat = group['beat']
        seconds_per_beat = []
        # Use exact pitch anchors, without spanning an unaligned score onset.
        if t is not None and set(group['expected']) == set(group['observed']):
            for other in groups[max(0, index-1):index]+groups[index+1:index+2]:
                if other['time'] is None or set(other['expected']) != set(other['observed']): continue
                db = other['beat']-beat; dt = other['time']-t
                if db and 0 < dt/db and abs(dt) <= 8:
                    seconds_per_beat.append(dt/db)
        slope = median(seconds_per_beat) if seconds_per_beat else None
        notes = []; roles = defaultdict(list)
        for played in group.get('played_notes', []):
            candidates = [n for n in group.get('score_notes', []) if n['pitch'] == played['pitch']]
            source = candidates[0] if len(candidates) == 1 else None
            velocity = played.get('velocity_14') / 128 if played.get('velocity_14') is not None else played.get('velocity')
            channel = played.get('channel', 0)
            pedal_index = bisect_right(pedal_times.get(channel, []), played['onset'])-1
            pedal = pedals[channel][pedal_index][1] if pedal_index >= 0 else None
            role = (source.get('role') or target.get('roles', {}).get(voice_key(source))) if source else None
            if role in ('bass', 'inner', 'melody') and velocity is not None: roles[role].append(velocity)
            duration_beats = played['duration']/slope if slope and played.get('released') else None
            expected_duration = source.get('duration') if source else None
            notes.append({**played, 'voice_key': voice_key(source) if source else None, 'role': role,
                          'velocity_normalized': velocity, 'pedal': pedal,
                          'duration_beats': duration_beats,
                          'duration_ratio': duration_beats/expected_duration if duration_beats is not None and expected_duration and not source.get('grace') else None,
                          'dynamic': source.get('dynamic') if source else None,
                          'dynamic_velocity': source.get('dynamic_velocity') if source else None})
        balances = {role: average(values) for role, values in roles.items()}
        comparisons = []
        for role in ('bass', 'inner'):
            if 'melody' in balances and role in balances:
                gap = round(balances['melody']-balances[role], 3)
                minimum = target.get('melody_min_gap')
                comparisons.append({'against': role, 'melody_gap': gap,
                                    'status': ('meets_target' if gap >= minimum else 'below_target') if trusted and minimum is not None else 'descriptive'})
        point = {'index': index, 'measure': group['measure'], 'beat': beat, 'time': t,
                 'bpm': round(60/slope, 2) if slope else None,
                 'velocity': average([n['velocity_normalized'] for n in notes]),
                 'duration_ratio': average([n['duration_ratio'] for n in notes]),
                 'release_velocity': average([n.get('release_velocity') for n in notes]),
                 'pedal': average([n['pedal'] for n in notes]),
                 'missing': sorted(set(group['expected'])-set(group['observed'])),
                 'extra': sorted(set(group['observed'])-set(group['expected'])),
                 'notes': notes, 'voices': balances, 'voicing': comparisons,
                 'pedal_changes': pedal_changes[bisect_left(change_times,t):bisect_left(change_times,(groups[index+1]['time'] if index+1<len(groups) and groups[index+1]['time'] is not None else t) if index+1<len(groups) else segment.get('end',t))] if t is not None else [],
                 'dynamics': sorted({n['dynamic'] for n in notes if n['dynamic']})}
        points.append(point); by_measure[group['measure']].append(point)
    measures = []
    for number, items in by_measure.items():
        voices=defaultdict(list)
        for p in items:
            for n in p['notes']:
                if n['role'] and n['velocity_normalized'] is not None: voices[n['role']].append(n['velocity_normalized'])
        levels={role:average(values) for role,values in voices.items()}
        voicing=[]
        for role in ('bass','inner'):
            if 'melody' in levels and role in levels:
                gap=round(levels['melody']-levels[role],3); minimum=target.get('melody_min_gap')
                voicing.append({'against':role,'melody_gap':gap,'status':('meets_target' if gap>=minimum else 'below_target') if trusted and minimum is not None else 'descriptive'})
        measures.append({'voices':levels,'voicing':voicing,'measure': number, 'groups': len(items), 'aligned_groups': sum(p['time'] is not None for p in items),
                         'missing': sum(len(p['missing']) for p in items), 'extra': sum(len(p['extra']) for p in items),
                         **{key: average([p[key] for p in items]) for key in ('bpm', 'velocity', 'duration_ratio', 'pedal', 'release_velocity')}})
    releases = [n.get('release_velocity_14') if n.get('release_velocity_14') is not None else n['release_velocity']*128
                for p in points for n in p['notes'] if n.get('release_velocity') is not None]
    return {'version': VERSION, 'reference_id': analysis.get('reference_id'), 'reference_revision':analysis.get('reference_revision'), 'trusted': trusted,
            'target': target, 'points': points, 'measures': measures,
            'voices': sorted({voice_key(n) for g in groups for n in g.get('score_notes', [])}),
            'release': {'count': len(releases), 'distinct_values': len(set(releases)),
                        'status': 'calibrated' if target.get('release_calibrated') and len(set(releases)) >= 3 else 'uncalibrated' if len(set(releases)) >= 3 else 'insufficient_variation',
                        'notice': 'Note-off velocity is separate from attack velocity. Zero-velocity note-on releases have no measured release velocity. Device/tone calibration is required before interpreting release speed or articulation.'},
            'notice': 'Shared score beats synchronize all measurements. MIDI velocity is a dynamics proxy, not loudness or an absolute p/f grade. Duration ratios describe key holds, not sustained sound. Pedal is raw CC64 (unknown until observed). Voicing checks require explicit voice roles, a chosen melody margin, verified alignment and healthy capture. Repeats, ornaments and inferred voices need review.'}


def compare_passages(left, right):
    a = left.get('passages'); b = right.get('passages')
    if not a or not b or (a['reference_id'],a.get('reference_revision')) != (b['reference_id'],b.get('reference_revision')):
        return {'status': 'unavailable', 'points': [], 'notice': 'Both attempts need alignment to the same digital reference.'}
    # Beat alone is not a unique score location when measures restart numbering.
    index = {ScorePosition(p['measure'], p['beat']): p for p in b['points']}
    rows = []
    for point in a['points']:
        other = index.get(ScorePosition(point['measure'], point['beat']))
        if other is None or point['time'] is None or other['time'] is None: continue
        rows.append({'measure': point['measure'], 'beat': point['beat'], 'left': point, 'right': other,
                     'delta': {key: round(other[key]-point[key], 3) if other[key] is not None and point[key] is not None else None
                               for key in ('bpm', 'velocity', 'duration_ratio', 'pedal', 'release_velocity')}})
    return {'status': 'aligned' if rows else 'no_overlap', 'points': rows,
            'notice': 'Only shared aligned score positions are compared; deltas are second minus first. Review repeated-theme location uncertainty before interpreting changes.'}
