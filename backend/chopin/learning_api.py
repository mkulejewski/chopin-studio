"""Small, explicit HTTP boundary for edition-bound Learning."""
import time
from typing import Literal
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .learning import BUNDLE, Learning


class LearningConfig(BaseModel):
    visible: int = Field(default=3, ge=1, le=20)
    hidden: int = Field(default=3, ge=1, le=20)
    connections: int = Field(default=2, ge=1, le=20)
    auto_continue: bool = True
    auto_finish: bool = True


class Chunk(BaseModel):
    start: int = Field(ge=0, le=49)
    end: int = Field(ge=0, le=49)
    focus: str = Field(default='', max_length=1000)


class PlanUpdate(BaseModel):
    config: LearningConfig
    chunks: list[Chunk] | None = Field(default=None, max_length=100)


class ReviewOptions(BaseModel):
    include_current: bool = False
    chunk_index: int | None = Field(default=None, ge=0, le=99)


class RestartTake(BaseModel):
    attempt_id: str = Field(min_length=1, max_length=100)


class AdvanceStage(BaseModel):
    stage_id: str = Field(min_length=1, max_length=100)
    generation: int = Field(ge=0)


class Variant(BaseModel):
    note_id: str = Field(max_length=100)
    action: Literal['omit', 'replace', 'revoke']
    pitch: int = Field(default=60, ge=0, le=127)
    reason: str = Field(min_length=1, max_length=1000)


def attach_learning_routes(app, store, recorder):
    learning = Learning(store, recorder)
    app.state.learning = learning

    def check(piece):
        if piece != 'e25-1':
            raise HTTPException(404, 'This piece needs in-depth model lesson analysis and edition review before proper Learning. No approved lesson exists yet.')

    @app.get('/api/learning/{piece}')
    def get(piece: str):
        check(piece)
        learning.last_frontend = time.monotonic()
        return learning.snapshot()

    @app.get('/api/learning/{piece}/reference')
    def reference(piece: str):
        check(piece)
        return FileResponse(BUNDLE, media_type='application/json', filename='aeolian-paderewski-learning.json')

    @app.put('/api/learning/{piece}')
    def configure(piece: str, update: PlanUpdate):
        check(piece)
        return learning.configure(update.config.model_dump(), [c.model_dump() for c in update.chunks] if update.chunks is not None else None)

    @app.post('/api/learning/{piece}/start')
    def start(piece: str):
        check(piece)
        return learning.start()

    @app.post('/api/learning/{piece}/finish')
    def finish(piece: str):
        check(piece)
        return learning.finish()

    @app.post('/api/learning/{piece}/peek')
    def peek(piece: str):
        check(piece)
        return learning.assist()

    @app.post('/api/learning/{piece}/pause')
    def pause(piece: str):
        check(piece)
        return learning.pause()

    @app.post('/api/learning/{piece}/restart')
    def restart(piece: str):
        check(piece)
        return learning.restart()

    @app.post('/api/learning/{piece}/variants')
    def variant(piece: str, rule: Variant):
        check(piece)
        return learning.variant(**rule.model_dump())

    @app.post('/api/learning/{piece}/attempts/{ident}/accept')
    def accept_take(piece: str, ident: str):
        check(piece)
        return learning.accept_take(ident)

    @app.post('/api/learning/{piece}/advance')
    def advance_stage(piece: str, request: AdvanceStage):
        check(piece)
        return learning.advance_stage(**request.model_dump())

    @app.post('/api/learning/{piece}/restart-take')
    def restart_take(piece: str, request: RestartTake):
        check(piece)
        return learning.restart_take(request.attempt_id)

    @app.post('/api/learning/{piece}/review')
    def review(piece: str, options: ReviewOptions = ReviewOptions()):
        check(piece)
        return learning.review(options.include_current, options.chunk_index)

    @app.post('/api/learning/{piece}/review/leave')
    def leave_review(piece: str):
        check(piece)
        return learning.leave_review()

    @app.get('/api/learning/{piece}/attempts/{ident}/staves')
    def live_staves(piece: str, ident: str, show_expected: bool = True, first_measure: int | None = None):
        check(piece)
        return learning.live_staves(ident, show_expected, first_measure)
