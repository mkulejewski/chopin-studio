"""Streaming MIDI reconstruction. Journal times remain the high-resolution source."""
import csv
import io
import json
import os
import shutil
import struct
import tempfile
from collections import Counter
from pathlib import Path

import mido

TICKS_PER_SECOND = 2000


def variable_length(value):
    if value < 0 or value > 0x0FFFFFFF:
        raise ValueError('MIDI delta outside supported range')
    out = [value & 127]
    while value >> 7:
        value >>= 7
        out.insert(0, (value & 127) | 128)
    return bytes(out)


def midi_payload(message):
    raw = bytes(message.bytes())
    if message.type == 'sysex':
        # SMF SysEx includes a length, unlike a live MIDI wire message.
        data = bytes(message.data) + b'\xf7'
        return b'\xf0' + variable_length(len(data)) + data
    if raw[0] >= 0xf0:
        # SMF has no native system-realtime event. Preserve wire bytes in a
        # sequencer-specific metadata event; the journal remains authoritative.
        data = b'ChopinStudio raw MIDI\x00' + raw
        return b'\xff\x7f' + variable_length(len(data)) + data
    return raw


def journal_events(path):
    with path.open() as source:
        for line in source:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # A process interruption may leave one truncated final record.
                if source.read():
                    raise ValueError('Corrupt journal before end of file')


def export_midi(journal: Path, target: Path, end=None):
    """Bounded-memory export; synthetic stop cleanup never changes the journal."""
    last_tick = 0
    notes = Counter()
    channels = set()
    with tempfile.TemporaryFile(dir=target.parent) as track:
        track.write(b'\x00\xff\x51\x03\x07\xa1\x20')
        for event in journal_events(journal):
            if 'message' not in event:
                continue
            msg = mido.Message.from_dict(event['message'])
            tick = max(last_tick, round(event['t'] * TICKS_PER_SECOND))
            track.write(variable_length(tick - last_tick) + midi_payload(msg))
            last_tick = tick
            if hasattr(msg, 'channel'):
                channels.add(msg.channel)
            if msg.type == 'note_on' and msg.velocity:
                notes[(msg.channel, msg.note)] += 1
            elif msg.type in ('note_on', 'note_off'):
                notes[(msg.channel, msg.note)] = max(0, notes[(msg.channel, msg.note)] - 1)
        stop_tick = max(last_tick, round((end or 0) * TICKS_PER_SECOND))
        pending_delta = stop_tick - last_tick
        for (channel, note), count in notes.items():
            for _ in range(count):
                track.write(variable_length(pending_delta) + bytes(mido.Message('note_off', channel=channel, note=note).bytes()))
                pending_delta = 0
        for channel in sorted(channels):
            for control in (64, 66, 67, 123):
                track.write(variable_length(pending_delta) + bytes(mido.Message('control_change', channel=channel, control=control, value=0).bytes()))
                pending_delta = 0
        track.write(variable_length(pending_delta) + b'\xff\x2f\x00')
        size = track.tell()
        track.seek(0)
        temporary = target.with_suffix('.mid.tmp')
        with temporary.open('wb') as dest:
            dest.write(b'MThd' + struct.pack('>IHHH', 6, 0, 1, 1000))
            dest.write(b'MTrk' + struct.pack('>I', size))
            shutil.copyfileobj(track, dest)
            dest.flush()
            os.fsync(dest.fileno())
        os.replace(temporary, target)


def midi_events(path):
    midi = mido.MidiFile(path)
    if midi.type == 2:
        raise ValueError('Asynchronous type-2 MIDI is not supported')
    elapsed = 0.0
    for message in midi:
        elapsed += message.time
        if not message.is_meta:
            yield {'t': elapsed, 'message': message.copy(time=0).dict()}


def midicsv_events(path):
    rows = list(csv.reader(path.read_text(encoding='utf-8-sig').splitlines()))
    division = None
    tempo_events = [(0, 500000)]
    messages = []
    for row in rows:
        if len(row) < 3:
            continue
        kind = row[2].strip().lower()
        values = [x.strip() for x in row]
        if kind == 'header':
            division = int(values[5])
        elif kind == 'tempo':
            tempo_events.append((int(values[1]), int(values[3])))
        elif kind in ('note_on_c', 'note_off_c', 'control_c', 'program_c', 'pitch_bend_c'):
            tick, channel = int(values[1]), int(values[3])
            if kind.startswith('note_'):
                msg = mido.Message('note_on' if kind == 'note_on_c' else 'note_off', channel=channel, note=int(values[4]), velocity=int(values[5]))
            elif kind == 'control_c':
                msg = mido.Message('control_change', channel=channel, control=int(values[4]), value=int(values[5]))
            elif kind == 'program_c':
                msg = mido.Message('program_change', channel=channel, program=int(values[4]))
            else:
                msg = mido.Message('pitchwheel', channel=channel, pitch=int(values[4]) - 8192)
            messages.append((tick, msg))
        elif kind not in ('start_track', 'end_track', 'end_of_file', 'title_t', 'time_signature', 'key_signature', 'copyright_t', 'text_t', 'instrument_name_t', 'marker_t'):
            raise ValueError(f'Unsupported midicsv event: {kind}; import original MIDI to preserve all events')
    if division is None or division <= 0:
        raise ValueError('midicsv requires a positive PPQ Header division')
    tempo_events.sort(key=lambda item: item[0])
    for tick, msg in sorted(messages, key=lambda item: item[0]):
        seconds, previous, tempo = 0.0, 0, 500000
        for change_tick, new_tempo in tempo_events:
            if change_tick > tick:
                break
            seconds += (change_tick - previous) * tempo / (division * 1_000_000)
            previous, tempo = change_tick, new_tempo
        seconds += (tick - previous) * tempo / (division * 1_000_000)
        yield {'t': seconds, 'message': msg.dict()}
