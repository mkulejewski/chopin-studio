"""Build the scan-reviewed Op.15/1 counterpart; never write the source library.

The complete lower staff is transcribed here from Paderewski PDF pp.22–25.
The pinned NIFC upper staff is a starting inventory, with explicit scan decisions.
Nominal attack positions aid display; this is not a measured score edition.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = '7e92d50bca4847d59673920428db355b.musicxml'
REFERENCE_HASH = '72398391f632561807898732beeeeacec32ca70ca886a3e9331dfacb4b5b1df1'
PDF_HASH = 'fbf6809027b4bd91e80864c5f43a16f78710f2f429fd234e839810ed9ddc9a6a'
PAGE_STARTS = [(0,22),(25,23),(37,24),(50,25)]


def spelling(value):
    match = re.fullmatch(r'([A-G])(bb|b|#|x)?(-?\d)', value)
    if not match:
        raise ValueError(value)
    step, accidental, octave = match.groups()
    return dict(step=step, alter={None:0,'b':-1,'bb':-2,'#':1,'x':2}[accidental], octave=int(octave))


def midi(note):
    return 12*(note['octave']+1)+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[note['step']]+note['alter']


def name(note):
    return note['step']+{-2:'bb',-1:'b',0:'',1:'#',2:'x'}[note['alter']]+str(note['octave'])


# Each row contains three triplet beats. '+' joins simultaneous attacks.
# Held bass notes appear only on their initial attack, including across barlines.
QUIET = {
1: 'F3+A3+F4 C4 C4 | A3+F4 C4 C4 | A3+E4 C4 C4',
2: 'F3+A3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
3: 'F3+G3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
4: 'F3+C4 A3 A3 | E3+G3+C#4 A3 A3 | D3+F3+D4 A3 A3',
5: 'D3+F3+B3 G3 G3 | Db3+F3+Bb3 G3 G3 | C3+E3+Bb3 G3 G3',
6: 'C3+E3+A3 F3 F3 | B2+D3+A3 F3 F3 | D3+A3 F3 F3',
7: 'B2+D3+G#3 E3 E3 | A2+C3+A3 E3 E3 | F2+B2+A3 D3 D3',
8: 'E2+B2+G#3 B3 B3 | G#3+E4 B3 B3 | G3+Bb3+E4 C4 C4',
9: 'F3+A3+F4 C4 C4 | A3+F4 C4 C4 | A3+E4 C4 C4',
10: 'F3+A3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | F3+G3+C4 Bb3 Bb3',
11: 'F3+G3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | F3+G3+C4 Bb3 Bb3',
12: 'F3+C4 A3 A3 | E3+G3+C#4 A3 A3 | G3+C#4 A3 A3',
13:'E3+G3+Db4 Bb3 Bb3 | G3+C4 Bb3 Bb3 | F#3+A3+D4 C4 C4',
14:'G3+Bb3+E4 C4 C4 | F3+A3+F4 C4 C4 | B3+G#4 D4 D4',
15: 'C3+C4 C4 C4 | A3+F4 C4 C4 | G3+E4 C4 C4',
16: 'F3+G3+Db4 B3 B3 | G3+Db4 B3 B3 | E3+G3+Db4 Bb3 Bb3',
17: 'Eb3+G3+Db4 Bb3 Bb3 | G3 Bb3 Bb3 | Eb3+Gb3+Db4 A3 A3',
18: 'Eb3+G3+C#4 A3 A3 | D3+F#3+C4 A3 A3 | D3+F3+B3 G3 G3',
19: 'C3+C4 C4 C4 | G3+Bb3+F4 C4 C4 | Bb3+E4 C4 C4',
20: 'F3+A3+F4 C4 C4 | B2+Ab3 Ab3 Ab3 | F3+D4 Ab3 Ab3',
21: 'C2+C4 C4 C4 | G3+Bb3+F4 C4 C4 | Bb3+E4 C4 C4',
22:'F3+A3+F4 C4 C4 | A3+F4 C4 C4 | A3+E4 C4 C4',
23: 'A3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
# 24 is two straight-eighth beats plus the fermata rest, defined below.
49: 'F2 C4 C4 | A3+F4 C4 C4 | A3+E4 C4 C4',
50: 'F3+A3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
51: 'F3+G3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
52: 'F3+C4 A3 A3 | E3+G3+C#4 A3 A3 | D3+F3+D4 A3 A3',
53: 'D3+F3+B3 G3 G3 | Db3+F3+Bb3 G3 G3 | C3+E3+Bb3 G3 G3',
54: 'C3+E3+A3 F3 F3 | B2+D3+A3 F3 F3 | D3+A3 F3 F3',
55: 'B2+D3+G#3 E3 E3 | A2+C3+A3 E3 E3 | F2+B2+A3 D3 D3',
# 56 has a reduced final accompaniment figure, defined below.
57:'F3+A3+F4 C4 C4 | A3+F4 C4 C4 | A3+E4 C4 C4',
58: 'F3+A3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | F3+G3+C4 Bb3 Bb3',
59: 'F3+G3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | F3+G3+C4 Bb3 Bb3',
60: 'F3+C4 A3 A3 | E3+G3+C#4 A3 A3 | G3+C#4 A3 A3',
61:'E3+G3+Db4 Bb3 Bb3 | G3+C4 Bb3 Bb3 | F#3+A3+D4 C4 C4',
62:'G3+Bb3+E4 C4 C4 | F3+A3+F4 C4 C4 | B3+G#4 D4 D4',
63: 'C3+C4 C4 C4 | A3+F4 C4 C4 | G3+E4 C4 C4',
64: 'F3+G3+Db4 B3 B3 | G3+Db4 B3 B3 | E3+G3+Db4 Bb3 Bb3',
65: 'Eb3+G3+Db4 Bb3 Bb3 | G3 Bb3 Bb3 | Eb3+Gb3+Db4 A3 A3',
66: 'Eb3+G3+C#4 A3 A3 | D3+F#3+C4 A3 A3 | D3+F3+B3 G3 G3',
67: 'C3+C4 C4 C4 | G3+Bb3+F4 C4 C4 | Bb3+E4 C4 C4',
68: 'F3+A3+F4 C4 C4 | B2+Ab3 Ab3 Ab3 | F3+D4 Ab3 Ab3',
69: 'C2+C4 C4 C4 | G3+Bb3+F4 C4 C4 | Bb3+E4 C4 C4',
70:'F3+A3+F4 C4 C4 | A3+F4 C4 C4 | A3+E4 C4 C4',
71: 'F3+A3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
72: 'F3+G3+D4 Bb3 Bb3 | G3+E4 Bb3 Bb3 | G3+C4 Bb3 Bb3',
}

# Teaching subdivisions, visually located in the scan; not an analytic edition.
SECTIONS = [
(0,8,'A · Opening sentence', 'Sing the melody, map the bass and then the triplet accompaniment. Keep long melody notes alive over the moving left hand. Use starts at the pickup, 5 and 7; include the pickup when joining the opening.'),
(9,16,'A · Decorated answer', 'Learn the little-note lead-ins and their destinations slowly. Compare the bass changes at 12–16 with the opening; sing the line before adding the accompaniment. Start independently at 9 and 13.'),
(17,24,'A · Closing sentence and stillness', 'Name the chromatic bass route and distinguish 19–20 from 21–22. Preserve the quiet cadence and fermata at 24. Prepare the F-minor entrance mentally before playing it.'),
(25,28,'B · Con fuoco launch', 'Map each left-hand sweep and landing first. Block the right-hand alternating intervals, then release into short relaxed groups. Coordinate slowly; stop and rest if tense. Loudness and speed are not memory goals.'),
(29,36,'B · First expansion and withdrawal', 'Extract the melody and bass from the moving texture. Learn the chromatic changes at 29–30, distinguish 31–32 from 33–34, then the descending exit and 6/8 at 36. Do not practise only from 25.'),
(37,40,'B · Relaunch', 'Compare with 25–28, then recall this occurrence independently. Name the route after 40: it goes into the new sequence, not back to 29.'),
(41,44,'B · New sequential climb', 'Block the changing harmony and name each bass destination. Isolate the natural signs at 42–44 and restore the upper-staff D naturals at 43; keep the inner movement separate from the bass.'),
(45,48,'B · Dissolving texture and return route', 'Sing the top voice, map the left-hand figuration, then coordinate in short sets. Isolate the tied melody and the 6/8 at 48. Practise arriving softly at 49 with a fresh tempo and key reset.'),
(49,56,'A′ · Varied return', 'Compare with 1–8; learn the new arpeggiated entry, seven-note run at 54 and rewritten answer at 55–56 as distinct events. Do not substitute the opening version from habit.'),
(57,64,'A′ · Decorated answer returns', 'Compare 57–64 with 9–16, including the different lead-in at 57. Learn ornaments as gestures with clear landing notes. Begin from 57 and 61 without a run-up.'),
(65,70,'A′ · Final closing sentence', 'Compare with 17–22 but name the final route. The small run at 68 contains a tiny repeated E and G-sharp; learn its exact contour before connecting 69–70.'),
(71,74,'Ending · Smorzando and final arpeggios', 'Learn 73–74 first, including the cross-staff arpeggios, then prepend 71–72 in normal playing order. Let the ending settle; preserve the distinction between the two final harmonies.'),
]
ORDER = [0,1,2,11,8,9,10,3,4,5,6,7]
BRIDGES = [(7,10),(15,18),(23,26),(27,30),(35,38),(39,42),(43,46),(47,50),(55,58),(63,66),(69,74)]


def transcribe(source):
    measures = {n:dict(number=n, pdf_page=max(p for a,p in PAGE_STARTS if a<=n),
                       key_fifths=-4 if 25<=n<=48 else -1,
                       time_signature=[6,8] if n in (36,48) else [3,4],
                       review_status='provisional', staves=[[],[]], spellings=[[],[]], grace_notes=[])
                for n in range(75)}
    raw = {n:[{},{}] for n in measures}
    def add(n, staff, beat, names):
        notes = [spelling(v) for v in names.split('+')] if names != '-' else []
        for note in notes:
            raw[n][staff].setdefault(F(beat), {})[midi(note)] = note
    def line(n, staff, names, step=F(1,6), start=0):
        for i, group in enumerate(names.split()): add(n, staff, F(start)+i*step, group)
    # Parse only the complete upper staff; the lower source part is incomplete.
    divisions=10080
    for bar in ET.parse(source).getroot().find('part').findall('measure'):
        n=int(bar.get('number')); cursor=last=F(0); pending=[]
        divisions=int(bar.findtext('attributes/divisions') or divisions)
        for item in bar:
            if item.tag in ('backup','forward'):
                cursor+=(-1 if item.tag=='backup' else 1)*F(int(item.findtext('duration')), divisions)
            if item.tag!='note': continue
            pitch=item.find('pitch')
            note=dict(step=pitch.findtext('step'), alter=int(pitch.findtext('alter') or 0), octave=int(pitch.findtext('octave'))) if pitch is not None else None
            if item.find('grace') is not None:
                if note: pending.append((cursor,note))
                continue
            chord=item.find('chord') is not None
            onset=last if chord else cursor
            if not chord:
                last=cursor; cursor+=F(int(item.findtext('duration') or 0),divisions)
            if note and not any(t.get('type')=='stop' for t in item.findall('tie')):
                raw[n][0].setdefault(onset,{})[midi(note)]=note
        for index,(before,note) in enumerate(pending):
            # Preserve ornament order without pretending to prescribe timing.
            same=[i for i,(beat,_) in enumerate(pending) if beat==before]
            pos=before-F(len(same)-same.index(index),64)
            raw[n][0].setdefault(pos,{})[midi(note)]=note
            measures[n]['grace_notes'].append(dict(staff=1, before_beat=str(before), attack_beat=str(pos), spellings=[note], policy='required'))
    for n, row in QUIET.items():
        tokens=row.replace('|','').split()
        assert len(tokens)==9,n
        line(n,1,' '.join(tokens),F(1,3))
    line(24,1,'F3+G3+D4 Bb3 F3+G3+E4 Bb3',F(1,2))
    line(56,1,'E2+B2+G#3 B3 B3 G#3+E4 B3 B3 G3+Bb3+E4 C4',F(1,3))
    add(56,1,F(8,3),'C4')
    # Con fuoco: complete scan-derived lower staff, including sustained voices.
    for n in (25,37):
        line(n,1,'F2+C3 B2 C3 Db3 C3 B2 C3 Bb2 Ab2 G2 F2 E2 F2 Eb2 Db2 C2 Bb1 Ab1')
    for n in (26,38):
        line(n,1,'F1 Db2 F2 Bb2 Db3',F(1,6))
        add(n,1,F(11,12),'F3'); add(n,1,1,'F3')
    for n in (27,39):
        line(n,1,'F2+Db3 C3 Db3 Eb3 Db3 C3 Db3 C3 Bb2 A2 Bb2 Ab2 G2 F2 Eb2 Db2 C2 Bb1')
    for n in (28,40):
        line(n,1,'F1 Gb2 C3 Eb3 Gb3',F(1,6))
        add(n,1,F(11,12),'C4'); add(n,1,1,'C4')
    # Sparse melody over held bass; tied continuations are deliberately absent.
    for n,events in {
        29:[(0,'Db3+C4'),(F(3,4),'Db4'),(1,'Bb3'),(2,'Ab3')],
        30:[(0,'Ab3'),(F(3,4),'Bb3'),(1,'Gb3'),(2,'F3')],
        31:[(0,'Gb2+Db3+F3'),(1,'Gb3'),(2,'Ab3')],
        32:[(0,'Bb3'),(1,'Ab3'),(2,'Db4')],
        33:[(0,'F3'),(1,'Db3+Gb3'),(2,'Ab3')],
        34:[(0,'Bb3'),(1,'Ab3'),(2,'Db4')],
        41:[(0,'Ab2+Eb3+Ab3'),(F(3,4),'F3'),(1,'Db3'),(2,'C3')],
        42:[(0,'B1+B2'),(F(3,4),'C2+C3'),(1,'Ab1+Ab2')],
        43:[(0,'Bb2+F3+Bb3'),(F(3,4),'Gb3'),(1,'Eb3'),(2,'D3')],
        44:[(0,'C#2+C#3'),(F(3,4),'D2+D3'),(1,'Bb1+Bb2')],
    }.items():
        for beat,notes in events:add(n,1,beat,notes)
    line(35,1,'E4 C4 E4 C4 E4 C4 F3+F4')
    line(45,1,'D4 Bb3 D4 Bb3 D4 Bb3 Eb3+Eb4 Bb3 Eb4 Bb3 Eb4 Bb3 D4 Bb3 D4 Bb3 D4 Bb3')
    line(46,1,'Eb3+Eb4 Bb3 Eb4 Bb3 Eb4 Bb3 C4 Ab3 C4 Ab3 C4 Ab3 Db3+Db4 Ab3 Db4 Ab3 Db4 Ab3')
    line(47,1,'Db4 Ab3 Db4 Ab3 Db4 Ab3 A3 F3 A3 F3 A3 F3 Bb2+Bb3 F3 Bb3 F3 Bb3 F3')
    line(48,1,'Bb3 F3 Bb3 F3 Bb3 F3 Bb3 F3 Bb3 F3 Bb3 F3',F(1,4))
    # Small notes engraved in the lower staff, absent from the base encoding.
    def grace(n,staff,before,values):
        values=values.split()
        for i,value in enumerate(values):
            pos=F(before)-F(len(values)-i,64)
            add(n,staff,pos,value)
            measures[n]['grace_notes'].append(dict(staff=staff+1,before_beat=str(before),attack_beat=str(pos),spellings=[spelling(value)],policy='required'))
    grace(33,1,0,'Db2')
    grace(35,1,0,'C3')
    grace(45,1,0,'Bb2'); grace(45,1,2,'Bb2')
    grace(46,1,1,'Ab2'); grace(47,1,1,'F2')
    # Source errors / edition differences in the upper staff.
    corrections=[]
    def replace(n,beat,before,after,reason):
        pos=F(beat); actual=raw[n][0][pos]
        assert sorted(map(name,actual.values()))==sorted(before.split('+')),(n,beat,list(map(name,actual.values())))
        raw[n][0][pos]={midi(spelling(v)):spelling(v) for v in after.split('+')}
        corrections.append(dict(measure=n,staff=1,beat=str(pos),before=before,after=after,reason=reason))
    for pos in (F(1,3),F(2,3)):
        replace(43,pos,'Bb4+Db4','Bb4+D4','The printed natural at D4 applies through the first beat.')
    for pos in (1,F(4,3),F(5,3)):
        replace(43,pos,'Bb4+Db4','Bb4+Eb4','Second-beat lower alternating note is E-flat4, not D-flat4.')
    # At 68 the repeated E is an explicitly engraved smaller lead-in within
    # the small-note run. The following G has a printed sharp in Paderewski.
    old=sorted((g for g in measures[68]['grace_notes'] if g['staff']==1),key=lambda g:F(g['attack_beat']))
    assert len(old)==9
    for g in old:raw[68][0].pop(F(g['attack_beat']))
    measures[68]['grace_notes']=[]
    grace(68,0,3,'E5 F5 E5 D5 E5 E5 G#5 F5 D5')
    measures[68]['grace_notes'][5]['nested_grace']=True
    corrections.append(dict(measure=68,staff=1,reason='Restore printed G-sharp5. Preserve the tiny repeated E5 lead-in within the nine-note run; it is not a conversion duplicate.'))
    # Final arpeggios cross the engraved staves: do not assign all notes to RH.
    for n,lower in [(73,5),(74,3)]:
        gs=sorted(measures[n]['grace_notes'],key=lambda g:F(g['attack_beat']))
        for g in gs[:lower]:
            pos=F(g['attack_beat']);raw[n][1][pos]=raw[n][0].pop(pos);g['staff']=2
        corrections.append(dict(measure=n,reason='Preserve printed ownership of the cross-staff final arpeggio; hand choice is a separate performance decision.'))
    for n,m in measures.items():
        for staff in (0,1):
            for beat,notes in sorted(raw[n][staff].items()):
                ordered=sorted(notes.values(),key=midi)
                m['staves'][staff].append([str(beat),list(map(midi,ordered))])
                m['spellings'][staff].append(ordered)
    return list(measures.values()),corrections


def validate_review(measures, review):
    """Bind each visual audit decision to the exact reviewed digital inventory.

    The builder cannot regenerate or approve this ledger. A transcription change
    requires revisiting the affected printed measure and updating its audit.
    """
    if (review.get('review_status')!='model-reviewed' or review.get('piece_id')!='n15-1'
            or review.get('pdf_sha256')!=PDF_HASH or review.get('reference_sha256')!=REFERENCE_HASH):
        raise ValueError('The scan-review ledger does not match these sources')
    reviewed=review['measures']
    if [r['number'] for r in reviewed]!=list(range(75)):
        raise ValueError('The scan-review ledger must cover every printed measure and pickup')
    fields=('number','pdf_page','key_fifths','time_signature','staves','spellings','grace_notes')
    for measure,record in zip(measures,reviewed):
        canonical={key:measure[key] for key in fields}
        digest=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if (digest!=record['inventory_sha256'] or record['status']!='model-reviewed'
                or record['pdf_page']!=measure['pdf_page']):
            raise ValueError(f"Digital inventory changed after scan review at measure {measure['number']}")


def build(data_dir):
    source=data_dir/'references'/REFERENCE
    pdf=data_dir/'scores/paderewski_nocturnes.pdf'
    for path,digest in [(source,REFERENCE_HASH),(pdf,PDF_HASH)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Unrecognized input: {path.name}; review a new revision first')
    manifest=json.loads((data_dir/'references/current-manifest.json').read_text())
    provenance=next(x for x in manifest if x['piece_id']=='n15-1')
    measures,corrections=transcribe(source)
    review=json.loads((ROOT/'data/nocturne_op15_no1_scan_review.json').read_text())
    validate_review(measures,review)
    for measure in measures:
        measure['review_status']='model-reviewed'
    sections=[dict(start=a,end=b,title=t,focus=f) for a,b,t,f in SECTIONS]
    chunks=[]
    for i,(a,b,title,focus) in enumerate(SECTIONS):
        starts=list(range(1 if a==0 else a,b+1,2))
        for j,start in enumerate(starts):
            start=0 if a==0 and j==0 else start
            end=min(b,(1 if start==0 else start)+1)
            chunks.append(dict(start=start,end=end,section=i,label=('pickup + 1–2' if start==0 else f'{start}–{end}'),focus=focus))
    return dict(version=1,piece_id='n15-1',title='Nocturne · Op. 15 No. 1',revision='paderewski-attacks-v1',
                previous_revision='paderewski-scan-study-v1',
                key_fifths=-1,beats_per_measure=3,attack_limit=6000,
                analysis_status='model-reviewed',reference_status='model-reviewed',
                reviewer='Codex; all four Paderewski pages and both staves of every measure visually audited for pitches, accidentals, octaves, chords, ordered attacks, ties, printed small notes and staff crossings, 2026-11-14. Model review, not independent editorial certification. Per-measure decisions and inventory hashes are recorded in data/nocturne_op15_no1_scan_review.json.',
                scope='Complete 0–74 model-reviewed pitch/attack counterpart, including the opening pickup, printed small notes, tied continuations and engraved staff ownership. All 1,801 attacks are reviewed against the exact Paderewski scan. Automatic pitch evaluation uses the authoritative captured take. The source scan governs rhythm, sustain, voicing, fingering, pedal and expression; these are not graded. This is an unmeasured study, not an engraved critical edition or a musical-quality assessment.',
                plan_summary='Learn the three quiet opening sentences; secure the ending backwards early. Compare and learn the varied return separately. Acquire the storm as five independent short sections, mapping bass and melody before figuration. Join the cadence, relaunch and Tempo I boundaries, then assemble A, B, A′ and the whole piece. Use independent starts and relaxed short sets; concert tempo is not required.',
                source=dict(volume_id='nocturnes',pdf_filename=pdf.name,pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),pdf_pages=[22,25],reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),url=provenance['source'],licence=provenance['licence'],scan_url='https://imslp.eu/files/imglnks/euimg/1/1d/IMSLP972729-PMLP209085-ChopinPaderewskiPWM_VII_Nocturnes.pdf'),
                corrections=corrections,
                review_gaps=[],
                review_pages=[dict(pdf_page=p,start=a,end=PAGE_STARTS[i+1][0]-1 if i+1<len(PAGE_STARTS) else 74,status='model-reviewed') for i,(a,p) in enumerate(PAGE_STARTS)],
                measure_reviews=review['measures'],
                sections=sections,chunks=chunks,section_order=ORDER,backward_sections=[11],connection_strategy='independent-sections',
                bridges=[dict(start=a,end=b,focus='Name the outgoing harmony, next entry and tempo before joining these boundary bars. Keep the route specific to this occurrence.') for a,b in BRIDGES],
                assembly=[dict(start=a,end=b,focus=f) for a,b,f in [(0,24,'Opening pickup and complete quiet A section.'),(25,48,'Complete storm; short relaxed attempts with rests.'),(49,74,'Varied return and ending, without substituting the opening version.'),(0,74,'Whole-piece recall after independent starts and boundary routes are secure.')]],
                measures=measures,ornaments=[])


def inventory(bundle):
    rows=['Op.15 No.1 - model-reviewed Paderewski attack inventory',bundle['scope'],'']
    for m in bundle['measures']:
        rows.append(f"Measure {m['number']} · PDF {m['pdf_page']}")
        for s in (0,1):
            rows.append(('RH ' if s==0 else 'LH ')+' | '.join(beat+':'+','.join(map(name,notes)) for (beat,_),notes in zip(m['staves'][s],m['spellings'][s])))
    return '\n'.join(rows)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    args=parser.parse_args()
    bundle=build(args.data_dir)
    (ROOT/'backend/chopin/learning_data/nocturne_op15_no1.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data/nocturne_op15_no1_review_inventory.txt').write_text(inventory(bundle))
