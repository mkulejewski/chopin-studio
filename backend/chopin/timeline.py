"""Atomic timeline edits and undo, independent of HTTP and background jobs."""

import json
from datetime import datetime, timezone
from .retention import locked


class TimelineConflict(ValueError):
    """The caller must reload or unlock the timeline before changing it."""


def _rows(store, ident):
    return store.query(
        "SELECT * FROM segments WHERE session_id=? ORDER BY start", (ident,)
    )


def save_history(store, session_id):
    snapshot = store.query(
        "SELECT * FROM segments WHERE session_id=? ORDER BY start", (session_id,)
    )
    store.execute(
        "INSERT INTO segment_history(session_id,created,snapshot) VALUES(?,?,?)",
        (session_id, datetime.now(timezone.utc).isoformat(), json.dumps(snapshot)),
    )


def edit_timeline(store, record, segments, expected_revision):
    ident = record["id"]
    if locked(store, ident):
        raise TimelineConflict(
            "Removed intervals cannot be restored. This timeline is locked; completeness can still be changed in recording cleanup."
        )
    rows = _rows(store, ident)
    revision = max((r["revision"] for r in rows), default=0)
    if revision != expected_revision:
        raise TimelineConflict("Timeline changed. Reload before editing.")
    ordered = sorted(segments, key=lambda s: s["start"])
    for i, item in enumerate(ordered):
        if item["end"] <= item["start"] or item["end"] > record["duration"] + 0.001:
            raise ValueError("Bounds must be ordered and within the original recording")
        if i and item["start"] < ordered[i - 1]["end"]:
            raise ValueError("Timeline segments cannot overlap")
        if item["piece_id"] and not store.query(
            "SELECT id FROM pieces WHERE id=?", (item["piece_id"],)
        ):
            raise ValueError("Unknown piece")
        if (
            item["first_measure"] is not None
            and item["last_measure"] is not None
            and item["first_measure"] > item["last_measure"]
        ):
            raise ValueError("Measure range is reversed")
        owner = store.query("SELECT session_id FROM segments WHERE id=?", (item["id"],))
        if owner and owner[0]["session_id"] != ident:
            raise ValueError("Segment belongs to another session")
    with store.transaction():
        choices = store.query(
            "SELECT c.* FROM recording_choices c JOIN segments s ON s.id=c.segment_id WHERE s.session_id=?",
            (ident,),
        )
        protected = store.query(
            "SELECT s.start,s.end FROM segments s JOIN recording_choices c ON c.segment_id=s.id WHERE s.session_id=? AND c.choice='keep'",
            (ident,),
        )
        locked_revision = (
            store.db.execute(
                "SELECT MAX(revision) FROM segments WHERE session_id=?", (ident,)
            ).fetchone()[0]
            or 0
        )
        if locked_revision != expected_revision:
            raise TimelineConflict("Timeline changed. Reload before editing.")
        save_history(store, ident)
        store.db.execute("DELETE FROM segments WHERE session_id=?", (ident,))
        for item in ordered:
            fields = {**item, "session_id": ident, "revision": revision + 1}
            if item["kind"] == "full_exercise":
                fields["complete"] = True
            fields["details"] = json.dumps({"manual_correction": True})
            keys = list(fields)
            store.db.execute(
                "INSERT INTO segments("
                + ",".join(keys)
                + ") VALUES("
                + ",".join("?" for _ in keys)
                + ")",
                tuple(fields.values()),
            )
        for choice in choices:
            if any(item["id"] == choice["segment_id"] for item in ordered):
                store.db.execute(
                    "INSERT INTO recording_choices(segment_id,choice,deleted) VALUES(?,?,?)",
                    (choice["segment_id"], choice["choice"], choice["deleted"]),
                )
        for row in store.query(
            "SELECT id,start,end FROM segments WHERE session_id=?", (ident,)
        ):
            if any(
                min(row["end"], r["end"]) > max(row["start"], r["start"])
                for r in protected
            ):
                store.db.execute(
                    "INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep') ON CONFLICT(segment_id) DO UPDATE SET choice='keep'",
                    (row["id"],),
                )


def undo_timeline(store, ident):
    if locked(store, ident):
        raise TimelineConflict("Deleted recordings cannot be restored by undo.")
    with store.transaction():
        history = store.query(
            "SELECT * FROM segment_history WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (ident,),
        )
        if not history:
            raise ValueError("No timeline edit to undo")
        revision = max((r["revision"] for r in _rows(store, ident)), default=0) + 1
        protected = store.query(
            "SELECT s.start,s.end FROM segments s JOIN recording_choices c ON c.segment_id=s.id WHERE s.session_id=? AND c.choice='keep'",
            (ident,),
        )
        store.db.execute("DELETE FROM segments WHERE session_id=?", (ident,))
        for row in json.loads(history[0]["snapshot"]):
            row["revision"] = revision
            keys = list(row)
            store.db.execute(
                "INSERT INTO segments("
                + ",".join(keys)
                + ") VALUES("
                + ",".join("?" for _ in keys)
                + ")",
                tuple(row.values()),
            )
        for row in store.query(
            "SELECT id,start,end FROM segments WHERE session_id=?", (ident,)
        ):
            if any(
                min(row["end"], r["end"]) > max(row["start"], r["start"])
                for r in protected
            ):
                store.db.execute(
                    "INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",
                    (row["id"],),
                )
        store.db.execute("DELETE FROM segment_history WHERE id=?", (history[0]["id"],))
