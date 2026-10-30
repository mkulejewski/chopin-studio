import json
import time
from pathlib import Path

import mido
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from chopin.app import create_app
from chopin.midi_files import export_midi, journal_events, midicsv_events, midi_events
from chopin.recorder import Recorder
from chopin.store import Store


def test_recorder_roundtrip_and_pedals(tmp_path):
    store = Store(tmp_path)
    recorder = Recorder(store)
    ident = recorder.start()
    source = [mido.Message('note_on', note=60, velocity=80), mido.Message('note_on',note=60,velocity=50),
              mido.Message('control_change',control=64,value=43),mido.Message('control_change',control=66,value=127),
              mido.Message('note_on',note=60,velocity=0),mido.Message('note_off',note=60)]
    for msg in source:
        recorder.receive(msg)
    time.sleep(.01)
    recorder.stop()
    folder = tmp_path / 'sessions' / ident
    journal = list(journal_events(folder / 'events.jsonl'))
    captured = [mido.Message.from_dict(x['message']) for x in journal if 'message' in x]
    assert captured == source
    exported = list(midi_events(folder / 'original.mid'))
    assert [x['message'] for x in exported[:len(source)]] == [x.dict() for x in source]
    assert [x['t'] for x in journal] == sorted(x['t'] for x in journal)
    assert store.query('SELECT status FROM sessions')[0]['status'] == 'saved'
    assert not recorder.active
    with pytest.raises(ValueError): recorder.stop()


def test_recovery_torn_final_record(tmp_path):
    store=Store(tmp_path)
    folder=tmp_path/'sessions'/'abc'
    folder.mkdir()
    store.execute("INSERT INTO sessions(id,name,started,status) VALUES('abc','test','2026-01-01','recording')")
    event={'t':36000.123456,'message':mido.Message('note_on',note=64).dict()}
    (folder/'events.jsonl').write_text(json.dumps(event)+'\n{"t":')
    Recorder(store)
    row=store.query('SELECT * FROM sessions')[0]
    assert row['status']=='recovered'
    assert row['duration']==36000.123456
    events=list(midi_events(folder/'original.mid'))
    assert events[0]['t']==pytest.approx(36000.1235,abs=.0005)
    assert events[1]['message']['type']=='note_off'


def test_midicsv_tempo_map(tmp_path):
    path=tmp_path/'in.csv'
    path.write_text('0, 0, Header, 1, 1, 480\n1, 0, Start_track\n1, 0, Tempo, 500000\n1, 0, Note_on_c, 0, 60, 70\n1, 480, Tempo, 1000000\n1, 960, Note_off_c, 0, 60, 0\n1, 960, End_track\n0, 0, End_of_file\n')
    events=list(midicsv_events(path))
    assert events[1]['t']==1.5


def test_stop_terminates_overlapping_notes(tmp_path):
    path=tmp_path/'j.jsonl'
    path.write_text('\n'.join(json.dumps({'t':t,'message':msg.dict()}) for t,msg in [(0,mido.Message('note_on',note=60)),(.1,mido.Message('note_on',note=60)),(.2,mido.Message('control_change',control=64,value=97))])+'\n')
    export_midi(path,tmp_path/'out.mid',1)
    events=list(midi_events(tmp_path/'out.mid'))
    assert len([x for x in events if x['message']['type']=='note_off'])==2
    assert events[3]['t']==1
    assert next(x for x in events if x['message'].get('control')==64)['message']['value']==97


