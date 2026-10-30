# Chopin Studio

A local, touch-first piano practice workstation for Linux Mint and the Casio AP-470. Start a session without choosing a piece or filename. MIDI capture runs in Python, independently of the browser. Your original performance stays on your computer.

**Version 0.1 — milestone 1 vertical slice.** Recording, PDF volumes, per-piece page ranges, touch score navigation, MIDI/midicsv import, recovery, diagnostics, simulation and basic descriptive measurements are implemented. Hardware and actual Cinnamon touchscreen acceptance remain required. This is not the full five-milestone application; see [known limitations](docs/LIMITATIONS.md).

## Install on Linux Mint 22.x

Prerequisites: Python 3.12+, venv/pip, Node.js 20.19+ (22 recommended) with npm or pnpm, and a current Chromium or Firefox browser. If Python MIDI wheels are unavailable, install build tools and ALSA headers:

```sh
sudo apt install python3-venv python3-pip libasound2-dev build-essential pkg-config
./scripts/install.sh
```

The script installs Python dependencies in `.venv`, builds the frontend and adds **Chopin Studio** to your applications menu. No root privileges are used by the installer. The application icon opens the backend and browser automatically. Right-click the launcher → Open fullscreen on Chromium; the interface also has a large fullscreen button for touch operation. Moving the repository requires rerunning the desktop installer.

```sh
make launch          # same action as the desktop launcher
make dev             # FastAPI + Vite (requires pnpm on PATH)
make test            # Python + frontend logic tests
cd frontend && pnpm test:e2e   # touch-enabled Chromium tests
```

Touch browser tests use a separate temporary data directory and loopback port 8766; install their browser once with `cd frontend && pnpm exec playwright install chromium`.

The normal interface is at `http://127.0.0.1:8765`. Only loopback is bound. The development interface is `http://127.0.0.1:5173` and proxies `/api` to Python. Frontend assets, fonts and PDF workers are local, with no CDN dependency. No telemetry, cloud accounts, AI calls or automatic audio rendering.

## First practice

1. Connect USB Type-B on the AP-470 to the laptop, then switch on the piano.
2. Launch **Chopin Studio**, tap **Settings & devices** and check the note/velocity and three pedal readouts. Select a device identity if auto-detection does not find yours; save settings.
3. Optionally import a legally obtained PDF in Library → Paderewski collection. Set each piece’s PDF page range with its edit button.
4. Tap **Record session**, practise, then **Stop session → Stop & save session**. No names or piece selections are required. The original MIDI is available in Sessions.
5. Without a piano, start a recording, open Settings, tap **Play synthetic scale**, then stop and inspect the saved session. Imported sessions can also be replayed into the capture service.

Touch supports page buttons, swipe at fit scale, pinch zoom, drag when zoomed, double-tap fit/enlarge, fullscreen and control hiding. Page, zoom, crop and one/two-page layout persist per piece. Settings can disable individual gestures. Optional keyboard controls: Left/Right pages, Ctrl+R recording/stop confirmation. There is no pause: original monotonic timing stays continuous.

## Data safety

Default storage is `$XDG_DATA_HOME/chopin-studio` or `~/.local/share/chopin-studio`. Set `CHOPIN_DATA_DIR` for a separate library. SQLite uses WAL; session journals are append-only and fsynced at most every 250 ms while writing, with an idle sync every 200 ms. A forced process/OS/power interruption can lose the unsynced tail. Startup rebuilds interrupted MIDI from the journal and marks it **recovered**; recovery stops at the last durable event, not at an invented end time.

Original imported `.mid`/`.midi` files are byte-for-byte preserved, including tempo maps and metadata. Live originals are reconstructed at 2,000 ticks/second, with ≤0.25 ms timestamp rounding; the nanosecond-based journal retains finer timing. Stop adds MIDI note-offs and pedal releases to prevent stuck sound, without changing recorded journal events. Overlapping same-pitch onsets are counted separately.

The bounded capture queue has 65,536 slots. Overflow and disk failures are visible errors and mark the session incomplete; no software can guarantee capture after storage failure. Disconnections/reconnections are timestamped journal markers. Do not unplug storage or shut down while recording. Closing the browser leaves capture running; stopping the backend normally finalises the recording. Do not run multiple backends against the same data directory.

Back up the entire data directory while the backend is stopped (SQLite database, journals, originals and scores together). Rendered media will be stored separately when rendering is implemented. Personal recordings and PDFs are ignored by Git.

Further reading: [architecture](docs/ARCHITECTURE.md), [library](docs/LIBRARY.md), [hardware and touch acceptance](docs/ACCEPTANCE.md), [validation](docs/VALIDATION.md), [limitations and roadmap](docs/LIMITATIONS.md).

System-realtime/common wire messages that have no native Standard MIDI File event are retained in the journal and embedded in live exports as tagged sequencer-specific metadata; normal channel messages and SysEx use standard MIDI encoding. Imported MIDI originals are never rewritten.
