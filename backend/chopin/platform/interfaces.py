"""Device contracts shared by the Linux host and hardware-free services."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import NotRequired, Protocol, Required, TypedDict


class MidiMessage(TypedDict, total=False):
    """Decoded MIDI 1.0 fields, compatible with the existing journal codec."""

    type: Required[str]
    time: int
    channel: int
    note: int
    velocity: int
    control: int
    value: int
    data: tuple[int, ...] | list[int]
    pitch: int
    program: int
    pos: int
    song: int
    frame_type: int
    frame_value: int


class JournalMidiEvent(TypedDict):
    t: float
    message: MidiMessage
    application_command: NotRequired[bool]


@dataclass(frozen=True)
class MidiEvent:
    """Delivery in wire order, timestamped on the recorder's monotonic clock.

    The adapter transfers ownership of a fresh message dictionary with time=0.
    Equal timestamps are valid. Display text is optional and never journaled.
    """

    timestamp_ns: int
    message: MidiMessage
    display: str = ""


@dataclass(frozen=True)
class MidiPort:
    id: str
    automatic: bool = True


class InputConnection(Protocol):
    def close(self) -> None: ...


class MidiInputDriver(Protocol):
    def inputs(self) -> list[MidiPort]: ...

    def open_input(
        self, port: str, receive: Callable[[MidiEvent], None],
        report_error: Callable[[str], None],
    ) -> InputConnection: ...


class OutputConnection(Protocol):
    def send(self, message: MidiMessage) -> None: ...

    def close(self) -> None: ...


class MidiOutputDriver(Protocol):
    def outputs(self) -> list[str]: ...

    def open_output(self, port: str) -> OutputConnection: ...


class MicrophoneSession(Protocol):
    def running(self) -> bool: ...

    def stop(self) -> dict: ...


class MicrophoneInput(Protocol):
    def available(self) -> bool: ...

    def start(self, folder: Path, device: str, epoch_ns: int) -> MicrophoneSession: ...


@dataclass(frozen=True)
class AudioPlayback:
    filename: str | None
    format: str
    engine: str = "MIDI instrument"


class HardwareAudio(Protocol):
    def capture_available(self) -> bool: ...

    def play(
        self, midi: Path, wav: Path, port: str, device: str, cancel: Event,
    ) -> AudioPlayback: ...


class AudioRenderer(Protocol):
    def engines(self) -> dict: ...

    def render(
        self, midi: Path, wav: Path, cancel: Event, *, soundfont: str,
        format: str, rate: int, gain: float, reverb: bool,
    ) -> dict: ...
