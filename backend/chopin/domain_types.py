"""Small internal evidence contracts; raw MIDI dictionaries remain untouched."""
from dataclasses import dataclass
from typing import NotRequired, TypedDict


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


class ScorePosition(TypedDict):
    measure: int | None
    beat: float
    staff: NotRequired[int | None]
    voice: NotRequired[str | None]


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
        return (self.snapshot_current and self.source_eligible
                and not self.recording_deleted and self.reference_current is not False)
