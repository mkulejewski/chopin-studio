"""Organisation, reference quality, jobs and live-following HTTP boundaries."""

from fastapi import APIRouter
from .context import PracticeContext


def router(context: PracticeContext):
    app = APIRouter()
    store = context.store
    jobs = context.jobs
    segment = context.segment

    @app.post("/api/segments/{ident}/analyse")
    def analyse(ident: str):
        return {"job_id": jobs.analysis(segment(ident))}

    @app.get("/api/sessions/{ident}/analyses")
    def analyses(ident: str):
        return context.analyses(ident)

    @app.get("/api/jobs")
    def job_list():
        return store.query("SELECT * FROM jobs ORDER BY created DESC LIMIT 100")

    @app.post("/api/jobs/{ident}/cancel")
    def cancel(ident: str):
        flag = jobs.cancellations.get(ident)
        if flag:
            flag.set()
        return {"ok": True}

    @app.get("/api/pieces/{ident}/assessment")
    def assessment(ident: str):
        return context.assessment(ident)

    @app.get("/api/performances")
    def performances(include_flagged: bool = False):
        return store.query(
            "SELECT s.*,p.title,p.opus,ps.started FROM segments s LEFT JOIN pieces p ON p.id=s.piece_id JOIN sessions ps ON ps.id=s.session_id WHERE s.discarded=0 AND ps.status NOT IN ('recording','saving','recovery_failed') AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording') ORDER BY ps.started DESC,s.start"
        )

    @app.get("/api/comparison")
    def comparison(left: str, right: str):
        from ..organisation import analyse_segment

        a, b = segment(left), segment(right)
        if not a["piece_id"] or a["piece_id"] != b["piece_id"]:
            raise ValueError("Choose two identified activities from the same piece")
        from ..passages import compare_passages

        aa, bb = analyse_segment(store, a), analyse_segment(store, b)
        return {
            "left": {"segment": a, "analysis": aa},
            "right": {"segment": b, "analysis": bb},
            "aligned": compare_passages(aa, bb),
            "notice": "Comparison uses the current reference representation. Source recordings and historical analyses are retained. Different measure coverage, editions and ornament choices can prevent direct comparison.",
        }

    return app
