"""Library metadata, PDF uploads and per-piece viewing preferences."""

import logging

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from ..imports import import_pdf_file

log = logging.getLogger(__name__)


from fastapi import APIRouter

from .models import PieceUpdate, ViewUpdate


def router(store, save_upload):
    app = APIRouter()

    @app.get("/api/library")
    def library():
        return {
            "pieces": store.query(
                "SELECT p.*, (SELECT COUNT(*) FROM symbolic_scores s WHERE s.piece_id=p.id) AS reference_count, "
                "(SELECT COUNT(*) FROM symbolic_scores s WHERE s.piece_id=p.id AND s.quality='verified') AS verified_reference_count, "
                "(SELECT COUNT(*) FROM symbolic_scores s WHERE s.piece_id=p.id AND s.quality='provisional') AS provisional_reference_count "
                "FROM pieces p ORDER BY genre, opus"
            ),
            "volumes": store.query("SELECT * FROM volumes"),
        }

    @app.put("/api/pieces/{ident}")
    def update_piece(ident: str, piece: PieceUpdate):
        volume = store.query("SELECT * FROM volumes WHERE id=?", (piece.volume_id,))
        if not volume or not store.query("SELECT id FROM pieces WHERE id=?", (ident,)):
            raise HTTPException(404, "Piece or volume not found")
        if bool(piece.start_page) != bool(piece.end_page):
            raise ValueError("Set both page bounds, or leave both empty")
        if piece.start_page and (
            piece.end_page < piece.start_page
            or (volume[0]["pages"] and piece.end_page > volume[0]["pages"])
        ):
            raise ValueError("Page range must be ordered and within the PDF")
        fields = piece.model_dump()
        from ..catalogue import catalogue_path

        fields["catalogue_path"] = catalogue_path(piece.genre, piece.opus)
        store.execute(
            "UPDATE pieces SET " + ",".join(k + "=?" for k in fields) + " WHERE id=?",
            (*fields.values(), ident),
        )
        return {"ok": True}

    @app.put("/api/pieces/{ident}/view")
    def update_view(ident: str, view: ViewUpdate):
        store.execute(
            "UPDATE pieces SET view=? WHERE id=?", (view.model_dump_json(), ident)
        )
        return {"ok": True}

    @app.post("/api/volumes/{ident}/pdf")
    async def import_pdf(ident: str, file: UploadFile):
        if not store.query("SELECT id FROM volumes WHERE id=?", (ident,)):
            raise HTTPException(404, "Volume not found")
        target = await save_upload(file, store.root / "scores", ".pdf")
        pages = import_pdf_file(store, ident, target)
        return {"pages": pages}

    @app.get("/api/volumes/{ident}/pdf")
    def pdf(ident: str):
        row = store.query("SELECT filename FROM volumes WHERE id=?", (ident,))
        if not row or not row[0]["filename"]:
            raise HTTPException(404, "Import this volume first")
        return FileResponse(
            store.root / "scores" / row[0]["filename"], media_type="application/pdf"
        )

    return app
