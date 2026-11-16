"""Current measure evidence and recall history, separate from personal mastery."""
import json
import hashlib
from collections import defaultdict
from datetime import datetime, timezone


def current_analyses(store, piece_id):
    from .analysis_selection import AnalysisReader
    yield from AnalysisReader(store).current_rows(piece_id)


def piece_progress(store, piece_id, now=None):
    measures = {}; mistakes = defaultdict(list)
    for row, result in current_analyses(store, piece_id):
        if result.get('match',{}).get('location_ambiguous'): continue
        passage = result.get('passages', {})
        for measure in passage.get('measures', []):
            if measure['measure'] is None: continue
            key = (passage.get('reference_id'), measure['measure'],passage.get('reference_revision'))
            item = measures.setdefault(key, {'reference_id': key[0], 'reference_revision':key[2], 'measure': key[1], 'attempts': 0, 'seconds': 0, 'history': []})
            item['attempts'] += 1
            item['latest'] = measure
            item['history'].append({'date': row['started'], 'missing': measure['missing'], 'extra': measure['extra'], 'trusted': passage.get('trusted', False)})
        # Time intervals are assigned once; long gaps are pauses, not inferred work.
        points = passage.get('points', [])
        for i, point in enumerate(points):
            key = (passage.get('reference_id'), point['measure'],passage.get('reference_revision'))
            if key not in measures or point['time'] is None: continue
            end = points[i+1]['time'] if i+1 < len(points) else row['end']
            dt = min(row['end'], end)-max(row['start'], point['time']) if end is not None else 0
            if 0 < dt <= 8: measures[key]['seconds'] += dt
        # Deduplicate a mistake within an attempt; recurring means distinct takes.
        keys = {(o.get('measure'), o.get('kind'), o.get('pitch')) for o in result.get('observations', [])}
        for key in keys:
            if key[0] is not None:
                mistakes[(result.get('reference_id'), *key,result.get('reference_revision'))].append({'date': row['started'], 'segment_id': row['segment_id'], 'trusted': passage.get('trusted', False)})
    for item in measures.values(): item['history']=item['history'][-12:]
    recall = {}
    now = now or datetime.now(timezone.utc)
    for row in store.query("SELECT * FROM learning_attempts WHERE piece_id=? AND status='evaluated' ORDER BY created,id", (piece_id,)):
        target = json.loads(row['target']); result = json.loads(row['result'] or '{}')
        if target.get('kind') not in ('hidden', 'review') or result.get('aborted') or result.get('assisted'): continue
        if not result.get('capture_ok') or result.get('uncertain'): continue
        rules=hashlib.sha256(json.dumps(target.get('variants',[]),sort_keys=True).encode()).hexdigest()[:12]
        key = (row['revision'], target['start'], target['end'], target.get('hand','both'),rules)
        item = recall.setdefault(key, {'revision': key[0], 'first_measure': key[1], 'last_measure': key[2], 'hand': key[3], 'note_rules': key[4], 'manual_recollections': 0, 'tests': 0, 'passes': 0, 'last_pass': None})
        item['tests'] += 1; item['passes'] += bool(result.get('passed'))
        item['manual_recollections'] += bool(result.get('manual_accepted'))
        item['last_manual_accepted'] = bool(result.get('manual_accepted'))
        item['last_test'] = row['created']; item['last_passed'] = bool(result.get('passed'))
        if result.get('passed'):
            try:
                gap = (datetime.fromisoformat(row['created'])-datetime.fromisoformat(item['last_pass'])).total_seconds()/86400 if item['last_pass'] else None
                if gap is not None: item['longest_successful_gap_days'] = max(item.get('longest_successful_gap_days',0),round(gap,1))
            except ValueError: pass
            item['last_pass'] = row['created']
    for item in recall.values():
        try:
            date = datetime.fromisoformat(item['last_test'].replace('Z','+00:00'))
            item['days_since_test'] = max(0, (now-date.replace(tzinfo=date.tzinfo or timezone.utc)).days)
        except ValueError: item['days_since_test'] = None
        item['review_due'] = not (item['last_passed'] or item['last_manual_accepted']) or item['days_since_test'] is None or item['days_since_test'] >= 7
    objectives = store.query('SELECT * FROM practice_objectives WHERE piece_id=? ORDER BY completed,created', (piece_id,))
    for obj in objectives:
        # Union overlapping manual attributions; timeline edits clip stale ranges.
        spans = defaultdict(list)
        obj['attributions'] = store.query('SELECT * FROM practice_problem_time WHERE objective_id=? ORDER BY created',(obj['id'],))
        for span in store.query('''SELECT t.*,s.start AS segment_start,s.end AS segment_end FROM practice_problem_time t
          JOIN segments s ON s.session_id=t.session_id JOIN sessions ps ON ps.id=s.session_id
          WHERE t.objective_id=? AND s.discarded=0 AND s.piece_id=? AND ps.status IN ('saved','imported','recovered','incomplete')
          AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording')''', (obj['id'],piece_id)):
            start=max(span['start'],span['segment_start']); end=min(span['end'],span['segment_end'])
            if end>start: spans[span['session_id']].append((start,end))
        seconds = 0
        for ranges in spans.values():
            edge = None
            for start,end in sorted(ranges):
                seconds += max(0,end-max(start,edge if edge is not None else start)); edge=max(edge or end,end)
        obj['seconds'] = seconds
    return {'measures': list(measures.values()),
            'recurring_mistakes': [{'reference_id': k[0], 'reference_revision':k[4], 'measure': k[1], 'kind': k[2], 'pitch': k[3], 'attempts': len(v), 'history': v[-12:]} for k,v in mistakes.items() if len(v)>=2],
            'retention': list(recall.values()), 'objectives': objectives,
            'notice': 'Measure time estimates omit gaps over eight seconds. Recurring differences are review candidates, not confirmed errors. Recall records are revision/hand specific, with a seven-day review reminder; no decay probability is inferred. Problem time is explicitly attributed and may overlap other objectives.'}


def piece_time(store, piece_id):
    """Union Practice intervals and Learning sessions, once per source session."""
    spans=defaultdict(list)
    for row in store.query("""SELECT s.session_id,s.start,s.end FROM segments s JOIN sessions ps ON ps.id=s.session_id
      WHERE s.piece_id=? AND s.discarded=0 AND ps.status IN ('saved','imported','recovered','incomplete')
      AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording')""",(piece_id,)):
        spans[row['session_id']].append((row['start'],row['end']))
    for row in store.query("""SELECT DISTINCT ps.id,ps.duration FROM sessions ps JOIN learning_attempts a ON a.session_id=ps.id
      WHERE a.piece_id=? AND ps.status IN ('saved','imported','recovered','incomplete')""",(piece_id,)):
        spans[row['id']].append((0,row['duration']))
    total=0
    for ranges in spans.values():
        edge=0
        for start,end in sorted(ranges):
            total+=max(0,end-max(start,edge));edge=max(edge,end)
    return total
