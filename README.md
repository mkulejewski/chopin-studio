# Chopin Studio

Chopin Studio is a piano practice companion that runs on your own computer. Read sheet music, record a practice session, revisit individual attempts and work on memorizing a piece in one place. You can start recording without choosing a piece or naming a file.

The application is designed for Linux Mint, a touchscreen and a Casio AP-470 connected by USB MIDI. Its library focuses on Chopin. Other MIDI devices can be selected in Settings, though compatibility needs checking on the actual instrument.

Future repertoire expansion includes Bach's *Well-Tempered Clavier*, Rachmaninoff's Prelude Op. 23 No. 5, selected Liszt works and all three movements of Beethoven's “Moonlight” Sonata. Each may be introduced in Practice only or in both Practice and Learning; see the [repertoire to-do list](docs/TODO.md#repertoire-beyond-chopin) for the requested works and review requirements.

Chopin's Nocturne in C minor, Op. 48 No. 1 is also planned for future Learning implementation; see the [Learning content to-do list](docs/TODO.md#next-pieces-to-implement).

Recording, score reading, session review, progress tracking and a dedicated Learning workspace are implemented. Project progress is measured by implemented features and their validation. Live recognition and score following provide similarity and position estimates; performance analysis remains experimental. Physical piano, microphone and touchscreen acceptance is still incomplete; see [current limitations](docs/LIMITATIONS.md).

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
- Use **App fullscreen** for the whole workspace or **Score fullscreen** for a larger score with practice controls available. Practice Score fullscreen opens the recognition panel automatically; **Hide recognition** collapses it for that visit. Optional pedal controls can turn pages.
- Import MusicXML files—a digital representation of the notes—for recognition and comparison. Preview them and review or correct the analysis reference separately from the source file. Library cards distinguish verified and provisional references. Individually scan-reviewed Practice counterparts are installed alongside their originals, with edition, measure coverage and review limits recorded. The narrowed nine-piece batch is complete, including both Op.40 Polonaises, Nocturne B.49, Waltz Op.64 No.2 and the Revolutionary Étude; every measure and both staves were model-reviewed against Paderewski scans. See the [counterpart audit and edition limits](docs/LIBRARY_COUNTERPART_AUDIT.md).

PDF score collections, imported MusicXML references and sound libraries are **not bundled with the source code**. Add copies you are entitled to use. Optional acquisition scripts and their source coverage are documented in [score sources and gaps](docs/SOURCES.md). A PDF scan alone does not provide the digital notes needed for matching or pitch analysis.

### Learn notes from memory

**Learning** offers three separate piece profiles. **Étude Op. 25 No. 1, “Aeolian Harp”** has a reviewed Paderewski note counterpart, from the pickup through measure 49. **“Heroic” Polonaise Op. 53** has a complete model-reviewed pitch/attack counterpart for all 181 measures, an 82-chunk section-based plan, backward coda acquisition and transition drills. **Nocturne Op. 15 No. 1** has a [model-reviewed counterpart and lesson plan](docs/nocturne_op15_no1_learning.md), covering 75 measure entries in 37 chunks. All three support automatic note-recall checks and explicit self-assessment with the exact reviewed PDF.

- Work through 35 editable chunks, alternating score-visible study and hidden recall, then connect sections and the whole piece.
- Practise both hands, the right hand or the left hand. Completed both-hands stages also count for each separate hand, including previously saved progress; higher separate-hand progress is preserved. Streaks and take histories stay specific to each mode. Hand selection follows the score's upper and lower staves.
- **Peek at score** stays open during an immediate retake, including pedal and automatic retries. Retakes after peeking remain assisted; finish or pause and start a fresh attempt for unassisted recall.
- Set repetition counts, automatically finish correct passages and continue to the next attempt, or finish, pause and restart manually.
- Review learned chunks individually or together without changing your place in the lesson.
- See a live staff comparison and review pitch differences after a take. During hidden recall, upcoming notes and error hints stay hidden unless you peek.
- Save personal note adaptations, correct individual local reference notes, or explicitly count a take or stage by your own assessment. Automatic results and past attempts remain in history.
- Use the middle pedal to repeat an attempt and keep the score beside an adjustable controls panel, including in fullscreen. Learning preloads and renders the assigned PDF pages during hidden recall, keeping them concealed until you peek or return to visible study.

Learning records **MIDI only**. It checks note recall across the assigned passage; it does not grade tempo, rhythm, expression or performance readiness. Starting requires the exact reviewed PDF, which is not included in the repository. The lessons' musical review was performed by a model and still needs real-player acceptance. Choose **Learning piece** to switch lessons; the last-viewed piece is restored at startup, with separate routines and progress for each piece and hand. Heroic's JSON reference and unmeasured MusicXML attack study are downloadable in the lesson. [Learning guide](docs/LEARNING.md) · [Aeolian review](docs/aeolian_harp_etude_op25_no1_learning.md) · [Heroic plan and transcription review](docs/heroic_polonaise_op53_learning.md)

