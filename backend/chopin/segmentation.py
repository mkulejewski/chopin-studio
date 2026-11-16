"""Pure activity bounds, completeness and conservative restart detection."""
import statistics
from collections import defaultdict
from rapidfuzz.distance import Levenshtein
from .performance import groups, melody
from .recognition import Recognizer

def likely_complete(match, reference_groups):
    """A timeline label for broad coverage, independent of assessment eligibility."""
    total=len(reference_groups)
    if total<8 or match.get('location_ambiguous') or match.get('confidence',0)<.75:return False
    start=match.get('reference_start',0);end=match.get('reference_end',0)
    covered=len({b for _,b in match.get('pairs',[])})/total
    return (start/total<=.10 and end/total>=.90 and (end-start)/total>=.85
            and covered>=.75 and match.get('query_coverage',0)>=.70)


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


def passage_restarts(notes, recognizer, match):
    """Split short mid-piece retries only with unique exact chord context."""
    played=groups(notes)
    reference=next((r for r in recognizer.references if r['id']==match.get('reference_id')),None)
    if not reference:
        head=recognizer.match([notes[j] for g in played[:6] for j in g['indices']],edges=False)
        tail=recognizer.match([notes[j] for g in played[-6:] for j in g['indices']],edges=False)
        if not head.get('piece_id') or head.get('piece_id')!=tail.get('piece_id'):return []
        reference=next((r for r in recognizer.references if r['id']==head.get('reference_id')),None)
    if not reference:return []
    rg=reference['groups'];size=6
    signatures=defaultdict(list)
    for i in range(len(rg)-size+1):
        signatures[tuple(tuple(sorted(g['pitches'])) for g in rg[i:i+size])].append(i)
    previous=None;start_index=0;cuts=[]
    for i in range(len(played)-size+1):
        key=tuple(tuple(sorted(g['pitches'])) for g in played[i:i+size])
        locations=signatures.get(key,[])
        if len(locations)!=1:continue
        position=locations[0]
        if previous is not None:
            pi,pr=previous
            # Opening returns remain governed by the dedicated written-repeat
            # checks above. A mid-piece retry must move backward after at least
            # six attacks, within a short continuous attempt.
            if position>0 and i-start_index>=size and i-pi<=size and position<pr+(i-pi)-3 and i-start_index<=64:
                cuts.append(played[i]['onset']);start_index=i
        previous=(i,position)
    return cuts

