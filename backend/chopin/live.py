"""Best-effort live recognition consumer; never controls authoritative capture."""
import json
import logging
import queue
import threading
import time
from collections import deque
from .organisation import Recognizer

log=logging.getLogger(__name__)

class LiveFollowing:
    def __init__(self,store,recorder):
        self.store=store;self.recorder=recorder;self.closed=threading.Event();self.window=deque(maxlen=192)
        self.state={'enabled':False,'label':'Live recognition off','piece_id':None,'measure':None,'confidence':0,'experimental':True}
        self.recognizer=Recognizer([]);self.signature=None;self.streak=0;self.last_piece=None;self.last_page=None
        self.thread=threading.Thread(target=self.run,daemon=True,name='live-recognition');self.thread.start()

    def run(self):
        last_run=0;last_note=None;last_catalogue_check=0;rows=[];previous_measure=None
        while not self.closed.wait(.15):
            try:
                enabled=self.store.setting('live_enabled',False)
                if not enabled:
                    self.state={**self.state,'enabled':False,'label':'Live recognition off'}
                    while True:
                        try:self.recorder.live_queue.get_nowait()
                        except queue.Empty:break
                    self.window.clear();self.recorder.live_overflow=False;continue
                if time.monotonic()-last_catalogue_check>5 or self.signature is None:
                    rows=self.store.query('SELECT * FROM symbolic_scores')
                    signature=tuple((r['id'],r['quality'],hash(r['notes'])) for r in rows)
                    if signature!=self.signature:
                        self.recognizer=Recognizer(rows);self.signature=signature
                    last_catalogue_check=time.monotonic()
                new=False
                while True:
                    try:event=self.recorder.live_queue.get_nowait()
                    except queue.Empty:break
                    message=event['message']
                    if message['type']=='note_on' and message.get('velocity',0):
                        if last_note is not None and event['t']-last_note>8:self.window.clear();self.streak=0
                        last_note=event['t'];self.window.append({'onset':event['t'],'pitch':message['note'],'velocity':message['velocity'],'duration':0});new=True
                if self.recorder.live_overflow:
                    self.window.clear();self.recorder.live_overflow=False;self.state={**self.state,'label':'Live input backlog reset; recording unaffected','piece_id':None,'measure':None};continue
                if last_note and time.monotonic()-last_note>12:
                    self.state={**self.state,'enabled':True,'label':'Waiting for piano input','piece_id':None,'measure':None};continue
                if not new or time.monotonic()-last_run<1:continue
                last_run=time.monotonic()
                pinned=self.store.setting('live_piece_id',None)
                recognizer=Recognizer([r for r in rows if r['piece_id']==pinned]) if pinned else self.recognizer
                match=recognizer.match(list(self.window))
                pid=match.get('piece_id')
                self.streak=self.streak+1 if pid and pid==self.last_piece else 1
                self.last_piece=pid
                candidate_measure=match.get('last_measure')
                progressing=previous_measure is None or candidate_measure is not None and 0<=candidate_measure-previous_measure<=8
                if pid!=self.state.get('piece_id') or not progressing:self.streak=1
                stable=bool(pid and self.streak>=3 and match['confidence']>=.85 and progressing)
                previous_measure=candidate_measure
                measure=match.get('last_measure') if stable else None
                self.state={**match,'enabled':True,'stable':stable,'measure':measure,'updated':time.time(),'experimental':True,'manual_override':pinned}
                if stable and match['confidence']>=.9 and self.store.setting('live_auto_turn',False) and match.get('quality')=='verified' and measure is not None:
                    pages=self.store.query('SELECT pdf_page FROM page_maps WHERE piece_id=? AND measure<=? ORDER BY measure DESC LIMIT 1',(pid,measure))
                    if pages:
                        # Send an explicit page request; the viewer checks current work and
                        # manual override cooldown. Never guess pagination from measure count.
                        request=(pid,pages[0]['pdf_page'])
                        if request!=self.last_page:
                            self.state['page_request']={'piece_id':pid,'page':request[1],'id':time.monotonic()};self.last_page=request
            except Exception:
                log.exception('Live recognition failed; capture remains independent')
                self.state={**self.state,'label':'Live recognition unavailable; recording unaffected','piece_id':None,'measure':None}

    def close(self):self.closed.set();self.thread.join(3)
