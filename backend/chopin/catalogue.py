"""User-authored repertoire, seeded once; subsequent edits always win."""
import re

# id, genre, opus/catalogue, key, nickname, mastery, liking, forgotten, intention, notes
REPERTOIRE = [
('w-b150','Waltzes','B.150 · posth.','A minor','',2,0,False,'Maintaining',''),
('w69-2','Waltzes','69 · No. 2','B minor','',2,0,False,'Maintaining',''),
('w64-2','Waltzes','64 · No. 2','C-sharp minor','',2.5,1,False,'Maintaining',''),
('w69-1','Waltzes','69 · No. 1','A-flat major','Farewell',3,1,False,'Maintaining',''),
('w70-1','Waltzes','70 · No. 1','G-flat major','',1,0,True,'Review','Largely forgotten.'),
('w70-3','Waltzes','70 · No. 3','D-flat major','',2,0,True,'Review','Largely forgotten.'),
('m30-2','Mazurkas','30 · No. 2','B minor','',2.5,1,False,'Maintaining',''),
('n9-1','Nocturnes','9 · No. 1','B-flat minor','',3,2,False,'Maintaining',''),
('n9-2','Nocturnes','9 · No. 2','E-flat major','',3,1,False,'Maintaining',''),
('p40-1','Polonaises','40 · No. 1','A major','Military',2.5,1,False,'Maintaining',''),
('w-b46','Waltzes','B.46 · No. 17 · posth.','E-flat major','',2,0,True,'Review','Largely forgotten. Authorship disputed in source catalogue; numbering varies.'),
('p28-15','Preludes','28 · No. 15','D-flat major','Raindrop',2.5,1,False,'Maintaining','Schott Music edition exclusively. D-flat major storm section: special liking ++, preserved verbatim from your description.'),
('n-b49','Nocturnes','B.49 · No. 20 · posth.','C-sharp minor','Lento con gran espressione',3,1,False,'Maintaining',''),
('m68-2','Mazurkas','68 · No. 2','A minor','',2.5,0,False,'Maintaining',''),
('e10-12','Études','10 · No. 12','C minor','Revolutionary',1.5,2,False,'Maintaining',''),
('p40-2','Polonaises','40 · No. 2','C minor','',2,1,False,'Maintaining','C minor parts only; A-flat major Sostenuto part not learnt.'),
('p28-4','Preludes','28 · No. 4','E minor','',1.5,0,False,'Maintaining',''),
('n72-1','Nocturnes','72 · No. 1','E minor','',1.5,1,False,'Maintaining',''),
('e25-1','Études','25 · No. 1','A-flat major','Aeolian Harp',None,0,False,'Learning','Currently learning.'),
('m24-2','Mazurkas','24 · No. 2','C major','',None,0,False,'Next',''),
('n15-1','Nocturnes','15 · No. 1','F major','',None,0,False,'Next',''),
('w-b133','Waltzes','B.133 · posth.','E-flat major','Sostenuto',None,0,False,'Next','Distinct from the E-flat major Waltz B.46 (No. 17).'),
('i66','Impromptus','66','C-sharp minor','Fantaisie-Impromptu',None,0,False,'Next',''),
('w-b56','Waltzes','B.56 · No. 14 · posth.','E minor','',None,0,False,'Next',''),
('e10-3','Études','10 · No. 3','E major','Tristesse',None,0,False,'Next',''),
('e10-5','Études','10 · No. 5','G-flat major','Black Keys',None,0,False,'Next',''),
('w64-1','Waltzes','64 · No. 1','D-flat major','Minute',None,0,False,'Next',''),
('n48-1','Nocturnes','48 · No. 1','C minor','',None,0,False,'Next',''),
('s35-3','Sonatas','35 · III','B-flat minor','Marche funèbre',None,0,False,'Next','Third movement of Sonata No. 2.'),
('m68-3','Mazurkas','68 · No. 3','F major','',None,0,False,'Planned',''),
('m6-1','Mazurkas','6 · No. 1','F-sharp minor','',None,0,False,'Planned',''),
('m7-1','Mazurkas','7 · No. 1','B-flat major','',None,0,False,'Planned',''),
('n55-1','Nocturnes','55 · No. 1','F minor','',None,0,False,'Planned',''),
('n62-1','Nocturnes','62 · No. 1','B major','',None,0,False,'Planned',''),
('n62-2','Nocturnes','62 · No. 2','E major','',None,0,False,'Planned',''),
('n27-2','Nocturnes','27 · No. 2','D-flat major','',None,0,False,'Planned',''),
('p26-1','Polonaises','26 · No. 1','C-sharp minor','',None,0,False,'Planned',''),
('p26-2','Polonaises','26 · No. 2','E-flat minor','',None,0,False,'Planned',''),
('e25-3','Études','25 · No. 3','F major','Horseman',None,0,False,'Planned',''),
('e10-2','Études','10 · No. 2','A minor','Chromatique',None,0,False,'Planned',''),
('e10-11','Études','10 · No. 11','E-flat major','',None,0,False,'Planned',''),
('e25-10','Études','25 · No. 10','B minor','',None,0,False,'Planned',''),
('p53','Polonaises','53','A-flat major','Heroic',None,3,False,'Dream','Greatest dream.'),
('b23','Ballades','23','G minor','Ballade No. 1',None,0,False,'Dream',''),
]

