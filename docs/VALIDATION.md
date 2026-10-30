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

## TODO implementation — 2026-10-30

Automatic background preanalysis runs after session organisation and timeline corrections. Historical analyses and per-analysis JSON files in `reports/` remain separate from personal notes and mastery. Session review exports structured preanalysis; Progress shows the latest current performance, latest eligible whole-piece assessment, and a suggestion when its 1/2/3 technical level differs from personal mastery by at least 0.75. These suggestions never edit personal fields.

Pitch precision counts correctly aligned pitches against all played pitches; recall counts them against all expected pitches in the aligned span. The score is their harmonic mean (F1). Unmatched groups and wrong/extra notes reduce it. This is an experimental alignment proxy, not certified musical accuracy. Thresholds: practice below 90%, good from 90%, concert from 98%. Level labels require verified references, similarity at least 0.85 and no unresolved grace notes. Whole-piece levels and audio-production flags additionally require at least 95% group coverage, alignment reaching both ends, and an error-free saved/imported capture. Audio-production candidates require 98% F1. Actual sound and interpretation need listening review. Partial work never overwrites the automatic whole-piece level. Discarded or edited-away activities do not supply the current automatic level.

The default separation cooldown is now 20 seconds (Settings: 5–300 seconds); slow passages can increase the silence threshold further. Short within-piece practice restarts remain one activity, and the timeline's split/merge controls remain available. This is a candidate grouping, not proof of piece identity.

Live following retains page requests across browser polls, resets on input overflow/idle/reference changes, uses a shorter rolling window, and allows provisional position display while reserving automatic turns for verified references with page maps. Pedal commands received together are applied in order. Settings selects CC64, CC66 or CC67; physical pedal behavior still needs validation. Manual navigation suspends automatic turns for 10 seconds. PDF documents remain cached across views (two volumes maximum); the following spread's operators are preloaded. Start-page input permits either parity in two-page mode, with layout and options buttons available while controls are hidden/fullscreen.

AP-470 audio production supports explicit real-time MIDI playback through a selected output and optional stereo 16-bit / 44.1 kHz ALSA capture (`arecord`, separately connected audio interface). Capture-free playback can be recorded using the piano's USB flash recorder; its WAV can then be attached to an activity. Starting MIDI recording during hardware playback is blocked, and playback input loopback is ignored. Cancellation releases notes/pedals and removes incomplete computer audio. No AP-470 sound library is installed on the computer. Hardware output, actual audio routing, latency, level/clipping, and the piano's flash-recorder behavior are not validated by synthetic tests.

Validation for these changes: the complete Python suite passed **44 tests**; final focused checks of exports, notes/levels, timeline reanalysis, configurable pedals, WAV import and playback cleanup passed **5 tests**. Frontend logic passed **3 tests**, TypeScript and the production Vite build succeeded, and the final touch-enabled Chrome suite passed **14 tests in 1.4 minutes** across both layouts. Browser coverage includes even-page spreads, fullscreen options/layout controls, two pedal commands per poll, cached PDF reuse and automatic following resuming after manual navigation. Saved normal/fullscreen screenshots were visually inspected. FastAPI TestClient stalled under the restricted sandbox, so backend integration and browser checks ran with approved local execution; the stalled process started by this task was terminated. Existing unrelated processes were left running. No physical AP-470/audio-interface or real cloud call was used.
