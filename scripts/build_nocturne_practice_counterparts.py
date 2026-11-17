"""Rebuild three complete first-edition digital scores without library writes.

Native Humdrum -> MEI/SVG/MIDI bypasses the older Music21 engraving conversion.
These are source-derived Practice counterparts, not verified Paderewski editions
or Learning lessons. Requires optional verovio==6.4.1, outside the app runtime.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PIECES = {"n9-1": "Nocturne Op. 9 No. 1", "n9-2": "Nocturne Op. 9 No. 2",
          "n72-1": "Nocturne Op. 72 No. 1"}
KERN_HASHES = {
    "n9-1": "59d7697d1a67ccd2454ec41bbf2b12a6e5cd3294d5df26eb9e5bd5b98f3aa8a8",
    "n9-2": "fbc872cec5a4c282b5c86ba71838fae8d1f794c71047b68cd86df3fac64046bc",
    "n72-1": "1fb1689c319616d1b764a188c616fa41f19fc5be2e5a2d017986c888fe9baaeb",
}
NS = {"m": "http://www.music-encoding.org/ns/mei"}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ATTRIBUTION = ("First Editions of Fryderyk Chopin's Music; Copyright 2017-2021 "
               "The Fryderyk Chopin Institute; https://nifc.pl; https://chopinscores.org; "
               "https://github.com/pl-wnifc/humdrum-chopin-first-editions; "
               "CC BY 4.0 https://creativecommons.org/licenses/by/4.0/")


def native_dynamics(mei, beat_unit):
    """Retain written dynamic levels, without inventing MIDI loudness targets."""
    changes = []
    for ordinal, measure in enumerate(ET.fromstring(mei).findall('.//m:measure', NS), 1):
        for mark in measure.findall('m:dynam', NS):
            label = ''.join(mark.itertext()).strip()
            if label not in ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff') or not mark.get('tstamp'):
                continue
            for staff in mark.get('staff', '').split():
                changes.append(dict(measure=ordinal, beat=(float(mark.get('tstamp'))-1)*4/beat_unit,
                                    staff=int(staff), dynamic=label))
    return changes


def attack_inventory(renderer, mei, timemap):
    """Use native note IDs and quarter-beat timing; never infer notes from PDF."""
    root = ET.fromstring(mei)
    by_id = {}
    coverage = []
    for ordinal, measure in enumerate(root.findall(".//m:measure", NS), 1):
        staves = []
        for staff in measure.findall("m:staff", NS):
            staff_number = int(staff.get("n"))
            staves.append(staff_number)
            for layer in staff.findall("m:layer", NS):
                for note in layer.findall(".//m:note", NS):
                    by_id[note.get(XML_ID)] = (ordinal, measure.get("n"), staff_number,
                                               layer.get("n", "1"), note)
        if set(staves) != {1, 2}:
            raise ValueError(f"Measure {ordinal}: expected both piano staves")
        coverage.append({"ordinal": ordinal, "source_measure": measure.get("n"),
                         "staves_present": staves})
    starts, ends = {}, {}
    for event in timemap:
        for ident in event.get("on", []):
            if ident in starts:
                raise ValueError("Unfolded repeated note ID: preserve traversal before exporting")
            starts[ident] = event["qstamp"]
        for ident in event.get("off", []):
            ends[ident] = event["qstamp"]
    notes = []
    ties = {tie.get("startid", "").lstrip("#"): tie.get("endid", "").lstrip("#")
            for tie in root.findall(".//m:tie", NS)}
    continuations = set(ties.values())
    for ident, onset in starts.items():
        if ident not in by_id or ident not in ends:
            raise ValueError(f"Native timing lacks a note or release: {ident}")
        if ident in continuations:
            continue  # A written tie continuation is not a new attack.
        measure, label, staff, voice, note = by_id[ident]
        values = renderer.getMIDIValuesForElement(ident)
        pitch = values.get("pitch")
        if not isinstance(pitch, int) or not 0 <= pitch <= 127:
            raise ValueError(f"Invalid native pitch: {ident}")
        tail, chain = ident, {ident}
        while tail in ties:
            tail = ties[tail]
            if tail in chain or tail not in ends:
                raise ValueError(f"Invalid tie chain: {ident}")
            chain.add(tail)
            if renderer.getMIDIValuesForElement(tail).get("pitch") != pitch:
                raise ValueError(f"Tie changes sounding pitch: {ident}")
        duration = ends[tail] - onset
        if duration < 0:
            raise ValueError(f"Negative native duration: {ident}")
        notes.append(dict(id=ident, pitch=pitch, onset=onset, duration=duration,
                          measure=measure, source_measure=label, staff=staff,
                          display_staff=staff, part=0, voice=voice,
                          grace=note.get("grace") is not None))
    notes.sort(key=lambda n: (n["onset"], n["pitch"]))
    if not notes:
        raise ValueError("Empty native counterpart")
    for row in coverage:
        row["attacks"] = {str(staff): sum(n["measure"] == row["ordinal"] and n["staff"] == staff
                                         for n in notes) for staff in (1, 2)}
    return notes, coverage


def build(data_dir, output):
    import verovio

    manifest = json.loads((ROOT / "data/reviewed_page_links.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    reports, sections = [], []
    for work in manifest["works"]:
        pid = work["piece_id"]
        if pid not in PIECES:
            continue
        ref = work["references"][0]
        original = data_dir / "references" / ref["filename"]
        if hashlib.sha256(original.read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError(f"{pid}: original conversion differs from pinned source")
        kern = original.with_name(ref["id"] + ".source.krn")
        if hashlib.sha256(kern.read_bytes()).hexdigest() != KERN_HASHES[pid]:
            raise ValueError(f"{pid}: native source differs from pinned input")
        source = kern.read_text()
        if "**kern" not in source or "Chopin" not in source:
            raise ValueError(f"{pid}: unexpected native source")
        folder = output / pid
        folder.mkdir(exist_ok=True)
        renderer = verovio.toolkit()
        renderer.setOptions(dict(inputFrom="humdrum", pageWidth=2100, pageHeight=2970,
                                 scale=40, breaks="auto", adjustPageHeight=False))
        if not renderer.loadData(source):
            raise ValueError(f"{pid}: native source import failed")
        mei = renderer.getMEI()
        timemap = renderer.renderToTimemap()
        notes, coverage = attack_inventory(renderer, mei, timemap)
        pages = renderer.getPageCount()
        for page in range(1, pages + 1):
            renderer.renderToSVGFile(str(folder / f"page-{page}.svg"), page)
        (folder / "score.mei").write_text(mei)
        renderer.renderToMIDIFile(str(folder / "reference.mid"))
        shutil.copyfile(original, folder / "existing-conversion.musicxml")
        report = dict(piece_id=pid, title=PIECES[pid], status="provisional-first-edition",
                      edition="NIFC first-edition encoding; not certified Paderewski",
                      source_commit="95dfb105c1669c72d10b04088566154f12d3dc1c",
                      source_kern_sha256=hashlib.sha256(kern.read_bytes()).hexdigest(),
                      existing_musicxml_sha256=ref["sha256"], attribution=ATTRIBUTION,
                      renderer=renderer.getVersion(), pages=pages, note_attacks=len(notes),
                      measures=coverage, notes=notes,
                      review=dict(structural="Both staves and native timed attacks exported for every measure",
                                  scan_pitch_audit="Not a complete Paderewski pitch/notation audit",
                                  learning="No Learning lesson or automatic assessment enabled"))
        report['dynamic_changes'] = native_dynamics(mei, 8 if pid == 'n9-2' else 4)
        source_tree = ET.fromstring(mei)
        report["source_problem_markers"] = [
            dict(source_measure=measure.get("n"), staff=direction.get("staff"),
                 source_id=direction.get(XML_ID))
            for measure in source_tree.findall(".//m:measure", NS)
            for direction in measure.findall("m:dir[@type='problem']", NS)
        ]
        (folder / "counterpart.json").write_text(json.dumps(report, indent=2)+"\n")
        reports.append({k:v for k,v in report.items() if k not in ("notes", "measures")})
        pictures = "".join(f'<img loading="lazy" src="{pid}/page-{p}.svg" alt="{html.escape(PIECES[pid])}, page {p}">'
                           for p in range(1, pages+1))
        sections.append(f'<section><h2>{html.escape(PIECES[pid])}</h2><p>{len(coverage)} source measure entries, '
                        f'{len(notes)} timed note attacks, both staves. '
                        f'{len(report["source_problem_markers"])} original source warning markers retained. '
                        f'<a href="{pid}/score.mei">Native MEI</a> · '
                        f'<a href="{pid}/reference.mid">Reference MIDI</a> · '
                        f'<a href="{pid}/counterpart.json">Attack inventory and provenance</a> · '
                        f'<a href="{pid}/existing-conversion.musicxml">Existing MusicXML conversion</a></p>{pictures}</section>')
    if len(reports) != len(PIECES):
        raise ValueError("Missing requested source")
    (output / "manifest.json").write_text(json.dumps(reports, indent=2)+"\n")
    annotations = {r['existing_musicxml_sha256']: dict(piece_id=r['piece_id'],
                   provenance=r['edition'], attribution=ATTRIBUTION,
                   source_commit=r['source_commit'], source_kern_sha256=r['source_kern_sha256'],
                   dynamic_changes=r['dynamic_changes']) for r in reports}
    (output / 'annotations.json').write_text(json.dumps(annotations, indent=2)+'\n')
    (output / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Nocturne digital counterparts</title>'
        '<style>body{max-width:1100px;margin:2rem auto;padding:0 1rem;font:17px/1.5 system-ui;background:#f5f2eb;color:#202828}'
        'section{background:white;padding:1rem;margin:2rem 0}img{display:block;width:100%;height:auto}a{color:#006c68}</style>'
        '<h1>Nocturne digital counterparts</h1><p>Complete source-derived digital scores for Practice inspection and MIDI playback. '
        'Provisional first-edition sources; these are not certified Paderewski transcriptions or Learning lessons. '
        'Native engraving bypasses the previous Music21 conversion. No application records or recordings were changed.</p>'
        f'<p>{html.escape(ATTRIBUTION)}</p>'+''.join(sections)+'</html>')
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/edition-pilot/nocturne-counterparts")
    args = parser.parse_args()
    for report in build(args.data_dir, args.output):
        print(report["title"], report["note_attacks"], "attacks;", report["pages"], "pages")
