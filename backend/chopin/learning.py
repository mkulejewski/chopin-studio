"""Edition-bound memorization: durable attempts and pitch-only partial-order matching.

Each staff has an ordered sequence of attacks; notes within a chord are unordered.
No elapsed-time, duration, velocity or tempo value enters the pitch judgement.
The bounded beam can decline a valid ambiguous performance, never invent a pass:
a pass is always a zero-edit path consuming the entire assigned reference.
"""
from datetime import datetime, timezone
import hashlib
import copy
import json
import re
import threading
import time
import uuid

from .midi_files import journal_events

from .learning_definition import (
    BUNDLE as BUNDLE, BUNDLES as BUNDLES, DEFAULTS as DEFAULTS, HANDS as HANDS,
    HAND_LABELS as HAND_LABELS, PROGRESS_FIELDS as PROGRESS_FIELDS,
    REVIEW_PAUSE_SECONDS as REVIEW_PAUSE_SECONDS, lesson as lesson, stages as stages,
)
from .learning_matching import (
    note_name as note_name, reference_groups as reference_groups, _choices as _choices,
    _advance as _advance, _consume as _consume, ornament_position as ornament_position,
    ornament_allowed as ornament_allowed, PitchPrefixMatcher as PitchPrefixMatcher,
    evaluate as evaluate,
)
from .learning_profiles import load_profile, save_profile


