# Chopin Studio architecture

Updated for Stage 1 platform separation on 2026-11-19. See the [documentation review](IMPLEMENTATION_REVIEW.md) for scope and the [future-work checklist](TODO.md) for deferred features.

## Platform and application boundaries

| Layer | Modules and responsibilities |
| --- | --- |
| Musical core | `midi_files`, `velocity`, `performance`, `recognition`, `segmentation`, `passages`, `tempo`, `symbolic`, `reference_review`, `learning_definition`, `learning_matching`, `certification_matching`, and deterministic reports in `teacher`. These use musical evidence, score data and portable codecs. |
| Application | `studio.Studio` composes `Recorder`, `Jobs`, `LiveFollowing`, `LearningSelection`, `ScoreCertification` and SQLite `Store`. Organisation, progress, imports, PCM/FLAC persistence, analysis and retention use shared services. Monitoring, pedal command policy and MIDI playback scheduling are shared. |
| Host contracts | `platform.interfaces` defines ordered MIDI events, ports, connections, optional output and audio facilities. `platform.files` defines app-private path-backed staging and durability. `StudioPlatform` supplies the chosen adapters at construction. |
| Linux | `platform/linux` owns Mido/RtMidi port access, ALSA microphone and stereo playback capture, FluidSynth discovery and limits, XDG configuration, the instance lock, loopback server, idle and desktop behavior. `start.sh` and `scripts/launch.py` still launch the desktop application. |
| API and UI | `app.py` adapts service lifetime and shutdown to FastAPI. `api/` and `learning_api` handle validation, uploads, downloads and transport. `frontend/src/api.ts` and the React UI still use same-origin HTTP. |

The dependency direction is from composition and transport toward shared
services and their contracts. Mido remains the pure Python MIDI/SMF codec.
The installed RtMidi driver is only used by the Linux port adapter. The base
Python package contains the musical and storage dependencies. The `web` extra
adds FastAPI, multipart handling and Uvicorn. The `linux` extra adds
python-rtmidi. ALSA utilities and FluidSynth are optional system tools. The
reporting provider remains an explicit optional cloud integration.

An additional host creates a private root, supplies `StudioPlatform` with
compatible file and device adapters, calls `Studio.start()`, schedules device
and Learning checks, and owns orderly shutdown. `MidiInput` handles preferred
port matching, discovery/reconnect and connection state. Attach/detach events
can wake it via `request_reconnect()`. Optional facilities can be absent. Shared
services can be exercised without a listener, a frontend, a default user path,
or a physical device. See the [baseline dependency audit](PLATFORM_AUDIT.md),
[adapter tests](../tests/test_platform_contracts.py) and
[future port contract](ANDROID_PORT.md).

## Local service and storage

A FastAPI service on `127.0.0.1` owns MIDI/audio capture and SQLite. React/TypeScript provides the touch interface. Closing Practice leaves capture running independently of the browser. MIDI-only sessions stop and save after a detected piano disconnection lasts 15 seconds. Otherwise the desktop service shuts down after five minutes without a connected piano or frontend. An active microphone session keeps it alive. Learning has its own pause/heartbeat rules.

Linux resolves the root through XDG or `CHOPIN_DATA_DIR`, then supplies it to Store. Application data contains `studio.sqlite3`, session journals and original MIDI, imported scores/references, microphone audio, rendered audio, exports and reports. Back up the whole directory with the service stopped. Private recordings and downloaded scores stay outside Git.

SQLite uses WAL and migrations through schema version **7**:

- `001_initial.sql`: sessions, volumes, pieces and settings.
- `002_practice.sql`: repertoire fields, symbolic references, activity timelines/history, page maps, analyses, jobs and reports.
- `003_recording_retention.sql`: take choices and durable deletion records.
- `004_audio_retention.sql`: distinguish audio cleanup from historical whole-recording deletion.
- `005_learning.sql`: Learning profiles and attempt history. Hand-specific progression and local note rules/corrections are stored in profile JSON.
- `006_practice_objectives.sql`: technical objectives, revisions and session-interval problem-time attribution.
- `007_score_certification.sql`: independently stored certification scopes, optional correction snapshots, MIDI-session links and cached reviews.

