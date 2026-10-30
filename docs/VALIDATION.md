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
