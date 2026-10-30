# Validation log — 30 October 2026

## Executed

- Python 3.12 virtual environment installed with FastAPI, Mido/python-rtmidi, pypdf, pytest and httpx.
- `python -m pytest -q`: 9 passed before final reliability refinements. Cases: overlapping same-pitch events, zero-velocity note-off, continuous CC64/CC66, durable journal ordering, stop cleanup, 10-hour simulated timestamp, torn-tail recovery, CSV tempo changes, duplicate recording guards, import byte preservation, malformed uploads, safe generated filenames, PDF page validation, foreign origin/host rejection, dropout markers, default-disabled CC66, double press, bounded queue overflow.
- Private `1.mid`: type 0, one track, PPQ 960; 321.029 seconds; 1,760 note-on, 1,760 note-off and 4,348 controller messages. The private fixture test imports through HTTP and asserts byte-for-byte original download equality. It is skipped when the private file is absent and never committed.
- Frontend TypeScript compilation and Vite production build succeeded.
- Vitest: 3 tests passed (elapsed-time formatting, backend error propagation and false settings serialisation).

Final touch browser and regression results are recorded below. Test fixtures are generated original blank PDFs and synthetic MIDI; no copyrighted score material is bundled.

## Environment notes

The ordinary sandbox prevents the ASGI TestClient event-loop wake-up and local browser/server sockets. Python API tests were rerun outside that sandbox and completed in under a second; this was an environment restriction, not a passing result inferred from stalled tests. Dependencies were installed with a temporary writable cache. Python 3.13 required unavailable ALSA build headers; system Python 3.12 supplied a prebuilt RtMidi wheel.

## Not validated

AP-470 USB connection, physical pedals, actual Linux Mint/Cinnamon touch hardware, acoustic sound, multiple wall-clock hours of recording, power-loss filesystem behaviour, Partitura/Matchmaker, rendering and AI. The ten-hour timestamp test is not a ten-hour soak test. Use the manual acceptance checklist before relying on the application for irreplaceable sessions.

## Final verified results

- Expanded Python suite: **13 passed** in 2.53 s, including 20,000 events captured while status is polled concurrently, future-schema protection simulation through the authoritative recorder, valid SysEx encoding and tagged system-realtime preservation. One upstream Starlette/httpx deprecation warning remains.
- Touch browser suite: **8 passed** in 13.8 s, no skipped private-fixture tests, using touch-enabled Chromium at 1280×900 / 1× and 820×1180 / 1.5×. Recording survived tab navigation and reload; stop confirmation/cancel, library editing/filtering, imported-original byte equality, PDF import/ranges, swipe, two-finger pinch, panning, fit zoom, fullscreen and persisted page/zoom were exercised.
- A stricter fit-zoom assertion caught Chromium suppressing compatibility clicks after pinch. Touch buttons now activate on pointer-up and suppress the duplicate click; rerun passed.
- User desktop shortcut installed to `~/.local/share/applications/chopin-studio.desktop`; launch script started the loopback backend successfully. The app was opened in a Codex browser panel (queued by the app UI).
- Private `1.mid` imported into the normal XDG application data, preserving its source file in the project and excluding both from Git. Export byte equality confirmed. SHA-256: `d04817105b1233fe885dc27649f26b19a5234d491997349ba1c316a95a0cdfd4`.

Browser tests use a separate temporary data directory and port 8766; the ordinary application uses port 8765. Generated blank-PDF fixtures are test navigation material, not a supplied musical score. A display reflow observer resizes PDF canvases when entering fullscreen or hiding controls.

# Continued milestones — version 0.2

Executed in this continuation:

- Existing changes validated (`16 passed`) and committed as `f701e29` before further implementation.
- Final expanded Python suite: **32 passed in 16.49 s**. Covers all 44 personal works and seed-once migrations; partial/tempo-varied/wrong-note recognition; conservative pause handling; repeated-attempt grouping; state-safe cuts and original preservation; unsafe XML/MXL rejection; actual Partitura import; timeline split/undo/revision conflicts; versioned analysis; local and edited reports; bundles; protected local AI configuration; mock OpenAI strict-schema/evidence validation; real FluidSynth WAV/FLAC output and cancellation; live simulated recognition; and settings isolation from MIDI reconnection. Two upstream Lark deprecation warnings remain.
- Final touch-enabled Playwright suite: **14 passed in 26.9 s**, at both screen sizes/scaling factors. New workflow imports/reviews MusicXML, renders a real OpenSheetMusicDisplay SVG, edits/undoes the timeline, requests analysis/local reporting, renders FluidSynth audio and starts playback by touching the browser-native audio control. It also enables/disables live recognition. The original recording, original-byte export, PDF gesture/fullscreen, diagnostics and protected shutdown flows continue to pass.
- Vitest: **3 passed**. TypeScript check, production build, Python compile checks and `git diff --check` passed. OpenSheetMusicDisplay is lazy loaded; its vendor bundle emits a build size advisory (about 1.44 MB uncompressed). No browser/server network dependency is required during ordinary offline use.
- Ten actual Paderewski PDF downloads validated with pypdf, hashes and visual contact-sheet review. 41 specific-work ranges indexed. The Études scan's printed-page offset was checked against PDF 8 / printed 7. Downloaded assets remain outside Git.
- 40 NIFC first-edition MusicXML conversions plus 2 Noctave CC0 XML imports are attached as **provisional**, with provenance and edition warnings. Two requested works lack imported XML; three lack the exact requested printed score in the local library (Schott Raindrop, Paderewski B.150 and B.133).
- Existing private `1.mid` processed by the actual recognition pipeline in 0.17 s on this environment: probable Op.9 No.1, similarity about 0.69; initial excerpt measure estimates are provisional. This is one real imported recording, not a claim of catalogue-wide recognition accuracy or reliable complete-score alignment.

No AP-470 hardware, real Cinnamon touch panel, live cloud model, specialist ornament evaluator, alternative renderer or multi-hour wall-clock soak was validated. Mock provider contracts and simulated live following are identified as such. See LIMITATIONS.md for remaining acceptance and musical validation work.

Additional focused checks passed after tightening concurrent timeline revisions and page-map rollback. Fullscreen practice now keeps Record/Stop in a persistent touch bar and reserves score space so the bar does not cover notation. The existing real library was opened in the running app and the downloaded Mazurka Op.30 No.2 was visually checked at PDF page 56 / printed page 52.
