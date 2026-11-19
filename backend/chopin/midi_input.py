"""Shared input selection, reconnect policy and connection diagnostics."""

import threading

from .midi_capabilities import MidiEvidence, load_profile
from .platform.interfaces import MidiEvent, MidiInputDriver, MidiPort


def select_input(ports: list[MidiPort], preferred: str) -> str | None:
    if preferred:
        return next((port.id for port in ports if preferred.casefold() in port.id.casefold()), None)
    # Preserve the primary test piano's default priority. Names do not determine capabilities.
    choices = [port.id for port in ports if port.automatic]
    return next((name for name in choices if any(
        hint in name.casefold() for hint in ('casio', 'ap-470', 'celviano')
    )), choices[0] if choices else None)


class MidiInput:
    """Only the monitor thread (or a manual host calling poll) opens/closes ports."""

    def __init__(self, recorder, driver: MidiInputDriver):
        self.recorder = recorder
        self.driver = driver
        self.port = None
        self.connected = None
        self.devices = []
        self.error = None
        self._lock = threading.Lock()
        self._connection = None
        self._callback_error = None
        self._evidence = MidiEvidence()
        self._closed = threading.Event()
        self._wake = threading.Event()
        self._reconnect = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None or self._closed.is_set():
            raise RuntimeError('MIDI monitor can only be started once')
        self._thread = threading.Thread(target=self._run, daemon=True, name='midi-discovery')
        self._thread.start()

    def _run(self):
        try:
            while not self._closed.is_set():
                self._wake.clear()
                self.poll()
                self._wake.wait(2)
        finally:
            try:
                self._disconnect()
            except Exception as exc:
                self.error = str(exc)

    def request_reconnect(self):
        self._reconnect.set()
        self._wake.set()

    def _disconnect(self, error=None):
        with self._lock:
            self._connection = None
            previous, self.connected = self.connected, None
            self._callback_error = None
        if previous:
            self.recorder.device_status(previous, connected=False, error=error)
        if self.port:
            port, self.port = self.port, None
            port.close()

    def poll(self):
        if self._closed.is_set():
            return
        try:
            ports = self.driver.inputs()
            self.devices = [port.id for port in ports]
            desired = select_input(ports, self.recorder.store.setting('preferred_device', ''))
            with self._lock:
                callback_error = self._callback_error
            if callback_error:
                self.recorder.input_failed(callback_error)
            if self._reconnect.is_set() or desired != self.connected or callback_error:
                self._reconnect.clear()
                self._disconnect(callback_error)
            if callback_error:
                self.error = callback_error
                return  # Retry on the next discovery cycle.
            if not self.port and desired:
                self._connect(desired)
            self.error = None
        except Exception as exc:
            self.error = str(exc)
            try:
                self._disconnect(self.error)
            except Exception as close_error:
                self.error += f'; could not close MIDI input: {close_error}'

    def _connect(self, desired):
        token = object()
        with self._lock:
            self._connection = token
            self._evidence = MidiEvidence()

        def receive(event: MidiEvent):
            with self._lock:
                if self._connection is token and not self._closed.is_set():
                    self.recorder.receive_event(event)
                    self._evidence.observe(event.message)

        def report_error(error):
            with self._lock:
                if self._connection is token:
                    self._callback_error = error
                    self._wake.set()

        # Do not hold the state lock across driver calls. Some drivers deliver
        # messages before open_input returns or wait for a callback during close.
        self.port = self.driver.open_input(desired, receive, report_error)
        with self._lock:
            self.connected = desired
        self.recorder.device_status(desired, connected=True)

    def profile(self, port):
        profile = load_profile(self.recorder.store, port)
        with self._lock:
            evidence = self._evidence if port == self.connected else MidiEvidence()
            return evidence.describe(profile)

    def close(self):
        self._closed.set()
        self._wake.set()
        if self._thread:
            self._thread.join(3)
        else:
            self._disconnect()
