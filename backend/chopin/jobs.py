"""Explicit, cancellable background jobs; no rendering/AI on ordinary recording."""
import json
import logging
import os
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path

from .organisation import organise,analyse_segment
from .extraction import segment_midi

log=logging.getLogger(__name__)

class Jobs:
    def __init__(self,store):
        self.store=store;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='offline-practice')
        self.cancellations={}
        store.execute("UPDATE jobs SET status='failed',error='Application stopped before this job completed' WHERE status IN ('queued','running')")

    def submit(self,kind,action):
        ident=uuid.uuid4().hex;cancel=threading.Event();self.cancellations[ident]=cancel
        self.store.execute('INSERT INTO jobs(id,kind,status,created) VALUES(?,?,?,?)',(ident,kind,'queued',datetime.now(timezone.utc).isoformat()))
        def run():
            try:
                if cancel.is_set():raise InterruptedError('Cancelled')
                self.store.execute("UPDATE jobs SET status='running',progress=.1 WHERE id=?",(ident,))
                result=action(cancel,ident)
                if cancel.is_set():raise InterruptedError('Cancelled')
                self.store.execute("UPDATE jobs SET status='done',progress=1,result=? WHERE id=?",(json.dumps(result),ident))
            except InterruptedError:
                self.store.execute("UPDATE jobs SET status='cancelled',error='Cancelled' WHERE id=?",(ident,))
            except Exception as exc:
                log.exception('Background %s failed',kind)
                self.store.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",(str(exc),ident))
            finally:self.cancellations.pop(ident,None)
        self.pool.submit(run)
        return ident

    def organise(self,session_id,force=False):return self.submit('organisation',lambda cancel,ident:organise(self.store,session_id,force))

    def analysis(self,segment):
        def save(cancel,ident):
            result=analyse_segment(self.store,segment)
            self.store.execute('INSERT INTO analyses(id,session_id,segment_id,version,created,result) VALUES(?,?,?,?,?,?)',(ident,segment['session_id'],segment['id'],result['version'],datetime.now(timezone.utc).isoformat(),json.dumps(result)))
            return result
        return self.submit('analysis',save)

    def render(self,segment,soundfont,format='wav',rate=44100,gain=.6,reverb=True):
        def action(cancel,ident):
            engine=shutil.which('fluidsynth')
            if not engine:raise ValueError('FluidSynth is not installed; original MIDI is safe')
            font=Path(soundfont).expanduser()
            if not font.is_file() or font.suffix.lower() not in ('.sf2','.sf3'):raise ValueError('Choose an installed SF2/SF3 soundfont')
            midi=segment_midi(self.store,segment,for_audio=True)
            # A generated copy owns its release tail. The immutable source is untouched.
            import mido
            file=mido.MidiFile(midi)
            file.tracks[0][-1].time+=6000
            tail=midi.with_name('with_tail.mid');file.save(tail)
            wav=self.store.root/'audio'/(ident+'.wav')
            logfile=self.store.root/'audio'/(ident+'.log')
            output=None
            try:
                with logfile.open('w') as stderr:
                    process=subprocess.Popen([engine,'-ni','-F',str(wav),'-T','wav','-r',str(rate),'-g',str(gain),
                                              '-o','synth.reverb.active='+('1' if reverb else '0'),str(font),str(tail)],stdout=stderr,stderr=stderr)
                    try:
                        if hasattr(__import__('resource'), 'prlimit'):
                            import resource
                            budget=int(os.environ.get('CHOPIN_RENDER_MEMORY_MB','2048'))*1024*1024
                            try:resource.prlimit(process.pid,resource.RLIMIT_AS,(budget,budget))
                            except ProcessLookupError:pass  # renderer already completed
                        while process.poll() is None:
                            if cancel.wait(.2):
                                process.terminate()
                                try:process.wait(5)
                                except subprocess.TimeoutExpired:process.kill();process.wait()
                                raise InterruptedError('Cancelled')
                        if process.returncode:raise ValueError('FluidSynth failed. See '+str(logfile))
                    finally:
                        if process.poll() is None:process.kill();process.wait()
                if not wav.exists():raise ValueError('Renderer produced no output')
                output=wav
                if format=='flac':
                    import soundfile as sf
                    output=wav.with_suffix('.flac')
                    with sf.SoundFile(wav) as source,sf.SoundFile(output,'w',samplerate=source.samplerate,channels=source.channels,format='FLAC',subtype='PCM_16') as target:
                        for block in source.blocks(blocksize=16384):
                            if cancel.is_set():raise InterruptedError('Cancelled')
                            target.write(block)
                    wav.unlink()
                return {'filename':output.name,'segment_id':segment['id'],'session_id':segment['session_id'],'engine':'FluidSynth','soundfont':font.name,'format':format,'rate':rate}
            except Exception:
                wav.unlink(missing_ok=True)
                if output:output.unlink(missing_ok=True)
                raise
        return self.submit('render',action)

    def close(self):
        for cancel in list(self.cancellations.values()):cancel.set()
        self.pool.shutdown(wait=True,cancel_futures=False)
