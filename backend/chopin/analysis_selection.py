"""Read-time analysis freshness shared by assessment, progress and audio review.

Eligibility never edits historical results. Consumer policies deliberately differ:
retention can describe recovered/discarded takes; automatic progress cannot.
Caches live only for this reader/request and are never reused across revisions.
"""
import hashlib
import json
from dataclasses import dataclass

from .domain_types import AnalysisFreshness, ReferenceIdentity

SNAPSHOT_FIELDS = ('piece_id', 'start', 'end', 'revision', 'discarded', 'complete')


def reference_identity(reference) -> ReferenceIdentity:
    notes = reference.get('note_data', reference.get('notes'))
    if isinstance(notes, str):
        notes = json.loads(notes)
    payload = {'notes': notes, 'quality': reference['quality'], 'edition': reference.get('edition')}
    revision = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return ReferenceIdentity(reference['id'], revision)


@dataclass(frozen=True)
class AnalysisPolicy:
    statuses: tuple[str, ...] = ('saved', 'imported')
    allow_discarded: bool = False


AUTOMATIC = AnalysisPolicy()
AUDIO_REVIEW = AnalysisPolicy(('saved', 'imported', 'recovered', 'incomplete'), allow_discarded=True)


class AnalysisReader:
    def __init__(self, store):
        self.store = store
        self._references = {}

    def freshness(self, result, segment, *, policy=AUTOMATIC):
        snapshot = result.get('segment_snapshot', {})
        status = segment.get('session_status')
        if status is None:
            rows = self.store.query('SELECT status FROM sessions WHERE id=?', (segment['session_id'],))
            status = rows[0]['status'] if rows else None
        removed = segment.get('recording_deleted')
        if removed is None:
            removed = bool(self.store.query("SELECT id FROM recording_deletions WHERE segment_id=? AND scope='recording'", (segment.get('segment_id', segment['id']),)))
        reference_current = None
        reference_id, revision = result.get('reference_id'), result.get('reference_revision')
        if reference_id and revision:
            if reference_id not in self._references:
                rows = self.store.query('SELECT * FROM symbolic_scores WHERE id=?', (reference_id,))
                self._references[reference_id] = reference_identity(rows[0]).revision if rows else None
            reference_current = self._references[reference_id] == revision
        return AnalysisFreshness(
            all(snapshot.get(k) == segment.get(k) for k in SNAPSHOT_FIELDS),
            status in policy.statuses and (policy.allow_discarded or not segment['discarded']),
            bool(removed), reference_current,
        )

    def latest_for_segment(self, segment, *, policy=AUTOMATIC):
        for row in self.store.query('SELECT result FROM analyses WHERE segment_id=? ORDER BY created DESC,id DESC', (segment['id'],)):
            result = json.loads(row['result'])
            if self.freshness(result, segment, policy=policy).current:
                return result
        return {}

    def current_rows(self, piece_id=None, *, newest_first=False):
        clause = ' AND s.piece_id=?' if piece_id is not None else ''
        order = 'ps.started DESC,s.start DESC' if newest_first else 'ps.started,s.start'
        rows = self.store.query('''SELECT a.*,s.start,s.end,s.revision,s.complete,s.discarded,s.piece_id,
            ps.started,ps.status AS session_status,
            EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording') AS recording_deleted
            FROM analyses a JOIN segments s ON s.id=a.segment_id JOIN sessions ps ON ps.id=s.session_id
            WHERE s.discarded=0 AND ps.status IN ('saved','imported')''' + clause +
            ' ORDER BY ' + order + ',a.created DESC,a.id DESC', (piece_id,) if piece_id is not None else ())
        seen = set()
        for row in rows:
            if row['segment_id'] in seen:
                continue
            result = json.loads(row['result'])
            if self.freshness(result, row).current:
                seen.add(row['segment_id'])
                yield row, result
