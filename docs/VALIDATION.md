# Validation history

## 2026-11-20 — Score certification discrepancy navigation

- The production build and all **47** frontend unit tests passed. The **6**
  targeted certification browser checks passed across all three headless
  viewports, including 1920×1080. They cover forward and backward wraparound,
  multiple corrections in one measure, the measure selector, red engraving
  and the saved MIDI review workflow.
- Full-measure correction rendering passed the same **6** browser checks,
  the production build, **47** frontend unit tests and **33** targeted
  backend tests. The Aeolian Harp measures containing hand-entered edits
  each supplied all 48 written notes across both staves.
- The correction glyphs passed the production build, **49** frontend unit
  tests and **6** browser checks. MusicXML regression checks cover the red
  cross for the original and the red notehead for both upward and downward
  pitch edits.
- Grouping edits by measure passed the production build, **49** frontend
  unit tests and **6** browser checks. The browser regression verifies all
  correction marks appear together in a measure and navigation moves by
  changed measures.

## 2026-11-19 — Score certification

- Backend tests passed **396**, with two dependency deprecation warnings. They
  cover full written-attack alignment of all three Learning pieces, reordered
  chord notes, omitted passages, isolated discrepancy proposals, capture
  isolation, correction snapshots, partial chords, persisted reviews and
  interrupted MIDI.
- Frontend unit tests passed **47**. The production build passed with the Vite
  large-chunk warning. Ruff, targeted Prettier and Git diff checks passed.
- The isolated Learning/fullscreen suite passed **48** checks across three
  headless touch viewports including 1920×1080. **9** reviewed-PDF fixture
  checks were skipped. The new certification browser test used a synthetic
  scan and deterministic MIDI responses to check both entry points, measure
  selection, live staves, pause and review, red discrepancy engraving and a
  proposed replacement. Backend integration tests used the real Recorder and
  synthetic MIDI events. The final build also passed **30** targeted browser
  checks across those same viewport sizes for certification, Practice,
  Recordings Library and session groups.
- Physical piano and touchscreen acceptance remain open.

## 2026-11-19 — Linux platform refactor

See the [platform audit](PLATFORM_AUDIT.md), [resulting architecture](ARCHITECTURE.md)
and [standalone phone port plan](ANDROID_PORT.md).

- The adapter contracts cover legacy preferred names, generic port selection,
  connection failure/reconnect, stale callbacks, monotonic timestamps with ties,
  CC88, release velocities, pedals, SysEx and system-message round trips, output
  and cancellation cleanup, persisted capability profiles, unavailable audio,
  queue overflow and storage faults. Synthetic takes go through shared Practice
  recognition and analysis and through authoritative Learning evaluation and
  progression. A fresh Python process blocks imports of Linux adapters, RtMidi
  and the HTTP stack and starts the shared Studio against a temporary store.
- Backend `.venv/bin/python -m pytest -q` passed **387** tests, with two
  existing dependency deprecation warnings. The installed FluidSynth and
  a synthetic MIDI take exercised real software rendering and cancellation.
- The OpenAPI fixture pins the existing endpoints plus the two capability
  operations. Migrations 001–006 and the production React source match the
  baseline. Linux startup, shutdown and restart were exercised with the real
  loopback server, a temporary data/state directory and hardware disabled.
- Frontend `pnpm test` passed all **47** unit tests. `pnpm build` passed with
  the Vite large-chunk warning. Ruff, targeted Prettier and Git diff checks
  passed.
- Isolated Chrome Playwright covered all three touch viewports, including
  1920×1080. Sessions passed **30** tests. Learning/fullscreen passed **45**
  with **9** requiring an unavailable local reviewed PDF.
- The initial general run had **133 passed**, **9 PDF-dependent skips** and
  **2 fullscreen fixture failures**. The fixture had requested real
  microphone capture in a hardware-disabled environment. After explicitly
  choosing MIDI-only recording, the general rerun passed **12** checks across
  all viewports, including the failed fullscreen cases, Practice capture,
  browser closure and byte-preserving MIDI import.
- Physical AP-470 and generic USB MIDI, microphone and stereo piano capture,
  touchscreen and long-duration acceptance remain open. Test services used
  fresh temporary stores and headless browser profiles.

## 2026-11-17 — musical-evidence audio shortlist

The final backend suite passed **341 tests**, with two existing Lark deprecation
warnings. Frontend unit checks passed **44 tests**; TypeScript/production build
passed with the existing bundle-size warning. The final isolated headless
Sessions suite passed **30 cases** across 1920×1080, 1280×900 and 820×1180,
including composite/component score display, manual Keep/remove controls and
audio-only deletion preserving MIDI. The initial new browser assertion checked
a kept score while the list still showed flagged audio; selecting Kept audio
before asserting corrected the test, and the full suite was rerun successfully.

Synthetic regressions cover older high-quality takes beating newer takes, note
accuracy losing to stronger timing/dynamics evidence, smooth local/inter-measure
rubato, missing/stale/partial/capture-fault evidence, tied scores, incompatible
reference identities, manual protections, headphone exclusion, native dynamics,
and pickup-aware fermata/tempo-change exclusions. Source dynamics annotations are
fingerprinted and retain CC BY 4.0 attribution. Module lint, package-data paths,
documentation links and whitespace checks passed.

Read-only diagnosis found stored Nocturne analyses with pitch/timing/velocity
evidence but no written dynamic labels. The new read-time scorer successfully
produced comparable component scores for the complete Op. 72 takes using the
native-source supplement; the partial run remained unrankable. This did not save
scores, change personal audio choices, rebuild timelines, delete recordings or
modify historical analyses. Test services owned temporary data/state and port
8768 with hardware disabled; no production service or user browser was touched.

The ranking is an explicitly documented heuristic, not a calibrated overall
musical-quality grade. Listening calibration, physical AP-470 velocity response,
complex rubato, hairpin shaping, articulation, pedal intention and acoustic tone
remain unverified or unassessed. See [criteria and limitations](AUDIO_QUALITY_RANKING.md).

## 2026-11-17 — repeated takes, recognition and Nocturne exports

The final backend suite passed **330 tests**, with two existing Lark deprecation
warnings. Synthetic regressions cover full/partial/full opening returns without
long pauses, independent completeness before a restart, written theme returns,
provisional-score ranking ties, damaged fingerprints beyond the old shortlist,
ornamented long-span alignment, live rewind/tempo-anchor retirement and native
counterpart tie/export integrity. Focused recognition/analysis checks passed
before the complete run. Module lint, local documentation links and whitespace
checks passed.

Isolated headless browsers passed **24 Practice/following checks** and **30
Sessions/analysis/cleanup checks**, across 1920×1080, 1280×900 and 820×1180.
Each suite owned its temporary data/state and port (8766 or 8768), with hardware
disabled and no existing-server reuse. No user browser was attached or changed.

User-requested, read-only diagnostics of the reported saved activity confirmed
the former pooled partial result and the revised complete/partial/complete
interpretation. This was diagnosis of existing evidence, not a test fixture:
no private recording/reference data was copied into tests or Git, and no personal
database rows, timelines, historical analyses, MIDI or audio were changed.

The three pinned licensed native Nocturne sources rebuilt successfully with
optional Verovio 6.4.1 into ignored local outputs. All **13 generated SVG pages**
were rendered in a separate headless browser and visually inspected. Every
measure contained both staves; exported attack inventories agreed with MIDI
note-on counts (1,727 / 1,246 / 1,091). Native source problem markers and renderer
mixed-beam/crowded-system warnings remain disclosed. This is structural and
export validation, **not a complete Paderewski pitch/notation audit**; no
reference promotion, new Learning lesson or silent source replacement occurred.

