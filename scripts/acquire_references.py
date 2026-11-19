"""Explicit acquisition of CC BY 4.0 Chopin Institute first-edition references.
These are NOT certified Paderewski transcriptions. Conversions remain provisional.
"""
import json
import re
import tempfile
from pathlib import Path
import httpx
from music21 import converter
from chopin.platform.linux.paths import data_root
from chopin.store import Store
from chopin.catalogue import REPERTOIRE
from chopin.symbolic import import_reference

REPO='pl-wnifc/humdrum-chopin-first-editions'
ATTRIBUTION="First Editions of Fryderyk Chopin's Music; Copyright 2017-2021 The Fryderyk Chopin Institute (https://nifc.pl); https://chopinscores.org; https://github.com/pl-wnifc/humdrum-chopin-first-editions; https://creativecommons.org/licenses/by/4.0"

def main():
    store=Store(data_root())
    with httpx.Client(timeout=45,follow_redirects=True) as client:
        commit=client.get(f'https://api.github.com/repos/{REPO}/commits/main').json()['sha']
        tree=client.get(f'https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1').json()['tree']
        paths=[e['path'] for e in tree if e['path'].endswith('.krn')]
        licence=client.get(f'https://raw.githubusercontent.com/{REPO}/{commit}/LICENSE.txt').text
        if 'creativecommons.org/licenses/by/4.0' not in licence:raise ValueError('Unexpected source licence')
        (store.root/'references'/'NIFC-LICENSE.txt').write_text(licence)
        results=[]
        for row in REPERTOIRE:
            ident,genre,opus=row[:3]
            if store.query('SELECT id FROM symbolic_scores WHERE piece_id=?',(ident,)):
                results.append({'piece':ident,'status':'already present'});continue
            match=re.match(r'(\d+)(?: · No\. (\d+))?',opus)
            if ident=='s35-3':op,number=35,3
            elif match:op,number=int(match[1]),int(match[2] or 0)
            else:op,number=0,0
            candidates=[p for p in paths if p.startswith(f'kern/{op:03d}-') and (not number or re.search(fr'-{number:03d}(?:-|\.krn)',p))]
            if ident=='w-b56':candidates=[p for p in paths if 'WaltzEm' in p]
            if not candidates:
                results.append({'piece':ident,'status':'missing legitimate matching reference'});continue
            # Prefer the same first-edition publisher consistently, never infer a PDF match.
            candidates.sort(key=lambda p:('Sm' not in p,'BH' not in p,p))
            path=candidates[0]
            source=f'https://raw.githubusercontent.com/{REPO}/{commit}/{path}'
            try:
                response=client.get(source);response.raise_for_status()
                with tempfile.TemporaryDirectory() as directory:
                    kern=Path(directory)/Path(path).name;kern.write_text(response.text)
                    score=converter.parse(kern,format='humdrum',forceSource=True)
                    score.metadata.copyright=ATTRIBUTION
                    xml_path=Path(directory)/'reference.musicxml'
                    score.write('musicxml',fp=xml_path)
                    ref=import_reference(store,ident,xml_path.read_bytes(),'.musicxml',source,'CC BY 4.0 · '+ATTRIBUTION,
                                         'NIFC first-edition encoding → Music21 MusicXML; compare against '+('Schott' if ident=='p28-15' else 'Paderewski'))
                (store.root/'references'/(ref+'.source.krn')).write_text(response.text)
                results.append({'piece':ident,'status':'imported provisional','source':source,'reference_id':ref})
            except Exception as exc:
                results.append({'piece':ident,'status':'failed','source':source,'error':str(exc)})
            print(ident,results[-1]['status'],flush=True)
        for ident,slug in [('n-b49','chopin-nocturne-b49'),('w-b150','chopin-valse-b150')]:
            if store.query('SELECT id FROM symbolic_scores WHERE piece_id=?',(ident,)):continue
            source=f'https://noctavepiano.com/partitions/{slug}/{slug}.mxl'
            try:
                response=client.get(source);response.raise_for_status()
                ref=import_reference(store,ident,response.content,'.mxl',source,
                    'CC0 1.0 · Noctave; https://noctavepiano.com/partitions/'+slug+'/',
                    'Noctave / first-edition-derived; provisional comparison with Paderewski required')
                results=[row for row in results if row['piece']!=ident]
                results.append({'piece':ident,'status':'imported provisional','source':source,'reference_id':ref})
            except Exception as exc:results.append({'piece':ident,'status':'failed','error':str(exc),'source':source})
        (store.root/'references'/'acquisition.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(results,indent=2))

if __name__=='__main__':main()
