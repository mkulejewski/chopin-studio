import hashlib
import json

from chopin.reference_review import navigation_map
from chopin.store import Store


def test_reviewed_map_tracks_matched_edition_and_keeps_manual_calibration(tmp_path):
    store=Store(tmp_path)
    pid='p40-1';saved=[{'measure':1,'pdf_page':28},{'measure':57,'pdf_page':31}]
    for p in saved:store.execute('INSERT INTO page_maps VALUES(?,?,?)',(pid,p['measure'],p['pdf_page']))
    reference={'id':'scan-reviewed-fixture','piece_id':pid,'filename':'test.musicxml'}
    path=store.root/'references/test.musicxml';path.write_text('<score-partwise/>')
    volume=store.query('SELECT v.filename FROM pieces p JOIN volumes v ON v.id=p.volume_id WHERE p.id=?',(pid,))[0]['filename']
    reviewed=[{'measure':1,'pdf_page':28},{'measure':42,'pdf_page':31}]
    metadata={'status':'model-reviewed','open_issues':[],'derived_musicxml_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'measure_layout_changed':True,'legacy_page_map':saved,'reviewed_page_map':reviewed,'scan':{'filename':volume}}
    sidecar=path.with_suffix('.review.json');sidecar.write_text(json.dumps(metadata))
    assert navigation_map(store,reference)==reviewed
    assert navigation_map(store,{**reference,'id':'other-edition'})==saved
    store.execute('UPDATE page_maps SET measure=43 WHERE piece_id=? AND measure=57',(pid,))
    assert navigation_map(store,reference)[1]['measure']==43
    # Source changes invalidate the fingerprint; no other edition's map is substituted.
    path.write_text('<changed/>')
    assert navigation_map(store,reference)==[]
    store.db.close()


def test_missing_or_incomplete_review_cannot_reuse_legacy_numbering(tmp_path):
    store=Store(tmp_path)
    reference={'id':'scan-reviewed-fixture','piece_id':'p40-1','filename':'test.musicxml'}
    store.execute('INSERT INTO page_maps VALUES(?,?,?)',('p40-1',1,28))
    assert navigation_map(store,reference)==[]
    store.db.close()
