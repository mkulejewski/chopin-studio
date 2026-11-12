"""Versioned, conservative symbolic retrieval and offline practice organisation.

RapidFuzz supplies C++ edit/subsequence alignment. Similarities are evidence scores,
not calibrated probabilities. Provisional editions never yield certified accuracy.
"""
import json
import math
import statistics
import uuid
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
from .midi_files import journal_events

VERSION='symbolic-edit-v6-opening-restarts-experimental'


def likely_complete(match, reference_groups):
    """A timeline label for broad coverage, independent of assessment eligibility."""
    total=len(reference_groups)
    if total<8 or match.get('confidence',0)<.75:return False
    start=match.get('reference_start',0);end=match.get('reference_end',0)
    covered=len({b for _,b in match.get('pairs',[])})/total
    return (start/total<=.10 and end/total>=.90 and (end-start)/total>=.85
            and covered>=.75 and match.get('query_coverage',0)>=.70)


def performance_notes(events):
    notes=[];active=defaultdict(deque)
    for event in events:
        msg=event.get('message',{})
        kind=msg.get('type')
        key=(msg.get('channel',0),msg.get('note'))
        if kind=='note_on' and msg.get('velocity',0)>0:
            note={'pitch':msg['note'],'onset':event['t'],'duration':0.0,'velocity':msg['velocity'],'channel':msg.get('channel',0)}
            notes.append(note);active[key].append(note)
        elif kind=='note_off' or kind=='note_on' and msg.get('velocity',0)==0:
            if active[key]:
                note=active[key].popleft();note['duration']=max(0,event['t']-note['onset'])
    return notes


def groups(notes, tolerance=.045):
    result=[]
    for index,note in enumerate(notes):
        if not result or note['onset']-result[-1]['onset']>tolerance:
            result.append({'onset':note['onset'],'pitches':set(),'indices':[],'measure':note.get('measure')})
        result[-1]['pitches'].add(note['pitch']);result[-1]['indices'].append(index)
    return result


def melody(grouped):return ''.join(chr(max(g['pitches'])+32) for g in grouped)
def grams(sequence,n=4):return Counter(sequence[i:i+n] for i in range(len(sequence)-n+1))


class Recognizer:
    def __init__(self,references,navigation=False):
        self.references=[];self.index=defaultdict(set);self.navigation=navigation
        for reference in references:
            if reference['quality']=='rejected':continue
            row=dict(reference);notes=json.loads(row['notes']) if isinstance(row['notes'],str) else row['notes']
            row['note_data']=notes;row['groups']=groups(notes,tolerance=.0001);row['melody']=melody(row['groups']);row['grams']=grams(row['melody'])
            index=len(self.references)
            for gram in row['grams']:self.index[gram].add(index)
            self.references.append(row)

    def match(self,notes,limit=5,edges=True):
        query_groups=groups(notes);query=melody(query_groups)
        if len(query)<8:return {'label':'Unknown piece','confidence':0,'candidates':[],'version':VERSION}
        votes=Counter()
        for gram,count in grams(query).items():
            for index in self.index.get(gram,()):votes[index]+=count
        candidates=[i for i,_ in votes.most_common(8)]
        if not candidates:candidates=list(range(min(8,len(self.references))))
        results=[]
        for index in candidates:
            reference=self.references[index]
            alignment=fuzz.partial_ratio_alignment(query,reference['melody'])
            if not alignment:continue
            qs,qe=alignment.src_start,alignment.src_end
            start,end=alignment.dest_start,alignment.dest_end
            rg=reference['groups'][start:end]
            if not rg:continue
            # Exact-pitch chord overlap provides independent polyphonic evidence.
            opcodes=Levenshtein.opcodes(query[qs:qe],reference['melody'][start:end])
            pairs=[]
            for op in opcodes:
                if op.tag in ('equal','replace'):
                    for offset in range(min(op.src_end-op.src_start,op.dest_end-op.dest_start)):
                        pairs.append((qs+op.src_start+offset,start+op.dest_start+offset))
            overlaps=[len(query_groups[a]['pitches']&reference['groups'][b]['pitches'])/max(1,len(query_groups[a]['pitches']|reference['groups'][b]['pitches'])) for a,b in pairs]
            poly=statistics.mean(overlaps) if overlaps else 0
            similarity=.75*alignment.score/100+.25*poly
            if reference['quality']!='verified' and not self.navigation:similarity=min(.84,similarity)
            result={'piece_id':reference['piece_id'],'reference_id':reference['id'],'confidence':round(similarity,4),
                    'query_coverage':(qe-qs)/len(query),'latest_matched':qe==len(query),
                    'first_measure':rg[0].get('measure'),'last_measure':rg[-1].get('measure'),
                    'reference_start':start,'reference_end':end,'quality':reference['quality'],
                    'melody_similarity':alignment.score/100,'polyphonic_overlap':poly,'pairs':pairs}
            results.append(result)
        # Competing editions of the same work are not competing piece identities.
        unique={}
        for result in sorted(results,key=lambda x:-x['confidence']):unique.setdefault(result['piece_id'],result)
        results=sorted(unique.values(),key=lambda x:-x['confidence'])[:limit]
        best=results[0] if results else None
        margin=(best['confidence']-results[1]['confidence']) if len(results)>1 else (best['confidence'] if best else 0)
        if not best or best['confidence']<.65 or margin<.035:
            return {'label':'Unknown piece' if not best or best['confidence']<.65 else 'Ambiguous match','confidence':best['confidence'] if best else 0,'candidates':results,'version':VERSION}
        # Whole-take partial alignment may prefer a later passage over a free
        # introduction. Preserve independent edge evidence without inventing
        # alignment pairs or changing completeness/assessment coverage.
        if edges and len(query_groups)>64:
            selected=[r for r in self.references if r['id']==best['reference_id']]
            edge_recognizer=Recognizer(selected,navigation=self.navigation)
            for side,subset in [('opening',query_groups[:48]),('ending',query_groups[-48:])]:
                excerpt=[notes[i] for g in subset for i in g['indices']]
                edge=edge_recognizer.match(excerpt,edges=False)
                if edge.get('piece_id')==best['piece_id'] and edge['confidence']>=.65 and edge.get('query_coverage',0)>=.8:
                    best[side+'_evidence']={k:edge.get(k) for k in ('confidence','first_measure','last_measure','reference_start','reference_end')}
                    if side=='opening':best['first_measure']=edge['first_measure']
                    else:best['last_measure']=edge['last_measure']
        return {**best,'label':'Identified' if best['confidence']>=.9 and margin>=.08 else 'Probable match · review suggested','candidates':results,'version':VERSION}


