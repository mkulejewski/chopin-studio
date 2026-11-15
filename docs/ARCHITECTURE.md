# Chopin Studio architecture

Reviewed against the working tree on 2026-11-12. See the [documentation review](IMPLEMENTATION_REVIEW.md) for scope and the [future-work checklist](TODO.md) for deferred features.

## Local service and storage

A FastAPI service on `127.0.0.1` owns MIDI/audio capture and SQLite. React/TypeScript provides the touch interface. Closing Practice leaves capture running independently of the browser. MIDI-only sessions stop and save after a detected piano disconnection lasts 15 seconds. Otherwise the desktop service shuts down after five minutes without a connected piano or frontend; an active microphone session keeps it alive. Learning has its own pause/heartbeat rules.

XDG application data contains `studio.sqlite3`, session journals and original MIDI, imported scores/references, microphone audio, rendered audio, exports and reports. `CHOPIN_DATA_DIR` overrides the default location. Back up the whole directory with the service stopped. Private recordings and downloaded scores stay outside Git.

SQLite uses WAL and migrations through schema version **6**:

- `001_initial.sql`: sessions, volumes, pieces and settings.
- `002_practice.sql`: repertoire fields, symbolic references, activity timelines/history, page maps, analyses, jobs and reports.
- `003_recording_retention.sql`: take choices and durable deletion records.
- `004_audio_retention.sql`: distinguish audio cleanup from historical whole-recording deletion.
- `005_learning.sql`: Learning profiles and attempt history. Hand-specific progression and local note rules/corrections are stored in profile JSON.
- `006_practice_objectives.sql`: technical objectives, revisions and session-interval problem-time attribution.

## Authoritative recording

The MIDI callback writes to a bounded 65,536-event queue; a dedicated writer appends the journal. Monotonic nanoseconds define session time. The journal is flushed/fsynced after about 250 ms of writes or a 200 ms idle queue timeout, and at stop. A crash can lose the unsynced tail. Overflow/storage failures mark capture problems rather than silently certifying a complete take.

Live MIDI export uses 1,000 ticks per beat at 500,000 microseconds per beat: 2,000 ticks/second, with at most 0.25 ms timestamp rounding. The higher-resolution journal remains authoritative. Imported MIDI originals are preserved byte for byte. Segment export initializes active notes/controllers and terminates notes/pedals without changing originals. Startup recovery reconstructs interrupted MIDI and attempts to finalize interrupted microphone PCM.

`microphone_capture.py` runs ALSA capture through `arecord`; `microphone.py` owns timing metadata, blockwise PCM-to-FLAC conversion, acoustic measurements, MIDI/audio correlation, interval exports and lossless compaction. Practice capture is mono 48 kHz/16-bit. MIDI and microphone share one editable activity timeline.

## References, organisation and analysis

`catalogue.py` seeds the 44-work personal repertoire once. Acquisition/indexing scripts are explicit operations, separate from startup. A new installation does not automatically contain the documented local PDF/reference collection.

`symbolic.py` validates bounded XML/MXL and uses Partitura to extract score notes, measures, staff/voice and beaming metadata. Source MusicXML is retained separately from editable analysis-note JSON. Quality labels are provisional, verified or rejected; a user changing the label is not an automatic editorial review.

`organisation.py` extracts performance notes, proposes activities and matches references using melodic n-grams, RapidFuzz edit/subsequence matching and chord overlap. It handles conservative aborted-opening and unique mid-piece retry contexts and distinctive six-onset attempts. Repeated phrase locations are explicit alternatives; general repeat/ornament traversal remains unresolved. Timeline revisions and undo preserve prior boundaries/labels. `extraction.py` produces state-correct MIDI cuts.

`assessment.py` saves strict pitch precision, recall and F1 separately from personal mastery. Verified-reference and capture gates restrict whole-piece technical levels and production suggestions. The general `accuracy` field stays unset; the strict proxy is not a musical-quality grade. `tempo.py` estimates score-relative local tempo; `musical_comparison.py` adds conservative difference triage. Staff notation and comparison PDFs are generated locally by the frontend from reference positions, not acoustic transcription.

## Background audio and reports

`jobs.py` serializes offline organisation, analysis, rendering and report jobs. Requested FluidSynth rendering uses a cancellable subprocess, installed soundfonts and a default Linux address-space ceiling of 2 GiB. `hardware_audio.py` supports requested real-time piano MIDI playback, optional stereo ALSA capture and cancellation cleanup; WAV attachment is a separate route. sfizz/Pianoteq are detected only, without renderer adapters.

