"""Transparent musical-performance proxies for comparing complete audio takes.

This ranks available MIDI evidence, not interpretation, tone or concert readiness.
Missing evidence is never replaced by recency or an invented neutral score.
"""
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import mean, median

from defusedxml import ElementTree

from .analysis_selection import reference_identity
from .performance import groups

VERSION = 'musical-audio-ranking-v1'
LEVELS = {name:i for i,name in enumerate(('ppp','pp','p','mp','mf','f','ff','fff'))}


@lru_cache(maxsize=16)
def source_annotations(filename, mtime, size):
    path = Path(filename)
    bundle = json.loads((Path(__file__).parent/'reference_annotations/nocturne_dynamics.json').read_text())
    entry = bundle.get(hashlib.sha256(path.read_bytes()).hexdigest(), {})
    try:
        tree = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise ValueError('Source notation could not be inspected') from exc
    exempt = set()
    for part in tree.findall('part'):
        for ordinal, measure in enumerate(part.findall('measure'), 1):
            words = ' '.join(w.text or '' for w in measure.findall('.//words'))
            if (measure.find('.//fermata') is not None or measure.find('.//metronome') is not None
                    or any(s.get('tempo') for s in measure.findall('.//sound'))
                    or re.search(r'rit\b|ritard|rall|rubato|accel|a\s+tempo|smorz|riten', words, re.I)):
                # Partitura's imported measure.number is ordinal; the XML's
                # printed label can start at pickup 0 or another number.
                exempt.add(ordinal)
    review_path=path.with_suffix('.review.json')
    if review_path.is_file():
        review=json.loads(review_path.read_text())
        if (review.get('status')=='model-reviewed' and not review.get('open_issues')
                and review.get('derived_musicxml_sha256')==hashlib.sha256(path.read_bytes()).hexdigest()):
            exempt.update(int(n) for n in review.get('timing_exempt_measure_ordinals',[]) if isinstance(n,int) and n>0)
    return entry.get('dynamic_changes', []), exempt


