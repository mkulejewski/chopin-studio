CREATE TABLE recording_choices(
  segment_id TEXT PRIMARY KEY REFERENCES segments(id) ON DELETE CASCADE,
  choice TEXT NOT NULL DEFAULT 'auto' CHECK(choice IN ('auto','keep','remove')),
  deleted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE recording_deletions(
  id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES sessions(id),
  segment_id TEXT NOT NULL,start REAL NOT NULL,end REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',created TEXT NOT NULL
);
CREATE INDEX recording_deletion_session ON recording_deletions(session_id);
PRAGMA user_version=3;
