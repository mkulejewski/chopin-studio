"""Reviewed pagination for exact downloaded scans; never guess other PDFs' indices.

PDF indices are one-based. Printed-page offsets were checked on the rendered scan.
Only fills unset ranges; user corrections always win.
"""
from chopin.store import Store,data_root

# piece -> (volume, first PDF page, inclusive last PDF page, printed first label)
RANGES={
'n9-1':('nocturnes',4,9,'7'),'n9-2':('nocturnes',10,12,'13'),
'n15-1':('nocturnes',22,25,'25'),'n27-2':('nocturnes',39,44,'42'),
'n48-1':('nocturnes',65,70,'68'),'n55-1':('nocturnes',78,82,'81'),
'n62-1':('nocturnes',88,93,'91'),'n62-2':('nocturnes',94,98,'97'),'n72-1':('nocturnes',99,102,'102'),
'w64-1':('waltzes',55,58,'55'),'w64-2':('waltzes',59,64,'59'),
'w69-1':('waltzes',71,74,'71'),'w69-2':('waltzes',79,82,'79'),
'w70-1':('waltzes',88,91,'88'),'w70-3':('waltzes',99,102,'99'),
'w-b56':('waltzes',103,107,'103'),'w-b46':('waltzes',115,117,'115'),
'm6-1':('mazurkas',11,13,'7'),'m7-1':('mazurkas',20,21,'16'),
'm24-2':('mazurkas',42,45,'38'),'m30-2':('mazurkas',56,57,'52'),
'm68-2':('mazurkas',162,163,'158'),'m68-3':('mazurkas',164,165,'160'),
'p26-1':('polonaises',11,16,'7'),'p26-2':('polonaises',17,25,'13'),
'p40-1':('polonaises',26,33,'22'),'p40-2':('polonaises',34,40,'30'),'p53':('polonaises',60,73,'56'),
'e10-2':('etudes',14,17,'15'),'e10-3':('etudes',18,21,'19'),'e10-5':('etudes',28,31,'29'),
'e10-11':('etudes',56,58,'57'),'e10-12':('etudes',59,63,'60'),
'e25-1':('etudes',64,68,'65'),'e25-3':('etudes',73,76,'74'),'e25-10':('etudes',104,110,'105'),
'p28-4':('preludes',13,13,'11'),
'n-b49':('minor',43,45,'43'),
# Volume IV's first printed page 7 is PDF page 10 (three prefatory pages).
'i66':('impromptus',33,42,'30'),
'b23':('ballades',7,20,'7'),
's35-3':('sonatas',59,61,'64'),
}

def main():
    import hashlib,json
    s=Store(data_root())
    for ident,(vid,start,end,printed) in RANGES.items():
        volume=s.query('SELECT * FROM volumes WHERE id=?',(vid,))[0]
        if volume['filename']!='paderewski_'+vid+'.pdf':continue
        path=s.root/'scores'/volume['filename'];source=path.with_suffix('.source.json')
        if not source.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=json.loads(source.read_text())['sha256']:continue
        s.execute('UPDATE pieces SET volume_id=?,start_page=?,end_page=?,printed_page=? WHERE id=? AND start_page IS NULL',(vid,start,end,printed,ident))
        s.execute('INSERT OR IGNORE INTO page_maps VALUES(?,?,?)',(ident,1,start))
    # These scans do not contain the posthumous A-minor Waltz or Sostenuto B.133.
    # A volume-level download must not pretend those individual works are present.
    s.execute('INSERT OR IGNORE INTO volumes(id,title,source,edition) VALUES(?,?,?,?)',('supplementary','Supplementary scores · edition to locate','https://imslp.org/wiki/Chopin_-_Paderewski_Complete_Edition','Requested Paderewski score not located in cached volumes'))
    for ident in ['w-b150','w-b133']:
        s.execute("UPDATE pieces SET volume_id='supplementary' WHERE id=? AND start_page IS NULL",(ident,))
    print('Indexed',len(RANGES),'reviewed work ranges; Schott preference retained; two supplementary scans remain to locate.')

if __name__=='__main__':main()
