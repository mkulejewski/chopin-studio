"""Reproducible synthetic endpoint timings; never opens personal data or hardware.

Run from the repository root: .venv/bin/python scripts/profile_refactoring.py
JSON output includes workload sizes, query counts, elapsed time and Python peaks.
"""

import argparse
import cProfile
import json
import os
import random
import statistics
import tempfile
import time
import tracemalloc
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from chopin.analysis_selection import reference_identity
from chopin.app import create_app
from chopin.organisation import organise


def session(store, piece, notes, take):
    ident = uuid.uuid4().hex
    folder = store.root / "sessions" / ident
    folder.mkdir()
    events = []
    for i, note in enumerate(notes):
        events.extend(
            [
                {
                    "t": i * 0.5,
                    "message": {
                        "type": "note_on",
                        "channel": 0,
                        "note": note["pitch"],
                        "velocity": 80,
                    },
                },
                {
                    "t": i * 0.5 + 0.3,
                    "message": {
                        "type": "note_off",
                        "channel": 0,
                        "note": note["pitch"],
                        "velocity": 30,
                    },
                },
            ]
        )
    (folder / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    store.execute(
        "INSERT INTO sessions(id,name,started,status,duration,events) VALUES(?,?,?,?,?,?)",
        (
            ident,
            "Synthetic profile",
            f"2026-10-{take + 1:02d}T12:00:00+00:00",
            "saved",
            len(notes) * 0.5,
            len(events),
        ),
    )
    store.set_setting("organised:" + ident, True)
    segment = dict(
        id=uuid.uuid4().hex,
        session_id=ident,
        piece_id=piece,
        start=0,
        end=len(notes) * 0.5,
        revision=1,
        complete=1,
        discarded=0,
        label="Synthetic",
        kind="complete",
        confidence=1,
    )
    keys = list(segment)
    store.execute(
        "INSERT INTO segments("
        + ",".join(keys)
        + ") VALUES("
        + ",".join("?" for _ in keys)
        + ")",
        tuple(segment.values()),
    )
    return segment


def measure(store, action, repeats):
    timings = []
    queries = []
    peak = 0
    original = store.query
    for _ in range(repeats):
        count = 0

        def counted(*args, **kwargs):
            nonlocal count
            count += 1
            return original(*args, **kwargs)

        store.query = counted
        tracemalloc.start()
        start = time.perf_counter()
        try:
            value = action()
            timings.append(time.perf_counter() - start)
            if hasattr(value, "raise_for_status"):
                value.raise_for_status()
            peak = max(peak, tracemalloc.get_traced_memory()[1])
            queries.append(count)
        finally:
            store.query = original
            tracemalloc.stop()
    return {
        "seconds": timings,
        "median_seconds": statistics.median(timings),
        "queries": queries,
        "python_peak_bytes": peak,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--takes", type=int, default=12, choices=range(1, 29))
    parser.add_argument("--notes", type=int, default=2000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--cpu-profile", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="chopin-profile-") as folder:
        os.environ.update(
            CHOPIN_DATA_DIR=str(Path(folder) / "data"),
            XDG_STATE_HOME=str(Path(folder) / "state"),
            CHOPIN_NO_HARDWARE="1",
            CHOPIN_PORT="8772",
        )
        app = create_app(Path(folder) / "data", hardware=False)
        with TestClient(app) as client:
            store = app.state.store
            app.state.live.close()  # Exclude unrelated polling queries from endpoint counts.
            pieces = store.query("SELECT id FROM pieces ORDER BY id")
            long_segments = []
            with store.transaction():
                for index, piece in enumerate(pieces):
                    count = args.notes if index == 0 else 24
                    rng = random.Random(piece["id"])
                    notes = [
                        dict(
                            pitch=rng.randrange(48, 84),
                            onset=i,
                            duration=0.5,
                            measure=i // 4 + 1,
                            staff=1,
                            voice="1",
                        )
                        for i in range(count)
                    ]
                    reference_id = uuid.uuid4().hex
                    reference = dict(
                        id=reference_id,
                        notes=notes,
                        quality="verified",
                        edition="Synthetic profile",
                    )
                    store.execute(
                        "INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            reference_id,
                            piece["id"],
                            reference_id + ".musicxml",
                            "synthetic",
                            "Original synthetic fixture",
                            reference["edition"],
                            "verified",
                            json.dumps(notes),
                            "2026-11-16",
                        ),
                    )
                    for take in range(args.takes):
                        segment = session(store, piece["id"], notes, take)
                        if index == 0 and take < 2:
                            long_segments.append(segment)
                        result = dict(
                            reference_id=reference_id,
                            reference_revision=reference_identity(reference).revision,
                            notes=len(notes),
                            segment_snapshot={
                                k: segment[k]
                                for k in (
                                    "piece_id",
                                    "start",
                                    "end",
                                    "revision",
                                    "complete",
                                    "discarded",
                                )
                            },
                            passages=dict(
                                reference_id=reference_id,
                                reference_revision=reference_identity(
                                    reference
                                ).revision,
                                measures=[dict(measure=1, missing=0, extra=0)],
                                points=[],
                            ),
                            assessment=dict(piece_level="concert", precision_score=100),
                        )
                        store.execute(
                            "INSERT INTO analyses VALUES(?,?,?,?,?,?)",
                            (
                                uuid.uuid4().hex,
                                segment["session_id"],
                                segment["id"],
                                "synthetic",
                                f"2026-10-{take + 1:02d}",
                                json.dumps(result),
                            ),
                        )
            output = {
                "workload": {
                    "pieces": len(pieces),
                    "takes_per_piece": args.takes,
                    "long_take_notes": args.notes,
                    "long_take_seconds": args.notes * 0.5,
                }
            }
            from chopin.segment_analysis import analyse_segment

            if args.cpu_profile:
                profiler = cProfile.Profile()
                profiler.runcall(analyse_segment, store, long_segments[0])
                profiler.dump_stats(args.cpu_profile)
            else:
                analyse_segment(
                    store, long_segments[0]
                )  # Warm optional numerical imports equally.
            output["progress"] = measure(
                store, lambda: client.get("/api/progress"), args.repeats
            )
            if len(long_segments) == 2:
                output["comparison"] = measure(
                    store,
                    lambda: client.get(
                        "/api/comparison",
                        params={
                            "left": long_segments[0]["id"],
                            "right": long_segments[1]["id"],
                        },
                    ),
                    args.repeats,
                )
            output["organisation"] = measure(
                store,
                lambda: organise(store, long_segments[0]["session_id"], force=True),
                1,
            )
            print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
