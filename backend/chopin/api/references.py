"""Organisation, reference quality, jobs and live-following HTTP boundaries."""

import json
import math
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..symbolic import import_reference, reference_info
from ..organisation import performance_notes
from ..midi_files import journal_events
from ..extraction import segment_midi


from fastapi import APIRouter
from .context import PracticeContext
from .models import ReferenceUpdate, PageMap


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    live = context.live
    save_upload = context.save_upload
    segment = context.segment

    @app.get("/api/pieces/{ident}/references")
    def references(ident: str):
        return reference_info(store, ident)

    @app.get("/api/pieces/{ident}/sessions")
    def piece_sessions(ident: str, include_flagged: bool = False):
        if not store.query("SELECT id FROM pieces WHERE id=?", (ident,)):
            raise HTTPException(404, "Piece not found")
        with store.lock:
            rows = store.query(
                """SELECT DISTINCT ps.* FROM sessions ps
                JOIN segments s ON s.session_id=ps.id
                WHERE s.piece_id=? AND s.discarded=0 AND ps.status NOT IN ('recording','saving','recovery_failed')
                ORDER BY ps.started DESC,ps.id DESC""",
                (ident,),
            )
            segments = store.query(
                """SELECT s.* FROM segments s JOIN sessions ps ON ps.id=s.session_id
                WHERE s.piece_id=? AND s.discarded=0 AND ps.status NOT IN ('recording','saving','recovery_failed')
                ORDER BY s.start,s.id""",
                (ident,),
            )
        from ..retention import catalogue

        decisions = (
            {take["id"]: take for take in catalogue(store, piece_id=ident)}
            if segments
            else {}
        )
        segments = [
            {
                **item,
                "audio_retention_action": decisions.get(item["id"], {}).get("action"),
            }
            for item in segments
        ]
        grouped = {}
        for item in segments:
            grouped.setdefault(item["session_id"], []).append(item)
        return [
            {**row, "segments": grouped[row["id"]]}
            for row in rows
            if row["id"] in grouped
        ]

    @app.post("/api/pieces/{ident}/references")
    async def reference_import(ident: str, file: UploadFile):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in (".musicxml", ".xml", ".mxl"):
            raise ValueError("Choose MusicXML, XML or MXL")
        path = await save_upload(file, store.root / "imports", suffix)
        try:
            ref = import_reference(store, ident, path.read_bytes(), suffix)
        except Exception as exc:
            raise ValueError("Reference import failed: " + str(exc)) from exc
        finally:
            path.unlink(missing_ok=True)
        live.signature = None
        return {"id": ref}

    @app.get("/api/references/{ident}")
    def reference(ident: str):
        row = store.query("SELECT * FROM symbolic_scores WHERE id=?", (ident,))
        if not row:
            raise HTTPException(404, "Reference not found")
        return {**row[0], "notes": json.loads(row[0]["notes"])}

    @app.get("/api/references/{ident}/musicxml")
    def reference_download(ident: str):
        ref = reference(ident)
        if not ref["filename"].endswith(".musicxml"):
            raise ValueError(
                "This reference is a labelled MIDI performance, not MusicXML"
            )
        return FileResponse(
            store.root / "references" / ref["filename"],
            media_type="application/vnd.recordare.musicxml+xml",
            filename=ref["piece_id"] + ".musicxml",
        )

    @app.put("/api/references/{ident}")
    def edit_reference(ident: str, update: ReferenceUpdate):
        ref = reference(ident)
        if update.quality == "verified" and not ref["filename"].endswith(".musicxml"):
            raise ValueError("A labelled MIDI reference cannot be verified as a score")
        notes = ref["notes"] if update.notes is None else update.notes
        if not notes or len(notes) > 100000:
            raise ValueError("Reference must contain 1–100,000 notes")
        for n in notes:
            if (
                not isinstance(n.get("pitch"), int)
                or not 0 <= n["pitch"] <= 127
                or not isinstance(n.get("onset"), (int, float))
                or not math.isfinite(n["onset"])
                or n["onset"] < -1024
            ):
                raise ValueError(
                    "Every note needs a MIDI pitch and finite score onset (pickup beats may be negative)"
                )
            if (
                not isinstance(n.get("duration"), (int, float))
                or not math.isfinite(n["duration"])
                or n["duration"] < 0
                or not isinstance(n.get("measure"), int)
            ):
                raise ValueError("Every note needs a duration and integer measure")
        notes.sort(key=lambda n: (n["onset"], n["pitch"]))
        # Revision copy preserves former reference evidence; the XML download is
        # the original source, while the corrected analysis representation is JSON.
        if update.notes is not None:
            (
                store.root
                / "references"
                / (ident + ".previous-" + uuid.uuid4().hex + ".json")
            ).write_text(json.dumps(ref["notes"]))
        store.execute(
            "UPDATE symbolic_scores SET quality=?,edition=?,notes=? WHERE id=?",
            (update.quality, update.edition, json.dumps(notes), ident),
        )
        live.signature = None
        return {"ok": True}

    @app.get("/api/pieces/{ident}/pages")
    def pages(ident: str):
        return store.query(
            "SELECT * FROM page_maps WHERE piece_id=? ORDER BY measure", (ident,)
        )

    @app.put("/api/pieces/{ident}/pages")
    def page_map(ident: str, mapping: list[PageMap]):
        piece = store.query(
            "SELECT p.*,v.pages AS pdf_pages FROM pieces p JOIN volumes v ON p.volume_id=v.id WHERE p.id=?",
            (ident,),
        )
        if not piece:
            raise ValueError("Unknown piece")
        if any(p.pdf_page > (piece[0]["pdf_pages"] or 0) for p in mapping):
            raise ValueError("Page map requires an imported PDF and valid page numbers")
        with store.lock:
            try:
                store.db.execute("DELETE FROM page_maps WHERE piece_id=?", (ident,))
                for item in mapping:
                    store.db.execute(
                        "INSERT INTO page_maps VALUES(?,?,?)",
                        (ident, item.measure, item.pdf_page),
                    )
                store.db.commit()
            except Exception:
                store.db.rollback()
                raise ValueError("Invalid page map; no links were changed")
        return {"ok": True}

    @app.post("/api/segments/{ident}/learn")
    def learn(ident: str):
        row = segment(ident)
        if not row["piece_id"]:
            raise ValueError("Assign a piece before saving a labelled MIDI reference")
        notes = performance_notes(
            journal_events(store.root / "sessions" / row["session_id"] / "events.jsonl")
        )
        notes = [
            {**n, "onset": n["onset"] - row["start"], "measure": None}
            for n in notes
            if row["start"] <= n["onset"] < row["end"]
        ]
        if len(notes) < 8:
            raise ValueError("At least eight notes are needed")
        ref = uuid.uuid4().hex
        # MIDI-reference seconds can retrieve identity, but never score measures.
        path = segment_midi(store, row)
        shutil.copyfile(path, store.root / "references" / (ref + ".mid"))
        store.execute(
            "INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)",
            (
                ref,
                row["piece_id"],
                ref + ".mid",
                "Locally confirmed segment " + ident,
                "Private user recording",
                "Labelled performance; no score-level measures",
                "provisional",
                json.dumps(notes),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        live.signature = None
        return {"id": ref}

    return app
