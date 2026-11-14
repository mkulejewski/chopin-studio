# Chopin Studio

Chopin Studio is a piano practice companion that runs on your own computer. Read sheet music, record a practice session, revisit individual attempts and work on memorizing a piece in one place. You can start recording without choosing a piece or naming a file.

The application is designed for Linux Mint, a touchscreen and a Casio AP-470 connected by USB MIDI. Its library focuses on Chopin. Other MIDI devices can be selected in Settings, though compatibility needs checking on the actual instrument.

Recording, score reading, session review, progress tracking and a dedicated Learning workspace are implemented. Project progress is measured by implemented features and their validation. Automatic piece recognition, score following and performance analysis are experimental. Physical piano, microphone and touchscreen acceptance is still incomplete; see [current limitations](docs/LIMITATIONS.md).

## What you can do

### Record your practice

- Capture **MIDI**, **microphone audio**, or both. MIDI records the keys, their timing, strike velocities and pedal messages; the microphone records the sound in the room.
- Keep playing across multiple pieces or attempts in one session. Recording runs independently of the browser window.
- Listen to saved microphone recordings and download a whole session or an individual passage as lossless FLAC audio.
- Import existing MIDI files for review. Imported originals are preserved unchanged.
- Try the recorder without a piano using the synthetic scale in Settings.

Practice enables MIDI and microphone recording by default in the interface. Choose your sources before starting; microphone capture uses the input on the computer running Chopin Studio and requires Linux's `arecord` utility. Audio-only sessions can suggest passages from sound and silence, but cannot identify a composition or transcribe its notes. [Recording details](docs/MICROPHONE_RECORDING.md)

### Read and organize scores

- Browse a curated catalogue of **44 Chopin works**, grouped by genre and opus or catalogue number.
- Keep personal notes, favourites, learning status, priorities and your own assessment of how well you know each piece.
- Import PDF scores and assign each piece its page range within a volume.
- Read one or two pages, swipe between pages, pinch to zoom, drag to pan and return to the opening score page. Reading settings are saved per piece.
- Use **App fullscreen** for the whole workspace or **Score fullscreen** for a larger score with practice controls available. Optional pedal controls can turn pages.
- Import MusicXML files—a digital representation of the notes—for recognition and comparison. Preview them and review or correct the analysis reference separately from the source file.

PDF score collections, imported MusicXML references and sound libraries are **not bundled with the source code**. Add copies you are entitled to use. Optional acquisition scripts and their source coverage are documented in [score sources and gaps](docs/SOURCES.md). A PDF scan alone does not provide the digital notes needed for matching or pitch analysis.

### Learn notes from memory

**Learning** offers separate piece profiles. **Étude Op. 25 No. 1, “Aeolian Harp”** has a reviewed Paderewski note counterpart, from the pickup through measure 49. **“Heroic” Polonaise Op. 53** has a complete model-reviewed pitch/attack counterpart for all 181 measures, an 82-chunk section-based plan, backward coda acquisition and transition drills. Both support automatic note-recall checks and explicit self-assessment.

- Work through 35 editable chunks, alternating score-visible study and hidden recall, then connect sections and the whole piece.
- Practise both hands, the right hand or the left hand, with separate saved progress for each mode. Hand selection follows the score's upper and lower staves.
- Set repetition counts, automatically finish correct passages and continue to the next attempt, or finish, pause and restart manually.
- Review learned chunks individually or together without changing your place in the lesson.
- See a live staff comparison and review pitch differences after a take. During hidden recall, upcoming notes and error hints stay hidden unless you peek.
- Save personal note adaptations, correct individual local reference notes, or explicitly count a take or stage by your own assessment. Automatic results and past attempts remain in history.
- Use the middle pedal to repeat an attempt and keep the score beside an adjustable controls panel, including in fullscreen.

Learning records **MIDI only**. It checks note recall across the assigned passage; it does not grade tempo, rhythm, expression or performance readiness. Starting requires the exact reviewed PDF, which is not included in the repository. The lessons' musical review was performed by a model and still needs real-player acceptance. Choose **Learning piece** to switch lessons; the last-viewed piece is restored at startup, with separate routines and progress for each piece and hand. Heroic's JSON reference and unmeasured MusicXML attack study are downloadable in the lesson. [Learning guide](docs/LEARNING.md) · [Aeolian review](docs/aeolian_harp_etude_op25_no1_learning.md) · [Heroic plan and transcription review](docs/heroic_polonaise_op53_learning.md)

### Review sessions and follow progress

