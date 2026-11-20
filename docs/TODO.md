# Future work and acceptance checklist

Reviewed against the working tree on **2026-11-19**. Unchecked items below are documented plans, incomplete extensions or unverified acceptance work, not scheduled commitments. See [Roadmap](ROADMAP.md) for available workflows and [the earlier documentation review](IMPLEMENTATION_REVIEW.md) for historical context.

## Multiplatform Stage 1 and future standalone Android app

- [x] Keep the musical engine and SQLite services shared. Inject device,
  rendering and durability contracts and compose the Linux implementation
  through its desktop runtime.
- [x] Retain preferred-device configuration and add generic input fallback,
  conservative device evidence and persistable user-confirmed profiles.
- [ ] Validate the Linux phase with real AP-470 USB reconnect, CC88 and release
  velocity, pedal commands, hardware playback and capture, long sessions and
  touchscreen interaction.

For the standalone Android phone port, see [Android port](ANDROID_PORT.md).

- [ ] Verify the portable Python packages for Android, including numerical
  libraries and native wheels, and select an embedded Python integration.
- [ ] Implement MIDI I/O, native MIDI parsing, USB permissions and attach/detach.
- [ ] Build foreground recording ownership and Android lifecycle/recovery,
  including offline recording across Activity loss and screen lock.
- [ ] Implement app-private storage, staged import/export, backups and restore.
- [ ] Integrate the Python engine with a compact React phone workspace.
- [ ] Produce signed installable APKs and validate AP-470 over direct USB-C/OTG,
  generic MIDI keyboards and offline capture/analysis on physical phones.

Defer tablet UI, two-page PDF and multi-panel tablet Learning, continuous
horizontally scrolling phone notation, precise original-score measure cropping,
Android microphone/audio enhancements and network/multi-device sync.

## Completed Score certification

- [x] Add independent, edition-bound MIDI read-through with live registration staves, inclusive measure ranges, a learned-range shortcut and review through a pause point.
- [x] Save measure-by-measure pitch comparisons, tentative score edit proposals and optional snapshots of Learning score corrections with the certification take.
- [x] Show hand-entered corrections in their full measure on both staves and support cycling through every individual pitch edit. Cross out the original pitch and show the correction as a red notehead.
- [ ] Verify the workflow on a physical piano and touchscreen, including a slow two-staff read-through and a pause inside a chord or measure.

## Completed Practice restart correction (2026-11-19)

- [x] Replace the rigid twelve-onset opening-signature gate with chord-supported phrase evidence and anchored boundary checks, including rolled chords and earlier abandoned attempts.
- [x] Compare plausible forward score passages before splitting written theme returns; keep independent repeated edge evidence from mislabelling a partial take's endpoint.
- [x] Cover exact retake timestamps, early/full preceding takes, bass-first/treble-first rolled attacks, written returns, capture preservation, undo history and inherited Keep protection with synthetic regressions.
- [x] Correct the reported latest saved timeline with a revision-checked undoable edit and fresh per-take analyses; verify original capture files and historical analyses remain unchanged.
- [ ] Extend real-player acceptance across other pieces, ornaments, severe opening mistakes and repeat routes; estimates and reference-quality gates remain explicit.

## Completed Analysis chart readability update (2026-11-19)

- [x] Increase whole-piece chart lane height and add multiple aligned y-axis values/gridlines, with explicit BPM labels for local tempo and readable numeric scales for other measurements.
- [ ] Validate chart readability with physical touchscreen use; automated layout checks do not establish that acceptance.

## Completed review measure retries (2026-11-19)

- [x] Default reviews to a browser-local mistake cue and retry of the affected measure after key release; keep the ordinary Learning auto-restart preference separate.
- [x] Make review retake controls rewind to the affected measure and record continuously through the original end, without a separate Finish/Start step at the repaired bar; retain explicit whole-review restart and interrupted MIDI.
- [x] Keep retry/tail assessments separate from full-range build-backward passes, with explicit manual acceptance of a finished review sequence; preserve saved learning position, streaks, note rules and hand selection.
- [ ] Verify notification audibility, retry timing and measure location with the physical piano and speakers/headphones; automated fixtures do not establish device acceptance.

## Completed whole-piece overview (2026-11-18)

- [x] Add a full-width Analysis overview independent of the 24-group detail pages, with whole/half/quarter-piece scales, range navigation, selectable tempo/dynamics/duration/pedal/release lanes, measure means and ranges, and measure selection for detailed review.
- [ ] Validate overview readability and measure selection with physical touchscreen use and personal long performances; automated synthetic browser checks do not establish that acceptance.

