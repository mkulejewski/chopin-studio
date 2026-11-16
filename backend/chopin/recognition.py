"""Conservative symbolic candidate retrieval, independent of capture and Learning."""

import json
import statistics
from collections import Counter, defaultdict
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
from .performance import groups, melody, grams

VERSION = "symbolic-edit-v7-passage-evidence-experimental"


class Recognizer:
    def __init__(self, references, navigation=False):
        self.references = []
        self.index = defaultdict(set)
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
        candidates = [i for i, _ in votes.most_common(8)]
        if not candidates:
            candidates = list(range(min(8, len(self.references))))
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
            if reference["quality"] != "verified" and not self.navigation:
                similarity = min(0.84, similarity)
            result = {
                "piece_id": reference["piece_id"],
                "reference_id": reference["id"],
                "confidence": round(similarity, 4),
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
        for result in sorted(results, key=lambda x: -x["confidence"]):
            unique.setdefault(result["piece_id"], result)
        results = sorted(unique.values(), key=lambda x: -x["confidence"])[:limit]
        best = results[0] if results else None
        margin = (
            (best["confidence"] - results[1]["confidence"])
            if len(results) > 1
            else (best["confidence"] if best else 0)
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
        return {
            **best,
            "label": "Identified"
            if best["confidence"] >= 0.9 and margin >= 0.08
            else "Probable match · review suggested",
            "candidates": results,
            "version": VERSION,
        }
