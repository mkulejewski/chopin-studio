import json
import os
import sqlite3
import threading
from pathlib import Path


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in ('sessions', 'scores', 'imports', 'references', 'audio', 'reports', 'exports'):
            (root / name).mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(root / 'studio.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute('PRAGMA user_version').fetchone()[0] > 6:
            raise RuntimeError('Database was created by a newer Chopin Studio; upgrade before opening it')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        try:
            for number, filename in [(1,'001_initial.sql'),(2,'002_practice.sql'),(3,'003_recording_retention.sql'),(4,'004_audio_retention.sql'),(5,'005_learning.sql'),(6,'006_practice_objectives.sql')]:
                if version < number:
                    sql=(Path(__file__).parent / 'migrations' / filename).read_text()
                    self.db.executescript('BEGIN IMMEDIATE;\n'+sql+'\nCOMMIT;')
        except Exception:
            self.db.rollback()
            self.db.close()
            raise
        self.db.commit()
        self.seed()
        from .catalogue import seed_repertoire
        seed_repertoire(self)

    def query(self, sql, args=()):
        with self.lock:
            return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def execute(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)
            self.db.commit()

    def setting(self, key, default=None):
        rows = self.query('SELECT value FROM settings WHERE key=?', (key,))
        return json.loads(rows[0]['value']) if rows else default

    def set_setting(self, key, value):
        self.execute('INSERT OR REPLACE INTO settings VALUES (?, ?)', (key, json.dumps(value)))

    def seed(self):
        volumes = [('preludes', 'Preludes · Volume I', '964318'), ('etudes', 'Études · Volume II', '964316'),
                   ('nocturnes', 'Nocturnes · Volume VII', '972729'), ('polonaises', 'Polonaises · Volume VIII', '964068'),
                   ('waltzes', 'Waltzes · Volume IX', '964071'), ('mazurkas', 'Mazurkas · Volume X', '964319')]
        for ident, title, source in volumes:
            self.execute('INSERT OR IGNORE INTO volumes(id,title,source,edition) VALUES(?,?,?,?)',
                         (ident, title, 'https://imslp.org/wiki/Chopin_-_Paderewski_Complete_Edition#IMSLP' + source,
                          'Paderewski / Bronarski / Turczyński; source metadata and pagination require local verification'))
        pieces = [('n9-1', 'Nocturne', 'Nocturnes', '9 · No. 1', 'B-flat minor', 'nocturnes'),
                  ('n9-2', 'Nocturne', 'Nocturnes', '9 · No. 2', 'E-flat major', 'nocturnes'),
                  ('n72-1', 'Nocturne', 'Nocturnes', '72 · No. 1', 'E minor', 'nocturnes'),
                  ('p28-15', 'Prelude “Raindrop”', 'Preludes', '28 · No. 15', 'D-flat major', 'preludes'),
                  ('e25-1', 'Étude', 'Études', '25 · No. 1', 'A-flat major', 'etudes'),
                  ('p40-2', 'Polonaise', 'Polonaises', '40 · No. 2', 'C minor', 'polonaises'),
                  ('w64-2', 'Waltz', 'Waltzes', '64 · No. 2', 'C-sharp minor', 'waltzes'),
                  ('m30-2', 'Mazurka', 'Mazurkas', '30 · No. 2', 'B minor', 'mazurkas')]
        for p in pieces:
            self.execute('INSERT OR IGNORE INTO pieces(id,title,genre,opus,musical_key,volume_id) VALUES(?,?,?,?,?,?)', p)


def data_root():
    return Path(os.environ.get('CHOPIN_DATA_DIR', str(Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'chopin-studio')))
