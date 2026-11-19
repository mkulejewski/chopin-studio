"""Build individually scan-audited Practice references; preserve all originals.

Only pieces with a completed review and an implemented correction builder may
be installed. A source conversion, successful parse or missing quality flag is
never sufficient to mark another piece verified.
"""
import argparse
import copy
from fractions import Fraction
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

from chopin.symbolic import parse_musicxml

ROOT=Path(__file__).resolve().parents[1]
REVIEW_ROOT=ROOT/'backend/chopin/reference_reviews'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def element(parent,tag,text=None,**attributes):
    node=ET.SubElement(parent,tag,attributes)
    if text is not None:node.text=str(text)
    return node


def prelude28_4(source):
    """Paderewski PDF p.13 / printed p.11; pickup 0 and measures 1-25."""
    tree=ET.parse(source).getroot()
    upper,lower=tree.findall('part')
    if len(upper.findall('measure'))!=26 or len(lower.findall('measure'))!=26:
        raise ValueError('Unexpected Prelude source coverage')
    changes={2:{('E','-1','4'):('D',1)},3:{('E','-1','4'):('D',1)},
             14:{('E','-1','4'):('D',1)},
             15:{('A','-1','3'):('G',1),('E','-1','4'):('D',1)},
             23:{('B','-1','2'):('A',1)}}
    for measure in lower.findall('measure'):
        number=int(measure.get('number'))
        for note in measure.findall('note'):
            pitch=note.find('pitch')
            if pitch is None:continue
            key=(pitch.findtext('step'),pitch.findtext('alter','0'),pitch.findtext('octave'))
            replacement=changes.get(number,{}).get(key)
            if replacement:
                pitch.find('step').text=replacement[0]
                pitch.find('alter').text=str(replacement[1])
                if note.find('accidental') is not None:note.find('accidental').text='sharp'
    # Repair the conversion's unterminated beam in printed measure 18, matching
    # the scan's two eighth pairs followed by four beamed eighth-note chords.
    groups=[]
    for note in lower.find("measure[@number='18']").findall('note'):
        for beam in list(note.findall('beam')):note.remove(beam)
        if note.find('chord') is None:groups.append(note)
    if len(groups)!=8:raise ValueError('Unexpected measure 18 accompaniment')
    for index,note in enumerate(groups):
        element(note,'beam','begin' if index in (0,2,4) else 'end' if index in (1,3,7) else 'continue',number='1')
    # The same B4 is sustained across the printed 12/13 system break.
    for number,side,kind in [(12,-1,'start'),(13,0,'stop')]:
        note=upper.find(f"measure[@number='{number}']").findall('note')[side]
        if (note.findtext('pitch/step'),note.findtext('pitch/octave'))!=('B','4'):
            raise ValueError('Tie source changed')
        element(note,'tie',type=kind)
        notation=note.find('notations')
        if notation is None:notation=element(note,'notations')
        element(notation,'tied',type=kind)

    # Grand-staff export preserves the printed crossing into the bass staff in
    # the final two measures, rather than confusing staff with physical hand.
    result=ET.Element('score-partwise',version='4.0')
    for tag in ('identification','defaults'):
        if tree.find(tag) is not None:result.append(copy.deepcopy(tree.find(tag)))
    work=element(result,'work')
    element(work,'work-title','Prelude Op. 28 No. 4 - Paderewski reviewed notes and rhythm')
    parts=element(result,'part-list');info=element(parts,'score-part',id='P1')
    element(info,'part-name','Piano')
    piano=element(result,'part',id='P1')
    dynamics={0:'p',17:'f',19:'p',24:'pp'}
    words={0:'Largo; espressivo',16:'stretto',18:'dim.',21:'smorz.'}
    for rh,lh in zip(upper.findall('measure'),lower.findall('measure')):
        number=int(rh.get('number'));measure=element(piano,'measure',number=str(number))
        divisions=10080
        duration=divisions if number==0 else 4*divisions
        if number==0:
            attrs=element(measure,'attributes');element(attrs,'divisions',divisions)
            element(element(attrs,'key'),'fifths',1)
            time=element(attrs,'time',symbol='cut');element(time,'beats',2);element(time,'beat-type',2)
            element(attrs,'staves',2)
            for staff,sign,line in [(1,'G',2),(2,'F',4)]:
                clef=element(attrs,'clef',number=str(staff));element(clef,'sign',sign);element(clef,'line',line)
        if number in dynamics:
            for staff in (1,2):
                direction=element(measure,'direction',placement='below')
                element(element(element(direction,'direction-type'),'dynamics'),dynamics[number])
                element(direction,'staff',staff)
        if number in words:
            direction=element(measure,'direction',placement='above')
            element(element(direction,'direction-type'),'words',words[number]);element(direction,'staff',1)
        for staff,original in ((1,rh),(2,lh)):
            if staff==2:element(element(measure,'backup'),'duration',duration)
            for item in original:
                if item.tag in ('attributes','print','direction'):continue
                if item.tag=='barline' and staff==1:continue
                if item.tag in ('backup','forward'):
                    raise ValueError('Unexpected multi-voice source cursor; review before merging')
                node=copy.deepcopy(item)
                if node.tag=='note':
                    voice=node.find('voice')
                    if voice is None:voice=element(node,'voice')
                    voice.text=str(staff)
                    target=2 if staff==2 or number>=24 else 1
                    score_staff=node.find('staff')
                    if score_staff is None:score_staff=element(node,'staff')
                    score_staff.text=str(target)
                    for slur in node.findall('.//slur'):
                        if staff==2:slur.set('number',str(int(slur.get('number','1'))+6))
                    for notation in node.findall('notations'):
                        for mark in list(notation):
                            if mark.tag not in ('tied','ornaments','fermata','tuplet'):notation.remove(mark)
                    order={tag:i for i,tag in enumerate(('grace','cue','chord','pitch','unpitched','rest',
                           'duration','tie','instrument','voice','type','dot','accidental','time-modification',
                           'stem','notehead','staff','beam','notations','lyric'))}
                    node[:]=sorted(node,key=lambda child:order.get(child.tag,100))
                measure.append(node)
    ET.indent(result)
    return ET.tostring(result,encoding='utf-8',xml_declaration=True)


