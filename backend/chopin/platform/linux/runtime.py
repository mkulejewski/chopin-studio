"""Linux composition, process lock, loopback server and desktop exit."""

import fcntl
import logging
import os
from logging.handlers import RotatingFileHandler

from ...studio import StudioPlatform
from ..files import LOCAL_FILES
from .audio import FluidSynth, LinuxHardwareAudio
from .midi import LinuxMidi
from .microphone import LinuxMicrophone
from .paths import data_root, state_root


def adapters(*, hardware=True):
    platform = StudioPlatform(renderer=FluidSynth(LOCAL_FILES))
    if hardware:
        midi = LinuxMidi()
        platform.midi_input = platform.midi_output = midi
        platform.microphone = LinuxMicrophone(platform.files)
        platform.hardware_audio = LinuxHardwareAudio(midi)
    return platform


def main():
    import uvicorn

    from ...app import create_app
    from .desktop import close_studio_windows

    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'backend.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Chopin Studio is already running for this data directory') from None

        log_root = state_root()
        log_root.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            handlers=[logging.StreamHandler(),
                      RotatingFileHandler(log_root / 'studio.log', maxBytes=2_000_000, backupCount=3)],
            format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        )
        desktop_shutdown_requested = False

        def request_shutdown():
            nonlocal desktop_shutdown_requested
            desktop_shutdown_requested = True
            server.should_exit = True

        app = create_app(root, hardware=os.environ.get('CHOPIN_NO_HARDWARE') != '1',
                         shutdown=request_shutdown)
        server = uvicorn.Server(uvicorn.Config(
            app, host='127.0.0.1', port=int(os.environ.get('CHOPIN_PORT', '8765')),
        ))
        server.run()
        if desktop_shutdown_requested and os.environ.get('CHOPIN_DESKTOP_LAUNCH') == '1':
            close_studio_windows()