VOLUMES = [('ballades','Ballades · Volume III','964059'),('impromptus','Impromptus · Volume IV','1011426'),
('sonatas','Sonatas · Volume VI','964706'),('minor','Minor Works · Volume XVIII','964070'),
('schott','Schott · Preludes (user edition)',None)]

def catalogue_path(genre, opus):
    return 'Chopin/' + genre + '/' + ('Op ' if opus[0].isdigit() else '') + opus.replace(' · ', ' ').replace('.', '').strip()


def seed_repertoire(store):
    if store.setting('repertoire_seed_v2', False):
        return
    for ident,title,index in VOLUMES:
        store.execute('INSERT OR IGNORE INTO volumes(id,title,source,edition) VALUES(?,?,?,?)',
                      (ident,title,('https://imslp.org/wiki/Special:ReverseLookup/'+index) if index else 'https://www.schott-music.com/',
                       'Paderewski / Bronarski / Turczyński' if index else 'Schott Music; user-supplied edition'))
    singular={'Waltzes':'Waltz','Mazurkas':'Mazurka','Nocturnes':'Nocturne','Polonaises':'Polonaise','Preludes':'Prelude','Études':'Étude','Impromptus':'Impromptu','Sonatas':'Sonata movement','Ballades':'Ballade'}
    volume_ids={'Waltzes':'waltzes','Mazurkas':'mazurkas','Nocturnes':'nocturnes','Polonaises':'polonaises','Preludes':'preludes','Études':'etudes','Impromptus':'impromptus','Sonatas':'sonatas','Ballades':'ballades'}
    for ident,genre,opus,key,nickname,mastery,liking,forgotten,intent,notes in REPERTOIRE:
        title=singular[genre]+(' “'+nickname+'”' if nickname else '')
        vid='schott' if ident=='p28-15' else 'minor' if ident=='n-b49' else volume_ids[genre]
        store.execute('INSERT OR IGNORE INTO pieces(id,title,genre,opus,musical_key,volume_id) VALUES(?,?,?,?,?,?)',(ident,title,genre,opus,key,vid))
        # Only the explicitly supplied personal fields are initially updated for existing works.
        store.execute('UPDATE pieces SET mastery=?,liking=?,forgotten=?,intent=?,favourite=?,practice_status=?,catalogue_path=?,preferred_edition=?,notes=CASE WHEN notes="" THEN ? ELSE notes END WHERE id=?',
                      (mastery,liking,forgotten,intent,liking>0,intent,catalogue_path(genre,opus),'Schott Music' if ident=='p28-15' else 'Paderewski',notes,ident))
        if ident=='p28-15':
            store.execute("UPDATE pieces SET volume_id='schott', start_page=NULL,end_page=NULL WHERE id=? AND volume_id='preludes' AND start_page IS NULL",(ident,))
    store.set_setting('repertoire_seed_v2',True)
