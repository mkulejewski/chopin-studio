"""Conservative symbolic candidate retrieval, independent of capture and Learning."""

import json
import statistics
from collections import Counter, defaultdict
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
from .performance import groups, melody, grams

VERSION = "symbolic-edit-v8-traversal-evidence-experimental"


class Recognizer:
    def __init__(self, references, navigation=False):
        self.references = []
        self.index = defaultdict(set)
        self.short_index = defaultdict(set)
        self.navigation = navigation
        for reference in references:
            if reference["quality"] == "rejected":
                continue
            row = dict(reference)
            notes = (
                json.loads(row["notes"])
                if isinstance(row["notes"], str)
                else row["notes"]
            )
            row["note_data"] = notes
            row["groups"] = groups(notes, tolerance=0.0001)
            row["melody"] = melody(row["groups"])
            row["grams"] = grams(row["melody"])
            index = len(self.references)
            for gram in row["grams"]:
                self.index[gram].add(index)
            for gram in grams(row["melody"], 2):
                self.short_index[gram].add(index)
            self.references.append(row)

    def match(self, notes, limit=5, edges=True):
        query_groups = groups(notes)
        query = melody(query_groups)
        if len(query) < 6:
            return {
                "label": "Unknown piece",
                "confidence": 0,
                "candidates": [],
                "version": VERSION,
            }
        votes = Counter()
        for gram, count in grams(query).items():
            for index in self.index.get(gram, ()):
                votes[index] += count
        # Four-note exact fingerprints alone miss phrases with frequent errors.
        # Short fingerprints broaden retrieval; final pitch/chord gates still
        # decide identity. Never restrict an unindexed phrase to the first works.
        short_votes = Counter()
        for gram, count in grams(query, 2).items():
            for index in self.short_index.get(gram, ()):
                short_votes[index] += count
        candidates = list(dict.fromkeys(
            [i for i, _ in votes.most_common(12)]
            + [i for i, _ in short_votes.most_common(12)]
        ))
        if not candidates:
            candidates = list(range(len(self.references)))
        results = []
        for index in candidates:
            reference = self.references[index]
            alignment = fuzz.partial_ratio_alignment(query, reference["melody"])
            if not alignment:
                continue
            qs, qe = alignment.src_start, alignment.src_end
            start, end = alignment.dest_start, alignment.dest_end
            rg = reference["groups"][start:end]
            if not rg:
                continue
            # Exact-pitch chord overlap provides independent polyphonic evidence.
            opcodes = Levenshtein.opcodes(query[qs:qe], reference["melody"][start:end])
            pairs = []
            for op in opcodes:
                if op.tag in ("equal", "replace"):
                    for offset in range(
                        min(op.src_end - op.src_start, op.dest_end - op.dest_start)
                    ):
                        pairs.append(
                            (qs + op.src_start + offset, start + op.dest_start + offset)
                        )
            overlaps = [
                len(query_groups[a]["pitches"] & reference["groups"][b]["pitches"])
                / max(
                    1,
                    len(query_groups[a]["pitches"] | reference["groups"][b]["pitches"]),
                )
                for a, b in pairs
            ]
            poly = statistics.mean(overlaps) if overlaps else 0
            similarity = 0.75 * alignment.score / 100 + 0.25 * poly
            identity_similarity = similarity
            if reference["quality"] != "verified" and not self.navigation:
                similarity = min(0.84, similarity)
            result = {
                "piece_id": reference["piece_id"],
                "reference_id": reference["id"],
                "confidence": round(similarity, 4),
                "identity_similarity": round(identity_similarity, 4),
                "query_coverage": (qe - qs) / len(query),
                "latest_matched": qe == len(query),
                "first_measure": rg[0].get("measure"),
                "last_measure": rg[-1].get("measure"),
                "reference_start": start,
                "reference_end": end,
                "quality": reference["quality"],
                "melody_similarity": alignment.score / 100,
                "polyphonic_overlap": poly,
                "pairs": pairs,
            }
            # Multiple exact full-phrase locations can establish identity but
            # cannot establish a measure, even within one edition.
            locations = []
            offset = 0
            signature = reference["melody"][start:end]
            while (
                len(signature) >= 6
                and (qe - qs) / len(query) >= 0.8
                and alignment.score >= 85
            ):
                found = reference["melody"].find(signature, offset)
                if found < 0:
                    break
                overlap = (
                    statistics.mean(
                        len(
                            query_groups[a]["pitches"]
                            & reference["groups"][found + b - start]["pitches"]
                        )
                        / max(
                            1,
                            len(
                                query_groups[a]["pitches"]
                                | reference["groups"][found + b - start]["pitches"]
                            ),
                        )
                        for a, b in pairs
                    )
                    if pairs
                    else 0
                )
                if overlap >= 0.8:
                    locations.append(found)
                offset = found + 1
            result["location_ambiguous"] = len(locations) > 1
            result["alternative_locations"] = [
                {
                    "reference_start": i,
                    "first_measure": reference["groups"][i]["measure"],
                }
                for i in locations[:16]
            ]
            if len(query) < 8 and (
                len(set(query)) < 4
                or alignment.score < 95
                or poly < 0.8
                or qe - qs != len(query)
            ):
                continue
            results.append(result)
        # Competing editions of the same work are not competing piece identities.
        unique = {}
        for result in sorted(results, key=lambda x: (-x["identity_similarity"], x["quality"] != "verified")):
            unique.setdefault(result["piece_id"], result)
        results = sorted(unique.values(), key=lambda x: -x["identity_similarity"])[:limit]
        best = results[0] if results else None
        margin = (
            (best["identity_similarity"] - results[1]["identity_similarity"])
            if len(results) > 1
            else (best["identity_similarity"] if best else 0)
        )
        if (
            not best
            or best["confidence"] < 0.65
            or margin < (0.08 if len(query) < 8 else 0.035)
        ):
            return {
                "label": "Unknown piece"
                if not best or best["confidence"] < 0.65
                else "Ambiguous match",
                "confidence": best["confidence"] if best else 0,
                "candidates": results,
                "version": VERSION,
            }
        # Whole-take partial alignment may prefer a later passage over a free
        # introduction. Preserve independent edge evidence without inventing
        # alignment pairs or changing completeness/assessment coverage.
        if edges and len(query_groups) > 64:
            selected = [r for r in self.references if r["id"] == best["reference_id"]]
            edge_recognizer = Recognizer(selected, navigation=self.navigation)
            for side, subset in [
                ("opening", query_groups[:48]),
                ("ending", query_groups[-48:]),
            ]:
                excerpt = [notes[i] for g in subset for i in g["indices"]]
                edge = edge_recognizer.match(excerpt, edges=False)
                if (
                    edge.get("piece_id") == best["piece_id"]
                    and edge["confidence"] >= 0.65
                    and edge.get("query_coverage", 0) >= 0.8
                ):
                    best[side + "_evidence"] = {
                        k: edge.get(k)
                        for k in (
                            "confidence",
                            "first_measure",
                            "last_measure",
                            "reference_start",
                            "reference_end",
                        )
                    }
                    if side == "opening":
                        best["first_measure"] = edge["first_measure"]
                    else:
                        best["last_measure"] = edge["last_measure"]
            # A single partial-ratio window drops the beginning of an ornamented
            # full performance. Independent local windows establish its span;
            # align that span once, retaining insertions and wrong notes.
            extended = edge_recognizer._span_alignment(notes, query_groups, best)
            if extended:
                best.update(extended)
        return {
            **best,
            "label": "Identified"
            if best["confidence"] >= 0.9 and margin >= 0.08
            else "Probable match · review suggested",
            "candidates": results,
            "version": VERSION,
        }

    def _span_alignment(self, notes, played, match):
        reference = self.references[0]
        rg = reference["groups"]
        windows = []
        offsets = sorted(set([*range(0, len(played) - 23, 32), max(0, len(played) - 32)]))
        for offset in offsets:
            subset = played[offset:offset + 32]
            local = self.match([notes[i] for g in subset for i in g["indices"]], edges=False)
            if (local.get("piece_id") and local["confidence"] >= 0.7
                    and local.get("query_coverage", 0) >= 0.8
                    and not local.get("location_ambiguous")):
                windows.append((offset, local))
        if len(windows) < 3:
            return None
        # A backward score jump is a separate traversal. Do not turn the union
        # of two partial attempts into one complete performance.
        if any(b["reference_start"] + 16 < a["reference_start"]
               for (_, a), (_, b) in zip(windows, windows[1:])):
            return None
        first_offset, first = windows[0]
        last_offset, last = windows[-1]
        if first_offset > 32 or last_offset + 64 < len(played):
            return None
        # Never extrapolate missing score notes from unmatched input. Extra
        # lead-ins/tails do not prove that the opening or ending was played.
        start = first["reference_start"]
        end = last["reference_end"]
        if end <= start or not 0.5 <= len(played) / (end - start) <= 1.75:
            return None
        query = melody(played)
        target = reference["melody"][start:end]
        pairs = [(op.src_start + k, start + op.dest_start + k)
                 for op in Levenshtein.opcodes(query, target)
                 if op.tag in ("equal", "replace")
                 for k in range(min(op.src_end-op.src_start, op.dest_end-op.dest_start))]
        overlap = statistics.mean(
            len(played[a]["pitches"] & rg[b]["pitches"])
            / len(played[a]["pitches"] | rg[b]["pitches"])
            for a, b in pairs
        ) if pairs else 0
        similarity = 0.75 * fuzz.ratio(query, target) / 100 + 0.25 * overlap
        if reference["quality"] != "verified" and not self.navigation:
            similarity = min(0.84, similarity)
        if similarity < 0.7 or overlap < 0.5:
            return None
        first_anchor = first_offset + min(a for a, _ in first["pairs"])
        last_anchor = last_offset + max(a for a, _ in last["pairs"])
        return dict(reference_start=start, reference_end=end, pairs=pairs,
                    first_measure=rg[start].get("measure"), last_measure=rg[end-1].get("measure"),
                    query_coverage=(last_anchor-first_anchor+1)/len(played),
                    latest_matched=last_anchor == len(played)-1,
                    confidence=round(similarity, 4), polyphonic_overlap=overlap,
                    melody_similarity=fuzz.ratio(query, target)/100,
                    alignment_method="window-supported-monotonic-span", supporting_windows=len(windows))
