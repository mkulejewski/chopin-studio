"""Safe reference ingestion using Partitura, not PDF-derived invented notes."""
import io
import json
import uuid
import zipfile
from functools import lru_cache
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
        beam_ids={}
        has_beams=any(n.beam is not None for n in part.iter_all(partitura.score.Note, include_subclasses=True))
        signatures=list(part.iter_all(partitura.score.TimeSignature))
        keys=list(part.iter_all(partitura.score.KeySignature))
        measures=list(part.iter_all(partitura.score.Measure))
        dynamics=list(part.iter_all(partitura.score.ConstantLoudnessDirection))
        for measure_index,measure in enumerate(measures):
            left=measure.start.t
            right=measure.end.t
            number=measure.number if measure.number is not None else measure_index+1
            try:number=int(number)
            except (TypeError,ValueError):number=measure_index+1
            measured_notes=list(part.iter_all(partitura.score.Note,start=measure.start,end=measure.end,include_subclasses=True))
            grace_attacks={}
            grace_clusters={}
            for note in sorted(measured_notes,key=lambda n:getattr(n,'doc_order',0) or 0):
                if not isinstance(note,partitura.score.GraceNote):continue
                key=(note.start.t,note.staff,note.voice)
                attacks=grace_clusters.setdefault(key,[])
                if not getattr(note,'is_grace_chord',False) or not attacks:attacks.append([])
                attacks[-1].append(note)
            for attacks in grace_clusters.values():
                for index,attack in enumerate(attacks):
                    for note in attack:grace_attacks[id(note)]=(index-len(attacks))*.001
            for note in measured_notes:
                if note.start.t<left or note.start.t>=right or note.tie_prev is not None:continue
                written_onset=float(part.quarter_map(note.start.t))
                onset=written_onset+grace_attacks.get(id(note),0)
                duration=float(part.quarter_map(note.end_tied.t)-part.quarter_map(note.start.t)) if note.end_tied else 0
                beam=note.beam
                beam_group=beam_ids.setdefault(id(beam),f'{part_index}:{len(beam_ids)}') if beam is not None else None
                signature=next((ts for ts in reversed(signatures) if ts.start.t<=note.start.t),None)
                key=next((ks for ks in reversed(keys) if ks.start.t<=note.start.t),None)
                beat_group=(signature.beats*4/signature.beat_type/signature.musical_beats) if signature else 1
                if signature and signature.beat_type>=8 and signature.beats%3==0:
                    beat_group=12/signature.beat_type
                dynamic=next((d.text for d in reversed(dynamics) if d.start.t<=note.start.t and (not d.staff or d.staff==(note.staff or 1))),None)
                notes.append({'dynamic':dynamic,'pitch':int(note.midi_pitch),'onset':onset,'written_onset':written_onset,'duration':duration,'measure':number,
                              'spelling':{'step':note.step,'alter':int(note.alter or 0),'octave':int(note.octave)},
                              'key_fifths':int(key.fifths) if key else None,
                              'voice':str(note.voice or ''),'staff':int(note.staff or 1),'part':part_index,
                              'id':str(note.id),'grace':bool(isinstance(note,partitura.score.GraceNote)),
                              'ornaments':list(getattr(note,'ornaments',None) or []),
                              'beam_group':beam_group,'beaming_source':'reference' if has_beams else 'meter',
                              'beat_group_size':beat_group,'measure_start':float(part.quarter_map(left))})
    notes.sort(key=lambda n:(n['onset'],n['pitch']))
    if not notes:raise ValueError('Reference has no pitched notes')
    return annotate_reference_staves(notes, path)


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


