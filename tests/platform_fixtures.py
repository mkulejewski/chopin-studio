"""Deterministic ports for the shared adapter contracts."""

from collections.abc import Callable
from dataclasses import dataclass, field

from chopin.platform.interfaces import MidiEvent, MidiMessage, MidiPort


@dataclass
class SyntheticInput:
    receive: Callable[[MidiEvent], None]
    report_error: Callable[[str], None]
    closed: bool = False

    def close(self):
        self.closed = True


@dataclass
class SyntheticOutput:
    messages: list[MidiMessage] = field(default_factory=list)
    closed: bool = False

    def send(self, message):
        self.messages.append(message.copy())

    def close(self):
        self.closed = True


class SyntheticMidi:
    def __init__(self, *ports):
        self.ports = [MidiPort(port) for port in ports]
        self.connections = []
        self.output = SyntheticOutput()
        self.output_port = None
        self.error = None

    def inputs(self):
        if self.error:
            raise OSError(self.error)
        return self.ports.copy()

    def open_input(self, port, receive, report_error):
        self.connections.append((port, SyntheticInput(receive, report_error)))
        return self.connections[-1][1]

    def outputs(self):
        return ['MIDI playback']

    def open_output(self, port):
        self.output_port = port
        return self.output