Physical piano/microphone/touchscreen acceptance and broader real-performance
recognition calibration remain unverified. See [findings](RECOGNITION.md).

## 2026-11-17 — preserve score peek during retakes

Immediate button, pedal and automatic retakes retain the open score and assisted
status. Finishing/pausing, a fresh start or changing the assignment/hand resets
peek visibility. Backend coverage checks that an assisted hidden retake cannot
advance progress and a subsequent fresh attempt starts unassisted. A synthetic
blank-PDF browser regression checks two consecutive retakes and finish visibility
without requiring a private source score or changing reference-quality gates.

Validation: **321 backend tests passed** (two existing Lark deprecation warnings),
**44 frontend tests passed**, and TypeScript/production build passed (existing
bundle-size warning). The isolated headless Learning suite passed **30 cases**
at 1920×1080, 1280×900 and 820×1180; **9 reviewed-PDF cases were skipped** because
the score was not supplied. Backend module lint and whitespace checks passed.
Suites used temporary data/state and disabled hardware; the browser server used
port 8767. No running-app restart, personal-data edit or physical-device test.

## 2026-11-17 — both-hands Learning progress inheritance

Completed both-hands stages now establish a minimum for right-hand and left-hand
progress, including existing saved profiles. Higher separate-hand positions,
mode-specific streaks and original take histories are preserved. Coverage includes
automatic pitch passes, self-assessment, hand switching, reload, learned-chunk
review availability and reference-correction invalidation.

Final backend suite: **321 passed**, with two existing Lark deprecation warnings.
Learning browser suite: **27 passed, 9 skipped**, across 1920×1080, 1280×900 and
820×1180. The skipped cases require the reviewed PDF, which was not supplied to
the isolated test library. Browser checks used a separate headless process,
temporary data/state, port 8767 and disabled hardware. The sandbox stalled in
TestClient startup, so completed suites ran outside that restriction; the bundled
Node runtime was added to PATH. Backend module lint, Python compilation and
whitespace checks passed. Linting the touched test files also reported six
pre-existing unused-import/local warnings outside the changed lines.

No running application restart, personal-data modification or physical
piano/microphone/touchscreen validation was performed.

Entries below describe the checkpoints when they were written, starting on
2026-10-30. Test counts, layouts, policies and library state in an earlier entry
are historical; later code may supersede them. They are not a report that the
current working tree has passed all those checks.

The 2026-11-12 [documentation review](IMPLEMENTATION_REVIEW.md) checked current
source, test definitions and bundled manifests without running application tests,
opening a browser, using hardware or contacting cloud services. In current code:

- Audio shortlisting removes flagged partial/surplus audio at shutdown, including
  flagged audio from capture-error sessions; uncertain takes and Keep flags are
  protected. MIDI-guided inaudible-piano microphone exclusion is a separate
  after-analysis deletion path. [Current policy](MICROPHONE_RECORDING.md)
- Learning uses a score-left adjustable split, reference-aligned played-only
  staves during hidden recall, per-hand progression and startup learned-prefix
  review selection. [Current workflow](LEARNING.md)
- The Learning Playwright configuration includes 1920×1080, 1280×900 and
  820×1180; the general and Sessions configurations currently define the latter
  two sizes. A configuration or test definition is not evidence of an executed
  result. Project instructions require Full HD for layout/fullscreen checks.

## Initial checkpoint — 30 October 2026

## Executed

- Python 3.12 virtual environment installed with FastAPI, Mido/python-rtmidi, pypdf, pytest and httpx.
- `python -m pytest -q`: 9 passed before final reliability refinements. Cases: overlapping same-pitch events, zero-velocity note-off, continuous CC64/CC66, durable journal ordering, stop cleanup, 10-hour simulated timestamp, torn-tail recovery, CSV tempo changes, duplicate recording guards, import byte preservation, malformed uploads, safe generated filenames, PDF page validation, foreign origin/host rejection, dropout markers, default-disabled CC66, double press, bounded queue overflow.
- Private `1.mid`: type 0, one track, PPQ 960; 321.029 seconds; 1,760 note-on, 1,760 note-off and 4,348 controller messages. The private fixture test imports through HTTP and asserts byte-for-byte original download equality. It is skipped when the private file is absent and never committed.
- Frontend TypeScript compilation and Vite production build succeeded.
- Vitest: 3 tests passed (elapsed-time formatting, backend error propagation and false settings serialisation).

Final touch browser and regression results are recorded below. Test fixtures are generated original blank PDFs and synthetic MIDI; no copyrighted score material is bundled.

## Environment notes

The ordinary sandbox prevents the ASGI TestClient event-loop wake-up and local browser/server sockets. Python API tests were rerun outside that sandbox and completed in under a second; this was an environment restriction, not a passing result inferred from stalled tests. Dependencies were installed with a temporary writable cache. Python 3.13 required unavailable ALSA build headers; system Python 3.12 supplied a prebuilt RtMidi wheel.

## Not validated at the initial checkpoint

AP-470 USB connection, physical pedals, actual Linux Mint/Cinnamon touch hardware, acoustic sound, multiple wall-clock hours of recording, power-loss filesystem behaviour, Partitura/Matchmaker, rendering and AI. The ten-hour timestamp test is not a ten-hour soak test. Use the manual acceptance checklist before relying on the application for irreplaceable sessions.

## Final verified results

- Expanded Python suite: **13 passed** in 2.53 s, including 20,000 events captured while status is polled concurrently, future-schema protection simulation through the authoritative recorder, valid SysEx encoding and tagged system-realtime preservation. One upstream Starlette/httpx deprecation warning remains.
- Touch browser suite: **8 passed** in 13.8 s, no skipped private-fixture tests, using touch-enabled Chromium at 1280×900 / 1× and 820×1180 / 1.5×. Recording survived tab navigation and reload; stop confirmation/cancel, library editing/filtering, imported-original byte equality, PDF import/ranges, swipe, two-finger pinch, panning, fit zoom, fullscreen and persisted page/zoom were exercised.
- A stricter fit-zoom assertion caught Chromium suppressing compatibility clicks after pinch. Touch buttons now activate on pointer-up and suppress the duplicate click; rerun passed.
- User desktop shortcut installed to `~/.local/share/applications/chopin-studio.desktop`; launch script started the loopback backend successfully. The app was opened in a Codex browser panel (queued by the app UI).
- Private `1.mid` imported into the normal XDG application data, preserving its source file in the project and excluding both from Git. Export byte equality confirmed. SHA-256: `d04817105b1233fe885dc27649f26b19a5234d491997349ba1c316a95a0cdfd4`.

Browser tests use a separate temporary data directory and port 8766; the ordinary application uses port 8765. Generated blank-PDF fixtures are test navigation material, not a supplied musical score. A display reflow observer resizes PDF canvases when entering fullscreen or hiding controls.

# Continued milestones

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

## Following and tempo — 2026-10-31

Read-only inspection of the ordinary library found all symbolic references provisional and page maps containing only opening-page links. Neither condition permits the former verified-only follower to reach later PDF pages. The UI now explains blocked turns, offers explicit provisional navigation without changing assessment/reference quality, and calibrates each PDF page in the practice view. Recognition retains recent onset groups rather than only 64 individual notes, and rejects page requests from alignments that omit the latest input.

New live and saved analysis results include bass-first MIDI tempo inference in quarter notes/minute, with matched-score timing as a fallback. At least four anchors and two usable estimates are required. Median slopes over up to four preceding anchors reduce ornament/rolled-chord spikes; intervals longer than eight seconds are excluded. The local curve retains tempo changes. Historical analyses remain intact; rerun analysis to obtain the new summary for an old take.

