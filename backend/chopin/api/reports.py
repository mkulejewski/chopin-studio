"""Organisation, reference quality, jobs and live-following HTTP boundaries."""

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.background import BackgroundTask


from fastapi import APIRouter
from .context import PracticeContext
from .models import AiKey, ReportEdit, TeacherRequest


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    jobs = context.jobs
    session = context.session
    timeline = context.timeline
    analyses = context.analyses

    @app.get("/api/ai/config")
    def ai_config():
        return {
            "configured": bool(
                os.environ.get("OPENAI_API_KEY") or (store.root / "openai-key").exists()
            ),
            "environment": bool(os.environ.get("OPENAI_API_KEY")),
        }

    @app.put("/api/ai/config")
    def ai_key(body: AiKey):
        path = store.root / "openai-key"
        temporary = store.root / "openai-key.tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write(body.api_key)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        return {"configured": True}

    @app.post("/api/reports/{ident}/revision")
    def revise_report(ident: str, body: ReportEdit):
        rows = store.query("SELECT * FROM reports WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Report not found")
        old = rows[0]
        new = uuid.uuid4().hex
        store.execute(
            "INSERT INTO reports VALUES(?,?,?,?,?,?)",
            (
                new,
                old["session_id"],
                "user-edited",
                datetime.now(timezone.utc).isoformat(),
                body.text,
                old["evidence"],
            ),
        )
        return {"id": new}

    @app.get("/api/sessions/{ident}/preanalysis")
    def preanalysis(ident: str):
        session(ident)
        from ..teacher import evidence_for

        path = store.root / "reports" / (ident + "-preanalysis.json")
        payload = evidence_for(store, ident, analyses_limit=None)
        payload["schema_version"] = "practice-preanalysis-v1"
        # Unique temporary paths allow concurrent exports without partial JSON.
        temporary = path.with_name(uuid.uuid4().hex + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2))
        temporary.replace(path)
        return FileResponse(
            path, media_type="application/json", filename="practice-preanalysis.json"
        )

    @app.get("/api/sessions/{ident}/bundle")
    def bundle(ident: str):
        import zipfile

        session(ident)
        path = store.root / "exports" / (ident + "-" + uuid.uuid4().hex + ".zip")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            folder = store.root / "sessions" / ident
            from ..microphone import audio_layout

            microphone, _ = audio_layout(folder)
            if microphone:
                archive.write(microphone, microphone.name)
            if (folder / "microphone.json").exists():
                archive.write(folder / "microphone.json", "microphone.json")
            if (folder / "original.mid").exists():
                archive.write(folder / "original.mid", "original.mid")
            archive.write(folder / "events.jsonl", "events.jsonl")
            archive.writestr("timeline.json", json.dumps(timeline(ident), indent=2))
            archive.writestr("analyses.json", json.dumps(analyses(ident), indent=2))
            from ..teacher import evidence_for

            archive.writestr(
                "preanalysis.json",
                json.dumps(evidence_for(store, ident, analyses_limit=None), indent=2),
            )
            for report in reports(ident):
                archive.writestr("reports/" + report["id"] + ".txt", report["text"])
            for job in store.query(
                "SELECT id,result FROM jobs WHERE kind='render' AND status='done'"
            ):
                if not job["result"]:
                    continue
                result = json.loads(job["result"])
                if result.get("session_id") == ident and result.get("filename"):
                    audiofile = store.root / "audio" / result["filename"]
                    if audiofile.exists():
                        archive.write(audiofile, "audio/" + audiofile.name)
        return FileResponse(
            path,
            media_type="application/zip",
            filename="ChopinStudio_" + ident[:8] + ".zip",
            background=BackgroundTask(path.unlink, missing_ok=True),
        )

    @app.post("/api/sessions/{ident}/teacher")
    def teacher(ident: str, body: TeacherRequest):
        session(ident)
        from ..teacher import create_report

        return {
            "job_id": jobs.submit(
                "teacher",
                lambda cancel, job: create_report(
                    store, ident, body.provider, body.question, body.model
                ),
            )
        }

    @app.get("/api/sessions/{ident}/reports")
    def reports(ident: str):
        return context.reports(ident)

    @app.get("/api/reports/{ident}/text")
    def report_text(ident: str):
        rows = store.query("SELECT text FROM reports WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Report not found")
        return PlainTextResponse(
            rows[0]["text"],
            headers={
                "Content-Disposition": 'attachment; filename="practice-report.txt"'
            },
        )

    return app
