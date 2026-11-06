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
    kind:Literal['unknown','partial','exercise','complete']='unknown'
    group_id:str|None=Field(default=None,max_length=80)
    complete:bool=False
    discarded:bool=False
    revision:int=1
    details:str='{}'

class TimelineEdit(BaseModel):
    segments:list[SegmentEdit]=Field(max_length=1000)
    expected_revision:int

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


def attach_practice_routes(app,store,recorder,jobs,live,save_upload):
    def session(ident):
        rows=store.query('SELECT * FROM sessions WHERE id=?',(ident,))
        if not rows:raise HTTPException(404,'Session not found')
        if rows[0]['status'] in ('recording','saving'):raise HTTPException(409,'Finish saving this session first')
        return rows[0]

    def segment(ident):
        rows=store.query('SELECT * FROM segments WHERE id=?',(ident,))
        if not rows:raise HTTPException(404,'Segment not found')
        session(rows[0]['session_id']);return rows[0]

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
    def piece_sessions(ident:str):
        if not store.query('SELECT id FROM pieces WHERE id=?',(ident,)):
            raise HTTPException(404,'Piece not found')
        with store.lock:
            rows=store.query('''SELECT DISTINCT ps.* FROM sessions ps
                JOIN segments s ON s.session_id=ps.id
                WHERE s.piece_id=? AND s.discarded=0 AND ps.status IN ('saved','imported')
                ORDER BY ps.started DESC,ps.id DESC''',(ident,))
            segments=store.query('''SELECT s.* FROM segments s JOIN sessions ps ON ps.id=s.session_id
                WHERE s.piece_id=? AND s.discarded=0 AND ps.status IN ('saved','imported')
                ORDER BY s.start,s.id''',(ident,))
        grouped={}
        for item in segments:grouped.setdefault(item['session_id'],[]).append(item)
        return [{**row,'segments':grouped[row['id']]} for row in rows]

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
        return store.query('SELECT * FROM segments WHERE session_id=? ORDER BY start',(ident,))

    @app.post('/api/sessions/{ident}/organise')
    def organise(ident:str,force:bool=False):session(ident);return {'job_id':jobs.organise(ident,force)}

    @app.put('/api/sessions/{ident}/segments')
    def edit_timeline(ident:str,body:TimelineEdit):
        record=session(ident)
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
            locked_revision=store.db.execute('SELECT MAX(revision) FROM segments WHERE session_id=?',(ident,)).fetchone()[0] or 0
            if locked_revision!=body.expected_revision:raise HTTPException(409,'Timeline changed. Reload before editing.')
            save_history(store,ident)
            store.db.execute('DELETE FROM segments WHERE session_id=?',(ident,))
            for item in ordered:
                fields={**item.model_dump(),'session_id':ident,'revision':revision+1}
                fields['details']=json.dumps({'manual_correction':True})
                keys=list(fields)
                store.db.execute('INSERT INTO segments('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(fields.values()))
            store.db.commit()
        updated=timeline(ident)
        for row in updated:jobs.analysis(row)
        return updated

    @app.post('/api/sessions/{ident}/segments/undo')
    def undo(ident:str):
        session(ident)
        history=store.query('SELECT * FROM segment_history WHERE session_id=? ORDER BY id DESC LIMIT 1',(ident,))
        if not history:raise ValueError('No timeline edit to undo')
        revision=max((r['revision'] for r in timeline(ident)),default=0)+1
        with store.lock:
            store.db.execute('DELETE FROM segments WHERE session_id=?',(ident,))
            for row in json.loads(history[0]['snapshot']):
                row['revision']=revision;keys=list(row)
                store.db.execute('INSERT INTO segments('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(row.values()))
            store.db.execute('DELETE FROM segment_history WHERE id=?',(history[0]['id'],));store.db.commit()
        updated=timeline(ident)
        for row in updated:jobs.analysis(row)
        return updated

    @app.get('/api/segments/{ident}/midi')
    def export_segment(ident:str):
        row=segment(ident);path=segment_midi(store,row)
        return FileResponse(path,media_type='audio/midi',filename=(row['piece_id'] or 'Unknown')+'_'+ident[:6]+'.mid')

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
    def performances():
        return store.query("SELECT s.*,p.title,p.opus,ps.started FROM segments s LEFT JOIN pieces p ON p.id=s.piece_id JOIN sessions ps ON ps.id=s.session_id WHERE s.discarded=0 ORDER BY ps.started DESC,s.start")

    @app.get('/api/comparison')
    def comparison(left:str,right:str):
        from .organisation import analyse_segment
        a,b=segment(left),segment(right)
        if not a['piece_id'] or a['piece_id']!=b['piece_id']:raise ValueError('Choose two identified activities from the same piece')
        return {'left':{'segment':a,'analysis':analyse_segment(store,a)},'right':{'segment':b,'analysis':analyse_segment(store,b)},
                'notice':'Comparison uses the current reference representation. Source recordings and historical analyses are retained. Different measure coverage, editions and ornament choices can prevent direct comparison.'}

    @app.get('/api/progress/days')
    def days():
        return store.query("SELECT substr(started,1,10) AS day,COUNT(*) AS sessions,SUM(duration) AS recorded_seconds FROM sessions WHERE status NOT IN ('recording','saving') GROUP BY day ORDER BY day DESC LIMIT 90")

    @app.get('/api/sessions/{ident}/bundle')
    def bundle(ident:str):
        import zipfile
        session(ident);path=store.root/'exports'/(ident+'.zip')
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            folder=store.root/'sessions'/ident
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
        return FileResponse(path,media_type='application/zip',filename='ChopinStudio_'+ident[:8]+'.zip')

    @app.get('/api/live')
    def live_status():return live.state

    @app.get('/api/progress')
    def progress():
        rows=store.query('SELECT p.id,p.title,p.genre,p.opus,p.mastery,p.intent,p.liking,p.forgotten,COUNT(s.id) AS attempts,SUM(CASE WHEN s.discarded=0 THEN s.end-s.start ELSE 0 END) AS seconds,SUM(s.complete) AS complete,MAX(ps.started) AS last_practised FROM pieces p LEFT JOIN segments s ON s.piece_id=p.id LEFT JOIN sessions ps ON ps.id=s.session_id GROUP BY p.id ORDER BY seconds DESC')

        return [{**row,'machine':assessment(row['id'])} for row in rows]

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
