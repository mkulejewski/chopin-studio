"""Pure activity bounds, completeness and conservative restart detection."""

import statistics
from collections import defaultdict
from rapidfuzz.distance import Levenshtein
from .performance import groups, melody
from .recognition import Recognizer


def likely_complete(match, reference_groups):
    """A timeline label for broad coverage, independent of assessment eligibility."""
    total = len(reference_groups)
    if (
        total < 8
        or match.get("location_ambiguous")
        or match.get("confidence", 0) < 0.75
    ):
        return False
    start = match.get("reference_start", 0)
    end = match.get("reference_end", 0)
    covered = len({b for _, b in match.get("pairs", [])}) / total
    return (
        start / total <= 0.10
        and end / total >= 0.90
        and (end - start) / total >= 0.85
        and covered >= 0.75
        and match.get("query_coverage", 0) >= 0.70
    )


def candidate_ranges(notes, duration, cooldown=20, recognizer=None):
    if not notes:
        return []
    onsets = sorted(set(n["onset"] for n in notes))
    intervals = [b - a for a, b in zip(onsets, onsets[1:]) if 0.08 < b - a < 3]
    median = statistics.median(intervals) if intervals else 0.5
    threshold = max(cooldown, min(30, median * 16))
    starts = [notes[0]["onset"]]
    ranges = []
    held_until = notes[0]["onset"] + notes[0]["duration"]
    for index, (previous, current) in enumerate(zip(notes, notes[1:])):
        # A candidate silence boundary remains explicitly uncertain: held notes and
        # Chopin pauses are not proof of a change of work.
        gap = current["onset"] - held_until
        contextual_change = False
        if recognizer and 3 <= gap < threshold:
            # A shorter rest is a piece boundary only when both sides provide
            # independent identity evidence. A fermata within a work stays intact.
            before = groups(notes[: index + 1])[-48:]
            after = groups(notes[index + 1 :])[:48]
            left = recognizer.match(
                [notes[i] for g in before for i in g["indices"]], edges=False
            )
            tail = notes[index + 1 :]
            right = recognizer.match(
                [tail[i] for g in after for i in g["indices"]], edges=False
            )
            contextual_change = bool(
                left.get("piece_id")
                and right.get("piece_id")
                and left["piece_id"] != right["piece_id"]
                and min(left["confidence"], right["confidence"]) >= 0.65
                and min(left.get("query_coverage", 0), right.get("query_coverage", 0))
                >= 0.8
            )
        if gap >= threshold or contextual_change:
            ranges.append(
                (
                    starts[-1],
                    min(duration, max(previous["onset"] + 0.2, held_until)),
                    True,
                )
            )
            starts.append(current["onset"])
        held_until = max(held_until, current["onset"] + current["duration"])
    ranges.append(
        (
            starts[-1],
            min(duration, max(n["onset"] + n["duration"] for n in notes) + 0.25),
            False,
        )
    )
    return ranges


