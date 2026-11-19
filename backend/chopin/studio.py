"""Platform-independent service ownership. Hosts decide when to run and exit."""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from .jobs import Jobs
from .learning import LearningSelection
from .live import LiveFollowing
from .midi_input import MidiInput
from .midi_simulation import MidiSimulation
from .platform.files import LOCAL_FILES, StorageFiles
from .platform.interfaces import AudioRenderer, HardwareAudio, MicrophoneInput, MidiInputDriver, MidiOutputDriver
from .recorder import Recorder
from .store import Store
from .score_certification import ScoreCertification

log = logging.getLogger(__name__)


@dataclass
class StudioPlatform:
    files: StorageFiles = LOCAL_FILES
    midi_input: MidiInputDriver | None = None
    midi_output: MidiOutputDriver | None = None
    microphone: MicrophoneInput | None = None
    hardware_audio: HardwareAudio | None = None
    renderer: AudioRenderer | None = None


class ShutdownBlocked(Exception):
    """Capture needs time or storage attention before the host may exit."""


class Studio:
    def __init__(self, root: Path, platform: StudioPlatform):
        self.store = Store(root, files=platform.files)
        self.recorder = Recorder(self.store, platform.microphone)
        self.jobs = Jobs(self.store, renderer=platform.renderer,
                         hardware_audio=platform.hardware_audio, midi_output=platform.midi_output)
        self.learning = LearningSelection(self.store, self.recorder)
        self.certification = ScoreCertification(self.store, self.recorder, self.learning.lock)
        self.live = LiveFollowing(self.store, self.recorder)
        self.midi = MidiInput(self.recorder, platform.midi_input) if platform.midi_input else None
        self.simulation = MidiSimulation(self.recorder, self.midi)
        self.shutting_down = False
        self._shutdown_lock = threading.Lock()

    def start(self):
        from .headphone_audio import needs_review
        for session in self.store.query(
            "SELECT id FROM sessions WHERE status IN ('saved','imported','recovered','incomplete') AND source NOT IN ('learning','score_certification')"
        ):
            sid = session['id']
            if not self.store.setting('organised:' + sid, False) or needs_review(self.store.root / 'sessions' / sid):
                self.jobs.organise(sid)
        if self.midi:
            self.midi.start()

    def start_recording(self, **options):
        with self._shutdown_lock:
            if self.shutting_down:
                raise ShutdownBlocked('Chopin Studio is shutting down')
            return self.recorder.start(simulated=self.simulation.running, **options)

    def stop_recording(self):
        with self.learning.lock:
            learning = self.learning.current
            if self.certification.active:
                piece, ident = self.certification.active
                self.certification.stop(piece, ident, interruption='Stopped outside Score certification.')
            elif learning.active:
                ident = learning.active['session_id']
                learning.pause()
            else:
                ident = self.recorder.stop()
                self.jobs.organise(ident)
            return ident

    def check_disconnect(self):
        if not self.midi:
            return
        with self.learning.lock:
            try:
                ident = self.recorder.stop_if_disconnected()
                if ident:
                    learning = self.learning.current
                    if learning.active and learning.active['session_id'] == ident:
                        learning.finish(aborted=True)
                    elif self.certification.active and self.certification.active[1] == ident:
                        self.certification.stop(*self.certification.active, interruption='The piano disconnected during capture.')
                    else:
                        self.jobs.organise(ident)
                    log.info('Saved recording %s after piano disconnection', ident)
            except Exception:
                log.exception('Cannot finish recording after piano disconnection')

    def tick_learning(self):
        with self.learning.lock:
            learning = self.learning.current
            try:
                learning.tick()
            except Exception as exc:
                learning.pending = None
                learning.error = 'Automatic Learning paused: ' + str(exc) + '. Finish or pause the attempt before continuing.'
                log.exception('Learning controller paused after an error')

    def _save_on_exit(self):
        with self.learning.lock:
            if self.recorder.saving:
                raise ShutdownBlocked('A recording is still saving. Wait before shutting down.')
            self.learning.current.pause()
            if self.certification.active:
                self.certification.stop(*self.certification.active, interruption='Chopin Studio shut down during capture.')
            if self.recorder.active:
                self.recorder.mark('shutdown', {})
                self.jobs.organise(self.recorder.stop())

    def prepare_shutdown(self):
        with self._shutdown_lock, self.learning.lock:
            if self.shutting_down:
                return False
            self.simulation.stop()
            try:
                self._save_on_exit()
            except ShutdownBlocked:
                raise
            except Exception as exc:
                log.exception('Cannot save recording before shutdown')
                raise ShutdownBlocked(
                    'Could not finish saving. The backend is still running; check storage before shutting down.'
                ) from exc
            self.shutting_down = True
            return True

    def finish_shutdown(self):
        from .retention import automatic_cleanup
        self.jobs.drain()
        automatic_cleanup(self.store, shutdown=True)

    def close(self):
        self.simulation.close()
        if self.midi:
            self.midi.close()
        try:
            self._save_on_exit()
        except ShutdownBlocked:
            # The host is already exiting. Recovery will reopen any interrupted save.
            log.warning('Host exited while a recording was saving. Retained capture will be recovered.')
        finally:
            self.live.close()
            try:
                self.finish_shutdown()
            finally:
                self.jobs.close()
                self.store.db.close()
