"""Build the scan-reviewed Op.53 Learning pitch/attack counterpart.

Reads exact cached, licensed inputs without changing the library. The Paderewski
scan owns the form, printed measure numbers, page map and lesson design. NIFC's
Schlesinger encoding supplies the base; every occurrence is checked against the scan.
See docs/heroic_polonaise_op53_learning.md for review coverage and matching policies.
"""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import copy
import re
from heroic_polonaise_op53_scan_review import (GROUP_FIXES, GRACE_FIXES, OPTIONAL_GRACES, SCALE_OCTAVE_FIXES,
    TIED_TRILLS, MEASURE_COPIES, STAFF_COPIES, CROSS_STAFF_OPENINGS, LOWER_STAFF_OCTAVES,
    UPPER_STAFF_VOICES, TRILL_PITCHES, SHORT_TRILL_PITCHES)
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = 'e7c184b31d8c4db9b482a147c431d306.musicxml'
REFERENCE_HASH = 'd9aaafb60e118510a992c14eb9821d6d674ddbd2e5e90a1900a4424fc3ec5703'
PDF_HASH = 'b1ea18ef7892aaafe9c7aa668ecf0b137c7bc9ee37ea54a6067377351681a8b7'
# Visually read from all fourteen Paderewski pages; these are printed bar labels,
# not the reference database's ordinal indices (which include a synthetic bar 0).
PAGE_STARTS = [(1, 60), (17, 61), (31, 62), (42, 63), (53, 64), (64, 65),
               (74, 66), (89, 67), (105, 68), (120, 69), (130, 70),
               (143, 71), (158, 72), (168, 73)]
SECTION_SPECS = [
    (1, 16, 'Introduction', 2,
     'Study the four-bar chromatic gestures, then the rising preparation. Name the changing intervals and bass destinations; do not begin every practice run here.'),
    (17, 32, 'A · Main polonaise: first statement', 2,
     'Establish the main theme as your first memory anchor. Learn bass, chord shapes and melody separately, then coordinate. Practise starting at 17, 21, 25 and 29 without an introductory run-up.'),
    (33, 48, 'A · Ornamented continuation', 2,
     'Compare the theme with 17–32. Isolate the written turns, trills, octave displacement and the scale into 47. Learn changed notes and the cadence as this occurrence, not as a presumed copy.'),
    (49, 64, 'A · Contrasting episode and sostenuto', 2,
     'Separate the repeated-note dialogue in 49–56 from the sustained melody in 57–64. Keep the inner accompaniment distinct; study the trill and ascending link into the return.'),
    (65, 80, 'A · Return and close before the trio', 2,
     'Compare with 33–48, then recall independently from 65. Learn the precise end at 79–80 and its route into the E-major entrance; do not automatically loop back to the opening.'),
    (81, 84, 'B · E-major entrance and octave launch', 2,
     'Locate the new four-sharp key and the repeated chords. Learn the quiet octave launch slowly, with releases and rests. Stop if tense; note recall is not an endurance or tempo target.'),
    (85, 100, 'B · First octave episode', 4,
     'Learn the descending E-major octave cell separately from the upper melody. Map the changing top voice and the chromatic exit at 97–100. Use short relaxed sets, then connect the phrase; never force repeated octaves at speed.'),
    (101, 120, 'B · Relaunch, second octave episode and exit', 4,
     'Treat 101–104 as a new launch. Compare 105–116 with 85–96, then study the chromatic exit 117–120. Practise this occurrence independently and name the route back to four flats.'),
    (121, 128, 'C · Chordal transition', 2,
     'Reset the key to four flats and learn the chordal responses by harmonic destination. Keep the moving upper voice separate from repeated inner notes; prepare the softer flowing episode.'),
    (129, 144, 'C · Flowing development', 2,
     'Learn each chromatic melodic contour with its bass landmarks. Isolate turns, trills and the sextuplets around 140; practise starts at 129, 133, 137 and 141 rather than one long run.'),
    (145, 154, 'C · Retransition to the main theme', 2,
     'Map each sequential shift, the easing dynamic and the descent into the low register. Build backwards from the landing at 155, then connect 151–154 to the returning theme.'),
    (155, 168, 'A′ · Final reprise', 2,
     'Compare with 65–78 but learn the final occurrence and its outgoing scale independently. Start from 155 and 163; distinguish the route to the coda from the earlier route to the trio.'),
    (169, 181, 'Coda · Closing route', 2,
     'Secure the ending early: first learn 179–181, then add 175–178, then 169–174. Inspect the octave marks, repeated chords and altered closing harmony. Finally connect 168 into 169 without restarting the theme.'),
]
ORDER = [1, 2, 4, 3, 0, 12, 5, 6, 7, 8, 9, 10, 11]
BRIDGES = [(13, 20), (29, 36), (45, 52), (61, 68), (77, 88),
           (97, 106), (117, 124), (125, 132), (149, 158), (165, 174)]


