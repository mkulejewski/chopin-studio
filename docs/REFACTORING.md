# Architectural refactoring

Started 2026-11-16 from `6c07577446615e254a478ccadd6ee2653a5043b2` on
`codex/architecture-consolidation`; initial working tree clean.
The [source inventory](REFACTORING_INVENTORY.md) records all production modules,
internal imports, largest Python functions and HTTP entry points before extraction.

## Boundaries and invariants

- `create_app` composes Store, authoritative Recorder, jobs, live following and
  Learning. Lifespan, loopback/origin enforcement and shutdown remain here.
- Recorder/MIDI journal and microphone capture are independent of derived
  recognition, rendering, assessment and reports. Preserve ordered events,
  recovery, overflow reporting, imported bytes and unknown MIDI fields.
- Store owns schema migrations and serialization. Existing migrations 001–006
  are immutable. Personal notes/mastery, lesson revisions, user corrections and
  historical analyses are preserved; eligibility is a read-time decision.
- Audio-only deletion uses its existing recoverable protocol; explicit Keep,
  timeline locks and whole-session deletion remain distinct.
- Learning matching differs from Practice recognition: two staff orders,
  unordered chords, reviewed edition/hash gates and authoritative final capture.
  Keep hand/piece progress, hidden recall, heartbeat, restart and pedal semantics.
- UI extraction preserves DOM structure/cascade, gestures, fullscreen hosts,
  navigation and Practice recording across UI closure. Learning still pauses.
- No production data, physical hardware or user browser is used for validation.

## Audit findings and intended boundaries

`main.tsx` (2,194 lines) mixes lifecycle/navigation with four workspaces, settings
and piece editing. Extract pages/dialogs with explicit typed props; keep shared
recording/navigation state at the root. `Learning.tsx` (1,567) mixes the lesson
selector, layout, requests and editors; separate types, workspace and panels.
`PracticeReview.tsx` (1,011) contains timeline, audio production and report flows.
`AnalysisEvidence.tsx` (763) owns types consumed by comparisonScore, creating an
undesirable presentation-to-domain dependency. Move types and pure selectors out.
`Score.tsx` (776) combines PDF rendering and gestures with fullscreen/following;
extract cohesive hooks while preserving renderer cancellation/cache ownership.
`style.css` (2,972) contains ordered historical overrides; split by contiguous
scope, preserving every selector and media-query order rather than deduplicating.

Backend `learning.py` (830) combines bundles/stages, pure matching, persistence and
controller. `organisation.py` (466) combines MIDI extraction, recognition,
segmentation and offline analysis. Existing velocity/passages/tempo/comparison
modules are cohesive and should be reused. `practice_api.py` (662) and `app.py`
(511) mix domain routes with composition. Extract scoped routers, shared readiness
lookups and upload handling; domain services must not import HTTP modules.

Assessment, retention and progress each compare six snapshot fields. Progress
filters saved/imported sessions and whole-recording deletion; retention permits
explicitly kept discarded takes; assessment currently lacks source/deletion gates.
Reference fingerprints exist but are not checked for current eligibility. Share
freshness evidence and retain explicit consumer policies; test fixes separately.

Store.seed creates eight legacy pieces before catalogue seeding 44 works.
Retain legacy initialization semantics until fresh/migrated database tests prove
consolidation safe. Keep DELETE recording alias: it is an existing external
contract. Local imports currently break cycles among organisation/retention and
Learning/staff projection; pure lower-level modules should remove these cycles.

## Coverage and gaps

Existing suites cover journal loss/recovery, disconnect, deletion recovery,
timeline revisions/undo, recognition boundaries, passage evidence/objectives,
Learning matching/hand selection/all three lessons, following gates and API/UI
workflows. Add contract, freshness, migrated-seeding and transactional failure
characterizations before extraction. Existing synthetic tests do not establish
physical MIDI/audio/touchscreen, long-duration or actual cloud acceptance.