### Check a score against your playing

Open **Score certification** on a Learning-grade score card or under **Score tools** near the bottom of Learning. Choose the whole piece, a measure range or your contiguous both-hands learned range. Play the written notes verbatim from both staves of your Paderewski copy to check the digital counterpart against the printed score. Watch the live MIDI staves to confirm the registered pitches. **Finish and review** compares the selected range. **Pause and review up to here** compares through the last aligned attack. The saved review shows matched pitches, red differences and proposed reference edits for isolated discrepancies. You can include a snapshot of your saved Learning score corrections for a take. Certification has its own recordings and review history. In a hand-entered correction review, choose a measure or cycle through individual pitch edits on the staves. [Score certification guide](docs/LEARNING.md#score-certification)

### Review sessions and follow progress

After recording or importing MIDI, Chopin Studio proposes a timeline of pieces and attempts. Recognition supports distinctive six-onset short attempts and conservative mid-piece retry splits. Repeated themes can identify the piece while keeping the score location uncertain. In Practice **Live controls**, enable **Automatically open the recognised piece** to open a stable, unambiguous match; the option defaults off and enables recognition when selected. You can correct labels and passage boundaries, split or merge activities, group attempts and undo timeline edits. Unknown or ambiguous material stays available for manual review.

Repeated full performances of the same piece and later returns to its opening can now form separate takes without a long silence. Each take gets its own completeness check; an opening return no longer automatically makes the preceding take partial. Recognition uses broader error-tolerant retrieval, underlying similarity for candidate ranking and independent passage evidence for long alignments. Rolled chords and extra opening attacks now use chord-supported phrase evidence for restart detection, with a forward-passage check to keep plausible written returns intact. Disjoint repeated motifs cannot extend a partial take’s displayed measure range. Live restarts discard stale note/tempo context. Existing saved timelines remain unchanged until explicitly rebuilt. See [recognition and Nocturne counterpart findings](docs/RECOGNITION.md).

**Sessions** is for organising recordings, editing the activity timeline, exporting originals and cleaning up audio. Choose a piece or passage in the timeline and tap **Analyse activity** to run analysis and open that same activity in **Analysis**. Save timeline edits before analysing.

**Library** has two views: **Score Library** for the score catalogue, and **Recordings Library** for saved performances organised by piece. Recordings lists only takes with available microphone audio or saved rendered MIDI audio, grouped into piece cards like the Score Library. MIDI-only takes and takes whose audio was removed remain accessible in Sessions. Unidentified audio has its own group. Saved-take views suppress the obsolete ALSA clean-stop “Interrupted system call” notice; original metadata and genuine capture/storage warnings are preserved. Open a piece to review a passage, download MIDI, listen to retained microphone audio or open a Practice recording in Analysis.

**Analysis** is for Practice sessions and imported performances; Learning takes are excluded from its picker and entry points. It has session and activity pickers. Switch between passages to view their latest saved analysis, rerun analysis, listen to retained microphone audio, or generate local and optional cloud reports. **Edit session timeline** returns to the selected activity in Sessions. The former session-wide velocity/pedal charts have been replaced by this activity-based workspace, which brings together:

- Original MIDI, microphone playback and passage downloads.
- Pitch differences against a digital reference, staff comparisons and a piano-roll view.
- A full-width **Whole-piece overview** across all saved measures, with whole/half/quarter-piece scales, a range slider, selectable measurement lanes and tap-to-review measures. Taller chart lanes and labelled y-axis gridlines (including local tempo in BPM) make values easier to read. Measure means and minimum–maximum strokes reveal broad tempo/dynamics shapes independently of the detailed note pagination; partial takes cover only their analysed region.
- Synchronized score-beat curves for local tempo, velocity, voice dynamics, key duration, pedal and release velocity, with per-passage discrepancies and configurable bass/inner-voice/melody balance targets. CC88 fourteen-bit reconstruction preserves original seven-bit values; release interpretation requires device calibration.
- **Compare different takes of a piece** overlays shared score positions from two attempts. Microphone level and MIDI/audio timing evidence remain available separately.
- Strict pitch comparison or a conservative musical-context view that highlights possible adaptations and uncertainty.
- Downloadable comparison PDFs, MusicXML passages, structured JSON, reports and complete-session bundles.

**Progress** shows piece and measure time, current measure evidence, recurring differences, unassisted recall retention, separate technical objectives and explicitly attributed musical-problem time. See [Progress guide](docs/PROGRESS.md). A piece's **Saved sessions** lists its attributed passages. Learning takes are grouped by piece and local calendar day in Sessions.

Measurements depend on the reference edition and the quality of the alignment. Eligible automatic levels and audio-production suggestions require verified references; your personal assessment stays separate. These tools support review and do not provide a definitive musical-quality grade. [Comparison guide](docs/MUSICAL_COMPARISON.md) · [Measurement definitions and validation](docs/VALIDATION.md)

Aeolian Harp Learning also offers **Review all learned · build backward**: recall the last two learned chunks, then four, six and so on through the learned passage. Each unassisted pass prepares the next length; press **Start review** to begin it. Existing full-span and single-chunk reviews remain available.

Build-backward reviews allow score peeks: after finishing a take, choose **Mark review take correct** to prepare the next length (or complete the full span) by your own judgement. The assisted flag, pitch verdict and errors remain in history. This manual action does not change learning mastery or streaks; aborted takes, capture faults and obsolete assignments cannot be accepted. Ordinary learning recall still requires unassisted takes for counted repetitions.

Learning reviews default to a local error tone and **measure rewind** after a definite pitch/order mistake: the error pauses your run; release all keys, replay from the beginning of the indicated bar, and keep playing through the original end. Recording stays active across the following measures, with no Finish/Start step at the repaired bar. **Retake last measure** also works manually; **Restart whole review** remains available. The review-specific option is in Edit routine. MIDI and learning progress are preserved; separate retry/tail takes do not count as an uninterrupted build-backward pass, but **Mark review sequence correct** can expand it by your own judgement. See [Learning review retries](docs/LEARNING.md#measure-retries-in-review).

Learning offers **Turn score pages automatically while peeking**, on by default and remembered in this browser. During an active peek it follows the latest matched attack in the reviewed lesson’s PDF map. Hidden recall never reveals page position; uncertain or unmatched latest notes hold the page. Manual navigation pauses automatic turns for ten seconds. This display aid does not change assessment or enable Practice recognition; provisional lessons do not turn automatically.

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

The installer downloads dependencies, creates a Python environment, builds the interface and adds **Chopin Studio** to the applications menu. The installer itself runs without root privileges. Launch from that menu or use the executable startup file in the project folder:

```sh
./start.sh
```

The startup file works from any working directory and forwards launcher options,
for example `./start.sh --fullscreen`. `make launch` remains available.

The app starts a local service at [localhost:8765](http://127.0.0.1:8765) and opens a dedicated Chromium/Chrome app window when available, falling back to the default browser. Launching again reuses the running service. Rerun the installer after moving the repository; after updating, rebuild the interface and restart the app to load backend changes.

Optional MIDI-to-audio rendering needs FluidSynth and an SF2/SF3 soundfont. Optional OpenAI reports need `.venv/bin/python -m pip install -e '.[ai]'` and an API key configured in the AI panel or through `OPENAI_API_KEY`.

## Your first session

1. Connect the piano's USB Type-B port to the computer and switch on the piano.
2. Open **Settings & devices**, select the MIDI input if needed and check the note, velocity and pedal readouts.
3. In **Practice**, choose MIDI, microphone or both under **Recording sources**. Check the computer's sound-input settings when using its microphone.
4. Tap **Record session**, practise, then choose **Stop session → Stop & save session**. No piece selection is required.
5. Open **Sessions** to listen, review suggested passages, correct labels and export a take. Audio cleanup starts collapsed, including after saving a recording; open it with **Audio cleanup · kept & flagged recordings**. Check **Audio cleanup** and protect audio you want to keep before shutting down.

To read a score, import its PDF in **Library** and set the piece's first and last PDF pages, counting from 1 including covers. Opening a score in **Practice**, returning to Practice or reloading starts at the piece’s first configured PDF page (page 1 if no range is set), rather than the last page viewed. Zoom, crop and one/two-page preferences remain saved per piece. Use **Learning** separately for the Aeolian Harp memory lesson or the Heroic Polonaise section plan.

## Privacy, storage and audio cleanup

Core recording, score viewing, analysis and local reports work offline after installation and importing your material. The service listens only on the local computer; interface assets are bundled locally. There is no telemetry or required cloud account.

Two optional features can use online services:

- **OpenAI reports** send structured analysis and your question only when you explicitly request a cloud report. The adapter does not upload raw MIDI files, PDFs or recorded audio.
- **Browser speech recognition**, used for commands and dictation, may send microphone audio to the browser's recognition provider and require internet access. It needs microphone permission; manual controls and typing remain available.

Data is stored in `$XDG_DATA_HOME/chopin-studio`, normally `~/.local/share/chopin-studio`. Set `CHOPIN_DATA_DIR` to choose another location. Back up the **entire data directory with the app shut down** to preserve the database, scores, recordings and history together. Do not run two services against the same directory.

**Audio cleanup can permanently remove audio.** By default, it shortlists the two best complete takes per piece using a transparent musical-evidence score: whole-take note alignment, timing control within measures and written dynamic contrasts, plus recording quality and chosen voicing targets where available. Smooth tempo changes and inter-measure rubato are not treated as metronomic errors. Recency does not select winners; missing evidence, incompatible references and boundary ties retain audio for review. Surplus ranked audio and identified partial attempts can be flagged for removal at shutdown. Use **Keep this audio** to protect any take. MIDI, analysis and session history remain available. See [ranking details and limitations](docs/AUDIO_QUALITY_RANKING.md).

Microphone takes with reliable MIDI evidence but no discernible piano sound—such as playing with headphones or muted speakers—can be discarded automatically after analysis and do not use the two-take allowance. Ambiguous audio and explicitly kept takes are protected. This detects absent audible piano; it cannot read the physical headphone-jack state.

**Delete audio** removes audio for a take. **Delete session** is a separate action that removes the whole session, including MIDI. Timeline undo cannot restore deleted sound. See [recording, retention and storage details](docs/MICROPHONE_RECORDING.md).

## Closing and recovery

Closing the Practice window leaves recording running. To stop the app, use the top-bar power button and **Save & shut down**; it saves an active recording before exiting and applies pending audio cleanup.

For MIDI-only recording, disconnecting the piano starts a 15-second grace period. Reconnect within that time to continue the same session; otherwise it is stopped and saved. Microphone-enabled sessions continue until stopped and keep the service running even with no open window. With no connected piano or open interface, the service otherwise shuts down after five minutes.

The recorder keeps a recovery journal and attempts to recover interrupted recordings on startup. Power loss or storage failure can still lose recent unsaved events; capture faults are reported. Avoid unplugging storage while recording. [Recovery architecture](docs/ARCHITECTURE.md)

## Platform support

The Linux desktop application uses the shared recording, analysis, Learning and
SQLite services with Linux adapters for USB MIDI, ALSA and FluidSynth. Existing
device preferences still apply. With an empty preferred-device setting, the
Casio AP-470 has priority and generic keyboards can connect automatically.
Per-port observations, confirmed capabilities and optional release calibration
are available through the local device capability API. See the
[architecture and API contract](docs/ARCHITECTURE.md#device-capability-profiles).

The base Python package is for engine and service use. For a manual Linux
application install, use `.venv/bin/python -m pip install -e '.[linux,web]'`. The standard installer
already installs those extras. Android is future work
for a standalone MIDI-first phone app. See the [port plan](docs/ANDROID_PORT.md).

## Development and further reading

Completed agent changes are validated and committed locally by default. See the [agent instructions](AGENTS.md).

The backend is Python/FastAPI; the interface is React/TypeScript. These commands assume installation has completed; development commands use pnpm:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check backend/chopin  # install the optional [quality] extra
cd frontend
pnpm format:check                 # incremental frontend style checks
pnpm test
pnpm build                        # strict TypeScript + production assets
pnpm exec playwright install chromium
PLAYWRIGHT_CHANNEL=chromium pnpm test:e2e
PLAYWRIGHT_CHANNEL=chromium pnpm exec playwright test --config=playwright.learning.config.ts
PLAYWRIGHT_CHANNEL=chromium pnpm exec playwright test --config=playwright.sessions.config.ts
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

Structural engineering work and compatibility boundaries are tracked in
[Refactoring](docs/REFACTORING.md), with a complete starting
[source inventory](docs/REFACTORING_INVENTORY.md).

Current Practice evidence uses shared timeline, source/deletion and reference
revision checks; historical analyses remain available when current eligibility
changes. Audio review retains its separate manual-retention policy.

Backend domain boundaries now separate Learning definitions/matching/profiles and
Practice projection/recognition/segmentation/analysis from stateful controllers.
Existing public imports remain available; see the refactoring guide for owners.

HTTP handlers live in scoped `backend/chopin/api/` routers; `create_app()` owns
service composition and shutdown. Atomic timeline edits/undo live in `timeline.py`.
Catalogue initialization uses the single repertoire definition and preserves
existing seed markers, personal fields and legacy startup repair behavior.

The architecture refactor separates workspace pages, Learning editors, review
panels, score interaction hooks and shared response types. Scoped styles preserve
the original cascade. Each Playwright invocation creates fresh data/state and
checks Full HD plus smaller viewports. CI runs backend correctness lint/tests and
frontend format/types/build/browser checks using synthetic fixtures. See
[Refactoring and developer guide](docs/REFACTORING.md) for ownership, compatibility,
measurements and acceptance limits.

[GitHub Actions checks](.github/workflows/checks.yml) run independent backend,
frontend and browser jobs. Browser jobs use fresh temporary data and synthetic
fixtures; hosted CI execution is still pending publication of this branch.
