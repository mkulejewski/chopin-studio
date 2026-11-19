"""Linux audio tools: FluidSynth rendering and optional stereo ALSA capture."""

import os
import resource
import shutil
import signal
import subprocess
import wave
from pathlib import Path

import soundfile as sf

from ...midi_files import add_render_tail, playback_messages
from ...midi_playback import play_messages
from ..files import staging_path
from ..interfaces import AudioPlayback, MidiOutputDriver


class LinuxHardwareAudio:
    def __init__(self, midi: MidiOutputDriver):
        self.midi = midi

    def capture_available(self):
        return shutil.which('arecord') is not None

    def play(self, midi, wav, port, device, cancel):
        log = wav.with_suffix('.log')
        process = None
        output = self.midi.open_output(port)
        success = False

        def check():
            if process and process.poll() is not None:
                raise ValueError('Audio capture stopped unexpectedly; see ' + str(log))

        try:
            with log.open('w') as errors:
                if device:
                    engine = shutil.which('arecord')
                    if not engine:
                        raise ValueError('Install ALSA arecord for audio-interface capture, or use the piano USB flash recorder')
                    process = subprocess.Popen(
                        [engine, '-D', device, '-t', 'wav', '-f', 'S16_LE',
                         '-r', '44100', '-c', '2', str(wav)],
                        stdout=errors, stderr=errors,
                    )
                    if cancel.wait(.5):
                        raise InterruptedError('Cancelled')
                    if process.poll() is not None:
                        raise ValueError('Audio input did not open. Check the selected ALSA device and ' + str(log))
                play_messages(output, playback_messages(midi), cancel, check)
                if process:
                    stop_process(process, signal.SIGINT)
            if device:
                with wave.open(str(wav)) as recording:
                    if not recording.getnframes():
                        raise ValueError('Audio capture is empty')
            success = True
            engine = 'AP-470 physical piano' if 'ap-470' in port.casefold() else 'MIDI instrument'
            return AudioPlayback(wav.name if device else None, 'wav' if device else 'playback', engine)
        finally:
            try:
                output.close()
            finally:
                if process and process.poll() is None:
                    process.kill()
                    process.wait()
                if not success:
                    wav.unlink(missing_ok=True)


def stop_process(process, signum):
    if process.poll() is None:
        process.send_signal(signum)
        try:
            process.wait(5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


class FluidSynth:
    def __init__(self, files):
        self.files = files

    def engines(self):
        return {
            'fluidsynth': shutil.which('fluidsynth'),
            'soundfonts': [
                str(path)
                for directory in ('/usr/share/sounds/sf2', '/usr/share/sounds/sf3')
                for path in Path(directory).glob('*')
                if path.suffix in ('.sf2', '.sf3')
            ],
            'external_engines': {
                'sfizz': shutil.which('sfizz_render'),
                'pianoteq': shutil.which('pianoteq'),
            },
        }

    def render(self, midi, wav, cancel, *, soundfont, format, rate, gain, reverb):
        engine = shutil.which('fluidsynth')
        if not engine:
            raise ValueError('FluidSynth is not installed; original MIDI is safe')
        font = Path(soundfont).expanduser()
        if not font.is_file() or font.suffix.lower() not in ('.sf2', '.sf3'):
            raise ValueError('Choose an installed SF2/SF3 soundfont')
        logfile = wav.with_suffix('.log')
        output = wav
        try:
            with staging_path(self.files, midi, suffix='.mid') as tail:
                # A generated copy owns its release tail. The source is immutable.
                add_render_tail(midi, tail)
                with logfile.open('w') as stderr:
                    process = subprocess.Popen(
                        [engine, '-ni', '-F', str(wav), '-T', 'wav', '-r', str(rate),
                         '-g', str(gain), '-o', 'synth.reverb.active=' + ('1' if reverb else '0'),
                         str(font), str(tail)], stdout=stderr, stderr=stderr,
                    )
                    try:
                        if hasattr(resource, 'prlimit'):
                            budget = int(os.environ.get('CHOPIN_RENDER_MEMORY_MB', '2048')) * 1024 * 1024
                            try:
                                resource.prlimit(process.pid, resource.RLIMIT_AS, (budget, budget))
                            except ProcessLookupError:
                                pass  # Renderer already completed.
                        while process.poll() is None:
                            if cancel.wait(.2):
                                stop_process(process, signal.SIGTERM)
                                raise InterruptedError('Cancelled')
                        if process.returncode:
                            raise ValueError('FluidSynth failed. See ' + str(logfile))
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
            if not wav.exists():
                raise ValueError('Renderer produced no output')
            if format == 'flac':
                output = wav.with_suffix('.flac')
                with sf.SoundFile(wav) as source, sf.SoundFile(
                    output, 'w', samplerate=source.samplerate, channels=source.channels,
                    format='FLAC', subtype='PCM_16',
                ) as target:
                    for block in source.blocks(blocksize=16384):
                        if cancel.is_set():
                            raise InterruptedError('Cancelled')
                        target.write(block)
                wav.unlink()
            return {'filename': output.name, 'engine': 'FluidSynth', 'soundfont': font.name,
                    'format': format, 'rate': rate}
        except Exception:
            wav.unlink(missing_ok=True)
            output.unlink(missing_ok=True)
            raise