def test_import_and_api(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        assert len(client.get('/api/library').json()['pieces'])==44
        assert client.post('/api/record/start').status_code==200
        assert client.post('/api/record/start').status_code==400
        app.state.recorder.receive(mido.Message('note_on',note=72,velocity=98))
        ident=client.post('/api/record/stop').json()['id']
        original=client.get(f'/api/sessions/{ident}/midi').content
        imported=client.post('/api/import/midi',files={'file':('performance.mid',original,'audio/midi')})
        assert imported.status_code==200
        imported_id=imported.json()['id']
        assert client.get(f'/api/sessions/{imported_id}/midi').content==original
        assert client.get(f'/api/sessions/{imported_id}/summary').json()['notes']==1
        assert client.get('/api/sessions/not-real/midi').status_code==404
        assert client.post('/api/import/midi',files={'file':('broken.mid',b'bad')}).status_code==400
        assert client.post('/api/import/midi',files={'file':('test.zip',b'bad')}).status_code==400
        assert client.post('/api/record/start',headers={'Origin':'https://untrusted.example'}).status_code==403
        assert client.get('/api/status',headers={'Host':'malicious.example'}).status_code==403


def test_pdf_page_validation_and_safe_filename(tmp_path):
    app=create_app(tmp_path,hardware=False)
    writer=PdfWriter();writer.add_blank_page(width=600,height=800);writer.add_blank_page(width=600,height=800)
    file=tmp_path/'test.pdf'
    writer.write(file)
    with TestClient(app) as client:
        response=client.post('/api/volumes/nocturnes/pdf',files={'file':('../../unsafe.pdf',file.read_bytes())})
        assert response.status_code==200
        assert response.json()['pages']==2
        library=client.get('/api/library').json()
        piece=next(p for p in library['pieces'] if p['id']=='n9-1')
        assert client.put('/api/pieces/n9-1',json={**piece,'start_page':1,'end_page':3}).status_code==400
        assert client.put('/api/pieces/n9-1',json={**piece,'start_page':1,'end_page':2}).status_code==200
        assert client.post('/api/volumes/nocturnes/pdf',files={'file':('bad.pdf',b'bad')}).status_code==400
        assert client.get('/api/volumes/nocturnes/pdf').content.startswith(b'%PDF-')
        assert not (tmp_path/'unsafe.pdf').exists()


def test_device_dropouts_and_application_commands(tmp_path):
    store=Store(tmp_path);recorder=Recorder(store)
    ident=recorder.start()
    recorder.mark('device_disconnected',{'device':'CASIO'})
    recorder.receive(mido.Message('control_change',control=66,value=127))
    recorder.receive(mido.Message('control_change',control=66,value=0))
    assert not recorder.page_commands  # default disabled
    store.set_setting('pedal_enabled',True)
    recorder.pedal_enabled=True
    recorder._pedal(mido.Message('control_change',control=66,value=127),1)
    recorder._pedal(mido.Message('control_change',control=66,value=0),1.15)
    recorder._pedal(mido.Message('control_change',control=66,value=127),1.25)
    recorder._pedal(mido.Message('control_change',control=66,value=0),1.4)
    assert [x['action'] for x in recorder.page_commands]==['previous']
    recorder.stop()
    assert any(e.get('kind')=='device_disconnected' for e in journal_events(tmp_path/'sessions'/ident/'events.jsonl'))


def test_queue_is_bounded_and_overflow_visible(tmp_path):
    store=Store(tmp_path);recorder=Recorder(store)
    import queue
    recorder.queue=queue.Queue(maxsize=1)
    recorder._enqueue({'t':0})
    recorder._enqueue({'t':1})
    assert 'overflow' in recorder.error.lower()


def test_user_recording_preserved_if_present(tmp_path):
    source=Path(__file__).parents[1]/'1.mid'
    if not source.exists():pytest.skip('Private user recording is intentionally not a fixture in Git')
    data=source.read_bytes()
    with TestClient(create_app(tmp_path,hardware=False)) as client:
        result=client.post('/api/import/midi',files={'file':('1.mid',data)})
        assert result.status_code==200
        ident=result.json()['id']
        assert client.get(f'/api/sessions/{ident}/midi').content==data
        summary=client.get(f'/api/sessions/{ident}/summary').json()
        assert summary['notes']>0
        assert client.get('/api/sessions').json()[0]['duration']>0


def test_concurrent_capture_and_status_snapshots(tmp_path):
    import threading
    store=Store(tmp_path);recorder=Recorder(store)
    ident=recorder.start()
    def feed():
        for i in range(10000):
            recorder.receive(mido.Message('note_on',channel=i%2,note=60+i%12,velocity=40+i%70))
            recorder.receive(mido.Message('note_off',channel=i%2,note=60+i%12))
    worker=threading.Thread(target=feed)
    worker.start()
    while worker.is_alive():
        snapshot=recorder.status()
        assert snapshot['queue_depth']<=65536
        assert isinstance(snapshot['notes'],dict)
        time.sleep(.002)
    worker.join();recorder.stop()
    assert not recorder.error
    events=sum('message' in item for item in journal_events(tmp_path/'sessions'/ident/'events.jsonl'))
    assert events==20000
    assert recorder.events==20000


def test_reject_future_schema_without_downgrading(tmp_path):
    import sqlite3
    db=sqlite3.connect(tmp_path/'studio.sqlite3')
    db.execute('PRAGMA user_version=99');db.close()
    with pytest.raises(RuntimeError,match='newer Chopin Studio'):Store(tmp_path)
    db=sqlite3.connect(tmp_path/'studio.sqlite3')
    assert db.execute('PRAGMA user_version').fetchone()[0]==99
    db.close()


def test_simulation_feeds_authoritative_capture(tmp_path):
    app=create_app(tmp_path,hardware=False)
    with TestClient(app) as client:
        ident=client.post('/api/record/start').json()['id']
        assert client.post('/api/simulation/start',json={'speed':8}).status_code==200
        for _ in range(200):
            if not client.get('/api/status').json()['simulation']:break
            time.sleep(.01)
        assert not client.get('/api/status').json()['simulation']
        assert client.post('/api/record/stop').status_code==200
        summary=client.get(f'/api/sessions/{ident}/summary').json()
        assert summary['notes']==24
        assert any(marker['kind']=='simulation_started' for marker in summary['markers'])


def test_sysex_and_system_realtime_preserved_in_standard_midi(tmp_path):
    path=tmp_path/'j.jsonl'
    source=[mido.Message('program_change',channel=1,program=4),mido.Message('pitchwheel',pitch=123),
            mido.Message('sysex',data=(67,1,2,3)),mido.Message('clock')]
    path.write_text(''.join(json.dumps({'t':i/10,'message':msg.dict()})+'\n' for i,msg in enumerate(source)))
    export_midi(path,tmp_path/'out.mid',.5)
    output=list(mido.MidiFile(tmp_path/'out.mid'))
    assert next(m for m in output if m.type=='sysex').data==(67,1,2,3)
    assert next(m for m in output if m.type=='program_change').program==4
    meta=next(m for m in output if m.type=='sequencer_specific')
    assert bytes(meta.data)==b'ChopinStudio raw MIDI\x00\xf8'


def test_configurable_pedal_controller_and_delayed_commands(tmp_path):
    from chopin.store import Store
    from chopin.recorder import Recorder
    import mido
    s=Store(tmp_path);r=Recorder(s);r.pedal_enabled=True;r.pedal_controller=67
    assert not r._pedal(mido.Message('control_change',control=66,value=127),1)
    r._pedal(mido.Message('control_change',control=67,value=127),2)
    r._pedal(mido.Message('control_change',control=67,value=0),2.1)
    r._pedal(mido.Message('control_change',control=67,value=127),2.2)
    r._pedal(mido.Message('control_change',control=67,value=0),2.3)
    assert [x['action'] for x in r.commands(0)]==['previous']
