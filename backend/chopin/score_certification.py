"""Edition-bound read-throughs, with independent capture scope and review history."""

from collections import deque
from datetime import datetime, timezone
import json
from threading import Lock

from .certification_matching import MAX_ATTACKS, compare, suggest_fixes
from .learning_definition import BUNDLES, lesson, stages
from .learning_profiles import load_profile
from .learning_source import LearningSource, reviewed_reference
from .midi_files import journal_events


class CertificationNotFound(LookupError):
    pass


class CertificationEnded(ValueError):
    pass


class CertificationUnavailable(ValueError):
    pass


def learned_end(bundle, profile):
    both = profile if profile['hand'] == 'both' else profile['hand_progress'].get('both', {})
    completed = set(both.get('completed', []))
    covered = {
        number
        for stage in stages(profile['chunks'], bundle)
        if stage['kind'] == 'hidden' and stage['id'] in completed
        for number in range(stage['start'], stage['end'] + 1)
    }
    last = None
    for measure in bundle['measures']:
        if measure['number'] not in covered:
            break
        last = measure['number']
    return last


def build_review(bundle, played, first, last, corrections=(), through_pause=False):
    scope = {**bundle, 'measures': [m for m in bundle['measures'] if first <= m['number'] <= last]}
    result = compare(scope, played, corrections, through_pause=through_pause)
    suggest_fixes(result)
    return result


