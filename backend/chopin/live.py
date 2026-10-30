"""Best-effort live recognition consumer; never controls authoritative capture."""
import logging
import queue
import threading
import time
from collections import deque
from .organisation import Recognizer

log=logging.getLogger(__name__)

class LiveFollowing:
    def __init__(self,store,recorder):
        self.store=store;self.recorder=recorder;self.closed=threading.Event();self.window=deque(maxlen=64)
        self.state={'enabled':False,'label':'Live recognition off','piece_id':None,'measure':None,'confidence':0,'experimental':True}
        self.recognizer=Recognizer([]);self.signature=None;self.streak=0;self.last_piece=None;self.last_page=None
        self.previous_measure=None;self.last_note=None;self.dirty=False;self.last_run=0;self.last_catalogue_check=0;self.rows=[];self.pinned=None
        self.thread=threading.Thread(target=self.run,daemon=True,name='live-recognition');self.thread.start()

    def reset(self,label,enabled=True):
        self.window.clear();self.streak=0;self.last_piece=None;self.previous_measure=None;self.last_page=None;self.last_note=None;self.dirty=False
        self.state={'enabled':enabled,'label':label,'piece_id':None,'measure':None,'confidence':0,'stable':False,'experimental':True}

    def tick(self):
        now=time.monotonic()
        if not self.store.setting('live_enabled',False):
            self.reset('Live recognition off',False)
            while True:
                try:self.recorder.live_queue.get_nowait()
                except queue.Empty:break
            self.recorder.live_overflow=False;return
        pinned=self.store.setting('live_piece_id',None)
        if pinned!=self.pinned:
            self.reset('Listening for the selected piece');self.pinned=pinned
        if now-self.last_catalogue_check>5 or self.signature is None:
            rows=self.store.query('SELECT * FROM symbolic_scores')
            signature=tuple((r['id'],r['quality'],hash(r['notes'])) for r in rows)
            if signature!=self.signature:
                self.recognizer=Recognizer(rows);self.signature=signature
                self.reset('Listening for a phrase')
            self.rows=rows;self.last_catalogue_check=now
        while True:
            try:event=self.recorder.live_queue.get_nowait()
            except queue.Empty:break
            message=event['message']
            if message['type']=='note_on' and message.get('velocity',0):
                if self.last_note is not None and event['t']-self.last_note>8:self.reset('Listening for a new phrase')
                self.last_note=event['t'];self.window.append({'onset':event['t'],'pitch':message['note'],'velocity':message['velocity'],'duration':0});self.dirty=True
        if self.recorder.live_overflow:
            self.recorder.live_overflow=False;self.reset('Live input backlog reset; recording unaffected');return
        if self.last_note is not None and now-self.last_note>12:
            self.reset('Waiting for piano input');return
        if not self.store.setting('live_auto_turn',False):
            self.state.pop('page_request',None);self.last_page=None
        if not self.dirty or now-self.last_run<.5:return
        self.last_run=now;self.dirty=False
        recognizer=Recognizer([r for r in self.rows if r['piece_id']==pinned]) if pinned else self.recognizer
        match=recognizer.match(list(self.window));pid=match.get('piece_id');measure=match.get('last_measure')
        same=pid is not None and pid==self.last_piece
        progressing=same and (self.previous_measure is None or measure is not None and 0<=measure-self.previous_measure<=16)
        self.streak=self.streak+1 if progressing else 1
        if not same or not progressing:self.last_page=None
        self.last_piece=pid;self.previous_measure=measure
        # Provisional references may follow visibly, but never trigger automatic turns.
        stable=bool(pid and self.streak>=3 and match['confidence']>=.75)
        pending=self.state.get('page_request') if stable and progressing else None
        self.state={**match,'enabled':True,'stable':stable,'measure':measure if stable else None,'updated':time.time(),'experimental':True,'manual_override':pinned}
        if pending:self.state['page_request']=pending
        if stable and match['confidence']>=.9 and self.store.setting('live_auto_turn',False) and match.get('quality')=='verified' and measure is not None:
            pages=self.store.query('SELECT pdf_page FROM page_maps WHERE piece_id=? AND measure<=? ORDER BY measure DESC LIMIT 1',(pid,measure))
            if pages:
                request=(pid,pages[0]['pdf_page'])
                if request!=self.last_page:
                    self.state['page_request']={'piece_id':pid,'page':request[1],'id':time.monotonic()};self.last_page=request
        else:
            self.state.pop('page_request',None);self.last_page=None

    def run(self):
        while not self.closed.wait(.15):
            try:self.tick()
            except Exception:
                log.exception('Live recognition failed; capture remains independent')
                self.reset('Live recognition unavailable; recording unaffected')

    def close(self):self.closed.set();self.thread.join(3)