## Authoritative recording

The Linux adapter stamps decoded MIDI at callback entry using monotonic nanoseconds. Recorder enqueues into a bounded 65,536-event queue under a short lock independent of file, audio and SQLite operations. A dedicated writer appends the journal; live recognition has a separate best-effort queue. Stop drains the authoritative queue before exporting. The journal is flushed/fsynced after about 250 ms of writes or a 200 ms idle queue timeout, and at stop. A crash can lose the unsynced tail. Overflow/storage failures mark capture problems rather than silently certifying a complete take.

Journal version 1 is UTF-8 JSON Lines. A start record contains a UTC
`started` timestamp, `t: 0` and source flags. Each MIDI record has `t` in seconds
relative to the recording epoch, a `message` dictionary containing the original
MIDI 1.0 fields with `time: 0`, and for live capture an `application_command`
flag. SysEx data serializes as an integer array. Connection, loss and stop
markers use `kind` with a relative `t` and additional diagnostics. Imports may
contain only events and older journals may omit optional fields. Preserve MIDI
delivery order, including equal timestamps and CC88 immediately before its
associated event. A torn final line is tolerated during recovery. Malformed
earlier records are reported as corruption. Generated stop/all-notes-off
messages and timing quantization belong to the export.

Live MIDI export uses 1,000 ticks per beat at 500,000 microseconds per beat: 2,000 ticks/second, with at most 0.25 ms timestamp rounding. The higher-resolution journal remains authoritative. System messages without an SMF representation use tagged sequencer-specific metadata, which Chopin Studio recognizes at reimport. Imported MIDI originals are preserved byte for byte. Segment export initializes active notes/controllers and terminates notes/pedals without changing originals. Startup recovery reconstructs interrupted MIDI and attempts to finalize interrupted microphone PCM.

`platform/linux/microphone_capture.py` supervises ALSA capture through `arecord`. `microphone.py` owns timing metadata, blockwise PCM-to-FLAC conversion, acoustic measurements, MIDI/audio correlation, interval exports and lossless compaction. Practice capture is mono 48 kHz/16-bit. MIDI and microphone share one editable activity timeline.

The file contract puts temporary artifacts on the target filesystem, syncs
durable data and publishes via atomic replacement. Store uses SQLite WAL and
app-private paths. Native file selection, desktop downloading and export target
selection belong to the host. The shared importer consumes staged MIDI or PDF
files; exports return local paths for the host to present or copy. Storage
errors surface in capture diagnostics, with available bytes when the filesystem
can report them. Journal and microphone recovery retain raw data during a
failed export or conversion. Hosts must validate actual filesystem guarantees.

Score certification shares the exclusive recorder and exact-edition check.
Its live staves read positive-velocity MIDI attacks from the journal. The final
comparison aligns the saved attack stream to chronological score positions with
unordered pitches within each chord. It evaluates selected measure ranges or
clips the comparison at the last aligned attack when paused. Certification
uses its own review history and excludes dedicated certification sessions from
ordinary Practice organization. The optional Learning correction snapshot is
read once at start and remains pinned to that take.

### Device capability profiles

Input names continue to accept the saved preferred case-insensitive substring.
Without a preference, the AP-470/Casio/Celviano priority is retained, then a
generic instrument port is eligible. The built-in ALSA MIDI Through port can be
explicitly selected. Names affect selection and do not establish capability.

