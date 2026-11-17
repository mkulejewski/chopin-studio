"""Native digital-score exports preserve attack/tie semantics without a renderer dependency."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "counterparts", Path(__file__).resolve().parents[1]/"scripts/build_nocturne_practice_counterparts.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

MEI = '''<mei xmlns="http://www.music-encoding.org/ns/mei"><music><measure n="0">
<staff n="1"><layer n="1"><note xml:id="a"/><note xml:id="b"/></layer></staff>
<staff n="2"><layer n="1"><note xml:id="bass"/></layer></staff>
<tie startid="#a" endid="#b"/>
</measure></music></mei>'''
TIMEMAP = [dict(qstamp=0,on=['a','bass']),dict(qstamp=1,on=['b'],off=['a']),
           dict(qstamp=2,off=['b','bass'])]


class Renderer:
    def getMIDIValuesForElement(self, ident):
        return {'pitch': 48 if ident == 'bass' else 72}


def test_native_inventory_uses_tie_chains_and_both_staves():
    notes, coverage = builder.attack_inventory(Renderer(), MEI, TIMEMAP)
    assert len(notes) == 2
    assert all(n['duration'] == 2 for n in notes)
    assert {n['staff'] for n in notes} == {1,2}
    assert all(n['measure'] == 1 and n['source_measure'] == '0' for n in notes)
    assert coverage[0]['attacks'] == {'1':1,'2':1}


def test_native_inventory_rejects_missing_release_or_unfolded_ids():
    with pytest.raises(ValueError,match='release|tie chain'):
        builder.attack_inventory(Renderer(), MEI, TIMEMAP[:-1])
    with pytest.raises(ValueError,match='Unfolded'):
        builder.attack_inventory(Renderer(), MEI, TIMEMAP+[dict(qstamp=3,on=['a'])])


def test_native_dynamic_levels_keep_staff_and_compound_meter_position():
    mei=MEI.replace('<tie startid="#a" endid="#b"/>',
                    '<dynam staff="1 2" tstamp="4">pp</dynam>')
    assert builder.native_dynamics(mei,8)==[
        dict(measure=1,beat=1.5,staff=1,dynamic='pp'),
        dict(measure=1,beat=1.5,staff=2,dynamic='pp')]