def mazurka68_3(source):
    """All 60 printed measures, Paderewski PDF pp.164-165 / pp.160-161."""
    tree=ET.parse(source).getroot()
    parts=tree.findall('part')
    if len(parts)!=2 or any(len(p.findall('measure'))!=60 for p in parts):
        raise ValueError('Unexpected Mazurka source coverage')
    tree.find('work/work-title').text='Mazurka Op. 68 No. 3 - Paderewski reviewed notes and rhythm'
    title=tree.find('movement-title')
    if title is not None:title.text='Mazurka Op. 68 No. 3 - Paderewski reviewed notes and rhythm'
    # The curved marks over the two upper voices are phrase slurs in this
    # edition. C#5 is attacked again on beat 3, not tied from beat 2.
    for number in (18,22):
        for note in parts[0].find(f"measure[@number='{number}']").findall('note'):
            for tie in list(note.findall('tie')):note.remove(tie)
            for tie in list(note.findall('notations/tied')):note.find('notations').remove(tie)
    # Retain pitches, durations and independent voices; remove unreviewed
    # first-edition expression marks and replace only scan-reviewed directions.
    for part in parts:
        for measure in part.findall('measure'):
            for direction in list(measure.findall('direction')):measure.remove(direction)
            # Converted beams can remain open across several measures. Rebuild
            # the scan's short rhythmic groups, independently for each voice.
            voices={}
            for note in measure.findall('note'):
                for beam in list(note.findall('beam')):note.remove(beam)
                if note.find('grace') is None and note.find('chord') is None:
                    voices.setdefault(note.findtext('voice','1'),[]).append(note)
            number=int(measure.get('number'))
            for voice_notes in voices.values():
                beam_notes=[]
                if part is parts[0] and 37<=number<=44:
                    beam_notes=[n for n in voice_notes if n.findtext('type')=='eighth']
                elif len(voice_notes)>=2 and all(n.findtext('type') in ('eighth','16th') for n in voice_notes[:2]):
                    beam_notes=voice_notes[:2]
                elif part is parts[1] and number in (7,51):
                    beam_notes=[n for n in voice_notes if n.findtext('type')=='eighth']
                if len(beam_notes)>1:
                    for i,note in enumerate(beam_notes):
                        # staff precedes beam; notations follow it in MusicXML.
                        beam=ET.Element('beam',number='1');beam.text='begin' if i==0 else 'end' if i==len(beam_notes)-1 else 'continue'
                        pos=next((i for i,n in enumerate(note) if n.tag=='notations'),len(note))
                        note.insert(pos,beam)
                        if note.findtext('type')=='16th':
                            hook=ET.Element('beam',number='2');hook.text='backward hook';note.insert(pos+1,hook)
            for notation in measure.findall('note/notations'):
                for mark in list(notation):
                    if mark.tag not in ('tied','ornaments','fermata','tuplet'):notation.remove(mark)
        measure=part.find("measure[@number='24']")
        for note in measure.findall('note'):
            if note.findtext('type')=='half' and note.find('chord') is None:
                notation=note.find('notations')
                if notation is None:notation=element(note,'notations')
                if notation.find('fermata') is None:element(notation,'fermata')
        dynamics={1:'f',9:'p',17:'ff',21:'p',25:'p',37:'p',45:'f',53:'p'}
        words={1:'Allegro, ma non troppo',33:'Poco più vivo',44:'rit.',45:'Tempo I'}
        for number,level in dynamics.items():
            m=part.find(f"measure[@number='{number}']")
            direction=ET.Element('direction',placement='below')
            element(element(direction,'direction-type'),'dynamics').append(ET.Element(level))
            m.insert(1 if m.find('attributes') is not None else 0,direction)
        if part is parts[0]:
            for number,word in words.items():
                m=part.find(f"measure[@number='{number}']")
                direction=ET.Element('direction',placement='above')
                element(element(direction,'direction-type'),'words',word)
                m.insert(1 if m.find('attributes') is not None else 0,direction)
    ET.indent(tree)
    return ET.tostring(tree,encoding='utf-8',xml_declaration=True)


def mazurka68_2(source):
    """Paderewski PDF pp.162-163, pickup 0 and printed measures 1-65."""
    tree=ET.parse(source).getroot();parts=tree.findall('part')
    if len(parts)!=2 or any(len(p.findall('measure'))!=66 for p in parts):
        raise ValueError('Unexpected Mazurka source coverage')
    title='Mazurka Op. 68 No. 2 - Paderewski reviewed notes and rhythm'
    tree.find('work/work-title').text=title
    if tree.find('movement-title') is not None:tree.find('movement-title').text=title
    # The scan writes a two-small-note ending after every trill, not only the
    # first occurrence of each figure. The source conversion omits most pairs.
    for measure in parts[0].findall('measure'):
        for note in list(measure.findall('note')):
            if note.find('notations/ornaments/trill-mark') is None:continue
            step=note.findtext('pitch/step');octave=note.findtext('pitch/octave')
            ending={('D','5'):[('C',2,5),('D',1,5)],
                    ('G','4'):[('F',1,4),('G',1,4)],
                    ('F','5'):[('E',1,5),('F',1,5)]}[(step,octave)]
            pos=list(measure).index(note)+1
            existing=[]
            while pos<len(measure) and measure[pos].tag=='note' and measure[pos].find('grace') is not None:
                existing.append(measure[pos]);pos+=1
            if existing:
                if len(existing)!=2:raise ValueError('Unexpected trill ending')
                continue
            pos=list(measure).index(note)+1
            for index,(s,a,o) in enumerate(ending):
                grace=ET.Element('note');element(grace,'grace')
                pitch=element(grace,'pitch');element(pitch,'step',s);element(pitch,'alter',a);element(pitch,'octave',o)
                element(grace,'type','16th');element(grace,'stem','up')
                for beam_number in ('1','2'):element(grace,'beam','begin' if index==0 else 'end',number=beam_number)
                measure.insert(pos,grace);pos+=1
    # Both staves share the same repeat routes and first/second endings.
    for part in parts:
        for m in part.findall('measure'):
            for repeat in list(m.findall('barline/repeat')):
                if repeat.get('direction')=='backward' and int(m.get('number')) in (36,37):
                    m.find('barline').remove(repeat)
        def bar(number,location):
            m=part.find(f"measure[@number='{number}']")
            node=next((b for b in m.findall('barline') if b.get('location')==location),None)
            if node is None:node=element(m,'barline',location=location)
            return node
        for number,which in ((28,'1'),(29,'2')):
            element(bar(number,'left'),'ending',type='start',number=which)
            element(bar(number,'right'),'ending',type='stop',number=which)
        element(bar(37,'right'),'repeat',direction='backward')
        for m in part.findall('measure'):
            for direction in list(m.findall('direction')):m.remove(direction)
            for notation in m.findall('note/notations'):
                for mark in list(notation):
                    if mark.tag not in ('tied','ornaments','fermata','tuplet'):notation.remove(mark)
        for number,level in {0:'p',8:'pp',16:'mf',21:'p',28:'mf',30:'mf',32:'f',33:'pp',34:'p',36:'mf',37:'pp',46:'p',53:'mf',58:'p'}.items():
            m=part.find(f"measure[@number='{number}']");direction=ET.Element('direction',placement='below')
            element(element(direction,'direction-type'),'dynamics').append(ET.Element(level))
            if number in (8,16,28,53):element(direction,'offset',17640)
            m.insert(1 if m.find('attributes') is not None else 0,direction)
        if part is parts[0]:
            for number,word in {0:'Lento',20:'rit.',21:'a tempo',30:'Poco più mosso; cresc.',38:'legatissimo',43:'poco a poco rit.',46:'Tempo I',57:'rit.',58:'a tempo'}.items():
                m=part.find(f"measure[@number='{number}']");direction=ET.Element('direction',placement='above')
                element(element(direction,'direction-type'),'words',word)
                m.insert(1 if m.find('attributes') is not None else 0,direction)
    ET.indent(tree)
    return ET.tostring(tree,encoding='utf-8',xml_declaration=True)