class ScoreCertification:
    def __init__(self, store, recorder, lifecycle_lock):
        self.store = store
        self.recorder = recorder
        self.lifecycle_lock = lifecycle_lock
        self.review_lock = Lock()
        self.source = LearningSource(store)
        self.active = None
        self.store.execute(
            """UPDATE score_certifications SET status='interrupted', notice=?
               WHERE status='recording'""",
            ('The app closed during this take. Any recovered MIDI is available for inspection.',),
        )

    def bundle(self, piece):
        if piece not in BUNDLES or not reviewed_reference(lesson(piece)):
            raise CertificationNotFound('This piece has no Learning-grade pitch reference.')
        return lesson(piece)

    def state(self, piece):
        with self.lifecycle_lock:
            bundle = self.bundle(piece)
            ready, notice = self.source.status(bundle)
            measures = bundle['measures']
            profile = load_profile(self.store, bundle)
            takes = self.store.query(
                """SELECT id, session_id, created, status, notice, revision,
                          start_measure, end_measure, through_pause, origin,
                          json_array_length(corrections) AS correction_count,
                          CASE WHEN origin='corrections' THEN corrections END AS manual_corrections
                   FROM score_certifications WHERE piece_id=? AND status<>'superseded'
                   ORDER BY created DESC""", (piece,),
            )
            for take in takes:
                snapshot = take.pop('manual_corrections')
                if snapshot is not None:
                    take['manual_corrections'] = [
                        {key: rule.get(key) for key in ('note_id', 'measure', 'staff', 'pitch', 'original_pitch', 'spelling')}
                        for rule in json.loads(snapshot)
                    ]
            return {
                'title': bundle['title'],
                'revision': bundle['revision'],
                'ready': ready,
                'notice': notice,
                'measures': [{'number': m['number'], 'pdf_page': m['pdf_page']} for m in measures],
                'learned_end': learned_end(bundle, profile),
                'correction_measures': [rule['measure'] for rule in profile['corrections']],
                'volume_id': bundle['source'].get('volume_id', 'etudes'),
                'first_page': min(m['pdf_page'] for m in measures),
                'last_page': max(m['pdf_page'] for m in measures),
                'takes': takes,
            }

    def start(self, piece, studio, *, start_measure=None, end_measure=None, include_corrections=False):
        with self.lifecycle_lock:
            if studio.shutting_down:
                raise CertificationUnavailable('Chopin Studio is shutting down.')
            if self.active:
                raise ValueError('Finish the active certification take first.')
            bundle = self.bundle(piece)
            ready, notice = self.source.status(bundle)
            if not ready:
                raise ValueError(notice)
            numbers = [m['number'] for m in bundle['measures']]
            first = numbers[0] if start_measure is None else start_measure
            last = numbers[-1] if end_measure is None else end_measure
            if first not in numbers or last not in numbers or first > last:
                raise ValueError('Choose an ordered range of measures in this score.')
            corrections = [
                rule for rule in load_profile(self.store, bundle)['corrections']
                if first <= rule['measure'] <= last
            ] if include_corrections else []
            sid = self.recorder.start(
                simulated=studio.simulation.running, source='score_certification',
                name_prefix=f"Score certification · {bundle['title']}",
            )
            try:
                self.store.execute(
                    """INSERT INTO score_certifications
                       (id,piece_id,session_id,revision,status,created,start_measure,end_measure,corrections)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (sid, piece, sid, bundle['revision'], 'recording', datetime.now(timezone.utc).isoformat(),
                     first, last, json.dumps(corrections)),
                )
            except Exception:
                self.recorder.stop()
                raise
            self.active = (piece, sid)
            return self.state(piece)

    def stop(self, piece, ident, *, interruption=None, through_pause=False):
        with self.lifecycle_lock:
            if self.active != (piece, ident):
                take = self.take(piece, ident)
                if take['status'] != 'recording':
                    return self.state(piece)
                raise ValueError('This certification take is no longer recording.')
            if self.recorder.active == ident:
                self.recorder.stop()
            session = self.store.query('SELECT status,error FROM sessions WHERE id=?', (ident,))[0]
            if session['status'] == 'saving':
                raise ValueError('The MIDI recording is still saving.')
            ready, notice = self.source.status(self.bundle(piece))
            if not interruption and (session['status'] != 'saved' or session['error']):
                interruption = session['error'] or 'Recording integrity could not be confirmed.'
            if not interruption and not ready:
                interruption = notice
            self.store.execute(
                'UPDATE score_certifications SET status=?,notice=?,through_pause=? WHERE id=?',
                ('interrupted' if interruption else 'saved', interruption, through_pause, ident),
            )
            self.active = None
            return self.state(piece)

    def take(self, piece, ident):
        self.bundle(piece)
        found = self.store.query("SELECT * FROM score_certifications WHERE piece_id=? AND id=? AND status<>'superseded'", (piece, ident))
        if not found:
            raise CertificationNotFound('Certification take not found.')
        return found[0]

    def attacks(self, ident):
        try:
            for event in journal_events(self.store.root / 'sessions' / ident / 'events.jsonl'):
                if event.get('kind') == 'capture_loss':
                    raise ValueError('The MIDI journal reports dropped events.')
                message = event.get('message', {})
                if message.get('type') == 'note_on' and message.get('velocity', 0) > 0:
                    yield message['note']
        except OSError as exc:
            raise ValueError('The MIDI journal is unavailable.') from exc

    def live(self, piece, ident):
        with self.lifecycle_lock:
            if self.active != (piece, ident):
                raise CertificationEnded('This certification take has ended.')
            with self.recorder.lock:
                if self.recorder.active == ident and not self.recorder.journal.closed:
                    self.recorder.journal.flush()
        recent = deque(maxlen=8)
        count = 0
        for count, pitch in enumerate(self.attacks(ident), 1):
            recent.append(pitch)
        return {'played_count': count, 'recent': list(recent)}

    def review(self, piece, ident):
        with self.review_lock:
            take = self.take(piece, ident)
            if take['review']:
                return json.loads(take['review'])
            if take['status'] != 'saved' or not take['session_id']:
                raise ValueError('A complete saved MIDI take is required for comparison.')
            bundle = self.bundle(piece)
            if bundle['revision'] != take['revision']:
                raise ValueError('This take uses an earlier reference revision.')
            played = []
            for pitch in self.attacks(take['session_id']):
                if len(played) >= MAX_ATTACKS:
                    raise ValueError(f'The take exceeds {MAX_ATTACKS:,} attacks. Original MIDI is available.')
                played.append(pitch)
            result = build_review(
                bundle, played, take['start_measure'], take['end_measure'],
                json.loads(take['corrections']), through_pause=bool(take['through_pause']),
            )
            self.store.execute('UPDATE score_certifications SET review=? WHERE id=?',
                               (json.dumps(result), ident))
            return result