## Completed startup update (2026-11-18)

- [x] Add executable `start.sh` in the project root, forwarding options to the existing launcher and resolving the project directory when started from elsewhere.

## Completed interface and following updates (2026-11-17)

- [x] Pre-render Learning PDF pages into the bounded cache during hidden recall so peeking and returning to visible study reuse warm pages without exposing the score.

- [x] Open Sessions with Audio cleanup collapsed, including after saving; retain explicit access to cleanup.
- [x] Automatically expand recognition on each entry to Practice Score fullscreen, with manual collapse available during the visit.
- [x] Label the panel **Live recognition** and hold automatic page movement when a backward opening match also fits a nearby returning theme. Distinguishing later notes can restore following; a genuine distinct restart still reacquires the opening.
- [ ] Validate recurring-theme holds and genuine restarts with physical piano performances; synthetic tests do not establish accuracy for every return, ornament or edition.

## Completed Practice and documentation updates (2026-11-15)

- [x] Add synchronized passage measurements and take comparison, explicit voice-role dynamics targets, ordered CC88 reconstruction and separate release-velocity evidence. See [Comparison](MUSICAL_COMPARISON.md).
- [x] Add measure history, recurring discrepancy review, recall retention evidence, separate technical objectives and attributed problem time. See [Progress](PROGRESS.md).
- [x] Add opt-in automatic opening of stable recognized pieces, distinctive short-attempt recognition, conservative mid-piece retry splits and repeated-location uncertainty.
- [ ] Validate the AP-470's actual CC88/note ordering, release range/calibration and voice-balance targets with controlled physical playing; synthetic regression tests do not establish device calibration.

- [x] Open Practice scores at the piece’s first configured PDF page instead of restoring the last viewed page; preserve saved zoom, crop and one/two-page preferences and Learning navigation. See [Library](LIBRARY.md).
- [x] Require updates to README, this checklist and relevant documentation for every project change in [agent instructions](../AGENTS.md).
- [x] Require automatic local commits for completed agent changes in [agent instructions](../AGENTS.md).

## Learning: additional content and authoring

### Next pieces to implement

User-requested priority order, recorded **2026-11-14**:

1. [ ] Mazurka, Op. 24 No. 2 in C major.
2. [ ] “Minute” Waltz, Op. 64 No. 1 in D-flat major.
3. [ ] Waltz No. 14 in E minor, Op. posth.

