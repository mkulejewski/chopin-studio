"""Audio-only retention recommendations. MIDI is retained until explicit session deletion."""
import json
import shutil
import logging
import uuid
from datetime import datetime, timezone

from .performance_quality import quality, source_annotations


def deleted(store, segment_id):
    return bool(store.query("SELECT id FROM recording_deletions WHERE segment_id=? AND scope='recording'", (segment_id,)))


def locked(store, session_id):
    return bool(store.query("SELECT id FROM recording_deletions WHERE session_id=? AND scope='recording'", (session_id,)))


def current_analysis(store, row):
    from .analysis_selection import AnalysisReader, AUDIO_REVIEW
    return AnalysisReader(store).latest_for_segment(row, policy=AUDIO_REVIEW)


def eligibility(store, row, result, reference_groups=None):
    if not row['piece_id']:
        return False, 'Unidentified: assign a piece and confirm completeness before keeping.'
    if row['kind']=='full_exercise':
        return True, 'Full-piece exercise: complete coverage, with practice mistakes allowed.'
    if row['complete'] or row['kind'] == 'complete':
        return True, 'Complete performance (automatic or manually confirmed).'
    details=json.loads(row.get('details') or '{}')
    if details.get('aborted_by_restart'):
        return False, 'Partial attempt: restarted from the opening; excluded from final audio selection.'
    source_match=details.get('match', {})
    if source_match.get('assumed'):
        return False, 'Open-score assumption only: review and confirm completeness before automatic audio retention.'
    return False, 'Not a complete performance.'


def needs_review(row):
    details = json.loads(row.get('details') or '{}')
    return (not row['piece_id'] or details.get('match', {}).get('assumed')
            or (not details.get('aborted_by_restart')
                and (row['kind'] != 'partial' or details.get('unclear_boundary'))))


def audio_assets(store, row, layout=None, renders=None, sample_rate=None):
    from .microphone import audio_layout, span_frame_bounds
    path, spans = audio_layout(store.root/'sessions'/row['session_id']) if layout is None else layout
    microphone = False
    if path:
        import soundfile as sf
        rate = sample_rate if sample_rate is not None else sf.info(path).samplerate
        microphone = any(left < right for left, right in
                         (span_frame_bounds(span, row['start'], row['end'], rate) for span in spans))
    if renders is None:
        renders = rendered_assets(store)
    files = renders.get(row['id'], [])
    return microphone, files


def rendered_assets(store):
    result = {}
    for job in store.query("SELECT result FROM jobs WHERE kind='render' AND status='done' AND result IS NOT NULL"):
        item = json.loads(job['result'])
        if isinstance(item,dict) and item.get('filename') and item.get('segment_id'):
            path = store.root/'audio'/item['filename']
            if path.is_file():result.setdefault(item['segment_id'], []).append(path)
    return result


def session_audio_bytes(store, session_id, renders=None, segment_ids=None):
    from .microphone import audio_layout
    path,_ = audio_layout(store.root/'sessions'/session_id)
    paths = {path} if path else set()
    if renders is None:
        renders = rendered_assets(store)
    if segment_ids is None:
        segment_ids = [row['id'] for row in store.query('SELECT id FROM segments WHERE session_id=?', (session_id,))]
    for ident in segment_ids:
        paths.update(renders.get(ident, []))
    raw = store.root/'sessions'/session_id/'microphone.pcm'
    if raw.exists():paths.add(raw)
    return sum(p.stat().st_size for p in paths)


