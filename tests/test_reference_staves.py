from chopin.symbolic import annotate_reference_staves, parse_musicxml


def score_xml(parts):
    return '<score-partwise version="4.0"><part-list>'+''.join(f'<score-part id="P{i}"><part-name>Piano</part-name></score-part>' for i in range(len(parts)))+'</part-list>'+''.join(f'<part id="P{i}">{content}</part>' for i,content in enumerate(parts))+'</score-partwise>'


def part(sign, octave):
    return f'<measure number="1"><attributes><divisions>1</divisions><clef><sign>{sign}</sign><line>{4 if sign=="F" else 2}</line></clef></attributes><note><pitch><step>C</step><octave>{octave}</octave></pitch><duration>1</duration><type>quarter</type><staff>1</staff></note></measure>'


def test_split_parts_use_reference_clefs_even_when_bass_note_is_high(tmp_path):
    path=tmp_path/'piano.musicxml'
    path.write_text(score_xml([part('G',3),part('F',5)]))
    notes=parse_musicxml(path)
    treble=next(n for n in notes if n['part']==0)
    bass=next(n for n in notes if n['part']==1)
    assert treble['staff']==bass['staff']==1
    assert treble['display_staff']==1 and bass['display_staff']==2
    assert bass['clef_sign']=='F' and bass['staff_source']=='reference_clef'


def test_source_key_changes_and_enharmonic_spelling_enrich_old_references(tmp_path):
    from chopin.symbolic import annotate_reference_rhythm
    path=tmp_path/'keys.musicxml'
    path.write_text(score_xml(['''<measure number="1"><attributes><divisions>1</divisions><key><fifths>-4</fifths></key></attributes>
      <note><pitch><step>C</step><alter>-1</alter><octave>5</octave></pitch><duration>1</duration></note>
      <note><pitch><step>E</step><alter>0</alter><octave>5</octave></pitch><duration>1</duration></note></measure>
      <measure number="2"><attributes><key><fifths>2</fifths></key></attributes>
      <note><pitch><step>F</step><alter>1</alter><octave>5</octave></pitch><duration>1</duration></note></measure>''']))
    original=path.read_bytes()
    notes=parse_musicxml(path)
    assert [n['key_fifths'] for n in notes]==[-4,-4,2]
    assert notes[0]['pitch']==71 and notes[0]['spelling']==dict(step='C',alter=-1,octave=5)
    assert notes[1]['spelling']==dict(step='E',alter=0,octave=5)
    old=[{k:v for k,v in n.items() if k not in ('spelling','key_fifths')} for n in notes]
    enriched=annotate_reference_rhythm(old,path)
    assert enriched==notes
    assert 'spelling' not in old[0] and path.read_bytes()==original
    old[0]['spelling']=dict(step='B',alter=0,octave=4)
    assert annotate_reference_rhythm(old,path)[0]['spelling']==old[0]['spelling']
    old[1]['pitch']=75  # A corrected pitch must not inherit stale E-natural spelling.
    assert 'spelling' not in annotate_reference_rhythm(old,path)[1]


def test_grand_staff_keeps_reference_number_despite_clef_change(tmp_path):
    path=tmp_path/'grand.musicxml'
    path.write_text(score_xml(['<measure number="1"><attributes><staves>2</staves><clef number="1"><sign>F</sign></clef><clef number="2"><sign>G</sign></clef></attributes></measure>']))
    notes=[dict(pitch=48,part=0,staff=1),dict(pitch=84,part=0,staff=2)]
    mapped=annotate_reference_staves(notes,path)
    assert [n['display_staff'] for n in mapped]==[1,2]
    assert all(n['staff_source']=='reference_staff' for n in mapped)
    assert all('display_staff' not in n for n in notes)


def test_split_parts_with_same_clef_keep_source_order(tmp_path):
    path=tmp_path/'same-clefs.musicxml';path.write_text(score_xml([part('G',4),part('G',5)]))
    notes=[dict(pitch=60,part=0,staff=1),dict(pitch=72,part=1,staff=1)]
    mapped=annotate_reference_staves(notes,path)
    assert [n['display_staff'] for n in mapped]==[1,2]
    assert all(n['staff_source']=='reference_part_order' for n in mapped)


def test_old_reference_without_xml_records_inferred_split_parts(tmp_path):
    mapped=annotate_reference_staves([dict(pitch=48,part=1,staff=1),dict(pitch=72,part=0,staff=1)],tmp_path/'missing.musicxml')
    assert [n['display_staff'] for n in mapped]==[2,1]
    assert all(n['staff_source']=='part_register_inferred' for n in mapped)


def test_reference_beams_and_compound_meter_are_saved_and_enrich_old_notes(tmp_path):
    from chopin.symbolic import annotate_reference_rhythm
    path=tmp_path/'beams.musicxml'
    content='<measure number="1"><attributes><divisions>2</divisions><time><beats>6</beats><beat-type>8</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'
    for step,beam in [('C','begin'),('D','continue'),('E','end'),('F',None)]:
        content+=f'<note><pitch><step>{step}</step><octave>4</octave></pitch><duration>1</duration><type>eighth</type>'+ (f'<beam number="1">{beam}</beam>' if beam else '')+'</note>'
    content+='</measure>'
    path.write_text(score_xml([content]))
    notes=parse_musicxml(path)
    assert len({n['beam_group'] for n in notes[:3]})==1
    assert notes[0]['beam_group'] is not None and notes[3]['beam_group'] is None
    assert all(n['beaming_source']=='reference' and n['beat_group_size']==1.5 for n in notes)
    assert all(n['measure_start']==notes[0]['onset'] for n in notes)
    old=[{k:v for k,v in n.items() if k not in ('beam_group','beaming_source','beat_group_size','measure_start')} for n in notes]
    enriched=annotate_reference_rhythm(old,path)
    assert [n['beam_group'] for n in enriched]==[n['beam_group'] for n in notes]
    old[0]['pitch']=99
    corrected=annotate_reference_rhythm(old,path)
    assert corrected[0]['pitch']==99 and 'beam_group' not in corrected[0]
