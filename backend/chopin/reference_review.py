"""Fingerprint-bound review metadata for derived references and page navigation."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path


@lru_cache(maxsize=32)
def _read_review(filename, xml_stat, review_stat):
    path=Path(filename)
    review=json.loads(path.with_suffix('.review.json').read_text())
    if (review.get('status')!='model-reviewed' or review.get('open_issues')
            or review.get('derived_musicxml_sha256')!=hashlib.sha256(path.read_bytes()).hexdigest()):
        return None
    return review


def reviewed_metadata(path):
    path=Path(path)
    try:
        xml=path.stat();sidecar=path.with_suffix('.review.json').stat()
        return _read_review(str(path),(xml.st_mtime_ns,xml.st_size),(sidecar.st_mtime_ns,sidecar.st_size))
    except (OSError,ValueError,TypeError):
        return None


def navigation_map(store, reference):
    """Use the matched edition's map; keep subsequent manual calibration effective."""
    pid=reference['piece_id']
    saved=store.query('SELECT measure,pdf_page FROM page_maps WHERE piece_id=? ORDER BY measure',(pid,))
    if not reference.get('id','').startswith('scan-reviewed-'):
        return saved
    review=reviewed_metadata(store.root/'references'/reference.get('filename',''))
    if not review:
        return []
    if not review.get('measure_layout_changed'):
        return saved
    baseline=review.get('legacy_page_map')
    if baseline is None:
        return []  # Never apply another edition's ordinal numbering implicitly.
    if saved!=baseline:
        return saved  # A later explicit calibration remains the user's choice.
    piece=store.query('SELECT v.filename FROM pieces p JOIN volumes v ON v.id=p.volume_id WHERE p.id=?',(pid,))
    if not piece or piece[0]['filename']!=review.get('scan',{}).get('filename'):
        return []
    return review.get('reviewed_page_map',[])
