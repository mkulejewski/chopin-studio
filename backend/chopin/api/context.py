"""Small HTTP readiness/lookups shared by routers; no global service locator."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..jobs import Jobs
from ..live import LiveFollowing
from ..recorder import Recorder
from ..store import Store


@dataclass
class PracticeContext:
    store: Store
    recorder: Recorder
    jobs: Jobs
    live: LiveFollowing
    save_upload: Callable[[UploadFile, Path, str], Awaitable[Path]]

    def session(self, ident):
        rows = self.store.query("SELECT * FROM sessions WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Session not found")
        if rows[0]["status"] in ("recording", "saving"):
            raise HTTPException(409, "Finish saving this session first")
        return rows[0]

    def segment(self, ident):
        rows = self.store.query("SELECT * FROM segments WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Segment not found")
        self.session(rows[0]["session_id"])
        from ..retention import deleted

        if deleted(self.store, ident):
            raise HTTPException(410, "This recording was permanently removed")
        return rows[0]

    def deletion_ready(self):
        if (
            self.recorder.active
            or self.recorder.saving
            or self.recorder.hardware_playback
        ):
            raise HTTPException(
                409, "Stop recording/playback and finish saving before deleting."
            )
        if self.store.query("SELECT id FROM jobs WHERE status IN ('queued','running')"):
            raise HTTPException(
                409, "Wait for background analysis/rendering to finish, then delete."
            )

    def piece_exists(self, piece_id):
        if not self.store.query("SELECT id FROM pieces WHERE id=?", (piece_id,)):
            raise HTTPException(404, "Piece not found")

    def timeline(self, ident: str):
        self.session(ident)
        from ..retention import deleted

        return [
            {**row, "recording_deleted": deleted(self.store, row["id"])}
            for row in self.store.query(
                "SELECT * FROM segments WHERE session_id=? ORDER BY start", (ident,)
            )
        ]

    def analyses(self, ident: str):
        self.session(ident)
        return [
            {**row, "result": json.loads(row["result"])}
            for row in self.store.query(
                "SELECT * FROM analyses WHERE session_id=? ORDER BY created DESC",
                (ident,),
            )
        ]

    def reports(self, ident: str):
        self.session(ident)
        return self.store.query(
            "SELECT * FROM reports WHERE session_id=? ORDER BY created DESC", (ident,)
        )

    def assessment(self, ident: str):
        from ..assessment import piece_assessment

        return piece_assessment(self.store, ident)
