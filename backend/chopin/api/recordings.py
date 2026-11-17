"""Retained recording inventory, choices and explicit deletion HTTP routes."""

import json

from fastapi import APIRouter, HTTPException

from .context import PracticeContext
from .models import DeleteRecording, RecordingChoice


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    jobs = context.jobs
    session = context.session
    segment = context.segment
    deletion_ready = context.deletion_ready

    @app.get("/api/recordings")
    def recordings():
        from ..retention import catalogue, rendered_assets, session_audio_bytes

        # File inventory and job payload decoding must not be repeated for every
        # session. Total artifact sizes are unused by the audio cleanup screen.
        takes = catalogue(store)
        with store.lock:
            sessions = store.query("SELECT * FROM sessions ORDER BY started DESC")
            locked_sessions = {
                row["session_id"]
                for row in store.query(
                    "SELECT DISTINCT session_id FROM recording_deletions WHERE scope='recording'"
                )
            }
            segments = store.query("SELECT id,session_id FROM segments")
            renders = rendered_assets(store)
        grouped = {}
        for row in segments:
            grouped.setdefault(row["session_id"], []).append(row["id"])
        for record in sessions:
            record["timeline_locked"] = record["id"] in locked_sessions
            record["audio_bytes"] = session_audio_bytes(
                store, record["id"], renders, grouped.get(record["id"], [])
            )
        return {
            "takes": takes,
            "sessions": sessions,
            "policy": "Keep audio for the two best comparable complete takes per piece using notes, local timing, written dynamics and available recording/voicing evidence. Missing evidence, incompatible comparisons and boundary ties retain audio for review; recency does not select winners. MIDI is kept indefinitely. Flagged audio is removed at shutdown; Keep flags protect any take. Inaudible-piano microphone cleanup remains a separate policy.",
        }

    @app.get("/api/recordings/library")
    def recordings_library():
        # Availability follows retained microphone spans and existing rendered files,
        # never metadata alone. Cache file layouts once per session.
        import soundfile as sf

        from ..microphone import audio_layout
        from ..retention import audio_assets, rendered_assets

        with store.lock:
            sessions = store.query("""SELECT s.*,a.piece_id AS learning_piece_id
                FROM sessions s LEFT JOIN learning_attempts a ON a.session_id=s.id
                WHERE s.status IN ('saved','imported','recovered','incomplete')
                ORDER BY s.started DESC,s.id DESC""")
            segments = store.query("""SELECT s.id,s.session_id,s.piece_id,s.start,s.end,s.kind,s.discarded
                FROM segments s JOIN sessions ps ON ps.id=s.session_id
                WHERE ps.status IN ('saved','imported','recovered','incomplete')
                AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id
                    AND d.scope='recording') ORDER BY s.start,s.id""")
            segmented = {
                r["session_id"]
                for r in store.query("SELECT DISTINCT session_id FROM segments")
            }
            renders = rendered_assets(store)
            render_urls = {}
            for job in store.query(
                "SELECT id,result FROM jobs WHERE kind='render' AND status='done' AND result IS NOT NULL"
            ):
                result = json.loads(job["result"])
                if isinstance(result, dict) and result.get("filename"):
                    render_urls[result["filename"]] = "/api/audio/" + job["id"]
            layouts, rates = {}, {}
            for session in sessions:
                ident = session["id"]
                try:
                    layouts[ident] = audio_layout(store.root / "sessions" / ident)
                    path, _ = layouts[ident]
                    if path:
                        rates[ident] = sf.info(path).samplerate
                except (OSError, RuntimeError, ValueError):
                    layouts[ident] = (None, [])
                path, spans = layouts[ident]
                session["audio_sources"] = (
                    [
                        {
                            "label": "Recorded microphone",
                            "url": f"/api/sessions/{ident}/microphone",
                        }
                    ]
                    if ident not in segmented
                    and path
                    and any(span["frames"] > 0 for span in spans)
                    else []
                )
            available = []
            for row in segments:
                microphone, files = audio_assets(
                    store,
                    row,
                    layouts[row["session_id"]],
                    renders,
                    rates.get(row["session_id"]),
                )
                sources = (
                    [
                        {
                            "label": "Recorded microphone",
                            "url": f"/api/segments/{row['id']}/microphone",
                        }
                    ]
                    if microphone
                    else []
                )
                sources += [
                    {"label": "Rendered MIDI audio", "url": render_urls[path.name]}
                    for path in files
                ]
                if sources:
                    available.append({**row, "audio_sources": sources})
            audible_sessions = {row["session_id"] for row in available}
            sessions = [
                s for s in sessions if s["id"] in audible_sessions or s["audio_sources"]
            ]
        return {"sessions": sessions, "segments": available}

    @app.put("/api/recordings/{ident}")
    def recording_choice(ident: str, body: RecordingChoice):
        from ..retention import audio_assets

        with store.lock:
            row = segment(ident)
            microphone, files = audio_assets(store, row)
            if not microphone and not files:
                raise ValueError(
                    "This take has no saved audio to flag. MIDI is retained indefinitely."
                )
            if body.complete is not None:
                row = {
                    **row,
                    "complete": int(body.complete),
                    "kind": "complete" if body.complete else "partial",
                }
            if body.complete is not None:
                store.execute(
                    "UPDATE segments SET complete=?,kind=?,revision=revision+1 WHERE id=?",
                    (row["complete"], row["kind"], ident),
                )
            store.execute(
                "INSERT INTO recording_choices(segment_id,choice) VALUES(?,?) ON CONFLICT(segment_id) DO UPDATE SET choice=excluded.choice",
                (ident, body.choice),
            )
            if body.complete is not None:
                jobs.analysis(segment(ident))
        return {"ok": True}

    @app.delete(
        "/api/recordings/{ident}"
    )  # Compatibility: cleanup is now always audio-only.
    @app.delete("/api/recordings/{ident}/audio")
    def remove_take(ident: str, body: DeleteRecording):
        from ..retention import delete_take

        with store.lock:
            deletion_ready()
            row = segment(ident)
            if body.revision != row["revision"]:
                raise HTTPException(409, "Recording changed. Refresh before deleting.")
            delete_take(store, row)
        return {"ok": True}

    @app.delete("/api/sessions/{ident}")
    def remove_session(ident: str, body: DeleteRecording):
        from ..retention import delete_session

        with store.lock:
            deletion_ready()
            session(ident)
            delete_session(store, ident)
        return {"ok": True}

    return app