def catalogue(store, piece_id=None):
    piece_filter = ' AND s.piece_id=?' if piece_id is not None else ''
    rows = store.query('''SELECT s.*,ps.started,ps.status AS session_status,ps.error AS session_error,
                         p.title,p.opus,COALESCE(c.choice,'auto') AS choice
                         FROM segments s JOIN sessions ps ON ps.id=s.session_id
                         LEFT JOIN pieces p ON p.id=s.piece_id
                         LEFT JOIN recording_choices c ON c.segment_id=s.id
                         WHERE ps.status NOT IN ('recording','saving','recovery_failed')
                         AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording')
                         ''' + piece_filter + ' ORDER BY ps.started DESC,s.start',
                       (piece_id,) if piece_id is not None else ())
    from .microphone import audio_layout, metadata
    layouts, audio_info, sample_rates, reference_groups = {}, {}, {}, {}
    renders = rendered_assets(store)
    audio_rows = []
    ranked = {}
    references = {}
    for row in rows:
        if row['session_id'] not in layouts:
            folder = store.root/'sessions'/row['session_id']
            audio_info[row['session_id']] = metadata(folder) or {}
            layouts[row['session_id']] = audio_layout(folder, audio_info[row['session_id']])
            path, _ = layouts[row['session_id']]
            if path:
                import soundfile as sf
                sample_rates[row['session_id']] = sf.info(path).samplerate
        microphone, files = audio_assets(store,row,layouts[row['session_id']],renders,sample_rates.get(row['session_id']))
        if not microphone and not files:
            continue
        row['microphone_audio'] = microphone
        row['rendered_audio_count'] = len(files)
        audio_rows.append(row)
        result = current_analysis(store, row)
        row['eligible'], row['eligibility_reason'] = eligibility(store, row, result, reference_groups)
        saved = audio_info[row['session_id']].get('headphone_play', {}).get(row['id'], {})
        evidence = ((result.get('audio') or {}).get('piano_presence') or
                    (saved.get('assessment') if all(saved.get(k) == row.get(k) for k in ('start', 'end', 'revision')) else None) or {})
        row['headphone_audio_excluded'] = bool(evidence.get('auto_discard')) and not files
        if row['headphone_audio_excluded']:
            row['eligible'] = False
            row['eligibility_reason'] = 'No discernible piano audio; excluded from the two-take limit.'
        audio = result.get('audio') or {}
        reference_id = result.get('reference_id')
        if reference_id not in references:
            ref = store.query('SELECT * FROM symbolic_scores WHERE id=?', (reference_id,))
            annotations, exempt = [], set()
            notation_error = False
            if ref:
                source = store.root/'references'/ref[0]['filename']
                if source.is_file() and source.suffix.lower() in ('.xml','.musicxml'):
                    try:
                        stat = source.stat()
                        annotations, exempt = source_annotations(str(source),stat.st_mtime_ns,stat.st_size)
                    except (OSError, ValueError): notation_error = True
            references[reference_id] = (ref[0] if ref and not notation_error else None, annotations, exempt)
        reference, annotations, exempt = references[reference_id]
        ranking = quality(result,reference,annotations,exempt) if reference else {
            'score':None,'components':{},'notice':'No current aligned analysis. Analyse the complete take; audio retained for review.'}
        row['quality_ranking'] = ranking
        row['quality_score'] = ranking['score']
        row['pitch_score'] = ranking['components'].get('notes')
        row['ranking_notice'] = ranking['notice']
        capture_ok = row['session_status'] in ('saved','imported') and not row['session_error'] and not audio.get('capture_error')
        if not capture_ok:
            row['quality_score'] = None
            row['ranking_notice'] = 'Capture integrity needs review; excluded from automatic musical ranking.'
            ranking.update(score=None,status='unavailable',notice=row['ranking_notice'])
        row['action'] = ('keep' if row['choice'] == 'keep' else
                         'review' if row['choice'] != 'remove' and not row['discarded']
                         and not row['eligible'] and needs_review(row) else 'remove')
        if row['eligible'] and not row['headphone_audio_excluded'] and (not row['discarded'] or row['choice']=='keep') and row['choice'] != 'remove':
            ranked.setdefault(row['piece_id'], []).append(row)
        row['reason'] = ('Manually kept.' if row['choice'] == 'keep' else 'Audio manually flagged for removal.' if row['choice'] == 'remove' or row['discarded']
                         else 'Uncertain audio: retained for manual review.' if row['action'] == 'review'
                         else 'Partial attempt: audio will be removed at shutdown.' if not row['eligible']
                         else 'Audio outside the default two-take shortlist.')
        if row['headphone_audio_excluded']:
            row['action'] = 'keep' if row['choice'] == 'keep' else 'remove'
            row['reason'] = 'Manually protected; no audible piano, so excluded from the two-take limit.' if row['choice'] == 'keep' else 'No audible piano detected; microphone-only cleanup pending.'
        elif row['eligible'] and row['quality_score'] is None and row['choice']=='auto' and not row['discarded']:
            row['action'] = 'review'
            row['reason'] = 'Complete audio retained until a musical comparison is available.'
    for takes in ranked.values():
        pins = [r for r in takes if r['choice'] == 'keep']
        automatic = [r for r in takes if r['choice']!='keep' and r['quality_score'] is not None]
        bases = {r['quality_ranking']['basis'] for r in automatic}
        if len(bases)>1:
            for row in automatic:
                row.update(action='review',reason='Complete takes use different reference or scoring targets; retained for comparison.')
            continue
        automatic.sort(key=lambda r:r['quality_score'],reverse=True)
        slots = max(0,2-len(pins))
        cutoff = automatic[slots-1]['quality_score'] if slots and len(automatic)>=slots else None
        tied = cutoff is not None and sum(abs(r['quality_score']-cutoff)<.25 for r in automatic)>1
        for index,row in enumerate(automatic):
            if tied and abs(row['quality_score']-cutoff)<.25:
                row.update(action='review',reason='Musical scores are tied at the shortlist boundary; audio retained for listening.')
            elif index<slots:
                row.update(action='keep',reason='One of the two best complete takes by the musical-evidence ranking.')
    return audio_rows


