"""Stable HTTP request validation schemas, separate from domain services."""

from typing import Literal

from pydantic import BaseModel, Field


class SegmentEdit(BaseModel):
    id: str = Field(pattern="^[a-f0-9]{32}$")
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    piece_id: str | None = None
    label: str = Field(max_length=200)
    confidence: float = Field(default=0, ge=0, le=1)
    first_measure: int | None = Field(default=None, ge=0)
    last_measure: int | None = Field(default=None, ge=0)
    kind: Literal["unknown", "partial", "exercise", "full_exercise", "complete"] = (
        "unknown"
    )
    group_id: str | None = Field(default=None, max_length=80)
    complete: bool = False
    discarded: bool = False
    revision: int = 1
    details: str = "{}"


class TimelineEdit(BaseModel):
    segments: list[SegmentEdit] = Field(max_length=1000)
    expected_revision: int


class RecordingChoice(BaseModel):
    choice: Literal["auto", "keep", "remove"] = "auto"
    complete: bool | None = None


class DeleteRecording(BaseModel):
    confirmation: Literal["delete"]
    revision: int | None = None


class LiveContext(BaseModel):
    piece_id: str | None = None


class ReferenceUpdate(BaseModel):
    quality: Literal["provisional", "verified", "rejected"] = "provisional"
    edition: str = Field(max_length=500)
    notes: list[dict] | None = None


class PageMap(BaseModel):
    measure: int = Field(ge=0)
    pdf_page: int = Field(ge=1)


class RenderRequest(BaseModel):
    soundfont: str = Field(max_length=2000)
    format: Literal["wav", "flac"] = "wav"
    rate: Literal[22050, 44100, 48000] = 44100
    gain: float = Field(default=0.6, ge=0.05, le=2)
    reverb: bool = True


class HardwareRender(BaseModel):
    port: str = Field(min_length=1, max_length=300)
    capture_device: str = Field(default="", max_length=300)


class AiKey(BaseModel):
    api_key: str = Field(min_length=10, max_length=1000)


class ReportEdit(BaseModel):
    text: str = Field(min_length=1, max_length=100000)


class TeacherRequest(BaseModel):
    provider: Literal["local", "openai"] = "local"
    question: str = Field(
        default="Suggest concrete practice priorities from the evidence.",
        max_length=2000,
    )
    model: str = Field(default="gpt-4.1-mini", max_length=100)


class VoicingTarget(BaseModel):
    roles: dict[str, Literal["bass", "inner", "melody", "unassigned"]] = Field(
        default_factory=dict, max_length=100
    )
    melody_min_gap: float | None = Field(default=None, ge=-127, le=127)
    release_calibrated: bool = False


class ObjectiveRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: Literal[
        "tempo",
        "rhythm",
        "voicing",
        "dynamics",
        "articulation",
        "pedal",
        "memory",
        "other",
    ] = "other"
    first_measure: int | None = Field(default=None, ge=0)
    last_measure: int | None = Field(default=None, ge=0)
    completed: bool = False
    revision: int = 1


class ProblemTime(BaseModel):
    segment_id: str
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)


class PieceUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=80)
    opus: str = Field(max_length=80)
    musical_key: str = Field(max_length=80)
    volume_id: str
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)
    printed_page: str = Field(default="", max_length=40)
    favourite: bool = False
    practice_status: str = Field(default="To explore", max_length=80)
    notes: str = Field(default="", max_length=10000)
    mastery: float | None = Field(default=None, ge=1, le=3)
    liking: int = Field(default=0, ge=0, le=3)
    forgotten: bool = False
    intent: str = Field(default="To explore", max_length=80)
    preferred_edition: str = Field(default="Paderewski", max_length=200)


class ViewUpdate(BaseModel):
    page: int = Field(ge=1)
    zoom: float = Field(ge=0.5, le=4)
    two_pages: bool = False
    crop: float = Field(default=0, ge=0, le=0.15)


class Settings(BaseModel):
    preferred_device: str = Field(default="", max_length=200)
    pedal_enabled: bool = False
    pedal_controller: Literal[64, 66, 67] = 66
    separation_cooldown: float = Field(default=20, ge=5, le=300)
    swipe: bool = True
    pinch: bool = True
    double_tap: bool = True
    tap_overlay: bool = False
    auto_hide: bool = False
    live_enabled: bool = False
    live_auto_open: bool = False
    live_auto_turn: bool = False
    live_allow_provisional: bool = False
    live_piece_id: str | None = None
    soundfont: str = ""


class RecordingOptions(BaseModel):
    midi_enabled: bool = True
    microphone_enabled: bool = False
    microphone_device: str = Field(default="default", min_length=1, max_length=300)


class Simulation(BaseModel):
    session_id: str | None = None
    speed: float = Field(default=1, ge=0.25, le=8)
