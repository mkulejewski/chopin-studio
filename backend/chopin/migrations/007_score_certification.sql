CREATE TABLE score_certifications(
    id TEXT PRIMARY KEY,
    piece_id TEXT NOT NULL REFERENCES pieces(id),
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    revision TEXT NOT NULL,
    status TEXT NOT NULL,
    created TEXT NOT NULL,
    start_measure INTEGER NOT NULL,
    end_measure INTEGER NOT NULL,
    through_pause INTEGER NOT NULL DEFAULT 0,
    corrections TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'certification',
    notice TEXT,
    review TEXT
);
CREATE INDEX score_certifications_piece ON score_certifications(piece_id, created);
PRAGMA user_version=7;
