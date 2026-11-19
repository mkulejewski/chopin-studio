"""Cancellable timed playback for any MIDI output driver."""

import logging
import time
from collections.abc import Callable, Iterable
from threading import Event

from .platform.interfaces import MidiMessage, OutputConnection

log = logging.getLogger(__name__)


def play_messages(
    output: OutputConnection, messages: Iterable[tuple[float, MidiMessage | None]],
    cancel: Event, check: Callable[[], None] | None = None, tail: float = 3,
):
    """Consume relative delays in seconds, including time carried by metadata."""
    deadline = time.monotonic()
    failure = None
    try:
        for delay, message in messages:
            deadline += delay
            if cancel.wait(max(0, deadline - time.monotonic())):
                raise InterruptedError('Cancelled')
            if check:
                check()
            if message is not None:
                output.send(message)
        if cancel.wait(tail):
            raise InterruptedError('Cancelled')
        if check:
            check()
    except BaseException as exc:
        failure = exc
        raise
    finally:
        # Best-effort cleanup must reach all channels even if one send fails.
        cleanup_error = None
        for channel in range(16):
            for control in (64, 66, 67, 123, 120):
                try:
                    output.send({'type': 'control_change', 'channel': channel,
                                 'control': control, 'value': 0, 'time': 0})
                except Exception as exc:
                    cleanup_error = cleanup_error or exc
        if cleanup_error:
            if failure is None:
                raise cleanup_error
            log.warning('MIDI cleanup after playback failure: %s', cleanup_error)