Validation: the Python suite passed 50 tests, followed by the added saved-analysis integration check (seven focused following/tempo tests passed). TypeScript and the production Vite build succeeded; frontend unit tests passed 10 tests. Four touch Chrome tests passed across 1280×900 and 820×1180 layouts: actual PDF-page calibration, provisional reference import, CSV/MIDI playback through the real live consumer, bass tempo display at 120 BPM and page 1→2→3 navigation, plus the existing gesture/fullscreen/cache/manual-cooldown regression. Synthetic blank PDFs and original note fixtures were used. Calibration and live-following screenshots were inspected. These checks do not establish AP-470 hardware acceptance, accuracy on real Chopin performances, acoustic-WAV transcription, or reliable automatic pagination of scanned scores.

The final compact-touch regression also passed after styling the calibration controls and explicitly pausing automatic turns while calibration is open; closing calibration applies the pending page request. The seven focused Python tests and final TypeScript/production build passed after restricting bass matching to the recognised score span.

## PDF rendering and overlapping spreads — 2026-11-03

The viewer now serializes PDF.js rendering into detached canvases and commits completed spreads together. It retains the previous displayed spread while loading, prepares up to four pages beyond the visible spread plus two previous pages, and reuses overlapping pages. Cached RGBA bitmap storage is limited to 64 MiB with a four-megapixel limit per page; very large pages therefore reduce prefetch depth or raster density. This budget excludes the displayed canvases, PDF document bytes, decoded source images and browser/GPU overhead. PDF page drawing resources are cleaned after rendering, and document-cache eviction skips volumes retained by a viewer. Resize redraws are debounced, cancelled generations cannot commit stale pages, and foreground failures expose a retry button. Returning from the symbolic preview also redraws the PDF.

Two-page next/previous navigation advances one page, and automatic page requests put the detected page on the left. Ten-second manual navigation suppression and calibration suppression remain in place. See [the automatic-following readiness review](AUTO_PAGE_TURNING.md) for the read-only library audit and preparation steps.

Validation: 16 frontend unit tests passed (including cache eviction/pinning, four-page prefetch, overlapping-spread reuse, cancellation, atomic spread readiness, retry and raster memory limits); seven focused Python following/tempo tests passed. TypeScript and the production Vite build succeeded; the existing large MusicXML-renderer bundle advisory remains. Six touch Chrome browser checks passed across both layouts, covering actual coloured PDF pixels on both pages, single-page progression in two-page view, rapid navigation, resize, end-of-piece behavior, gesture/fullscreen/document-cache/manual-cooldown regressions, page calibration, and simulated MIDI requests moving the detected page to the left. A screenshot of the final-page state was inspected. An initial restricted run could not reach its local test server; its cleanup collided with one trace in the first unrestricted run. The clean six-test rerun used its own output directory. These fixtures do not prove that the reported freezes on the user's actual scanned scores have been eliminated, nor establish live-piano following accuracy.

After adding the guard that disables page-map saving until the requested spread is actually displayed, both calibration/following browser cases passed again (30.4 seconds). The final production build, TypeScript check and whitespace check passed.

## Reviewed page links — 2026-11-03

Visually inspected 205 rendered pages across the 41 indexed works. Read 204 musical page boundaries (one blank page excluded), translated printed/XML measure labels to the currently stored ordinal bar numbers, and applied 152 new links plus one corrected seed link. The library has 193 links; 36 works have complete maps and five have 11 explicitly withheld boundaries because of reference numbering/form conflicts. Corrected Op.26 No.2 to PDF 17-27, Op.40 No.1 to PDF 28-33 / printed 24, and Fantaisie-Impromptu to PDF 33-41. Exact PDF/reference/stored-note fingerprints guard application; custom calibration is preserved. Transactional application created an affected-data backup before changes. A read through the live SQLite WAL verified all persisted links/ranges and a repeat dry run proposed zero changes. Five new importer/data tests plus seven following/tempo tests passed; Python compilation and whitespace checks passed. See [reviewed links and unresolved references](REVIEWED_PAGE_LINKS.md). No reference notes, quality, live settings, personal notes or recordings were changed.

PDF cache follow-up: background preparation now includes two preceding pages, including when opening a saved position or jumping into a piece. Backward preparation respects the piece start. Forward pages retain priority and the existing bitmap memory limit remains in force.

## 2026-11-10 — audio cleanup, estimated following and piece boundaries

Automatic audio cleanup now keeps the two-take shortlist and explicit keep flags, only at application shutdown after organisation finishes. The initial two-minute timer was removed at the user’s request; expired deadlines from that policy cannot trigger deletion while the app is open. Uncertain/unidentified takes, capture-error sessions and overlapping intervals are excluded from automatic deletion. Keep flags can protect partial takes without certifying completeness and follow overlapping intervals across rebuild/edit/undo. MIDI and session history remain intact.

Estimated following uses a confident matched score-time anchor and local quarter-note tempo for up to 30 seconds/eight measures, pausing after three seconds without notes. Provisional navigation remains opt-in and its notice remains visible during estimates. A regression changes bass density from one to two attacks per four-quarter-note bar while holding score-relative tempo at 120 quarter notes/minute.

Segmentation checks 48-onset phrases at 24-onset steps, requires consecutive evidence for changes without silence, and accepts a shorter rest when independent identities on either side disagree. Separate opening/ending evidence supplies displayed measure bounds without manufacturing global alignment pairs. Reorganisation on an isolated copy of the latest session changed Op.9 No.1's displayed opening from measure 10 to measure 1; Op.9 No.2 retained its ending through 672.87 seconds, and Nocturne No.20 began at 686.22 seconds, after the silence, instead of the old 649.08-second cut. The ordinary session data was not rewritten; use Rebuild candidate timeline to apply the new algorithm to saved sessions.

Validation: the full backend suite passed 121 tests; after the final keep/edit/undo and provisional-notice refinements, all 29 focused backend checks passed. Frontend unit tests passed 27 tests, TypeScript and the production build succeeded, and eight Chrome browser checks passed across both touch layouts. Cleanup screenshots were visually inspected. Tests used isolated data; no physical piano or microphone acceptance was performed. Restricted TestClient execution stalled even with a minimal FastAPI app; successful integration checks ran outside that restriction and the two stalled test processes were terminated.

## 2026-11-10 — tempo ambiguity, conservative turns, full-piece exercises and fullscreen

Bass timing is now compared with matched-score timing; approximately half/double-speed disagreement produces an ambiguous tempo with no extrapolation anchor. Phrase-median filtering withholds isolated timing slopes beyond a factor of 1.75, and extrapolation uses the lower of the phrase median and its latest retained local estimate. Estimated turns wait two seconds after a one-measure margin (two measures in two-page view), cannot reverse a note-confirmed page or run more than one page ahead, and preserve confirmed requests across frontend polling. Synthetic regressions cover disagreement, timing spikes, two-page delay and confirmed-request persistence. These checks do not establish correct tempo on arbitrary real performances or repeats.

Activity selection now distinguishes Partial exercise, Full-piece exercise and Complete performance. Full-piece exercise confirms whole-piece extent without asserting performance quality; grouping does not overwrite type, and equivalent rebuilds preserve the user-confirmed classification. The user-confirmed Op.72 No.1 take was relabelled Full-piece exercise · practice baseline and protected with a keep flag after a database backup. Only its metadata and tempo evidence were refreshed; original MIDI/audio were not rewritten. Its revised estimate is 54.56 quarter notes/minute with abrupt timing outliers withheld. A separate recording was active and was left running.

The header now names App fullscreen; a separate Score fullscreen control expands only the score and its page toolbar. Fit page retains its size-reset function and has a visible label. Browser tests verify actual PDF rendering in score fullscreen and recording controls in app fullscreen, as well as selecting Full-piece exercise and seeing it in piece history. Application code takes effect on the next launch; the active recording was not interrupted.