def session_files(store, session_id):
    """All owned artifacts, including rendered audio and exported bundles."""
    segments = store.query('SELECT id FROM segments WHERE session_id=?', (session_id,))
    paths = [store.root/'sessions'/session_id, store.root/'exports'/(session_id+'.zip')]
    paths += list((store.root/'exports').glob(session_id+'-*.zip'))
    paths += [store.root/'exports'/row['id'] for row in segments]
    paths += [store.root/'reports'/(row['id']+'.json') for row in store.query('SELECT id FROM analyses WHERE session_id=?', (session_id,))]
    paths += list((store.root/'reports').glob(session_id+'*'))
    for row in store.query('SELECT result FROM jobs WHERE result IS NOT NULL'):
        result = json.loads(row['result'])
        if isinstance(result, dict) and result.get('session_id') == session_id and result.get('filename'):
            paths.append(store.root/'audio'/result['filename'])
            paths.append((store.root/'audio'/result['filename']).with_suffix('.log'))
    return paths


def erase_path(path):
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def delete_session(store, session_id):
    # Stage owned files within the data root so a DB failure can restore them.
    paths = session_files(store, session_id)
    staging = store.root/'sessions'/('.deleting-'+session_id)
    staging.mkdir(exist_ok=True)
    manifest = staging/'manifest.json'
    with manifest.open('w') as output:
        json.dump([str(path.relative_to(store.root)) for path in paths],output)
        store.files.sync(output)
    store.files.sync_directory(staging)
    moved = []
    try:
        for index, source in enumerate(paths):
            if source.exists():
                destination = staging/str(index)
                store.files.replace(source, destination)
                moved.append((source, destination))
        with store.db:
            ids = [r['id'] for r in store.query('SELECT id FROM segments WHERE session_id=?', (session_id,))]
            report_ids = {r['id'] for r in store.query('SELECT id FROM reports WHERE session_id=?',(session_id,))}
            for ident in ids:
                store.db.execute('DELETE FROM recording_choices WHERE segment_id=?', (ident,))
            for table in ('recording_deletions','segments','segment_history','analyses','reports'):
                store.db.execute('DELETE FROM '+table+' WHERE session_id=?', (session_id,))
            # Completed jobs can contain old file names and complete analysis payloads.
            for row in store.query('SELECT id,result FROM jobs WHERE result IS NOT NULL'):
                result = json.loads(row['result'])
                owns = isinstance(result, dict) and (result.get('session_id') == session_id or result.get('segment_snapshot',{}).get('id') in ids or result.get('report_id') in report_ids)
                owns = owns or isinstance(result, list) and any(isinstance(item, dict) and item.get('session_id') == session_id for item in result)
                if owns:store.db.execute('DELETE FROM jobs WHERE id=?', (row['id'],))
            store.db.execute('DELETE FROM settings WHERE key=?', ('organised:'+session_id,))
            store.db.execute('DELETE FROM sessions WHERE id=?', (session_id,))
    except Exception:
        for source, destination in reversed(moved):
            store.files.replace(destination, source)
        shutil.rmtree(staging)
        raise
    shutil.rmtree(staging)


