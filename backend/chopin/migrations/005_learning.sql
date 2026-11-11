CREATE TABLE learning_profiles(piece_id TEXT PRIMARY KEY REFERENCES pieces(id), revision TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE learning_attempts(id TEXT PRIMARY KEY, piece_id TEXT NOT NULL REFERENCES pieces(id), session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL, revision TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL, target TEXT NOT NULL, result TEXT);
CREATE INDEX learning_attempt_piece ON learning_attempts(piece_id,created);
PRAGMA user_version=5;
