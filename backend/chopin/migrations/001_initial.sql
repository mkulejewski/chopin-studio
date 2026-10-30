CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, started TEXT NOT NULL,
                status TEXT NOT NULL, duration REAL DEFAULT 0, events INTEGER DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'live', error TEXT);
            CREATE TABLE IF NOT EXISTS volumes(
                id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
                filename TEXT, pages INTEGER, edition TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pieces(
                id TEXT PRIMARY KEY, title TEXT NOT NULL, genre TEXT NOT NULL,
                opus TEXT NOT NULL, musical_key TEXT NOT NULL, volume_id TEXT REFERENCES volumes(id),
                start_page INTEGER, end_page INTEGER, printed_page TEXT DEFAULT '',
                favourite INTEGER DEFAULT 0, practice_status TEXT DEFAULT 'To explore',
                notes TEXT DEFAULT '', view TEXT DEFAULT '{}');
            PRAGMA user_version=1;
