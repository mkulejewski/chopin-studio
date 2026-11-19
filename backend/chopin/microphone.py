"""Portable microphone PCM/FLAC persistence, measurements and interval exports."""

import json

import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

from .platform.files import LOCAL_FILES, staging_path

RATE = 48000


def metadata(folder):
    path = folder / 'microphone.json'
    return json.loads(path.read_text()) if path.exists() else None


def write_metadata(folder, data, *, files=LOCAL_FILES):
    path = folder / 'microphone.json'
    with staging_path(files, path) as temporary:
        with temporary.open('w') as stream:
            json.dump(data, stream, indent=2)
            files.sync(stream)
        files.replace(temporary, path)
        files.sync_directory(folder)


def finalise(folder, data, *, files=LOCAL_FILES):
    raw = folder / 'microphone.pcm'
    if raw.exists():
        target = folder / 'microphone.flac'
        with staging_path(files, target, suffix='.flac') as temporary:
            with sf.SoundFile(raw, samplerate=RATE, channels=1, format='RAW', subtype='PCM_16', endian='LITTLE') as source:
                data['duration'] = len(source) / RATE
                with sf.SoundFile(temporary, 'w', samplerate=RATE, channels=1, format='FLAC', subtype='PCM_16') as output:
                    for block in source.blocks(blocksize=65536, dtype='int16'):
                        output.write(block)
            with temporary.open('rb') as stream:
                files.sync(stream)
            files.replace(temporary, target)
        data['filename'] = target.name
        write_metadata(folder, data, files=files)
        raw.unlink()
        files.sync_directory(folder)
    return data


def audio_layout(folder, info=None):
    info = metadata(folder) if info is None else info
    if not info:
        return None, []
    filename = info.get('filename', 'microphone.flac')
    path = folder / filename if filename else None
    if not path or not path.exists():
        return None, []
    with sf.SoundFile(path) as source:
        spans = info.get('spans', [{'start': info['offset_seconds'], 'frame': 0, 'frames': len(source)}])
    return path, spans


def span_frame_bounds(span, start, end, rate):
    """Use the same nearest-sample interval for reading, deletion and availability.

    Capture timestamps need not lie on the audio sample grid. Testing continuous
    time overlap after compaction can report a fraction of a sample as audio even
    though no frame can be read for that interval.
    """
    frames = span['frames']
    left = max(0, min(frames, round((start - span['start']) * rate)))
    right = max(0, min(frames, round((end - span['start']) * rate))) if end is not None else frames
    return left, right


def audio_blocks(folder, start=0, end=None, dtype='float64'):
    path, spans = audio_layout(folder)
    if path is None:
        return
    with sf.SoundFile(path) as source:
        rate = source.samplerate
        for span in spans:
            left, right = span_frame_bounds(span, start, end, rate)
            if right <= left:
                continue
            source.seek(span['frame'] + left)
            while left < right:
                block = source.read(min(rate, right - left), dtype=dtype, always_2d=True)
                if not len(block):break
                yield span['start'] + left / rate, block, rate
                left += len(block)