`teacher.py` generates deterministic local reports. Its optional OpenAI adapter is explicitly requested, sends structured analysis/question/report context, requests strict structured output and validates cited evidence IDs. Local API-key configuration is protected and not returned or exported. User report edits create revisions. A local LLM runtime/provider adapter is not implemented.

`retention.py` shortlists stored audio and removes flagged audio at shutdown after work finishes. MIDI/history survive audio cleanup. Separately, `headphone_audio.py` detects sustained MIDI playing without discernible piano tone; `jobs.py` can immediately discard that microphone interval after analysis. Keep flags, capture-health checks and overlap checks protect uncertain takes. Entire-session deletion is an explicit separate action.

## Live recognition and Learning

`live.py` consumes a separate 4,096-event best-effort MIDI queue. Overflow resets following without affecting capture. It recognizes phrases, estimates position/tempo and issues page requests subject to stability, reference-quality and page-map gates. A trusted anchor can bridge brief recognition gaps; manual navigation suppresses turns for ten seconds in the client. This is an experimental custom follower; Matchmaker is not integrated.

`learning.py` and `learning_api.py` implement the Aeolian Harp lesson from the packaged model-reviewed pitch/attack bundle. Starting/passing requires the exact reviewed PDF hash. Learning captures MIDI only, evaluates the complete assigned pitch sequence, and saves per-hand progression, assisted/self-assessed results, personal note rules and local reference corrections. Startup can select learned-prefix review without starting recording; it is not a spaced-review scheduler.

`learning_staves.py` incrementally projects captured attacks onto a reference passage for display. Its provisional live alignment cannot grant a pass; final evaluation reads the authoritative journal. Hidden recall returns played notes without upcoming expected notes or error hints. Learning pauses on leaving/hiding the workspace or after its frontend heartbeat expires.

## Frontend and boundaries

Components separate Practice/PDF viewing, Learning, references, session review, comparisons, cleanup, progress and live controls. PDF document/bitmap caches and detached-canvas rendering reduce repeated work. Browser speech recognition handles score-opening commands and reason dictation; it can use the browser provider's online service independently of the local recorder.

Automated UI checks must run in a separate headless Playwright process with a fresh browser context, dedicated loopback port, temporary data/state and `CHOPIN_NO_HARDWARE=1`; never attach to the user's browser. Include 1920×1080 when checking layout/fullscreen. Test fixtures and simulated MIDI do not establish hardware, musical or real-cloud acceptance.

Continuous Practice capture intentionally has no pause/resume action. Learning's pause saves a separate take; it does not suspend and resume a single continuous recording.


### Multiple Learning pieces

The Learning route layer selects one piece controller at a time and saves
`learning_piece` in the existing SQLite settings table. Profiles and attempts
remain keyed by piece and lesson revision; each profile retains separate hand
progress. Selection pauses/saves the previous Learning take and clears its
continuation before changing the active controller. A serialized route check
rejects stale piece requests, preventing a late UI event from recording under
the previous lesson. Practice capture remains independent.

Lesson bundles own printed bounds, source-volume/hash gates and connection
strategy. Aeolian keeps its original stage IDs. Heroic uses independent sections,
backward coda acquisition and explicit bridges/assemblies. Both current lessons
have model-reviewed attack references; generic provisional bundles cannot drive
pitch passes, auto finish, mismatch restart or comparison staves. Heroic's builder
checks pinned inputs, applies occurrence-specific scan decisions and exports a
complete readable inventory. Its 181-measure bundle includes required graces,
local ornament policies, a mid-bar key change and an 8,000-attack limit. The
reference route also exports explicitly unmeasured MusicXML via `learning_score.py`.
Its new revision retains the earlier provisional profile as nested historical
state, carries routine preferences forward and starts reviewed progression fresh.

## Passage evidence and technical practice history

`velocity.py` derives one-shot, channel-scoped CC88 pairings and separate release
velocities from ordered source events. It does not run inside MIDI callbacks.
`passages.py` places note, tempo, voicing and pedal evidence on reference score
beats, with independent confidence/capture gates. Saved analyses include a
fingerprint of the reference notes, edition and quality so incompatible score
revisions do not merge in measure history. Raw journals, imports and historical
analyses remain immutable.

`progress.py` selects current activity snapshots once per take, summarizes
measure evidence and recurring discrepancies, and reads revision/hand/note-rule
specific Learning recall history. Migration 006 stores independent technical
objectives and explicit problem-time intervals. Time belongs to the original
session interval rather than a generated candidate-segment identity, preserving
user attributions through timeline rebuilds; totals are unioned and clipped to
current matching activities. The analysis-target setting stores explicit voice
roles, a MIDI-velocity melody margin and a user-declared release calibration.
These targets never alter Learning advancement or personal mastery.