def annotate_reference_staves(notes, path):
    """Resolve local part/staff numbers to the comparison's two piano staves.

    Separate treble/bass MusicXML parts commonly both use local staff 1.
    Preserve raw staff/part fields and add an explicit display assignment.
    No source file or stored reference is rewritten by analysis-time enrichment.
    """
    from collections import defaultdict
    from statistics import median
    layout = {}
    path = Path(path)
    if path.is_file() and path.suffix.lower() in ('.xml', '.musicxml'):
        try:
            root = ElementTree.parse(path).getroot()
            parts = root.findall('part')
            single = []
            for index, part in enumerate(parts):
                clefs = {}
                for clef in part.findall('.//clef'):
                    staff = int(clef.get('number', '1'))
                    clefs.setdefault(staff, clef.findtext('sign', ''))
                count = max([1, *clefs, *[int(s.text) for s in part.findall('.//staves') if s.text]])
                if count >= 2:
                    for staff in range(1, count+1):
                        layout[index, staff] = (min(staff, 2), 'reference_staff', clefs.get(staff))
                else:
                    single.append((index, clefs.get(1)))
            # An upper/lower pair with identical clefs still has a meaningful
            # source part order. A G/F pair can be identified directly by clef.
            ordered_pair = len(parts) == 2 and len(single) == 2 and single[0][1] == single[1][1]
            for ordinal, (index, sign) in enumerate(single):
                if ordered_pair:
                    layout[index, 1] = (ordinal+1, 'reference_part_order', sign)
                elif sign in ('G', 'F'):
                    layout[index, 1] = (2 if sign == 'F' else 1, 'reference_clef', sign)
        except (ValueError, OSError, ElementTree.ParseError):
            layout = {}
    by_part = defaultdict(list)
    for note in notes:
        by_part[note.get('part', 0) or 0].append(note['pitch'])
    # If source XML is unavailable, old split-part references can still be
    # distinguished using their parts' register. Record that this is inferred.
    lower_part = min(by_part, key=lambda p: median(by_part[p])) if len(by_part) == 2 else None
    all_single_staff = all((n.get('staff') or 1) == 1 for n in notes)
    enriched = []
    for note in notes:
        item = dict(note)
        part = note.get('part', 0) or 0
        staff = note.get('staff') or 1
        assignment = layout.get((part, staff))
        if assignment is None:
            if note.get('display_staff') in (1, 2):
                assignment = (note['display_staff'], note.get('staff_source', 'reference_staff'), note.get('clef_sign'))
            elif lower_part is not None and all_single_staff:
                assignment = (2 if part == lower_part else 1, 'part_register_inferred', None)
            elif note.get('staff') in (1, 2):
                assignment = (staff, 'reference_staff', None)
            else:
                assignment = (2 if note['pitch'] < 60 else 1, 'pitch_register_inferred', None)
        item.update(display_staff=assignment[0], staff_source=assignment[1], clef_sign=assignment[2])
        enriched.append(item)
    return enriched


def _note_position(note):
    return (note.get('part',0) or 0,note.get('staff',1) or 1,
            round(note['onset'],6),note['pitch'],str(note.get('voice') or ''))


@lru_cache(maxsize=8)
def _reference_rhythm_snapshot(filename,mtime_ns,size):
    # File identity invalidates the cache when the source changes. Corrected
    # JSON pitches/onsets are not replaced by the original MusicXML contents.
    return {_note_position(n): {k:n[k] for k in ('beam_group','beaming_source','beat_group_size','measure_start','spelling','key_fifths','dynamic')}
            for n in parse_musicxml(filename)}


def annotate_reference_rhythm(notes,path):
    """Best-effort source notation enrichment without rewriting stored references."""
    path=Path(path)
    if all(all(k in n for k in ('beaming_source','spelling','key_fifths','dynamic')) for n in notes) or not path.is_file() or path.suffix.lower() not in ('.xml','.musicxml'):
        return notes
    try:
        stat=path.stat()
        metadata=_reference_rhythm_snapshot(str(path),stat.st_mtime_ns,stat.st_size)
    except Exception:
        # Optional engraving data must never prevent pitch analysis of a
        # corrected JSON reference whose original XML is no longer parsable.
        return notes
    return [{**metadata.get(_note_position(n),{}),**n} for n in notes]