def rebeam_quarters(tree):
    """Bound converted beam groups to each voice and quarter-note beat."""
    from fractions import Fraction
    for part in tree.findall('part'):
        divisions=1
        for measure in part.findall('measure'):
            divisions=int(measure.findtext('attributes/divisions') or divisions)
            cursor=Fraction(0);voices={}
            for item in measure:
                if item.tag in ('backup','forward'):
                    cursor+=Fraction(int(item.findtext('duration')),divisions)*(-1 if item.tag=='backup' else 1)
                if item.tag!='note':continue
                for beam in list(item.findall('beam')):item.remove(beam)
                if item.find('chord') is not None:continue
                grace=item.find('grace') is not None
                key=(item.findtext('voice','1'),grace)
                voices.setdefault(key,[]).append((cursor,item))
                if not grace:cursor+=Fraction(int(item.findtext('duration','0')),divisions)
            for (voice,grace),events in voices.items():
                clusters=[]
                for onset,note in events:
                    eligible=note.findtext('type') in ('eighth','16th','32nd') and note.find('rest') is None
                    beat=onset if grace else onset//1
                    if not eligible:clusters.append((None,[]));continue
                    if not clusters or clusters[-1][0]!=beat:clusters.append((beat,[]))
                    clusters[-1][1].append(note)
                for beat,notes in clusters:
                    if len(notes)<2:continue
                    for index,note in enumerate(notes):
                        pos=next((i for i,n in enumerate(note) if n.tag=='notations'),len(note))
                        beam=ET.Element('beam',number='1');beam.text='begin' if index==0 else 'end' if index==len(notes)-1 else 'continue';note.insert(pos,beam)
                        if note.findtext('type') in ('16th','32nd'):
                            extra=ET.Element('beam',number='2');extra.text='backward hook' if index else 'forward hook';note.insert(pos+1,extra)


def mazurka30_2(source):
    """Paderewski PDF pp.56-57, pickup 0 and printed measures 1-64."""
    tree=ET.parse(source).getroot();parts=tree.findall('part')
    if len(parts)!=2 or any(len(p.findall('measure'))!=65 for p in parts):
        raise ValueError('Unexpected Mazurka source coverage')
    title='Mazurka Op. 30 No. 2 - Paderewski reviewed notes and rhythm'
    tree.find('work/work-title').text=title
    if tree.find('movement-title') is not None:tree.find('movement-title').text=title
    for number in (39,45,47):
        grace=next(n for n in parts[0].find(f"measure[@number='{number}']").findall('note') if n.find('grace') is not None and n.findtext('pitch/step')=='G' and n.findtext('pitch/octave')=='5')
        pitch=grace.find('pitch');alter=pitch.find('alter')
        if alter is None:alter=ET.Element('alter');pitch.insert(1,alter)
        alter.text='1'
        if grace.find('accidental') is not None:grace.find('accidental').text='sharp'
    for number in (29,61):
        measure=parts[1].find(f"measure[@number='{number}']")
        anchor=next(n for n in measure.findall('note') if n.findtext('pitch/step')=='C' and n.findtext('pitch/octave')=='4')
        note=copy.deepcopy(anchor);pitch=note.find('pitch');pitch.find('step').text='G';pitch.find('alter').text='1';pitch.find('octave').text='3'
        for accidental in list(note.findall('accidental')):note.remove(accidental)
        measure.insert(list(measure).index(anchor)+1,note)
    for part in parts:
        for measure in part.findall('measure'):
            for direction in list(measure.findall('direction')):measure.remove(direction)
            for notation in measure.findall('note/notations'):
                for mark in list(notation):
                    if mark.tag not in ('tied','ornaments','fermata','tuplet'):notation.remove(mark)
        for number,level in {0:'p',3:'f',5:'p',7:'f',8:'p',11:'f',13:'p',15:'f',17:'p',25:'p',33:'p',41:'p',49:'p',57:'p'}.items():
            m=part.find(f"measure[@number='{number}']");direction=ET.Element('direction',placement='below')
            element(element(direction,'direction-type'),'dynamics').append(ET.Element(level))
            if number==8:element(direction,'offset',25200)
            m.insert(1 if m.find('attributes') is not None else 0,direction)
        if part is parts[0]:
            for number,word in {0:'Allegretto',19:'poco a poco cresc.',27:'poco a poco cresc.',38:'poco rit.',41:'a tempo',51:'poco a poco cresc.',59:'poco a poco cresc.'}.items():
                m=part.find(f"measure[@number='{number}']");direction=ET.Element('direction',placement='above')
                element(element(direction,'direction-type'),'words',word)
                m.insert(1 if m.find('attributes') is not None else 0,direction)
    rebeam_quarters(tree)
    ET.indent(tree)
    return ET.tostring(tree,encoding='utf-8',xml_declaration=True)


def measure_events(measure,divisions):
    events=[];cursor=Fraction(0);last=cursor
    for item in measure:
        if item.tag in ('backup','forward'):
            cursor+=Fraction(int(item.findtext('duration')),divisions)*(-1 if item.tag=='backup' else 1)
        if item.tag!='note':continue
        chord=item.find('chord') is not None
        duration=Fraction(int(item.findtext('duration','0')),divisions)
        events.append({'onset':last if chord else cursor,'duration':duration,'note':copy.deepcopy(item)})
        if not chord:last=cursor;cursor+=duration
    return events


