"""Explicit, cancellable background jobs; no rendering/AI on ordinary recording."""
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime,timezone

from .organisation import organise,analyse_segment
from .extraction import segment_midi
from .midi_files import playback_messages
from .midi_playback import play_messages
from .platform.files import staging_path
from .platform.interfaces import AudioPlayback, AudioRenderer, HardwareAudio, MidiOutputDriver

log=logging.getLogger(__name__)

class Jobs:
    def __init__(
        self, store, *, renderer: AudioRenderer | None = None,
        hardware_audio: HardwareAudio | None = None,
        midi_output: MidiOutputDriver | None = None,
    ):
        self.renderer = renderer
        self.hardware_audio = hardware_audio
        self.midi_output = midi_output
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

    def organise(self,session_id,force=False):
        def action(cancel,ident):
            segments=organise(self.store,session_id,force)
            for segment in segments:
                if cancel.is_set():raise InterruptedError('Cancelled')
                self.save_analysis(segment,uuid.uuid4().hex)
            from .headphone_audio import mark_reviewed
            mark_reviewed(self.store.root/'sessions'/session_id, files=self.store.files)
            return segments
        return self.submit('organisation',action)

    def save_analysis(self,segment,ident):
        from .retention import deleted
        if deleted(self.store,segment['id']) or not self.store.query('SELECT id FROM segments WHERE id=?',(segment['id'],)):
            raise ValueError('Recording was deleted before analysis could run')
        result=analyse_segment(self.store,segment)
        from .retention import discard_unheard_microphone
        try:
            if discard_unheard_microphone(self.store, segment, result):
                result['audio'].update(available=False, discarded_for_headphone_play=True,
                    notice='No discernible piano during MIDI playing: microphone audio discarded; MIDI retained. This audio does not count toward the two-take limit.')
        except Exception:
            log.exception('Headphone microphone cleanup deferred for %s', segment['id'])
            result['audio']['discard_pending'] = True
        result['segment_snapshot']={key:segment.get(key) for key in ('id','piece_id','start','end','revision','discarded','complete')}
        created=datetime.now(timezone.utc).isoformat()
        self.store.execute('INSERT INTO analyses(id,session_id,segment_id,version,created,result) VALUES(?,?,?,?,?,?)',(ident,segment['session_id'],segment['id'],result['version'],created,json.dumps(result)))
        path=self.store.root/'reports'/(ident+'.json')
        with staging_path(self.store.files, path) as temporary:
            temporary.write_text(json.dumps({'analysis_id':ident,'session_id':segment['session_id'],'created':created,**result},indent=2))
            self.store.files.replace(temporary, path)
        return result

    def analysis(self,segment):
        def save(cancel,ident):
            return self.save_analysis(segment,ident)
        return self.submit('analysis',save)

    def render(self, segment, soundfont, format='wav', rate=44100, gain=.6, reverb=True):
        def action(cancel, ident):
            if self.renderer is None:
                raise ValueError('Audio rendering is unavailable on this host; original MIDI is safe')
            midi = segment_midi(self.store, segment, for_audio=True)
            wav = self.store.root / 'audio' / (ident + '.wav')
            result = self.renderer.render(midi, wav, cancel, soundfont=soundfont,
                                          format=format, rate=rate, gain=gain, reverb=reverb)
            return {**result, 'segment_id': segment['id'], 'session_id': segment['session_id']}
        return self.submit('render', action)

    def audio_engines(self):
        if self.renderer is not None:
            return self.renderer.engines()
        return {'fluidsynth': None, 'soundfonts': [],
                'external_engines': {'sfizz': None, 'pianoteq': None}}

    def playback_status(self):
        try:
            ports = self.midi_output.outputs() if self.midi_output is not None else []
            error = None
        except Exception as exc:
            ports = []
            error = str(exc)
        return {'ports': ports, 'error': error, 'capture_available': (
            self.hardware_audio is not None and self.hardware_audio.capture_available()
        )}

    def playback(self, recorder, segment, port, device):
        if self.hardware_audio is None and (device or self.midi_output is None):
            raise ValueError('Hardware playback is unavailable on this host')
        if recorder.active or recorder.saving:
            raise ValueError('Stop recording before hardware playback')

        def action(cancel, ident):
            with recorder.playback():
                midi = segment_midi(self.store, segment, for_audio=True)
                wav = self.store.root / 'audio' / (ident + '.wav')
                if self.hardware_audio is not None:
                    result = self.hardware_audio.play(midi, wav, port, device, cancel)
                else:
                    with closing(self.midi_output.open_output(port)) as output:
                        play_messages(output, playback_messages(midi), cancel)
                    result = AudioPlayback(None, 'playback')
                return {'filename': result.filename, 'session_id': segment['session_id'],
                        'segment_id': segment['id'], 'engine': result.engine,
                        'format': result.format, 'port': port, 'capture_device': device}
        return self.submit('render', action)

    def drain(self):
        self.pool.submit(lambda: None).result()

    def close(self):
        for cancel in list(self.cancellations.values()):cancel.set()
        self.pool.shutdown(wait=True,cancel_futures=False)
