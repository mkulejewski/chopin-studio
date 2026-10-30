"""Explicit real-time AP-470 MIDI playback and optional ALSA audio capture."""
import signal
import shutil
import subprocess
import time
import wave
import mido
from .extraction import segment_midi


def play(store,segment,port,capture_device,cancel,ident):
    path=segment_midi(store,segment,for_audio=True)
    wav=store.root/'audio'/(ident+'.wav');log=wav.with_suffix('.log')
    process=None;success=False
    try:
        with mido.open_output(port) as output,log.open('w') as errors:
            try:
                if capture_device:
                    engine=shutil.which('arecord')
                    if not engine:raise ValueError('Install ALSA arecord for audio-interface capture, or use the piano USB flash recorder')
                    process=subprocess.Popen([engine,'-D',capture_device,'-t','wav','-f','S16_LE','-r','44100','-c','2',str(wav)],stdout=errors,stderr=errors)
                    if cancel.wait(.5):raise InterruptedError('Cancelled')
                    if process.poll() is not None:raise ValueError('Audio input did not open. Check the selected ALSA device and '+str(log))
                # MidiFile iteration converts the tempo map into seconds. Absolute
                # deadlines avoid accumulating USB-send and scheduling overhead.
                deadline=time.monotonic()
                for message in mido.MidiFile(path):
                    deadline+=message.time
                    if cancel.wait(max(0,deadline-time.monotonic())):raise InterruptedError('Cancelled')
                    if process and process.poll() is not None:raise ValueError('Audio capture stopped unexpectedly; see '+str(log))
                    if not message.is_meta:output.send(message.copy(time=0))
                if cancel.wait(3):raise InterruptedError('Cancelled')
                if process and process.poll() is not None:raise ValueError('Audio capture stopped unexpectedly; see '+str(log))
            finally:
                # Release pedals as well as sounding notes, including on cancellation.
                for channel in range(16):
                    for controller in (64,66,67,123,120):
                        output.send(mido.Message('control_change',channel=channel,control=controller,value=0))
                if process and process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:process.wait(5)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
        if capture_device:
            with wave.open(str(wav)) as recording:
                if recording.getnframes()==0:raise ValueError('Audio capture is empty')
        success=True
        return {'filename':wav.name if capture_device else None,'session_id':segment['session_id'],'segment_id':segment['id'],
                'engine':'AP-470 physical piano','format':'wav' if capture_device else 'playback','port':port,'capture_device':capture_device}
    finally:
        if process and process.poll() is None:
            process.kill();process.wait()
        if not success:wav.unlink(missing_ok=True)
