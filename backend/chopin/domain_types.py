"""Small internal evidence contracts; raw MIDI dictionaries remain untouched."""

from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict


class PerformanceNote(TypedDict):
    pitch: int
    onset: float
    duration: float
    velocity: int
    channel: int
    velocity_14: int | None
    release_velocity: int | None
    release_velocity_14: int | None
    release_source: str | None
    released: bool


@dataclass(frozen=True)
class ScorePosition:
    measure: int | None
    beat: float


@dataclass(frozen=True)
class ReferenceIdentity:
    id: str
    revision: str


@dataclass(frozen=True)
class AnalysisFreshness:
    snapshot_current: bool
    source_eligible: bool
    recording_deleted: bool
    reference_current: bool | None

    @property
    def current(self) -> bool:
        # Legacy evidence without a fingerprint retains its snapshot semantics.
        # None means unknown, never a claim that its edition was re-reviewed.
        return (
            self.snapshot_current
            and self.source_eligible
            and not self.recording_deleted
            and self.reference_current is not False
        )


class CaptureStatus(TypedDict):
    active: str | None
    saving: bool
    event_rate: int
    duration: float
    events: int
    error: str | None
    midi_enabled: bool
    microphone_enabled: bool
    notes: dict[str, int]
    pedals: dict[str, int]
    recent: list[dict]
    queue_depth: int
    last_event_age: float | None


class LearningRange(TypedDict):
    start: int
    end: int
    hand: NotRequired[Literal['both', 'right', 'left']]


class LearningEvaluation(TypedDict):
    passed: bool
    uncertain: bool
    errors: list[dict]
    notice: str
    hand: NotRequired[str]
    version: NotRequired[str]
    played_attacks: NotRequired[int]
    error_count: NotRequired[int]
    errors_truncated: NotRequired[bool]
    variant_count: NotRequired[int]
    correction_count: NotRequired[int]
