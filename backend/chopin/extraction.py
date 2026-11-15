import json
from collections import defaultdict,deque
from .midi_files import journal_events,export_midi
from .velocity import velocity_events


def segment_midi(store,segment,for_audio=False):
    """Initialise active notes/controllers at a cut; terminate on export; source unchanged."""
    start,end=segment['start'],segment['end']
    source=store.root/'sessions'/segment['session_id']/'events.jsonl'
    directory=store.root/'exports'/segment['id'];directory.mkdir(exist_ok=True)
    journal=directory/('audio.jsonl' if for_audio else 'segment.jsonl')
    destination=directory/('audio.mid' if for_audio else 'segment.mid')
    active=defaultdict(deque);states={}
    with journal.open('w') as output:
        initialised=False
        def write(event):output.write(json.dumps(event)+'\n')
        def prefix(message, value):
            if value is not None:
                write({'t':0,'message':{'type':'control_change','channel':message.get('channel',0),'control':88,'value':value & 127}})
        def initialise():
            for message in states.values():write({'t':0,'message':message})
            for messages in active.values():
                for message,value in messages:
                    prefix(message,value)
                    write({'t':0,'message':message})
        for event in velocity_events(journal_events(source)):
            if 'message' not in event:continue
            msg=event['message'];kind=msg['type'];channel=msg.get('channel',0)
            if kind=='control_change' and msg.get('control')==88:continue
            if for_audio and event.get('application_command') and kind=='control_change' :continue
            if event['t']<start:
                key=(channel,msg.get('note'))
                if kind=='note_on' and msg.get('velocity',0):active[key].append((msg,event.get('velocity_14')))
                elif kind in ('note_off','note_on'):
                    if active[key]:active[key].popleft()
                elif kind in ('control_change','program_change','pitchwheel','aftertouch'):
                    states[(kind,channel,msg.get('control'))]=msg
                continue
            if event['t']>=end:break
            if not initialised:initialise();initialised=True
            value=event.get('velocity_14',event.get('release_velocity_14'))
            if value is not None:
                write({'t':event['t']-start,'message':{'type':'control_change','channel':channel,'control':88,'value':value & 127}})
            write({**event,'t':event['t']-start})
        if not initialised:initialise()
    export_midi(journal,destination,end-start)
    return destination
