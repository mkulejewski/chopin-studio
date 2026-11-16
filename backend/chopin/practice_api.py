"""Compatibility entry point; application composition installs scoped routers."""
from .api.context import PracticeContext
from .api.models import (
    SegmentEdit as SegmentEdit,
    TimelineEdit as TimelineEdit,
    RecordingChoice as RecordingChoice,
    DeleteRecording as DeleteRecording,
    LiveContext as LiveContext,
    ReferenceUpdate as ReferenceUpdate,
    PageMap as PageMap,
    RenderRequest as RenderRequest,
    HardwareRender as HardwareRender,
    AiKey as AiKey,
    ReportEdit as ReportEdit,
    TeacherRequest as TeacherRequest,
    VoicingTarget as VoicingTarget,
    ObjectiveRequest as ObjectiveRequest,
    ProblemTime as ProblemTime,
)
from .api import recordings, reports, references, timelines, analysis, audio, progress, following


def attach_practice_routes(app, store, recorder, jobs, live, save_upload, *, hardware=True):
    context = PracticeContext(store, recorder, jobs, live, save_upload, hardware)
    app.include_router(recordings.router(context))
    app.include_router(reports.router(context))
    app.include_router(references.router(context))
    app.include_router(timelines.router(context))
    app.include_router(analysis.router(context))
    app.include_router(audio.router(context))
    app.include_router(progress.router(context))
    app.include_router(following.router(context))
