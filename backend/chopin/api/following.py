"""Organisation, reference quality, jobs and live-following HTTP boundaries."""

from fastapi import HTTPException


from fastapi import APIRouter
from .context import PracticeContext
from .models import LiveContext


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    recorder = context.recorder
    live = context.live

    @app.put("/api/live/context")
    def live_context(body: LiveContext):
        if body.piece_id and not store.query(
            "SELECT id FROM pieces WHERE id=?", (body.piece_id,)
        ):
            raise HTTPException(404, "Piece not found")
        with recorder.lock:
            if recorder.context_piece_id != body.piece_id:
                recorder.context_piece_id = body.piece_id
                recorder.mark("piece_context", {"piece_id": body.piece_id})
            live.context_piece_id = body.piece_id
        return {"ok": True}

    @app.get("/api/live")
    def live_status():
        return live.state

    return app