def rebuild_grand_staff(tree,rows,title,meters,dynamics,words,attribute_changes=None,barlines=None):
    """Serialize reviewed event corrections without quantizing their fractions."""
    from math import lcm
    divisions=lcm(4,*[x.denominator for _,events in rows for e in events for x in (e['onset'],e['duration'])])
    result=copy.deepcopy(tree)
    if result.find('work') is None:element(element(result,'work'),'work-title',title)
    else:result.find('work/work-title').text=title
    if result.find('movement-title') is not None:result.find('movement-title').text=title
    for part in list(result.findall('part')):result.remove(part)
    piano=element(result,'part',id=tree.find('part').get('id'))
    order={tag:i for i,tag in enumerate(('grace','cue','chord','pitch','unpitched','rest','duration','tie','instrument','voice','type','dot','accidental','time-modification','stem','notehead','staff','beam','notations','lyric'))}
    for number,events in rows:
        measure=element(piano,'measure',number=str(number))
        if number==rows[0][0]:
            attrs=copy.deepcopy(tree.find('part/measure/attributes'))
            attrs.find('divisions').text=str(divisions)
            for oldtime in list(attrs.findall('time')):attrs.remove(oldtime)
            measure.append(attrs)
        if number in meters:
            attrs=measure.find('attributes')
            if attrs is None:attrs=element(measure,'attributes')
            time=element(attrs,'time');element(time,'beats',meters[number]);element(time,'beat-type',4)
        for offset,level in dynamics.get(number,[]):
            for staff in (1,2):
                direction=element(measure,'direction',placement='below')
                element(element(element(direction,'direction-type'),'dynamics'),level)
                if offset:element(direction,'offset',int(offset*divisions))
                element(direction,'staff',staff)
        if number in words:
            direction=element(measure,'direction',placement='above')
            element(element(direction,'direction-type'),'words',words[number]);element(direction,'staff',1)
        for offset,attributes in (attribute_changes or {}).get(number,[]):
            if offset:element(element(measure,'forward'),'duration',int(offset*divisions))
            measure.append(copy.deepcopy(attributes))
            if offset:element(element(measure,'backup'),'duration',int(offset*divisions))
        voices={}
        for event in events:voices.setdefault(event['note'].findtext('voice','1'),[]).append(event)
        cursor=Fraction(0)
        for voice,voice_events in voices.items():
            if cursor:element(element(measure,'backup'),'duration',int(cursor*divisions))
            cursor=Fraction(0)
            for event in voice_events:
                note=copy.deepcopy(event['note']);onset=event['onset'];duration=event['duration']
                if note.find('chord') is None:
                    if onset<cursor:raise ValueError(f'Overlapping single voice in {number}: {voice}')
                    if onset>cursor:
                        forward=element(measure,'forward');element(forward,'duration',int((onset-cursor)*divisions));element(forward,'voice',voice)
                    cursor=onset+duration
                if note.find('grace') is None:note.find('duration').text=str(int(duration*divisions))
                for notation in note.findall('notations'):
                    for mark in list(notation):
                        if mark.tag not in ('tied','ornaments','fermata','tuplet'):notation.remove(mark)
                note[:]=sorted(note,key=lambda n:order.get(n.tag,100));measure.append(note)
        if number==rows[-1][0]:element(element(measure,'barline',location='right'),'bar-style','light-heavy')
        for barline in (barlines or {}).get(number,[]):measure.append(copy.deepcopy(barline))
    ET.indent(result)
    return ET.tostring(result,encoding='utf-8',xml_declaration=True)


def nocturne_b49(source):
    """Every bar against Paderewski Minor Works pp.43-45, including 2/4+3/4."""
    tree=ET.parse(source).getroot();part=tree.find('part')
    if len(tree.findall('part'))!=1 or len(part.findall('measure'))!=64:
        raise ValueError('Unexpected B.49 source coverage')
    rows=[];divisions=1
    for original in part.findall('measure'):
        divisions=int(original.findtext('attributes/divisions') or divisions)
        number=int(original.get('number'));events=measure_events(original,divisions)
        if number==32:
            for event in events:
                for mark in list(event['note'].findall('notations/fermata')):
                    event['note'].find('notations').remove(mark)
        # Noctave adds a lead-in to three trills which this scan does not print.
        if number in (5,13,46):
            events=[e for e in events if not (e['note'].find('grace') is not None and e['onset']==2 and e['note'].findtext('staff','1')=='1')]
        if number in (15,48,52):
            run=[e for e in events if e['note'].findtext('staff','1')=='1' and e['note'].find('pitch') is not None]
            if len(run)!=17:raise ValueError('Unexpected B.49 flourish inventory')
            cursor=Fraction(0)
            for index,event in enumerate(run):
                duration=Fraction(1,3) if index<6 else Fraction(1,4) if index<8 else Fraction(1,6)
                event['onset']=cursor;event['duration']=duration;cursor+=duration;note=event['note']
                note.find('type').text='eighth' if index<6 else '16th'
                for old in list(note.findall('time-modification')):note.remove(old)
                for old in list(note.findall('notations/tuplet')):note.find('notations').remove(old)
                if index<6 or index>=8:
                    mod=element(note,'time-modification');element(mod,'actual-notes',3);element(mod,'normal-notes',2)
                    if (index if index<6 else index-8)%3 in (0,2):
                        notation=note.find('notations')
                        if notation is None:notation=element(note,'notations')
                        element(notation,'tuplet',type='start' if (index if index<6 else index-8)%3==0 else 'stop',number='1')
            if cursor!=4:raise ValueError('B.49 flourish duration differs')
        if number==56:
            anchor=next(e for e in events if e['note'].findtext('staff','1')=='1' and e['note'].find('grace') is None)
            for step in ('C','D'):
                note=copy.deepcopy(anchor['note'])
                for tag in ('duration','notations','time-modification','dot','beam','tie'):
                    for child in list(note.findall(tag)):note.remove(child)
                note.insert(0,ET.Element('grace'));note.find('pitch/step').text=step;note.find('pitch/alter').text='1';note.find('type').text='16th'
                for beam in ('1','2'):element(note,'beam','begin' if step=='C' else 'end',number=beam)
                events.insert(0 if step=='C' else 1,{'onset':Fraction(0),'duration':Fraction(0),'note':note})
        if number==32:
            for printed,left,right in ((32,0,2),(33,2,5)):
                sub=[]
                for event in events:
                    if left<=event['onset']<right:
                        clone=copy.deepcopy(event);clone['onset']-=left;sub.append(clone)
                rows.append((printed,sub))
        else:rows.append((number if number<32 else number+1,events))
    dynamics={m:[(Fraction(beat),level)] for m,beat,level in ((1,0,'p'),(3,0,'pp'),(12,3,'p'),(19,0,'f'),(21,0,'pp'),(27,0,'p'),(29,0,'f'),(30,0,'pp'),(34,0,'p'),(46,0,'ppp'),(49,0,'f'),(50,0,'p'),(58,2,'p'),(62,0,'pp'),(64,2,'ppp'))}
    words={1:'Lento con gran espressione',5:'legato; dolce',14:'cresc.',15:'con forza',17:'cresc.',20:'dim.',25:'sotto voce',36:'sempre più dim.',40:'sempre più piano, rallentando',45:'Adagio; morendo',46:'Tempo I',47:'dolce',48:'cresc.',53:'con forza',54:'appassionato',59:'sempre più piano',60:'delicato',61:'delicatissimo',62:'rall.'}
    return rebuild_grand_staff(tree,rows,'Nocturne B.49 - Paderewski reviewed notes and rhythm',{1:4,32:2,33:3,45:4},dynamics,words)


