from ..timeline import (
    edit_timeline as replace_timeline,
    undo_timeline,
    TimelineConflict,
)

"""Organisation, reference quality, jobs and live-following HTTP boundaries."""

from fastapi import HTTPException


from fastapi import APIRouter
from .context import PracticeContext
from .models import TimelineEdit


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    jobs = context.jobs
    session = context.session

    @app.get("/api/sessions/{ident}/segments")
    def timeline(ident: str):
        return context.timeline(ident)

    @app.put("/api/sessions/{ident}/segments")
    def edit_timeline(ident: str, body: TimelineEdit):
        record = session(ident)
        try:
            replace_timeline(
                store,
                record,
                [item.model_dump() for item in body.segments],
                body.expected_revision,
            )
        except TimelineConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        updated = context.timeline(ident)
        for row in updated:
            jobs.analysis(row)
        return updated

    @app.post("/api/sessions/{ident}/segments/undo")
    def undo(ident: str):
        session(ident)
        try:
            undo_timeline(store, ident)
        except TimelineConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        updated = context.timeline(ident)
        for row in updated:
            jobs.analysis(row)
        return updated

    @app.post("/api/sessions/{ident}/organise")
    def organise(ident: str, force: bool = False):
        session(ident)
        from ..retention import locked

        if locked(store, ident):
            raise HTTPException(
                409, "Removed intervals cannot be restored. This timeline is locked."
            )
        return {"job_id": jobs.organise(ident, force)}

    return app
