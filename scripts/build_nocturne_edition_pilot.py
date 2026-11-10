"""Build a local, inspectable Op. 9 No. 1 edition study (no library writes).

Run with the optional Verovio Python package installed. The default inputs are
the exact cached sources reviewed in data/reviewed_page_links.json.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = 'eef849129d1945e8b4af3655875f9214'
DIVISIONS = 1320  # Exact eighths and 11/22-note groups, without rounding.


def element(parent, name, text=None, **attributes):
    child = ET.SubElement(parent, name, attributes)
    if text is not None:
        child.text = str(text)
    return child


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def excerpt(source):
    original = ET.parse(source).getroot()
    parts = original.findall('part')
    if len(parts) != 2:
        raise ValueError('Expected the reviewed two-part Music21 conversion')
    score = ET.Element('score-partwise', version='4.0')
    work = element(score, 'work')
    element(work, 'work-title', 'Nocturne Op. 9 No. 1 - pitch/rhythm pilot')
    identification = element(score, 'identification')
    element(identification, 'creator', 'Fryderyk Chopin', type='composer')
    element(identification, 'rights',
            'Adapted from NIFC first-edition encoding, CC BY 4.0; '
            'opening pitch/rhythm checked against the local Paderewski scan. '
            'Slurs, dynamics, fingering and pedal are omitted. '
            'https://github.com/pl-wnifc/humdrum-chopin-first-editions')
    part_list = element(score, 'part-list')
    part_info = element(part_list, 'score-part', id='P1')
    element(part_info, 'part-name', 'Piano')
    part = element(score, 'part', id='P1')
    checks = []
    for number in range(5):
        measure = element(part, 'measure', number=str(number),
                          implicit='yes' if number == 0 else 'no')
        if number == 3:
            element(measure, 'print', **{'new-system': 'yes'})
        if number == 0:
            attributes = element(measure, 'attributes')
            element(attributes, 'divisions', DIVISIONS)
            key = element(attributes, 'key')
            element(key, 'fifths', -5)
            element(key, 'mode', 'minor')
            time = element(attributes, 'time')
            element(time, 'beats', 6)
            element(time, 'beat-type', 4)
            element(attributes, 'staves', 2)
            for staff, sign, line in [(1, 'G', 2), (2, 'F', 4)]:
                clef = element(attributes, 'clef', number=str(staff))
                element(clef, 'sign', sign)
                element(clef, 'line', line)
        totals = []
        for staff, original_part in enumerate(parts, 1):
            if staff == 2:
                backup = element(measure, 'backup')
                element(backup, 'duration', totals[0])
            source_measure = original_part.findall('measure')[number]
            notes = source_measure.findall('note')
            # Paderewski engraves a half rest plus a quarter rest in the pickup.
            if number == 0 and staff == 2:
                notes = []
                for kind, duration in [('half', 2 * DIVISIONS), ('quarter', DIVISIONS)]:
                    note = ET.Element('note')
                    element(note, 'rest')
                    element(note, 'duration', duration)
                    element(note, 'type', kind)
                    notes.append(note)
            total = 0
            for index, source_note in enumerate(notes):
                note = copy.deepcopy(source_note)
                note.attrib.clear()
                tuplet = source_note.find('time-modification') is not None
                if number == 0 and staff == 2:
                    duration = int(note.findtext('duration'))
                elif tuplet:
                    duration = 360  # 3/11 of a quarter, exactly.
                else:
                    numerator = int(note.findtext('duration')) * DIVISIONS
                    if numerator % 10080:
                        raise ValueError('Unexpected non-integral ordinary duration')
                    duration = numerator // 10080
                note.find('duration').text = str(duration)
                total += duration
                for tag in ('voice', 'staff'):
                    for item in note.findall(tag):
                        note.remove(item)
                # Insert voice before type, staff before beam/notations (MusicXML order).
                position = list(note).index(note.find('type'))
                voice = ET.Element('voice')
                voice.text = str(staff)
                note.insert(position, voice)
                if tuplet:
                    note.find('type').text = 'eighth'
                    for dot in note.findall('dot'):
                        note.remove(dot)
                    modification = note.find('time-modification')
                    modification.clear()
                    actual = 22 if number == 3 else 11
                    normal = 12 if number == 3 else 6
                    element(modification, 'actual-notes', actual)
                    element(modification, 'normal-notes', normal)
                    element(modification, 'normal-type', 'eighth')
                    notations = note.find('notations')
                    if notations is None:
                        notations = element(note, 'notations')
                    for old in notations.findall('tuplet'):
                        notations.remove(old)
                    start = index == (0 if number == 3 else 2)
                    stop = index == len(notes) - 1
                    if start:
                        marking = element(notations, 'tuplet', type='start', number='1',
                                          bracket='yes', placement='below')
                        actual_mark = element(marking, 'tuplet-actual')
                        element(actual_mark, 'tuplet-number', actual)
                        element(actual_mark, 'tuplet-type', 'eighth')
                        normal_mark = element(marking, 'tuplet-normal')
                        element(normal_mark, 'tuplet-number', normal)
                        element(normal_mark, 'tuplet-type', 'eighth')
                    if stop:
                        element(notations, 'tuplet', type='stop', number='1')
                    for beam in note.findall('beam'):
                        note.remove(beam)
                    # One continuous beam for each printed ornamental group.
                    beam = ET.Element('beam', number='1')
                    beam.text = 'begin' if start else 'end' if stop else 'continue'
                    note.insert(list(note).index(notations), beam)
                staff_node = ET.Element('staff')
                staff_node.text = str(staff)
                before = next((i for i, n in enumerate(note)
                               if n.tag in ('beam', 'notations')), len(note))
                note.insert(before, staff_node)
                measure.append(note)
            totals.append(total)
        expected = (3 if number == 0 else 6) * DIVISIONS
        if totals != [expected, expected]:
            raise ValueError(f'Measure {number}: unequal staff lengths {totals}')
        checks.append({'printed_measure': number, 'follower_ordinal': number + 1,
                       'staff_duration_quarters': [v / DIVISIONS for v in totals]})
    ET.indent(score)
    return ET.tostring(score, encoding='unicode', xml_declaration=True), checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path,
                        default=Path.home() / '.local/share/chopin-studio')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/edition-pilot')
    args = parser.parse_args()
    import verovio  # Optional study dependency, not an application dependency.

    reference = args.data_dir / 'references' / (REFERENCE + '.musicxml')
    kern = args.data_dir / 'references' / (REFERENCE + '.source.krn')
    pdf = args.data_dir / 'scores/paderewski_nocturnes.pdf'
    review = json.loads((ROOT / 'data/reviewed_page_links.json').read_text())
    entry = next(row for row in review['works'] if row['piece_id'] == 'n9-1')
    if digest(reference) != entry['references'][0]['sha256']:
        raise ValueError('Reference changed since review; inspect it before rebuilding')
    # Scan hash is recorded in the same source inventory.
    if digest(pdf) != review['volumes'][pdf.name]:
        raise ValueError('PDF changed since review; inspect it before rebuilding')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    xml, checks = excerpt(reference)
    (output / 'paderewski-opening.musicxml').write_text(xml)
    renderer = verovio.toolkit()
    renderer.setOptions({'inputFrom': 'musicxml', 'pageWidth': 2600,
                         'pageHeight': 1800, 'scale': 45, 'breaks': 'encoded',
                         'adjustPageHeight': True, 'footer': 'none'})
    if not renderer.loadData(xml) or renderer.getPageCount() != 1:
        raise ValueError('Expected a one-page opening engraving')
    svg = renderer.renderToSVG(1)
    (output / 'paderewski-opening.svg').write_text(svg)
    # Also provide the full original edition through its native Humdrum input,
    # bypassing our application's lossy Music21 conversion entirely.
    renderer.setOptions({'inputFrom': 'humdrum', 'pageWidth': 2100,
                         'pageHeight': 2970, 'scale': 40, 'breaks': 'auto',
                         'adjustPageHeight': False})
    if not renderer.loadFile(str(kern)):
        raise ValueError('Native Humdrum engraving failed')
    source_pages = renderer.getPageCount()
    for page in range(1, source_pages + 1):
        renderer.renderToSVGFile(str(output / f'nifc-first-edition-{page}.svg'), page)
    subprocess.run(['pdftoppm', '-f', '4', '-l', '4', '-scale-to', '2200',
                    '-png', '-singlefile', str(pdf), str(output / 'paderewski-page-4')],
                   check=True)
    report = {'piece': 'Nocturne Op. 9 No. 1',
              'scope': 'Pickup and printed measures 1-4, pitch/rhythm pilot only',
              'omitted': ['slurs', 'dynamics', 'fingering', 'pedal', 'original layout'],
              'reference_sha256': digest(reference), 'pdf_sha256': digest(pdf),
              'kern_sha256': digest(kern), 'renderer': renderer.getVersion(),
              'source_pages': source_pages, 'exact_duration_checks': checks,
              'corrections': ['Half plus quarter rest in pickup',
                              'Exact 11:6 eighth-note tuplet in measure 2',
                              'One 22:12 eighth-note tuplet in measure 3',
                              'Grand staff; preserve printed pickup numbering'],
              'not_verified': 'Remaining measures; full editorial/expressive equivalence'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    pages = ''.join(f'<img loading="lazy" src="nifc-first-edition-{p}.svg" '
                    f'alt="NIFC Schlesinger engraving, page {p}">'
                    for p in range(1, source_pages + 1))
    svg = svg[svg.index('<svg'):]
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nocturne Op. 9 No. 1 — edition study</title>
<style>
body{margin:0;background:#f3f0e9;color:#242a2b;font:16px/1.55 system-ui,sans-serif}
main{max-width:1400px;margin:auto;padding:32px}h1{font:38px Georgia,serif;margin:8px 0}
h2{font:26px Georgia,serif}a{color:#126a68}p{max-width:900px}
.label{letter-spacing:.14em;text-transform:uppercase;font-size:12px;color:#526b68}
.card{background:white;border:1px solid #d6d9d3;border-radius:12px;padding:22px;margin:24px 0}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{padding:9px 16px;border:1px solid #9aa9a4;border-radius:6px;background:white;cursor:pointer}
button[aria-pressed=true]{background:#126a68;color:white}
.engraving{overflow-x:auto}.engraving svg{width:100%;height:auto;min-width:800px}
.measure{cursor:pointer;pointer-events:bounding-box}.measure.selected .note,.measure.selected .rest{fill:#007f78;color:#007f78}
img{display:block;max-width:100%;height:auto;margin:auto}small{color:#52615d}
details summary{cursor:pointer;font-weight:600}code{background:#e9eeea;padding:2px 4px}
</style><main><div class="label">Chopin Studio · inspectable edition pilot</div>
<h1>Nocturne in B-flat minor, Op. 9 No. 1</h1>
<p>The NIFC companion in this library encodes <b>Schlesinger’s first edition</b>.
It is not an encoding of the Paderewski volume. This study separates that source
from a small pitch/rhythm adaptation checked against the actual local scan.</p>
<section class="card"><h2>Paderewski opening — digital pitch/rhythm pilot</h2>
<p>Pickup and printed measures 1–4. Both staves use exact durations. The 11-note
and 22-note groups retain the printed grouping. Slurs, dynamics, fingering,
pedal and the original layout are omitted; this is not a complete critical transcription.</p>
<div class="controls">Highlight:
''' + ''.join(f'<button data-index="{i}" aria-pressed="false">{html.escape(label)}</button>'
              for i, label in enumerate(['Pickup (0)', 'Measure 1', 'Measure 2', 'Measure 3', 'Measure 4'])) + '''
<button id="clear">Clear</button><span id="status" role="status">Select a measure</span></div>
<div class="engraving">''' + svg + '''</div>
<small>Manual selection demonstrates addressable notation. This example is not connected to live MIDI.</small>
<p><a href="paderewski-opening.musicxml" download>Download editable MusicXML</a> ·
<a href="paderewski-opening.svg" download>Download vector engraving</a> ·
<a href="report.json">Provenance and exact-duration checks</a></p></section>
<details class="card" open><summary>Compare with Paderewski — PDF page 4, printed page 7</summary>
<img src="paderewski-page-4.png" alt="Local Paderewski scan, Nocturne Op. 9 No. 1 opening"></details>
<details class="card"><summary>Full NIFC first-edition engraving — a different edition</summary>
<p>Rendered directly from the original Humdrum with Verovio, bypassing Music21.
No claim of exact equivalence to Paderewski is made, and these pages have not all
been checked for rendering defects or musical accuracy.</p>''' + pages + '''</details>
<p><small>Source: First Editions of Fryderyk Chopin’s Music; copyright 2017–2021
The Fryderyk Chopin Institute. <a href="https://github.com/pl-wnifc/humdrum-chopin-first-editions">
NIFC source repository</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
Source file: 009-1b-Sm-001.krn. Paderewski scan retained for private local comparison.</small></p>
</main><script>
const measures=[...document.querySelectorAll('.engraving .measure')];
const buttons=[...document.querySelectorAll('button[data-index]')];
function select(index){measures.forEach((m,i)=>m.classList.toggle('selected',i===index));
buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
document.getElementById('status').textContent=index<0?'Selection cleared':
index===0?'Pickup · follower ordinal 1':`Printed measure ${index} · follower ordinal ${index+1}`;}
buttons.forEach((b,i)=>b.addEventListener('click',()=>select(i)));
measures.forEach((m,i)=>m.addEventListener('click',()=>select(i)));
document.getElementById('clear').addEventListener('click',()=>select(-1));
</script></html>'''
    (output / 'index.html').write_text(document)
    print(json.dumps({'output': str(output), 'duration_checks': checks,
                      'selectable_measures': svg.count('class="measure"')}, indent=2))


if __name__ == '__main__':
    main()
