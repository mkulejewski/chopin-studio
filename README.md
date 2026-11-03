# Chopin Studio

A local, touch-first piano practice workstation for Linux Mint and the Casio AP-470. Start a session without choosing a piece or filename. MIDI capture runs in Python, independently of the browser. Your original performance stays on your computer.

**Version 0.2 — integrated paths across milestones 1–5.** Recorder, personal repertoire, downloaded PDF volumes, provisional MusicXML references, offline activity organisation, a reversible touch timeline, evidence-based measurements, optional audio/local reports and experimental live piece recognition/following are implemented. Reference/recognition quality and actual AP-470/Cinnamon acceptance remain explicit limitations: [scope and acceptance status](docs/LIMITATIONS.md).

## Install on Linux Mint 22.x

Prerequisites: Python 3.12+, venv/pip, Node.js 20.19+ (22 recommended) with npm or pnpm, and a current Chromium or Firefox browser. If Python MIDI wheels are unavailable, install build tools and ALSA headers:

```sh
sudo apt install python3-venv python3-pip libasound2-dev build-essential pkg-config
./scripts/install.sh
```

The script installs Python dependencies in `.venv`, builds the frontend and adds **Chopin Studio** to your applications menu. No root privileges are used by the installer. One click on the application icon starts the backend and opens the frontend in a dedicated Chromium/Chrome app window (or your default browser if neither is installed). Launching again reuses the running backend. You can pin the application icon to your panel for single-click access. Right-click the launcher → Open fullscreen on Chromium; the interface also has a large fullscreen button for touch operation. Moving the repository requires rerunning the desktop installer.

```sh
make launch          # same action as the desktop launcher
make dev             # FastAPI + Vite (requires pnpm on PATH)
make test            # Python + frontend logic tests
cd frontend && pnpm test:e2e   # touch-enabled Chromium tests
```

Touch browser tests use a separate temporary data directory and loopback port 8766; install their browser once with `cd frontend && pnpm exec playwright install chromium`.

The normal interface is at `http://127.0.0.1:8765`. Only loopback is bound. The development interface is `http://127.0.0.1:5173` and proxies `/api` to Python. Frontend assets, fonts and PDF workers are local, with no CDN dependency. No telemetry, mandatory cloud account or automatic AI/audio processing. Cloud reports require an explicit request.

Closing the frontend window leaves the backend and any recording running while the piano is connected. If the piano is disconnected and no frontend has been open for five continuous minutes, the backend automatically saves any active recording and shuts down. An open frontend sends a heartbeat even when unfocused; reopening it or reconnecting the piano resets the timer. The same five-minute grace period applies when starting without a piano or frontend. A save failure keeps the backend running. To stop the backend immediately, use the **power button** in the top bar → **Save & shut down**. After confirmation, any active recording is saved before the service exits; the frontend displays a shutdown screen. A save failure displays an error. Click the application icon to start again.

When a connected piano disconnects during recording, capture continues for a **15-second grace period** after MIDI discovery detects the loss. Reconnecting during that period keeps the same session. Otherwise, the backend automatically stops and saves the recording, then queues the usual session analysis; the frontend session list updates automatically. Reconnecting afterward does not start another recording. This works with the frontend closed and is separate from the five-minute app shutdown timer. Recordings using simulated input are exempt. A save failure remains visible in recording status and keeps the backend running with the journal retained for recovery.

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

The bounded capture queue has 65,536 slots. Overflow and disk failures are visible errors and mark the session incomplete; no software can guarantee capture after storage failure. Disconnections/reconnections are timestamped journal markers. Do not unplug storage or shut down while recording. Closing the browser leaves capture running, subject to the five-minute idle shutdown rule above; stopping the backend normally finalises the recording. Do not run multiple backends against the same data directory.

Back up the entire data directory while the backend is stopped (SQLite database, journals, originals and scores together). Rendered media is stored separately under `audio/`. Personal recordings and PDFs are ignored by Git.

Further reading: [architecture](docs/ARCHITECTURE.md), [library](docs/LIBRARY.md), [hardware and touch acceptance](docs/ACCEPTANCE.md), [validation](docs/VALIDATION.md), [limitations and roadmap](docs/LIMITATIONS.md).

System-realtime/common wire messages that have no native Standard MIDI File event are retained in the journal and embedded in live exports as tagged sequencer-specific metadata; normal channel messages and SysEx use standard MIDI encoding. Imported MIDI originals are never rewritten.

## Personal repertoire and advanced workflow

Library groups all 44 supplied works as `Chopin / Genre / Opus or catalogue number`, retaining your learning levels, liking pluses, forgotten flags and priorities. Your private local installation has ten downloaded Paderewski volumes and 42 provisional MusicXML references: see [sources and exact gaps](docs/SOURCES.md). Scans/references remain outside Git. Raindrop retains Schott as its preferred printed edition.

After a session stops or a MIDI is imported, background organisation proposes activities. Open Sessions → a session → an activity to correct its boundaries and identity, split/merge, group attempts, undo edits, export MIDI, analyse or explicitly render audio. Save edits before those actions. Unknown/ambiguous matches remain unassigned.

Library → Machine references lets you import XML/MXL, review source notes, correct the analysis representation, mark quality and link score measures to PDF pages. The source MusicXML can be previewed with locally bundled OpenSheetMusicDisplay. A scan does not become a verified symbolic score automatically.

Practice → Live controls enables live recognition across references or a manual piece override. Automatic following/page turns remain experimental and off by default. They require a verified reference and explicit page map; manual navigation suspends automatic turns.

FluidSynth uses installed soundfonts (no sample library bundled). Install `fluidsynth` through Mint's Software Manager, or `sudo apt install fluidsynth`. WAV/FLAC jobs are cancellable. Reports work locally; the optional OpenAI adapter requires `pip install -e '.[ai]'` and either `OPENAI_API_KEY` on the backend or a key saved through the optional AI panel (owner-only local file). The explicit cloud button discloses that structured analysis and the question go to OpenAI. No private MIDI, scores or audio are sent by that adapter. No real API call was made during development.

Export a complete session bundle to keep originals, timeline, analysis, saved reports and any rendered audio together. Progress shows attributed activity history and recording-day totals; compare attempts from the Analysis section.

Automatic preanalysis now saves pitch-alignment scores separately from your personal notes and level. Progress shows the latest performance and eligible automatic whole-piece level, with a review suggestion when levels diverge. Eligible complete takes are flagged for optional audio production. Session review exports structured JSON for LLM use. These are experimental technical measurements; verified references are required for level/production decisions. See [scoring definitions](docs/VALIDATION.md).

AP-470 sound production uses the connected physical piano: play saved MIDI through it and record to its USB flash drive, or capture through a separately connected audio interface. You can also record WAV on the piano while originally playing and attach it later. See [AP-470 audio setup](docs/AP470_AUDIO.md). Settings includes pedal-controller selection and a default 20-second activity separation cooldown; the score viewer supports any first page of a spread and keeps fullscreen layout/options controls available.
