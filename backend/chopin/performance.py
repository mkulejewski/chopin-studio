"""Offline MIDI projections and onset groups; never used in the capture callback."""
from collections import Counter, defaultdict, deque
from .domain_types import PerformanceNote

def performance_notes(events, diagnostics=None) -> list[PerformanceNote]:
    from .velocity import velocity_events
    notes=[];active=defaultdict(deque)
    for event in velocity_events(events, diagnostics):
        msg=event.get('message',{})
        kind=msg.get('type')
        key=(msg.get('channel',0),msg.get('note'))
        if kind=='note_on' and msg.get('velocity',0)>0:
            note={'pitch':msg['note'],'onset':event['t'],'duration':0.0,'velocity':msg['velocity'],'channel':msg.get('channel',0)}
            note.update(velocity_14=event.get('velocity_14'), release_velocity=None, release_velocity_14=None, release_source=None, released=False)
            notes.append(note);active[key].append(note)
        elif kind=='note_off' or kind=='note_on' and msg.get('velocity',0)==0:
            if active[key]:
                note=active[key].popleft();note['duration']=max(0,event['t']-note['onset'])
                note.update(released=True, release_velocity=msg.get('velocity') if kind=='note_off' else None,
                            release_velocity_14=event.get('release_velocity_14') if kind=='note_off' else None,
                            release_source='note_off' if kind=='note_off' else 'note_on_zero')
    return notes


def groups(notes, tolerance=.045):
    result=[]
    for index,note in enumerate(notes):
        if not result or note['onset']-result[-1]['onset']>tolerance:
            result.append({'onset':note['onset'],'pitches':set(),'indices':[],'measure':note.get('measure')})
        result[-1]['pitches'].add(note['pitch']);result[-1]['indices'].append(index)
    return result


def melody(grouped):return ''.join(chr(max(g['pitches'])+32) for g in grouped)


def grams(sequence,n=4):return Counter(sequence[i:i+n] for i in range(len(sequence)-n+1))