After recording or importing MIDI, Chopin Studio proposes a timeline of pieces and attempts. You can correct labels and passage boundaries, split or merge activities, group attempts and undo timeline edits. Unknown or ambiguous material stays available for manual review.

**Sessions** is for organising recordings, editing the activity timeline, exporting originals and cleaning up audio. Choose a piece or passage in the timeline and tap **Analyse activity** to run analysis and open that same activity in **Analysis**. Save timeline edits before analysing.

**Library** has two views: **Score Library** for the score catalogue, and **Recordings Library** for saved performances organised by piece. Recordings lists only takes with available microphone audio or saved rendered MIDI audio, grouped into piece cards like the Score Library. MIDI-only takes and takes whose audio was removed remain accessible in Sessions. Unidentified audio has its own group. Saved-take views suppress the obsolete ALSA clean-stop “Interrupted system call” notice; original metadata and genuine capture/storage warnings are preserved. Open a piece to review a passage, download MIDI, listen to retained microphone audio or open a Practice recording in Analysis.

**Analysis** is for Practice sessions and imported performances; Learning takes are excluded from its picker and entry points. It has session and activity pickers. Switch between passages to view their latest saved analysis, rerun analysis, listen to retained microphone audio, or generate local and optional cloud reports. **Edit session timeline** returns to the selected activity in Sessions. The former session-wide velocity/pedal charts have been replaced by this activity-based workspace, which brings together:

- Original MIDI, microphone playback and passage downloads.
- Pitch differences against a digital reference, staff comparisons and a piano-roll view.
- Estimated local tempo, key-strike velocity and pedal-use summaries, plus microphone level and MIDI/audio timing evidence when available.
- Strict pitch comparison or a conservative musical-context view that highlights possible adaptations and uncertainty.
- Downloadable comparison PDFs, MusicXML passages, structured JSON, reports and complete-session bundles.

**Progress** shows recorded practice time, recording-day activity, per-piece history and comparisons between attempts. A piece's **Saved sessions** lists its attributed passages. Learning takes are grouped by piece and local calendar day in Sessions.

Measurements depend on the reference edition and the quality of the alignment. Eligible automatic levels and audio-production suggestions require verified references; your personal assessment stays separate. These tools support review and do not provide a definitive musical-quality grade. [Comparison guide](docs/MUSICAL_COMPARISON.md) · [Measurement definitions and validation](docs/VALIDATION.md)

### Try live recognition and page following

Enable **Live controls** in Practice to try recognizing the piece and estimating your position while you play. You can also select a piece manually. Recognition uses MIDI, not microphone transcription.

Automatic page turns are **off by default**. They require stable matches and links between score measures and PDF pages. Provisional digital references need an additional explicit opt-in; **Calibrate page** lets you add page links. Manual page navigation temporarily suspends automatic turns. Repeated passages, edition differences and uncertain matches can still cause mistakes. [Following and page-map readiness](docs/AUTO_PAGE_TURNING.md)

### Use optional audio, reports and voice controls

- **Rendered audio:** turn saved MIDI into WAV or FLAC using FluidSynth and an installed soundfont. This is generated sound; microphone capture records the actual instrument and room. For recording the AP-470's own sound directly, see [piano audio options](docs/AP470_AUDIO.md).
- **Reports:** generate local reports from saved analysis, or explicitly request an optional OpenAI report after configuring access.
- **Voice:** tap the floating Voice button and say “Open Nocturne Opus Nine Number One” to open a matching score. Learning note-rule and reference-correction forms also offer reason dictation.

## Install and start

The intended platform is **Linux Mint 22.x**, with **Python 3.12+**, **Node.js 20.19+** (22 recommended), npm or pnpm, and a current Chromium or Firefox browser. Voice recognition support varies by browser.

From a checkout of this repository:

```sh
sudo apt install python3-venv python3-pip libasound2-dev build-essential pkg-config alsa-utils
./scripts/install.sh
```

The installer downloads dependencies, creates a Python environment, builds the interface and adds **Chopin Studio** to the applications menu. The installer itself runs without root privileges. Launch from that menu or run:

```sh
make launch
```

