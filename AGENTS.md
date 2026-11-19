# Agent instructions

## Project and working scope

- Chopin Studio is a local-first piano practice application. Python/FastAPI in `backend/chopin/` owns MIDI/audio capture and SQLite; React/TypeScript in `frontend/` provides the touch interface.
- Prioritize reliable recording, preservation of personal data and offline core workflows. Keep changes focused on the requested task and preserve unrelated working-tree changes.
- Read the relevant documentation and owning code before changing behavior. Roadmap items are proposals; historical validation logs do not establish that the current checkout passes.

## Protect the running application and personal data

- Do not stop/restart the user's application, interrupt a recording, access physical MIDI/audio devices or change desktop integration unless authorized by the task. Routine development must use an isolated test instance.
- Real application data lives in `$CHOPIN_DATA_DIR`, or `$XDG_DATA_HOME/chopin-studio` (normally `~/.local/share/chopin-studio`). Never use it for tests, fixtures, migration experiments or cleanup. Never run two services against the same data directory.
- Before starting any test/development service, set a dedicated `CHOPIN_PORT`, temporary `CHOPIN_DATA_DIR` and `XDG_STATE_HOME`, and `CHOPIN_NO_HARDWARE=1`. Do not use `make dev`, `make backend` or `make launch` against default personal data for testing.
- Preserve imported MIDI byte for byte, authoritative capture journals, source scores, user corrections and historical analyses/reports. Derived exports, analysis and reference corrections must remain separate from originals.
- Audio cleanup must preserve MIDI, journals, analyses and session history. Keep explicit audio protections effective through timeline edits and undo. Whole-session deletion is a separate explicit action; follow the documented retention/recovery workflow when changing audio files.
- Keep recordings, downloaded scores, application databases, credentials and private fixtures out of Git and test artifacts intended for sharing. Use synthetic or appropriately licensed fixtures.

## Browser testing must not interrupt the user's work

- Never use the user's open Chrome/Chromium windows, tabs, or profiles for testing. Do not navigate, focus, resize, close, or change zoom or fullscreen in those sessions.
- Do not use connected-browser or in-app browser automation to test this project when it can affect the user's desktop browser. Interact with the user's browser only when the user specifically asks for that interaction.
- Run UI tests in a separate **headless Playwright browser process**, with Playwright's fresh temporary profile and isolated browser contexts. Never attach to the user's browser through CDP or reuse their profile.
- Configure resolution and fullscreen checks only inside that isolated test browser. Include **1920×1080** for this user's Full HD display; use smaller viewports as additional responsive checks.
- Use a dedicated loopback test port, temporary application data and state directories, and `CHOPIN_NO_HARDWARE=1`. Never reuse the production server or access the physical piano/microphone during automated tests.
- Inspect saved screenshots, traces, DOM bounds, and test results instead of manipulating a live browser. Do not run headed tests unless the user explicitly requests a separate visible test browser.

## Recording and persistence guarantees

- Keep MIDI callbacks fast and bounded: no blocking database, analysis or network work. Preserve monotonic capture timing, journal ordering, flushing and recovery behavior; report overflow/storage faults rather than silently treating a take as complete.
- Recognition, live following, rendering and reports are independent consumers. Their failures, cancellation or queue overruns must not disrupt authoritative capture.
- Closing or reloading the browser must not terminate continuous Practice recording. Preserve the distinct, documented Learning pause/heartbeat behavior.
- Use versioned SQLite migrations in `backend/chopin/migrations/` for schema changes. Preserve existing data and reject unsupported future schemas. Do not rewrite already-applied migrations to change installed databases.
- Preserve optimistic revision checks, undo history and the distinction between user decisions and automatically derived suggestions.

## Musical evidence and Learning