def opening_restarts(notes, recognizer, match):
    """Find repeated opening attempts, withholding ambiguous written repeats.

    Six opening groups give short abandoned starts enough evidence without
    treating every backward jump in a recurring theme as a new performance.
    """
    reference = next(
        (r for r in recognizer.references if r["id"] == match.get("reference_id")), None
    )
    if not reference or match.get("confidence", 0) < 0.7:
        return []
    rg = reference["groups"]
    played = groups(notes)
    if len(rg) < 24 or len(played) < 12:
        return []
    signature = reference["melody"][:6]
    query = melody(played)
    # A written recurrence near the opening cannot establish an aborted run.
    if any(
        Levenshtein.normalized_similarity(signature, reference["melody"][i : i + 6])
        >= 0.8
        for i in range(6, max(6, len(rg) // 4))
    ):
        return []

    def opening(index):
        if played[index]["pitches"] != rg[0]["pitches"]:
            return False
        for size in range(6, 10):
            fragment = query[index : index + size]
            if (
                len(fragment) != size
                or Levenshtein.normalized_similarity(fragment, signature) < 0.8
            ):
                continue
            pairs = [
                (index + op.src_start + k, op.dest_start + k)
                for op in Levenshtein.opcodes(fragment, signature)
                if op.tag in ("equal", "replace")
                for k in range(
                    min(op.src_end - op.src_start, op.dest_end - op.dest_start)
                )
            ]
            overlap = statistics.mean(
                len(played[a]["pitches"] & rg[b]["pitches"])
                / len(played[a]["pitches"] | rg[b]["pitches"])
                for a, b in pairs
            )
            if overlap >= 0.65:
                return True
        return False

    if not opening(0):
        return []
    cuts = []
    start = 0
    local = Recognizer([reference])
    for index in range(6, len(played) - 5):
        if index - start < 6 or not opening(index):
            continue
        excerpt = [notes[j] for g in played[start:index] for j in g["indices"]]
        prior = local.match(excerpt, edges=False)
        # Very short attempts are supported by the opening signature itself.
        short = index - start < 8
        if not short and not (
            prior.get("piece_id") == reference["piece_id"]
            and prior["confidence"] >= 0.7
            and prior.get("query_coverage", 0) >= 0.8
            and prior.get("reference_start", len(rg)) <= 6
            and prior.get("reference_end", len(rg)) <= len(rg) * 0.25
        ):
            continue
        cuts.append(played[index]["onset"])
        start = index
    return cuts


def passage_restarts(notes, recognizer, match):
    """Split short mid-piece retries only with unique exact chord context."""
    played = groups(notes)
    reference = next(
        (r for r in recognizer.references if r["id"] == match.get("reference_id")), None
    )
    if not reference:
        head = recognizer.match(
            [notes[j] for g in played[:6] for j in g["indices"]], edges=False
        )
        tail = recognizer.match(
            [notes[j] for g in played[-6:] for j in g["indices"]], edges=False
        )
        if not head.get("piece_id") or head.get("piece_id") != tail.get("piece_id"):
            return []
        reference = next(
            (r for r in recognizer.references if r["id"] == head.get("reference_id")),
            None,
        )
    if not reference:
        return []
    rg = reference["groups"]
    size = 6
    signatures = defaultdict(list)
    for i in range(len(rg) - size + 1):
        signatures[tuple(tuple(sorted(g["pitches"])) for g in rg[i : i + size])].append(
            i
        )
    previous = None
    start_index = 0
    cuts = []
    for i in range(len(played) - size + 1):
        key = tuple(tuple(sorted(g["pitches"])) for g in played[i : i + size])
        locations = signatures.get(key, [])
        if len(locations) != 1:
            continue
        position = locations[0]
        if previous is not None:
            pi, pr = previous
            # Opening returns remain governed by the dedicated written-repeat
            # checks above. A mid-piece retry must move backward after at least
            # six attacks, within a short continuous attempt.
            if (
                position > 0
                and i - start_index >= size
                and i - pi <= size
                and position < pr + (i - pi) - 3
                and i - start_index <= 64
            ):
                cuts.append(played[i]["onset"])
                start_index = i
        previous = (i, position)
    return cuts


def performance_restarts(notes, recognizer, match):
    """Detect full takes and later aborted runs returning to the opening.

    Both sides need independent score evidence. Written theme returns remain
    intact when the surrounding notes match a continuous passage of the score.
    """
    reference = next((r for r in recognizer.references
                      if r["id"] == match.get("reference_id")), None)
    if not reference or match.get("confidence", 0) < 0.7:
        return []
    played = groups(notes)
    rg = reference["groups"]
    if len(rg) < 24 or len(played) < 24:
        return []
    local = Recognizer([reference])
    query = melody(played)
    signature = reference["melody"][:12]
    cuts = []
    last_cut = 0
    for index in range(12, len(played) - 11):
        if index - last_cut < 12:
            continue
        # Cheap proposal gate, tolerant of a wrong opening note/chord.
        if Levenshtein.normalized_similarity(query[index:index+12], signature) < 0.75:
            continue
        first_overlap = len(played[index]["pitches"] & rg[0]["pitches"]) / len(played[index]["pitches"] | rg[0]["pitches"])
        if first_overlap < 0.65:
            continue
        after = [notes[j] for g in played[index:index+32] for j in g["indices"]]
        right = local.match(after, edges=False)
        if (not right.get("piece_id") or right["confidence"] < 0.7
                or right.get("query_coverage", 0) < 0.8
                or right.get("reference_start", 99) > 3
                or right.get("location_ambiguous")):
            continue
        # Mistakes immediately before abandoning a take must not erase the
        # preceding independently recognised progress. Keep a bounded lookback.
        preceding = []
        for end in range(index, max(last_cut+23, index-96), -16):
            before = [notes[j] for g in played[max(last_cut, end-32):end] for j in g["indices"]]
            left = local.match(before, edges=False)
            if (left.get("piece_id") and left["confidence"] >= 0.7
                    and left.get("query_coverage", 0) >= 0.75):
                preceding.append(left)
        if not preceding:
            continue
        # The old detector covered only the first quarter. Here a substantial
        # backward jump or an ending-to-opening return proposes a new take.
        if max(left.get("reference_end", 0) for left in preceding) < max(24, min(96, len(rg)*0.2)):
            continue
        context = [notes[j] for g in played[max(last_cut, index-16):index+16] for j in g["indices"]]
        continuous = local.match(context, edges=False)
        if (continuous.get("piece_id") and continuous["confidence"] >= 0.8
                and continuous.get("query_coverage", 0) >= 0.95
                and continuous.get("polyphonic_overlap", 0) >= 0.8):
            continue
        cuts.append(played[index]["onset"])
        last_cut = index
    return cuts
