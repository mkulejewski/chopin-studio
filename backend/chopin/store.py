import json
import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager

from .platform.files import LOCAL_FILES, StorageFiles


class Store:
    def __init__(self, root: Path, *, files: StorageFiles = LOCAL_FILES):
        self.root = root
        self.files = files
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in ('sessions', 'scores', 'imports', 'references', 'audio', 'reports', 'exports'):
            (root / name).mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self._transaction_depth = 0
        self.db = sqlite3.connect(root / 'studio.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute('PRAGMA user_version').fetchone()[0] > 7:
            raise RuntimeError('Database was created by a newer Chopin Studio; upgrade before opening it')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        try:
            for number, filename in [(1,'001_initial.sql'),(2,'002_practice.sql'),(3,'003_recording_retention.sql'),(4,'004_audio_retention.sql'),(5,'005_learning.sql'),(6,'006_practice_objectives.sql'),(7,'007_score_certification.sql')]:
                if version < number:
                    sql=(Path(__file__).parent / 'migrations' / filename).read_text()
                    self.db.executescript('BEGIN IMMEDIATE;\n'+sql+'\nCOMMIT;')
        except Exception:
            self.db.rollback()
            self.db.close()
            raise
        self.db.commit()
        self.seed()

    def query(self, sql, args=()):
        with self.lock:
            return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def execute(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)
            if not self._transaction_depth:
                self.db.commit()

    @contextmanager
    def transaction(self):
        """Serialize a multi-statement change and roll back nested failures.

        Store.execute participates without committing the surrounding savepoint.
        Direct db users inside this scope must not commit or roll back themselves.
        """
        with self.lock:
            name = f"chopin_{self._transaction_depth}"
            self.db.execute(f"SAVEPOINT {name}")
            self._transaction_depth += 1
            try:
                yield self
            except BaseException:
                self.db.execute(f"ROLLBACK TO {name}")
                self.db.execute(f"RELEASE {name}")
                raise
            else:
                self.db.execute(f"RELEASE {name}")
            finally:
                self._transaction_depth -= 1

    def setting(self, key, default=None):
        rows = self.query('SELECT value FROM settings WHERE key=?', (key,))
        return json.loads(rows[0]['value']) if rows else default

    def set_setting(self, key, value):
        self.execute('INSERT OR REPLACE INTO settings VALUES (?, ?)', (key, json.dumps(value)))

    def seed(self):
        from .catalogue import seed_catalogue
        with self.transaction():
            seed_catalogue(self)
