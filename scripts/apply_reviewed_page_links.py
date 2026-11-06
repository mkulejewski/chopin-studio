"""Apply visually reviewed page links only to the exact PDF/reference snapshots.

Dry-run by default. Existing user calibration wins over proposed links. Only the
three explicitly reviewed seed range mistakes can be corrected. Reference notes,
quality, settings, recordings and personal notes are never changed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_links(db, root, manifest):
    changes, skipped = [], []
    pdf_hashes = {}
    for work in manifest['works']:
        pid = work['piece_id']
        row = db.execute('SELECT p.start_page,p.end_page,p.printed_page,v.filename FROM pieces p JOIN volumes v ON v.id=p.volume_id WHERE p.id=?', (pid,)).fetchone()
        if row is None or row['filename'] != work['filename']:
            skipped.append(f'{pid}: PDF assignment differs'); continue
        path = root/'scores'/row['filename']
        if row['filename'] not in pdf_hashes:
            pdf_hashes[row['filename']] = digest(path) if path.is_file() else None
        if pdf_hashes[row['filename']] != manifest['volumes'][row['filename']]:
            skipped.append(f'{pid}: PDF content differs'); continue
        refs = db.execute('SELECT filename,notes FROM symbolic_scores WHERE piece_id=?', (pid,)).fetchall()
        actual = []
        for ref in refs:
            file = root/'references'/ref['filename']
            actual.append((digest(file) if file.is_file() else None, hashlib.sha256(ref['notes'].encode()).hexdigest()))
        expected = [(r['sha256'], r['notes_sha256']) for r in work['references']]
        if Counter(actual) != Counter(expected):
            skipped.append(f'{pid}: symbolic references or their stored numbering differ'); continue
        before_range = [row['start_page'], row['end_page']]
        if before_range not in [work['expected_range'], work['reviewed_range']]:
            skipped.append(f'{pid}: preserving custom page range'); continue
        existing = dict(db.execute('SELECT measure,pdf_page FROM page_maps WHERE piece_id=?', (pid,)).fetchall())
        combined = dict(existing)
        proposed = []
        if before_range != work['reviewed_range']:
            proposed.append({'kind':'range', 'piece_id':pid, 'before':before_range, 'after':work['reviewed_range']})
        if pid == 'p40-1' and row['printed_page'] == '22':
            proposed.append({'kind':'printed-page', 'piece_id':pid, 'before':'22', 'after':'24'})
        for page in work['pages']:
            if page['status'] == 'withheld': continue
            measure, number = page['measure'], page['pdf_page']
            old = combined.get(measure)
            if old == number: continue
            # Correct only the known unedited opening link from the bad seed.
            if measure == 1 and old == work['expected_range'][0] and number == work['reviewed_range'][0] and old != number:
                proposed.append({'kind':'link', 'piece_id':pid, 'measure':measure, 'before':old, 'after':number})
                combined[measure] = number
            elif old is not None or number in combined.values():
                skipped.append(f'{pid}: preserving custom link at measure {measure} / PDF {number}')
            else:
                proposed.append({'kind':'link', 'piece_id':pid, 'measure':measure, 'before':None, 'after':number})
                combined[measure] = number
        ordered = sorted(combined.items())
        if any(b[1] < a[1] for a,b in zip(ordered, ordered[1:])):
            skipped.append(f'{pid}: proposed links conflict with existing page order; no changes to this work')
            continue
        changes.extend(proposed)
    return {'changes':changes, 'skipped':skipped,
            'withheld':[{'piece_id':w['piece_id'], **p} for w in manifest['works'] for p in w['pages'] if p['status']=='withheld']}


def apply_plan(db, root, manifest, backup):
    # Validate under the same write lock as the update. Roll back the whole batch
    # if any write fails; the backup is written before the first mutation.
    db.execute('BEGIN IMMEDIATE')
    try:
        plan = plan_links(db, root, manifest)
        if plan['changes']:
            ids = [w['piece_id'] for w in manifest['works']]
            snapshot = {'created':datetime.now(timezone.utc).isoformat(), 'changes':plan['changes'],
                        'pieces':[dict(r) for pid in ids for r in db.execute('SELECT id,start_page,end_page,printed_page FROM pieces WHERE id=?',(pid,))],
                        'page_maps':[dict(r) for pid in ids for r in db.execute('SELECT * FROM page_maps WHERE piece_id=?',(pid,))]}
            backup.parent.mkdir(parents=True, exist_ok=True)
            # An earlier backup must never be overwritten.
            with backup.open('x') as output: json.dump(snapshot,output,indent=2);output.write('\n')
            for change in plan['changes']:
                pid = change['piece_id']
                if change['kind'] == 'range':
                    db.execute('UPDATE pieces SET start_page=?,end_page=? WHERE id=?', (*change['after'],pid))
                elif change['kind'] == 'printed-page':
                    db.execute('UPDATE pieces SET printed_page=? WHERE id=?', (change['after'],pid))
                elif change['before'] is None:
                    db.execute('INSERT INTO page_maps(piece_id,measure,pdf_page) VALUES(?,?,?)', (pid,change['measure'],change['after']))
                else:
                    db.execute('UPDATE page_maps SET pdf_page=? WHERE piece_id=? AND measure=?', (change['after'],pid,change['measure']))
        db.commit()
        return plan
    except Exception:
        db.rollback()
        raise


def main():
    from chopin.store import data_root
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=data_root())
    parser.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[1]/'data/reviewed_page_links.json')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--backup',type=Path)
    args=parser.parse_args()
    root=args.data_dir.resolve()
    manifest=json.loads(args.manifest.read_text())
    if manifest['version'] != 1: raise ValueError('Unsupported manifest version')
    db=sqlite3.connect(f'file:{root / "studio.sqlite3"}?mode={"rw" if args.apply else "ro"}', uri=True, timeout=15)
    db.row_factory=sqlite3.Row
    try:
        backup=args.backup or root/'exports'/('page-links-backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        plan=apply_plan(db,root,manifest,backup) if args.apply else plan_links(db,root,manifest)
        links=[c for c in plan['changes'] if c['kind']=='link']
        print(json.dumps({'applied':args.apply,'new_links':sum(c['before'] is None for c in links),
                          'corrected_links':sum(c['before'] is not None for c in links),
                          'range_corrections':sum(c['kind']=='range' for c in plan['changes']),
                          'printed_page_corrections':sum(c['kind']=='printed-page' for c in plan['changes']),
                          'withheld_boundaries':len(plan['withheld']),'skipped':plan['skipped'],
                          'backup':str(backup) if args.apply and plan['changes'] else None},indent=2))
    finally: db.close()


if __name__=='__main__': main()
