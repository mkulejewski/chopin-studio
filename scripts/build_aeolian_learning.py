"""Rebuild the model-reviewed Paderewski Op.25/1 pitch/attack counterpart.

Requires the exact cached PDF and NIFC-to-Music21 source identified below.
This script replays documented corrections; checks do not independently prove
musical equivalence. See docs/AEOLIAN_LEARNING.md for the visual-review record.
"""
import argparse
import copy,hashlib,json,xml.etree.ElementTree as E
from fractions import Fraction as F
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path.home()/'.local/share/chopin-studio')
parser.add_argument('--output',type=Path,default=root/'backend/chopin/learning_data/aeolian.json')
parser.add_argument('--inventory',type=Path,default=root/'data/aeolian_review_inventory.txt')
args=parser.parse_args()
source_path=args.data_dir/'references/e1419432ded045abbb9a37cdd79086ee.musicxml'
pdf=args.data_dir/'scores/paderewski_etudes.pdf'
if hashlib.sha256(source_path.read_bytes()).hexdigest()!='81c15b3e01ab1db8074974cf2b3c1df351d97fbf4345324e45931ea18c8b64d1':raise ValueError('Unreviewed digital input')
if hashlib.sha256(pdf.read_bytes()).hexdigest()!='d88745ff8b7647759e000b5be8f8bd23b016bc77aacc5a8ceced3c4fa2d67ee3':raise ValueError('Unreviewed printed input')
xml=E.parse(source_path).getroot()
fixes=[]
def change(staff,m,index,old,new):
 part=xml.findall('part')[staff-1]; bar=next(b for b in part.findall('measure') if b.get('number')==str(m))
 n=bar.findall('note')[index];pitch=n.find('pitch')
 def name(p):return p.findtext('step')+{-1:'b',0:'',1:'#'}[int(p.findtext('alter') or 0)]+p.findtext('octave')
 if name(pitch)!=old:raise ValueError(f'Unexpected source pitch: {staff}, {m}, {index}, {name(pitch)}; expected {old}')
 pitch.find('step').text=new[0];pitch.find('octave').text=new[-1]
 a=pitch.find('alter')
 if a is None:a=E.SubElement(pitch,'alter')
 a.text=str(-1 if 'b' in new else 1 if '#' in new else 0)
 fixes.append({'staff':staff,'measure':m,'attack_index':index,'before':old,'after':new})
for i in (15,21):change(2,15,i,'Db4','D4')
change(1,22,9,'Db4','D4')
for i in (19,22):change(1,22,i,'G#4','G4')
for i in (20,22):change(2,22,i,'G#3','G3')
for m in (23,24):
 for i in (3,21):change(1,m,i,'Eb4','E4')
 change(1,m,9,'Db4','D4')
 for i in (15,21):change(2,m,i,'Db4','D4')
change(2,23,9,'Bb3','B3')
for i in (3,9):change(1,25,i,'Eb4','E4')
change(1,25,21,'A4','Ab4')
for i in (2,4,8,10):change(2,25,i,'Ab3','A3')
change(2,25,18,'A2','Ab2')
change(1,33,12,'Ab5','A5')
change(1,34,15,'Ab4','A4')
bar=next(b for b in xml.findall('part')[1].findall('measure') if b.get('number')=='16')
for n in bar.findall('note')[18:]:
 n.find('duration').text='1680'
 tm=n.find('time-modification')
 if tm is not None:
  tm.find('actual-notes').text='3';tm.find('normal-notes').text='2'
n=copy.deepcopy(bar.findall('note')[-1]);n.find('pitch/step').text='G';n.find('pitch/octave').text='2';bar.append(n)
fixes.append({'staff':2,'measure':16,'before':'C2 G2 C3 G3 C3 (five attacks)','after':'C2 G2 C3 G3 C3 G2 (six attacks at sextuplet positions)'})
measures={i:{'number':i,'pdf_page':64 if i<=8 else 65 if i<=18 else 66 if i<=28 else 67 if i<=38 else 68,'staves':[]} for i in range(50)}
for staff,part in enumerate(xml.findall('part'),1):
 div=10080
 for bar in part.findall('measure'):
  m=int(bar.get('number'));beat=F(0);last=F(0);groups=[]
  for n in bar.findall('note'):
   if n.find('chord') is not None:beat-=last
   d=F(int(n.findtext('duration') or 0),div);p=n.find('pitch')
   if n.find('grace') is not None:continue
   if p is not None:
    pitch=12*(int(p.findtext('octave'))+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p.findtext('step')]+int(p.findtext('alter') or 0)
    if groups and groups[-1][0]==str(beat):groups[-1][1].append(pitch)
    else:groups.append([str(beat),[pitch]])
   beat+=d;last=d
  measures[m]['staves'].append(groups)