def discard_unheard_microphone(store, row, result):
    """Apply the explicitly requested headphone-audio policy, preserving MIDI."""
    assessment = (result.get('audio') or {}).get('piano_presence') or {}
    if not assessment.get('auto_discard'):
        return False
    from .microphone import audio_layout, metadata, write_metadata
    with store.lock:
        session = store.query('SELECT status,error FROM sessions WHERE id=?', (row['session_id'],))
        current = store.query('SELECT * FROM segments WHERE id=?', (row['id'],))
        if (not session or session[0]['status'] not in ('saved', 'imported') or session[0]['error']
                or not current or any(current[0].get(k) != row.get(k) for k in ('session_id', 'start', 'end', 'revision'))):
            return False
        folder = store.root/'sessions'/row['session_id']
        path, _ = audio_layout(folder)
        if path is None:
            return False
        stat = path.stat()
        if assessment.get('input_audio') != {'filename': path.name, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}:
            return False  # Do not delete bytes changed since they were inspected.
        pin = store.query("SELECT segment_id FROM recording_choices WHERE segment_id=? AND choice='keep'", (row['id'],))
        overlaps = store.query('SELECT id FROM segments WHERE session_id=? AND id<>? AND start<? AND end>?',
                              (row['session_id'], row['id'], row['end'], row['start']))
        if overlaps:
            return False
        info = metadata(folder)
        entries = dict(info.get('headphone_play', {}))
        entries[row['id']] = {'start': row['start'], 'end': row['end'], 'revision': row['revision'], 'assessment': assessment,
                             'action': 'kept' if pin else 'pending', 'notice': assessment['notice']}
        write_metadata(folder, {**info, 'headphone_play': entries}, files=store.files)
        if pin:
            return False
        pending = store.query("SELECT * FROM recording_deletions WHERE segment_id=? AND scope='headphone' AND status='pending'", (row['id'],))
        if pending:
            deletion = pending[0]
        else:
            ident = 'headphone-v1-'+uuid.uuid4().hex
            store.execute("INSERT INTO recording_deletions(id,session_id,segment_id,start,end,created,scope) VALUES(?,?,?,?,?,?,'headphone')",
                          (ident, row['session_id'], row['id'], row['start'], row['end'], datetime.now(timezone.utc).isoformat()))
            deletion = store.query('SELECT * FROM recording_deletions WHERE id=?', (ident,))[0]
        finish_deletion(store, deletion)
        return True


def finish_headphone_deletion(store, deletion):
    from .microphone import compact_audio, metadata, write_metadata
    folder = store.root/'sessions'/deletion['session_id']
    # A keep decision made before a retry still wins.
    if store.query("SELECT segment_id FROM recording_choices WHERE segment_id=? AND choice='keep'", (deletion['segment_id'],)):
        store.execute("UPDATE recording_deletions SET status='cancelled' WHERE id=?", (deletion['id'],))
        return
    compact_audio(folder, deletion['start'], deletion['end'], deletion['id'], files=store.files)
    info = metadata(folder) or {}
    entries = dict(info.get('headphone_play', {}))
    entry = entries.get(deletion['segment_id'], {})
    entries[deletion['segment_id']] = {**entry, 'action': 'discarded',
        'notice': 'No discernible piano during MIDI playing: microphone audio discarded; MIDI retained. This audio does not count toward the two-take limit.'}
    write_metadata(folder, {**info, 'headphone_play': entries}, files=store.files)
    # Only microphone copies and mixed export caches are invalidated. Synthetic
    # MIDI renders and MIDI-only exports remain usable.
    for path in (store.root/'exports').glob('microphone-clip-'+deletion['session_id']+'-*.flac'):
        path.unlink(missing_ok=True)
    for path in (store.root/'exports').glob(deletion['session_id']+'*.zip'):
        path.unlink(missing_ok=True)
    store.files.sync_directory(folder)
    store.execute("UPDATE recording_deletions SET status='done' WHERE id=?", (deletion['id'],))


def delete_take(store, row):
    microphone, files = audio_assets(store,row)
    if not microphone and not files:
        raise ValueError('No saved audio remains for this take. Its MIDI is retained.')
    # Removing shared microphone samples requires non-overlapping activity bounds.
    if microphone:
        overlaps=store.query("SELECT id FROM segments WHERE session_id=? AND id<>? AND start<? AND end>? AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=segments.id AND d.scope='recording')",(row['session_id'],row['id'],row['end'],row['start']))
        if overlaps:raise ValueError('This interval overlaps another take. Correct the timeline before deleting its audio.')
    ident = uuid.uuid4().hex
    store.execute("INSERT INTO recording_deletions(id,session_id,segment_id,start,end,created,scope) VALUES(?,?,?,?,?,?,'audio')",
                  (ident,row['session_id'],row['id'],row['start'],row['end'],datetime.now(timezone.utc).isoformat()))
    finish_deletion(store, store.query('SELECT * FROM recording_deletions WHERE id=?', (ident,))[0])


