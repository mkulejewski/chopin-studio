"""Pure pitch partial-order evaluation; independent of Practice recognition.

Each staff orders attacks; chords are unordered. Only a complete zero-edit path
passes. Timing, velocity and provisional display projections do not grant passes.
"""

from fractions import Fraction
from .domain_types import LearningEvaluation, LearningRange
from .learning_definition import HANDS


def note_name(pitch):
    return ["C", "D♭", "D♮", "E♭", "E♮", "F", "G♭", "G", "A♭", "A♮", "B♭", "B♮"][
        pitch % 12
    ] + str(pitch // 12 - 1)


def reference_groups(bundle, start, end, variants=(), hand="both"):
    if hand not in HANDS:
        raise ValueError("Choose both, right or left hand.")
    rules = {v["note_id"]: v for v in variants}
    staves = [[], []]
    for m in bundle["measures"]:
        if not start <= m["number"] <= end:
            continue
        for staff, source in enumerate(m["staves"]):
            if (hand == "right" and staff != 0) or (hand == "left" and staff != 1):
                continue
            for index, (beat, pitches) in enumerate(source):
                notes = []
                for n, pitch in enumerate(pitches):
                    ident = f"m{m['number']}:s{staff + 1}:g{index}:n{n}"
                    rule = rules.get(ident)
                    if rule and rule["action"] == "omit":
                        continue
                    notes.append(
                        {
                            "id": ident,
                            "pitch": rule["pitch"] if rule else pitch,
                            "spelling": rule.get("spelling")
                            if rule
                            else m["spellings"][staff][index][n]
                            if m.get("spellings")
                            else None,
                            "original_pitch": pitch,
                            "measure": m["number"],
                            "staff": staff + 1,
                        }
                    )
                if notes:
                    staves[staff].append(
                        {"position": (m["number"], Fraction(beat)), "notes": notes}
                    )
    # Shared staff unisons are one physical key attack. Assign ownership once,
    # before alignment; otherwise flexible hand ordering could consume them twice.
    upper = {(g["position"], n["pitch"]) for g in staves[0] for n in g["notes"]}
    for g in staves[1]:
        g["notes"] = [n for n in g["notes"] if (g["position"], n["pitch"]) not in upper]
    staves[1] = [g for g in staves[1] if g["notes"]]
    return staves


def _choices(groups, state, staff):
    index, mask = state[staff * 2 : staff * 2 + 2]
    if index >= len(groups[staff]):
        return []
    return [
        (bit, note)
        for bit, note in enumerate(groups[staff][index]["notes"])
        if not mask & (1 << bit)
    ]


def _advance(groups, state, staff, bit):
    state = list(state)
    index, mask = state[staff * 2 : staff * 2 + 2]
    mask |= 1 << bit
    if mask == (1 << len(groups[staff][index]["notes"])) - 1:
        index += 1
        mask = 0
    state[staff * 2 : staff * 2 + 2] = index, mask
    return tuple(state)


def _consume(groups, state, staff, bit, note):
    return _advance(groups, state, staff, bit)


def ornament_position(bundle, groups, state, staff, pitch):
    index = state[staff * 2]
    for ornament in bundle.get("ornaments", []):
        if ornament.get("staff") != staff + 1 or pitch not in ornament.get(
            "pitches", []
        ):
            continue
        position = (ornament["measure"], Fraction(ornament.get("beat", 3)))
        if any(
            g["position"] == position
            for g in groups[staff][max(0, index - 1) : index + 1]
        ):
            return position
    return None


def ornament_allowed(bundle, groups, state, staff, pitch):
    return ornament_position(bundle, groups, state, staff, pitch) is not None


class PitchPrefixMatcher:
    """Bounded zero-edit paths, independent of the provisional staff display.

    Unplayed notes are never missing during a take. If ambiguous paths exceed
    the bound, decline automatic restarts for this take rather than guess.
    """

    def __init__(self, bundle, target, max_states=48):
        self.bundle = bundle
        self.groups = reference_groups(
            bundle,
            target["start"],
            target["end"],
            target.get("variants", []),
            target.get("hand", "both"),
        )
        self.states = {(0, 0, 0, 0)}
        self.count = 0
        self.uncertain = False
        self.max_states = max_states
        self.last_measure = target['start']
        self.mistake_measure = None

    @property
    def pending_measures(self):
        return {min(g['position'][0] for staff in (0, 1)
                    for g in self.groups[staff][state[staff * 2]:state[staff * 2] + 1])
                for state in self.states
                if any(state[s * 2] < len(self.groups[s]) for s in (0, 1))}

    @property
    def retake_measure(self):
        if self.uncertain:
            return None
        if self.mistaken:
            return self.mistake_measure
        measures = self.pending_measures
        if len(measures) > 1 or self.last_measure is None:
            return None
        if not measures:
            return self.last_measure
        measure = next(iter(measures))
        return measure if self.count == 0 else min(self.last_measure, measure)

    def feed(self, pitches):
        for pitch in pitches:
            self.count += 1
            if self.uncertain or not self.states:
                continue
            following = set()
            matched_measures = set()
            pending = self.pending_measures
            for state in self.states:
                for staff in (0, 1):
                    if ornament_allowed(self.bundle, self.groups, state, staff, pitch):
                        following.add(state)
                        matched_measures.add(ornament_position(self.bundle, self.groups, state, staff, pitch)[0])
                    for bit, note in _choices(self.groups, state, staff):
                        if note["pitch"] == pitch:
                            matched_measures.add(note['measure'])
                            following.add(
                                _consume(self.groups, state, staff, bit, note)
                            )
            if len(following) > self.max_states:
                self.uncertain = True
                self.states = set()
            else:
                if not following:
                    self.mistake_measure = next(iter(pending)) if len(pending) == 1 else self.last_measure if not pending else None
                else:
                    self.last_measure = next(iter(matched_measures)) if len(matched_measures) == 1 else None
                self.states = following

    @property
    def mistaken(self):
        return not self.uncertain and not self.states


def evaluate(bundle, target: LearningRange, observed, variants=(), beam_size=48) -> LearningEvaluation:
    if bundle.get("reference_status", "model-reviewed") not in (
        "model-reviewed",
        "human-reviewed",
    ):
        return {
            "passed": False,
            "uncertain": True,
            "errors": [],
            "error_count": 0,
            "notice": "The digital reference is provisional; automatic pitch judgement is unavailable.",
        }
    groups = reference_groups(
        bundle, target["start"], target["end"], variants, target.get("hand", "both")
    )
    total = len(observed)
    # Explicit limits yield uncertainty, never silently truncate the assignment.
    if total > bundle.get("attack_limit", 6000):
        return {
            "passed": False,
            "uncertain": True,
            "errors": [],
            "notice": "Attempt too long; finish and try a smaller chunk.",
        }
    initial = (0, 0, 0, 0)
    # Linked histories avoid copying an entire error list at every beam transition.
    beam = {initial: (0, None)}
    pruned = False
    for played_index, pitch in enumerate(observed):
        candidates = {}

        def offer(state, cost, history):
            old = candidates.get(state)
            if old is None or cost < old[0]:
                candidates[state] = (cost, history)

        for state, (cost, history) in beam.items():
            offer(
                state,
                cost + 1,
                (
                    history,
                    {"kind": "extra", "pitch": pitch, "played_index": played_index},
                ),
            )
            for staff in (0, 1):
                # Only an explicitly reviewed local ornament slot is flexible;
                # required printed attacks remain mandatory.
                if ornament_allowed(bundle, groups, state, staff, pitch):
                    offer(state, cost, history)
                frontier = [(state, 0, history)]
                for skip in range(3):
                    following = []
                    for cursor, skipped, trail in frontier:
                        for bit, note in _choices(groups, cursor, staff):
                            advanced = _consume(groups, cursor, staff, bit, note)
                            if note["pitch"] == pitch:
                                offer(advanced, cost + skipped, trail)
                            if skip < 2:
                                error = {"kind": "missing", **note}
                                following.append(
                                    (advanced, skipped + 1, (trail, error))
                                )
                    frontier = following
        ranked = sorted(
            candidates.items(), key=lambda item: (item[1][0], -sum(item[0][::2]))
        )
        if len(ranked) > beam_size and ranked[beam_size][1][0] == 0:
            pruned = True
        beam = dict(ranked[:beam_size])
    finals = []
    for state, (cost, history) in beam.items():
        remaining = []
        cursor = state
        for staff in (0, 1):
            while _choices(groups, cursor, staff):
                bit, note = _choices(groups, cursor, staff)[0]
                remaining.append({"kind": "missing", **note})
                cursor = _consume(groups, cursor, staff, bit, note)
        finals.append((cost + len(remaining), history, remaining))
    cost, history, remaining = min(finals, key=lambda item: item[0])
    errors = []
    while history:
        history, error = history
        errors.append(error)
    errors.reverse()
    errors.extend(remaining)
    for error in errors:
        spelling = error.get("spelling")
        error["name"] = (
            (
                spelling["step"]
                + {
                    -2: "♭♭",
                    -1: "♭",
                    0: "♮" if spelling["step"] in "BEAD" else "",
                    1: "♯",
                    2: "♯♯",
                }[spelling["alter"]]
                + str(spelling["octave"])
            )
            if spelling
            else note_name(error["pitch"])
        )
    passed = cost == 0 and total > 0
    return {
        "version": "learning-pitch-order-v1",
        "hand": target.get("hand", "both"),
        "passed": passed,
        "uncertain": pruned and not passed,
        "played_attacks": total,
        "errors": errors[:200],
        "error_count": len(errors),
        "errors_truncated": len(errors) > 200,
        "variant_count": sum(v.get("kind") != "correction" for v in variants),
        "correction_count": sum(v.get("kind") == "correction" for v in variants),
        "notice": "Complete passage recalled under your approved note rules."
        if passed
        else "Some ambiguous paths exceeded the matcher limit; review or use a smaller chunk."
        if pruned
        else "Review the note differences, then repeat the complete passage. Timing is not graded.",
    }
