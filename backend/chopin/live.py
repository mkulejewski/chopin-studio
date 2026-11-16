"""Best-effort live recognition consumer; never controls authoritative capture."""
import logging
import queue
import threading
import time
from collections import deque
from .recognition import Recognizer
from .tempo import infer_tempo

log=logging.getLogger(__name__)

class LiveFollowing:
    def __init__(self,store,recorder):
        self.store=store;self.recorder=recorder;self.closed=threading.Event();self.window=deque(maxlen=512)
        self.state={'enabled':False,'label':'Live recognition off','piece_id':None,'measure':None,'confidence':0,'experimental':True}
        self.recognizer=Recognizer([]);self.signature=None;self.streak=0;self.last_piece=None;self.last_page=None
        self.previous_measure=None;self.last_note=None;self.dirty=False;self.last_run=0;self.last_catalogue_check=0;self.rows=[];self.pinned=None;self.context_piece_id=None;self.last_context=None;self.anchor=None;self.estimated_turn=None;self.confirmed_page=None;self.confirmed_request=None
        self.thread=threading.Thread(target=self.run,daemon=True,name='live-recognition');self.thread.start()

    def reset(self,label,enabled=True):
        self.anchor=None;self.estimated_request=None;self.estimated_turn=None;self.confirmed_page=None;self.confirmed_request=None
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
        allow_provisional=self.store.setting('live_allow_provisional',False)
        context=self.context_piece_id
        if context!=self.last_context:
            self.reset('Listening with the open score as context');self.last_context=context
        if pinned!=self.pinned:
            self.reset('Listening for the selected piece');self.pinned=pinned
        if now-self.last_catalogue_check>5 or self.signature is None:
            rows=self.store.query('SELECT * FROM symbolic_scores')
            signature=(allow_provisional,tuple((r['id'],r['quality'],hash(r['notes'])) for r in rows))
            if signature!=self.signature:
                self.recognizer=Recognizer(rows,navigation=allow_provisional);self.signature=signature
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
        if not self.dirty or now-self.last_run<.5:
            self.estimate(now)
            self.assume_context()
            return
        self.last_run=now;self.dirty=False
        # Keep complete recent chords: a 64-note window can contain fewer than
        # the eight onsets required to recognise dense piano writing.
        from .performance import groups
        grouped=groups(list(self.window))
        if len(grouped)>32:
            cutoff=grouped[-32]['onset']
            while self.window and self.window[0]['onset']<cutoff:self.window.popleft()
        recognizer=Recognizer([r for r in self.rows if r['piece_id']==pinned],navigation=allow_provisional) if pinned else self.recognizer
        match=recognizer.match(list(self.window))
        # Old phrase context must not pin the listener after a mid-piece retry.
        if len(grouped)>=12:
            recent=[list(self.window)[i] for g in groups(list(self.window))[-8:] for i in g['indices']]
            tail=recognizer.match(recent)
            if tail.get('piece_id') and tail.get('latest_matched') and tail.get('query_coverage',0)>=.95 and tail['confidence']>=.8 and not tail.get('location_ambiguous'):
                if not match.get('latest_matched') or match.get('query_coverage',0)<.8 or (tail.get('piece_id')==match.get('piece_id') and tail.get('last_measure',0)<match.get('last_measure',0)):
                    match=tail
        pid=match.get('piece_id');measure=match.get('last_measure')
        same=pid is not None and pid==self.last_piece
        progressing=same and (self.previous_measure is None or measure is not None and 0<=measure-self.previous_measure<=16)
        self.streak=self.streak+1 if progressing else 1
        if not same or not progressing:self.last_page=None
        self.last_piece=pid;self.previous_measure=measure
        # Provisional navigation is opt-in; assessment quality remains unchanged.
        current=not match.get('location_ambiguous',False) and match.get('latest_matched',True) and match.get('query_coverage',1)>=.8
        stable=bool(pid and self.streak>=3 and match['confidence']>=.75 and current)
        pending=self.state.get('page_request') if stable and progressing else None
        self.state={**match,'enabled':True,'stable':stable,'measure':measure if stable else None,'updated':time.time(),'experimental':True,'manual_override':pinned}
        ref=next((r for r in recognizer.references if r['id']==match.get('reference_id')),None)
        if ref:self.state['tempo']=infer_tempo(list(self.window),ref,match)
        if self.state.get('tempo',{}).get('status')=='ambiguous':self.anchor=None
        if stable and current and match['confidence'] >= .9:
            tempo=self.state.get('tempo',{})
            if tempo.get('bpm') and tempo.get('curve'):
                point=tempo['curve'][-1]
                self.anchor={'time':point['time'],'beat':point['beat'],
                             'bpm':min(tempo['bpm'],tempo['curve'][-1]['bpm']),'reference':ref,
                             'state':dict(self.state),'measure':point['measure']}
                self.estimated_turn=None
        elif pid and self.anchor and pid != self.anchor['state']['piece_id'] and match.get('confidence',0)>=.75:
            self.anchor=None
        eligible=match.get('quality')=='verified' or (allow_provisional and match.get('quality')=='provisional')
        self.state['turn_status']=('Automatic turns are off' if not self.store.setting('live_auto_turn',False) else
            'Waiting for a stable match to the latest notes' if not stable else
            'Provisional reference: enable provisional following in Live controls or verify the reference' if not eligible else
            'Waiting for a more confident match before turning' if match['confidence']<.9 else
            'Following mapped pages'+(' · provisional reference' if match.get('quality')=='provisional' else ''))
        if pending:self.state['page_request']=pending
        if stable and match['confidence']>=.9 and self.store.setting('live_auto_turn',False) and eligible and measure is not None:
            mapping=self.store.query('SELECT measure,pdf_page FROM page_maps WHERE piece_id=? ORDER BY measure',(pid,))
            pages=[p for p in mapping if p['measure']<=measure][-1:]
            if len(mapping)<2:
                self.state['turn_status']='Only the opening page is mapped; calibrate later pages beside the score' if mapping else 'No page map; calibrate pages beside the score'
            if pages:
                request=(pid,pages[0]['pdf_page'])
                self.confirmed_page=request
                if request!=self.last_page or not self.confirmed_request:
                    self.confirmed_request={'piece_id':pid,'page':request[1],'id':time.monotonic()}
                self.state['page_request']=self.confirmed_request
                self.last_page=request
            else:
                self.state.pop('page_request',None);self.last_page=None
        else:
            self.state.pop('page_request',None);self.last_page=None

        if not stable or not current:
            self.estimate(now)
        self.assume_context()

    def assume_context(self):
        context=self.pinned or self.context_piece_id
        if not context or self.state.get('piece_id') or self.last_note is None:
            return
        self.state.update(piece_id=context,assumed=True,estimated=False,stable=False,confidence=0,
                          measure=None,label='Assuming open score · notes not yet recognised',
                          turn_status='Open score context only; waiting for a trusted score position')
        self.state.pop('page_request',None)

    def estimate(self, now):
        anchor=self.anchor
        if not anchor:
            return
        notice=' · provisional reference' if anchor['reference']['quality']=='provisional' else ''
        age=max(0,now-anchor['time'])
        silence=now-self.last_note if self.last_note is not None else float('inf')
        if age>30 or silence>3:
            if self.state.get('estimated'):
                self.state.update(stable=False, estimated=True,
                                  turn_status='Estimated following paused; waiting for piano input or a fresh match'+notice)
                self.state.pop('page_request',None)
                self.last_page=None
            self.anchor=None
            return
        beat=anchor['beat']+age*anchor['bpm']/60
        reference=anchor['reference']
        positions=[g for g in reference['groups'] if g['onset']<=beat and g.get('measure') is not None]
        if not positions:
            return
        measure=positions[-1]['measure']
        if measure < anchor['measure'] or measure-anchor['measure']>8:
            self.state.update(stable=False, turn_status='Waiting for a fresh score match')
            self.state.pop('page_request',None)
            self.last_page=None
            self.anchor=None
            return
        self.state={**anchor['state'], 'measure':measure, 'stable':True,
                    'estimated':True, 'updated':time.time(),
                    'confidence':round(anchor['state']['confidence']*max(.4,1-age/40),2),
                    'turn_status':'Estimated measure from tempo; listening to re-align'+notice}
        self.state.pop('page_request',None)
        eligible=reference['quality']=='verified' or (reference['quality']=='provisional' and self.store.setting('live_allow_provisional',False))
        if self.store.setting('live_auto_turn',False) and eligible:
            if self.confirmed_request:self.state['page_request']=self.confirmed_request
            # With a two-page spread the next notes are already visible. Retain
            # two measures of margin for inferred turns (one in single-page mode).
            view=self.store.query('SELECT view FROM pieces WHERE id=?',(self.state['piece_id'],))
            import json
            two_pages=bool(view and json.loads(view[0]['view'] or '{}').get('two_pages'))
            margin=2 if two_pages else 1
            pages=self.store.query('SELECT measure,pdf_page FROM page_maps WHERE piece_id=? AND measure<=? ORDER BY measure',
                                   (self.state['piece_id'],measure-margin))
            if pages:
                request=(self.state['piece_id'],pages[-1]['pdf_page'])
                confirmed=self.confirmed_page
                if confirmed and confirmed[0]==request[0]:
                    # An estimate must never rewind a note-confirmed turn or
                    # run more than one page ahead without fresh recognition.
                    if request[1]<=confirmed[1] or request[1]>confirmed[1]+1:
                        return
                if not self.estimated_turn or self.estimated_turn[:2]!=request:
                    self.estimated_turn=(*request,now)
                if now-self.estimated_turn[2]<2:
                    self.state['turn_status']='Estimated position; waiting before turning'+notice
                    return
                # Keep a request visible across the frontend's polling interval.
                previous=getattr(self,'estimated_request',None)
                if request!=self.last_page or not previous or (previous['piece_id'],previous['page'])!=request:
                    self.estimated_request={'piece_id':request[0],'page':request[1],'id':time.monotonic(),'estimated':True}
                self.last_page=request
                self.state['page_request']=self.estimated_request

    def run(self):
        while not self.closed.wait(.15):
            try:self.tick()
            except Exception:
                log.exception('Live recognition failed; capture remains independent')
                self.reset('Live recognition unavailable; recording unaffected')

    def close(self):self.closed.set();self.thread.join(3)
