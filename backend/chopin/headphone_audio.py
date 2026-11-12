"""Conservative MIDI-guided detection of microphone takes without audible piano.

This infers absent acoustic piano, not a physical headphone-jack state. A quiet
recording alone is never sufficient: reliable MIDI, coverage and tonal checks
are required. Uncertain/corrupt captures are retained.
"""
import math
import numpy as np
import soundfile as sf

VERSION = 'inaudible-piano-v1'


def assess_piano_presence(folder, segment, notes, env):
    from .microphone import audio_layout
    result = {'version': VERSION, 'status': 'uncertain', 'auto_discard': False,
              'source': 'midi-and-microphone', 'jack_status': 'unavailable',
              'notice': 'Not enough reliable evidence to discard microphone audio.'}
    if env is None or env['info'].get('capture_error') or env['rate'] < 8000:
        return result
    usable = [n for n in notes if isinstance(n.get('pitch'), (int, float))
              and math.isfinite(n.get('onset', float('nan')))
              and n.get('velocity', 0) > 0 and n.get('duration', 0) >= .03]
    groups = []
    for note in sorted(usable, key=lambda n: n['onset']):
        if not groups or note['onset']-groups[-1]['time'] > .045:
            groups.append({'time': note['onset'], 'pitches': [], 'strong': False})
        groups[-1]['pitches'].append(note['pitch'])
        groups[-1]['strong'] |= note.get('velocity', 0) >= 35
    result['midi_groups'] = len(groups)
    if sum(g['strong'] for g in groups) < 8 or groups[-1]['time']-groups[0]['time'] < 4:
        return result
    start, end = groups[0]['time'], min(segment['end'], groups[-1]['time']+.4)
    active = (env['times'] >= start) & (env['times'] < end)
    levels = env['rms'][active]
    coverage = len(levels)*.01/max(.01, end-start)
    result['coverage_fraction'] = min(1, coverage)
    if not len(levels) or not np.all(np.isfinite(levels)) or coverage < .95:
        result['notice'] = 'Incomplete microphone coverage; audio kept for review.'
        return result
    path, spans = audio_layout(folder)
    if path is None:
        return result
    stat = path.stat()
    result['input_audio'] = {'filename': path.name, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    db = 20*np.log10(np.maximum(levels, 1e-7))
    result.update(quiet_fraction=float(np.mean(db < -40)), level_spread_db=float(np.percentile(db, 95)-np.percentile(db, 10)), rms_p90_dbfs=float(np.percentile(db, 90)),
                  rms_p95_dbfs=float(np.percentile(db, 95)))
    selected = np.unique(np.linspace(0, len(groups)-1, min(64, len(groups))).astype(int))
    checked, tonal = 0, 0
    with sf.SoundFile(path) as source:
        rate = source.samplerate
        def window(at, duration=.18):
            stop = min(segment['end'], at+duration)
            at = max(segment['start'], at)
            if stop-at < .12:
                return None
            chunks, frames = [], 0
            for span in spans:
                left = max(0, round((at-span['start'])*rate))
                right = min(span['frames'], round((stop-span['start'])*rate))
                if right <= left:
                    continue
                source.seek(span['frame']+left)
                block = source.read(right-left, always_2d=True).mean(axis=1)
                chunks.append(block)
                frames += len(block)
            if frames < .98*(stop-at)*rate:
                return None
            return np.concatenate(chunks)
        for index in selected:
            group = groups[index]
            valid, heard = False, False
            for delay in (-.5, -.25, 0, .15, .35, .55):
                samples = window(group['time']+delay)
                if samples is None:
                    continue
                valid = True
                samples = samples-np.mean(samples)
                power = np.abs(np.fft.rfft(samples*np.hanning(len(samples))))**2
                frequencies = np.fft.rfftfreq(len(samples), 1/rate)
                band = (frequencies >= 25) & (frequencies <= min(8000, rate*.45))
                total = float(np.sum(power[band]))
                if total <= 1e-15:
                    continue
                # Any strong narrow-band tone protects a quiet recording, even
                # when pitch, latency or tuning differs from the MIDI estimate.
                spectrum = power[band]
                if spectrum.max()/total > .06 and spectrum.max() > 20*max(float(np.median(spectrum)), 1e-20):
                    heard = True
                for pitch in group['pitches'][:8]:
                    fundamental = 440*2**((pitch-69)/12)
                    for harmonic in (1, 2, 3, 4):
                        frequency = fundamental*harmonic
                        if frequency > min(8000, rate*.45):
                            break
                        near = np.abs(frequencies-frequency) <= max(7, frequency*.015)
                        surroundings = (np.abs(frequencies-frequency) < 70) & ~near & band
                        if not np.any(near) or not np.any(surroundings):
                            continue
                        peak = float(power[near].max())
                        floor = max(float(np.median(power[surroundings])), 1e-20)
                        if peak/total > .01 and peak > 12*floor:
                            heard = True
                if heard:
                    break
            checked += int(valid)
            tonal += int(heard)
    result.update(checked_groups=checked, tonal_groups=tonal)
    if checked < 8 or checked < .95*len(selected):
        result['notice'] = 'Incomplete MIDI/audio comparison; audio kept for review.'
    elif tonal:
        result.update(status='audible', notice='Tonal sound is discernible during MIDI playing; microphone audio kept.')
    elif ((result['rms_p90_dbfs'] < -50 and result['rms_p95_dbfs'] < -44 and result['quiet_fraction'] >= .95)
          or (result['rms_p95_dbfs'] < -32 and result['level_spread_db'] < 3)):
        result.update(status='inaudible', auto_discard=True,
            notice='MIDI playing without discernible piano audio: likely headphones or muted speakers. Microphone audio is excluded from the retention limit.')
    else:
        result['notice'] = 'Piano audibility is uncertain in the background sound; audio kept for review.'
    return result


def audio_signature(folder, info):
    filename = info.get('filename')
    path = folder/filename if filename else None
    if not path or not path.is_file():
        return None
    stat = path.stat()
    return {'filename': filename, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def needs_review(folder):
    from .microphone import metadata
    try:
        info = metadata(folder) or {}
        signature = audio_signature(folder, info)
    except (OSError, ValueError, TypeError):
        return (folder/'microphone.json').exists()  # Report corrupt metadata in a job, not at startup.
    return bool(signature and (info.get('headphone_detection_version') != VERSION
                or info.get('headphone_detection_audio') != signature))


def mark_reviewed(folder):
    from .microphone import metadata, write_metadata
    info = metadata(folder)
    if info:
        write_metadata(folder, {**info, 'headphone_detection_version': VERSION,
                               'headphone_detection_audio': audio_signature(folder, info)})
