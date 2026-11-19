"""HTTP boundary for edition-bound score read-throughs."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..score_certification import CertificationEnded, CertificationNotFound, CertificationUnavailable


class CertificationRange(BaseModel):
    start_measure: int | None = Field(default=None, ge=0)
    end_measure: int | None = Field(default=None, ge=0)
    include_corrections: bool = False


def certification_router(studio):
    router = APIRouter(prefix='/api/score-certification')
    certification = studio.certification

    def call(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except CertificationNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except CertificationEnded as exc:
            raise HTTPException(409, str(exc)) from exc
        except CertificationUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @router.get('/{piece}')
    def certification_state(piece: str):
        return call(certification.state, piece)

    @router.post('/{piece}/start')
    def start_certification(piece: str, scope: CertificationRange = CertificationRange()):
        return call(certification.start, piece, studio, **scope.model_dump())

    @router.post('/{piece}/{ident}/finish')
    def finish_certification(piece: str, ident: str):
        return call(certification.stop, piece, ident)

    @router.post('/{piece}/{ident}/pause')
    def pause_certification(piece: str, ident: str):
        return call(certification.stop, piece, ident, through_pause=True)

    @router.get('/{piece}/{ident}/live')
    def certification_live(piece: str, ident: str):
        return call(certification.live, piece, ident)

    @router.get('/{piece}/{ident}/review')
    def certification_review(piece: str, ident: str):
        return call(certification.review, piece, ident)

    return router
