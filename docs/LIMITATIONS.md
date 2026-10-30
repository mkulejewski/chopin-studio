# Scope and roadmap

This is a runnable first vertical slice of milestone 1, not a completed five-milestone system.

## Implemented

- Touch-first React/TypeScript interface with five sections, real library/session/measurement data.
- Dedicated callback/queue/journal writer, monotonic timing, bounded capture queue, periodic fsync, streaming export, original preservation and interrupted-session recovery.
- ALSA Mido/RtMidi discovery, preferred-name matching, reconnect polling and dropout markers.
- MIDI and common midicsv import. MIDI originals retain all metadata. midicsv rejects unsupported events rather than silently dropping them; SMPTE and type-2 files are unsupported.
- Six PDF volume slots and eight initial pieces; editable piece metadata/page ranges, favourites and learning status.
- PDF.js, fullscreen, one/two-page view, zoom/pan/swipe, fixed 5% margin-crop toggle, persistent reading state.
- Optional CC66 mapping with debounce/delayed single press and raw command tags; simulation via the same capture method.
- Saved-session downloads, basic velocity/pedal summaries, session counts and total recorded duration.

## Not yet complete

- Complete verified Paderewski catalogue and bibliographic metadata, arbitrary added pieces/editions, MusicXML, OMR, reference correction UI.
- Automatic segmentation, recognition, repeated-attempt grouping, confidence-driven timeline editing and segment exports. Sessions currently show one explicitly unidentified complete recording. No automatic piece labels or measure numbers are fabricated.
- Score alignment, note/missing-note errors, tempo/rubato or voice analysis, ornament handling, per-piece practice history and recommendations. Velocity is not acoustic loudness. Onset-active seconds are not a claim about actual sounding time.
- Audio audition/rendering, FluidSynth jobs, sfizz/Pianoteq adapters, Casio audio capture and cloud/local AI teaching. No inert playback/render buttons are provided.
- Live score following, comparative performance plots, PWA/service worker, configurable long-press action and fit-to-width calibration. Double-tap currently toggles fit / 150%, not a geometry-derived fit-to-width.
- Capture failover to another disk, automatic backups, performance benchmarking over multiple wall-clock hours, and real hardware verification.

## Next engineering work

1. Complete manual AP-470/Cinnamon acceptance; soak-test capture under disk/CPU pressure and exercise reconnect with real ALSA ports. Tighten device identity across changing ALSA suffixes.
2. Extend catalogue and MusicXML reference quality model. Basic Partitura and Matchmaker interface research is recorded in RESEARCH.md; benchmark their suitability before integration. Audiveris remains uninvestigated.
3. Build offline segmentation as a versioned service with conservative unknown labels; implement reversible timeline corrections and state-safe segment export, tested on the supplied private recording and synthetic multi-piece fixtures.
4. Integrate alignment-backed recognition and evidence-linked analysis before optional rendering and AI.

Library page bounds, settings and session status use SQLite schema version 1. Future migrations must preserve originals and historical analysis versions. A future schema version is rejected rather than opened blindly.
