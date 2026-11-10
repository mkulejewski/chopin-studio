"""Audio-only retention recommendations. MIDI is retained until explicit session deletion."""
import json
import shutil
import uuid
from datetime import datetime, timezone

from .organisation import groups


def deleted(store, segment_id):
    return bool(store.query("SELECT id FROM recording_deletions WHERE segment_id=? AND scope='recording'", (segment_id,)))


def locked(store, session_id):
    return bool(store.query("SELECT id FROM recording_deletions WHERE session_id=? AND scope='recording'", (session_id,)))


def current_analysis(store, row):
    for analysis in store.query('SELECT result FROM analyses WHERE segment_id=? ORDER BY created DESC,id DESC', (row['id'],)):
        result = json.loads(analysis['result'])
        snapshot = result.get('segment_snapshot', {})
        if all(snapshot.get(k) == row.get(k) for k in ('piece_id', 'start', 'end', 'revision', 'discarded', 'complete')):
            return result
    return {}


def eligibility(store, row, result):
    if not row['piece_id']:
        return False, 'Unidentified: assign a piece and confirm completeness before keeping.'
    if row['complete'] or row['kind'] == 'complete':
        return True, 'Complete performance (automatic or manually confirmed).'
    match = result.get('match') or json.loads(row.get('details') or '{}').get('match', {})
    reference = store.query('SELECT notes FROM symbolic_scores WHERE id=?', (match.get('reference_id'),))
    if reference:
        total = len(groups(json.loads(reference[0]['notes']), tolerance=.0001))
        coverage = len({b for _, b in match.get('pairs', [])}) / max(1, total)
        if (total >= 8 and match.get('confidence', 0) >= .75 and coverage >= .80
                and match.get('reference_start', total) <= .10 * total
                and match.get('reference_end', 0) >= .90 * total):
            return True, f'Near-complete: {coverage:.0%} matched groups, including the opening and ending buffer.'
    return False, 'Partial or uncertain: audio flagged for removal; you can mark it complete after review.'


def audio_assets(store, row, layout=None, renders=None):
    from .microphone import audio_layout
    path, spans = audio_layout(store.root/'sessions'/row['session_id']) if layout is None else layout
    microphone = False
    if path:
        import soundfile as sf
        rate = sf.info(path).samplerate
        microphone = any(min(row['end'], span['start']+span['frames']/rate) > max(row['start'],span['start']) for span in spans)
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


def session_audio_bytes(store, session_id):
    from .microphone import audio_layout
    path,_ = audio_layout(store.root/'sessions'/session_id)
    paths = {path} if path else set()
    renders = rendered_assets(store)
    for row in store.query('SELECT id FROM segments WHERE session_id=?',(session_id,)):
        paths.update(renders.get(row['id'], []))
    raw = store.root/'sessions'/session_id/'microphone.pcm'
    if raw.exists():paths.add(raw)
    return sum(p.stat().st_size for p in paths)


def catalogue(store):
    rows = store.query('''SELECT s.*,ps.started,ps.status AS session_status,ps.error AS session_error,
                         p.title,p.opus,COALESCE(c.choice,'auto') AS choice
                         FROM segments s JOIN sessions ps ON ps.id=s.session_id
                         LEFT JOIN pieces p ON p.id=s.piece_id
                         LEFT JOIN recording_choices c ON c.segment_id=s.id
                         WHERE ps.status NOT IN ('recording','saving','recovery_failed')
                         AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording')
                         ORDER BY ps.started DESC,s.start''')
    from .microphone import audio_layout
    layouts = {}
    renders = rendered_assets(store)
    audio_rows = []
    ranked = {}
    for row in rows:
        if row['session_id'] not in layouts:
            layouts[row['session_id']] = audio_layout(store.root/'sessions'/row['session_id'])
        microphone, files = audio_assets(store,row,layouts[row['session_id']],renders)
        if not microphone and not files:
            continue
        row['microphone_audio'] = microphone
        row['rendered_audio_count'] = len(files)
        audio_rows.append(row)
        result = current_analysis(store, row)
        row['eligible'], row['eligibility_reason'] = eligibility(store, row, result)
        assessment = result.get('assessment') or {}
        audio = result.get('audio') or {}
        row['pitch_score'] = assessment.get('precision_score') if assessment.get('reference_quality') == 'verified' and assessment.get('level') else None
        row['ranking_notice'] = ('Verified-reference pitch proxy; interpretation still needs listening.' if row['pitch_score'] is not None
                                 else 'No reliable whole-take score: newest take wins ties; review manually.')
        capture_ok = row['session_status'] in ('saved','imported') and not row['session_error'] and not audio.get('capture_error')
        row['_rank'] = (int(capture_ok), int(row['pitch_score'] is not None), row['pitch_score'] or 0,
                        -audio.get('clipped_sample_fraction', 0), row['started'], row['id'])
        row['action'] = 'remove'
        if row['eligible'] and (not row['discarded'] or row['choice']=='keep') and row['choice'] != 'remove':
            ranked.setdefault(row['piece_id'], []).append(row)
        row['reason'] = ('Audio manually flagged for removal.' if row['choice'] == 'remove' or row['discarded']
                         else row['eligibility_reason'] if not row['eligible'] else 'Audio outside the default two-take shortlist.')
    for takes in ranked.values():
        pins = [r for r in takes if r['choice'] == 'keep']
        automatic = sorted((r for r in takes if r['choice'] != 'keep'), key=lambda r: r['_rank'], reverse=True)
        for index, row in enumerate(pins + automatic):
            if row['choice'] == 'keep' or index < max(2, len(pins)):
                row['action'] = 'keep'
                row['reason'] = 'Manually kept.' if row['choice'] == 'keep' else 'One of the two best eligible takes by the available evidence.'
    for row in audio_rows:
        del row['_rank']
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
    from .microphone import sync_directory
    import os
    with manifest.open('w') as output:
        json.dump([str(path.relative_to(store.root)) for path in paths],output)
        output.flush()
        os.fsync(output.fileno())
    sync_directory(staging)
    moved = []
    try:
        for index, source in enumerate(paths):
            if source.exists():
                destination = staging/str(index)
                source.rename(destination)
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
            destination.rename(source)
        shutil.rmtree(staging)
        raise
    shutil.rmtree(staging)


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
    from .microphone import compact_audio, sync_directory
    folder = store.root/'sessions'/deletion['session_id']
    compact_audio(folder, deletion['start'], deletion['end'], deletion['id'])
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
    sync_directory(folder)
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
                if saved.exists():saved.rename(store.root/relative)
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
