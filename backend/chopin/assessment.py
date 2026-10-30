"""Versioned technical proxies, kept separate from the pianist's notes and level."""
import json


def assess(store,segment,reference,match,observed,expected,correct):
    wanted=sum(len(g['pitches']) for g in expected[match['reference_start']:match['reference_end']])
    played=sum(len(g['pitches']) for g in observed)
    precision=correct/played if played else 0
    recall=correct/wanted if wanted else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    coverage=len({b for _,b in match.get('pairs',[])})/max(1,len(expected))
    verified=reference['quality']=='verified'
    session=store.query('SELECT status,error FROM sessions WHERE id=?',(segment['session_id'],))[0]
    events_path=store.root/'sessions'/segment['session_id']/'events.jsonl'
    from .midi_files import journal_events
    capture_ok=session['status'] in ('saved','imported') and not session['error'] and not any(e.get('kind')=='capture_loss' for e in journal_events(events_path))
    reliable=verified and match['confidence']>=.85 and not any(n.get('grace') for n in reference['note_data'])
    level=('concert' if f1>=.98 else 'good' if f1>=.90 else 'practice') if reliable else None
    complete=coverage>=.95 and match['reference_start']==0 and match['reference_end']==len(expected)
    return {'version':'pitch-f1-v1','pitch_precision':round(100*precision,2),'pitch_recall':round(100*recall,2),
            'precision_score':round(100*f1,2),'coverage':round(coverage,4),'level':level,'piece_level':level if complete and reliable and capture_ok else None,
            'audio_candidate':bool(complete and reliable and capture_ok and f1>=.98 and not segment.get('discarded')),
            'reference_quality':reference['quality'],'capture_ok':capture_ok,
            'notice':'Technical pitch-alignment proxy only; concert is a threshold label, not a judgement of interpretation or audio quality. Partial passages do not update the automatic piece level. Unverified references and grace notes require review.',
            'thresholds':{'good':90,'concert':98,'whole_piece_coverage':.95}}


def piece_assessment(store,piece_id):
    """Latest current performance and latest eligible whole-piece level, by performance date."""
    piece=store.query('SELECT mastery,notes FROM pieces WHERE id=?',(piece_id,))
    if not piece:raise ValueError('Unknown piece')
    rows=store.query('''SELECT a.*,s.start,s.end,s.revision,s.discarded,s.complete,ps.started FROM analyses a
        JOIN segments s ON s.id=a.segment_id JOIN sessions ps ON ps.id=s.session_id
        WHERE s.piece_id=? AND s.discarded=0 ORDER BY ps.started DESC,s.start DESC,a.created DESC,a.id DESC''',(piece_id,))
    latest=None;level=None
    for row in rows:
        result=json.loads(row['result']);snapshot=result.get('segment_snapshot',{})
        if any(snapshot.get(k)!=row[k] for k in ('start','end','revision','discarded','complete')) or snapshot.get('piece_id')!=piece_id:continue
        assessment=result.get('assessment')
        item={'analysis_id':row['id'],'segment_id':row['segment_id'],'session_id':row['session_id'],'performed':row['started'],
              'assessment':assessment,'notes':result.get('notes',0)}
        if latest is None:latest=item
        if assessment and assessment.get('piece_level') and level is None:level=item
    suggestion=None
    if level and piece[0]['mastery'] is not None:
        automatic={'practice':1,'good':2,'concert':3}[level['assessment']['piece_level']]
        if abs(automatic-piece[0]['mastery'])>=.75:
            suggestion=f"Review your saved level ({piece[0]['mastery']}/3) alongside the automatic {level['assessment']['piece_level']} pitch assessment. Your notes and level have been retained."
    return {'latest_performance':latest,'automatic_level':level,'revision_suggestion':suggestion,'personal_notes':piece[0]['notes'],'personal_level':piece[0]['mastery']}
