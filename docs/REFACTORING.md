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