def quality(result, reference, annotations=(), timing_exempt=()):
    missing = []
    assessment = result.get('assessment') or {}
    match = result.get('match') or {}
    comparison = result.get('note_comparison') or []
    reference_notes = reference.get('note_data', reference['notes'])
    if isinstance(reference_notes, str): reference_notes = json.loads(reference_notes)
    reference_groups = groups(reference_notes, tolerance=.0001)
    if not reference_groups:
        return {'status':'unavailable','score':None,'notice':'Reference has no score notes.'}
    covered = len({b for _,b in match.get('pairs',[])})/len(reference_groups)
    if (match.get('location_ambiguous') or match.get('confidence',0)<.75
            or match.get('query_coverage',0)<.7 or covered<.8
            or match.get('reference_start',len(reference_groups))>.1*len(reference_groups)
            or match.get('reference_end',0)<.9*len(reference_groups)):
        missing.append('whole-take alignment')
    if not assessment.get('capture_ok'):
        missing.append('healthy authoritative capture')
    if reference['quality'] not in ('verified','provisional'):
        missing.append('usable reference')
    if result.get('reference_revision') != reference_identity(reference).revision:
        missing.append('current reference fingerprint')
    expected = sum(len(g['pitches']) for g in reference_groups)
    played, correct = result.get('notes',0), result.get('matched_pitch_count',0)
    if not played or 'matched_pitch_count' not in result:
        missing.append('whole-take pitch measurements')
    pitch = min(100, 200*correct/(expected+played)) if expected+played else 0

    measures = defaultdict(list)
    for point in comparison:
        measures[point['measure']].append(point)
    residuals, eligible_measures, measured = [], 0, 0
    for number, points in measures.items():
        if number in timing_exempt or any(n.get('grace') or n.get('ornaments') for p in points for n in p.get('score_notes',[])):
            continue
        if len(points)<5:
            continue
        eligible_measures += 1
        intervals = []
        for a,b in zip(points,points[1:]):
            if a.get('time') is None or b.get('time') is None:
                continue
            if set(a['expected'])!=set(a['observed']) or set(b['expected'])!=set(b['observed']):
                continue
            db,dt = b['beat']-a['beat'], b['time']-a['time']
            if db>0 and dt>0:
                intervals.append(((a['beat']+b['beat'])/2, math.log(dt/db)))
        if len(intervals)<4:
            continue
        # Fit a smooth local log-tempo trend independently in each measure.
        # Different overall tempos, inter-measure rubato and gradual local
        # acceleration/ritardando are not scored as timing errors.
        slope = median((y2-y1)/(x2-x1) for i,(x1,y1) in enumerate(intervals)
                       for x2,y2 in intervals[i+1:] if x2!=x1)
        intercept = median(y-slope*x for x,y in intervals)
        residuals.append(math.sqrt(mean((y-intercept-slope*x)**2 for x,y in intervals)))
        measured += 1
    timing = 100*math.exp(-3*mean(residuals)) if residuals else None
    if measured<3 or measured<.5*eligible_measures:
        missing.append('within-measure timing coverage')

    dynamic_values = defaultdict(lambda:defaultdict(list))
    changes = sorted(annotations,key=lambda a:(a['measure'],a['beat']))
    for number, points in measures.items():
        first_beat = min(p['beat'] for p in points)
        for point in points:
            if point.get('time') is None:
                continue
            for note in point.get('played_notes',[]):
                sources = [n for n in point.get('score_notes',[]) if n['pitch']==note['pitch']]
                if len(sources)!=1:
                    continue
                source = sources[0]
                part,staff = source.get('part',0) or 0, source.get('staff',1) or 1
                voice = (part,staff,str(source.get('voice') or ''))
                label = source.get('dynamic')
                if not label and changes:
                    display_staff = source.get('display_staff') or (2 if part==1 else staff)
                    prior = [a for a in changes if a['staff']==display_staff and
                             (a['measure'],a['beat']) <= (number,point['beat']-first_beat+1e-5)]
                    if prior: label = prior[-1]['dynamic']
                velocity = note.get('velocity_14')
                velocity = velocity/128 if velocity is not None else note.get('velocity')
                if label in LEVELS and velocity is not None:
                    dynamic_values[voice][LEVELS[label]].append(velocity)
    contrasts = []
    for levels in dynamic_values.values():
        levels = sorted((k,median(v)) for k,v in levels.items() if len(v)>=3)
        contrasts.extend(50+50*math.tanh((b-a)/6) for i,(_,a) in enumerate(levels)
                         for _,b in levels[i+1:])
    dynamics = mean(contrasts) if contrasts else None
    if dynamics is None:
        missing.append('written dynamic contrasts with matched velocities')
    clipping = (result.get('audio') or {}).get('clipped_sample_fraction')
    components = {'notes':round(pitch,2), 'timing':round(timing,2) if timing is not None else None,
                  'dynamics':round(dynamics,2) if dynamics is not None else None}
    weights = {'notes':35,'timing':35,'dynamics':25}
    if clipping is not None:
        components['recording'] = max(0,100-1000*clipping)
        weights['recording'] = 5
    passages = result.get('passages') or {}
    target = passages.get('target',{}).get('melody_min_gap')
    balances = [v['melody_gap'] for m in passages.get('measures',[]) for v in m.get('voicing',[])]
    if target is not None and balances:
        components['voicing'] = mean(100*math.exp(-max(0,target-gap)/10) for gap in balances)
        weights['voicing'] = 10
    if any(not math.isfinite(v) for v in components.values() if v is not None):
        missing.append('finite measurements')
    score = sum(components[k]*w for k,w in weights.items())/sum(weights.values()) if not missing else None
    return {'version':VERSION,'status':'available' if score is not None else 'unavailable',
            'score':round(score,2) if score is not None else None,'components':components,
            'weights':weights,'timing_measures':measured,'reference_key':reference_identity(reference).revision,
            'notice': ('Missing '+', '.join(missing)+'. Reanalyse or review manually; audio retained.' if missing else
                       'Musical-evidence proxy: notes, local timing and written dynamic contrasts; '
                       'MIDI velocity is not loudness. Rubato, interpretation and tone still need listening.'
                       + (' Provisional-reference edition differences may affect this ranking.' if reference['quality']=='provisional' else '')),
            'basis':(VERSION,reference['id'],reference_identity(reference).revision,tuple(weights),target)}
