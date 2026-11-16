from .models import RenderRequest

"""Organisation, reference quality, jobs and live-following HTTP boundaries."""
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..extraction import segment_midi


from fastapi import APIRouter
from .context import PracticeContext
from .models import HardwareRender


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    recorder = context.recorder
    jobs = context.jobs
    save_upload = context.save_upload
    segment = context.segment

    @app.get("/api/segments/{ident}/audio-status")
    def segment_audio_status(ident: str):
        from ..retention import audio_assets

        microphone, files = audio_assets(store, segment(ident))
        return {"microphone": microphone, "rendered_audio_count": len(files)}

    @app.get("/api/segments/{ident}/microphone")
    def microphone_segment(ident: str):
        from ..microphone import export_audio, export_stem

        row = segment(ident)
        path = export_audio(store, row)
        return FileResponse(
            path,
            media_type="audio/flac",
            filename=export_stem(store, row) + "__microphone.flac",
            background=BackgroundTask(path.unlink, missing_ok=True),
        )

    @app.get("/api/segments/{ident}/midi")
    def export_segment(ident: str):
        row = segment(ident)
        path = segment_midi(store, row)
        from ..microphone import export_stem

        return FileResponse(
            path,
            media_type="audio/midi",
            filename=export_stem(store, row) + "__midi.mid",
        )

    @app.get("/api/audio/hardware")
    def hardware():
        import mido

        try:
            ports = mido.get_output_names() if context.hardware else []
            error = None
        except Exception as exc:
            ports = []
            error = str(exc)
        return {
            "ports": ports,
            "capture_available": bool(shutil.which("arecord")),
            "error": error,
        }

    @app.post("/api/segments/{ident}/ap470")
    def ap470(ident: str, body: HardwareRender):
        row = segment(ident)
        # Capture stays authoritative; replay must not be mistaken for a new take.
        if recorder.active or recorder.saving:
            raise ValueError("Stop recording before hardware playback")
        from ..hardware_audio import play

        def action(cancel, job):
            # Serialize the start check with Record session. Ignore keyboard loopback
            # while producing sound, then restore normal input handling.
            with recorder.lock:
                if recorder.active or recorder.saving:
                    raise ValueError("Stop recording before hardware playback")
                recorder.hardware_playback = True
            try:
                return play(store, row, body.port, body.capture_device, cancel, job)
            finally:
                recorder.hardware_playback = False

        return {"job_id": jobs.submit("render", action)}

    @app.post("/api/segments/{ident}/audio")
    async def import_audio(ident: str, file: UploadFile):
        import wave

        row = segment(ident)
        path = await save_upload(file, store.root / "imports", ".wav")
        try:
            try:
                with wave.open(str(path)) as recording:
                    if recording.getnframes() == 0:
                        raise ValueError("Empty WAV recording")
                    if (
                        recording.getnchannels() != 2
                        or recording.getsampwidth() != 2
                        or recording.getframerate() != 44100
                    ):
                        raise ValueError(
                            "Choose a stereo 16-bit 44.1 kHz WAV from the AP-470"
                        )
            except (wave.Error, EOFError) as exc:
                raise ValueError("Choose a PCM WAV recording") from exc
            job = uuid.uuid4().hex
            destination = store.root / "audio" / (job + ".wav")
            path.replace(destination)
            result = {
                "filename": destination.name,
                "segment_id": ident,
                "session_id": row["session_id"],
                "engine": "AP-470 imported WAV",
                "format": "wav",
                "alignment": "User attached; timing has not been verified",
            }
            store.execute(
                "INSERT INTO jobs(id,kind,status,progress,created,result) VALUES(?,?,?,?,?,?)",
                (
                    job,
                    "render",
                    "done",
                    1,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(result),
                ),
            )
            return result
        finally:
            path.unlink(missing_ok=True)

    @app.get("/api/audio/engines")
    def engines():
        fonts = [
            str(p)
            for directory in ("/usr/share/sounds/sf2", "/usr/share/sounds/sf3")
            for p in Path(directory).glob("*")
            if p.suffix in (".sf2", ".sf3")
        ]
        return {
            "fluidsynth": shutil.which("fluidsynth"),
            "soundfonts": fonts,
            "external_engines": {
                "sfizz": shutil.which("sfizz_render"),
                "pianoteq": shutil.which("pianoteq"),
            },
        }

    @app.get("/api/audio/{ident}")
    def audio(ident: str):
        rows = store.query(
            "SELECT * FROM jobs WHERE id=? AND kind='render' AND status='done'",
            (ident,),
        )
        if not rows:
            raise HTTPException(404, "Finished render not found")
        result = json.loads(rows[0]["result"])
        if not result.get("filename"):
            raise HTTPException(
                404, "Playback completed without computer audio capture"
            )
        path = store.root / "audio" / result["filename"]
        if not path.exists():
            raise HTTPException(
                404, "Rendered audio was removed; original MIDI is retained"
            )
        return FileResponse(
            path, media_type="audio/flac" if path.suffix == ".flac" else "audio/wav"
        )

    @app.delete("/api/audio/{ident}")
    def delete_audio(ident: str):
        rows = store.query(
            "SELECT result FROM jobs WHERE id=? AND kind='render'", (ident,)
        )
        if not rows:
            raise HTTPException(404, "Render not found")
        if rows[0]["result"]:
            filename = json.loads(rows[0]["result"]).get("filename")
            if filename:
                (store.root / "audio" / filename).unlink(missing_ok=True)
        return {"ok": True}

    @app.post("/api/segments/{ident}/render")
    def render(ident: str, request: RenderRequest):
        return {"job_id": jobs.render(segment(ident), **request.model_dump())}

    return app