def polonaise40_1(source):
    """Paderewski pp.24-29: 88 bars, rather than the source's written-out repeat."""
    tree=ET.parse(source).getroot();parts=tree.findall('part')
    if len(parts)!=2 or any(len(p.findall('measure'))!=105 for p in parts):
        raise ValueError('Unexpected Military Polonaise source coverage')
    template=copy.deepcopy(tree)
    for part in list(template.findall('part'))[1:]:template.remove(part)
    listing=template.find('part-list')
    for item in list(listing)[1:]:listing.remove(item)
    first=template.find('part/measure/attributes')
    element(first,'staves',2)
    first.find('clef').set('number','1')
    clef=element(first,'clef',number='2');element(clef,'sign','F');element(clef,'line',4)
    rows={};changes={};barlines={}
    crossed={2,4,9,10,18,20,82,84,89,90,98,100}
    for staff,part in enumerate(parts,1):
        divisions=1
        for original in part.findall('measure'):
            divisions=int(original.findtext('attributes/divisions') or divisions)
            source_number=int(original.get('number'))
            if source_number==0 or 41<=source_number<=56:continue
            number=source_number if source_number<=40 else source_number-16
            events=measure_events(original,divisions)
            events=[e for e in events if not (
                staff==2 and source_number in (1,17,81,97) and e['onset']==0
                and e['note'].findtext('pitch/step')=='E' and e['note'].findtext('pitch/octave')=='2')]
            events=[e for e in events if not (
                staff==1 and source_number==3 and e['onset']==0
                and e['note'].findtext('pitch/step')=='A' and e['note'].findtext('pitch/octave')=='4')]
            if staff==1 and source_number in (33,73):
                events=[e for e in events if not(e['onset']==1 and e['note'].find('rest') is not None)]
                for e in events:
                    if e['onset']==0:e['duration']=Fraction(2);e['note'].find('type').text='half'
            for e in events:
                note=e['note'];voice=note.find('voice')
                if voice is None:voice=element(note,'voice','1')
                voice.text=str(int(voice.text)+(0 if staff==1 else 2))
                display=staff
                if staff==1 and source_number in crossed and e['onset']>=Fraction(3,2):
                    pitch=note.find('pitch')
                    if pitch is not None and (int(pitch.findtext('octave'))<=3 or (pitch.findtext('step')=='C' and pitch.findtext('octave')=='4')):
                        display=2
                if staff==1 and (source_number in (57,59,61) or source_number==62 and e['onset']>=2):display=2
                target=note.find('staff')
                if target is None:target=element(note,'staff')
                target.text=str(display)
            rows.setdefault(number,[]).extend(events)
            cursor=Fraction(0)
            for item in original:
                if item.tag in ('backup','forward'):cursor+=Fraction(int(item.findtext('duration')),divisions)*(-1 if item.tag=='backup' else 1)
                elif item.tag=='note' and item.find('chord') is None:cursor+=Fraction(int(item.findtext('duration','0')),divisions)
                elif item.tag=='attributes' and source_number!=1:
                    attrs=ET.Element('attributes')
                    if staff==1:
                        for key in item.findall('key'):
                            for staff_number in (1,2):
                                k=copy.deepcopy(key);k.set('number',str(staff_number));attrs.append(k)
                    for original_clef in item.findall('clef'):
                        c=copy.deepcopy(original_clef);c.set('number',str(staff));attrs.append(c)
                    if len(attrs):changes.setdefault(number,[]).append((cursor,attrs))
                elif item.tag=='barline' and staff==1:barlines.setdefault(number,[]).append(copy.deepcopy(item))
    # These clefs are printed in the upper staff around the descending trill run.
    for number,offset,sign,line in ((48,Fraction(1,2),'F',4),(49,Fraction(0),'G',2)):
        attrs=ET.Element('attributes');c=element(attrs,'clef',number='1');element(c,'sign',sign);element(c,'line',line)
        changes.setdefault(number,[]).append((offset,attrs))
    # The lower staff returns to bass after the canonical repeat, not after
    # the discarded written-out second pass in the first-edition encoding.
    attrs=ET.Element('attributes');c=element(attrs,'clef',number='2');element(c,'sign','F');element(c,'line',4)
    changes.setdefault(41,[]).insert(0,(Fraction(0),attrs))
    for number,location,direction in ((25,'left','forward'),(40,'right','backward')):
        b=ET.Element('barline',location=location);element(b,'repeat',direction=direction);barlines.setdefault(number,[]).append(b)
    dynamics={m:[(Fraction(0),level)] for m,level in {1:'f',13:'ff',17:'f',25:'ff',33:'fff',41:'f',49:'fff',57:'fff',65:'f',77:'ff',81:'f'}.items()}
    words={1:'Allegro con brio',25:'energico; 2a Volta: D4 grace',37:'cresc.',48:'rit. e cresc.',49:'a tempo',61:'cresc.'}
    result=ET.fromstring(rebuild_grand_staff(template,sorted(rows.items()),'Polonaise Op. 40 No. 1 - Paderewski reviewed notes and rhythm',{1:3},dynamics,words,changes,barlines))
    rebeam_quarters(result)
    ET.indent(result)
    return ET.tostring(result,encoding='utf-8',xml_declaration=True)


def two_part_grand_staff(source,measure_numbers,transform):
    tree=ET.parse(source).getroot();parts=tree.findall('part')
    if len(parts)!=2:raise ValueError('Expected separate upper/lower source parts')
    template=copy.deepcopy(tree)
    for part in list(template.findall('part'))[1:]:template.remove(part)
    listing=template.find('part-list')
    for item in list(listing)[1:]:listing.remove(item)
    first=template.find('part/measure/attributes');element(first,'staves',2)
    first.find('clef').set('number','1')
    c=element(first,'clef',number='2');element(c,'sign','F');element(c,'line',4)
    rows={};changes={};barlines={}
    for staff,part in enumerate(parts,1):
        divisions=1
        for ordinal,original in enumerate(part.findall('measure'),1):
            divisions=int(original.findtext('attributes/divisions') or divisions)
            source_number=int(original.get('number'));number=measure_numbers.get((source_number,ordinal),measure_numbers.get(source_number))
            if number is None:continue
            events=measure_events(original,divisions)
            for e in events:
                note=e['note'];voice=note.find('voice')
                if voice is None:voice=element(note,'voice','1')
                voice.text=str(int(voice.text)+(0 if staff==1 else 3))
                target=note.find('staff')
                if target is None:target=element(note,'staff')
                target.text=str(staff)
            transform(staff,source_number,events)
            rows.setdefault(number,[]).extend(events)
            cursor=Fraction(0)
            for item in original:
                if item.tag in ('backup','forward'):cursor+=Fraction(int(item.findtext('duration')),divisions)*(-1 if item.tag=='backup' else 1)
                elif item.tag=='note' and item.find('chord') is None:cursor+=Fraction(int(item.findtext('duration','0')),divisions)
                elif item.tag=='attributes' and ordinal!=1:
                    attrs=ET.Element('attributes')
                    if staff==1:
                        for key in item.findall('key'):
                            for n in (1,2):
                                k=copy.deepcopy(key);k.set('number',str(n));attrs.append(k)
                    for original_clef in item.findall('clef'):
                        c=copy.deepcopy(original_clef);c.set('number',str(staff));attrs.append(c)
                    if len(attrs):changes.setdefault(number,[]).append((cursor,attrs))
                elif item.tag=='barline' and staff==1:barlines.setdefault(number,[]).append(copy.deepcopy(item))
    return template,sorted(rows.items()),changes,barlines


