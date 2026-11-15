"""Score-relative MIDI tempo; score onsets are quarter notes, capture onsets seconds."""
import statistics

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein


def timing_curve(anchors):
    """Local score-beat slopes, with octave outliers withheld from the curve."""
    estimates=[]
    for i,anchor in enumerate(anchors):
        slopes=[]
        for previous in anchors[max(0,i-4):i]:
            seconds=anchor['time']-previous['time']
            beats=anchor['beat']-previous['beat']
            if .15<=seconds<=8 and beats>=1:
                slopes.append(60*beats/seconds)
        if slopes:
            estimates.append({**anchor,'bpm':round(statistics.median(slopes),2)})
    if not estimates:
        return [],0
    center=statistics.median(p['bpm'] for p in estimates)
    # Repeated accompaniment figures can align to the next half-bar/bar. Keep
    # their half/double-speed spikes from becoming extrapolation anchors.
    retained=[p for p in estimates if center/1.75<=p['bpm']<=center*1.75]
    return retained,len(estimates)-len(retained)


def infer_tempo(observed, reference, match):
    # Import here to keep recognition independent of tempo estimation.
    from .organisation import groups, melody

    result = {'status': 'insufficient', 'bpm': None, 'unit': 'quarter notes/min',
              'method': None, 'anchors': 0, 'curve': [],
              'notice': 'Not enough reliable score timing anchors.'}
    if match.get('location_ambiguous'):
        result.update(status='ambiguous',notice='Repeated theme has multiple score locations; tempo is withheld.')
        return result
    if not match.get('reference_id'):
        return result
    og,rg=groups(observed),reference['groups']
    matched=[]
    for a,b in match.get('pairs',[]):
        if 0<=a<len(og) and 0<=b<len(rg) and og[a]['pitches'] & rg[b]['pitches']:
            matched.append({'time':og[a]['onset'],'beat':rg[b]['onset'],'measure':rg[b]['measure']})
    matched_curve,_=timing_curve(matched)
    anchors = []
    # Low notes are much less affected by right-hand trills and ornaments. Match
    # their sequence independently, then require agreement with the main location.
    first = reference['groups'][match['reference_start']]['onset']
    last = reference['groups'][match['reference_end']-1]['onset']
    bass_ref = [n for n in reference['note_data'] if n['pitch'] < 60 and not n.get('grace')
                and first <= n['onset'] <= last]
    bass_obs = [n for n in observed if n['pitch'] < 60]
    bg, br = groups(bass_obs), groups(bass_ref, tolerance=.0001)
    query, target = melody(bg), melody(br)
    if len(bg) >= 4 and len(br) >= 4:
        alignment = fuzz.partial_ratio_alignment(query, target)
        if alignment and alignment.score >= 85 and alignment.src_end-alignment.src_start >= .8*len(query):
            qs, qe, rs, re = alignment.src_start, alignment.src_end, alignment.dest_start, alignment.dest_end
            for op in Levenshtein.opcodes(query[qs:qe], target[rs:re]):
                if op.tag != 'equal':
                    continue
                for offset in range(op.src_end-op.src_start):
                    a, b = qs+op.src_start+offset, rs+op.dest_start+offset
                    anchors.append({'time': bg[a]['onset'], 'beat': br[b]['onset'], 'measure': br[b]['measure']})
            if len(anchors) >= 4:
                result['method'] = 'bass notes'
    bass_curve,bass_outliers=timing_curve(anchors)
    if len(anchors)<4 or len(bass_curve)<2:
        anchors=matched
        result['method']='matched score notes'
        curve,outliers=timing_curve(anchors)
    else:
        curve,outliers=bass_curve,bass_outliers
        if len(matched_curve)>=8 and match.get('confidence',0)>=.75 and match.get('query_coverage',0)>=.8:
            bass_bpm=statistics.median(p['bpm'] for p in curve)
            full_bpm=statistics.median(p['bpm'] for p in matched_curve)
            ratio=bass_bpm/full_bpm
            if 1.8<=ratio<=2.2 or .45<=ratio<=.55:
                result.update(status='ambiguous',anchors=len(anchors),
                              notice='Bass and matched-score timing disagree by roughly a factor of two. Tempo and predictive turns are withheld until timing is consistent.')
                return result
    result['anchors']=len(anchors)
    result['rejected_timing_outliers']=outliers
    if len(anchors)>=4 and len(curve)>=2:
        result.update(status='estimated',bpm=round(statistics.median(p['bpm'] for p in curve),2),curve=curve,
                      reference_quality=reference['quality'],
                      notice='Score-relative quarter notes/minute; bass attacks are not counted as beats. Half/double-speed timing outliers are withheld. Repeats and edition differences can affect alignment.')
    return result