# Small grace lead-in belongs to the explicitly flexible final trill, not two mandatory attacks.
# In the conversion they precede the main Eb2 at the same score onset.

sections=[(0,8,'Opening: tonic pattern and first departure'),(9,16,'Varied return and approach to the middle'),(17,25,'Independent left-hand patterns and chromatic sequence'),(26,35,'Sequential expansion and climax'),(36,43,'Return and descent'),(44,49,'Register sweep and closing gestures')]
chunks=[]
for section,(start,end,title) in enumerate(sections):
 ranges=([(0,2),(3,4),(5,6),(7,8)] if start==0 else [(9,10),(11,12),(13,14),(15,16)] if start==9 else [(i,i) for i in range(start,end+1)] if start in (17,26) else [(36,37),(38,39),(40,41),(42,43)] if start==36 else [(44,44),(45,45),(46,47),(48,49)])
 for a,b in ranges:
  chunks.append({'start':a,'end':b,'section':section,'label':f'{"Pickup–" if a==0 else str(a)+"–"}{b}' if a!=b else str(a),'focus': title + ('; compare the changed melody/bass with the opening' if 9<=a<=14 else '; learn each hand sequence before coordinating them' if 17<=a<=21 else '; name the altered pitches before playing' if 22<=a<=25 else '; inspect the new bass and register carefully' if 26<=a<=35 else '')})

