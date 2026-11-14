"""Export an explicitly unmeasured pitch/attack study, separate from source scores.

This engraving shows each staff's required attack order and grace/ornament marks.
It deliberately does not invent notated sustain lengths or hand coordination.
The edition-bound JSON remains the authority for matching and nominal positions.
"""
from fractions import Fraction
import xml.etree.ElementTree as ET


def attack_score_xml(bundle):
    provisional = bundle.get('reference_status', 'model-reviewed') not in ('model-reviewed', 'human-reviewed')
    def element(parent, tag, text=None, **attributes):
        child = ET.SubElement(parent, tag, attributes)
        if text is not None:
            child.text = str(text)
        return child
    root = ET.Element('score-partwise', version='4.0')
    work = element(root,'work')
    element(work,'work-title', bundle['title']+(' — PROVISIONAL' if provisional else '')+' — unmeasured pitch/attack study')
    identification = element(root,'identification')
    element(identification,'creator','Fryderyk Chopin',type='composer')
    element(identification,'rights',bundle['source']['licence'])
    parts = element(root,'part-list')
    info = element(parts,'score-part',id='P1')
    element(info,'part-name','Piano · ordered attacks')
    part = element(root,'part',id='P1')
    for index, source in enumerate(bundle['measures']):
        measure = element(part,'measure',number=str(source['number']))
        attributes = element(measure,'attributes')
        element(attributes,'divisions',64)
        key = element(attributes,'key')
        element(key,'fifths',source.get('key_fifths',bundle.get('key_fifths',0)))
        if index==0:
            time = element(attributes,'time')
            element(time,'senza-misura')
            element(attributes,'staves',2)
            for staff,sign,line in [(1,'G',2),(2,'F',4)]:
                clef=element(attributes,'clef',number=str(staff))
                element(clef,'sign',sign)
                element(clef,'line',line)
            direction=element(measure,'direction',placement='above')
            words=element(direction,'direction-type')
            element(words,'words',('PROVISIONAL digital draft; full note review pending. No automatic pitch verdict. ' if provisional else '')+
                    'Unmeasured ordered attacks. Printed grace notes required; ornament repetitions flexible. Consult Paderewski for rhythm, sustain, fingering and expression.')
        cursors=[]
        for staff in (1,2):
            if staff==2 and cursors[0]:
                backup=element(measure,'backup')
                element(backup,'duration',cursors[0])
            cursor=0
            graces={Fraction(g['attack_beat']):g for g in source.get('grace_notes',[])
                    if g.get('policy')=='required' and g['staff']==staff}
            optional=[g for g in source.get('grace_notes',[]) if g['policy']=='optional-editorial' and g['staff']==staff]
            key_changes=list(source.get('key_changes',[]))
            for gi,((position,pitches),spellings) in enumerate(zip(source['staves'][staff-1],source['spellings'][staff-1])):
                position=Fraction(position)
                for change in list(key_changes):
                    if Fraction(change['beat'])<=position:
                        attrs=element(measure,'attributes')
                        key=element(attrs,'key',number=str(staff))
                        element(key,'fifths',change['fifths'])
                        key_changes.remove(change)
                if gi==0:
                    for grace in optional:
                        for note in grace['spellings']:
                            n=element(measure,'note')
                            element(n,'grace',slash='yes')
                            p=element(n,'pitch')
                            for tag in ('step','alter','octave'):element(p,tag,note[tag])
                            element(n,'voice',staff)
                            element(n,'type','eighth')
                            element(n,'notehead','normal',parentheses='yes')
                            element(n,'staff',staff)
                grace=position in graces
                ornaments=[o for o in bundle.get('ornaments',[]) if o['measure']==source['number'] and o['staff']==staff
                           and Fraction(o.get('notation_beat',o.get('beat',3)))==position and o.get('kind') in ('trill','short-trill')]
                for ni,note in enumerate(spellings):
                    n=element(measure,'note')
                    if grace:element(n,'grace',slash='yes')
                    if ni:element(n,'chord')
                    p=element(n,'pitch')
                    for tag in ('step','alter','octave'):element(p,tag,note[tag])
                    if not grace:element(n,'duration',64)
                    element(n,'voice',staff)
                    element(n,'type','eighth' if grace else 'quarter')
                    element(n,'staff',staff)
                    if ni==0 and ornaments:
                        notation=element(n,'notations')
                        marks=element(notation,'ornaments')
                        for ornament in ornaments:
                            element(marks,'trill-mark' if ornament['kind']=='trill' else 'inverted-mordent')
                if not grace:cursor+=64
            if not source['staves'][staff-1]:
                n=element(measure,'note')
                element(n,'rest',measure='yes')
                element(n,'duration',64)
                element(n,'voice',staff)
                element(n,'type','quarter')
                element(n,'staff',staff)
                cursor=64
            cursors.append(cursor)
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n'