Final validation: 126 backend tests and 27 frontend unit tests passed; TypeScript and the production build succeeded. Ten relevant browser checks passed across both layouts over the final focused runs: following, actual-PDF fullscreen modes, cached PDF rendering, activity history, and fullscreen recording controls. Fullscreen screenshots were visually inspected. Earlier browser runs exposed a confirmed-request polling regression; it was fixed and both simulated-MIDI following cases passed again. Physical-piano acceptance remains unverified.

## 2026-11-10 — fullscreen render stability and open-score fallback

Fullscreen score rendering previously placed the conditional loading/error notice in the fullscreen flex layout. Inserting the notice shrank the observed score viewport, causing another raster request; removing it expanded the viewport and could repeat the cycle. Loading/error notices are now positioned over the viewer and do not consume layout height. The browser regression repeatedly inserts/removes the notice and asserts that fullscreen score height stays constant, then verifies rendering settles.

Open-score context is passed to live recognition without restricting catalogue matching. Unknown identity falls back to an explicit unconfirmed assumption with no measure/page request; a recognised different piece wins. New recordings preserve context markers for conservative offline fallback. Mixed-context intervals remain unidentified; assumptions do not establish completeness or automatic audio-retention eligibility. Capture, input queues and existing recording files remain independent.

The complete backend suite passed 129 tests. TypeScript and the production build passed. Both touch layouts passed fullscreen geometry/settling and ordinary simulated-MIDI following checks. The new context browser check waits for the selected library piece to load before exercising the fallback.

## 2026-11-10 — consistent fullscreen modes, maximized launch and score controls

App fullscreen now targets the document root without hiding the sidebar or practice controls. Auto-hide is suspended while either fullscreen mode is active, and returning from score fullscreen restores the app controls. Score fullscreen targets only the score shell; the existing LivePanel is portalled into that shell as a floating panel. Showing recognition therefore does not reduce page size. The loading-status overlay remains outside layout, preserving the previous render-loop fix.

The default launcher still passes --start-maximized. On X11, when wmctrl is available, it also identifies the localhost Chopin Studio app window and maximizes it after creation/restoration. Newly opened windows are preferred over older app windows; ordinary Chrome tabs and differently titled localhost apps are excluded. Explicit fullscreen launches retain their separate startup flag. Five launcher regression tests cover window identity, new/reused windows, restoration retries, default maximization and the fullscreen override. No Chopin Studio window was open for a physical maximization check during the final audit.

Clear score is available in the score toolbar and the optional hidden-controls touch bar. It clears the selected score, saved selection, automatic page command and open-score recognition context, without deleting the library PDF or recordings. The score toolbar also has Auto turns: on/off, including in score fullscreen; enabling it enables live recognition while preserving the provisional-reference opt-in.

Validation: TypeScript, the production build and whitespace checks passed. All five launcher checks passed. Fourteen existing practice/PDF/recording browser cases passed across both touch layouts; the two expanded fullscreen cases then passed after correcting their fixture so it did not reselect the score on reload. Those cases verify repeated app fullscreen with visible sidebar, direct and nested score fullscreen with live controls, persisted automatic-turn toggling, loading-status geometry, and Clear score remaining empty after reload while its library PDF still exists. Floating-recognition screenshots were visually inspected.

## Learning acceptance (2026-11-11)

- Full Python suite: 156 tests passed at the integration checkpoint. The final
  focused Learning run passed all 23 tests, including the additional provisional
  analysis gate. Existing Partitura/Lark deprecation warnings remain.
- Frontend: 27 unit tests passed; TypeScript checking and production build passed.
- Chrome: four Learning scenarios passed across landscape and compact layouts,
  including the actual reviewed PDF, automatic completion, hidden score, assisted
  recall, occurrence-specific omission, reload and navigation pause. A final
  navigation check covers the import-library action when the PDF is unreviewed.
- Rebuilding the full digital counterpart and human-readable inventory from the
  pinned local inputs produced byte-identical outputs.
- These checks use isolated data and simulated MIDI. Actual AP-470 input and real
  beginner-performance matching remain unverified; model visual score review is
  separate from independent musical/editorial verification.

Run Python from the repository root (`.venv/bin/python -m pytest -q`). For the
real-edition browser checks, build the frontend, then run from `frontend`:

```bash
CHOPIN_LEARNING_PDF=/absolute/path/to/paderewski_etudes.pdf \
  pnpm exec playwright test --config=playwright.learning.config.ts
```

The Learning browser configuration uses Chrome and port 8767 with isolated data
under `/tmp/chopin-learning-browser`; its tests do not operate on the normal
library. Without `CHOPIN_LEARNING_PDF`, the actual-edition scenario is explicitly
skipped; the unreviewed-source gate still runs. No scan is committed to the repo.


### Learning controls and fullscreen follow-up (2026-11-11)

The updated backend suite passed 162 tests; frontend unit tests passed 27 tests.
TypeScript checking and the production build passed. Browser checks cover nested
app/score fullscreen in Practice and Learning, persistent fullscreen across hidden
stages, automatic repeated takes, self-assessed take acceptance, manual stage
advancement, the first page of the selected piece, one-page default and optional
two-page mode. Layout assertions check that the controls occupy the left half and
the score occupies the full height of the right half. The controls panel scrolls
independently, including lesson settings and history. Simulated MIDI is used.

Final follow-up validation: 164 backend tests and all six Chrome checks passed.
The 30 focused Learning tests include an immediate restart that never invokes the
pitch evaluator, preserves the existing correct-attempt streak, and stays on the
same assignment. Browser checks also exercise the Restart take button within the
persistent fullscreen workspace. Restarting is neutral; it neither increments
nor resets the streak. The production build and TypeScript checks passed.

Adjustable layout follow-up: eight Chrome checks passed across landscape and
compact layouts. They verify the default score-left two-thirds split, pointer
resizing, keyboard adjustment, persistence across reload and reset, along with
fullscreen and the existing Learning flow. TypeScript and production build passed.

Learned-prefix review follow-up: 167 backend tests and ten Chrome checks passed.
Coverage includes learned-only/current-chunk boundaries, review after full-piece
completion, successful and failed review takes, restart and return, unchanged
Learning position/streak, and no automatic review repetition. Browser checks
exercise review and return within fullscreen in both layouts. TypeScript checking
and the production build passed. Automatic review prompts/startup remain planned.

Daily Sessions grouping follow-up: 18 backend metadata/retention tests, 31 frontend
unit tests and ten Chrome Sessions/cleanup checks passed. Tests cover local-date
boundaries and DST, per-piece groups, aggregate counts/time, retained individual
MIDI links, returning to an expanded group, and deleting only the selected take.
Existing piece-session navigation and audio-only cleanup checks remain passing.
TypeScript and production build passed. Learning uses a graduation-cap icon;
Library retains its book icon.

Live Learning staves and clickable completed chunks: 38 focused Learning tests,
32 frontend unit tests and all ten Chrome checks passed in landscape and compact
layouts. Browser coverage includes actual rendered live staves, played-only
hidden recall, selected-chunk review during recording, and return with unchanged
assignment/streak. Backend tests cover incremental projection, pending versus
missing notes, hidden-reference privacy, invalid chunk rejection before stopping
a take, and preserved progress. The broader backend checkpoint passed 184 tests;
TypeScript checking, production build and diff whitespace checks passed. MIDI was
simulated; physical piano input remains a hardware verification step.

Practice score fullscreen now includes Record session, an elapsed timer and Stop
session using the existing source choices and recording actions. The confirmation
dialog stays within the fullscreen element. Both landscape and compact Chrome
checks cover start, cancel stop, and stop-and-save from fullscreen, alongside the
existing fullscreen/page controls. TypeScript and the production build passed.