These are queued for implementation, not available Learning lessons. Each needs
the exact-edition musical-content and lesson-plan reviews described in
[Adding another piece](LEARNING.md#adding-another-piece), plus its Library
**Open in Learning** button.

Additional future Learning implementation, requested **2026-11-16** (the priority
order above is unchanged):

- [ ] Chopin: Nocturne in C minor, Op. 48 No. 1. Complete the exact-edition transcription audit, lesson-plan review and Learning integration checks before enabling automatic assessment.

### Other content and authoring work

- [x] Review and change file names for pieces in Learning, updating affected references while preserving piece IDs and saved progress. Implemented in `b8c0edd`; see [Learning file conventions](LEARNING.md).
- [x] Complete the Heroic Op. 53 Paderewski pitch/attack counterpart and occurrence-level model review: 181 measures, required graces, local ornament policies, automatic checks and downloadable attack study. See [Heroic review](heroic_polonaise_op53_learning.md). Independent musician and real-player acceptance remain outstanding.
- [x] Add Nocturne Op. 15 No. 1 with separate exact-edition musical-content and lesson-plan review, Library selection and authoritative-capture assessment. See [Nocturne review](nocturne_op15_no1_learning.md).
- [ ] Add further lessons beyond the three registered pieces, with separate musical-content and lesson-plan review for each exact edition; the requested queue above remains open.
- [ ] Provide a lesson authoring/review interface. Editing the existing lesson's routine/chunks is already available; authoring another piece is not.
- [ ] Generate explicitly provisional algorithmic lesson/chunk proposals, with trusted advancement withheld until edition review.

## Learning: display and acquisition

- [ ] Show only the assigned region of the original PDF, using chunk masks/crops; provide faithful digital excerpts and overlays on the scan. Full-page reading and passage-scoped live comparison staves already exist.
- [ ] Allow within-measure/note-level chunk boundaries and overlapping boundary drills. Current editable chunks use whole measures within the six reviewed sections.
- [ ] Add dedicated guided note-by-note acquisition with prompts, separate from complete-passage recall tests.
- [ ] Select individual voices within a staff. Right-hand, left-hand and both-hands modes already exist.
- [ ] Add harmonic annotations, fingering notes and silent-study tasks beyond the current textual chunk guidance.
- [ ] Offer an optional MIDI demonstration, excluded from evaluated input. Physical-piano playback in Practice is already available; Learning demonstration is not.

## Learning: practice strategies and feedback

- [x] Aeolian Harp: expanding backward review of the learned prefix, last 2/4/6 chunks through the full learned span, without changing learning progress.
- [ ] Extend expanding backward review to other Learning pieces, respecting their section order and connection strategies.

- [ ] Add random-start scheduling and generally editable connection strategies. Heroic already uses independent sections, backward coda acquisition and explicit transition drills.
- [ ] Add scheduled delayed-retention assignments and adaptive spaced review. Progress now shows unassisted recall-test history and a fixed seven-day review reminder; it does not schedule tests.
- [ ] Suggest review after time away and offer configurable gap-based review startup. Startup already selects learned-prefix review after a backend restart when learned chunks exist, without starting capture; there is no elapsed-gap scheduler or opt-in setting for that behavior.
- [ ] Suggest adaptive chunk splits and workloads rather than relying on manual chunk editing.
- [ ] Automatically segment failed repetitions. Manual Finish, Restart take and middle-pedal repeat already exist.
- [ ] Add richer substitution explanations and evidence playback directly from each Learning discrepancy. Live alignment, final error lists, local reference corrections and reasoned personal note rules already exist.
- [ ] Add optional elementary rhythmic-order checks. Current Learning evaluates pitch attack order within staves; it does not grade elapsed rhythm, tempo, duration, dynamics or pedal.

Detailed scope and lesson prerequisites: [LEARNING](LEARNING.md), [Aeolian review](aeolian_harp_etude_op25_no1_learning.md), [Heroic plan](heroic_polonaise_op53_learning.md).

## Repertoire beyond Chopin

Requested **2026-11-16** for future introduction in **Practice only, or both
Practice and Learning**, with the scope decided per work:

- [ ] J. S. Bach: *The Well-Tempered Clavier*.
- [ ] Sergei Rachmaninoff: Prelude in G minor, Op. 23 No. 5.
- [ ] Franz Liszt: *Liebestraum* No. 3 in A-flat major.
- [ ] Franz Liszt: “Un Sospiro” Étude in D-flat major, S. 144 No. 3.
- [ ] Franz Liszt: “La Campanella” Étude in G-sharp minor, S. 141 No. 3.
- [ ] Franz Liszt: Hungarian Rhapsody No. 2 in C-sharp minor, S. 244 No. 2.
- [ ] Ludwig van Beethoven: “Moonlight” Sonata — all three movements.

These are future repertoire tasks, not implemented catalogue entries or lessons.
Preserve score/reference source, licence and edition provenance. Any Learning
addition requires the full transcription audit and integration checks described
in [Adding another piece](LEARNING.md#adding-another-piece). The ordered Chopin
Learning queue above remains unchanged.

## Scores, editions and comparison

- [ ] Integrate a reviewed local OMR/scan-to-MusicXML workflow, retaining sources, corrections and unresolved notation. Importing externally prepared MusicXML already works.
- [ ] Extend the Nocturne Op. 9 No. 1 Paderewski pilot beyond pickup/measures 1–4 and review the remaining work. Its standalone selectable demo is not live app integration.
- [ ] Support faithful source-notation comparison/annotation, including exceptional tuplets, voices and expressive/editorial detail. Current comparison notation regenerates voices/durations and is not a facsimile edition.
- [ ] Map page/system/measure/note coordinates for highlights on the original scan; provide finer than integer-measure page anchors where a measure crosses a page.
- [ ] Expand catalogue coverage beyond the 44-work repertoire, complete volume/supplement indexing and provide a full bibliographic/edition editor. Preferred-edition text and reference-edition text are already editable.
- [ ] Consider confirmed per-piece/per-measure personal variants in general Practice comparison. Conservative adaptation labels exist; Learning has its own occurrence-specific personal rules, but Practice does not create an approved personal edition.

Sources: [Library](LIBRARY.md), [Comparison](MUSICAL_COMPARISON.md), [Nocturne pilot](NOCTURNE_EDITION_PILOT.md), [Following readiness](AUTO_PAGE_TURNING.md).

## Recognition, following and analysis

- [x] Rank complete audio takes by combined note, within-measure timing and written-dynamics evidence, adding available clipping/voicing evidence. Preserve incomplete comparisons and shortlist ties for listening rather than choosing newest audio; expose component scores. See [audio ranking](AUDIO_QUALITY_RANKING.md).
- [x] Recover missing written dynamic levels for Op. 9 Nos. 1–2 and Op. 72 No. 1 from fingerprinted native sources without rewriting installed references or promoting their quality.
- [ ] Calibrate musical-evidence ranking against pianist listening choices and real AP-470 velocity response; extend hairpin, articulation and pedal-intent evidence before treating those as graded criteria.
- [x] Recognize repeated full takes and later opening returns, assess each take independently, rank provisional candidates without capped-score ties, broaden error-tolerant retrieval and discard stale live restart context. See [recognition findings](RECOGNITION.md).
- [x] Rebuild complete source-derived digital scores and MIDI for Nocturnes Op. 9 Nos. 1–2 and Op. 72 No. 1, with both-staff inventories, tie handling and explicit first-edition/source-warning provenance. These remain provisional; full Paderewski pitch/notation audits and Learning integrations are not supplied by this export.
- [ ] Evaluate/integrate a specialist online follower such as Matchmaker against the existing custom baseline, with repeat/restart traversal and multiple-position hypotheses.
- [ ] Extend restart and repeated-theme handling to fuzzy multi-location tracking through ornaments, long attempts and explicit repeat structures. Unique exact six-chord contexts now support short mid-piece retries; repeated phrase locations remain explicitly uncertain. This is not a general repeat/ornament evaluator.
- [ ] Anchor following to the latest aligned note/beat rather than only the end of a matched reference span; use finer score positions for page boundaries.
- [ ] Benchmark large reference libraries and bound multi-hour offline-analysis memory. Capture and the live input queue are bounded; offline note extraction currently materializes a session's notes.

Sources: [Limitations](LIMITATIONS.md), [Following readiness](AUTO_PAGE_TURNING.md). Recognition similarity and technical pitch F1 already exist; neither establishes calibrated musical accuracy or interpretation quality.

## Audio and report integrations

- [ ] Implement sfizz and Pianoteq rendering adapters with supported vendor/version command contracts. Executable detection alone is implemented.
- [ ] Add arbitrary local LLM/provider adapters. Existing local reports are deterministic; OpenAI is the implemented optional cloud provider.

Sources: [Limitations](LIMITATIONS.md), [Architecture](ARCHITECTURE.md). FluidSynth rendering, microphone recording, physical-piano playback/audio-interface capture, WAV attachment and local/OpenAI report paths already exist.

## Content and musical review still needed

These are missing or unresolved assets/reviews from the recorded acquisition inventory, not absent import software. Recheck the target installation before acquiring or changing anything.

- [ ] Find suitable symbolic references for Waltz B.46 and Sostenuto B.133.
- [ ] Fill the exact requested printed-score gaps: Schott Raindrop, B.150 and B.133.
- [x] Repair/review the later part-numbering mismatch in Étude Op. 10 No. 12 through a separate scan-reviewed 84-measure counterpart and reference-specific page map; preserve the acquired original. See [counterpart audit](LIBRARY_COUNTERPART_AUDIT.md).
- [ ] Repair/review the conflicting references and eleven withheld page boundaries for Ballade Op. 23, Étude Op. 25 No. 10, Nocturne Op. 62 No. 1 and Waltzes Op. 69 No. 2 / Op. 70 No. 3. Recheck B.46's printed-only links when importing its reference. The Revolutionary Étude repair above does not resolve these other works.
- [x] Finish the user-narrowed nine-piece measured Practice batch: the four started audits plus Nocturne B.49, Polonaises Op.40 Nos.1–2, Waltz Op.64 No.2 and Revolutionary Étude Op.10 No.12. Every measure/both staves checked against pinned Paderewski scans; additive installation and edition-aware following completed. See [piece status and review limits](LIBRARY_COUNTERPART_AUDIT.md). The other 31 original candidates are deferred by the user; B.46/B.133 remain excluded and Op.28 No.15/B.150 deferred. Real-performance threshold calibration remains separate.
- [x] Preserve written grace attacks and grace chords during MusicXML ingestion; retain ornament metadata and withhold strict technical levels when ornament realization requires review.
- [x] Add additive, fingerprinted installation of completed scan audits and distinguish verified/provisional reference counts on Library cards.

Sources: [Sources](SOURCES.md), [Reviewed page links](REVIEWED_PAGE_LINKS.md).

## Acceptance of implemented features

- [ ] Validate AP-470 connection/reconnection, all three physical pedals and actual repertoire following/page maps.
- [ ] Validate Linux Mint/Cinnamon touchscreen, on-screen keyboard, scaling and fullscreen on the real display, including Full HD.
- [ ] Validate physical-piano MIDI playback, USB-flash recording, microphone/audio-interface capture, cancellation, levels and routing.
- [ ] Validate real beginner Learning performances, repeated figures, rolled chords, hand spans, selected-hand behavior and error localization; seek independent musical review.
- [ ] Run multi-hour wall-clock capture/CPU/disk-pressure checks and actual interruption/backup-restore acceptance. Accelerated timestamps do not establish a soak result.
- [ ] Validate the optional OpenAI adapter with an explicitly authorized real request; existing mocked contracts do not prove real-cloud success.

Use [ACCEPTANCE](ACCEPTANCE.md) for manual procedures. Do not mark these complete from source inspection or simulated tests.

## Already implemented: do not keep on the future list

- [x] 44-work repertoire, PDF import/viewer, explicit acquisition scripts, MusicXML/MXL ingestion, reference editing/quality labels, page calibration and reusable labelled MIDI references.
- [x] Candidate organisation, reversible timeline, grouped attempts, completeness labels, some aborted-opening splits, per-piece Saved sessions and progress history.
- [x] Strict pitch proxy and eligible technical levels/production suggestions, local tempo, conservative musical comparison, comparison PDF/MusicXML/JSON and session bundles.
- [x] Optional microphone capture, audio-only cleanup at shutdown, manual Keep/Delete audio, separate Delete session and MIDI-guided inaudible-microphone exclusion after analysis.
- [x] Requested FluidSynth audio, physical-piano playback/optional interface capture, WAV attachment and local/explicit OpenAI reports.
- [x] Experimental live recognition/estimated following, provisional opt-in, page-turn blockers, manual override, configurable pedal controller, PDF caching and distinct app/score fullscreen.
- [x] Aeolian Learning chunks, full-passage pitch evaluation, automatic finish/continuation, saved progress, self-assessment, restart/pedal repeat, learned-prefix/selected-chunk review and startup review selection.
- [x] Per-hand Learning progress, live/hidden-recall staves, reference spelling/key signature, local reference corrections, personal note rules and daily Learning session groups.
- [x] Use completed both-hands Learning stages as a minimum for each separate hand, including existing profiles; preserve higher separate-hand progress and mode-specific repetition streaks/history.
- [x] Keep Peek at score visible across immediate Learning retakes, including pedal/automatic retries, while retaining assisted status and resetting visibility on fresh attempts or assignment changes.
- [x] Browser score-opening voice commands and Learning reason dictation.

## Architecture refactoring (2026-11-16)

- [x] Inventory the current source/imports/API entry points and establish a dedicated branch.
- [x] Complete domain, router and workspace extractions with compatibility checks.
- [x] Record synthetic performance measurements and add isolated browser validation and incremental CI.

See [Refactoring](REFACTORING.md) for current evidence and remaining work.
- [x] Consolidate analysis freshness across assessment, progress and audio review;
  cover reference changes, source status, discarded takes and whole-recording deletion.
- [x] Extract pure Learning and Practice domains with compatibility imports;
  retain distinct matching rules and controller safety boundaries.
- [x] Extract scoped HTTP routers without changing OpenAPI; centralize lookups/uploads.
- [x] Consolidate catalogue initialization and test fresh/schema-001/edited databases.
- [x] Fix failed timeline writes with tested atomic rollback of history and Keep flags.

- [x] Extract workspace/dialog/Learning/review components, shared response types,
  score gesture/fullscreen/following hooks and ordered styles without a redesign.
- [x] Profile 528 synthetic takes and 2,000-note comparisons; reduce duplicate
  progress reads, timing-neighbor work and response copying.
- [ ] Verify the authored GitHub Actions workflow in a hosted run after publication.
- [x] Add `.github/workflows/checks.yml` with backend Ruff/tests, frontend
  formatting/types/build and isolated browser jobs; hosted execution remains open above.

- [x] Allow explicit manual correctness for finished build-backward review takes, including score peeks, while preserving assistance and original pitch evidence.

- [x] Add default-on, browser-persisted automatic Learning page turns during active score peeks, using reviewed lesson alignment and preserving manual navigation.