def add_tie(note,kind):
    if not any(t.get('type')==kind for t in note.findall('tie')):element(note,'tie',type=kind)
    notation=note.find('notations')
    if notation is None:notation=element(note,'notations')
    if not any(t.get('type')==kind for t in notation.findall('tied')):element(notation,'tied',type=kind)
    # A continuation ends the preceding tie before beginning the next one.
    # Start-before-stop can make engravers construct a self-referential tie.
    for parent,tag in ((note,'tie'),(notation,'tied')):
        marks=parent.findall(tag)
        for mark in marks:parent.remove(mark)
        for mark in sorted(marks,key=lambda t:t.get('type')!='stop'):parent.append(mark)


def polonaise40_2(source):
    """Paderewski pp.30-36: 117 printed bars, with the first repeat folded."""
    numbers={n:n if n<=18 else n-16 for n in range(1,134) if not 19<=n<=34}
    def correct(staff,number,events):
        for e in events:
            note=e['note'];pitch=note.find('pitch')
            step=note.findtext('pitch/step');octave=note.findtext('pitch/octave')
            if staff==1:
                if (number==35 and e['onset']==0 or number==51 and e['onset']==0 and note.findtext('voice')=='1'
                    or number==52 and e['onset']==Fraction(11,4) or 53<=number<=55 or number==56 and e['onset']==0):
                    note.find('staff').text='2'
                if number==84 and e['onset']==0 and step=='D' and octave=='5':
                    pitch.find('step').text='E';pitch.find('alter').text='-1'
                if number==82 and e['onset']==1 and step=='A' and octave=='4':
                    e['duration']=Fraction(3,2);element(note,'dot')
                if number==96 and e['onset']==Fraction(9,4) and step=='F' and octave=='4':
                    pitch.find('step').text='E';element(pitch,'alter',0)
                if number==51 and e['onset']==2 and step=='B' and octave=='4':
                    e['duration']=Fraction(1);note.find('type').text='quarter';add_tie(note,'start')
                if number==51 and e['onset']==Fraction(5,2) and note.findtext('voice')=='1':note.find('voice').text='3'
                if number==52 and e['onset']==0 and step=='B' and octave=='4':add_tie(note,'stop')
                if number==97 and e['onset']==2 and step=='C' and octave=='5':add_tie(note,'start')
                if number==98 and e['onset']==0 and step=='C' and octave=='5':add_tie(note,'stop')
                if number in (132,133) and step=='G' and octave=='4':add_tie(note,'start' if number==132 else 'stop')
                if number==98:
                    for fermata in note.findall('notations/fermata'):fermata.set('type','upright')
            if number==133 and note.find('chord') is None and pitch is not None:
                notation=note.find('notations')
                if notation is None:notation=element(note,'notations')
                element(notation,'fermata')
        if staff==1 and number==82:
            events[:]=[e for e in events if not(e['onset']==2 and e['note'].findtext('voice')=='2' and e['note'].find('rest') is not None)]
    template,rows,changes,barlines=two_part_grand_staff(source,numbers,correct)
    if len(rows)!=117:raise ValueError('Unexpected C minor Polonaise coverage')
    for offset,attrs in changes.get(101,[]):
        for key in attrs.findall('key'):key.find('fifths').text='-3'
    for number,location,direction in ((3,'left','forward'),(18,'right','backward')):
        barline=ET.Element('barline',location=location);element(barline,'repeat',direction=direction);barlines.setdefault(number,[]).append(barline)
    dynamics={m:[(Fraction(0),level)] for m,level in {1:'p',19:'ff',20:'p',21:'ff',22:'p',40:'f',56:'p',58:'pp',63:'p',71:'ff',75:'ff',83:'p',85:'pp',90:'p',101:'ff',116:'fff'}.items()}
    for m in (71,75):dynamics[m].append((Fraction(3,2),'p'))
    words={1:'Allegro maestoso',3:'sotto voce; legato; 2a volta: forte',12:'cresc.',17:'dim.',23:'cresc.',30:'dim.',39:'cresc.',49:'cresc.',54:'dim.',56:'sostenuto; espressivo',77:'cresc.',79:'dim.',81:'slentando',83:'espressivo',97:'cresc.',99:'cresc.',110:'cresc.'}
    result=ET.fromstring(rebuild_grand_staff(template,rows,'Polonaise Op. 40 No. 2 - Paderewski reviewed notes and rhythm',{1:3},dynamics,words,changes,barlines))
    rebeam_quarters(result);ET.indent(result)
    return ET.tostring(result,encoding='utf-8',xml_declaration=True)


