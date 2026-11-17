# Implemented scope and remaining acceptance work

Reviewed against the working tree on 2026-11-12. The application provides working paths across all five original milestones plus Learning and microphone recording; several music-information-retrieval features remain experimental. Implementation coverage does not establish verified musical accuracy or physical-hardware acceptance. See the [documentation review](IMPLEMENTATION_REVIEW.md) and consolidated [future-work checklist](TODO.md).

## Milestone 1 — recorder and library

Dedicated MIDI callback/queue/journal writer, fsync/recovery, bounded capture memory, interruption markers, valid MIDI export including SysEx, preserved imported originals, midicsv import, diagnostics, simulation, standalone launcher/shutdown protection, touch PDF viewer and optional CC66 controls remain implemented.

The personal catalogue contains all 44 supplied works under composer/genre/work paths, with subjective mastery, liking, forgotten flags, intentions and original partial-learning notes. The dated acquisition record reports ten local Paderewski scans and 41 reviewed exact-scan work ranges; these assets are not bundled and were not rechecked in the current installation during this review. Raindrop retains its exclusive Schott preference. The recorded exact-score gaps are Schott Raindrop, B.150 and B.133. See [Sources](SOURCES.md). Catalogue coverage beyond the supplied repertoire, full volume/supplement indexing and bibliographic editing remain incomplete.

Nine measured Practice counterparts now have complete model audits against exact local Paderewski scans: Prelude Op.28 No.4; Mazurkas Op.30 No.2 / Op.68 Nos.2–3; Nocturne B.49; Polonaises Op.40 Nos.1–2; Waltz Op.64 No.2; and Étude Op.10 No.12. This finishes the narrowed request; the other 31 original candidates are deferred by the user; all 42 acquired first-edition/Noctave originals retain their provisional status. The Schott Raindrop and B.150 audits are deferred at the user’s request. See [scope and review limits](LIBRARY_COUNTERPART_AUDIT.md).

## Milestone 2 — organisation

On stop/import, a separate background job proposes adaptive silence boundaries and reference-based work changes. RapidFuzz provides subsequence/edit matching; polyphonic chord overlap and indexed melodic n-grams rank candidates. Partial excerpts, tempo changes, wrong notes and repeated separated attempts have synthetic tests. Low similarities and close competing identities remain unknown/ambiguous. Similarities are not calibrated probabilities.

A touch timeline supports numeric boundary edits, split, merge, piece/measure correction, complete/disposable flags, attempt groups, optimistic revision checks and undo. Confirmed excerpts can become reusable labelled MIDI references. Segment exports initialise active notes/controller states and terminate notes/pedals without changing originals.

Repeated full takes and later returns to a supported opening can now be split without a long silence; completeness is checked separately for each take. Long-span alignment uses independent local windows, and provisional candidate ranking no longer creates artificial capped-score ties. Short mid-piece retries with unique six-chord context remain supported. General repeat/ornament traversal, severely damaged openings and rubato boundaries remain experimental; legitimate recurring themes may be ambiguous. Candidate boundaries need review. Multi-hour offline-analysis RAM is not bounded like capture: note extraction currently materialises a session's notes. An oversized personal reference library needs further candidate-index benchmarking. Labelled MIDI has no score-level measure certainty. See [recognition findings and provisional Nocturne exports](RECOGNITION.md).

## Milestone 3 — technical measurements

Partitura ingests safe MusicXML/MXL, preserving note pitches, ties, grace flags, score-quarter timings, measures, staff and voice metadata. References expose source, licence, edition and provisional/verified/rejected status. The touch review editor can correct the analysis note representation and save prior snapshots; source MusicXML remains unchanged and its score preview explicitly says corrections are separate.