def finish_deletion(store, deletion):
    """Idempotent audio-only cleanup; never rewrite MIDI, analyses or session history."""
    if deletion.get('scope') == 'headphone':
        return finish_headphone_deletion(store, deletion)
    from .microphone import compact_audio
    folder = store.root/'sessions'/deletion['session_id']
    compact_audio(folder, deletion['start'], deletion['end'], deletion['id'], files=store.files)
    # Invalidate audio copies only. MIDI exports and source imports remain intact.
    for row in store.query('SELECT id FROM segments WHERE session_id=?',(deletion['session_id'],)):
        directory = store.root/'exports'/row['id']
        if directory.exists():
            for path in directory.glob('*.flac'):path.unlink(missing_ok=True)
            for path in directory.glob('*.wav'):path.unlink(missing_ok=True)
    for path in (store.root/'exports').glob(deletion['session_id']+'*.zip'):path.unlink(missing_ok=True)
    for job in store.query("SELECT id,result FROM jobs WHERE kind='render' AND result IS NOT NULL"):
        result = json.loads(job['result'])
        if isinstance(result,dict) and result.get('segment_id') == deletion['segment_id']:
            if result.get('filename'):
                (store.root/'audio'/result['filename']).unlink(missing_ok=True)
                (store.root/'audio'/result['filename']).with_suffix('.log').unlink(missing_ok=True)
            store.execute('DELETE FROM jobs WHERE id=?',(job['id'],))
    store.files.sync_directory(folder)
    store.execute("UPDATE recording_deletions SET status='done',scope='audio' WHERE id=?",(deletion['id'],))


def recover_deletions(store):
    # A staged whole-session deletion either restores files if the DB transaction
    # did not commit, or finishes erasing them if it did.
    for staging in (store.root/'sessions').glob('.deleting-*'):
        manifest = staging/'manifest.json'
        if not manifest.exists():continue
        ident = staging.name.removeprefix('.deleting-')
        if store.query('SELECT id FROM sessions WHERE id=?',(ident,)):
            for index, relative in enumerate(json.loads(manifest.read_text())):
                saved = staging/str(index)
                if saved.exists():
                    store.files.replace(saved, store.root/relative)
        shutil.rmtree(staging)
    for row in store.query("SELECT * FROM recording_deletions WHERE status='pending'"):
        try:
            finish_deletion(store, row)
        except Exception as exc:
            store.execute('UPDATE sessions SET error=? WHERE id=?',('Recording cleanup incomplete; restart to retry: '+str(exc),row['session_id']))
    # Reproducible caches from the previous version are not second masters.
    for path in (store.root/'exports').glob('microphone-clip-*.flac'):path.unlink(missing_ok=True)
    for path in (store.root/'exports').glob('*/microphone-*.flac'):path.unlink(missing_ok=True)
    for path in (store.root/'exports').glob('*.zip'):path.unlink(missing_ok=True)


def automatic_cleanup(store, *, shutdown=False):
    """Re-evaluate under the write lock so a keep flag wins over deletion.

    Unidentified/uncertain takes stay available for manual review. Flagged audio,
    including partial attempts and sessions with capture errors, is removed only
    at shutdown. Keep choices always protect audio.
    """
    if not shutdown:
        return
    with store.lock:
        if store.query("SELECT id FROM sessions WHERE status IN ('recording','saving')"):
            return
        if store.query("SELECT id FROM jobs WHERE status IN ('queued','running')"):
            return
        rows = catalogue(store)
        candidates = {r['id']: r for r in rows if r['action'] == 'remove'
                      and r['session_status'] in ('saved', 'imported', 'incomplete', 'recovered')}
        # Ignore deadlines persisted by the earlier timed-cleanup policy.
        store.execute("DELETE FROM settings WHERE key='audio_cleanup_pending'")
        for ident, row in candidates.items():
            try:
                if row.get('headphone_audio_excluded'):
                    result = current_analysis(store, row)
                    if not (result.get('audio') or {}).get('piano_presence'):
                        from .microphone import metadata
                        saved = (metadata(store.root/'sessions'/row['session_id']) or {}).get('headphone_play', {}).get(row['id'], {})
                        result = {'audio': {'piano_presence': saved.get('assessment')}}
                    discard_unheard_microphone(store, row, result)
                else:
                    delete_take(store, row)
            except Exception:
                logging.getLogger(__name__).exception('Automatic audio cleanup deferred for %s', ident)
