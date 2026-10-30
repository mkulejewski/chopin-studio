"""Cache public PDFs resolved through the normal IMSLP download flow.

Run explicitly. Never called at application startup; downloads stay outside Git.
"""
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone

import httpx
from pypdf import PdfReader
from chopin.store import Store, data_root

BASE='https://imslp.eu/files/imglnks/euimg/'
FILES={
'preludes':'0/0a/IMSLP964318-PMLP209085-IMSLP864159-PMLP2344-Chopin_Prelude_Paderewski.pdf',
'etudes':'5/5b/IMSLP964316-PMLP209085-IMSLP843321-PMLP722042-Chopin_Etude_Paderewski.pdf',
'nocturnes':'1/1d/IMSLP972729-PMLP209085-ChopinPaderewskiPWM_VII_Nocturnes.pdf',
'polonaises':'c/c3/IMSLP964068-PMLP209085-Chopin_Paderewski_No_8_Polonaises_scan.pdf',
'waltzes':'8/84/IMSLP964071-PMLP209085-Chopin_Werke_Paderewski_09_Walzer_scan.pdf',
'mazurkas':'3/30/IMSLP964319-PMLP209085-PWM-1949-Chopin-Complete-Mazurkas_1.pdf',
'ballades':'b/b1/IMSLP964059-PMLP209085-Chopin_Paderewski_No_3_Ballades_scan.pdf',
'impromptus':'5/53/IMSLP1011426-PMLP209085-PWM-1978-Chopin-Impromptus-Complete.pdf',
'sonatas':'e/e8/IMSLP964706-PMLP209085-PWM-1950-Chopin-Piano-Sonatas-Complete.pdf',
'minor':'b/b7/IMSLP964070-PMLP209085-Chopin_Paderewski_No_18_Minor_Works_scan.pdf'}


def acquire(store,ident,path):
    row=store.query('SELECT * FROM volumes WHERE id=?',(ident,))[0]
    if row['filename'] and (store.root/'scores'/row['filename']).exists():
        return {'volume':ident,'status':'already present','pages':row['pages']}
    target=store.root/'scores'/('paderewski_'+ident+'.pdf')
    temporary=target.with_suffix('.part')
    url=BASE+path
    try:
        with httpx.stream('GET',url,follow_redirects=True,timeout=120) as response:
            response.raise_for_status()
            with temporary.open('wb') as output:
                size=0
                for chunk in response.iter_bytes(1024*1024):
                    size+=len(chunk)
                    if size>100*1024*1024:raise ValueError('PDF download too large')
                    output.write(chunk)
                output.flush();os.fsync(output.fileno())
        with temporary.open('rb') as source:
            if source.read(5)!=b'%PDF-':raise ValueError('Source did not return a PDF; no access restriction will be bypassed')
        pages=len(PdfReader(temporary).pages)
        os.replace(temporary,target)
        store.execute('UPDATE volumes SET filename=?,pages=?,edition=? WHERE id=?',(target.name,pages,'Paderewski / Bronarski / Turczyński · PWM · IMSLP EU scan',ident))
        result={'volume':ident,'url':url,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'pages':pages,'downloaded':datetime.now(timezone.utc).isoformat(),'licence':'IMSLP public-domain / urtext notice; local personal library, no redistribution by this app'}
        target.with_suffix('.source.json').write_text(json.dumps(result,indent=2))
        return result
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        return {'volume':ident,'status':'failed','error':str(exc),'url':url}

if __name__=='__main__':
    store=Store(data_root())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda entry:acquire(store,*entry),FILES.items()))
    print(json.dumps(results,indent=2))
    sys.exit(int(any(x.get('status')=='failed' for x in results)))
