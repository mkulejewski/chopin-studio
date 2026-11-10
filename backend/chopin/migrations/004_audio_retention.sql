-- Keep historical whole-recording deletions distinguishable from audio-only cleanup.
ALTER TABLE recording_deletions ADD COLUMN scope TEXT NOT NULL DEFAULT 'recording';
-- A pending cleanup must never resume by erasing MIDI under the corrected policy.
UPDATE recording_deletions SET scope='audio' WHERE status='pending';
PRAGMA user_version=4;