The app starts a local service at [localhost:8765](http://127.0.0.1:8765) and opens a dedicated Chromium/Chrome app window when available, falling back to the default browser. Launching again reuses the running service. Rerun the installer after moving the repository; after updating, rebuild the interface and restart the app to load backend changes.

Optional MIDI-to-audio rendering needs FluidSynth and an SF2/SF3 soundfont. Optional OpenAI reports need `.venv/bin/python -m pip install -e '.[ai]'` and an API key configured in the AI panel or through `OPENAI_API_KEY`.

## Your first session

1. Connect the piano's USB Type-B port to the computer and switch on the piano.
2. Open **Settings & devices**, select the MIDI input if needed and check the note, velocity and pedal readouts.
3. In **Practice**, choose MIDI, microphone or both under **Recording sources**. Check the computer's sound-input settings when using its microphone.
4. Tap **Record session**, practise, then choose **Stop session → Stop & save session**. No piece selection is required.
5. Open **Sessions** to listen, review suggested passages, correct labels and export a take. Check **Audio cleanup** and protect audio you want to keep before shutting down.

To read a score, import its PDF in **Library** and set the piece's first and last PDF pages, counting from 1 including covers. Use **Learning** separately for the Aeolian Harp memory lesson or the Heroic Polonaise section plan.

## Privacy, storage and audio cleanup

Core recording, score viewing, analysis and local reports work offline after installation and importing your material. The service listens only on the local computer; interface assets are bundled locally. There is no telemetry or required cloud account.

Two optional features can use online services:

- **OpenAI reports** send structured analysis and your question only when you explicitly request a cloud report. The adapter does not upload raw MIDI files, PDFs or recorded audio.
- **Browser speech recognition**, used for commands and dictation, may send microphone audio to the browser's recognition provider and require internet access. It needs microphone permission; manual controls and typing remain available.

Data is stored in `$XDG_DATA_HOME/chopin-studio`, normally `~/.local/share/chopin-studio`. Set `CHOPIN_DATA_DIR` to choose another location. Back up the **entire data directory with the app shut down** to preserve the database, scores, recordings and history together. Do not run two services against the same directory.

**Audio cleanup can permanently remove audio.** By default, it shortlists audio for two complete or near-complete takes per piece and flags surplus audio and identified partial attempts for removal at shutdown. Unidentified or uncertain takes remain for review. Use **Keep this audio** to protect any take. The two-take policy applies to audio; MIDI, analysis and session history remain available.

Microphone takes with reliable MIDI evidence but no discernible piano sound—such as playing with headphones or muted speakers—can be discarded automatically after analysis and do not use the two-take allowance. Ambiguous audio and explicitly kept takes are protected. This detects absent audible piano; it cannot read the physical headphone-jack state.

**Delete audio** removes audio for a take. **Delete session** is a separate action that removes the whole session, including MIDI. Timeline undo cannot restore deleted sound. See [recording, retention and storage details](docs/MICROPHONE_RECORDING.md).

## Closing and recovery

Closing the Practice window leaves recording running. To stop the app, use the top-bar power button and **Save & shut down**; it saves an active recording before exiting and applies pending audio cleanup.

For MIDI-only recording, disconnecting the piano starts a 15-second grace period. Reconnect within that time to continue the same session; otherwise it is stopped and saved. Microphone-enabled sessions continue until stopped and keep the service running even with no open window. With no connected piano or open interface, the service otherwise shuts down after five minutes.

The recorder keeps a recovery journal and attempts to recover interrupted recordings on startup. Power loss or storage failure can still lose recent unsaved events; capture faults are reported. Avoid unplugging storage while recording. [Recovery architecture](docs/ARCHITECTURE.md)

## Development and further reading

The backend is Python/FastAPI; the interface is React/TypeScript. These commands assume installation has completed; development commands use pnpm:

```sh
make dev                          # local backend and Vite interface
make test                         # Python and frontend logic tests
cd frontend
pnpm exec playwright install chromium
pnpm test:e2e                     # isolated headless browser tests
```

Browser tests use a separate loopback port, temporary application data and simulated input with `CHOPIN_NO_HARDWARE=1`. They must not attach to an existing browser or access the physical piano or microphone. Automated checks do not establish real-device acceptance.

- [Implemented scope and limitations](docs/LIMITATIONS.md)
- [Documentation review against the implementation](docs/IMPLEMENTATION_REVIEW.md)
- [Learning workflow](docs/LEARNING.md)
- [Microphone recording and retention](docs/MICROPHONE_RECORDING.md)
- [Score sources and missing references](docs/SOURCES.md)
- [Hardware and touch acceptance](docs/ACCEPTANCE.md)
- [Architecture](docs/ARCHITECTURE.md) and [validation](docs/VALIDATION.md)
- [Roadmap](docs/ROADMAP.md) and [future work](docs/TODO.md)
