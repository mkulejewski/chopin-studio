"""ALSA MIDI ports via the existing Mido/RtMidi backend."""

import time

import mido

from ..interfaces import MidiEvent, MidiPort


class MidoOutput:
    def __init__(self, port):
        self.port = port

    def send(self, message):
        self.port.send(mido.Message.from_dict(message))

    def close(self):
        self.port.close()


class LinuxMidi:
    def inputs(self):
        # Keep explicit selection of ALSA's loopback port possible.
        return [MidiPort(name, automatic=not name.casefold().startswith('midi through:'))
                for name in mido.get_input_names()]

    def open_input(self, port, receive, report_error):
        def on_message(message):
            timestamp = time.monotonic_ns()
            try:
                display = f'sysex ({len(message.data)} data bytes)' if message.type == 'sysex' else str(message)
                event = MidiEvent(timestamp, message.copy(time=0).dict(), display)
                receive(event)
            except Exception as exc:
                report_error(str(exc))

        return mido.open_input(port, callback=on_message)

    def outputs(self):
        return mido.get_output_names()

    def open_output(self, port):
        return MidoOutput(mido.open_output(port))
