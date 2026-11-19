"""Import app-owned, durably staged files supplied by a user or host."""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from .midi_files import export_midi, midi_events, midicsv_events

MIDI_SUFFIXES = ('.mid', '.midi', '.csv')


def import_midi_file(store, original: Path, display_name: str):
    """Consume a staged file and preserve the original bytes in the new session."""
    suffix = original.suffix.lower()
    ident = uuid.uuid4().hex
    folder = store.root / 'sessions' / ident
    created = False
    try:
        if suffix not in MIDI_SUFFIXES:
            raise ValueError('Choose a .mid, .midi or midicsv .csv file')
        folder.mkdir()
        created = True
        count, duration = 0, 0.0
        parser = midicsv_events if suffix == '.csv' else midi_events
        with (folder / 'events.jsonl').open('x') as journal:
            for event in parser(original):
                journal.write(json.dumps(event) + '\n')
                count += 1
                duration = max(duration, event['t'])
            store.files.sync(journal)
        if not count:
            raise ValueError('No supported MIDI events found')
        if suffix == '.csv':
            export_midi(folder / 'events.jsonl', folder / 'original.mid', duration, files=store.files)
            store.files.replace(original, folder / 'source.csv')
        else:
            store.files.replace(original, folder / 'original.mid')
        store.files.sync_directory(folder)
        store.files.sync_directory(folder.parent)
        name = 'Imported_' + Path(display_name).stem[:100] + '_' + ident[:6]
        started = datetime.now(timezone.utc).isoformat()
        source = 'midicsv' if suffix == '.csv' else 'midi'
        store.execute(
            "INSERT INTO sessions(id,name,started,status,duration,events,source) VALUES(?,?,?,'imported',?,?,?)",
            (ident, name, started, duration, count, source),
        )
    except Exception as exc:
        if created:
            shutil.rmtree(folder)
        original.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f'Cannot read MIDI: {exc}') from exc
    return ident


def import_pdf_file(store, volume, target: Path):
    """Publish a validated PDF staged directly in the app's scores directory."""
    try:
        with target.open('rb') as stream:
            if stream.read(5) != b'%PDF-':
                raise ValueError('Not a PDF document')
            stream.seek(0)
            reader = PdfReader(stream)
            if reader.is_encrypted:
                raise ValueError('Encrypted PDFs are unsupported; import a permitted unlocked copy')
            pages = len(reader.pages)
        if not pages:
            raise ValueError('PDF has no pages')
        if not store.query('SELECT id FROM volumes WHERE id=?', (volume,)):
            raise ValueError('Volume not found')
        store.execute('UPDATE volumes SET filename=?,pages=? WHERE id=?', (target.name, pages, volume))
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise ValueError(f'Cannot import PDF: {exc}') from exc
    return pages