Performance-sensitive areas: capture callback/writer queues (leave bounded),
offline materialized notes, repeated progress queries per 44 pieces, alignment
on long recordings, bounded Learning beam and PDF document/bitmap caches.
Measure synthetic endpoint workloads before adding optimization; no persistent
cache without revision/deletion invalidation.

## Execution phases

1. Baseline inventory, tests and API compatibility fixture.
2. Shared freshness/types; tested catalogue initialization and transactions.
3. Backend Learning and organisation domain extraction with stable facades.
4. HTTP model/context helpers and scoped routers; preserve path/payload contracts.
5. Root pages/dialogs; Learning and review panels; shared response types.
6. Score hooks and ordered scoped styles; browser layout checks.
7. Measured performance, incremental quality tooling/CI and final documentation.

## Validation log

- Initial frontend attempt failed because `node` was absent from shell PATH.
  Bundled Node runtime found; commands use its bin directory in PATH.
- Baseline frontend: 8 files / 44 tests passed; strict TypeScript/Vite build passed.
  Existing large-bundle warning retained.
- Baseline backend: all 292 pre-existing tests passed in the full run (129 s).
  Two initial new-fixture errors were corrected; all 10 characterization tests
  then passed (4.97 s). Sandboxed AnyIO TestClient startup stalled; tests run
  outside that sandbox with temporary fixtures. Browser baseline still running.

### Shared evidence selection

`analysis_selection.py` now owns snapshot equality, source/deletion policy and
reference fingerprint checks. `domain_types.py` names performance notes, score
positions, reference identity and freshness evidence. Assessment/progress select
one current result per take; retention explicitly allows recovered/incomplete or
discarded takes for manual audio review. Legacy analyses without fingerprints
retain snapshot behavior (reference freshness is unknown), without changing their
saved evidence. A changed or removed fingerprinted reference withholds current
eligibility. Historical rows and personal mastery are untouched.

Targeted contracts/retention/passage tests: **59 passed**. Baseline isolated
Learning/fullscreen Playwright: **27 passed, 9 skipped**, three viewports including
1920×1080. Skips require an unbundled reviewed PDF; no private scan was fetched.

### Domain extraction

Learning definitions/stage strategy, pure pitch evaluation and versioned profile
persistence now live in `learning_definition.py`, `learning_matching.py` and
`learning_profiles.py`. The stable `learning.py` controller still owns recorder,
heartbeat, locking, source hash, continuation and authoritative final judgement.
`learning_staves.py` depends on the pure matcher rather than the controller.

Practice uses `performance.py`, `recognition.py`, `segmentation.py` and
`segment_analysis.py`; `organisation.py` retains timeline orchestration and
compatibility exports. Retention/live/tempo import the smaller owning modules,
removing the former retention → organisation → retention dependency.
No matcher, thresholds, journal format or MIDI originals changed.

Broader backend after freshness: **309 passed** (74.86 s). After correcting two missing imports found by the extraction tests, the full
backend suite passed again: **309 passed** (76.38 s). No migrations introduced.

### HTTP and persistence ownership

`api/` contains scoped capture, library, settings, timelines, recordings, audio,
analysis, progress, references, reports and following routers. Request models and
bounded upload staging are separate; a small explicit `PracticeContext` shares
readiness checks and read helpers. `create_app` still owns lifespan/security,
Learning composition and shutdown. `practice_api` preserves its public installer
and request-model imports. The complete pre-refactor OpenAPI fixture still passes.

`timeline.py` owns reusable timeline writes/undo. An injected SQLite failure
reproduced partial timeline deletion in the old route. `Store.transaction()` now
uses serialized savepoints; nested `execute` calls participate, and failed writes
restore segments, history and Keep protection. Undo reads its snapshot/revision
inside the same transaction. Audio deletion's recovery protocol is unchanged.

