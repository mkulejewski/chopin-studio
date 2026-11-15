CREATE TABLE practice_objectives(
 id TEXT PRIMARY KEY,
 piece_id TEXT NOT NULL REFERENCES pieces(id),
 title TEXT NOT NULL,
 category TEXT NOT NULL,
 first_measure INTEGER,
 last_measure INTEGER,
 completed INTEGER NOT NULL DEFAULT 0,
 revision INTEGER NOT NULL DEFAULT 1,
 created TEXT NOT NULL
);
CREATE TABLE practice_problem_time(
 id TEXT PRIMARY KEY,
 objective_id TEXT NOT NULL REFERENCES practice_objectives(id),
 segment_id TEXT NOT NULL,
 session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 start REAL NOT NULL,
 end REAL NOT NULL,
 created TEXT NOT NULL
);
PRAGMA user_version=6;
