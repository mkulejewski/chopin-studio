"""Piece identity on both sides of a rest determines short silence boundaries."""
import json
import random

from chopin.organisation import Recognizer, candidate_ranges, opening_restarts, organise
from chopin.store import Store


def references():
    rng=random.Random(321)
    return [dict(id=pid,piece_id=pid,quality='verified',
                 notes=[dict(pitch=rng.randrange(lo,hi),onset=i,duration=.4,measure=i//4+1)
                        for i in range(96)])
            for pid,lo,hi in [('n9-2',40,65),('n-b49',66,90)]]


def test_short_silence_between_different_works_preserves_entire_coda():
    refs=references();left=[{**n,'onset':n['onset']*.5} for n in refs[0]['notes']]
    # A held last chord followed by 13 seconds of silence is below the old 20s threshold.
    left[-1]['duration']=6
    end=left[-1]['onset']+6
    right=[{**n,'onset':end+13+n['onset']*.5} for n in refs[1]['notes']]
    ranges=candidate_ranges(left+right,right[-1]['onset']+1,20,Recognizer(refs))
    assert len(ranges)==2
    assert ranges[0][1]>=end
    assert ranges[1][0]==right[0]['onset']


def test_short_rest_inside_same_piece_does_not_split():
    ref=references()[0]
    played=[{**n,'onset':n['onset']*.5+(10 if i>=48 else 0)} for i,n in enumerate(ref['notes'])]
    assert len(candidate_ranges(played,played[-1]['onset']+1,20,Recognizer([ref])))==1


def test_opening_restarts_split_short_aborts_and_export_only_final_take(tmp_path):
    import numpy as np
    import soundfile as sf
    from chopin.microphone import RATE, export_audio, write_metadata
    from chopin.retention import eligibility
    store=Store(tmp_path);ref=references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'test.xml','local','test','test','verified',json.dumps(ref['notes']),'today'))
    # Two aborted openings, including one too short for whole-piece recognition.
    # No silence boundary separates these runs.
    sequence=ref['notes'][:18]+ref['notes'][:6]+ref['notes']
    played=[{**n,'onset':1+i*.5,'duration':.2} for i,n in enumerate(sequence)]
    folder=tmp_path/'sessions'/'restarts';folder.mkdir()
    events=[]
    for n in played:
        events.extend([dict(t=n['onset'],message=dict(type='note_on',note=n['pitch'],velocity=80)),
                       dict(t=n['onset']+.2,message=dict(type='note_off',note=n['pitch']))])
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute("INSERT INTO sessions(id,name,started,status,duration,events) VALUES('restarts','test','today','saved',62,240)")
    samples=(np.arange(62*RATE)%30000).astype('int16')
    sf.write(folder/'microphone.flac',samples,RATE,subtype='PCM_16')
    write_metadata(folder,{'offset_seconds':0,'filename':'microphone.flac','duration':62})
    rows=organise(store,'restarts')
    assert [r['start'] for r in rows]==[1,10,13]
    assert [r['kind'] for r in rows]==['partial','partial','complete']
    assert [r['complete'] for r in rows]==[0,0,1]
    assert all(r['piece_id']==ref['piece_id'] for r in rows)
    assert [eligibility(store,r,{})[0] for r in rows]==[False,False,True]
    clip=export_audio(store,rows[-1])
    decoded,rate=sf.read(clip,dtype='int16')
    np.testing.assert_array_equal(decoded,samples[13*RATE:round(rows[-1]['end']*RATE)])
    assert rate==RATE and sf.info(folder/'microphone.flac').frames==len(samples)
    store.db.close()


def test_written_opening_repeat_and_later_theme_return_are_not_aborted_starts():
    ref=references()[0]
    # A written repeat near the opening is ambiguous and must stay intact.
    written={**ref,'notes':ref['notes'][:18]+ref['notes'][:6]+ref['notes'][18:]}
    written['notes']=[{**n,'onset':i} for i,n in enumerate(written['notes'])]
    rec=Recognizer([written]);played=written['notes']
    assert opening_restarts(played,rec,rec.match(played))==[]
    # A return after substantial score progress is not an aborted introduction.
    rec=Recognizer([ref]);sequence=ref['notes'][:72]+ref['notes'][:24]
    played=[{**n,'onset':i} for i,n in enumerate(sequence)]
    assert opening_restarts(played,rec,rec.match(played))==[]


def test_separate_opening_evidence_and_keep_flag_survive_rebuild(tmp_path):
    store=Store(tmp_path);ref=references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'test.xml','local','test','test','verified',json.dumps(ref['notes']),'today'))
    folder=tmp_path/'sessions'/'test';folder.mkdir()
    events=[]
    for n in ref['notes']:
        t=n['onset']*.5
        events.extend([dict(t=t,message=dict(type='note_on',note=n['pitch'],velocity=80)),
                       dict(t=t+.2,message=dict(type='note_off',note=n['pitch']))])
    (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    store.execute("INSERT INTO sessions(id,name,started,status,duration,events) VALUES('test','test','today','saved',49,192)")
    first=organise(store,'test')[0]
    assert first['first_measure']==1
    assert json.loads(first['details'])['match']['opening_evidence']['first_measure']==1
    store.execute("INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",(first['id'],))
    store.execute("UPDATE segments SET kind='full_exercise',complete=1 WHERE id=?",(first['id'],))
    rebuilt=organise(store,'test',True)[0]
    assert rebuilt['kind']=='full_exercise' and rebuilt['complete']==1
    assert store.query('SELECT choice FROM recording_choices WHERE segment_id=?',(rebuilt['id'],))[0]['choice']=='keep'
    store.db.close()


def test_recorded_open_score_context_only_fills_unknown_identity(tmp_path):
    store=Store(tmp_path)
    ref=references()[0]
    store.execute('INSERT INTO symbolic_scores VALUES(?,?,?,?,?,?,?,?,?)',
                  (ref['id'],ref['piece_id'],'test.xml','local','test','test','verified',json.dumps(ref['notes']),'today'))
    for session,played,changed,expected in [
        ('unknown',[dict(pitch=100,onset=i,duration=.2) for i in range(12)],False,'n72-1'),
        ('other',ref['notes'],False,'n9-2'),
        ('mixed',[dict(pitch=100,onset=i,duration=.2) for i in range(12)],True,None),
    ]:
        folder=tmp_path/'sessions'/session;folder.mkdir()
        events=[dict(t=0,kind='piece_context',piece_id='n72-1')]
        if changed:events.append(dict(t=5,kind='piece_context',piece_id='n9-1'))
        for n in played:
            t=n['onset']+.5
            events.extend([dict(t=t,message=dict(type='note_on',note=n['pitch'],velocity=80)),
                           dict(t=t+.2,message=dict(type='note_off',note=n['pitch']))])
        events.sort(key=lambda e:e['t'])
        (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
        store.execute('INSERT INTO sessions(id,name,started,status,duration,events) VALUES(?,?,?,?,?,?)',
                      (session,session,'today','saved',100,len(events)))
        row=organise(store,session)[0]
        assert row['piece_id']==expected
        if session=='unknown':
            assert not row['complete'] and row['confidence']==0
            assert json.loads(row['details'])['match']['assumed']
            from chopin.retention import eligibility
            assert not eligibility(store,row,{'match':{'confidence':1}})[0]
    store.db.close()
