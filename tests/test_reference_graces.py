from chopin.symbolic import parse_musicxml
from chopin.performance import groups


def test_import_keeps_ordered_grace_attacks_and_turn_marking(tmp_path):
    path=tmp_path/'graces.musicxml'
    path.write_text('''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Piano</part-name></score-part></part-list>
<part id="P"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
<note><grace slash="yes"/><pitch><step>B</step><octave>4</octave></pitch><type>eighth</type></note>
<note><grace slash="yes"/><pitch><step>C</step><octave>5</octave></pitch><type>eighth</type></note>
<note><pitch><step>A</step><octave>4</octave></pitch><duration>16</duration><type>whole</type><notations><ornaments><turn/></ornaments></notations></note>
</measure></part></score-partwise>''')
    notes=parse_musicxml(path)
    assert [n['pitch'] for n in notes]==[71,72,69]
    assert [n['grace'] for n in notes]==[True,True,False]
    assert all(n['written_onset']==0 for n in notes)
    assert notes[-1]['ornaments']==['turn']
    assert len(groups(notes,tolerance=.0001))==3


def test_grace_chord_members_share_one_attack(tmp_path):
    path=tmp_path/'chord.musicxml'
    path.write_text('''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Piano</part-name></score-part></part-list><part id="P">
<measure number="1"><attributes><divisions>1</divisions></attributes>
<note><grace/><pitch><step>C</step><octave>4</octave></pitch><type>eighth</type></note>
<note><grace/><chord/><pitch><step>E</step><octave>4</octave></pitch><type>eighth</type></note>
<note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
</measure></part></score-partwise>''')
    notes=parse_musicxml(path)
    assert groups(notes,tolerance=.0001)[0]['pitches']=={60,64}
    assert len(groups(notes,tolerance=.0001))==2