Catalogue initialization now has one owner in `catalogue.py`; the duplicate
eight-piece data table is removed. The original eight-ID repair behavior and
seed markers are deliberately retained, using the 44-piece data as their source.
Fresh installs, migration from schema 001, edited pages/notes/mastery and reopening
are characterized. `Store.seed()` remains a compatibility entry point.
Hardware-disabled servers skip physical MIDI-output enumeration.

Router/store/catalogue broader validation: **312 passed** (62.61 s), followed by
focused validation of the extracted timeline service. Ruff's undefined/unused
checks pass across production Python; unused imports and an unused summary list
were removed. No schema migrations or API payload/path changes were introduced.


### Frontend workspaces, evidence and score interactions

`main.tsx` only mounts `App`. `App.tsx` coordinates navigation, shared selection,
recording/shutdown, fullscreen hosts and dialogs; `useAppStatus` owns service
polling/presence, cancellation and save-triggered refresh. Practice, Library,
Sessions and Analysis pages live under `pages/`. Search/filter and cross-workspace
selection remain in App to preserve restoration when a page unmounts. Library
owns its filtering computation. `dialogs/` separates orchestration, piece editing
and device/settings presentation.

`Learning.tsx` owns lesson selection; `learning/LearningWorkspace.tsx` owns its
safety-sensitive polling, visibility pause, pedal lease and shared attempt/editor
state. LearningControls, ChunkMap, AttemptReview, NoteRuleEditor and RoutineEditor
preserve the existing DOM and pass/hidden-recall behavior. Heartbeats remain
separate from ordinary polling. All three piece bundles and revisions are unchanged.

`practice/` separates timeline controls, activity editing, microphone playback,
audio production and report workflows. Audio/report-only state and their loading
effects live in their owning panels, with cancellation guards. `analysis/` owns
piano-roll and microphone evidence presentation. Shared analysis/passage/progress/
comparison response types live in `types/`; comparisonScore no longer imports
its domain types from AnalysisEvidence. Compatibility type re-exports remain.
Edition-aware pitchLabel and Learning spelling policies remain distinct from the
plain MIDI fallback label; no enharmonic policy was simplified.

`score/` owns fullscreen subscription, pointer gestures/cancellation and gated
page following/manual override. Score retains document/view state, rendering,
cache ownership and controls. PDF cache limits/cancellation are unchanged.
`styles/` holds ordered contiguous base, Practice/score, library/dialog, responsive,
evidence, fullscreen, Learning, recording and passage scopes. No selectors were
removed or reordered. Vite produced the exact original `index-B_sEFykq.css` hash;
six saved Full HD/compact Learning screenshots matched the baseline pixel for
pixel. Additional Practice/score screenshots and DOM bounds were inspected.

### Measured performance

`scripts/profile_refactoring.py` creates only temporary synthetic data: 44 pieces,
12 takes per piece (528 saved analyses), and two 2,000-note / 1,000-second takes.
Numerical imports are warmed equally; three requests per endpoint run under
tracemalloc. These are local instrumented measurements, not hardware acceptance or
universal latency guarantees. Background live polling is stopped in this fixture.

| Workload | Before | After | Result |
| --- | ---: | ---: | --- |
| GET progress, median | 0.236 s / 397 queries | 0.130 s / 309 queries | Current evidence decoded once per piece for both consumers |
| GET comparison, median | 12.602 s | 3.642 s | Bounded timing-neighbor scan and JSON-native response serialization |
| Comparison Python peak | 54.0 MB | 33.1 MB | Avoid generic recursive response copying |
| Organisation, one sample | 0.559 s | 0.774 s | No optimization claimed; comparable 10.1 MB Python peak |

CPU profiling identified the quadratic timing-neighbor scan (about 0.284 s for
2,000 onsets in the direct CPU sample). It now examines at most eight adjacent
score intervals, preserving sparse/unlocated-anchor gates. Complete JSON payload
comparison tests protect the explicit JSONResponse paths. Progress reuses evidence
only within one request and one piece at a time; no persistent invalidation cache
or work in MIDI callbacks was introduced. Frontend profiling exercises 24 page
visits per viewport, checks one PDF request and records descriptive JS heap and
all three Learning snapshot sizes in a synthetic test artifact. JS heap excludes
GPU/canvas/process memory; existing renderer tests independently cover 64 MiB
bitmap eviction, pixel limits and cancellation.