class Learning:
    def __init__(self, store, recorder, piece_id='e25-1'):
        self.piece_id = piece_id
        self.store, self.recorder = store, recorder
        self.lock = threading.RLock()
        self.active = None
        self.review_target = None
        self.initial_view = True
        self.pending = None
        self.last_count = -1
        self.completion_at = None
        self.last_evaluation = None
        self.staff_matcher = None
        self.staff_attempt = None
        self.last_pedal_repeat = 0
        self.pdf_cache = None
        self.last_frontend = time.monotonic()
        self.error = None
        store.execute("UPDATE learning_attempts SET status='interrupted' WHERE status='recording' AND piece_id=?", (piece_id,))

    def lesson(self):
        return lesson() if self.piece_id == 'e25-1' else lesson(self.piece_id)

    def automatic_ready(self):
        return self.lesson().get('reference_status') in ('model-reviewed', 'human-reviewed')

    def profile(self):
        return load_profile(self.store, self.lesson())

    def save(self, profile):
        save_profile(self.store, self.lesson(), profile)

    def source_status(self):
        bundle = self.lesson()
        if bundle.get('analysis_status') not in ('model-reviewed', 'human-reviewed') or (not self.automatic_ready() and not bundle.get('allow_scan_study')):
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
        return (True, 'Full Paderewski pitch/attack counterpart · model-reviewed' if self.automatic_ready() else
                'Paderewski scan study · provisional digital draft. Automatic grading, finish and mistake restart are disabled; use your own memory judgement to progress.')

    def review_assignment(self, profile, start, end, chunk_index=None):
        return {'id': f"review:{start}:{end}:{profile['generation']}", 'kind': 'review',
                'start': start, 'end': end, 'chunk': chunk_index if chunk_index is not None else next(i for i,c in enumerate(profile['chunks']) if c['end']>=end),
                'focus': ('Review this learned chunk.' if chunk_index is not None else 'Recall the learned span of this section.' if self.lesson().get('section_order') else 'Recall the piece from the pickup through this point.')+' Review never changes your learning position or correct-attempt streak.'}

    def snapshot(self):
        with self.lock:
            bundle = self.lesson()
            profile = self.profile()
            sequence = stages(profile['chunks'], self.lesson())
            learning_target = sequence[profile['stage_index']] if profile['stage_index'] < len(sequence) else None
            independent = bundle.get('connection_strategy') == 'independent-sections'
            current_section = profile['chunks'][learning_target['chunk']]['section'] if learning_target else bundle.get('section_order', [0])[-1]
            review_chunks = [c for c in profile['chunks'] if not independent or c['section'] == current_section]
            if independent and current_section in bundle.get('backward_sections', []):
                review_chunks = list(reversed(review_chunks))
            learned_start, learned_end = None, None
            for c in review_chunks:
                if any(t['kind']=='hidden' and t['start']==c['start'] and t['end']==c['end'] and t['id'] in profile['completed'] for t in sequence):
                    learned_start = c['start'] if learned_start is None else min(learned_start, c['start'])
                    learned_end = c['end'] if learned_end is None else max(learned_end, c['end'])
                else:
                    break
            if self.initial_view:
                self.initial_view = False
                if learned_end is not None:
                    self.review_target = self.review_assignment(profile, learned_start, learned_end)
            target = self.review_target or learning_target
            ready, source_notice = self.source_status()
            history = self.store.query("SELECT * FROM learning_attempts WHERE piece_id=? AND COALESCE(json_extract(target, '$.hand'), 'both')=? ORDER BY created DESC LIMIT 12", (bundle['piece_id'], profile['hand']))
            for row in history:
                row['target'] = json.loads(row['target'])
                row['result'] = json.loads(row['result']) if row['result'] else None
            return {'lesson': {k: v for k, v in bundle.items() if k not in ('measures', 'chunks')},
                    'profile': profile, 'stages': sequence, 'automatic_ready': self.automatic_ready(), 'target': target, 'learning_target': learning_target, 'ready': ready,
                    'review': {'active': self.review_target is not None, 'learned_start': learned_start, 'learned_end': learned_end,
                               'current_start': (min(learning_target['start'], learned_start if learned_start is not None else learning_target['start']) if learning_target else learned_start) if independent else bundle['measures'][0]['number'],
                               'current_end': max(learning_target['end'], learned_end or learning_target['end']) if learning_target else learned_end},
                    'source_notice': source_notice, 'active': self.active,
                    'pending_at': self.pending, 'history': history, 'controller_error': self.error,
                    'progress': {'completed': profile['stage_index'], 'total': len(sequence)},
                    'target_page': next((m['pdf_page'] for m in bundle['measures'] if target and m['number'] == target['start']), bundle['source']['pdf_pages'][0])}

    def select_hand(self, hand):
        if hand not in HANDS:
            raise ValueError('Choose both, right or left hand.')
        with self.lock:
            profile = self.profile()
            if hand == profile['hand']:
                return self.snapshot()
            if self.active:
                raise ValueError('Finish or pause the attempt before changing hands.')
            profile['hand_progress'][profile['hand']] = copy.deepcopy({
                k: profile[k] for k in PROGRESS_FIELDS if k in profile})
            progress = profile['hand_progress'].get(hand, {'stage_index': 0, 'streak': 0, 'completed': []})
            for field in PROGRESS_FIELDS:
                profile.pop(field, None)
            profile.update(copy.deepcopy(progress))
            profile['hand'] = hand
            profile['generation'] += 1
            self.pending = None
            self.review_target = None
            self.save(profile)
            return self.snapshot()

    def configure(self, config, chunks=None):
        with self.lock:
            if self.active:
                raise ValueError('Finish or pause the attempt before changing the lesson.')
            self.pending = None
            self.review_target = None
            profile = self.profile()
            profile['config'] = config
            if chunks is not None:
                # Require complete, ordered, non-overlapping coverage, even after edits.
                first, last = self.lesson()['measures'][0]['number'], self.lesson()['measures'][-1]['number']
                if not chunks or len(chunks) > 100 or chunks[0]['start'] != first or chunks[-1]['end'] != last:
                    raise ValueError(f'Chunks must cover measures {first} through {last}.')
                for i, c in enumerate(chunks):
                    if c['start'] > c['end'] or (i and c['start'] != chunks[i-1]['end']+1):
                        raise ValueError('Chunks must cover every measure exactly once, without gaps or overlap.')
                    section = next(s for s in self.lesson()['sections'] if s['start'] <= c['start'] <= s['end'])
                    if c['end'] > section['end']:
                        raise ValueError('Keep a chunk inside its musical section; edit boundaries within sections.')
                    c['section'] = self.lesson()['sections'].index(section)
                    c['label'] = f"{c['start']}–{c['end']}"
                same = [(c['start'], c['end'], c['focus']) for c in chunks] == [(c['start'], c['end'], c['focus']) for c in profile['chunks']]
                if not same:
                    profile.update(chunks=chunks, stage_index=0, streak=0, completed=[], hand_progress={})
                    profile['generation'] += 1
            # Repetition requirements are shared across all hand modes.
            profile['streak'] = 0
            for progress in profile['hand_progress'].values():
                progress['streak'] = 0
            self.save(profile)
            return self.snapshot()

    def review(self, include_current=False, chunk_index=None):
        with self.lock:
            if self.active and chunk_index is None:
                raise ValueError('Finish or pause the current take before starting review.')
            snap = self.snapshot()
            if not snap['ready']:
                raise ValueError(snap['source_notice'])
            start = snap['review']['current_start'] if include_current else snap['review']['learned_start']
            end = snap['review']['current_end'] if include_current else snap['review']['learned_end']
            if chunk_index is not None:
                if not 0 <= chunk_index < len(snap['profile']['chunks']):
                    raise ValueError('Unknown chunk.')
                chunk = snap['profile']['chunks'][chunk_index]
                if not any(t['kind']=='hidden' and t['chunk']==chunk_index and t['id'] in snap['profile']['completed'] for t in snap['stages']):
                    raise ValueError('This chunk has not been learned yet.')
                start, end = chunk['start'], chunk['end']
            if end is None or start is None:
                raise ValueError('No chunks learned yet. Complete hidden recall or include the current chunk.')
            if self.active:
                self.finish(aborted=True, preserve_streak=True)
            self.pending = None
            self.review_target = self.review_assignment(snap['profile'], start, end, chunk_index)
            return self.start()

    def leave_review(self):
        with self.lock:
            if self.active and self.active['target']['kind'] == 'review':
                self.finish(aborted=True)
            self.review_target = None
            self.pending = None
            return self.snapshot()

    def start(self):
        with self.lock:
            self.last_frontend = time.monotonic()
            snap = self.snapshot()
            if not snap['ready']:
                raise ValueError(snap['source_notice'])
            if not snap['target']:
                raise ValueError('All lesson stages are complete. Restart the lesson to review it.')
            if self.active or self.recorder.active:
                raise ValueError('A recording is already active. Finish it before starting Learning.')
            ident = uuid.uuid4().hex
            profile = snap['profile']
            target = {**snap['target'], 'hand': profile['hand'], 'config': profile['config'], 'variants': profile.get('corrections', []) + profile['variants'],
                      'generation': profile['generation'], 'streak_before': profile['streak']}
            sid = self.recorder.start(midi_enabled=True, microphone_enabled=False)
            self.store.execute("UPDATE sessions SET source='learning',name=? WHERE id=?", (f"Learning {self.lesson()['title']} · {target['start']}–{target['end']} · {target['kind']} · {HAND_LABELS[profile['hand']]} · {ident[:6]}", sid))
            self.recorder.mark('learning_attempt', {'id': ident, 'piece_id': self.piece_id, 'target': target})
            try:
                self.store.execute('INSERT INTO learning_attempts VALUES(?,?,?,?,?,?,?,?)',
                    (ident, self.piece_id, sid, self.lesson()['revision'], 'recording', datetime.now(timezone.utc).isoformat(), json.dumps(target), None))
            except Exception:
                self.recorder.stop()
                raise
            self.active = {'id': ident, 'session_id': sid, 'target': target, 'assisted': False}
            groups = reference_groups(self.lesson(), target['start'], target['end'], target['variants'], target.get('hand', 'both'))
            self.minimum_attacks = len({(g['position'], n['pitch']) for staff in groups for g in staff for n in g['notes']})
            self.pending = None
            self.error = None
            self.last_count = -1
            self.completion_at = None
            self.last_evaluation = None
            self.restart_matcher = PitchPrefixMatcher(self.lesson(), target) if self.automatic_ready() and profile['config'].get('auto_restart_on_mistake') else None
            return self.snapshot()

    def assist(self):
        with self.lock:
            if self.active:
                self.active['assisted'] = True
                self.recorder.mark('learning_peek', {})
            return self.snapshot()

    def _observed(self, sid):
        events = list(journal_events(self.store.root / 'sessions' / sid / 'events.jsonl'))
        return [e['message']['note'] for e in events if e.get('message', {}).get('type') == 'note_on'
                and e['message'].get('velocity', 0) > 0], events

    def finish(self, aborted=False, restarted=False, preserve_streak=False, auto_restarted=False):
        with self.lock:
            if not self.active:
                raise ValueError('No Learning attempt is recording.')
            active = self.active
            sid = active['session_id']
            if self.recorder.active == sid:
                self.recorder.stop()
            elif self.recorder.active:
                raise ValueError('A different recording is active; Learning is paused.')
            observed, events = self._observed(sid)
            session = self.store.query('SELECT * FROM sessions WHERE id=?', (sid,))[0]
            result = evaluate(self.lesson(), active['target'], observed, active['target']['variants']) if not aborted and self.automatic_ready() else {
                'version': 'learning-pitch-order-v1', 'passed': False, 'uncertain': False,
                'errors': [], 'error_count': 0, 'played_attacks': len(observed),
                'notice': 'Unevaluated take.' if aborted else 'Digital reference is provisional. This take has no automatic pitch verdict; assess your recall against the Paderewski scan.'}
            capture_ok = session['status'] == 'saved' and not session['error'] and not any(e.get('kind') == 'capture_loss' for e in events)
            source_ok, _ = self.source_status()
            assisted = active['assisted'] and active['target']['kind'] != 'visible'
            result.update(capture_ok=capture_ok, assisted=assisted, aborted=aborted, restarted=restarted,
                          auto_restarted=auto_restarted, suspended_for_review=preserve_streak)
            result['passed'] = bool(result['passed'] and capture_ok and source_ok and not assisted and not aborted)
            if not capture_ok or not source_ok:
                result['notice'] = 'Recording or edition integrity could not be confirmed. Progress has not advanced.'
            elif aborted:
                result['notice'] = ('Take automatically restarted after a pitch/order mismatch; MIDI saved without evaluation. Your correct-attempt streak is unchanged.' if auto_restarted else
                                    'Take restarted; MIDI saved without evaluation. Your correct-attempt streak is unchanged.' if restarted else
                                    'Take saved to enter chunk review. Your correct-attempt streak is unchanged.' if preserve_streak else
                                    'Attempt paused; MIDI saved. This attempt does not count toward advancement.')
            elif assisted:
                result['notice'] = 'Score consulted. Repeat without assistance to count toward recall.'
            profile = self.profile()
            is_review = active['target']['kind'] == 'review'
            if is_review:
                result['notice'] += ' Review saved; learning position and streak unchanged.'
            if not is_review and result['passed']:
                profile['streak'] += 1
                kind = active['target']['kind']
                required = profile['config'][kind] if kind in ('visible', 'hidden') else profile['config']['connections']
                if profile['streak'] >= required:
                    profile['completed'].append(active['target']['id'])
                    profile['stage_index'] += 1
                    profile['streak'] = 0
            elif not is_review and not restarted and not preserve_streak:
                profile['streak'] = 0
            # Store attempt result and advancement in a single transaction.
            with self.store.lock:
                try:
                    self.store.db.execute('UPDATE learning_attempts SET status=?,result=? WHERE id=?',
                        ('restarted' if restarted else 'paused' if aborted else 'evaluated', json.dumps(result), active['id']))
                    self.store.db.execute('INSERT OR REPLACE INTO learning_profiles VALUES(?,?,?)',
                        (self.piece_id, self.lesson()['revision'], json.dumps(profile)))
                    self.store.db.commit()
                except Exception:
                    self.store.db.rollback()
                    raise
            self.active = None
            self.pending = time.time()+REVIEW_PAUSE_SECONDS if not is_review and profile['config']['auto_continue'] and result['passed'] and not aborted and source_ok and capture_ok and profile['stage_index'] < len(stages(profile['chunks'], self.lesson())) else None
            return self.snapshot()

    def repeat_from_pedal(self, owner, command_id, attempt_id, target_id):
        with self.lock:
            with self.recorder.lock:
                valid = (owner == self.recorder.learning_pedal_owner
                         and time.monotonic() < self.recorder.learning_pedal_until
                         and any(c['id'] == command_id and c['owner'] == owner
                                 for c in self.recorder.learning_pedal_commands))
            if not valid or command_id <= self.last_pedal_repeat:
                return self.snapshot()
            self.last_pedal_repeat = command_id
            snapshot = self.snapshot()
            if not snapshot['target'] or snapshot['target']['id'] != target_id:
                return snapshot
            if self.active:
                return self.restart_take(attempt_id) if attempt_id else snapshot
            self.pending = None
            return self.start()

    def restart_take(self, attempt_id, automatic=False):
        with self.lock:
            if not self.active:
                raise ValueError('No take is recording. Start an attempt first.')
            if self.active['id'] != attempt_id:
                return self.snapshot()  # A repeated restart request is harmless.
            ready, notice = self.source_status()
            if not ready:
                raise ValueError(notice)
            finished = self.finish(aborted=True, restarted=True, auto_restarted=automatic)
            if automatic and not finished['history'][0]['result']['capture_ok']:
                return finished
            # No review countdown, no grade and no change of assignment or streak.
            return self.start()

    def accept_take(self, ident):
        """Count a pianist's memory judgement without changing pitch evidence."""
        with self.lock:
            if self.active:
                raise ValueError('Finish the current attempt before assessing the previous take.')
            rows = self.store.query("SELECT * FROM learning_attempts WHERE piece_id=? AND COALESCE(json_extract(target, '$.hand'), 'both')=? ORDER BY created DESC LIMIT 1", (self.piece_id, self.profile()['hand']))
            if not rows or rows[0]['id'] != ident:
                raise ValueError('Only the most recent finished take can be counted as remembered.')
            row = rows[0]
            target = json.loads(row['target'])
            result = json.loads(row['result']) if row['result'] else None
            if target['kind'] == 'review':
                raise ValueError('Review never changes the learning streak. Return to Learning for counted repetitions.')
            if result and result.get('manual_accepted'):
                return self.snapshot()  # Repeated clicks/retries are idempotent.
            if not result or row['status'] != 'evaluated' or result.get('passed') or result.get('aborted') or result.get('assisted') or not result.get('capture_ok'):
                raise ValueError('Use a finished, unassisted take with intact MIDI for this memory judgement.')
            profile = self.profile()
            sequence = stages(profile['chunks'], self.lesson())
            current = sequence[profile['stage_index']] if profile['stage_index'] < len(sequence) else None
            if (row['revision'] != self.lesson()['revision'] or not current or current['id'] != target['id']
                    or profile['generation'] != target['generation'] or profile['config'] != target['config']):
                raise ValueError('The lesson has changed since that take. Repeat the current assignment.')
            ready, notice = self.source_status()
            if not ready:
                raise ValueError(notice)
            before = target.get('streak_before')
            if before is None:
                raise ValueError('This older take has no saved streak snapshot. Make a new attempt to use memory judgement.')
            profile['streak'] = before+1
            kind = target['kind']
            required = profile['config'][kind] if kind in ('visible', 'hidden') else profile['config']['connections']
            if profile['streak'] >= required:
                profile['completed'].append(target['id'])
                profile['stage_index'] += 1
                profile['streak'] = 0
            result.update(manual_accepted=True, accepted_at=datetime.now(timezone.utc).isoformat(),
                          acceptance_reason='Pianist declares the passage remembered despite accidental key errors.')
            # The original passed=False, errors and notice remain unchanged.
            with self.store.lock:
                try:
                    self.store.db.execute('UPDATE learning_attempts SET result=? WHERE id=?', (json.dumps(result), ident))
                    self.store.db.execute('INSERT OR REPLACE INTO learning_profiles VALUES(?,?,?)',
                        (self.piece_id, self.lesson()['revision'], json.dumps(profile)))
                    self.store.db.commit()
                except Exception:
                    self.store.db.rollback()
                    raise
            self.pending = time.time()+REVIEW_PAUSE_SECONDS if profile['config']['auto_continue'] and profile['stage_index'] < len(sequence) else None
            return self.snapshot()

    def advance_stage(self, stage_id, generation):
        """The pianist may move on by self-assessment, without grading a take."""
        with self.lock:
            if self.review_target:
                raise ValueError('Return to Learning before advancing a learning stage.')
            profile = self.profile()
            sequence = stages(profile['chunks'], self.lesson())
            if generation != profile['generation']:
                raise ValueError('The lesson changed. Review the current stage before advancing.')
            current = sequence[profile['stage_index']] if profile['stage_index'] < len(sequence) else None
            if not current or current['id'] != stage_id:
                if any(t['id'] == stage_id for t in sequence[:profile['stage_index']]):
                    return self.snapshot()  # Already advanced; do not skip another stage.
                raise ValueError('Unknown current stage.')
            ready, notice = self.source_status()
            if not ready:
                raise ValueError(notice)
            if self.active:
                self.finish(aborted=True)
                profile = self.profile()
            profile.setdefault('manual_advances', []).append({
                'stage_id': stage_id, 'generation': generation, 'revision': self.lesson()['revision'],
                'accepted_at': datetime.now(timezone.utc).isoformat(),
                'reason': 'Pianist chose the next stage by self-assessment.'})
            profile['completed'].append(stage_id)
            profile['stage_index'] += 1
            profile['streak'] = 0
            self.save(profile)
            self.pending = time.time()+REVIEW_PAUSE_SECONDS if profile['config']['auto_continue'] and profile['stage_index'] < len(sequence) else None
            return self.snapshot()

    def pause(self):
        with self.lock:
            self.pending = None
            return self.finish(aborted=True) if self.active else self.snapshot()

    def restart(self):
        with self.lock:
            if self.active:
                raise ValueError('Pause the attempt before restarting.')
            self.pending = None
            self.review_target = None
            p = self.profile()
            p.update(stage_index=0, streak=0, completed=[], generation=p['generation']+1)
            self.save(p)
            return self.snapshot()

    def variant(self, note_id, action, pitch, reason, *, correction=False, spelling=None):
        with self.lock:
            if self.active:
                raise ValueError('Finish or pause before changing reference notes or personal rules.')
            all_notes = {n['id']: n for hand in ('right', 'left')
                         for staff in reference_groups(self.lesson(), self.lesson()['measures'][0]['number'], self.lesson()['measures'][-1]['number'], hand=hand) for g in staff for n in g['notes']}
            note = all_notes.get(note_id)
            if not note:
                raise ValueError('Unknown note occurrence in this edition revision.')
            profile = self.profile()
            collection = 'corrections' if correction else 'variants'
            if correction and any(v['note_id'] == note_id for v in profile['variants']):
                raise ValueError('Revoke the personal rule for this note before correcting its reference.')
            if action == 'revoke' and not any(v['note_id'] == note_id for v in profile[collection]):
                return self.snapshot()
            self.pending = None
            self.review_target = None
            profile[collection] = [v for v in profile[collection] if v['note_id'] != note_id]
            if action != 'revoke':
                profile[collection].append({'note_id': note_id, 'action': action, 'pitch': pitch,
                    'reason': reason, 'measure': note['measure'], 'staff': note['staff'],
                    'original_pitch': note['pitch'], 'kind': 'correction' if correction else 'personal',
                    'spelling': spelling})
            # Retain earlier unaffected progress; recheck the changed chunk and
            # every cumulative stage that depends on it. Historical MIDI is kept.
            sequence = stages(profile['chunks'], self.lesson())
            affected = next(i for i, t in enumerate(sequence) if t['start'] <= note['measure'] <= t['end'])
            progress_by_hand = {**profile['hand_progress'], profile['hand']: profile}
            for hand, progress in progress_by_hand.items():
                if hand != 'both' and hand != ('right' if note['staff'] == 1 else 'left'):
                    continue
                progress['stage_index'] = min(progress['stage_index'], affected)
                progress['completed'] = progress['completed'][:progress['stage_index']]
                progress['streak'] = 0
            profile['generation'] += 1
            self.save(profile)
            return self.snapshot()

    def correct_note(self, note_id, replacement, reason, action='replace'):
        pitch, spelling = 60, None
        if action != 'revoke':
            match = re.fullmatch(r'([A-Ga-g])([#b♯♭♮]?)(-?\d)', replacement.strip())
            if not match:
                raise ValueError('Enter a note such as E5, Eb5 or F#4.')
            step, accidental, octave = match.groups()
            alter = 1 if accidental in ('#', '♯') else -1 if accidental in ('b', '♭') else 0
            step, octave = step.upper(), int(octave)
            pitch = 12*(octave+1) + {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step] + alter
            if not 0 <= pitch <= 127:
                raise ValueError('That note is outside the MIDI range.')
            spelling = {'step': step, 'alter': alter, 'octave': octave}
        return self.variant(note_id, action, pitch, reason, correction=True, spelling=spelling)

    def live_staves(self, attempt_id, show_expected=True, first_measure=None):
        from .learning_staves import LiveStaffMatcher, played_only
        with self.lock:
            if not self.automatic_ready():
                raise ValueError('The digital draft needs full Paderewski review before staff comparison. Use the source scan.')
            rows = self.store.query('SELECT * FROM learning_attempts WHERE id=? AND piece_id=?', (attempt_id, self.lesson()['piece_id']))
            if not rows:
                raise ValueError('Learning take not found.')
            row = rows[0]
            if not row['session_id'] or row['revision'] != self.lesson()['revision']:
                raise ValueError('This take has no MIDI or uses a different reference revision.')
            active = bool(self.active and self.active['id'] == attempt_id)
            if active:
                with self.recorder.lock:
                    if self.recorder.active == row['session_id'] and not self.recorder.journal.closed:
                        self.recorder.journal.flush()
            try:
                observed, _ = self._observed(row['session_id'])
            except OSError as exc:
                raise ValueError('The saved MIDI journal is unavailable.') from exc
            target = json.loads(row['target'])
            expected_visible = bool(show_expected and (not active or target['kind']=='visible' or self.active['assisted']))
            if len(observed) > self.lesson().get('attack_limit', 6000):
                raise ValueError('Take too long for live notation; finish and use a shorter passage.')
            if self.staff_attempt != attempt_id or self.staff_matcher.count > len(observed):
                self.staff_attempt = attempt_id
                self.staff_matcher = LiveStaffMatcher(self.lesson(), target)
            self.staff_matcher.feed(observed[self.staff_matcher.count:])
            projection = self.staff_matcher.comparison(not active and row['status']=='evaluated', first_measure)
            if not expected_visible:
                projection = played_only(projection)
            return {**projection, 'attempt_id': attempt_id, 'active': active,
                    'expected_visible': expected_visible, 'played_attacks': len(observed),
                    'key_fifths': next((m.get('key_fifths', self.lesson().get('key_fifths', 0)) for m in self.lesson()['measures'] if m['number']==projection['first_measure']), self.lesson().get('key_fifths',0)),
                    'notice': 'Live alignment is provisional. Note spacing follows the reference; timing is not graded.' if expected_visible else
                              'Played notes only during hidden recall, using reference rhythm and beaming. Alignment is provisional; upcoming notes stay hidden.'}

    def tick(self):
        with self.lock:
            if self.error:
                return
            if (self.pending or self.active) and time.monotonic()-self.last_frontend > 15:
                self.pause()
                return
            if self.pending and time.time() >= self.pending:
                self.pending = None
                self.start()
                return
            if not self.active:
                return
            if self.recorder.active != self.active['session_id']:
                self.finish(aborted=True)
                return
            if not self.automatic_ready():
                return
            config = self.active['target']['config']
            if not config['auto_finish'] and not config.get('auto_restart_on_mistake'):
                return
            # The writer is authoritative. Flush pending writes before reading;
            # never take notes from the lossy live-recognition queue.
            with self.recorder.lock:
                if not self.recorder.queue.empty():
                    return
                self.recorder.journal.flush()
                notes_down = any(v for v in self.recorder.notes.values())
            observed, events = self._observed(self.active['session_id'])
            if config.get('auto_restart_on_mistake') and len(observed) <= self.lesson().get('attack_limit', 6000):
                self.restart_matcher.feed(observed[self.restart_matcher.count:])
                if (self.restart_matcher.mistaken and not notes_down and not self.recorder.error
                        and not any(e.get('kind') == 'capture_loss' for e in events)):
                    self.restart_take(self.active['id'], automatic=True)
                    return
            if not config['auto_finish']:
                return
            if len(observed) < self.minimum_attacks:
                return
            if len(observed) != self.last_count:
                self.last_count = len(observed)
                self.last_evaluation = evaluate(self.lesson(), self.active['target'], observed, self.active['target']['variants'])
                self.completion_at = time.monotonic() if self.last_evaluation['passed'] else None
            if self.completion_at and not notes_down and time.monotonic()-self.completion_at >= 1.5:
                self.finish()
