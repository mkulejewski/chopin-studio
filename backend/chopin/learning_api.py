"""Small, explicit HTTP boundary for edition-bound Learning."""
import time
import threading
from functools import wraps
from typing import Literal
from fastapi import HTTPException, Depends
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from .learning import BUNDLES, Learning


class PieceChoice(BaseModel):
    piece_id: str = Field(min_length=1, max_length=100)


class LearningConfig(BaseModel):
    visible: int = Field(default=3, ge=1, le=20)
    hidden: int = Field(default=3, ge=1, le=20)
    connections: int = Field(default=2, ge=1, le=20)
    auto_continue: bool = True
    auto_finish: bool = True
    auto_restart_on_mistake: bool = False


class Chunk(BaseModel):
    start: int = Field(ge=0, le=10000)
    end: int = Field(ge=0, le=10000)
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


class ReferenceCorrection(BaseModel):
    note_id: str = Field(min_length=1, max_length=100)
    replacement: str = Field(default='', max_length=12)
    reason: str = Field(min_length=1, max_length=1000)
    action: Literal['replace', 'revoke'] = 'replace'


class HandChoice(BaseModel):
    hand: Literal['both', 'right', 'left'] = 'both'


class PedalControl(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    enabled: bool


class PedalRepeat(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    command_id: float = Field(ge=0, allow_inf_nan=False)
    attempt_id: str | None = Field(default=None, max_length=100)
    target_id: str = Field(min_length=1, max_length=100)


def attach_learning_routes(app, store, recorder):
    selection_lock = threading.Lock()
    selected = store.setting('learning_piece', 'e25-1')
    if selected not in BUNDLES:
        selected = 'e25-1'
    controllers = {selected: Learning(store, recorder, selected)}
    app.state.learning = controllers[selected]

    def check(piece):
        if piece not in BUNDLES:
            raise HTTPException(404, 'This piece needs in-depth model lesson analysis and edition review before proper Learning. No approved lesson exists yet.')

    # Resolve, then serialize and recheck selection in the endpoint itself.
    # Keeping a lock inside a yield dependency can starve FastAPI's threadpool.
    def current(piece: str):
        with selection_lock:
            check(piece)
            if app.state.learning.piece_id != piece:
                raise HTTPException(409, 'Select this Learning piece before changing or reading its lesson.')
            return app.state.learning

    def serialized(function):
        @wraps(function)
        def invoke(*args, **kwargs):
            with selection_lock:
                if kwargs.get('learning') is not app.state.learning:
                    raise HTTPException(409, 'The selected Learning piece changed; reload the lesson.')
                return function(*args, **kwargs)
        return invoke

    @app.get('/api/learning')
    def catalogue():
        with selection_lock:
            from .learning import lesson
            return {'selected_piece': app.state.learning.piece_id,
                    'pieces': [{'piece_id': ident, 'title': (lesson() if ident == 'e25-1' else lesson(ident))['title']}
                               for ident in BUNDLES]}

    @app.post('/api/learning/selection')
    def select_piece(choice: PieceChoice):
        with selection_lock:
            check(choice.piece_id)
            previous = app.state.learning
            if previous.piece_id != choice.piece_id:
                # Pause saves authoritative MIDI; selecting another lesson never
                # grades the interrupted take or starts the next one.
                previous.pause()
                if choice.piece_id not in controllers:
                    controllers[choice.piece_id] = Learning(store, recorder, choice.piece_id)
                app.state.learning = controllers[choice.piece_id]
            store.set_setting('learning_piece', choice.piece_id)
            return {'selected_piece': choice.piece_id}

    @app.get('/api/learning/{piece}')
    @serialized
    def get(piece: str, learning: Learning = Depends(current)):
        check(piece)
        learning.last_frontend = time.monotonic()
        return learning.snapshot()

    @app.get('/api/learning/{piece}/reference')
    @serialized
    def reference(piece: str, format: Literal['json','musicxml'] = 'json', learning: Learning = Depends(current)):
        check(piece)
        if format == 'musicxml':
            from .learning_score import attack_score_xml
            return Response(attack_score_xml(learning.lesson()), media_type='application/vnd.recordare.musicxml+xml',
                            headers={'Content-Disposition': f'attachment; filename="{BUNDLES[piece].stem}_paderewski_attacks.musicxml"'})
        return FileResponse(BUNDLES[piece], media_type='application/json', filename=f'{BUNDLES[piece].stem}_paderewski_learning.json')

    @app.put('/api/learning/{piece}')
    @serialized
    def configure(piece: str, update: PlanUpdate, learning: Learning = Depends(current)):
        check(piece)
        return learning.configure(update.config.model_dump(), [c.model_dump() for c in update.chunks] if update.chunks is not None else None)

    @app.put('/api/learning/{piece}/hand')
    @serialized
    def select_hand(piece: str, choice: HandChoice, learning: Learning = Depends(current)):
        check(piece)
        return learning.select_hand(choice.hand)

    @app.post('/api/learning/{piece}/pedal-control')
    @serialized
    def pedal_control(piece: str, control: PedalControl, learning: Learning = Depends(current)):
        check(piece)
        return recorder.learning_pedal_control(control.owner, control.enabled)

    @app.get('/api/learning/{piece}/pedal-commands')
    @serialized
    def pedal_commands(piece: str, owner: str, after: float = 0, learning: Learning = Depends(current)):
        check(piece)
        return recorder.learning_commands(owner, after)

    @app.post('/api/learning/{piece}/pedal-repeat')
    @serialized
    def pedal_repeat(piece: str, repeat: PedalRepeat, learning: Learning = Depends(current)):
        check(piece)
        return learning.repeat_from_pedal(**repeat.model_dump())

    @app.post('/api/learning/{piece}/start')
    @serialized
    def start(piece: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.start()

    @app.post('/api/learning/{piece}/finish')
    @serialized
    def finish(piece: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.finish()

    @app.post('/api/learning/{piece}/peek')
    @serialized
    def peek(piece: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.assist()

    @app.post('/api/learning/{piece}/pause')
    @serialized
    def pause(piece: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.pause()

    @app.post('/api/learning/{piece}/restart')
    @serialized
    def restart(piece: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.restart()

    @app.post('/api/learning/{piece}/variants')
    @serialized
    def variant(piece: str, rule: Variant, learning: Learning = Depends(current)):
        check(piece)
        return learning.variant(**rule.model_dump())

    @app.post('/api/learning/{piece}/corrections')
    @serialized
    def correct_reference(piece: str, correction: ReferenceCorrection, learning: Learning = Depends(current)):
        check(piece)
        return learning.correct_note(**correction.model_dump())

    @app.post('/api/learning/{piece}/attempts/{ident}/accept')
    @serialized
    def accept_take(piece: str, ident: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.accept_take(ident)

    @app.post('/api/learning/{piece}/advance')
    @serialized
    def advance_stage(piece: str, request: AdvanceStage, learning: Learning = Depends(current)):
        check(piece)
        return learning.advance_stage(**request.model_dump())

    @app.post('/api/learning/{piece}/restart-take')
    @serialized
    def restart_take(piece: str, request: RestartTake, learning: Learning = Depends(current)):
        check(piece)
        return learning.restart_take(request.attempt_id)

    @app.post('/api/learning/{piece}/review')
    @serialized
    def review(piece: str, options: ReviewOptions = ReviewOptions(), learning: Learning = Depends(current)):
        check(piece)
        return learning.review(options.include_current, options.chunk_index)

    @app.post('/api/learning/{piece}/review/leave')
    @serialized
    def leave_review(piece: str, learning: Learning = Depends(current)):
        check(piece)
        return learning.leave_review()

    @app.get('/api/learning/{piece}/attempts/{ident}/staves')
    @serialized
    def live_staves(piece: str, ident: str, show_expected: bool = True, first_measure: int | None = None, learning: Learning = Depends(current)):
        check(piece)
        return learning.live_staves(ident, show_expected, first_measure)
