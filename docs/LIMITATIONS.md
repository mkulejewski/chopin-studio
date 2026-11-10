# Implemented scope and remaining acceptance work

Version 0.2 continues all five milestones. It provides working paths across the workflow; several music-information-retrieval features remain experimental. Do not equate implementation coverage with verified musical accuracy or physical-hardware acceptance.

## Milestone 1 — recorder and library

Dedicated MIDI callback/queue/journal writer, fsync/recovery, bounded capture memory, interruption markers, valid MIDI export including SysEx, preserved imported originals, midicsv import, diagnostics, simulation, standalone launcher/shutdown protection, touch PDF viewer and optional CC66 controls remain implemented.

The personal catalogue now contains all 44 supplied works under composer/genre/work paths, with subjective mastery, liking, forgotten flags, intentions and original partial-learning notes. Ten Paderewski scans are cached locally. 41 exact-scan page ranges have been reviewed; the Raindrop Prelude retains its exclusive Schott preference. B.150 and B.133 are absent from the downloaded Waltzes/Minor Works volumes and retain a clearly missing supplementary score slot. See SOURCES.md. The complete six-volume catalogue beyond the supplied repertoire is not exhaustive.

## Milestone 2 — organisation

On stop/import, a separate background job proposes adaptive silence boundaries and reference-based work changes. RapidFuzz provides subsequence/edit matching; polyphonic chord overlap and indexed melodic n-grams rank candidates. Partial excerpts, tempo changes, wrong notes and repeated separated attempts have synthetic tests. Low similarities and close competing identities remain unknown/ambiguous. Similarities are not calibrated probabilities.

A touch timeline supports numeric boundary edits, split, merge, piece/measure correction, complete/disposable flags, attempt groups, optimistic revision checks and undo. Confirmed excerpts can become reusable labelled MIDI references. Segment exports initialise active notes/controller states and terminate notes/pedals without changing originals.

Limitations: continuous within-piece restarts and rubato boundaries are not yet robustly resolved; legitimate recurring themes may be ambiguous. Candidate boundaries need review. Multi-hour offline-analysis RAM is not bounded like capture: note extraction currently materialises a session's notes. An oversized personal reference library needs further candidate-index benchmarking. Labelled MIDI has no score-level measure certainty.

## Milestone 3 — technical measurements

Partitura ingests safe MusicXML/MXL, preserving note pitches, ties, grace flags, score-quarter timings, measures, staff and voice metadata. References expose source, licence, edition and provisional/verified/rejected status. The touch review editor can correct the analysis note representation and save prior snapshots; source MusicXML remains unchanged and its score preview explicitly says corrections are separate.

Activity analysis stores versioned evidence for matched pitch discrepancies, unpaired expected groups, score-relative local tempo estimates, reference staff/voice velocity summaries, pedal thresholds/partial values and reference grace-note counts. Every uncertain discrepancy retains its caveat and ID. Accuracy percentages remain withheld: repeated structure, ornaments, hand/voice ambiguities and edition differences are not resolved well enough for a defensible percentage. There is no claim of a complete ornament-specific evaluator or acoustic diagnosis.

## Milestone 4 — audio and reports

FluidSynth rendering is explicitly requested, asynchronous, single-concurrency and cancellable. It uses installed/user-supplied SF2/SF3, release tails, WAV/FLAC and journal tags to exclude page-command CC66 from generated sound. Browser-native audio controls allow listening. Originals survive failures/cancellation. Installed sfizz/Pianoteq executables are detected but their rendering adapters are not implemented or tested. The external-engine interface needs vendor/version-specific supported command contracts.

Local evidence-linked reports, downloadable reports and complete-session MIDI/audio/report bundles work without cloud services. Optional OpenAI Responses API uses structured evidence, explicit UI disclosure/action, an environment key, a user-editable model and `store=False`; no automatic call is made. It has no real-cloud validation in this environment. Arbitrary local LLM provider adapters are not implemented. Report text edits create new revisions; historical reports are retained.

Renderer concurrency is limited to one, with a Linux address-space ceiling of 2 GiB (override via CHOPIN_RENDER_MEMORY_MB). A large piano library may require a consciously raised limit. Cancellation can stop rendering, but an already-running synchronous cloud HTTP request may take its configured timeout to return. AI-generated prose is interpretation, not a replacement for deterministic facts.

## Milestone 5 — live environment and progress

Live piece recognition and score-position estimates consume a separate bounded best-effort queue, never the authoritative recording queue. Recognition can work before a score is selected. Enable it in Live controls; manually pin a piece if useful. Automatic turns require a verified reference or explicit provisional-following opt-in, high similarity, three stable advancing matches, coverage of the latest notes, explicit measure/PDF page links and a 10-second manual-navigation override. Provisional following does not verify a reference or enable its technical levels. Backward jumps/restarts reset turn stability. A confident timing anchor can sustain labelled estimated following for up to 30 seconds or eight measures while notes continue; a three-second silence pauses estimation until reacquisition. The rolling window retains up to 32 onset groups within a 512-note cap, so dense chords do not reduce the input to fewer than eight required onsets. Capture remains available if recognition errors or the optional consumer overruns.

This is experimental fingerprint/edit-based following, not a completed Matchmaker integration. Matchmaker/Partitura were inspected before implementation; evaluating Matchmaker's specialist repeat/restart tracking remains necessary before production automatic-following acceptance. Current maps initially contain first-measure links. Calibrate each page beside the displayed PDF; pagination cannot be inferred reliably from a different MusicXML edition or scanned PDF. Turns occur when a stable match reaches the mapped measure; there is no predictive turn ahead of the page boundary. Edition differences may cause incorrect turns with provisional following enabled.

Tempo inference matches bass notes below MIDI 60 independently within the recognised score span, falling back to matched score-note timing when bass evidence is insufficient. It requires at least four timing anchors and two usable interval estimates, uses median slopes over up to four preceding anchors, and does not bridge intervals over eight seconds. BPM is quarter notes per minute, regardless of the score's meter. Sparse passages, repeated bass patterns, wrong alignment and unverified editions can leave estimates uncertain or unavailable. Attached acoustic WAVs are not transcribed by this estimator.

Per-piece attributed time, activity counts/completions, recent recording-day heatmaps, forgotten/learning priorities and same-piece take comparisons are available. Time attribution depends on confirmed/corrected matches; recorded time includes pauses. Comparative measurements use the current reference and disclose coverage differences, while historical stored analyses remain intact. No single numerical musical-quality grade is produced.

## Still requires actual hardware/user validation

AP-470 connection/reconnection, all three physical pedals, native Linux Mint/Cinnamon touchscreen/OSK/display scaling, internal sostenuto effect, audio routing and multiple wall-clock hours under CPU/disk pressure. Browser touch emulation and accelerated timestamp tests do not substitute for these checks. No real hardware or real cloud-AI success is claimed.

Offline segmentation checks shorter silences (at least three seconds after held notes end) when independent phrases on either side confidently identify different pieces. Two consecutive phrase windows are required for a change without silence. Whole-take opening/ending evidence is checked separately so a later alignment cannot hide the introduction. Existing saved timelines need **Rebuild candidate timeline (undo available)** to use the revised algorithm.