Learning comparison now shows one source measure at a time (or the most recent
16 played notes in one schematic measure during hidden recall), with the SVG
scaled to the controls panel. The current Learning chunk becomes a return button
in the map while reviewing. All 38 focused backend tests passed; browser checks
verify no horizontal overflow, a single-measure projection and map-based return
with unchanged progress. TypeScript checking and the production build passed.

## 2026-11-13: Heroic section Learning and separate piece persistence

- Backend: `.venv/bin/python -m pytest -q` — **250 passed**, two existing
  dependency deprecation warnings. The five new Heroic tests cover form/order,
  backward coda connections and review, per-piece/per-hand restoration after
  service restart, ungraded save on switching, stale requests, scan hashing and
  withholding automatic draft verdicts. The final focused rerun also checks the
  downloadable draft and the completed-lesson review span.
- Frontend: `pnpm test` — **39 passed**; `pnpm build` passed. Vite continues to
  report its large-bundle advisory.
- Headless isolated browser: Learning configuration — **21 passed, 9 skipped**
  across 1920×1080, 1280×900 and 820×1180. The skipped cases require a supplied
  real-edition PDF; no personal score fixture was supplied. The final Heroic-only
  rerun after the persistent provisional-status badge — **6 passed**.
- Browser server used port 8767, a new temporary data/state root per invocation,
  hardware disabled, and fresh headless profiles. Layout used an original generated
  synthetic PDF with the UI readiness flag mocked; the backend edition gate stayed
  active and rejected attempts with that synthetic PDF. Saved screenshots were
  inspected. No open user browser or running user service was controlled.
- Builder/source inspection and Python compilation completed; Markdown paths and
  `git diff --check` passed. Scores and original reference files were read-only.
- This validates software state handling and simulated workflows, **not** a finished
  Paderewski pitch transcription, physical piano/microphone/touchscreen acceptance,
  long-duration behavior or independent musical/editorial certification. Heroic's
  digital draft and outstanding review are described in [HEROIC_LEARNING](heroic_polonaise_op53_learning.md).

## 2026-11-13: completed Heroic pitch/attack counterpart

This supersedes the provisional digital-reference status in the earlier entry.
The fourteen Paderewski pages were visually compared with the complete inventory,
covering all 181 measures, 5,892 required physical attacks and 82 required grace
tones. The new bundle records 103 occurrence-specific corrections/decisions,
explicit local ornament policies and the resolved 119–120 conversion. This is
model musical review, not independent musician certification.

- Backend: `.venv/bin/python -m pytest -q` — **265 passed**, two dependency
  deprecation warnings. Ten Heroic tests cover the form, piece/hand persistence,
  scan gate, provisional-reference refusal, required grace notes, local ornament
  boundaries, full-piece matching, historical profile retention and MusicXML
  export. Matching a derived sequence is an integration check, not independent
  proof that the pitches match the scan.
- Frontend: `pnpm test` — **41 passed**; `pnpm build` passed, with the existing
  Vite large-bundle advisory.
- Headless Learning browser suite — **27 passed, 9 skipped**, across 1920×1080,
  1280×900 and 820×1180. The skipped tests require a supplied real-edition PDF.
  Port 8767, new temporary data/state roots, hardware disabled and fresh browser
  contexts were used. Heroic layout tests use a synthetic coloured PDF and mock
  only UI readiness; the backend exact-edition gate is unchanged. Full HD and
  compact screenshots were inspected.
- The final unmeasured MusicXML attack export rendered all **181 measures** with
  OSMD in an isolated headless browser. Selected excerpts spanning all fourteen
  pages and corrected notation hazards were visually inspected. Export checks
  compare every required spelled pitch with the JSON, including small notes and
  the mid-bar key change. The JSON and readable inventory rebuild byte for byte
  from pinned, read-only inputs.
- Source scans/reference XML were not modified. No running user service, open
  user browser or physical device was controlled. Independent musician, real
  performance, repeated-octave comfort, touchscreen and long-duration acceptance
  remain unverified. Learning and the exported study assess/show ordered attacks;
  they do not encode a facsimile performance score or grade rhythm/expression.

## Practice opening page and documentation rule — 2026-11-15

Practice now opens each score at its configured first PDF page, or PDF page 1
without a range, rather than restoring the saved page. Zoom, crop and one/two-page
preferences remain saved; Learning retains its existing page selection behavior.
README, TODO, Library and the acceptance checklist describe the change. AGENTS
now requires README, TODO and relevant documentation updates for every project
change.

Validation: `cd frontend && pnpm build` passed (with the existing large-bundle
warning), and `pnpm test` passed all 44 tests. Targeted headless Playwright tests
(`pnpm exec playwright test e2e/practice.spec.ts --grep 'Practice opens|PDF import'`)
passed four cases across 1280×900 and 820×1180. They cover a non-page-1 piece
start, saved later page, reload, return from Library, no-range fallback, saved
zoom/two-page preferences, PDF navigation, gestures, fullscreen and automatic-turn
cooldown. The first sandboxed attempt timed out waiting for the isolated server;
the retry with loopback access passed using fresh temporary data/state directories
and `CHOPIN_NO_HARDWARE=1`. Local documentation link targets and `git diff --check`
passed. No physical piano, microphone or touchscreen acceptance was performed.

## Score-aligned passages, MIDI resolution and practice progress — 2026-11-15

Implemented shared score-beat measurements for Analysis and two-take comparison;
explicit bass/inner/melody targets; ordered one-shot CC88 decoding; separate
release velocity; current measure histories, recurring differences, recall
retention, technical objectives and attributed problem time; opt-in recognised
piece opening; and conservative short-attempt/restart/repeated-theme handling.
Migration 006 preserves prior tables and adds objective/time records.

Automated verification:

- `.venv/bin/python -m pytest -q`: **292 passed**, with two existing Partitura/Lark
  deprecation warnings. Coverage includes channel/order/one-shot prefix handling,
  interrupted/stale/reversed streams, release semantics, byte-preserved journals,
  CC88-safe clips/held notes/cut boundaries, pedal inheritance, arpeggiated voice
  balance and target gates, printed dynamics, shared-reference take alignment,
  current/stale analysis selection, objective revisions/time unions/rebuilds,
  recall gaps, short attempts and repeated themes with an input error.
- `cd frontend && pnpm test`: **44 passed**.
- `cd frontend && pnpm build`: passed with the existing large-chunk warning.
- `PLAYWRIGHT_CHANNEL=chrome pnpm exec playwright test recognition-context.spec.ts practice.spec.ts --grep-invert 'import private recording'`:
  **14 passed** across 1280×900 and 820×1180. The optional private-MIDI case was
  deliberately omitted; synthetic fixtures cover the new functionality.
- Local Markdown link paths, Python compilation and `git diff --check`: passed.

Browser runs used fresh headless Chrome processes/contexts, dedicated loopback
ports, unique temporary application data/state and `CHOPIN_NO_HARDWARE=1`.
Final runs use separate temporary `--output` directories as well. Initial attempts
exposed a test-selector issue, cross-viewport objective-name reuse and collisions
between concurrent Playwright artifact directories; those test issues were
corrected. The default bundled Chromium binary was unavailable, so the general
suite used the installed Chrome channel in an isolated headless process. A longer
browser runner was terminated before completion; bounded per-viewport runs are
recorded below rather than treating interruption as a pass.

No personal application data, running user service, open user browser or physical
MIDI/audio device was used. AP-470 wire ordering, effective sensor resolution,
release calibration by device/tone, musical target suitability, real playing,
touchscreen and long-duration acceptance remain unverified. Existing analyses
need reanalysis to populate passage evidence; reference/voice ambiguity is kept
explicit and does not establish an automatic musical-quality grade.