### Legacy decisions and compatibility

Removed: the second eight-piece data table; repeated snapshot predicates;
component-owned domain types; unused Python imports and the unused summary list;
large UI blocks now owned by named pages/panels. No historical migrations, journals,
original MIDI/PDF/reference files, analyses, progress or user decisions were removed.

Retained intentionally:

- `Store.seed`, `organisation` and `learning` public imports, request-model aliases
  and component type re-exports: supported scripts/tests/external imports may use them.
- DELETE `/api/recordings/{id}`: public compatibility alias for audio-only deletion.
- Legacy eight-ID startup repair and existing catalogue markers: installed datasets
  can depend on their repair/reopening semantics.
- Historical analyses without reference fingerprints: snapshot compatibility is
  retained; reference freshness is explicitly unknown, not newly certified.
- Separate RecordingLibrary and activity playback flows: whole-take retained
  sources differ from editable interval playback and dirty-timeline disabling.
- Repeated CSS selectors/media overrides: their cascade is intentional evidence,
  and removing them offered no demonstrated benefit.
- Existing small velocity/tempo/passages/comparison/retention/capture services:
  reuse their policies rather than creating competing algorithms.

The complete baseline OpenAPI fixture passes after router extraction. There are
**no API path/payload migrations and no SQLite migrations**. Read-time eligibility
now withholds fingerprinted stale references or ineligible source/deletion states;
saved results remain unchanged. Failed timeline writes now roll back atomically.
Hardware-disabled instances do not enumerate physical MIDI outputs.

The general following test had two inherited fixture issues: an exact repeated
phrase correctly withheld a score location, and shared-piece reference edits
changed quality between viewport runs. Baseline/refactored recognition returned
identical ambiguous results. The test now uses a unique phrase on a dedicated
catalogue piece and checks the provisional label during stable following. Safety
gates and musical algorithms were not relaxed. The two inherited optional tests
that read ignored `1.mid` now use synthetic MIDI; their byte-preservation coverage
runs without private assets. The initial baseline inherited that old optional
fixture behavior; no private file was changed or added to Git.

## Before/after responsibilities

Line counts describe boundaries, not complexity or performance; moved Python
modules were formatted locally for readability.

| Original module | Before | After | New owners / retained responsibility |
| --- | ---: | ---: | --- |
| frontend main.tsx | 2,194 | 9 | Mount only; App coordinator 846, pages 132–348, dialogs 170–287 |
| frontend Learning.tsx | 1,567 | 63 | Selection; LearningWorkspace 709 plus focused controls/editors |
| frontend PracticeReview.tsx | 1,011 | 382 | Workflow coordination; panels 73–237 |
| frontend Score.tsx | 776 | 660 | PDF rendering/view; fullscreen/gesture/following hooks 41–118 |
| frontend AnalysisEvidence.tsx | 763 | 484 | Evidence interaction; presentation 71/124 and shared response types |
| frontend PassageComparison.tsx | 508 | 453 | Passage visualization; response types moved out |
| frontend style.css | 2,972 | 10 | Ordered imports; largest scoped stylesheet 771 |
| backend learning.py | 830 | 585 | Controller; definitions 96, matcher 276, profiles 51 |
| backend organisation.py | 466 | 125 | Organisation facade/orchestration; projection 72, retrieval 214, segmentation 215, analysis 301 |
| backend practice_api.py | 662 | 32 | Compatibility installer; scoped routers 34–219, models/context/uploads separate |
| backend app.py | 511 | 194 | Composition, security, lifespan and shutdown |
| backend store.py | 73 | 82 | Persistence/migrations and explicit savepoint transactions; catalogue owns seeding |

## Developer guide