- Finish the transcription audit when adding or expanding a Learning piece; a provisional digital draft is an intermediate result, not task completion. Visually verify every measure and both staves against the requested source scans, including pitches, accidentals, sounding octaves, chord membership, attack order, ties, written small notes, ornaments and staff crossings. Record review coverage and corrections, then verify the Learning integration, including Library selection, separate-hand references and authoritative-capture assessment. Do not make the learner verify the transcription by playing the piece or require independent human certification before completing the model audit. If a specific source ambiguity genuinely prevents completion, identify that exact passage and keep its uncertainty explicit; never promote an unaudited reference merely to enable grading.
- Every newly added Learning piece must have an **Open in Learning** button on its Library card. Use the same piece ID in the Learning catalogue and Library, and verify that the button selects the intended lesson.
- Keep provisional, verified and rejected reference states distinct. A scanned PDF does not supply symbolic notes; a different edition does not establish matching measures or pagination. Preserve source, licence and edition provenance.
- Label recognition, alignment, tempo and comparison estimates with their uncertainty. Similarity is not a calibrated probability; strict pitch metrics are not a general musical-quality grade. Preserve reference-quality, coverage and capture-health gates for automatic assessments and following.
- Automatic results must not overwrite personal mastery, notes or confirmed corrections. Do not silently promote references or bypass explicit provisional-following choices.
- Learning passes must use the authoritative captured performance and the reviewed reference requirements. Provisional live staves cannot grant a pass; hidden-recall views must not reveal upcoming expected notes or error hints.

## Touch interface, offline operation and privacy

- Keep essential Record/Stop controls reachable on touchscreens and in the appropriate fullscreen mode. Check for clipped controls, score overlap and regressions after gestures; preserve the distinction between App fullscreen and Score fullscreen.
- Preserve manual navigation and typed input alongside optional recognition and voice controls. Do not require cloud services for recording, score viewing, local analysis or local reports.
- Keep the service bound to loopback and retain host/origin protections. Do not add telemetry, automatic uploads or implicit cloud requests.
- Cloud reports require an explicit user action and disclosure of transmitted data. Protect API keys from responses, logs and exports. Browser speech recognition can use an online provider; keep that disclosure separate from local microphone capture.

## Validation and completion

Run checks appropriate to the changed behavior using the existing environment and package manager:

| Change | Check from repository root |
| --- | --- |
| Backend | `.venv/bin/python -m pytest -q` (target relevant tests while iterating) |
| Frontend logic | `cd frontend && pnpm test` |
| Frontend types and production build | `cd frontend && pnpm build` |
| General browser workflows | `cd frontend && pnpm test:e2e` |
| Learning and fullscreen workflows | `cd frontend && pnpm exec playwright test --config=playwright.learning.config.ts` |
| Sessions and cleanup workflows | `cd frontend && pnpm exec playwright test --config=playwright.sessions.config.ts` |

- Browser suites must follow the isolation rules above. Confirm the selected configuration covers the required viewport; include 1920×1080 for layout/fullscreen changes. Keep test data/state separate from other concurrent runs and never reuse an existing production server.
- Add meaningful regression coverage for capture, recovery, migrations, destructive cleanup and other behavioral fixes. Documentation-only changes need link/path and diff checks, not application startup.
- Report what changed, checks actually run and any remaining limitations. Distinguish automated/simulated coverage from physical piano, microphone, touchscreen, long-duration and real-cloud acceptance. A blocked or skipped check is not a pass.
- For every project change, update `README.md`, `docs/TODO.md` and any other relevant user/developer documentation to reflect the resulting behavior, completed work and remaining limitations. Keep this file focused on durable working rules; store detailed designs, plans and validation history in `docs/`.
- After validating a completed change, automatically create a local Git commit with a descriptive message unless the user asks to leave it uncommitted. Stage only changes within the authorized task, group related changes together, and report the resulting commit hashes. Pushing requires separate authorization.

## Documentation map

- [README](README.md): setup, user workflows and development entry points.
- [Architecture](docs/ARCHITECTURE.md): service boundaries, capture, persistence and derived processing.
- [Microphone recording](docs/MICROPHONE_RECORDING.md): recording sources, recovery, retention and deletion.
- [Musical comparison](docs/MUSICAL_COMPARISON.md), [score sources](docs/SOURCES.md) and [page following](docs/AUTO_PAGE_TURNING.md): evidence, provenance and uncertainty.
- [Learning](docs/LEARNING.md) and [Aeolian Harp](docs/aeolian_harp_etude_op25_no1_learning.md): lesson behavior and reference requirements.
- [Limitations](docs/LIMITATIONS.md), [acceptance](docs/ACCEPTANCE.md) and [validation](docs/VALIDATION.md): remaining acceptance work and recorded verification.
- [Roadmap](docs/ROADMAP.md) and [TODO](docs/TODO.md): future work, not standing authorization to implement it.