def candidate_ranges(notes,duration,cooldown=20,recognizer=None):
    if not notes:return []
    onsets=sorted(set(n['onset'] for n in notes))
    intervals=[b-a for a,b in zip(onsets,onsets[1:]) if .08<b-a<3]
    median=statistics.median(intervals) if intervals else .5
    threshold=max(cooldown,min(30,median*16))
    starts=[notes[0]['onset']];ranges=[]
    held_until=notes[0]['onset']+notes[0]['duration']
    for index,(previous,current) in enumerate(zip(notes,notes[1:])):
        # A candidate silence boundary remains explicitly uncertain: held notes and
        # Chopin pauses are not proof of a change of work.
        gap=current['onset']-held_until
        contextual_change=False
        if recognizer and 3<=gap<threshold:
            # A shorter rest is a piece boundary only when both sides provide
            # independent identity evidence. A fermata within a work stays intact.
            before=groups(notes[:index+1])[-48:]
            after=groups(notes[index+1:])[:48]
            left=recognizer.match([notes[i] for g in before for i in g['indices']],edges=False)
            tail=notes[index+1:]
            right=recognizer.match([tail[i] for g in after for i in g['indices']],edges=False)
            contextual_change=bool(left.get('piece_id') and right.get('piece_id')
                and left['piece_id']!=right['piece_id']
                and min(left['confidence'],right['confidence'])>=.65
                and min(left.get('query_coverage',0),right.get('query_coverage',0))>=.8)
        if gap>=threshold or contextual_change:
            ranges.append((starts[-1],min(duration,max(previous['onset']+.2,held_until)),True))
            starts.append(current['onset'])
        held_until=max(held_until,current['onset']+current['duration'])
    ranges.append((starts[-1],min(duration,max(n['onset']+n['duration'] for n in notes)+.25),False))
    return ranges


