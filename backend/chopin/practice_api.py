"""Organisation, reference quality, jobs and live-following HTTP boundaries."""
import json
import math
import os
import shutil
import uuid
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal

from fastapi import HTTPException,UploadFile
from fastapi.responses import FileResponse,PlainTextResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel,Field

from .symbolic import import_reference,reference_info
from .organisation import save_history,performance_notes
from .midi_files import journal_events
from .extraction import segment_midi

class SegmentEdit(BaseModel):
    id:str=Field(pattern='^[a-f0-9]{32}$')
    start:float=Field(ge=0)
    end:float=Field(gt=0)
    piece_id:str|None=None
    label:str=Field(max_length=200)
    confidence:float=Field(default=0,ge=0,le=1)
    first_measure:int|None=Field(default=None,ge=0)
    last_measure:int|None=Field(default=None,ge=0)
    kind:Literal['unknown','partial','exercise','full_exercise','complete']='unknown'
    group_id:str|None=Field(default=None,max_length=80)
    complete:bool=False
    discarded:bool=False
    revision:int=1
    details:str='{}'

class TimelineEdit(BaseModel):
    segments:list[SegmentEdit]=Field(max_length=1000)
    expected_revision:int

class RecordingChoice(BaseModel):
    choice:Literal['auto','keep','remove']='auto'
    complete:bool|None=None

class DeleteRecording(BaseModel):
    confirmation:Literal['delete']
    revision:int|None=None

class LiveContext(BaseModel):
    piece_id:str|None=None

class ReferenceUpdate(BaseModel):
    quality:Literal['provisional','verified','rejected']='provisional'
    edition:str=Field(max_length=500)
    notes:list[dict]|None=None

class PageMap(BaseModel):
    measure:int=Field(ge=0)
    pdf_page:int=Field(ge=1)

class RenderRequest(BaseModel):
    soundfont:str=Field(max_length=2000)
    format:Literal['wav','flac']='wav'
    rate:Literal[22050,44100,48000]=44100
    gain:float=Field(default=.6,ge=.05,le=2)
    reverb:bool=True

class HardwareRender(BaseModel):
    port:str=Field(min_length=1,max_length=300)
    capture_device:str=Field(default='',max_length=300)

class AiKey(BaseModel):
    api_key:str=Field(min_length=10,max_length=1000)

class ReportEdit(BaseModel):
    text:str=Field(min_length=1,max_length=100000)

class TeacherRequest(BaseModel):
    provider:Literal['local','openai']='local'
    question:str=Field(default='Suggest concrete practice priorities from the evidence.',max_length=2000)
    model:str=Field(default='gpt-4.1-mini',max_length=100)


class VoicingTarget(BaseModel):
    roles:dict[str,Literal['bass','inner','melody','unassigned']]=Field(default_factory=dict,max_length=100)
    melody_min_gap:float|None=Field(default=None,ge=-127,le=127)
    release_calibrated:bool=False