`GET /api/devices/capabilities?port=<id>` reads the current connection's MIDI
evidence and per-port confirmations. `PUT` replaces the optional profile. Send
`identity`, `manufacturer`, `confirmed` (feature to tri-state string),
`controllers` (CC number to tri-state string), and optionally a
`release_velocity_range` pair. Tri-state values are `supported`,
`unsupported` and `unknown`. Feature names are maintained in
[`midi_capabilities.py`](../backend/chopin/midi_capabilities.py).
Observed intermediate CC64 values demonstrate continuous data. Endpoints alone
leave the sustain mode unknown, and a fixed release value leaves release
sensing unknown. Input and output may be distinct ports; matching names never
confirm a pairing. Explicit confirmations take precedence and are stored in the
existing settings table under the full port ID. ALSA may assign a new port ID
on reconnect or reboot. Per-port calibration is descriptive. The existing
explicit analysis target controls release analysis. Page and Learning commands
still annotate source controller events, with no removal from the journal.

## References, organisation and analysis

`catalogue.py` seeds the 44-work personal repertoire once. Acquisition/indexing scripts are explicit operations, separate from startup. A new installation does not automatically contain the documented local PDF/reference collection.

`symbolic.py` validates bounded XML/MXL and uses Partitura to extract score notes, measures, staff/voice and beaming metadata. Source MusicXML is retained separately from editable analysis-note JSON. Grace-note subclasses are explicitly included, grace-chord members share an ordered attack, and written ornament metadata remains available to conservative grading/timing gates. Individually completed `reference_reviews` descriptors pin both source XML and scan fingerprints; `build_verified_practice_counterparts.py` produces separate measured exports and adds them without changing acquired originals. Library counts and reference detail metadata expose their quality and review scope. Quality labels are provisional, verified or rejected; a user changing the label is not an automatic editorial review.

`performance.py` extracts performance notes. `recognition.py` matches references with melodic n-grams, RapidFuzz edit/subsequence matching and chord overlap. Four/two-note retrieval, uncapped identity ranking and window-supported long-span alignment handle noisy phrases while retaining reference-quality gates. `segmentation.py` can use opening evidence to split full repetitions and later retries. Each take receives its own completeness check in `organisation.py`. Live backward reacquisition retires stale note/tempo context. Repeated phrase locations are explicit alternatives. General repeat and ornament traversal remain unresolved. Timeline revisions and undo preserve prior boundaries and labels. `extraction.py` produces state-correct MIDI cuts. See [recognition details](RECOGNITION.md).

`assessment.py` saves strict pitch precision, recall and F1 separately from personal mastery. Verified-reference and capture gates restrict whole-piece technical levels and production suggestions. The general `accuracy` field stays unset; the strict proxy is not a musical-quality grade. `tempo.py` estimates score-relative local tempo; `musical_comparison.py` adds conservative difference triage. Staff notation and comparison PDFs are generated locally by the frontend from reference positions, not acoustic transcription.

## Background audio and reports

`jobs.py` serializes offline organisation, analysis, rendering and report jobs. The Linux renderer uses a cancellable FluidSynth subprocess, installed soundfonts and a default address-space ceiling of 2 GiB. Linux hardware audio provides optional stereo ALSA capture during real-time playback. The shared output path supports standalone MIDI playback and controller/note cleanup. WAV attachment is a separate route. sfizz/Pianoteq are detected only, without renderer adapters.

`teacher.py` generates deterministic local reports. Its optional OpenAI adapter is explicitly requested, sends structured analysis/question/report context, requests strict structured output and validates cited evidence IDs. Local API-key configuration is protected and not returned or exported. User report edits create revisions. A local LLM runtime/provider adapter is not implemented.

`retention.py` shortlists complete stored-audio takes using `performance_quality.py`: current whole-take note evidence, within-measure timing residuals, written dynamic contrasts and available clipping/explicit voicing evidence. Fingerprinted native Nocturne annotations supplement missing converted dynamics without editing references. Reference/target mismatches, missing evidence and boundary ties retain audio for review; dates never rank winners. This is a musical-evidence proxy, separate from verified technical levels. Flagged audio is removed at shutdown after work finishes; MIDI/history survive. Separately, `headphone_audio.py` detects sustained MIDI playing without discernible piano tone; `jobs.py` can immediately discard that microphone interval after analysis. Keep flags, capture-health checks and overlap checks protect uncertain takes. Entire-session deletion is an explicit separate action. See [ranking](AUDIO_QUALITY_RANKING.md).

