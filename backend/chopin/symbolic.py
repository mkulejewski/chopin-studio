"""Safe reference ingestion using Partitura, not PDF-derived invented notes."""
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from defusedxml import ElementTree

MAX_XML=20*1024*1024


def unpack_xml(data, suffix):
    if suffix.lower()=='.mxl':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist())>MAX_XML:
                raise ValueError('Expanded MusicXML exceeds 20 MiB')
            container=ElementTree.fromstring(archive.read('META-INF/container.xml'))
            roots=[e.attrib['full-path'] for e in container.iter() if e.tag.endswith('rootfile')]
            if not roots or '..' in Path(roots[0]).parts or Path(roots[0]).is_absolute():
                raise ValueError('Unsafe MXL rootfile')
            data=archive.read(roots[0])
    if len(data)>MAX_XML:raise ValueError('MusicXML exceeds 20 MiB')
    root=ElementTree.fromstring(data)
    if root.tag not in ('score-partwise','score-timewise'):raise ValueError('Expected MusicXML score')
    # Re-serialise parsed XML: remove external DTDs and entity declarations before Partitura.
    return ElementTree.tostring(root,encoding='utf-8',xml_declaration=True)


def parse_musicxml(path):
    import partitura
    score=partitura.load_musicxml(path,force_note_ids=True,quiet=True)
    notes=[]
    for part_index,part in enumerate(score.parts):
        measures=list(part.iter_all(partitura.score.Measure))
        for measure_index,measure in enumerate(measures):
            left=measure.start.t
            right=measure.end.t
            number=measure.number if measure.number is not None else measure_index+1
            try:number=int(number)
            except (TypeError,ValueError):number=measure_index+1
            for note in part.iter_all(partitura.score.Note,start=measure.start,end=measure.end):
                if note.start.t<left or note.start.t>=right or note.tie_prev is not None:continue
                onset=float(part.quarter_map(note.start.t))
                duration=float(part.quarter_map(note.end_tied.t)-part.quarter_map(note.start.t)) if note.end_tied else 0
                notes.append({'pitch':int(note.midi_pitch),'onset':onset,'duration':duration,'measure':number,
                              'voice':str(note.voice or ''),'staff':int(note.staff or 1),'part':part_index,
                              'id':str(note.id),'grace':bool(isinstance(note,partitura.score.GraceNote))})
    notes.sort(key=lambda n:(n['onset'],n['pitch']))
    if not notes:raise ValueError('Reference has no pitched notes')
    return notes


def import_reference(store,piece_id,data,suffix,source='User supplied',licence='User supplied; verify permission',edition='Unspecified; compare with printed score'):
    if not store.query('SELECT id FROM pieces WHERE id=?',(piece_id,)):raise ValueError('Unknown piece')
    ident=uuid.uuid4().hex
    path=store.root/'references'/(ident+'.musicxml')
    try:
        path.write_bytes(unpack_xml(data,suffix))
        notes=parse_musicxml(path)
        store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                      (ident,piece_id,path.name,source,licence,edition,'provisional',json.dumps(notes),datetime.now(timezone.utc).isoformat()))
        return ident
    except Exception:
        path.unlink(missing_ok=True)
        raise


def reference_info(store,piece_id=None):
    return store.query('SELECT id,piece_id,filename,source,licence,edition,quality,created FROM symbolic_scores'+(' WHERE piece_id=?' if piece_id else ''),(piece_id,) if piece_id else ())