Final bounded Sessions/Analysis verification passed using
`pnpm exec playwright test --config=playwright.sessions.config.ts --project=<name> --output=<unique-temp-directory>`:

| Project | Viewport | Result |
| --- | --- | --- |
| `full-hd` | 1920×1080 | 10 passed |
| `landscape` | 1280×900 | 10 passed |
| `compact` | 820×1180 | 10 passed |

These 30 cases cover the selected activity's newest evidence, the new synchronized
passage/take view, measure filtering, fourteen-bit detail and ordering diagnostics,
objective creation and interval attribution, automatic opening gates, piece/session
navigation, audio cleanup and Learning recording groups. Saved Full HD and compact
screenshots were inspected. Together with the 14 Practice/recognition cases above,
44 headless browser cases passed. No previously interrupted run is counted as a
completed suite.

## Architectural refactor — 2026-11-16

Starting revision: `6c07577446615e254a478ccadd6ee2653a5043b2`. Branch:
`codex/architecture-consolidation`. See [Refactoring](REFACTORING.md) for the
source/import/route inventory, module boundaries, compatibility decisions,
measurements, before/after table and developer guide.

| Executed check | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 316 passed, 2 existing dependency deprecation warnings, 69.27 s |
| Post-import-cleanup contract/passage/comparison regression subset | 46 passed, 2 dependency warnings, 2.52 s |
| `.venv/bin/ruff check backend/chopin scripts/profile_refactoring.py` | Passed |
| `cd frontend && pnpm format:check` | Passed for the documented incremental scope |
| `cd frontend && pnpm test` | 8 files / 44 tests passed |
| `cd frontend && pnpm build` | Strict TypeScript and Vite passed; existing OSMD chunk-size warning |
| `cd frontend && pnpm test:e2e` (headless Chrome channel) | 114 passed, 9 skipped, 5.0 min |
| Learning config | 27 passed, 9 skipped, 49 s |
| Sessions config | 30 passed, 1.8 min |
| Rendering-profile artifact rerun | 3 passed, 7.7 s |

Browser checks use independent headless processes/fresh contexts, hardware-disabled
servers and unique temporary data/state on ports 8766/8767/8768. All configs cover
1920×1080, 1280×900 and 820×1180. No user's running application or browser was
modified/restarted. The three scan-dependent Learning scenarios skip at each
viewport; they were not counted as passes. Backend tests cover synthetic
edition/hash gates, all three lessons, independent hands, interruption/restart,
heartbeat/pedal, hidden recall and authoritative-journal assessment.

The first broad browser runs exposed an inherited repeated-phrase following
fixture and cross-workflow reference-quality contamination. Baseline and
refactored recognizers returned identical ambiguous locations. The fixture now
uses one unique phrase on a dedicated catalogue piece and checks its provisional
label while stable. The complete subsequent suite passed; earlier failures are
not counted as passes. Optional ignored-private-MIDI fixture readers were replaced
with synthetic data; initial baseline tests inherited their former behavior.
No private recordings, scores, databases or measurement artifacts entered Git.

Vite emitted the same stylesheet hash as the original build. Six saved Learning
screenshots (Heroic fullscreen, review-return fullscreen and resizable score, Full
HD and compact) had identical dimensions and pixel content to baseline. Practice,
fullscreen and evidence screenshots were inspected; existing DOM-bound checks
verified reachable controls and score layout.

Synthetic profiling used 44 catalogue pieces / 528 takes and two 2,000-note,
1,000-second performances, with warmed imports and three tracemalloc samples.
Progress median: 0.236 → 0.130 s, 397 → 309 queries. Comparison median:
12.602 → 3.642 s; Python peak: 54.0 → 33.1 MB. Organisation's single sample
0.559 → 0.774 s is recorded without an improvement claim (about 10.1 MB peak).
These instrumented local results are not real-piano, power-loss or soak acceptance.

A 24-page-visit browser profile made one PDF request per viewport. Two 12-page
cycles measured 496/404 ms at Full HD, 399/332 ms at 1280×900 and 395/330 ms
at 820×1180. Descriptive Chromium JS heap samples were about 7.35–8.22 MB.
Learning snapshot sizes were 34,250 bytes (Aeolian), 127,278 (Heroic) and
65,610 (Nocturne); test artifacts include exact values. GPU/canvas/process RAM
and long-duration growth are not inferred. Existing unit tests separately check
PDF bitmap limits, eviction and cancellation.

The sandbox stalled in AnyIO TestClient startup and blocked Playwright readiness;
completed suites ran outside that restriction with the isolation above. The Node
runtime was explicitly added to PATH because the initial shell had no `node`.
Authored GitHub Actions has not run remotely. Physical MIDI/audio/touchscreen,
long-duration capture, actual power loss, real cloud and private-scan GUI acceptance
remain unverified. No SQLite migrations, API path changes or source-data changes.


## Library measured counterpart audit — 2026-11-17

Four complete local model audits: Prelude Op.28 No.4 (26 measure entries), Mazurkas Op.68 No.3 (60), Op.68 No.2 (66) and Op.30 No.2 (65), every measure and both staves. Source PDFs and enlarged passage crops were visually compared with full pitch/rhythm/chord inventories and rendered derived MusicXML. The six final SVG export pages were rendered in a fresh headless Chromium process and visually inspected. The exact checked/excluded scope and corrections are in `reference_reviews`; no scan, downloaded XML or private recording is committed. Installation added four active verified counterparts, preserved all 42 acquired provisional originals, and retained one superseded generated Prelude engraving with rejected quality after restoring visible tuplet numbers.

New importer/installer/metadata regressions plus recognition boundaries: **18 passed**, clean exit. Frontend unit tests: **44 passed**; production types/build passed (existing large-chunk warning). New Library quality-label browser checks: **3 passed**, isolated hardware-disabled temporary app, fresh headless Chrome at 1920×1080, 1280×900 and 820×1180. The initial browser run used a stale built frontend and failed to find the new label; rebuilding and rerunning passed. No user browser or running app was controlled.

The full backend run printed **347 passed** but its command later ended with SIGTERM (exit 143). A disjoint two-part rerun printed 185 and 162 passed; the first command exited normally, the second again ended with SIGTERM after its passing summary. These are recorded assertion results, not a clean full-suite process/teardown pass. The focused 18-test rerun exited normally. No production restart, physical piano/audio/touchscreen test, historical reanalysis or audio retention change was performed. The broader 40-piece request remains unfinished: **36 pending** in the audit ledger.

## Sessions defaults and returning-theme live following — 2026-11-17

Sessions now opens with Audio cleanup collapsed, including after Stop & save and after leaving an explicitly expanded cleanup panel. Practice Score fullscreen expands recognition on each entry; users can hide it during the visit. The visible label is **Live recognition**. A backward live match that also plausibly fits the nearby later passage holds automatic page movement and reports returning-theme uncertainty, rather than treating that evidence as a restart. Saved segmentation and authoritative capture are unchanged by this safeguard.

Checks completed:

- Targeted backend: `tests/test_tempo_following.py` and `tests/test_recognition_boundaries.py` — **29 passed**, clean exit. Synthetic sequences cover exact/varied return themes without backward page requests, recovery on distinctive later notes, and genuine distinct opening restarts.
- Frontend `pnpm test` — **44 passed**; `pnpm build` passed with the existing large-chunk warning.
- Headless Playwright `fullscreen-modes.spec.ts` with the Learning configuration — **3 passed**; `recording-cleanup.spec.ts` with the Sessions configuration — **12 passed**; `pdf-rendering.spec.ts` and `milestones.spec.ts` with the general configuration and `PLAYWRIGHT_CHANNEL=chrome` — **6 passed**. Each covers 1920×1080, 1280×900 and 820×1180 with fresh browser contexts and temporary hardware-disabled application data/state. Full HD screenshots were visually inspected; overlay expansion preserves PDF dimensions and recording controls remain reachable.
- `git diff --check` passed.

