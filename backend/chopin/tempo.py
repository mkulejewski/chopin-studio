"""Score-relative MIDI tempo; score onsets are quarter notes, capture onsets seconds."""
import statistics

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein


def infer_tempo(observed, reference, match):
    # Import here to keep recognition independent of tempo estimation.
    from .organisation import groups, melody

    result = {'status': 'insufficient', 'bpm': None, 'unit': 'quarter notes/min',
              'method': None, 'anchors': 0, 'curve': [],
              'notice': 'Not enough reliable score timing anchors.'}
    if not match.get('reference_id'):
        return result
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
    if len(anchors) < 4:
        anchors = []
        og, rg = groups(observed), reference['groups']
        for a, b in match.get('pairs', []):
            if a < len(og) and b < len(rg) and og[a]['pitches'] & rg[b]['pitches']:
                anchors.append({'time': og[a]['onset'], 'beat': rg[b]['onset'], 'measure': rg[b]['measure']})
        result['method'] = 'matched score notes'
    # Median slopes over multiple anchors suppress rolled-chord timing spikes.
    # Do not bridge long pauses, repeats or backwards score motion.
    estimates = []
    curve = []
    for i, anchor in enumerate(anchors):
        local = []
        for previous in anchors[max(0, i-4):i]:
            seconds = anchor['time']-previous['time']
            beats = anchor['beat']-previous['beat']
            if .15 <= seconds <= 8 and beats >= 1:
                local.append(60*beats/seconds)
        if local:
            bpm = statistics.median(local)
            estimates.append(bpm)
            curve.append({**anchor, 'bpm': round(bpm, 2)})
    result['anchors'] = len(anchors)
    if len(anchors) >= 4 and len(estimates) >= 2:
        result.update(status='estimated', bpm=round(statistics.median(estimates), 2), curve=curve,
                      reference_quality=reference['quality'],
                      notice='Score-relative MIDI estimate; rubato is preserved. Repeats and edition differences can affect alignment.')
    return result