## Live recognition and Learning

`live.py` consumes a separate 4,096-event best-effort MIDI queue. Overflow resets following without affecting capture. It recognizes phrases, estimates position/tempo and issues page requests subject to stability, reference-quality and page-map gates. A trusted anchor can bridge brief recognition gaps; manual navigation suppresses turns for ten seconds in the client. This custom live follower checks plausible nearby continuation before accepting a backward match, withholding page requests for uncertain returning themes; Matchmaker is not integrated.

`learning.py` and `learning_api.py` implement Aeolian Harp, Heroic Polonaise and Nocturne Op. 15 No. 1 from packaged model-reviewed pitch/attack bundles. Starting/passing requires the exact reviewed PDF hash. Learning captures MIDI only, evaluates the complete assigned pitch sequence, and saves per-hand progression, assisted/self-assessed results, personal note rules and local reference corrections. Startup can select learned-prefix review without starting recording; it is not a spaced-review scheduler.

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
backward coda acquisition and explicit bridges/assemblies. All three current lessons
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

## Refactored domain ownership

Learning bundle/stage generation is in `learning_definition.py`, pitch evaluation
in `learning_matching.py`, and versioned profile loading/saving in
`learning_profiles.py`. `learning.py` retains stateful control and its stable
public imports. Live staff projections depend only on the pure matching layer.

Practice MIDI projection, candidate retrieval, boundaries/restarts and derived
analysis live in `performance.py`, `recognition.py`, `segmentation.py` and
`segment_analysis.py`. `organisation.py` owns timeline orchestration. Shared
`analysis_selection.py` applies read-time freshness with explicit automatic and
audio-review policies. Existing fingerprints are generated by the same shared
identity function; historical evidence is retained. See [Refactoring](REFACTORING.md).

HTTP validation lives in `api/models.py`; scoped routers receive explicit service
arguments or a small `PracticeContext`. No domain module imports an API module.
`api/uploads.py` preserves bounded durable staging. Timeline mutation is reusable
business logic in `timeline.py`, with serialized Store savepoints and post-commit
analysis scheduling. Audio deletion retains its dedicated recovery protocol.
Catalogue seeding derives both normal initialization and legacy eight-ID repair
from `catalogue.py`; existing migration SQL remains unchanged.

The frontend entry point only mounts `App.tsx`. Pages and dialogs own presentation;
App retains cross-workspace selection and recording lifecycle, with service polling
in `hooks/useAppStatus.ts`. `learning/` separates selection-independent workspace
control and editors. `practice/` owns timeline/audio/report panels, `analysis/`
evidence presentation, and `types/` shared response shapes. Score's interaction
hooks live in `score/`; PDF cache/rendering ownership stays in the existing viewer.
Styles are imported in their original cascade order from `styles/`.

Validation entry points and synthetic profiling are described in
[Refactoring](REFACTORING.md). GitHub Actions installs the optional Ruff quality
extra and runs independent backend/frontend/browser jobs; no hardware, private
fixtures or cloud credentials are required.

Scan-reviewed Practice references carry fingerprint-bound review sidecars beside their derived MusicXML. For corrected bar layouts, `reference_review.navigation_map` resolves the matched edition's page boundaries for both direct and tempo-estimated live turns. The pre-installation global map is retained as a baseline, not overwritten; subsequent explicit calibration takes precedence. A missing/invalid review or a different selected score volume withholds automatic turns for that derived reference. Review descriptors and the narrowed completed batch are documented in [the counterpart audit](LIBRARY_COUNTERPART_AUDIT.md).