Activity analysis stores versioned evidence for matched pitch discrepancies, unpaired expected groups, score-relative local tempo estimates, reference staff/voice velocity summaries, pedal thresholds/partial values and reference grace-note counts. Discrepancies retain caveats and evidence IDs. Strict pitch precision/recall/F1 percentages are implemented as technical alignment proxies; the separate general `accuracy` field remains unset. Technical practice/good/concert levels require a verified reference, similarity at least 0.85 and no reference grace notes. Whole-piece levels and audio-production suggestions also require at least 95% group coverage, alignment reaching both ends and healthy capture. These labels do not certify interpretation or concert readiness; [definitions](VALIDATION.md#todo-implementation--2026-10-30) describe the gates. General ornament-specific evaluation and acoustic diagnosis are not implemented.

Conservative musical-context comparison, staff/piano-roll review and full-activity comparison PDF export are implemented. Possible octave redistribution or chord reduction remains visible as uncertainty rather than assumed intent. Comparison notation uses reference positions and regenerated durations/voices; it does not transcribe played rhythm or faithfully re-engrave exceptional tuplets. OMR/automatic scan conversion and note-coordinate overlays on the original PDF remain future work. See [musical comparison](MUSICAL_COMPARISON.md).

## Milestone 4 — audio and reports

FluidSynth rendering is explicitly requested, asynchronous, single-concurrency and cancellable. It uses installed/user-supplied SF2/SF3, release tails, WAV/FLAC and journal tags to exclude page-command CC66 from generated sound. Browser-native audio controls allow listening. Originals survive failures/cancellation. Installed sfizz/Pianoteq executables are detected but their rendering adapters are not implemented or tested. The external-engine interface needs vendor/version-specific supported command contracts.

Local evidence-linked reports, downloadable reports and complete-session MIDI/audio/report bundles work without cloud services. Optional OpenAI Responses API uses structured evidence, explicit UI disclosure/action, an environment key, a user-editable model and `store=False`; no automatic call is made. It has no real-cloud validation in this environment. Arbitrary local LLM provider adapters are not implemented. Report text edits create new revisions; historical reports are retained.

Renderer concurrency is limited to one, with a Linux address-space ceiling of 2 GiB (override via CHOPIN_RENDER_MEMORY_MB). A large piano library may require a consciously raised limit. Cancellation can stop rendering, but an already-running synchronous cloud HTTP request may take its configured timeout to return. AI-generated prose is interpretation, not a replacement for deterministic facts.

## Milestone 5 — live environment and progress

Live piece recognition and score-position estimates consume a separate bounded best-effort queue, never the authoritative recording queue. Recognition can work before a score is selected. Enable it in Live controls; manually pin a piece if useful. Automatic turns require a verified reference or explicit provisional-following opt-in, high similarity, three stable advancing matches, coverage of the latest notes, explicit measure/PDF page links and a 10-second manual-navigation override. Provisional following does not verify a reference or enable its technical levels. Backward jumps/restarts reset turn stability. A confident timing anchor can sustain labelled estimated following for up to 30 seconds or eight measures while notes continue; a three-second silence pauses estimation until reacquisition. The rolling window retains up to 32 onset groups within a 512-note cap, so dense chords do not reduce the input to fewer than the required onset groups. Distinctive six/seven-onset attempts have stricter recognition gates; repeated phrase alternatives withhold stable position. An opt-in auto-open setting opens stable recognised pieces without enabling page turns. Capture remains available if recognition errors or the optional consumer overruns.

Live recognition uses fingerprint/edit-based following; Matchmaker is not integrated. Backward matches that also fit nearby returning themes hold the page, but this bounded continuity check does not resolve every repeat or ornament. Partitura is used for reference import; Matchmaker was researched but is not a runtime dependency. Evaluating specialist repeat/restart tracking remains future work. Basic indexing supplies opening links; a separate reviewed manifest records 193 links across 41 works, with eleven deliberately withheld boundaries. Applying that manifest requires exact source fingerprints and does not verify musical content. Calibrate other pages beside the displayed PDF; pagination cannot be inferred from a different edition. Note-confirmed turns occur at mapped boundaries; estimated turns add one/two-measure margins and a two-second dwell. There is no predictive early turn. Bass/whole-score half/double-tempo disagreement suspends estimation. Edition differences can still cause incorrect turns with provisional following enabled. See [reviewed links](REVIEWED_PAGE_LINKS.md) and [following](AUTO_PAGE_TURNING.md).

Tempo inference matches bass notes below MIDI 60 independently within the recognised score span, falling back to matched score-note timing when bass evidence is insufficient. It requires at least four timing anchors and two usable interval estimates, uses median slopes over up to four preceding anchors, and does not bridge intervals over eight seconds. BPM is quarter notes per minute, regardless of the score's meter. Sparse passages, repeated bass patterns, wrong alignment and unverified editions can leave estimates uncertain or unavailable. Attached acoustic WAVs are not transcribed by this estimator.

Per-piece attributed time, activity counts/completions, recent recording-day heatmaps, forgotten/learning priorities and same-piece take comparisons are available. Time attribution depends on confirmed/corrected matches; recorded time includes pauses. Comparative measurements use the current reference and disclose coverage differences, while historical stored analyses remain intact. No single numerical musical-quality grade is produced.

## Microphone capture and audio retention

Practice can record local mono 48 kHz/16-bit microphone audio, MIDI or both. Captured PCM is finalized as lossless FLAC; interrupted PCM can be recovered. Audio-only energy segmentation proposes unidentified activities rather than transcribing notes or recognizing pieces. Level/attack measurements and uncertain MIDI/audio offset estimates are implemented; hardware sample-zero calibration, clock-drift correction and acoustic pitch/interpretation analysis are not provided.

The two-take shortlist applies only to stored audio and compares complete takes by an explicit combination of note, within-measure timing and written-dynamics proxies, adding available recording/voicing evidence. This is not a calibrated overall musical-quality grade: complex rubato, hairpins, interpretation, articulation, pedal intention and acoustic tone remain incompletely assessed. Unscored/incomparable takes and shortlist-boundary ties remain for review rather than being selected by date. Surplus ranked audio and identified partial attempts can be removed at shutdown; Keep flags protect any take. A separate conservative MIDI-guided inaudible-piano detector can remove microphone intervals immediately after analysis; it does not detect a physical headphone plug. Audio cleanup preserves MIDI/history. Entire-session deletion is explicit and separate. See [ranking](AUDIO_QUALITY_RANKING.md) and [microphone recording and deletion policy](MICROPHONE_RECORDING.md).

## Learning

The Aeolian Harp lesson has a separate model-reviewed pitch/attack counterpart and exact-PDF gate. Visible/hidden chunks, cumulative connections, auto finish/continuation, manual/self-assessed advancement, local note corrections/adaptations, per-hand progress, learned-chunk review, live comparison staves and pedal repeat are implemented. Startup review selects a learned prefix without starting recording. Live staves are provisional display evidence; full-passage evaluation owns pass decisions.

Heroic Op. 53 has a complete model-reviewed Paderewski pitch/attack counterpart for all 181 measures, with required printed graces, local ornament policies and automatic note checks. Its plan uses independent sections, backward coda acquisition, boundary drills and separate persistence. The downloadable MusicXML is an unmeasured attack study, not a facsimile engraving; consult the scan for durations, sustain, pedal and expression. Trill realization count and speed are not graded. Earlier provisional progress remains historical and reviewed progression starts fresh. See [Heroic review](heroic_polonaise_op53_learning.md). Model review is not independent editorial certification. Learning grades pitch attack order within staves, not elapsed rhythm, tempo, dynamics or performance readiness. Chunk masks, note-level boundaries, guided acquisition, individual voices, spaced/gap-based review, general editable alternative drill strategies, automatic failed-repetition segmentation and Learning demonstrations remain deferred. Current hands modes and live staves should not be listed as absent. See [Learning](LEARNING.md) and [TODO](TODO.md).

## Still requires actual hardware/user validation

AP-470 connection/reconnection, all three physical pedals, native Linux Mint/Cinnamon touchscreen/OSK/display scaling, internal sostenuto effect, audio routing, real beginner Learning performances and multiple wall-clock hours under CPU/disk pressure. Browser touch emulation and accelerated timestamp tests do not substitute for these checks. No real hardware or real cloud-AI success is claimed by this documentation review.

Offline segmentation checks shorter silences (at least three seconds after held notes end) when independent phrases on either side confidently identify different pieces. Two consecutive phrase windows are required for a change without silence. Whole-take opening/ending evidence is checked separately so a later alignment cannot hide the introduction. Existing saved timelines need **Rebuild candidate timeline (undo available)** to use the revised algorithm.

## Passage measurements and Progress

Synchronized tempo/velocity/voice-dynamics/key-duration/pedal/release comparisons and shared-position take comparison are implemented. Dynamics are MIDI proxies; printed constant markings are descriptive and no acoustic p/f calibration is inferred. Explicit voice roles and chosen melody margins support target checks only under verified, unambiguous, healthy alignment. Roles that change within a score voice need finer annotation. CC88 and actual note-off data are decoded from received order, with rejection diagnostics; AP-470 physical stream and release calibration remain unverified. See [Comparison](MUSICAL_COMPARISON.md).

Progress includes measure evidence/time estimates, recurring discrepancy candidates, unassisted recall histories, separate technical objectives and manually attributed problem time. Recall review uses a fixed seven-day reminder; adaptive spaced repetition and a forgetting model are not implemented. Historical aggregate-only analyses need reanalysis. See [Progress](PROGRESS.md).


## Refactoring acceptance (2026-11-16)

The [structural refactor](REFACTORING.md) preserves public HTTP paths and the
existing database schema, source recordings and historical results. Current
eligibility checks distinguish reference/timeline changes from saved history.
Synthetic timing and memory measurements cover the 44-piece catalogue with 528
takes and 2,000-note comparisons; multi-hour offline analysis still materializes
notes. Browser JS heap samples do not establish GPU/canvas/process memory bounds.
The existing OSMD bundle-size warning remains. Physical devices, touchscreen,
wall-clock soak/power-loss and real-cloud acceptance remain open. Nine Learning
browser cases across three viewports require an unbundled reviewed scan and are
reported as skips; backend edition/hash and authoritative-capture cases use
synthetic fixtures. Authored CI has not yet run on GitHub.
