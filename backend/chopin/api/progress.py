"""Progress summaries, voicing targets and technical-objective HTTP routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .context import PracticeContext
from .models import ObjectiveRequest, ProblemTime, VoicingTarget


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    segment = context.segment
    piece_exists = context.piece_exists

    @app.get("/api/progress/days")
    def days():
        return store.query(
            "SELECT substr(started,1,10) AS day,COUNT(*) AS sessions,SUM(duration) AS recorded_seconds FROM sessions WHERE status NOT IN ('recording','saving') GROUP BY day ORDER BY day DESC LIMIT 90"
        )

    @app.get("/api/progress")
    def progress():
        from ..progress import progress_overview

        # Evidence consists of JSON-native saved values. Avoid recursively copying
        # the whole history through FastAPI's generic encoder a second time.
        return JSONResponse(progress_overview(store))

    @app.get("/api/pieces/{piece_id}/voicing")
    def voicing(piece_id: str):
        piece_exists(piece_id)
        return store.setting("voicing:" + piece_id, VoicingTarget().model_dump())

    @app.put("/api/pieces/{piece_id}/voicing")
    def save_voicing(piece_id: str, body: VoicingTarget):
        piece_exists(piece_id)
        store.set_setting("voicing:" + piece_id, body.model_dump())
        return body.model_dump()

    @app.post("/api/pieces/{piece_id}/objectives")
    def add_objective(piece_id: str, body: ObjectiveRequest):
        piece_exists(piece_id)
        if (
            body.first_measure is not None
            and body.last_measure is not None
            and body.last_measure < body.first_measure
        ):
            raise HTTPException(422, "Invalid measure range")
        ident = uuid.uuid4().hex
        store.execute(
            "INSERT INTO practice_objectives VALUES(?,?,?,?,?,?,?,?,?)",
            (
                ident,
                piece_id,
                body.title,
                body.category,
                body.first_measure,
                body.last_measure,
                int(body.completed),
                1,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return {"id": ident, "revision": 1}

    @app.put("/api/objectives/{ident}")
    def edit_objective(ident: str, body: ObjectiveRequest):
        if (
            body.first_measure is not None
            and body.last_measure is not None
            and body.last_measure < body.first_measure
        ):
            raise HTTPException(422, "Invalid measure range")
        with store.lock:
            rows = store.query(
                "SELECT revision FROM practice_objectives WHERE id=?", (ident,)
            )
            if not rows:
                raise HTTPException(404, "Objective not found")
            if rows[0]["revision"] != body.revision:
                raise HTTPException(409, "Objective changed; reload before saving")
            store.execute(
                "UPDATE practice_objectives SET title=?,category=?,first_measure=?,last_measure=?,completed=?,revision=revision+1 WHERE id=?",
                (
                    body.title,
                    body.category,
                    body.first_measure,
                    body.last_measure,
                    int(body.completed),
                    ident,
                ),
            )
        return {"id": ident, "revision": body.revision + 1}

    @app.post("/api/objectives/{ident}/time")
    def attribute_time(ident: str, body: ProblemTime):
        objectives = store.query(
            "SELECT * FROM practice_objectives WHERE id=?", (ident,)
        )
        if not objectives:
            raise HTTPException(404, "Objective not found")
        row = segment(body.segment_id)
        if (
            row["piece_id"] != objectives[0]["piece_id"]
            or row["discarded"]
            or not row["start"] <= body.start < body.end <= row["end"]
        ):
            raise HTTPException(
                422, "Choose an interval inside an activity of this piece"
            )
        time_id = uuid.uuid4().hex
        store.execute(
            "INSERT INTO practice_problem_time VALUES(?,?,?,?,?,?,?)",
            (
                time_id,
                ident,
                body.segment_id,
                row["session_id"],
                body.start,
                body.end,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return {"id": time_id}

    @app.delete("/api/objectives/{ident}/time/{time_id}")
    def remove_time(ident: str, time_id: str):
        store.execute(
            "DELETE FROM practice_problem_time WHERE id=? AND objective_id=?",
            (time_id, ident),
        )
        return {"ok": True}

    return app
