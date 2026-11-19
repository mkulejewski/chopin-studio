"""ALSA Practice capture and Linux process supervision."""

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from ...microphone import RATE, finalise, write_metadata
from ..files import LOCAL_FILES


class LinuxMicrophone:
    def __init__(self, files=LOCAL_FILES):
        self.files = files

    def available(self):
        return shutil.which('arecord') is not None

    def start(self, folder, device, epoch_ns):
        return Microphone(folder, device, epoch_ns, files=self.files)


class Microphone:
    def __init__(self, folder, device, epoch, *, files=LOCAL_FILES):
        engine = shutil.which('arecord')
        if not engine:
            raise ValueError('Microphone recording requires ALSA arecord (install alsa-utils).')
        self.folder = folder
        self.files = files
        self.errors = (folder / 'microphone.log').open('w')
        self.data = {'version': 1, 'source': 'laptop microphone', 'device': device,
                     'sample_rate': RATE, 'channels': 1, 'subtype': 'PCM_16',
                     'offset_seconds': (time.monotonic_ns() - epoch) / 1e9,
                     'clock_notice': 'Sample zero is estimated at process launch; acoustic alignment is measured separately. Hardware latency and clock drift are not calibrated.'}
        try:
            write_metadata(folder, self.data, files=self.files)
            self.process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('microphone_capture.py')), str(os.getpid()), engine, '-q', '-D', device, '-t', 'raw', '-f', 'S16_LE',
                                             '-r', str(RATE), '-c', '1', str(folder / 'microphone.pcm')],
                                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=self.errors, start_new_session=True)
            time.sleep(.25)
            if self.process.poll() is not None:
                raise ValueError('Microphone input could not open. Check the system input, permissions and ALSA device. ' + (folder / 'microphone.log').read_text()[-1000:])
        except Exception:
            if hasattr(self, 'process') and self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
            self.errors.close()
            raise

    def running(self):
        return self.process.poll() is None

    def stop(self):
        unexpected = not self.running()
        # Keep errors already reported during capture, even if they resemble
        # the EINTR diagnostic arecord can emit when our SIGINT stops a read.
        prior_lines = (self.folder / 'microphone.log').read_text().splitlines()
        if not unexpected:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
                unexpected = True
        self.errors.close()
        lines = (self.folder / 'microphone.log').read_text().splitlines()
        log = '\n'.join(line for index, line in enumerate(lines)
                        if line.strip() not in ('Aborted by signal Interrupt...', 'Aborted by signal Terminated...')
                        and not (not unexpected and index >= len(prior_lines)
                                 and re.fullmatch(r'arecord: pcm_read:\d+: read error: Interrupted system call', line.strip())))
        self.data['capture_error'] = ('Microphone stopped unexpectedly or reported capture errors: ' + log[-1000:]) if unexpected or log.strip() else None
        write_metadata(self.folder, self.data, files=self.files)
        result = finalise(self.folder, self.data, files=self.files)
        if not result.get('duration'):
            raise ValueError('Microphone recording is empty; check the selected system input.')
        return result