def opening_restarts(notes, recognizer, match):
    """Find repeated opening attempts, withholding ambiguous written repeats.

    Six opening groups give short abandoned starts enough evidence without
    treating every backward jump in a recurring theme as a new performance.
    """
    reference=next((r for r in recognizer.references if r['id']==match.get('reference_id')),None)
    if not reference or match.get('confidence',0)<.7:return []
    rg=reference['groups'];played=groups(notes)
    if len(rg)<24 or len(played)<12:return []
    signature=reference['melody'][:6];query=melody(played)
    # A written recurrence near the opening cannot establish an aborted run.
    if any(Levenshtein.normalized_similarity(signature,reference['melody'][i:i+6])>=.8
           for i in range(6,max(6,len(rg)//4))):return []

    def opening(index):
        if played[index]['pitches']!=rg[0]['pitches']:return False
        for size in range(6,10):
            fragment=query[index:index+size]
            if len(fragment)!=size or Levenshtein.normalized_similarity(fragment,signature)<.8:continue
            pairs=[(index+op.src_start+k,op.dest_start+k)
                   for op in Levenshtein.opcodes(fragment,signature) if op.tag in ('equal','replace')
                   for k in range(min(op.src_end-op.src_start,op.dest_end-op.dest_start))]
            overlap=statistics.mean(len(played[a]['pitches']&rg[b]['pitches'])/len(played[a]['pitches']|rg[b]['pitches'])
                                    for a,b in pairs)
            if overlap>=.65:return True
        return False

    if not opening(0):return []
    cuts=[];start=0
    local=Recognizer([reference])
    for index in range(6,len(played)-5):
        if index-start<6 or not opening(index):continue
        excerpt=[notes[j] for g in played[start:index] for j in g['indices']]
        prior=local.match(excerpt,edges=False)
        # Very short attempts are supported by the opening signature itself.
        short=index-start<8
        if not short and not (prior.get('piece_id')==reference['piece_id']
                and prior['confidence']>=.7 and prior.get('query_coverage',0)>=.8
                and prior.get('reference_start',len(rg))<=6
                and prior.get('reference_end',len(rg))<=len(rg)*.25):continue
        cuts.append(played[index]['onset']);start=index
    return cuts


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
        cuts=opening_restarts(excerpt,recognizer,match)
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
            if aborted and not match.get('piece_id'):
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


def save_history(store,session_id):
    snapshot=store.query('SELECT * FROM segments WHERE session_id=? ORDER BY start',(session_id,))
    store.execute('INSERT INTO segment_history(session_id,created,snapshot) VALUES(?,?,?)',(session_id,datetime.now(timezone.utc).isoformat(),json.dumps(snapshot)))


def analyse_segment(store,segment):
    observed=performance_notes(journal_events(store.root/'sessions'/segment['session_id']/'events.jsonl'))
    observed=[n for n in observed if segment['start']<=n['onset']<segment['end']]
    reference=store.query('SELECT * FROM symbolic_scores WHERE piece_id=? ORDER BY quality DESC',(segment['piece_id'],)) if segment['piece_id'] else []
    velocities=[n['velocity'] for n in observed]
    result={'version':VERSION,'notes':len(observed),'velocity_mean':statistics.mean(velocities) if velocities else None,
            'observations':[],'accuracy':None,'notice':'No verified score alignment. Descriptive measurements only.'}
    from .microphone import analyse_audio
    try:
        result['audio'] = analyse_audio(store.root/'sessions'/segment['session_id'], segment, observed)
    except Exception as exc:
        result['audio'] = {'available': False, 'notice': 'Audio analysis failed: ' + str(exc)}
    capture = store.query('SELECT status,error FROM sessions WHERE id=?', (segment['session_id'],))
    if capture and (capture[0]['error'] or capture[0]['status'] not in ('saved', 'imported')):
        presence = result.get('audio', {}).get('piano_presence')
        if presence:
            presence.update(status='uncertain', auto_discard=False, notice='Capture integrity needs review; microphone audio retained.')
    if not reference:return result
    recognizer=Recognizer(reference);match=recognizer.match(observed)
    result['match']=match
    if not match.get('reference_id'):return result
    ref=next(r for r in recognizer.references if r['id']==match['reference_id'])
    og=groups(observed);rg=ref['groups'];evidence=[];correct=0;expected=0;tempo=[]
    for a,b in match.get('pairs',[]):
        if a>=len(og) or b>=len(rg):continue
        actual=og[a]['pitches'];wanted=rg[b]['pitches'];correct+=len(actual&wanted);expected+=len(wanted)
        for kind,pitches in [('missing',wanted-actual),('extra',actual-wanted)]:
            for pitch in sorted(pitches):
                evidence.append({'id':f'{segment["id"]}:{a}:{kind}:{pitch}','kind':kind,'pitch':pitch,'measure':rg[b]['measure'],
                                 'time':og[a]['onset'],'confidence':match['confidence'],'expected':sorted(wanted),'observed':sorted(actual),
                                 'uncertainty':'Ornaments, repeats, voice allocation and edition differences require review.'})
        tempo.append({'time':og[a]['onset'],'beat':rg[b]['onset'],'measure':rg[b]['measure']})
    paired_observed={a for a,b in match.get('pairs',[])}
    paired_reference={b for a,b in match.get('pairs',[])}
    # Compact score-relative note groups for the review overlay. Keep unaligned
    # played groups separate: an uncertain alignment is not proof of extra notes.
    paired_by_reference={b:a for a,b in match.get('pairs',[])}
    from .symbolic import annotate_reference_staves,annotate_reference_rhythm
    source=store.root/'references'/ref.get('filename','')
    score_notes=annotate_reference_rhythm(annotate_reference_staves(ref['note_data'],source),source)
    comparison=[]
    for index in range(match['reference_start'],min(match['reference_end'],len(rg))):
        played=og[paired_by_reference[index]] if index in paired_by_reference else None
        comparison.append({'measure':rg[index]['measure'],'beat':rg[index]['onset'],
                           'time':played['onset'] if played else None,
                           'expected':sorted(rg[index]['pitches']),
                           'observed':sorted(played['pitches']) if played else [],
                           'score_notes':[{key:score_notes[j].get(key) for key in ('pitch','duration','staff','voice','part','grace','display_staff','staff_source','clef_sign','beam_group','beaming_source','beat_group_size','measure_start')}
                                          for j in rg[index]['indices']],
                           'played_notes':[{key:observed[j].get(key) for key in ('pitch','onset','duration')}
                                           for j in played['indices']] if played else []})
    result['note_comparison']=comparison
    result['unaligned_played_groups']=sum(index not in paired_observed for index in range(len(og)))
    for index in range(match['reference_start'],min(match['reference_end'],len(rg))):
        if index not in paired_reference:
            for pitch in rg[index]['pitches']:
                evidence.append({'id':f'{segment["id"]}:unmatched:{index}:{pitch}','kind':'unmatched_expected_group','pitch':pitch,'measure':rg[index]['measure'],
                                 'time':None,'confidence':match['confidence'],'expected':sorted(rg[index]['pitches']),'observed':[],
                                 'uncertainty':'Could be omission, repeat structure or alignment ambiguity; no exact observed timestamp exists.'})
    voice_velocities=defaultdict(list)
    for a,b in match.get('pairs',[]):
        for observed_index in og[a]['indices']:
            note=observed[observed_index]
            candidates=[ref['note_data'][j] for j in rg[b]['indices'] if ref['note_data'][j]['pitch']==note['pitch']]
            if len(candidates)==1:
                source_note=candidates[0];voice_velocities[f"part {source_note.get('part',0)} / staff {source_note.get('staff','?')} / voice {source_note.get('voice','?')}"].append(note['velocity'])
    pedal_events=[e for e in journal_events(store.root/'sessions'/segment['session_id']/'events.jsonl') if segment['start']<=e['t']<segment['end'] and e.get('message',{}).get('type')=='control_change' and e['message'].get('control')==64]
    values=[e['message']['value'] for e in pedal_events]
    pedal_changes=sum(a>=64>b or a<64<=b for a,b in zip(values,values[1:]))
    result.update({'observations':evidence[:5000],'observations_truncated':len(evidence)>5000,'alignment':tempo,'reference_id':ref['id'],'reference_quality':ref['quality'],
                   'voice_velocity':{voice:{'mean':statistics.mean(velocities),'count':len(velocities)} for voice,velocities in voice_velocities.items()},
                   'pedal':{'messages':len(values),'threshold_crossings':pedal_changes,'partial_values':sum(0<v<127 for v in values),'notice':'Controller positions only, not proof of acoustic clearing or blurring.'},
                   'ornaments':{'reference_grace_notes':sum(bool(n.get('grace')) for n in ref['note_data']),'treatment':'Grace-note durations are retained; trills and free ornaments are not classified reliably and may appear as uncertain mismatches.'},
                   'notice':'Experimental edit alignment. Ornaments and repeated passages can be ambiguous. Review note evidence; MIDI velocity is not loudness.'})
    # Accuracy remains withheld: ornaments, unmatched groups and edition variants
    # are not yet resolved robustly enough for a defensible percentage.
    result['matched_pitch_count'] = correct
    from .assessment import assess
    result['assessment']=assess(store,segment,ref,match,og,rg,correct)
    from .tempo import infer_tempo
    result['tempo'] = infer_tempo(observed,ref,match)
    result['tempo_curve'] = result['tempo']['curve']
    from .musical_comparison import musical_review
    result['musical_review'] = musical_review(comparison, ref['quality'], match['confidence'])
    judgements={(g['time'],g['measure'],side,int(pitch)):item for g in comparison
                for side,items in g['musical_context'].items() for pitch,item in items.items()}
    for observation in result['observations']:
        side='observed' if observation['kind']=='extra' else 'expected'
        observation['musical_judgement']=judgements.get((observation['time'],observation['measure'],side,observation['pitch']))
    return result