class ObjectiveRequest(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    category:Literal['tempo','rhythm','voicing','dynamics','articulation','pedal','memory','other']='other'
    first_measure:int|None=Field(default=None,ge=0)
    last_measure:int|None=Field(default=None,ge=0)
    completed:bool=False
    revision:int=1

class ProblemTime(BaseModel):
    segment_id:str
    start:float=Field(ge=0,allow_inf_nan=False)
    end:float=Field(gt=0,allow_inf_nan=False)


def attach_practice_routes(app,store,recorder,jobs,live,save_upload):
    def session(ident):
        rows=store.query('SELECT * FROM sessions WHERE id=?',(ident,))
        if not rows:raise HTTPException(404,'Session not found')
        if rows[0]['status'] in ('recording','saving'):raise HTTPException(409,'Finish saving this session first')
        return rows[0]

    def segment(ident):
        rows=store.query('SELECT * FROM segments WHERE id=?',(ident,))
        if not rows:raise HTTPException(404,'Segment not found')
        session(rows[0]['session_id'])
        from .retention import deleted
        if deleted(store,ident):raise HTTPException(410,'This recording was permanently removed')
        return rows[0]

    def deletion_ready():
        if recorder.active or recorder.saving or recorder.hardware_playback:
            raise HTTPException(409,'Stop recording/playback and finish saving before deleting.')
        if store.query("SELECT id FROM jobs WHERE status IN ('queued','running')"):
            raise HTTPException(409,'Wait for background analysis/rendering to finish, then delete.')

    @app.get('/api/recordings')
    def recordings():
        from .retention import catalogue, session_audio_bytes, rendered_assets
        # File inventory and job payload decoding must not be repeated for every
        # session. Total artifact sizes are unused by the audio cleanup screen.
        takes = catalogue(store)
        with store.lock:
            sessions = store.query('SELECT * FROM sessions ORDER BY started DESC')
            locked_sessions = {row['session_id'] for row in store.query(
                "SELECT DISTINCT session_id FROM recording_deletions WHERE scope='recording'")}
            segments = store.query('SELECT id,session_id FROM segments')
            renders = rendered_assets(store)
        grouped = {}
        for row in segments:
            grouped.setdefault(row['session_id'], []).append(row['id'])
        for record in sessions:
            record['timeline_locked'] = record['id'] in locked_sessions
            record['audio_bytes'] = session_audio_bytes(store, record['id'], renders, grouped.get(record['id'], []))
        return {'takes':takes,'sessions':sessions,'policy':'Keep audio for two complete or near-complete takes per piece. MIDI is kept indefinitely; flagged audio, including partial attempts and recordings with capture errors, is removed at application shutdown. MIDI playing without discernible piano audio is detected after analysis; its microphone audio is discarded and excluded from the two-take limit. Uncertain audio stays for manual review. Keep flags protect any take.'}

    @app.get('/api/recordings/library')
    def recordings_library():
        # Availability follows retained microphone spans and existing rendered files,
        # never metadata alone. Cache file layouts once per session.
        from .microphone import audio_layout
        from .retention import audio_assets, rendered_assets
        import soundfile as sf
        with store.lock:
            sessions = store.query("""SELECT s.*,a.piece_id AS learning_piece_id
                FROM sessions s LEFT JOIN learning_attempts a ON a.session_id=s.id
                WHERE s.status IN ('saved','imported','recovered','incomplete')
                ORDER BY s.started DESC,s.id DESC""")
            segments = store.query("""SELECT s.id,s.session_id,s.piece_id,s.start,s.end,s.kind,s.discarded
                FROM segments s JOIN sessions ps ON ps.id=s.session_id
                WHERE ps.status IN ('saved','imported','recovered','incomplete')
                AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id
                    AND d.scope='recording') ORDER BY s.start,s.id""")
            segmented = {r['session_id'] for r in store.query('SELECT DISTINCT session_id FROM segments')}
            renders = rendered_assets(store)
            render_urls = {}
            for job in store.query("SELECT id,result FROM jobs WHERE kind='render' AND status='done' AND result IS NOT NULL"):
                result = json.loads(job['result'])
                if isinstance(result, dict) and result.get('filename'):
                    render_urls[result['filename']] = '/api/audio/' + job['id']
            layouts, rates = {}, {}
            for session in sessions:
                ident = session['id']
                try:
                    layouts[ident] = audio_layout(store.root/'sessions'/ident)
                    path, _ = layouts[ident]
                    if path:
                        rates[ident] = sf.info(path).samplerate
                except (OSError, RuntimeError, ValueError):
                    layouts[ident] = (None, [])
                path, spans = layouts[ident]
                session['audio_sources'] = ([{'label': 'Recorded microphone', 'url': f'/api/sessions/{ident}/microphone'}]
                    if ident not in segmented and path and any(span['frames'] > 0 for span in spans) else [])
            available = []
            for row in segments:
                microphone, files = audio_assets(store, row, layouts[row['session_id']], renders, rates.get(row['session_id']))
                sources = ([{'label': 'Recorded microphone', 'url': f"/api/segments/{row['id']}/microphone"}] if microphone else [])
                sources += [{'label': 'Rendered MIDI audio', 'url': render_urls[path.name]} for path in files]
                if sources:
                    available.append({**row, 'audio_sources': sources})
            audible_sessions = {row['session_id'] for row in available}
            sessions = [s for s in sessions if s['id'] in audible_sessions or s['audio_sources']]
        return {'sessions': sessions, 'segments': available}

    @app.put('/api/recordings/{ident}')
    def recording_choice(ident:str,body:RecordingChoice):
        from .retention import eligibility, current_analysis, audio_assets
        with store.lock:
            row = segment(ident)
            microphone,files = audio_assets(store,row)
            if not microphone and not files:raise ValueError('This take has no saved audio to flag. MIDI is retained indefinitely.')
            if body.complete is not None:
                row = {**row,'complete':int(body.complete),'kind':'complete' if body.complete else 'partial'}
            if body.complete is not None:
                store.execute('UPDATE segments SET complete=?,kind=?,revision=revision+1 WHERE id=?',(row['complete'],row['kind'],ident))
            store.execute('INSERT INTO recording_choices(segment_id,choice) VALUES(?,?) ON CONFLICT(segment_id) DO UPDATE SET choice=excluded.choice',(ident,body.choice))
            if body.complete is not None:jobs.analysis(segment(ident))
        return {'ok':True}

    @app.delete('/api/recordings/{ident}')  # Compatibility: cleanup is now always audio-only.
    @app.delete('/api/recordings/{ident}/audio')
    def remove_take(ident:str,body:DeleteRecording):
        from .retention import delete_take
        with store.lock:
            deletion_ready()
            row = segment(ident)
            if body.revision != row['revision']:raise HTTPException(409,'Recording changed. Refresh before deleting.')
            delete_take(store,row)
        return {'ok':True}

    @app.delete('/api/sessions/{ident}')
    def remove_session(ident:str,body:DeleteRecording):
        from .retention import delete_session
        with store.lock:
            deletion_ready()
            session(ident)
            delete_session(store,ident)
        return {'ok':True}

    @app.get('/api/ai/config')
    def ai_config():
        return {'configured':bool(os.environ.get('OPENAI_API_KEY') or (store.root/'openai-key').exists()),'environment':bool(os.environ.get('OPENAI_API_KEY'))}

    @app.put('/api/ai/config')
    def ai_key(body:AiKey):
        path=store.root/'openai-key';temporary=store.root/'openai-key.tmp'
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as output:
            output.write(body.api_key);output.flush();os.fsync(output.fileno())
        os.chmod(temporary,0o600);os.replace(temporary,path)
        return {'configured':True}

    @app.post('/api/reports/{ident}/revision')
    def revise_report(ident:str,body:ReportEdit):
        rows=store.query('SELECT * FROM reports WHERE id=?',(ident,))
        if not rows:raise HTTPException(404,'Report not found')
        old=rows[0];new=uuid.uuid4().hex
        store.execute('INSERT INTO reports VALUES(?,?,?,?,?,?)',(new,old['session_id'],'user-edited',datetime.now(timezone.utc).isoformat(),body.text,old['evidence']))
        return {'id':new}

    @app.get('/api/pieces/{ident}/references')
    def references(ident:str):return reference_info(store,ident)

    @app.get('/api/pieces/{ident}/sessions')
    def piece_sessions(ident:str,include_flagged:bool=False):
        if not store.query('SELECT id FROM pieces WHERE id=?',(ident,)):
            raise HTTPException(404,'Piece not found')
        with store.lock:
            rows=store.query('''SELECT DISTINCT ps.* FROM sessions ps
                JOIN segments s ON s.session_id=ps.id
                WHERE s.piece_id=? AND s.discarded=0 AND ps.status NOT IN ('recording','saving','recovery_failed')
                ORDER BY ps.started DESC,ps.id DESC''',(ident,))
            segments=store.query('''SELECT s.* FROM segments s JOIN sessions ps ON ps.id=s.session_id
                WHERE s.piece_id=? AND s.discarded=0 AND ps.status NOT IN ('recording','saving','recovery_failed')
                ORDER BY s.start,s.id''',(ident,))
        from .retention import catalogue
        decisions={take['id']:take for take in catalogue(store, piece_id=ident)} if segments else {}
        segments=[{**item,'audio_retention_action':decisions.get(item['id'],{}).get('action')} for item in segments]
        grouped={}
        for item in segments:grouped.setdefault(item['session_id'],[]).append(item)
        return [{**row,'segments':grouped[row['id']]} for row in rows if row['id'] in grouped]

    @app.post('/api/pieces/{ident}/references')
    async def reference_import(ident:str,file:UploadFile):
        suffix=Path(file.filename or '').suffix.lower()
        if suffix not in ('.musicxml','.xml','.mxl'):raise ValueError('Choose MusicXML, XML or MXL')
        path=await save_upload(file,store.root/'imports',suffix)
        try:ref=import_reference(store,ident,path.read_bytes(),suffix)
        except Exception as exc:raise ValueError('Reference import failed: '+str(exc)) from exc
        finally:path.unlink(missing_ok=True)
        live.signature=None
        return {'id':ref}

    @app.get('/api/references/{ident}')
    def reference(ident:str):
        row=store.query('SELECT * FROM symbolic_scores WHERE id=?',(ident,))
        if not row:raise HTTPException(404,'Reference not found')
        return {**row[0],'notes':json.loads(row[0]['notes'])}

    @app.get('/api/references/{ident}/musicxml')
    def reference_download(ident:str):
        ref=reference(ident)
        if not ref['filename'].endswith('.musicxml'):raise ValueError('This reference is a labelled MIDI performance, not MusicXML')
        return FileResponse(store.root/'references'/ref['filename'],media_type='application/vnd.recordare.musicxml+xml',filename=ref['piece_id']+'.musicxml')

    @app.put('/api/references/{ident}')
    def edit_reference(ident:str,update:ReferenceUpdate):
        ref=reference(ident)
        if update.quality=='verified' and not ref['filename'].endswith('.musicxml'):raise ValueError('A labelled MIDI reference cannot be verified as a score')
        notes=ref['notes'] if update.notes is None else update.notes
        if not notes or len(notes)>100000:raise ValueError('Reference must contain 1–100,000 notes')
        for n in notes:
            if not isinstance(n.get('pitch'),int) or not 0<=n['pitch']<=127 or not isinstance(n.get('onset'),(int,float)) or not math.isfinite(n['onset']) or n['onset'] < -1024:
                raise ValueError('Every note needs a MIDI pitch and finite score onset (pickup beats may be negative)')
            if not isinstance(n.get('duration'),(int,float)) or not math.isfinite(n['duration']) or n['duration']<0 or not isinstance(n.get('measure'),int):raise ValueError('Every note needs a duration and integer measure')
        notes.sort(key=lambda n:(n['onset'],n['pitch']))
        # Revision copy preserves former reference evidence; the XML download is
        # the original source, while the corrected analysis representation is JSON.
        if update.notes is not None:
            (store.root/'references'/(ident+'.previous-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(ref['notes']))
        store.execute('UPDATE symbolic_scores SET quality=?,edition=?,notes=? WHERE id=?',(update.quality,update.edition,json.dumps(notes),ident))
        live.signature=None
        return {'ok':True}

    @app.get('/api/pieces/{ident}/pages')
    def pages(ident:str):return store.query('SELECT * FROM page_maps WHERE piece_id=? ORDER BY measure',(ident,))

    @app.put('/api/pieces/{ident}/pages')
    def page_map(ident:str,mapping:list[PageMap]):
        piece=store.query('SELECT p.*,v.pages AS pdf_pages FROM pieces p JOIN volumes v ON p.volume_id=v.id WHERE p.id=?',(ident,))
        if not piece:raise ValueError('Unknown piece')
        if any(p.pdf_page>(piece[0]['pdf_pages'] or 0) for p in mapping):raise ValueError('Page map requires an imported PDF and valid page numbers')
        with store.lock:
            try:
                store.db.execute('DELETE FROM page_maps WHERE piece_id=?',(ident,))
                for item in mapping:store.db.execute('INSERT INTO page_maps VALUES(?,?,?)',(ident,item.measure,item.pdf_page))
                store.db.commit()
            except Exception:
                store.db.rollback()
                raise ValueError('Invalid page map; no links were changed')
        return {'ok':True}

    @app.get('/api/sessions/{ident}/segments')
    def timeline(ident:str):
        session(ident)
        from .retention import deleted
        return [{**row,'recording_deleted':deleted(store,row['id'])} for row in store.query('SELECT * FROM segments WHERE session_id=? ORDER BY start',(ident,))]

    @app.post('/api/sessions/{ident}/organise')
    def organise(ident:str,force:bool=False):
        session(ident)
        from .retention import locked
        if locked(store,ident):raise HTTPException(409,'Removed intervals cannot be restored. This timeline is locked.')
        return {'job_id':jobs.organise(ident,force)}

    @app.put('/api/sessions/{ident}/segments')
    def edit_timeline(ident:str,body:TimelineEdit):
        record=session(ident)
        from .retention import locked
        if locked(store,ident):raise HTTPException(409,'Removed intervals cannot be restored. This timeline is locked; completeness can still be changed in recording cleanup.')
        rows=timeline(ident);revision=max((r['revision'] for r in rows),default=0)
        if revision!=body.expected_revision:raise HTTPException(409,'Timeline changed. Reload before editing.')
        ordered=sorted(body.segments,key=lambda s:s.start)
        for i,item in enumerate(ordered):
            if item.end<=item.start or item.end>record['duration']+.001:raise ValueError('Bounds must be ordered and within the original recording')
            if i and item.start<ordered[i-1].end:raise ValueError('Timeline segments cannot overlap')
            if item.piece_id and not store.query('SELECT id FROM pieces WHERE id=?',(item.piece_id,)):raise ValueError('Unknown piece')
            if item.first_measure is not None and item.last_measure is not None and item.first_measure>item.last_measure:raise ValueError('Measure range is reversed')
            owner=store.query('SELECT session_id FROM segments WHERE id=?',(item.id,))
            if owner and owner[0]['session_id']!=ident:raise ValueError('Segment belongs to another session')
        with store.lock:
            choices=store.query('SELECT c.* FROM recording_choices c JOIN segments s ON s.id=c.segment_id WHERE s.session_id=?',(ident,))
            protected=store.query("SELECT s.start,s.end FROM segments s JOIN recording_choices c ON c.segment_id=s.id WHERE s.session_id=? AND c.choice='keep'",(ident,))
            locked_revision=store.db.execute('SELECT MAX(revision) FROM segments WHERE session_id=?',(ident,)).fetchone()[0] or 0
            if locked_revision!=body.expected_revision:raise HTTPException(409,'Timeline changed. Reload before editing.')
            save_history(store,ident)
            store.db.execute('DELETE FROM segments WHERE session_id=?',(ident,))
            for item in ordered:
                fields={**item.model_dump(),'session_id':ident,'revision':revision+1}
                if item.kind=='full_exercise':fields['complete']=True
                fields['details']=json.dumps({'manual_correction':True})
                keys=list(fields)
                store.db.execute('INSERT INTO segments('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(fields.values()))
            for choice in choices:
                if any(item.id==choice['segment_id'] for item in ordered):
                    store.db.execute('INSERT INTO recording_choices(segment_id,choice,deleted) VALUES(?,?,?)',(choice['segment_id'],choice['choice'],choice['deleted']))
            for row in store.query('SELECT id,start,end FROM segments WHERE session_id=?',(ident,)):
                if any(min(row['end'],r['end'])>max(row['start'],r['start']) for r in protected):
                    store.db.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep') ON CONFLICT(segment_id) DO UPDATE SET choice='keep'",(row['id'],))
            store.db.commit()
        updated=timeline(ident)
        for row in updated:jobs.analysis(row)
        return updated

    @app.post('/api/sessions/{ident}/segments/undo')
    def undo(ident:str):
        session(ident)
        from .retention import locked
        if locked(store,ident):raise HTTPException(409,'Deleted recordings cannot be restored by undo.')
        history=store.query('SELECT * FROM segment_history WHERE session_id=? ORDER BY id DESC LIMIT 1',(ident,))
        if not history:raise ValueError('No timeline edit to undo')
        revision=max((r['revision'] for r in timeline(ident)),default=0)+1
        with store.lock:
            protected=store.query("SELECT s.start,s.end FROM segments s JOIN recording_choices c ON c.segment_id=s.id WHERE s.session_id=? AND c.choice='keep'",(ident,))
            store.db.execute('DELETE FROM segments WHERE session_id=?',(ident,))
            for row in json.loads(history[0]['snapshot']):
                row['revision']=revision;keys=list(row)
                store.db.execute('INSERT INTO segments('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(row.values()))
            for row in store.query('SELECT id,start,end FROM segments WHERE session_id=?',(ident,)):
                if any(min(row['end'],r['end'])>max(row['start'],r['start']) for r in protected):
                    store.db.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(row['id'],))
            store.db.execute('DELETE FROM segment_history WHERE id=?',(history[0]['id'],));store.db.commit()
        updated=timeline(ident)
        for row in updated:jobs.analysis(row)
        return updated

    @app.get('/api/segments/{ident}/audio-status')
    def segment_audio_status(ident:str):
        from .retention import audio_assets
        microphone,files = audio_assets(store,segment(ident))
        return {'microphone':microphone,'rendered_audio_count':len(files)}

    @app.get('/api/segments/{ident}/microphone')
    def microphone_segment(ident:str):
        from .microphone import export_audio, export_stem
        row = segment(ident)
        path = export_audio(store,row)
        return FileResponse(path, media_type='audio/flac', filename=export_stem(store,row)+'__microphone.flac', background=BackgroundTask(path.unlink,missing_ok=True))

    @app.get('/api/segments/{ident}/midi')
    def export_segment(ident:str):
        row=segment(ident);path=segment_midi(store,row)
        from .microphone import export_stem
        return FileResponse(path,media_type='audio/midi',filename=export_stem(store,row)+'__midi.mid')

    @app.post('/api/segments/{ident}/learn')
    def learn(ident:str):
        row=segment(ident)
        if not row['piece_id']:raise ValueError('Assign a piece before saving a labelled MIDI reference')
        notes=performance_notes(journal_events(store.root/'sessions'/row['session_id']/'events.jsonl'))
        notes=[{**n,'onset':n['onset']-row['start'],'measure':None} for n in notes if row['start']<=n['onset']<row['end']]
        if len(notes)<8:raise ValueError('At least eight notes are needed')
        ref=uuid.uuid4().hex
        # MIDI-reference seconds can retrieve identity, but never score measures.
        path=segment_midi(store,row);shutil.copyfile(path,store.root/'references'/(ref+'.mid'))
        store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',(ref,row['piece_id'],ref+'.mid','Locally confirmed segment '+ident,'Private user recording','Labelled performance; no score-level measures','provisional',json.dumps(notes),datetime.now(timezone.utc).isoformat()))
        live.signature=None;return {'id':ref}

    @app.post('/api/segments/{ident}/analyse')
    def analyse(ident:str):return {'job_id':jobs.analysis(segment(ident))}

    @app.get('/api/sessions/{ident}/analyses')
    def analyses(ident:str):session(ident);return [{**row,'result':json.loads(row['result'])} for row in store.query('SELECT * FROM analyses WHERE session_id=? ORDER BY created DESC',(ident,))]

    @app.get('/api/jobs')
    def job_list():return store.query('SELECT * FROM jobs ORDER BY created DESC LIMIT 100')

    @app.post('/api/jobs/{ident}/cancel')
    def cancel(ident:str):
        flag=jobs.cancellations.get(ident)
        if flag:flag.set()
        return {'ok':True}

    @app.get('/api/pieces/{ident}/assessment')
    def assessment(ident:str):
        from .assessment import piece_assessment
        return piece_assessment(store,ident)

    @app.get('/api/sessions/{ident}/preanalysis')
    def preanalysis(ident:str):
        session(ident)
        from .teacher import evidence_for
        path=store.root/'reports'/(ident+'-preanalysis.json')
        payload=evidence_for(store,ident,analyses_limit=None)
        payload['schema_version']='practice-preanalysis-v1'
        # Unique temporary paths allow concurrent exports without partial JSON.
        temporary=path.with_name(uuid.uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(payload,indent=2));temporary.replace(path)
        return FileResponse(path,media_type='application/json',filename='practice-preanalysis.json')

    @app.get('/api/audio/hardware')
    def hardware():
        import mido
        try:ports=mido.get_output_names();error=None
        except Exception as exc:ports=[];error=str(exc)
        return {'ports':ports,'capture_available':bool(shutil.which('arecord')),'error':error}

    @app.post('/api/segments/{ident}/ap470')
    def ap470(ident:str,body:HardwareRender):
        row=segment(ident)
        # Capture stays authoritative; replay must not be mistaken for a new take.
        if recorder.active or recorder.saving:raise ValueError('Stop recording before hardware playback')
        from .hardware_audio import play
        def action(cancel,job):
            # Serialize the start check with Record session. Ignore keyboard loopback
            # while producing sound, then restore normal input handling.
            with recorder.lock:
                if recorder.active or recorder.saving:raise ValueError('Stop recording before hardware playback')
                recorder.hardware_playback=True
            try:return play(store,row,body.port,body.capture_device,cancel,job)
            finally:recorder.hardware_playback=False
        return {'job_id':jobs.submit('render',action)}

    @app.post('/api/segments/{ident}/audio')
    async def import_audio(ident:str,file:UploadFile):
        import wave
        row=segment(ident)
        path=await save_upload(file,store.root/'imports','.wav')
        try:
            try:
                with wave.open(str(path)) as recording:
                    if recording.getnframes()==0:raise ValueError('Empty WAV recording')
                    if recording.getnchannels()!=2 or recording.getsampwidth()!=2 or recording.getframerate()!=44100:
                        raise ValueError('Choose a stereo 16-bit 44.1 kHz WAV from the AP-470')
            except (wave.Error,EOFError) as exc:raise ValueError('Choose a PCM WAV recording') from exc
            job=uuid.uuid4().hex;destination=store.root/'audio'/(job+'.wav');path.replace(destination)
            result={'filename':destination.name,'segment_id':ident,'session_id':row['session_id'],'engine':'AP-470 imported WAV','format':'wav','alignment':'User attached; timing has not been verified'}
            store.execute('INSERT INTO jobs(id,kind,status,progress,created,result) VALUES(?,?,?,?,?,?)',(job,'render','done',1,datetime.now(timezone.utc).isoformat(),json.dumps(result)))
            return result
        finally:path.unlink(missing_ok=True)

    @app.get('/api/audio/engines')
    def engines():
        fonts=[str(p) for directory in ('/usr/share/sounds/sf2','/usr/share/sounds/sf3') for p in Path(directory).glob('*') if p.suffix in ('.sf2','.sf3')]
        return {'fluidsynth':shutil.which('fluidsynth'),'soundfonts':fonts,'external_engines':{'sfizz':shutil.which('sfizz_render'),'pianoteq':shutil.which('pianoteq')}}

    @app.post('/api/segments/{ident}/render')
    def render(ident:str,request:RenderRequest):return {'job_id':jobs.render(segment(ident),**request.model_dump())}

    @app.get('/api/audio/{ident}')
    def audio(ident:str):
        rows=store.query("SELECT * FROM jobs WHERE id=? AND kind='render' AND status='done'",(ident,))
        if not rows:raise HTTPException(404,'Finished render not found')
        result=json.loads(rows[0]['result'])
        if not result.get('filename'):raise HTTPException(404,'Playback completed without computer audio capture')
        path=store.root/'audio'/result['filename']
        if not path.exists():raise HTTPException(404,'Rendered audio was removed; original MIDI is retained')
        return FileResponse(path,media_type='audio/flac' if path.suffix=='.flac' else 'audio/wav')

    @app.delete('/api/audio/{ident}')
    def delete_audio(ident:str):
        rows=store.query("SELECT result FROM jobs WHERE id=? AND kind='render'",(ident,))
        if not rows:raise HTTPException(404,'Render not found')
        if rows[0]['result']:
            filename=json.loads(rows[0]['result']).get('filename')
            if filename:(store.root/'audio'/filename).unlink(missing_ok=True)
        return {'ok':True}

    @app.get('/api/performances')
    def performances(include_flagged:bool=False):
        return store.query("SELECT s.*,p.title,p.opus,ps.started FROM segments s LEFT JOIN pieces p ON p.id=s.piece_id JOIN sessions ps ON ps.id=s.session_id WHERE s.discarded=0 AND ps.status NOT IN ('recording','saving','recovery_failed') AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording') ORDER BY ps.started DESC,s.start")

    @app.get('/api/comparison')
    def comparison(left:str,right:str):
        from .organisation import analyse_segment
        a,b=segment(left),segment(right)
        if not a['piece_id'] or a['piece_id']!=b['piece_id']:raise ValueError('Choose two identified activities from the same piece')
        from .passages import compare_passages
        aa,bb=analyse_segment(store,a),analyse_segment(store,b)
        return {'left':{'segment':a,'analysis':aa},'right':{'segment':b,'analysis':bb},'aligned':compare_passages(aa,bb),
                'notice':'Comparison uses the current reference representation. Source recordings and historical analyses are retained. Different measure coverage, editions and ornament choices can prevent direct comparison.'}

    @app.get('/api/progress/days')
    def days():
        return store.query("SELECT substr(started,1,10) AS day,COUNT(*) AS sessions,SUM(duration) AS recorded_seconds FROM sessions WHERE status NOT IN ('recording','saving') GROUP BY day ORDER BY day DESC LIMIT 90")

    @app.get('/api/sessions/{ident}/bundle')
    def bundle(ident:str):
        import zipfile
        session(ident);path=store.root/'exports'/(ident+'-'+uuid.uuid4().hex+'.zip')
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            folder=store.root/'sessions'/ident
            from .microphone import audio_layout
            microphone,_ = audio_layout(folder)
            if microphone:archive.write(microphone,microphone.name)
            if (folder/'microphone.json').exists():archive.write(folder/'microphone.json','microphone.json')
            if (folder/'original.mid').exists():archive.write(folder/'original.mid','original.mid')
            archive.write(folder/'events.jsonl','events.jsonl')
            archive.writestr('timeline.json',json.dumps(timeline(ident),indent=2))
            archive.writestr('analyses.json',json.dumps(analyses(ident),indent=2))
            from .teacher import evidence_for
            archive.writestr('preanalysis.json',json.dumps(evidence_for(store,ident,analyses_limit=None),indent=2))
            for report in reports(ident):archive.writestr('reports/'+report['id']+'.txt',report['text'])
            for job in store.query("SELECT id,result FROM jobs WHERE kind='render' AND status='done'"):
                if not job['result']:continue
                result=json.loads(job['result'])
                if result.get('session_id')==ident and result.get('filename'):
                    audiofile=store.root/'audio'/result['filename']
                    if audiofile.exists():archive.write(audiofile,'audio/'+audiofile.name)
        return FileResponse(path,media_type='application/zip',filename='ChopinStudio_'+ident[:8]+'.zip',background=BackgroundTask(path.unlink,missing_ok=True))

    @app.put('/api/live/context')
    def live_context(body:LiveContext):
        if body.piece_id and not store.query('SELECT id FROM pieces WHERE id=?',(body.piece_id,)):
            raise HTTPException(404,'Piece not found')
        with recorder.lock:
            if recorder.context_piece_id!=body.piece_id:
                recorder.context_piece_id=body.piece_id
                recorder.mark('piece_context',{'piece_id':body.piece_id})
            live.context_piece_id=body.piece_id
        return {'ok':True}

    @app.get('/api/live')
    def live_status():return live.state

    @app.get('/api/progress')
    def progress():
        rows=store.query("SELECT p.id,p.title,p.genre,p.opus,p.mastery,p.intent,p.liking,p.forgotten,COUNT(s.id) AS attempts,SUM(CASE WHEN s.discarded=0 THEN s.end-s.start ELSE 0 END) AS seconds,SUM(s.complete) AS complete,MAX(ps.started) AS last_practised FROM pieces p LEFT JOIN segments s ON s.piece_id=p.id AND NOT EXISTS(SELECT 1 FROM recording_deletions d WHERE d.segment_id=s.id AND d.scope='recording') LEFT JOIN sessions ps ON ps.id=s.session_id GROUP BY p.id ORDER BY seconds DESC")

        from .progress import piece_progress,piece_time
        return [{**row,'seconds':piece_time(store,row['id']),'machine':assessment(row['id']),'practice':piece_progress(store,row['id'])} for row in rows]

    def piece_exists(piece_id):
        if not store.query('SELECT id FROM pieces WHERE id=?',(piece_id,)):raise HTTPException(404,'Piece not found')

    @app.get('/api/pieces/{piece_id}/voicing')
    def voicing(piece_id:str):
        piece_exists(piece_id)
        return store.setting('voicing:'+piece_id,VoicingTarget().model_dump())

    @app.put('/api/pieces/{piece_id}/voicing')
    def save_voicing(piece_id:str,body:VoicingTarget):
        piece_exists(piece_id)
        store.set_setting('voicing:'+piece_id,body.model_dump())
        return body.model_dump()

    @app.post('/api/pieces/{piece_id}/objectives')
    def add_objective(piece_id:str,body:ObjectiveRequest):
        piece_exists(piece_id)
        if body.first_measure is not None and body.last_measure is not None and body.last_measure<body.first_measure:raise HTTPException(422,'Invalid measure range')
        ident=uuid.uuid4().hex
        store.execute('INSERT INTO practice_objectives VALUES(?,?,?,?,?,?,?,?,?)',
          (ident,piece_id,body.title,body.category,body.first_measure,body.last_measure,int(body.completed),1,datetime.now(timezone.utc).isoformat()))
        return {'id':ident,'revision':1}

    @app.put('/api/objectives/{ident}')
    def edit_objective(ident:str,body:ObjectiveRequest):
        if body.first_measure is not None and body.last_measure is not None and body.last_measure<body.first_measure:raise HTTPException(422,'Invalid measure range')
        with store.lock:
            rows=store.query('SELECT revision FROM practice_objectives WHERE id=?',(ident,))
            if not rows:raise HTTPException(404,'Objective not found')
            if rows[0]['revision']!=body.revision:raise HTTPException(409,'Objective changed; reload before saving')
            store.execute('UPDATE practice_objectives SET title=?,category=?,first_measure=?,last_measure=?,completed=?,revision=revision+1 WHERE id=?',
              (body.title,body.category,body.first_measure,body.last_measure,int(body.completed),ident))
        return {'id':ident,'revision':body.revision+1}

    @app.post('/api/objectives/{ident}/time')
    def attribute_time(ident:str,body:ProblemTime):
        objectives=store.query('SELECT * FROM practice_objectives WHERE id=?',(ident,))
        if not objectives:raise HTTPException(404,'Objective not found')
        row=segment(body.segment_id)
        if row['piece_id']!=objectives[0]['piece_id'] or row['discarded'] or not row['start']<=body.start<body.end<=row['end']:raise HTTPException(422,'Choose an interval inside an activity of this piece')
        time_id=uuid.uuid4().hex
        store.execute('INSERT INTO practice_problem_time VALUES(?,?,?,?,?,?,?)',(time_id,ident,body.segment_id,row['session_id'],body.start,body.end,datetime.now(timezone.utc).isoformat()))
        return {'id':time_id}

    @app.delete('/api/objectives/{ident}/time/{time_id}')
    def remove_time(ident:str,time_id:str):
        store.execute('DELETE FROM practice_problem_time WHERE id=? AND objective_id=?',(time_id,ident))
        return {'ok':True}

    @app.post('/api/sessions/{ident}/teacher')
    def teacher(ident:str,body:TeacherRequest):
        session(ident)
        from .teacher import create_report
        return {'job_id':jobs.submit('teacher',lambda cancel,job:create_report(store,ident,body.provider,body.question,body.model))}

    @app.get('/api/sessions/{ident}/reports')
    def reports(ident:str):session(ident);return store.query('SELECT * FROM reports WHERE session_id=? ORDER BY created DESC',(ident,))

    @app.get('/api/reports/{ident}/text')
    def report_text(ident:str):
        rows=store.query('SELECT text FROM reports WHERE id=?',(ident,))
        if not rows:raise HTTPException(404,'Report not found')
        return PlainTextResponse(rows[0]['text'],headers={'Content-Disposition':'attachment; filename="practice-report.txt"'})