Initial sandbox browser attempts could not reach their temporary loopback servers and timed out. General tests initially lacked the bundled Chromium headless executable; rerunning with installed Chrome and loopback access passed. These were isolated test services, not the user's browser or production service. The running app was not restarted. Physical piano, microphone and touchscreen acceptance, long-session following and universal repeat/edition disambiguation remain unverified.

## Learning hidden-recall PDF pre-rendering — 2026-11-17

The Score viewer now rasterises assigned pages into its existing bounded detached-canvas cache while concealed. Hidden recall still removes score canvases from the DOM and keeps loading/error page notices concealed. Peeking and returning to visible study reuse completed cached renders; different pages/viewports and an unfinished initial preload can still require rendering. This does not mark an attempt assisted until the existing explicit peek action.

`pnpm build` passed (existing large-chunk warning); `pnpm test` passed all **44 tests**. Isolated headless `learning.spec.ts` and `fullscreen-modes.spec.ts` with the Learning configuration passed **21 checks**, with **6 skipped** because the private reviewed-PDF/learned-prefix fixture was not configured. Viewports: 1920×1080, 1280×900 and 820×1180. New synthetic tests start directly in hidden recall and hidden review, verify a fully painted detached page with no score canvas in the DOM, then reject fresh PDF rasterisation to verify that Peek, immediate retakes and Return to learning reuse the warmed page. `git diff --check` passed. No production restart, user browser, physical hardware or personal application data was involved.

## Narrowed nine-piece counterpart batch — 2026-11-17

This supersedes the earlier four-complete/36-pending batch status: the user narrowed production to nine works, all now audited and installed. The other 31 original candidates are deferred. Full both-staff scan review and derived-export inspection finished for Nocturne B.49 (65 bars), Polonaises Op.40 Nos.1/2 (88/117), Waltz Op.64 No.2 (193 entries including pickup) and Étude Op.10 No.12 (84). Enlarged source crops resolved accidentals, tied voices, optional graces and ending runs; full derived notation was rendered with Verovio in a separate headless Chrome process and visually checked. Rendered exports are not facsimile replacements. Exact coverage, corrections, original source and scan fingerprints are in the packaged per-piece descriptors.

- Final focused backend suite: **47 passed**, clean exit, covering additive installation/edit protection, import graces, fractional tuplets and simultaneous voices, scope/completed-coverage gates, recognition/restarts, musical-quality evidence and direct/estimated following. New mapping tests cover reference-specific numbering, preserved subsequent manual calibration and missing/invalid review rejection.
- Ruff correctness/import checks passed for the builder, review metadata/page-map helper, live following, quality ranking and associated tests. `git diff --check` passed.
- All nine corrected scores were rebuilt against their pinned sources and compared with installed MusicXML hashes, stored notes, measure counts and per-measure event inventories. A read-only installed-data check also compared every original reference listed in the batch ledger against its pre-audit file/note fingerprints and provisional status.
- The complete backend run was attempted again but terminated with **SIGTERM / exit 143**, after 41 progress dots and without a summary. It is **not** a full-suite pass. The focused suite above completed normally. Earlier frontend/unit/build/Library browser results are recorded above; this continuation adds no frontend change.

Installation was additive against supported schema 6 and refreshed matching review metadata/page-map baselines. It did not restart the running application, alter source files, rewrite historical analyses or touch recordings/MIDI/journals. Headless export inspection used file URLs and a fresh temporary browser profile; no user browser or physical devices were accessed. Installed references can be found by the running application's catalogue refresh; changed backend behavior requires the normal application reload/restart. Physical performance acceptance, repeat-route calibration and independent editorial certification remain unperformed.

## Aeolian Harp expanding backward review — 2026-11-17

Added an explicit learned-only expanding review alongside standard review: last two chunks, then four, six and so on, capped at the selected hand's learned prefix. One/odd totals are capped correctly. Unassisted, capture/source-valid passes prepare the next range without starting capture; failure/assistance keeps the range. Full-span success marks review completion. No learning position/streak/mastery is advanced, and actual attempted ranges remain in history. The sequence is temporary; other pieces reject the mode and are tracked as future work.

Validation: full `tests/test_learning.py` **84 passed**, clean exit, including new 1/5/6-chunk sequences, failure/peek holds, neutral profiles, exact final completion and unsupported-piece/options rejection. Targeted review subset **6 passed**. Frontend build and **44 unit tests passed** (existing large-chunk warning). Isolated headless Learning checks **12 passed**, across 1920×1080, 1280×900 and 820×1180, covering the new mode beside standard review, progress text, return control and concealed-score caching. `git diff --check` passed. The initial sandbox backend run stalled without results and was interrupted; the clean full-suite run used normal loopback access outside that sandbox with temporary synthetic data. No user browser, production restart or physical piano/microphone acceptance was involved.

## Build-backward review manual correctness — 2026-11-18

Finished build-backward review takes now offer **Mark review take correct**, including assisted takes with score peeks. Explicit acceptance advances the review length or marks the full range complete, without modifying the learning profile or the original pitch verdict, errors or assisted flag. Only the latest evaluated, capture-healthy take for the unchanged active review assignment can be accepted; repeated acceptance is idempotent. Ordinary learning and standard review acceptance rules are unchanged.

Validation: full `tests/test_learning.py` **87 passed**, covering assisted/unassisted manual progression through 2/4/5 chunks, preserved evidence/profiles, final completion, duplicate requests, paused takes and obsolete assignments. Frontend build passed (existing chunk-size warning), **44 frontend unit tests passed**, and **6 isolated headless browser checks passed** at 1920×1080, 1280×900 and 820×1180. Browser checks verify mode availability and manual acceptance of a synthetic assisted take with the next-length status. `git diff --check` passed. No running-app restart, personal-data test or physical piano/microphone acceptance was performed.

## Whole-piece Analysis overview — 2026-11-18

Added an activity-wide chart above the detailed comparison, with whole/half/quarter-piece scales, range navigation, independently selectable measurements and tap/keyboard measure selection. The chart uses measure means and minimum–maximum strokes from saved aligned measurements; absent bars/values remain gaps, unlocated points are omitted and partial activities retain their actual coverage. Detail pagination/filtering does not trim the overview.

Validation: **47 frontend unit tests passed**, including 181-measure coverage, missing/unmatched/unlocated data, mean/range aggregation and uncertainty/historical-data notices. TypeScript/production build passed (existing large-chunk warning). The targeted score-aligned analysis browser workflow **passed at all three configured sizes: 1920×1080, 1280×900 and 820×1180**, exercising full-width bounds, half/quarter ranges, slider navigation, measure drill-down, independent detail filtering, optional empty lanes and existing passage/take/progress flows. Full HD and compact saved overview screenshots were inspected. `git diff --check` passed. The first sandbox run timed out at server readiness; the bundled Playwright browser was also unavailable. Successful runs used installed Chrome headlessly with fresh temporary profiles, a separate loopback server, temporary data/state and hardware disabled. No user browser, personal data, physical devices or running-app restart was used. Physical touchscreen readability and personal long-performance acceptance remain unverified; the complete browser suite was not run.

## Optional page turning during Learning peeks — 2026-11-18

Added **Turn score pages automatically while peeking**, default on and saved in browser storage. During an active revealed peek, the reviewed Learning staff alignment supplies the PDF page for the most recent matched/ornament attack. Unmatched newest attacks and pruned/uncertain projections withhold requests. Hidden recall and finished attempts expose no follow-page request. Practice recognition and assessment remain independent; provisional lessons do not supply this alignment. Existing manual-navigation cooldown applies, and disabling the option cancels pending automatic movement.