# Deliberate passage-by-passage model lesson analysis, not an automatic form detector.
focus={
0:'Learn the Eb5 pickup, then the Ab/C/Eb arpeggio. The first bass is Ab1; later bass attacks rise to Ab2. Notice F5 at the start of measure 2.',
3:'Learn the G/Db inner pattern in measure 3, then the Bb5-to-Ab5 melody in measure 4. E naturals change both staves halfway through measure 4.',
5:'Anchor the low Db2 entry and higher Db3 repetitions. Measure 6 changes its bass on each beat and introduces Cb; name each six-note cell.',
7:'Follow the descending upper line into the lower register. Keep the D naturals in measure 7 distinct from the Db material in measure 8.',
9:'Rebuild the opening Ab arpeggio as a separate occurrence. Recall the low Ab1 entry rather than assuming every bass is Ab2.',
11:'Compare with measures 3–4: the inner pattern returns, but measure 11 now reaches Bb5 and C6 before G5. Measure 12 restores the E naturals.',
13:'Compare with measures 5–6. Measure 14 reaches C6 then repeats G5 over a changing F-to-E inner pattern; do not copy measure 6 unchanged.',
15:'Learn B, D and E naturals explicitly. The lower D4 is natural in the last two cells of measure 15. All four lower-staff cells in measure 16 have six attacks.',
17:'Learn the repeating E2–C3–Bb3–C3 lower pattern independently of the six-note upper cells. The upper melody changes to Db5 on beat 3.',
18:'The bass stays F2 while the upper lower-staff tone descends Bb3, Ab3, G3, F3. The upper staff changes C5, D5, E5, F5.',
19:'Remember G2–Eb3–Db4–Eb3 below the six-note upper pattern. The upper first note changes to F5 on beat 3.',
20:'The Ab2 bass returns. The upper lower-staff tone descends Db4–C4–Bb3–Ab3 while the upper melody rises Eb5–F5–G5–Ab5.',
21:'Learn the four changing lower cells separately: Eb2, C3, F2, then G2 entries. The last lower group has five attacks. Watch D and B naturals.',
22:'Both staves return to six-note cells. Learn the explicit E, D and B naturals; the last G pitches in both staves are natural, not sharp.',
23:'Anchor the B2 bass after the first cell. Learn the G sharps and the low E4/D4 naturals; the lower-staff B3 and D4 are also natural.',
24:'Anchor A2. Name C# and F# while keeping the low E4 and D4 natural. The last cell introduces G# in both staves.',
25:'Begin with A and E naturals and C#. Rise through the chromatic sequence, then flatten A to Ab in the last cell in both staves.',
26:'Alternate low Db2 and Db3 bass entries. The upper line C6–Bb5–Db6–F5 changes its inner pattern halfway through the measure.',
27:'Alternate Eb2 and C3 in the bass. Learn the upper Bb5–Ab5–C6–Eb5 outline and the inner-pattern change on beat 3.',
28:'Alternate Eb2 and Bb2 below. The upper outline Eb5–E5–F5–Eb5 requires restoring Eb after the natural.',
29:'Learn the shorter lower groups around F2/C3 separately. The upper staff descends Db5 to C5 before leaping to C6 in the last cell.',
30:'Alternate Bb1 and Bb2. The last two cells flatten F in both staves; do not reuse the unaltered pattern from measure 26.',
31:'Relearn the returning measure-27 pattern at this occurrence. Connect its Eb2/C3 bass alternation to the altered pattern in measure 32.',
32:'The lower pattern now uses A3 and C4, with F4 at the end. Learn the upper Eb5–F5–Gb5–F5 outline and A naturals.',
33:'Name the B and D naturals below. The third upper cell starts on A5 natural and uses B4 natural; keep its F4 inner attack.',
34:'The Eb bass supports widening register changes. The third cell has A naturals in two octaves; the last cell leaps to Gb6.',
35:'Learn the high F6 entry and the changes from D natural to Db below and F to Fb above. Finish the descent to G5 before returning to Ab.',
36:'Reconnect the Ab return to the changing upper line in measure 37: F5, Eb5, C6, G5. Keep every inner arpeggio attack.',
38:'The return repeats, but measure 39 reaches F6 rather than the previous C6. Learn this changed summit as its own landmark.',
40:'Recall the returning Ab pattern with its F5 change, then descend through the alternating Db5/C5 cells in measure 41.',
42:'Learn the low Ab1 accompaniment and alternating Bb4/Ab4 upper cells. Measures 42–43 repeat the same note pattern before the register sweep.',
44:'The upper staff begins with a rest, then joins the rising sweep. Read the actual sounding octaves under the ottava marking; both staves change register.',
45:'Connect the continuing high-to-low and low-to-high sweeps. Keep the lower staff a distinct sequence; avoid shifting either hand an octave.',
46:'After the first descending cell of measure 46, settle into the narrower repeating Ab pattern. Carry it through all of measure 47.',
48:'Recall the closing single attacks and rolled chords in any chord-tone order. The D2/Eb2 grace lead-in and trill length are flexible; the main Eb2 and final chord remain required.'
}
for c in chunks:c['focus']=focus[c['start']]
bundle={'version':1,'piece_id':'e25-1','title':'Aeolian Harp · Op. 25 No. 1','revision':'paderewski-attacks-v1','analysis_status':'model-reviewed','reference_status':'model-reviewed','reviewer':'Codex; full five-page visual pitch/attack review, 2026-11-11','scope':'Pitches, octaves, attack order, chords and printed measure identity. Not a facsimile engraving or duration, fingering, pedal or interpretation assessment. Model review; independent musician review remains welcome.','source':{'reference_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'url':'https://raw.githubusercontent.com/pl-wnifc/humdrum-chopin-first-editions/95dfb105c1669c72d10b04088566154f12d3dc1c/kern/025-1b-LE-001.krn','licence':'Adapted from First Editions of Fryderyk Chopin’s Music; Copyright 2017–2021 The Fryderyk Chopin Institute; https://nifc.pl; https://chopinscores.org; CC BY 4.0 https://creativecommons.org/licenses/by/4.0/','pdf_filename':'paderewski_etudes.pdf','pdf_sha256':'d88745ff8b7647759e000b5be8f8bd23b016bc77aacc5a8ceced3c4fa2d67ee3','pdf_pages':[64,68]},'corrections':fixes,'sections':[{'start':a,'end':b,'title':s} for a,b,s in sections],'chunks':chunks,'measures':list(measures.values()),'ornaments':[{'measure':48,'staff':2,'pitches':[38,39],'policy':'Optional D2–Eb2 lead-in and any number of D2/Eb2 trill alternations around the required main Eb2. No speed or alternation-count grade.'}]}
args.output.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
names=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
inventory=['Paderewski Op.25 No.1 - reviewed required attack inventory', 'Printed measure 0 = pickup. Brackets = one simultaneous chord.', 'm48 lower-staff D2/Eb2 grace lead-in and trill alternations are optional; main Eb2 required.', 'This is an attack inventory, not a complete duration or expression transcription.', '']
for staff in range(2):
 inventory.append('UPPER STAFF' if staff==0 else 'LOWER STAFF')
 for m in bundle['measures']:
  groups=[]
  for beat,pitches in m['staves'][staff]:
   notes=','.join(names[p%12]+str(p//12-1) for p in pitches)
   groups.append(f'{beat}:['+notes+']')
  inventory.append(str(m['number'])+': '+' '.join(groups))
args.inventory.write_text('\n'.join(inventory)+'\n')
print('fixes',len(fixes),'chunks',len(chunks))