def waltz64_2(source):
    """Paderewski pp.59-64; pickup 0, 192 full bars, no inserted rest bar."""
    original=ET.parse(source).getroot()
    if any(len(p.findall('measure'))!=194 for p in original.findall('part')):raise ValueError('Unexpected Waltz source coverage')
    added=original.findall('part')[0].findall('measure')[65].find('note')
    if added.findtext('pitch/step')!='F':raise ValueError('Unexpected Più lento pickup')
    numbers={n:n for n in range(193)};numbers[(0,66)]=None
    def correct(staff,number,events):
        if staff!=1:return
        if number==64:
            events[:]=[e for e in events if e['onset']!=2]
            note=copy.deepcopy(added)
            if note.find('voice') is None:element(note,'voice','1')
            else:note.find('voice').text='1'
            if note.find('staff') is None:element(note,'staff',1)
            events.append({'onset':Fraction(2),'duration':Fraction(1),'note':note})
        for e in events:
            note=e['note']
            if number in (30,80,158):
                for mark in note.findall('notations/ornaments/mordent'):mark.tag='inverted-mordent'
            if number==84:
                note.find('type').text='eighth'
                for tag in ('dot','time-modification'):
                    for old in list(note.findall(tag)):note.remove(old)
                for old in list(note.findall('notations/tuplet')):note.find('notations').remove(old)
                mod=element(note,'time-modification');element(mod,'actual-notes',8);element(mod,'normal-notes',6)
                if e is events[0] or e is events[-1]:
                    notation=note.find('notations')
                    if notation is None:notation=element(note,'notations')
                    element(notation,'tuplet',type='start' if e is events[0] else 'stop',number='1')
            if number in (27,29,155,157) and e['onset']==2 and note.findtext('voice')=='1':add_tie(note,'start')
            if number in (28,30,156,158) and e['onset']==0 and note.findtext('voice')=='1':add_tie(note,'stop')
            if number==93 and e['onset']==1:
                e['duration']=Fraction(3,2);element(note,'dot')
            if number==93 and e['onset']==2:
                e['onset']=Fraction(5,2);e['duration']=Fraction(1,2);note.find('type').text='eighth'
        if number in (159,160):
            anchor=next(e for e in events if e['note'].find('pitch') is not None)
            note=copy.deepcopy(anchor['note'])
            for tag in ('chord','beam','notations','tie','dot','time-modification','accidental'):
                for old in list(note.findall(tag)):note.remove(old)
            pitch=note.find('pitch');pitch.find('step').text='G';pitch.find('octave').text='4'
            alter=pitch.find('alter')
            if alter is None:alter=element(pitch,'alter')
            alter.text='1';note.find('voice').text='3';note.find('type').text='quarter' if number==159 else 'half'
            add_tie(note,'start' if number==159 else 'stop')
            events.append({'onset':Fraction(2 if number==159 else 0),'duration':Fraction(1 if number==159 else 2),'note':note})
    template,rows,changes,barlines=two_part_grand_staff(source,numbers,correct)
    if len(rows)!=193:raise ValueError('Waltz printed measure inventory changed')
    for i,(offset,attrs) in enumerate(changes.get(64,[])):
        for key in attrs.findall('key'):key.find('fifths').text='-5'
        changes[64][i]=(Fraction(2),attrs)
    dynamics={m:[(Fraction(0),level)] for m,level in {49:'pp',65:'mf',113:'pp',177:'pp'}.items()}
    dynamics[81]=[(Fraction(2),'p')]
    words={0:'Tempo giusto',64:'Più lento',93:'poco riten.',97:'Più mosso',129:'Tempo I',161:'Più mosso'}
    result=ET.fromstring(rebuild_grand_staff(template,rows,'Waltz Op. 64 No. 2 - Paderewski reviewed notes and rhythm',{0:3},dynamics,words,changes,barlines))
    rebeam_quarters(result);ET.indent(result)
    return ET.tostring(result,encoding='utf-8',xml_declaration=True)


