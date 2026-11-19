"""Packaged edition-bound lesson bundles, routine defaults and stage strategy."""

import json
from pathlib import Path
from functools import lru_cache

BUNDLE = Path(__file__).parent / "learning_data" / "aeolian_harp_etude_op25_no1.json"
BUNDLES = {
    "e25-1": BUNDLE,
    "p53": BUNDLE.with_name("heroic_polonaise_op53.json"),
    "n15-1": BUNDLE.with_name("nocturne_op15_no1.json"),
}
REVIEW_PAUSE_SECONDS = 2
HANDS = ("both", "right", "left")
HAND_LABELS = {"both": "both hands", "right": "right hand", "left": "left hand"}
PROGRESS_FIELDS = ("stage_index", "streak", "completed", "manual_advances")

DEFAULTS = {
    "visible": 3,
    "hidden": 3,
    "connections": 2,
    "auto_continue": True,
    "auto_finish": True,
    "auto_restart_on_mistake": False,
    "review_measure_retry": True,
}


@lru_cache(maxsize=4)
def lesson(piece_id="e25-1"):
    return json.loads(BUNDLES[piece_id].read_text())


def stages(chunks, bundle=None):
    result = []
    independent = bundle and bundle.get("connection_strategy") == "independent-sections"
    order = list(enumerate(chunks))
    if independent:
        # Coda acquisition runs backwards: final chunk first, then prepend the
        # previous chunk. Every connection still follows printed playing order.
        order = [
            item
            for section in bundle["section_order"]
            for item in sorted(
                (item for item in enumerate(chunks) if item[1]["section"] == section),
                key=lambda item: item[1]["start"],
                reverse=section in bundle.get("backward_sections", []),
            )
        ]
    learned = []
    for position, (i, chunk) in enumerate(order):
        base = {
            "chunk": i,
            "start": chunk["start"],
            "end": chunk["end"],
            "focus": chunk["focus"],
        }
        result.extend([{**base, "kind": "visible"}, {**base, "kind": "hidden"}])
        previous = [c for c in learned if c["section"] == chunk["section"]]
        if previous:
            result.append(
                {
                    **base,
                    "start": min([chunk["start"]] + [c["start"] for c in previous]),
                    "end": max([chunk["end"]] + [c["end"] for c in previous]),
                    "kind": "connection",
                }
            )
        learned.append(chunk)
        if not independent and (
            position == len(order) - 1
            or order[position + 1][1]["section"] != chunk["section"]
        ):
            if chunk["section"] != chunks[0]["section"]:
                result.append(
                    {**base, "start": chunks[0]["start"], "kind": "cumulative"}
                )
    if independent:
        for kind, passages in [
            ("transition", bundle.get("bridges", [])),
            ("assembly", bundle.get("assembly", [])),
        ]:
            for passage in passages:
                result.append(
                    {
                        **passage,
                        "kind": kind,
                        "chunk": next(
                            i
                            for i, c in enumerate(chunks)
                            if c["start"] <= passage["start"] <= c["end"]
                        ),
                    }
                )
    for index, stage in enumerate(result):
        stage["id"] = f"{index}:{stage['kind']}:{stage['start']}:{stage['end']}"
    return result