Validation: full Learning backend suite **88 passed**, clean exit; frontend types/build passed with the existing chunk-size warning and **47 frontend tests passed**. Isolated headless Learning checks **9 passed**, including default-on behavior, actual page movement, disabling with continued polling, stored preference after reload and hidden-score cache safeguards, at 1920×1080, 1280×900 and 820×1180. Backend coverage checks hidden/revealed/finished follow-page gates and reviewed PDF mapping. No production restart, personal-data testing or physical piano/microphone/touchscreen acceptance was performed.

## Review measure retries and local error cue — 2026-11-19

Reviews now default to a local browser error tone and measure-only retry after a definite authoritative-capture pitch/order mismatch and key release. Manual review retake uses the last located measure, including from the finished result; explicit whole-review restart remains available. A pitch-correct repaired measure prepares the remaining range. Interrupted, repair and tail captures keep their original MIDI and individual assessment ranges; explicit acceptance can advance a segmented build-backward sequence without inventing an uninterrupted full-range pass. Learning stages/streaks and ordinary Learning's opt-in restart preference are preserved. Peeks remain visible and assisted across immediate retries.

Validation:

- Final Learning and API-contract regression run: **95 passed**, clean exit. Coverage includes both/right/left hands, default review retry with ordinary auto-restart off, held-key notification and release gating, measure boundaries/staff overlap, extra final attacks, finished-measure retakes, separate tail ranges, full-review escape, retained MIDI, idempotency and explicit segmented acceptance with unchanged pitch evidence/profile.
- **47 frontend tests passed**; production type/build check passed with the existing bundle-size warning. Changed frontend files pass Prettier; changed backend modules pass Ruff correctness/import checks. The broader Ruff invocation including `tests/test_learning.py` reports five existing unused imports/variables in unchanged lines; they were left outside this task.
- Complete isolated headless Learning/fullscreen browser suite: **42 passed, 9 skipped**. Skips require an optional reviewed-score fixture; they are not passes. Final focused browser checks: **9 passed** at 1920×1080, 1280×900 and 820×1180, covering actual target changes to one measure, warm concealed scores/retained peeks, one Web Audio tone per mistake without duplicate history cues, and explicit segmented-review acceptance.
- Full backend suite attempted: **365 passed, 2 failed**. The additive OpenAPI snapshot mismatch was corrected and its contract check passes in the final run above; the snapshot also incorporates the existing expanding-review mode. The separate `tests/test_practice.py::test_live_requests_survive_polling_and_reset_after_idle` failure (`KeyError: page_request`) reproduces alone and remains unresolved; its test and Practice/live implementation were not changed by this task. The full suite is therefore not reported as passing.
- `git diff --check` passed. Sandbox API/browser startup attempts stalled and were interrupted or timed out; completed runs used the same temporary data, hardware-disabled services and isolated headless browsers with the required execution access.

No production restart, personal-data test, user-browser interaction or physical piano/microphone/touchscreen/speaker acceptance was performed. Audible output still depends on browser audio activation and output volume. Restart the application when convenient to load the backend update.

### Uninterrupted review after a measure rewind — 2026-11-19

Follow-up correction: an error now rewinds the review to the beginning of the affected measure and immediately records from there through the original review end after key release. The corrected bar is no longer a separate one-bar drill, so it cannot trigger an intermediate finish or require Start review for the remaining passage. Manual Retake last measure uses the same rewind behavior. Repeated errors rewind again; Pause still saves and stops. Interrupted MIDI, exposed score/assistance and separate captured-range assessments remain preserved. Updated README, Learning instructions and TODO to remove the intermediate Finish/Start step; the earlier validation entry above describes the superseded first implementation.

Validation: **96 Learning/API-contract tests passed**, including both/right/left-hand capture remaining active across the repaired bar even with automatic finish enabled, automatic completion only at the original end, repeated rewinds, manual/finished retakes, explicit whole-review restart and pause. **47 frontend tests passed**, production types/build passed with the existing bundle-size warning, and **12 isolated headless browser checks passed** across 1920×1080, 1280×900 and 820×1180. Browser checks cover the resumed range, recording controls with no Start review button during the rewind, sound deduplication, retained score peeks and fullscreen return controls. Backend Ruff and git diff checks passed. The full backend suite was not repeated for this follow-up; the separate Practice page-request failure recorded above remains unresolved. Physical piano/audio/touch acceptance remains untested. No production restart, hardware access or personal-data testing was performed.

## Taller Analysis overview and labelled y axes — 2026-11-19

Whole-piece overview lanes now use 180 rather than 105 SVG units, with 115 rather than 55 units of plotting height. Multiple labelled horizontal gridlines replace the former two endpoint labels; tempo explicitly shows BPM, variable ranges use readable rounded tick steps, and velocity/pedal retain 0–127 scales. Axis labels sit at their actual plotted values and scales remain stable when navigating the same activity. Coverage, measure selection and measurement estimates are unchanged.

Validation: **47 frontend tests passed**, including tempo tick labels and existing coverage/gap behavior; frontend types and production build passed with the existing bundle-size warning. **3 isolated headless Analysis workflow checks passed** at 1920×1080, 1280×900 and 820×1180, verifying chart height/width, visible BPM axis values, range navigation and measure selection. Saved Full HD and compact screenshots were visually inspected. The initial browser attempt could not launch the missing bundled Chromium; the completed checks used installed Chrome in fresh headless processes, temporary app data/state, a dedicated loopback port and disabled hardware. `git diff --check` passed. No production restart, personal-data testing or physical touchscreen acceptance was performed.

## Practice restart recognition and the reported saved take — 2026-11-19

Read-only forensic inspection identified a missed opening return in the latest reported Practice recording. The rigid twelve-onset maximum-pitch proposal rejected a phrase whose longer chord alignment independently supported the opening. A repeated short opening motif also disabled the older early-retry path. The new detector proposes from a chord (including closely spaced rolled attacks), validates the opening phrase and its first anchors, checks prior progress and rejects plausible forward continuations/written returns. Anchors prevent cutting on a coincidental opening pitch before the actual restart. Independent edge evidence in a disjoint repeated passage no longer changes the displayed endpoint without monotonic-span support. Derived results use version `symbolic-edit-v9-chord-supported-restarts-experimental`.

Validation: **377 backend tests passed**, clean exit, with two dependency deprecation warnings. Synthetic coverage includes bass-first/treble-first rolled chords after early, later and full preceding takes; a repeated short opening motif; exact timestamps; ornamented written returns; disjoint endpoint evidence; and rebuild preservation of original capture bytes, undo history and overlapping Keep protection. Existing capture/recovery, retention, timeline, reference-quality and live-following checks passed. The previously failing live lifecycle test used a piece-only mocked recognition result without the reference identity needed for edition-bound page maps; its fixture now retains a real synthetic reference/alignment while scripting the recognition verdict. No production navigation gate was weakened to satisfy that test. Ruff correctness/import checks on changed recognition modules and boundary tests, and git diff checks, passed.

The reported recording was corrected separately from testing through the existing undoable timeline editor with the checked prior revision: one abandoned attempt followed by the complete retake. Two new range/revision-bound analyses and reports were added. Historical analysis rows and the previous timeline snapshot remain available; all five original capture files, including original MIDI, journal, microphone audio and metadata, were fingerprint-verified unchanged before and after commit. The stopped app was not launched, migrated or seeded, no device was opened, and no automatic audio cleanup was run. No personal recording or score data was added to regression fixtures or Git. Other saved timelines were not changed. Physical live-recognition acceptance beyond the diagnosed saved case remains open; arbitrary ornaments, severe errors and ambiguous repeat routes are still estimates, not guaranteed recognition.
