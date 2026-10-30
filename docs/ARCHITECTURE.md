# Chopin Studio architecture and task list

Local FastAPI service (127.0.0.1) owns MIDI capture and SQLite; React/TypeScript is a replaceable touch client. Closing a browser never stops a recording. XDG data contains SQLite, append-only session journals, immutable original MIDI and imported scores. Assets and recordings are never committed.

Capture callback → bounded thread-safe queue → dedicated journal writer. Monotonic nanoseconds define session time. Every journal batch is flushed and fsynced. MIDI exports use 1,000 ticks per beat at 500,000 µs per beat (2,000 ticks/second), no quantisation beyond 0.5 ms MIDI resolution. The nanosecond journal is authoritative. Recovery retains received messages and marks interrupted sessions.

SQLite migrations are versioned with PRAGMA user_version. Future alignment, analysis, audio and AI components consume immutable originals through independent services. Recognition must distinguish verified symbolic references from scanned PDFs. No fabricated metrics or automatic uploads.

## Current implementation target
- [x] Durable recorder, ALSA discovery/reconnection, dropout records, recovery
- [x] MIDI / midicsv import and original export
- [x] Individual-piece catalogue, attributed volume PDF import, page ranges
- [x] Touch practice viewer, gestures, saved view state, fullscreen and stop confirmation
- [x] Diagnostics, calibrated optional CC66 page turning, simulation
- [x] Tests, Linux desktop launcher, acceptance guides

The first slice is implemented; release acceptance on the physical piano/touchscreen is still pending. Scope exclusions are in LIMITATIONS.md.

## Subsequent milestones
2. Adaptive segmentation, symbolic candidate retrieval, alignment-backed recognition, uncertainty, timeline corrections and reusable labels. Evaluate Partitura and Matchmaker before selecting alignment implementations.
3. Verified score analysis, evidence-linked observations, ornaments and comparative graphs.
4. Explicit background FluidSynth rendering/cancellation; optional provider adapters and evidence-bound AI reports.
5. Live following, history comparisons, practice heatmaps, reference editing.

No PDF implies symbolic notes. No performance accuracy is claimed without a verified alignment. Pause is intentionally unsupported: uninterrupted timing and original preservation take priority.

## Version 0.2 component boundaries

Schema migration 002 adds personal repertoire state, symbolic reference provenance/quality, activity segments with revisions/history, page maps, versioned analyses, asynchronous jobs and reports. `catalogue.py` seeds the 44 supplied works once, preserving future edits. Acquisition scripts populate XDG data separately from Git.

`symbolic.py` validates/decompresses bounded XML before Partitura ingestion. `organisation.py` combines n-gram retrieval, RapidFuzz subsequence/edit alignment and polyphonic overlap, explicitly experimental. `extraction.py` owns segment controller/note state. `jobs.py` serialises explicit offline jobs and manages cancellable renderer processes. FluidSynth uses a Linux address-space ceiling and never runs automatically.

`live.py` consumes a separate 4,096-event best-effort queue; an overrun resets only following. Reference reloads are throttled, and score following cannot modify the capture journal. Device reconnection is only requested when the selected device identity changes, not when gesture/live settings change. CC66 configuration is cached in the recorder so no database operation occurs in its incoming-event callback.

`teacher.py` computes local evidence reports; explicit OpenAI requests use strict structured output and reject unknown evidence IDs. Local API-key configuration is protected and never returned or exported. Report revisions preserve earlier text. `practice_api.py` exposes the independent services, optimistic timeline edits and local bundles.

Frontend components separate practice/score rendering, reference review, activity review, comparisons, progress and live controls. Pointer-up activation prevents suppressed compatibility clicks after pinch; optimistic live-toggle state avoids delayed checkbox resets. Touch browser tests cover real PDF/MusicXML rendering, safe edits and audio playback.
