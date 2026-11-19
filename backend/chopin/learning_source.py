"""Edition and pitch reference eligibility shared by the score workflows."""

import hashlib


def reviewed_reference(bundle):
    return bundle.get("reference_status") in ("model-reviewed", "human-reviewed")


class LearningSource:
    def __init__(self, store):
        self.store = store
        self.pdf_cache = None

    def status(self, bundle):
        automatic_ready = reviewed_reference(bundle)
        if bundle.get('analysis_status') not in ('model-reviewed', 'human-reviewed') or (not automatic_ready and not bundle.get('allow_scan_study')):
            return False, 'This lesson or its digital counterpart is provisional and needs in-depth review before advancement.'
        rows = self.store.query('SELECT * FROM volumes WHERE id=?', (bundle['source'].get('volume_id', 'etudes'),))
        if not rows or not rows[0]['filename']:
            return False, f"Import the reviewed Paderewski {bundle['source'].get('volume_id', 'etudes').title()} PDF in Library."
        path = self.store.root / 'scores' / rows[0]['filename']
        try:
            stat = path.stat()
            key = (str(path), stat.st_mtime_ns, stat.st_size)
            if not self.pdf_cache or self.pdf_cache[0] != key:
                self.pdf_cache = (key, hashlib.sha256(path.read_bytes()).hexdigest())
            if self.pdf_cache[1] != bundle['source']['pdf_sha256']:
                return False, 'This PDF differs from the reviewed Paderewski scan. Learning needs edition review before advancement.'
        except OSError:
            return False, 'The reviewed PDF is unavailable.'
        return (True, 'Full Paderewski pitch/attack counterpart · model-reviewed' if automatic_ready else
                'Paderewski scan study · provisional digital draft. Automatic grading, finish and mistake restart are disabled; use your own memory judgement to progress.')