def etude10_12(source):
    """Paderewski pp.58-62: recover 84 bars and the lost concluding voices."""
    def pitch(note,step,alter,octave=None):
        p=note.find('pitch');p.find('step').text=step
        a=p.find('alter')
        if a is None:a=element(p,'alter')
        a.text=str(alter)
        if octave is not None:p.find('octave').text=str(octave)
        for old in list(note.findall('accidental')):note.remove(old)
    def correct(staff,number,events):
        for e in events:
            n=e['note'];s=n.findtext('pitch/step');o=n.findtext('pitch/octave');at=e['onset']
            if staff==1 and number==80 and n.findtext('voice')=='2':e['onset']+=4
            if n.find('pitch') is None:continue
            if staff==1:
                fixes={(31,Fraction(3),'C','4'):('C',1),(31,Fraction(3),'F','4'):('F',1),
                       (46,Fraction(3,4),'F','4'):('G',0),
                       (55,Fraction(10,3),'A','5'):('A',-1),(55,Fraction(10,3),'A','4'):('A',-1),
                       (80,Fraction(19,4),'F','4'):('G',0),
                       (80,Fraction(1),'E','6'):('E',0),(80,Fraction(3),'E','5'):('E',0),
                       (80,Fraction(15,2),'D','3'):('D',-1)}
                if (number,at,s,o) in fixes:pitch(n,*fixes[number,at,s,o])
                if number in (17,57) and at==Fraction(15,4) and s=='E' and o in ('4','5'):add_tie(n,'start')
                if number in (18,58) and at==0 and s=='E' and o in ('4','5'):add_tie(n,'stop')
                if number in (22,62) and at in (0,2) and (s=='C' and o=='5' or number==62 and s=='E' and o=='5'):
                    add_tie(n,'start' if at==0 else 'stop')
                if number in (77,78) and at==0 and s=='C' and o=='5':add_tie(n,'start' if number==77 else 'stop')
                if number in (6,46) and at>=2 or number in (7,47) or number in (8,48) and (at<Fraction(1,2) or at>=2) or number in (9,49) and at==0:
                    n.find('staff').text='2'
            else:
                fixes={(12,Fraction(1,4),'F','2'):('G',0),
                       (30,Fraction(7,4),'D','3'):('D',1),(30,Fraction(3),'D','3'):('D',1),(30,Fraction(15,4),'F','2'):('F',1),
                       (31,Fraction(9,4),'F','3'):('F',1),(31,Fraction(3),'F','3'):('F',1),(31,Fraction(15,4),'F','3'):('F',1),
                       (31,Fraction(13,4),'A','3'):('A',0),(32,Fraction(11,4),'G','2'):('G',1),
                       (29,Fraction(13,4),'B','3'):('A',1),(38,Fraction(5,4),'D','3'):('D',-1),
                       (55,Fraction(1,4),'B','2'):('B',0),(55,Fraction(7,4),'B','2'):('B',0),(55,Fraction(3),'D','4'):('D',-1),
                       (81,Fraction(1),'E','5'):('E',0),(81,Fraction(3),'E','4'):('E',0),
                       (81,Fraction(7,2),'D','4'):('D',-1),(82,Fraction(7,2),'D','2'):('D',-1)}
                if (number,at,s,o) in fixes:pitch(n,*fixes[number,at,s,o])
                if number in (1,3,41,43) and Fraction(1,2)<=at<2:n.find('staff').text='1'
    template,rows,changes,barlines=two_part_grand_staff(source,{n:n for n in range(1,85)},correct)
    bars=dict(rows)
    def extra(number,step,alter,octave,onset,duration,voice,kind,chord=False):
        n=ET.Element('note')
        if chord:element(n,'chord')
        p=element(n,'pitch');element(p,'step',step);element(p,'alter',alter);element(p,'octave',octave)
        element(n,'duration',1);element(n,'voice',voice);element(n,'type',kind);element(n,'staff',1)
        bars[number].append({'onset':Fraction(onset),'duration':Fraction(duration),'note':n})
        return n
    # The converter placed four concluding bars simultaneously in bar 80.
    for e in list(bars[80]):
        if e['note'].findtext('voice')=='2':
            bars[80].remove(e);number=80+int(e['onset']//4);e['onset']%=4
            e['note'].find('voice').text='1'
            if number==82 and e['onset']>=2 or number>=83:e['note'].find('staff').text='2'
            bars[number].append(e)
    for m in (70,71):bars[m]=[e for e in bars[m] if e['note'].findtext('voice')!='2']
    extra(70,'D',0,5,0,4,2,'whole')
    for at in (0,2):extra(70,'G',0,4,at,2,3,'half')
    for m,tones in ((71,[('C',0,5),('G',0,4)]),(72,[('A',-1,4),('F',0,4)])):
        for i,(s,a,o) in enumerate(tones):extra(m,s,a,o,0,4,2,'whole',i>0)
    extra(80,'A',-1,4,0,4,2,'whole')
    for at,s in ((0,'G'),(2,'F')):
        extra(80,s,0,4,at,2,3,'half')
        add_tie(extra(80,'C',0,4,at,2,3,'half',True),'start' if at==0 else 'stop')
    for m,at,sign,line in ((81,Fraction(1,2),'G',2),(82,Fraction(0),'F',4)):
        attrs=ET.Element('attributes');clef=element(attrs,'clef',number='2');element(clef,'sign',sign);element(clef,'line',line)
        changes.setdefault(m,[]).append((at,attrs))
    if len(bars)!=84:raise ValueError('Etude must contain all 84 printed bars')
    dynamics={m:[(Fraction(0),v)] for m,v in {1:'f',3:'f',29:'f',37:'f',41:'ff',43:'f',45:'ff',63:'f',65:'ff',67:'f',69:'p',71:'p',78:'pp',80:'pp',81:'p',83:'fff'}.items()}
    dynamics[4]=[(Fraction(3),'f')]
    for m,v in {10:'f',11:'p',12:'f',20:'p',50:'f',51:'p',53:'p',61:'p'}.items():dynamics[m]=[(Fraction(11,4),v)]
    for m in (52,60,62):dynamics[m]=[(Fraction(7,3),'f')]
    dynamics[63].append((Fraction(11,4),'p'));dynamics[81].append((Fraction(1,2),'ff'))
    words={1:'Allegro con fuoco',2:'energico',5:'sf; con fuoco',10:'appassionato',14:'sf; ten.',15:'sf; con forza',20:'sotto voce',23:'sf',24:'sf',25:'cresc.',26:'stretto',27:'sf',34:'sf; cresc.',35:'sf',54:'sf',57:'cresc.',64:'sf; cresc.',69:'sfp',73:'cresc.',75:'smorz.',77:'sotto voce',80:'poco rallentando',81:'a tempo; ed appassionato'}
    result=ET.fromstring(rebuild_grand_staff(template,sorted(bars.items()),'Etude Op. 10 No. 12 - Paderewski reviewed notes and rhythm',{1:4},dynamics,words,changes,barlines))
    rebeam_quarters(result);ET.indent(result)
    return ET.tostring(result,encoding='utf-8',xml_declaration=True)


BUILDERS={'p28-4':prelude28_4,'m68-3':mazurka68_3,'m68-2':mazurka68_2,'m30-2':mazurka30_2,'n-b49':nocturne_b49,'p40-1':polonaise40_1,'p40-2':polonaise40_2,'w64-2':waltz64_2,'e10-12':etude10_12}


def build(data_dir,output,piece):
    review=json.loads((REVIEW_ROOT/(piece+'.json')).read_text())
    if review['status']!='model-reviewed' or review.get('open_issues'):
        raise ValueError('Reference has no complete scan audit')
    start=review.get('first_printed_measure',0)
    expected=list(range(start,start+review['measure_count']))
    if [r['printed_measure'] for r in review['coverage']]!=expected or any(r['staves']!=[1,2] for r in review['coverage']):
        raise ValueError('Incomplete measure/staff coverage')
    source=data_dir/'references'/review['original_musicxml']['filename']
    pdf=data_dir/'scores'/review['scan']['filename']
    if digest(source)!=review['original_musicxml']['sha256'] or digest(pdf)!=review['scan']['sha256']:
        raise ValueError('Pinned source or scan changed; audit required')
    output.mkdir(parents=True,exist_ok=True)
    path=output/(piece+'-paderewski-reviewed.musicxml')
    path.write_bytes(BUILDERS[piece](source))
    notes=parse_musicxml(path)
    if len(notes)!=review['expected_attacks'] or len({n['measure'] for n in notes})!=review['measure_count']:
        raise ValueError('Reviewed attack or measure inventory differs')
    evidence={**review,'derived_musicxml_sha256':digest(path),'notes':notes}
    (output/(piece+'-review.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    return path,evidence


def install(data_dir,path,evidence):
    """One additive transaction; no migration, seed, recording or source edits."""
    if evidence.get('status')!='model-reviewed' or evidence.get('open_issues'):
        raise ValueError('Only completed model reviews can be installed')
    if digest(path)!=evidence['derived_musicxml_sha256']:
        raise ValueError('Derived score changed after review')
    ident='scan-reviewed-'+evidence['piece_id']+'-'+evidence['derived_musicxml_sha256'][:12]
    target=data_dir/'references'/(ident+'.musicxml')
    if target.exists() and digest(target)!=evidence['derived_musicxml_sha256']:
        raise ValueError('Derived file collision; original preserved')
    db=sqlite3.connect((data_dir/'studio.sqlite3').as_uri()+'?mode=rw',uri=True)
    try:
        if db.execute('PRAGMA user_version').fetchone()[0] not in (6, 7):
            raise ValueError('Unsupported installed schema')
        if not db.execute('SELECT id FROM pieces WHERE id=?',(evidence['piece_id'],)).fetchone():
            raise ValueError('Piece missing from Library')
        existing=db.execute('SELECT notes FROM symbolic_scores WHERE id=?',(ident,)).fetchone()
        if existing and existing[0]!=json.dumps(evidence['notes']):
            raise ValueError('Installed derived reference has edits; preserve them')
        if not target.exists():
            temporary=target.with_suffix('.tmp');temporary.write_bytes(path.read_bytes());temporary.replace(target)
        review_target=target.with_suffix('.review.json')
        temporary_review=review_target.with_suffix('.tmp')
        metadata={k:v for k,v in evidence.items() if k!='notes'}
        if evidence.get('measure_layout_changed'):
            previous=json.loads(review_target.read_text()) if review_target.exists() else {}
            if previous and previous.get('derived_musicxml_sha256')!=evidence['derived_musicxml_sha256']:
                raise ValueError('Installed review has edits; preserve it')
            metadata={**previous,**metadata}
            metadata['legacy_page_map']=previous.get('legacy_page_map',[{'measure':m,'pdf_page':p} for m,p in db.execute('SELECT measure,pdf_page FROM page_maps WHERE piece_id=? ORDER BY measure',(evidence['piece_id'],))])
        temporary_review.write_text(json.dumps(metadata,indent=2)+'\n')
        temporary_review.replace(review_target)
        if existing:return ident
        with db:
            db.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                       (ident,evidence['piece_id'],target.name,evidence['provenance'],evidence['licence'],
                        evidence['edition'],'verified',json.dumps(evidence['notes']),datetime.now(timezone.utc).isoformat()))
        return ident
    finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'output/verified-counterparts')
    parser.add_argument('--piece',choices=BUILDERS,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();path,evidence=build(args.data_dir,args.output,args.piece)
    print(path)
    if args.apply:print('Installed',install(args.data_dir,path,evidence))