def spelling(name):
    match = re.fullmatch(r'([A-G])(bb|b|#|x)?(-?\d)', name)
    if not match:
        raise ValueError(f'Invalid reviewed note: {name}')
    step, accidental, octave = match.groups()
    return {'step':step, 'alter':{None:0,'bb':-2,'b':-1,'#':1,'x':2}[accidental], 'octave':int(octave)}


def name(note):
    return note['step']+{-2:'bb',-1:'b',0:'',1:'#',2:'x'}[note['alter']]+str(note['octave'])


def midi(note):
    return 12*(note['octave']+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[note['step']]+note['alter']


def transcribe(score):
    measures = {n: {'number':n, 'pdf_page':max(p for a,p in PAGE_STARTS if a<=n),
                    'key_fifths':4 if 81<=n<=120 else -4, 'review_status':'model-reviewed',
                    'staves':[[],[]], 'spellings':[[],[]], 'grace_notes':[]}
                for n in range(1,182)}
    # Normal attacks are separate from grace notation until the occurrence
    # corrections have been applied, so group indices remain auditable.
    raw = {n:[{},{}] for n in measures}
    corrections = []
    for staff, part in enumerate(score.findall('part')):
        divisions = 10080
        for bar in part.findall('measure'):
            number = int(bar.get('number'))
            if number == 0:
                continue  # First-edition-only material; 119 is retranscribed below.
            cursor = last_onset = Fraction(0)
            divisions = int(bar.findtext('attributes/divisions') or divisions)
            last_grace = None
            for item in bar:
                if item.tag in ('backup','forward'):
                    cursor += (-1 if item.tag=='backup' else 1)*Fraction(int(item.findtext('duration')),divisions)
                    continue
                if item.tag!='note':
                    continue
                pitch = item.find('pitch')
                note = ({'step':pitch.findtext('step'), 'alter':int(pitch.findtext('alter') or 0),
                         'octave':int(pitch.findtext('octave'))} if pitch is not None else None)
                grace = item.find('grace') is not None
                if grace:
                    if note is not None:
                        if item.find('chord') is not None and last_grace is not None:
                            last_grace['spellings'].append(note)
                        else:
                            last_grace = {'staff':staff+1, 'before_beat':str(cursor), 'spellings':[note], 'policy':'required'}
                            measures[number]['grace_notes'].append(last_grace)
                    continue
                onset = last_onset if item.find('chord') is not None else cursor
                if item.find('chord') is None:
                    last_onset = cursor
                    cursor += Fraction(int(item.findtext('duration') or 0),divisions)
                # Hidden rests still advance a polyphonic cursor; ties do not
                # create new key attacks. Original XML remains unchanged.
                if note is not None and not any(t.get('type')=='stop' for t in item.findall('tie')):
                    raw[number][staff].setdefault(onset,{}).setdefault(midi(note),note)
    groups = {n:[[[pos,list(notes.values())] for pos,notes in sorted(staff.items())] for staff in staves]
              for n,staves in raw.items()}
    def log(number, staff, before, after, reason, **extra):
        corrections.append({'measure':number,'staff':staff,'before':before,'after':after,'reason':reason,**extra})
    for number,staff,index,before,after,reason in GROUP_FIXES:
        group = groups[number][staff-1][index]
        actual = ' '.join(map(name,group[1]))
        if actual!=before:
            raise ValueError(f'Source drift at {number}/{staff}/{index}: {actual!r}, expected {before!r}')
        group[1] = [spelling(n) for n in after.split()]
        log(number,staff,before,after,reason,group=index,beat=str(group[0]))
    for number,staff,first,last in SCALE_OCTAVE_FIXES:
        for index in range(first,last+1):
            group = groups[number][staff-1][index]
            before = ' '.join(map(name,group[1]))
            for note in group[1]:
                note['octave'] += 1
            log(number,staff,before,' '.join(map(name,group[1])),
                'Continue the printed ascending scale across the staff crossing.',group=index,beat=str(group[0]))
    for number,source,reason in MEASURE_COPIES:
        before = [[str(p),list(map(name,ns))] for staff in groups[number] for p,ns in staff]
        groups[number] = copy.deepcopy(groups[source])
        log(number,0,before,f'Reviewed complete measure {source}',reason)
    for number,staff,source,reason in STAFF_COPIES:
        groups[number][staff-1] = copy.deepcopy(groups[source][staff-1])
        log(number,staff,'Incomplete converted staff',f'Reviewed staff {staff} of measure {source}',reason)
    def add(number, staff, pos, notes):
        found = next((g for g in groups[number][staff-1] if g[0]==pos),None)
        if found is None:
            groups[number][staff-1].append([pos,notes])
        else:
            known = {midi(n) for n in found[1]}
            found[1].extend(n for n in notes if midi(n) not in known)
    for number,old,new in CROSS_STAFF_OPENINGS:
        lower = groups[number][1][0]
        if lower[0]!=0 or list(map(name,lower[1]))!=[old]:
            raise ValueError(f'Unexpected crossed opening at {number}')
        lower[1] = []
        add(number,1,Fraction(0),[spelling(new)])
        log(number,2,old,new,'Printed in the upper staff with the opening octave; sounding octave reviewed.')
    for number in LOWER_STAFF_OCTAVES:
        for group in groups[number][0]:
            if number in (83,103) and group[0]==0:
                continue
            add(number,2,group[0],group[1])
            group[1] = []
        log(number,0,'Octaves split between converted parts','Octaves together in lower staff',
            'The scan prints both octave voices in the lower staff; the upper staff rests after the launch.')
    for number,notes in UPPER_STAFF_VOICES.items():
        for group in groups[number][1]:
            moving = [n for n in group[1] if name(n) in notes]
            if moving:
                add(number,1,group[0],moving)
                group[1] = [n for n in group[1] if name(n) not in notes]
        log(number,0,'Upper-staff voice in converted lower part','Voice returned to upper staff',
            'Preserve the printed staff assignment for separate-hand study.')
    for number,(before,after,reason) in GRACE_FIXES.items():
        grace = measures[number]['grace_notes']
        actual = ' '.join(name(n) for g in grace for n in g['spellings'])
        if actual!=before:
            raise ValueError(f'Grace-source drift at {number}: {actual!r}')
        replacements = [spelling(n) for n in after.split()]
        if len(grace)==1:
            grace[0]['spellings'] = replacements
        else:
            if len(grace)!=len(replacements):
                raise ValueError(f'Unexpected grace grouping at {number}')
            for g,n in zip(grace,replacements):
                g['spellings'] = [n]
        log(number,1,before,after,reason,kind='grace')
    for number,reason in OPTIONAL_GRACES.items():
        for grace in measures[number]['grace_notes']:
            grace['policy'] = 'optional-editorial'
        log(number,1,'Required source grace','Optional parenthesized alternative',reason,kind='editorial')
    # This tie is visible in the scan. The grace octave is still required; the
    # trill's variable return attacks are covered by its local symbol policy.
    for number in TIED_TRILLS:
        group = next(g for g in groups[number][0] if g[0]==2)
        if list(map(name,group[1]))!=['Db5']:
            raise ValueError('Unexpected tied trill main note')
        group[1] = []
        log(number,1,'Repeated Db5 at beat 2','Db5 held from beat 7/4',
            'The small Db4 octave is written under the tied upper note; no extra principal attack is required.')
    # Keep explicit ornament symbols, including those absent/wrong in the first
    # edition. Learning checks written attacks, not the number/speed of alternations.
    ornaments = []
    for kind,source in [('trill',TRILL_PITCHES),('short-trill',SHORT_TRILL_PITCHES)]:
        for number,pairs in source.items():
            used = set()
            for principal,auxiliary in pairs:
                candidates = [g for g in groups[number][0] if principal in map(name,g[1]) and g[0] not in used]
                # In 62/63 the trill sign starts on a tie at beat 2; scope it to
                # the immediately preceding Db5 and following small octave.
                group = candidates[-1] if number in (62,63) else candidates[0]
                used.add(group[0])
                ornaments.append({'measure':number,'staff':1,'beat':str(Fraction(127,64) if number in (62,63) else group[0]),
                    'kind':kind,'principal':principal,'auxiliary':auxiliary, 'notation_beat':str(group[0]),
                    'pitches':[midi(spelling(principal)),midi(spelling(auxiliary))],
                    'policy':'The printed principal attack and written small notes remain required. Additional local principal/upper-neighbour alternations are permitted; realization count and speed are not graded.'})
    for number,measure in measures.items():
        for staff in (1,2):
            grace_by_beat = {}
            for grace in measure['grace_notes']:
                if grace['staff']==staff and grace['policy']=='required':
                    grace_by_beat.setdefault(Fraction(grace['before_beat']),[]).append(grace)
            for beat,graces in grace_by_beat.items():
                # Fractional slots express attack order, not performed duration.
                # At the opening, place the main attack after its lead-in so no
                # synthetic negative score positions leak into the renderer.
                if beat==0:
                    for g in groups[number][staff-1]:
                        if g[0]==0:
                            g[0] = Fraction(len(graces),64)
                for i,grace in enumerate(graces):
                    pos = Fraction(i,64) if beat==0 else beat-Fraction(len(graces)-i,64)
                    grace['attack_beat'] = str(pos)
                    add(number,staff,pos,grace['spellings'])
            ordered = sorted((g for g in groups[number][staff-1] if g[1]),key=lambda g:g[0])
            measure['staves'][staff-1] = [[str(pos),[midi(n) for n in ns]] for pos,ns in ordered]
            measure['spellings'][staff-1] = [ns for pos,ns in ordered]
    # Parenthesized alternative only, never applied to other Gb passages.
    ornaments.append({'measure':21,'staff':1,'beat':'0','kind':'editorial-alternative',
                      'pitches':[midi(spelling('Gb4'))], 'policy':OPTIONAL_GRACES[21]})
    measures[120]['key_changes'] = [{'beat':'1/2','fifths':-4}]
    return measures, corrections, ornaments


def inventory(bundle):
    lines = ['Paderewski Op.53: required pitch/attack inventory',
             'Printed measures 1–181. Brackets denote a simultaneous chord.',
             'Fractional grace slots specify order, not performed rhythm.',
             'Trill and short-trill signs are preserved as local ornament policies; their realization count is not graded.', '']
    for measure in bundle['measures']:
        lines.append(f"MEASURE {measure['number']} | PDF {measure['pdf_page']}")
        for staff in (0,1):
            lines.append(('UPPER: ' if staff==0 else 'LOWER: ')+ ' '.join(
                pos+':['+','.join(map(name,notes))+']' for (pos,ps),notes in zip(measure['staves'][staff],measure['spellings'][staff])))
        for ornament in bundle['ornaments']:
            if ornament['measure']==measure['number']:
                lines.append('ORNAMENT: '+json.dumps(ornament,ensure_ascii=False))
    return '\n'.join(lines)+'\n'


def build(data_dir):
    source = data_dir / 'references' / REFERENCE
    pdf = data_dir / 'scores/paderewski_polonaises.pdf'
    for path, digest in [(source, REFERENCE_HASH), (pdf, PDF_HASH)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Unrecognized input: {path.name}; review a new revision first')
    measures, corrections, ornaments = transcribe(ET.parse(source).getroot())
    sections, chunks = [], []
    for section, (a, b, title, width, focus) in enumerate(SECTION_SPECS):
        sections.append({'start': a, 'end': b, 'title': title, 'focus': focus})
        for start in range(a, b+1, width):
            end = min(b, start+width-1)
            chunks.append({'start': start, 'end': end, 'section': section, 'label': f'{start}–{end}', 'focus': focus})
    # Backward acquisition of the coda, in groups that remain contiguous for
    # connection stages. The score/chunk map itself stays in printed order.
    return {
        'version': 1, 'piece_id': 'p53', 'title': 'Heroic Polonaise · Op. 53',
        'revision': 'paderewski-attacks-v1', 'key_fifths': -4, 'beats_per_measure': 3,
        'attack_limit': 8000,
        'analysis_status': 'model-reviewed', 'reference_status': 'model-reviewed',
        'previous_revision': 'paderewski-plan-v1-draft-attacks-v1',
        'reviewer': 'Codex; all fourteen Paderewski pages reviewed for pitches, octaves, ordered attacks, small notes, ties and local ornament marks, 2026-11-13. Model review, not independent editorial certification.',
        'scope': 'Pitch/attack counterpart for all 181 printed measures, including required printed grace notes and recorded ornament symbols. Trill/short-trill realization length is flexible only at enumerated local slots. The parenthesized Gb4 alternative at 21 is optional. This is not a facsimile or duration, fingering, pedal, expression or performance assessment. Independent musician review remains welcome.',
        'plan_summary': 'Learn the A-theme family first; compare its returns, then the contrasting episode and introduction. Secure the coda early. Study the octave trio as a separate branch, then the flowing development and final reprise. Join routes with boundary drills and larger blocks only after independent section recall.',
        'source': {'volume_id': 'polonaises', 'pdf_filename': pdf.name, 'pdf_sha256': PDF_HASH,
                   'pdf_pages': [60, 73], 'reference_sha256': REFERENCE_HASH,
                   'url': 'https://raw.githubusercontent.com/pl-wnifc/humdrum-chopin-first-editions/95dfb105c1669c72d10b04088566154f12d3dc1c/kern/053-1-Sm.krn',
                   'licence': 'Adapted from First Editions of Fryderyk Chopin’s Music; Copyright 2017–2021 The Fryderyk Chopin Institute; https://nifc.pl; https://chopinscores.org; CC BY 4.0 https://creativecommons.org/licenses/by/4.0/',
                   'scan_url': 'https://imslp.eu/files/imglnks/euimg/c/c3/IMSLP964068-PMLP209085-Chopin_Paderewski_No_8_Polonaises_scan.pdf'},
        'corrections': corrections,
        'review_gaps': [],
        'review_pages': [{'pdf_page': page, 'start': start,
                          'end': PAGE_STARTS[i+1][0]-1 if i+1 < len(PAGE_STARTS) else 181,
                          'status': 'model-reviewed'} for i,(start,page) in enumerate(PAGE_STARTS)],
        'sections': sections, 'section_order': ORDER, 'connection_strategy': 'independent-sections',
        'backward_sections': [12], 'bridges': [{'start': a, 'end': b, 'focus': 'Practise the outgoing phrase and the next entry as one route. Name which return or contrasting section comes next.'} for a,b in BRIDGES],
        'assembly': [{'start': a, 'end': b, 'focus': focus} for a,b,focus in
                     [(1,80,'Connect introduction and the complete first polonaise group.'),
                      (81,120,'Connect both octave episodes, their relaunch and exit; rest between attempts.'),
                      (121,154,'Connect the contrasting development and its retransition.'),
                      (155,181,'Connect final reprise to coda; preserve the final-return route.'),
                      (1,181,'Final whole-piece note-recall check after independent starts and all transition drills. Tempo, endurance and interpretation remain outside this judgement.')]],
        'chunks': chunks, 'measures': list(measures.values()), 'ornaments': ornaments}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path.home()/'.local/share/chopin-studio')
    parser.add_argument('--inventory', type=Path, default=ROOT/'data/heroic_polonaise_op53_review_inventory.txt')
    parser.add_argument('--output', type=Path, default=ROOT/'backend/chopin/learning_data/heroic_polonaise_op53.json')
    args = parser.parse_args()
    bundle = build(args.data_dir)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2)+'\n')
    args.inventory.write_text(inventory(bundle))
    print(f"{len(bundle['chunks'])} chunks; {len(bundle['measures'])} measures; model-reviewed pitch/attack counterpart")


if __name__ == '__main__':
    main()
