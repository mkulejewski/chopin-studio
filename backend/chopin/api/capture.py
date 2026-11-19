"""Recording lifecycle, session inspection and original MIDI import/export routes."""

import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..imports import MIDI_SUFFIXES, import_midi_file
from ..midi_files import journal_events
from ..studio import ShutdownBlocked

log = logging.getLogger(__name__)


from fastapi import APIRouter

from .models import RecordingOptions


def router(studio, session_folder, save_upload):
    app = APIRouter()
    store, recorder, jobs = studio.store, studio.recorder, studio.jobs

    @app.post("/api/record/start")
    def start(options: RecordingOptions = RecordingOptions()):
        try:
            return {"id": studio.start_recording(**options.model_dump())}
        except ShutdownBlocked as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/record/stop")
    def stop():
        return {"id": studio.stop_recording()}

    @app.get("/api/sessions")
    def sessions():
        return store.query("""SELECT s.*,a.piece_id AS learning_piece_id,
            p.title AS learning_piece_title,p.opus AS learning_piece_opus
            FROM sessions s LEFT JOIN learning_attempts a ON a.session_id=s.id
            LEFT JOIN pieces p ON p.id=a.piece_id ORDER BY s.started DESC""")

    @app.get("/api/sessions/{ident}/microphone")
    def microphone_download(ident: str):
        folder = session_folder(ident)
        from ..microphone import audio_layout

        path, _ = audio_layout(folder)
        if recorder.active == ident or recorder.saving or path is None:
            raise HTTPException(409, "No finished microphone recording is available")
        return FileResponse(
            path, media_type="audio/flac", filename=ident + "__microphone.flac"
        )

    @app.get("/api/sessions/{ident}/recording")
    def recording_info(ident: str):
        from ..microphone import metadata
        from ..retention import locked

        return {
            "microphone": metadata(session_folder(ident)),
            "timeline_locked": locked(store, ident),
        }

    @app.get("/api/sessions/{ident}/midi")
    def download(ident: str):
        folder = session_folder(ident)
        if not (folder / "original.mid").exists():
            raise HTTPException(409, "Session has not finished saving")
        name = store.query("SELECT name FROM sessions WHERE id=?", (ident,))[0]["name"]
        return FileResponse(
            folder / "original.mid", media_type="audio/midi", filename=name + ".mid"
        )

    @app.get("/api/sessions/{ident}/summary")
    def summary(ident: str):
        folder = session_folder(ident)
        notes, pedals, markers = 0, [], []
        # Bound graph sampling; use online aggregation rather than retaining an entire session.
        bins = {}
        session = store.query("SELECT * FROM sessions WHERE id=?", (ident,))[0]
        width = max(1, session["duration"] / 240)
        active_seconds = set()
        for event in journal_events(folder / "events.jsonl"):
            msg = event.get("message", {})
            if msg.get("type") == "note_on" and msg.get("velocity", 0):
                notes += 1
                index = int(event["t"] / width)
                bucket = bins.setdefault(index, [0, 0, 127, 0])
                bucket[0] += msg["velocity"]
                bucket[1] += 1
                bucket[2] = min(bucket[2], msg["velocity"])
                bucket[3] = max(bucket[3], msg["velocity"])
                active_seconds.add(int(event["t"]))
            if msg.get("type") == "control_change" and msg.get("control") == 64:
                if len(pedals) < 2000:
                    pedals.append({"t": event["t"], "value": msg["value"]})
            if event.get("kind") and event["kind"] not in ("start", "stop"):
                if len(markers) < 1000:
                    markers.append(event)
        graph = [
            {
                "t": index * width,
                "mean": b[0] / b[1],
                "min": b[2],
                "max": b[3],
                "notes": b[1],
            }
            for index, b in sorted(bins.items())
        ]
        return {
            "version": 1,
            "notes": notes,
            "note_active_seconds": len(active_seconds),
            "velocity": graph,
            "pedals": pedals,
            "markers": markers,
            "pedals_truncated": len(pedals) == 2000,
            "notice": "Descriptive MIDI measurements only. No symbolic reference is aligned; accuracy, measures and musical quality are not evaluated.",
        }

    @app.post("/api/import/midi")
    async def import_midi(file: UploadFile):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in MIDI_SUFFIXES:
            raise ValueError("Choose a .mid, .midi or midicsv .csv file")
        original = await save_upload(file, store.root / "imports", suffix)
        ident = import_midi_file(store, original, file.filename or "recording")
        jobs.organise(ident)
        return {"id": ident}

    return app