| Future change | Implement it here |
| --- | --- |
| Capture, journal durability or recovery | recorder.py / midi_files.py; recorder/disconnect/recovery tests first |
| Recognition evidence or restarts | performance.py / recognition.py / segmentation.py; never Learning matcher or MIDI callback |
| Derived measurements / comparison | segment_analysis.py plus existing velocity/tempo/passages/musical_comparison services |
| Current-result policy | analysis_selection.py with explicit consumer policy and freshness tests |
| Timeline changes | timeline.py; retain revision checks, rollback, undo and Keep overlap tests |
| Audio cleanup/recovery | retention.py and MICROPHONE_RECORDING.md protocol; dedicated failure/recovery tests |
| Lesson strategy / matching / profiles | learning_definition.py / learning_matching.py / learning_profiles.py; controller lifecycle remains learning.py |
| Learning UI / editors | learning/; selector remains Learning.tsx, heartbeat/pedal state stays in the workspace |
| Workspace behavior / dialogs | pages/ / dialogs/; App owns cross-workspace recording and selection |
| Review and shared response shapes | practice/ / analysis/ / types/; pure algorithms do not import React components |
| Score gestures / following / rendering | score/ hooks / Score.tsx / existing pdfRenderer and pdfCache |
| HTTP contract | api/<domain>.py and api/models.py; compose in create_app and check the baseline contract |
| Styling | Appropriate ordered styles/ scope; check cascade, Full HD/compact DOM bounds and screenshots |

## Tooling and acceptance boundaries

Ruff starts with F/E9 correctness and import hygiene across production Python.
Prettier checks the changed frontend areas and configurations, with strict
TypeScript/Vite plus existing unit/browser suites. GitHub Actions runs separate
backend, frontend and browser jobs with synthetic fixtures and no required MIDI,
microphone, private scans, cloud credentials or personal application directory.
CI was authored and locally validated; a hosted Actions run is not claimed.

Remaining acceptance: physical AP-470/audio/touchscreen, long wall-clock capture,
real power loss, real cloud calls and exact private-scan Learning GUI cases.
Offline analysis still materializes long-session notes; the 2,000-note profile is
not a bound for multi-hour histories. Existing large OSMD bundle warning remains.
No end-to-end calibrated musical interpretation or unlimited-history scalability
is claimed. No new musical features or UI redesign were added.


Static dependency review after extraction found no domain-to-HTTP imports. The
remaining function-local microphone ↔ headphone_audio dependency is deliberately
retained: acoustic evidence calls layout/metadata helpers while microphone analysis
calls the detector. It has no import-time cycle; splitting the cohesive audio
persistence/recovery helpers would enlarge this refactor's deletion-protocol scope.


## Final executed checks

- Backend: **316 passed**; final focused import/contract/passage checks **46 passed**.
- Frontend: **44 unit tests**, strict TypeScript/Vite build, incremental Prettier.
- Ruff F/E9: production backend and profiling script passed.
- General headless Playwright: **114 passed, 9 skipped**; Learning **27 passed,
  9 skipped**; Sessions **30 passed**. These suites overlap; counts are per run.
- Persisted rendering-profile rerun: **3 passed**. Each viewport fetched its PDF
  once for 24 visits; JS heap samples about 7.35–8.22 MB, snapshot payloads
  34,250 / 127,278 / 65,610 bytes (Aeolian / Heroic / Nocturne).
- `git diff --check` and tracked-asset review passed. Source scores/recordings,
  database migrations and the running user's application were untouched.

See [Validation](VALIDATION.md#architectural-refactor--2026-11-16) for commands,
failed intermediate runs, instrumentation limits and remaining acceptance.

The CI definition is `.github/workflows/checks.yml`; Ruff installation is declared
in the optional `quality` extra. Local equivalents of its lint, format, unit,
type/build and browser commands passed. Publishing or running hosted Actions was
not part of this local task. Remaining broad `api<T = any>` compatibility for
untouched callers is retained; refactored analysis/progress/comparison/workspace
areas use explicit response contracts.
