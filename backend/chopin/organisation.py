from .timeline import save_history as save_history
"""Session organisation orchestration and stable public imports.

Pure projections, retrieval, boundaries and analysis live below this facade.
"""
import json
import uuid
from rapidfuzz import fuzz
from .midi_files import journal_events
from .performance import performance_notes as performance_notes, groups as groups, melody as melody, grams as grams
from .recognition import Recognizer as Recognizer, VERSION as VERSION
from .segmentation import (likely_complete as likely_complete, candidate_ranges as candidate_ranges,
                           opening_restarts as opening_restarts, passage_restarts as passage_restarts)
from .segment_analysis import analyse_segment as analyse_segment

def organise(store,session_id,force=False):
    from .retention import locked
    if locked(store,session_id):raise ValueError('Cannot rebuild a timeline after permanent recording removal.')
    session=store.query('SELECT * FROM sessions WHERE id=?',(session_id,))
    if not session:raise ValueError('Session not found')
    if session[0]['status'] in ('recording','saving'):raise ValueError('Finish saving before organisation')
    existing=store.query('SELECT * FROM segments WHERE session_id=? ORDER BY start',(session_id,))
    if existing and not force:
        store.set_setting('organised:'+session_id,True)
        return existing
    protected=store.query("SELECT s.start,s.end FROM segments s JOIN recording_choices c ON c.segment_id=s.id WHERE s.session_id=? AND c.choice='keep'",(session_id,))
    if existing:save_history(store,session_id)
    contexts=[]
    def contextual_events():
        for event in journal_events(store.root/'sessions'/session_id/'events.jsonl'):
            if event.get('kind')=='piece_context':contexts.append((event['t'],event.get('piece_id')))
            yield event
    notes=performance_notes(contextual_events())
    recognizer=Recognizer(store.query('SELECT * FROM symbolic_scores'))
    segments=[]
    cooldown=store.setting('separation_cooldown',20)
    ranges = candidate_ranges(notes,session[0]['duration'],cooldown,recognizer)
    if not notes:
        from .microphone import audio_ranges
        ranges = audio_ranges(store.root/'sessions'/session_id, session[0]['duration'], cooldown)
    attempts=[]
    for start,end,unclear in ranges:
        excerpt=[n for n in notes if start<=n['onset']<end]
        match=recognizer.match(excerpt)
        cuts=sorted(set(opening_restarts(excerpt,recognizer,match)+passage_restarts(excerpt,recognizer,match)))
        points=[start,*cuts,end]
        attempts.extend((left,right,unclear,index<len(cuts),match)
                        for index,(left,right) in enumerate(zip(points,points[1:])))
    for start,end,unclear,aborted,parent_match in attempts:
        excerpt=[n for n in notes if start<=n['onset']<=end]
        # Sample consecutive windows; different confident works inside a continuous
        # activity create additional provisional cuts even without silence.
        window_results=[]
        grouped=groups(excerpt)
        for offset in range(0,len(grouped),24):
            window=[excerpt[i] for g in grouped[offset:offset+48] for i in g['indices']]
            if len(groups(window))>=12:window_results.append((window[0]['onset'],recognizer.match(window,edges=False)))
        boundaries=[(start,None)]
        previous=None;pending=None
        for timestamp,result in window_results:
            pid=result.get('piece_id')
            reliable=pid and result['confidence']>=.7 and result.get('query_coverage',0)>=.8
            if not reliable:
                pending=None
                continue
            if previous is None:
                previous=pid
            elif pid!=previous:
                if pending and pending[1]==pid and pending[0]-boundaries[-1][0]>=cooldown:
                    boundaries.append(pending)
                    previous=pid;pending=None
                else:pending=(timestamp,pid)
            else:pending=None
        for index,(left,_) in enumerate(boundaries):
            right=boundaries[index+1][0] if index+1<len(boundaries) else end
            chunk=[n for n in excerpt if left<=n['onset']<right]
            match=recognizer.match(chunk)
            if aborted and not match.get('piece_id') and parent_match.get('piece_id'):
                match={k:parent_match[k] for k in ('piece_id','reference_id','confidence')}
                match['label']='Partial attempt · restarted'
            if not match.get('piece_id'):
                previous_context=[pid for t,pid in contexts if t<=left]
                ids={previous_context[-1] if previous_context else None}
                ids.update(pid for t,pid in contexts if left<t<right)
                assumed=next(iter(ids)) if len(ids)==1 else None
                if assumed and store.query('SELECT id FROM pieces WHERE id=?',(assumed,)):
                    match={**match,'piece_id':assumed,'confidence':0,'assumed':True,
                           'label':'Assuming open score · recognition unconfirmed'}
            reference=next((r for r in recognizer.references if r['id']==match.get('reference_id')),None)
            complete=bool(not aborted and reference and likely_complete(match,reference['groups']))
            ident=uuid.uuid4().hex
            segments.append({'id':ident,'session_id':session_id,'start':left,'end':max(left+.001,right),'piece_id':match.get('piece_id'),
                             'label':match['label'],'confidence':match['confidence'],'first_measure':match.get('first_measure'),
                             'last_measure':match.get('last_measure'),'kind':'complete' if complete else 'partial' if match.get('piece_id') else 'unknown',
                             'group_id':None,'complete':int(complete),'discarded':0,'revision':1,
                             'details':json.dumps({'match':match,'unclear_boundary':unclear,'aborted_by_restart':aborted,'algorithm':VERSION})})
    # Retain a user-confirmed full-piece exercise across an equivalent rebuild.
    for segment in segments:
        for prior in existing:
            overlap=max(0,min(segment['end'],prior['end'])-max(segment['start'],prior['start']))
            span=max(segment['end']-segment['start'],prior['end']-prior['start'])
            if (not json.loads(segment['details']).get('aborted_by_restart') and prior['kind']=='full_exercise'
                    and prior['piece_id']==segment['piece_id'] and overlap>=.95*span):
                segment.update(kind='full_exercise',complete=1,label=prior['label'])
                break
    # Group similar attempts using exact-pitch melodies, retaining separate timestamps.
    for i,segment in enumerate(segments):
        a=melody(groups([n for n in notes if segment['start']<=n['onset']<segment['end']]))
        for prior in segments[:i]:
            if segment['piece_id']!=prior['piece_id']:continue
            b=melody(groups([n for n in notes if prior['start']<=n['onset']<prior['end']]))
            if min(len(a),len(b))>=8 and fuzz.ratio(a,b)>=85:
                group=prior['group_id'] or uuid.uuid4().hex;prior['group_id']=group;segment['group_id']=group;break
    with store.lock:
        try:
            store.db.execute('DELETE FROM segments WHERE session_id=?',(session_id,))
            for segment in segments:
                keys=list(segment)
                store.db.execute('INSERT INTO segments('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(segment.values()))
                if any(min(segment['end'],r['end'])>max(segment['start'],r['start']) for r in protected):
                    store.db.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(segment['id'],))
            store.db.commit()
        except Exception:store.db.rollback();raise
    store.set_setting('organised:'+session_id,True)
    return segments
