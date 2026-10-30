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