def envelope(folder, start=0, end=None):
    """10 ms bins in original session time, including after explicit audio removal."""
    info = metadata(folder)
    times, rms, peaks, clipping, samples = [], [], [], 0, 0
    rate = RATE
    for timestamp, block, rate in audio_blocks(folder, start, end):
        block = block.mean(axis=1)
        hop = max(1, rate // 100)
        samples += len(block)
        clipping += int(np.sum(np.abs(block) >= .999))
        for index in range(0, len(block), hop):
            part = block[index:index + hop]
            times.append(timestamp + index / rate)
            rms.append(float(np.sqrt(np.mean(part * part))))
            peaks.append(float(np.max(np.abs(part))))
    if not samples:
        return None
    return {'times': np.array(times), 'rms': np.array(rms), 'peaks': np.array(peaks),
            'clipped_samples': clipping, 'samples': samples, 'rate': rate, 'info': info}


def compact_audio(folder, start, end, deletion_id, *, files=LOCAL_FILES):
    """Remove an explicitly deleted interval from the single audio copy, losslessly.

    Physical frames are packed together; spans retain original session timestamps.
    A durable metadata swap precedes removing the previous generation.
    """
    info = metadata(folder)
    if not info:
        return
    if deletion_id in info.get('removed_intervals', []):
        # A prior attempt may have replaced the manifest but failed its directory sync.
        files.sync_directory(folder)
        cleanup_generations(folder, info, files=files)
        return
    path, spans = audio_layout(folder, info)
    if path is None:
        return
    import uuid
    target = folder / ('microphone-retained-' + uuid.uuid4().hex + '.flac')
    updated, frame = [], 0
    try:
        with sf.SoundFile(path) as source, sf.SoundFile(target, 'w', samplerate=source.samplerate,
                channels=source.channels, format='FLAC', subtype='PCM_16') as output:
            rate = source.samplerate
            for span in spans:
                cut_left, cut_right = span_frame_bounds(span, start, end, rate)
                for left, right in ((0, cut_left), (cut_right, span['frames'])):
                    if right <= left:continue
                    updated.append({'start': span['start'] + left/rate, 'frame': frame, 'frames': right-left})
                    source.seek(span['frame']+left)
                    remaining = right-left
                    while remaining:
                        block = source.read(min(65536,remaining), dtype='int16', always_2d=True)
                        if not len(block):raise ValueError('Audio ended unexpectedly during deletion; original retained.')
                        output.write(block)
                        remaining -= len(block)
                    frame += right-left
        with target.open('rb') as stream:
            files.sync(stream)
        info = {**info, 'filename': target.name if frame else None, 'spans': updated,
                'stored_duration': frame/rate, 'removed_intervals': info.get('removed_intervals', [])+[deletion_id]}
        write_metadata(folder, info, files=files)
    except Exception:
        # If the manifest swap succeeded, leave the referenced generation intact.
        if (metadata(folder) or {}).get('filename') != target.name:target.unlink(missing_ok=True)
        raise
    cleanup_generations(folder, info, files=files)


def cleanup_generations(folder, info, *, files=LOCAL_FILES):
    for path in [folder/'microphone.flac', *folder.glob('microphone-retained-*.flac')]:
        if path.name != info.get('filename'):path.unlink(missing_ok=True)
    files.sync_directory(folder)


def audio_ranges(folder, duration, cooldown):
    env = envelope(folder)
    if env is None or not len(env['times']):
        return []
    levels = env['rms']
    # Relative floor suppresses steady room noise; boundaries are proposals only.
    threshold = max(.003, float(np.percentile(levels, 20)) * 3,
                    float(np.percentile(levels, 95)) * .08)
    activity = env['times'][levels > threshold]
    if not len(activity):
        return []
    cuts = np.flatnonzero(np.diff(activity) >= cooldown) + 1
    return [(max(0, float(part[0]) - .3), min(duration, float(part[-1]) + 1.5), True)
            for part in np.split(activity, cuts) if len(part) and part[0] < duration]


def analyse_audio(folder, segment, notes):
    env = envelope(folder, segment['start'], segment['end'])
    if env is None or not len(env['times']):
        saved = (metadata(folder) or {}).get('headphone_play', {}).get(segment.get('id'), {})
        return {'available': False, 'notice': saved.get('notice', 'No microphone audio covers this activity.'),
                'piano_presence': saved.get('assessment'), 'discarded_for_headphone_play': saved.get('action') == 'discarded'}
    from .headphone_audio import assess_piano_presence
    presence = assess_piano_presence(folder, segment, notes, env)
    times, levels = env['times'], env['rms']
    db = 20 * np.log10(np.maximum(levels, 1e-7))
    # Rising energy peaks detect acoustic attacks, not pitches or individual chord notes.
    rise = np.maximum(0, db - np.concatenate((db[:3], db[:-3]))) if len(db) >= 3 else np.zeros_like(db)
    indices, _ = find_peaks(rise, height=5, prominence=3, distance=6)
    indices = indices[levels[indices] > max(.002, float(np.percentile(levels, 20)) * 2)]
    attacks = times[indices]
    midi = []
    for note in sorted(notes, key=lambda n: n['onset']):
        if not midi or note['onset'] - midi[-1]['time'] > .045:
            midi.append({'time': note['onset'], 'velocities': []})
        midi[-1]['velocities'].append(note['velocity'])
    result = {'available': True, 'version': 'acoustic-envelope-v1', 'piano_presence': presence,
              'rms_dbfs': float(20 * np.log10(max(float(np.sqrt(np.mean(levels ** 2))), 1e-7))),
              'peak_dbfs': float(20 * np.log10(max(float(env['peaks'].max()), 1e-7))),
              'clipped_sample_fraction': env['clipped_samples'] / max(1, env['samples']),
              'quiet_fraction': float(np.mean(db < -50)), 'acoustic_attacks': len(attacks),
              'capture_error': env['info'].get('capture_error'),
              'coverage_seconds': env['samples'] / env['rate'],
              'notice': 'Microphone levels are dBFS, not calibrated loudness. Room noise, reverb, automatic gain and overlapping notes affect these measurements. Acoustic attacks do not establish pitch correctness or pedal quality.',
              'correlation': {'status': 'unavailable', 'notice': 'At least five clear, consistently aligned MIDI/acoustic attacks are needed.'}}
    if len(midi) < 5 or len(attacks) < 5 or env['info'].get('capture_error'):
        return result
    onsets = np.array([g['time'] for g in midi])
    # Fit a constant latency with one-to-one nearest matches. Refuse ambiguous fits.
    def pairs(delay, selected):
        targets = onsets[selected] + delay
        right = np.clip(np.searchsorted(attacks, targets), 0, len(attacks) - 1)
        left = np.maximum(0, right - 1)
        nearest = np.where(np.abs(attacks[left] - targets) < np.abs(attacks[right] - targets), left, right)
        used = set()
        matches = []
        for i, index, residual in zip(selected, nearest, attacks[nearest] - targets):
            if abs(residual) <= .045 and index not in used:
                used.add(int(index))
                matches.append((int(i), int(index), float(residual)))
        return matches
    # Fit across the whole take with at most 3,000 groups, then match all groups.
    selected = np.unique(np.linspace(0, len(onsets) - 1, min(3000, len(onsets))).astype(int))
    candidates = []
    for lag in np.arange(-.5, .501, .01):
        matched = pairs(float(lag), selected)
        candidates.append((float(lag), len(matched), float(np.mean([abs(p[2]) for p in matched])) if matched else 1))
    candidates.sort(key=lambda item: (-item[1], item[2]))
    delay, count, _ = candidates[0]
    competing = max((n for d, n, _ in candidates if abs(d - delay) > .1), default=0)
    if count < 5 or count / len(selected) < .45 or competing >= count * .9:
        result['correlation']['status'] = 'uncertain'
        return result
    matched = pairs(delay, selected)
    delay = float(np.median([attacks[j] - onsets[i] for i, j, _ in matched]))
    matched = pairs(delay, np.arange(len(onsets)))
    events = []
    for i, j, residual in matched[:2000]:
        at = indices[j]
        events.append({'midi_time': float(onsets[i]), 'audio_time': float(attacks[j]),
                       'residual_ms': residual * 1000, 'attack_dbfs': float(np.max(db[at:at + 8])),
                       'midi_velocity': float(np.mean(midi[i]['velocities']))})
    result['correlation'] = {'status': 'estimated', 'audio_minus_midi_seconds': delay,
                             'matched_groups': len(matched), 'midi_groups': len(midi),
                             'median_absolute_residual_ms': float(np.median([abs(p[2]) for p in matched]) * 1000),
                             'events': events, 'events_truncated': len(matched) > 2000,
                             'notice': 'Estimated constant offset within ±0.5 s; residuals include detection error, hardware latency, room propagation and clock drift. They are not performance timing errors.'}
    return result


def export_audio(store, segment):
    """A request-owned temporary clip, never a persistent second recording."""
    folder = store.root / 'sessions' / segment['session_id']
    path, _ = audio_layout(folder)
    if path is None:
        raise ValueError('This session has no saved microphone recording.')
    target = store.files.temporary_path(
        store.root / 'exports', prefix='microphone-clip-' + segment['session_id'] + '-', suffix='.flac',
    )
    frames = 0
    try:
        with sf.SoundFile(path) as source, sf.SoundFile(target, 'w', samplerate=source.samplerate,
                channels=source.channels, format='FLAC', subtype='PCM_16') as output:
            for _, block, _ in audio_blocks(folder, segment['start'], segment['end'], dtype='int16'):
                output.write(block)
                frames += len(block)
        if not frames:raise ValueError('No microphone audio covers this activity.')
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def export_stem(store, segment):
    import re
    session = store.query('SELECT started FROM sessions WHERE id=?', (segment['session_id'],))[0]
    from datetime import datetime, timezone
    stamp = datetime.fromisoformat(session['started']).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    piece = re.sub(r'[^a-zA-Z0-9_-]', '-', segment['piece_id'] or 'unidentified')[:80]
    return f"{stamp}__{piece}__{segment['session_id'][:8]}__{segment['id'][:8]}__{segment['start']:.3f}-{segment['end']:.3f}s"
