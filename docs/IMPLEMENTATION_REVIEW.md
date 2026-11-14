# Documentation review against the implementation

Reviewed on **2026-11-12**, against the current working tree. All **17 pre-existing files in `docs/`** were reviewed. The README is the general introduction; [Roadmap](ROADMAP.md) summarizes available workflows and [TODO](TODO.md) is the consolidated future-work checklist.

## Verification scope

This was a source/documentation review. Backend modules, HTTP routes, frontend controls, scripts, existing test definitions and bundled data/manifests were cross-checked. Small read-only consistency checks confirmed catalogue, lesson and manifest counts. No application test suite, browser session, hardware capture, acquisition script or cloud request was run. No ordinary application database, recording, PDF or saved setting was changed or revalidated.

“Implemented” means a code path exists, with its stated gates and limitations. Existing test definitions provide supporting intent/coverage, not a new passing test result. Historical validation logs and acquisition records remain dated evidence; they do not establish the current installation's contents, runtime behavior, musical accuracy or device acceptance. External source/manual claims and current download availability were not rechecked.

## Main corrections

1. **Old future descriptions:** library/architecture/research/roadmap text still treated MusicXML import, analysis, rendering, reporting and following as future milestones. These paths are implemented; specialist following, OMR and additional adapters remain absent.
2. **Pitch scores:** a general musical `accuracy` value is withheld, but strict pitch precision, recall and F1 percentages are already saved/displayed. Automatic technical levels and production flags have stricter reference/capture/coverage gates.
3. **Audio deletion:** the two-take shortlist can remove flagged partial/surplus audio at shutdown, including flagged audio from capture-error sessions. Uncertain audio and explicit Keep choices are protected. Separately, a MIDI-guided inaudible-piano detector can remove microphone intervals immediately after analysis. MIDI survives both paths; full-session deletion is explicit.
4. **Learning plans:** per-hand progress, live comparison staves, local reference corrections, pedal repeat and learned-chunk reviews are implemented. Startup already selects learned-prefix review when available after a backend restart, without starting recording. Gap-based suggestions/configuration and spaced scheduling remain future work. Chunk masks and faithful scan overlays are absent despite the live staves.
5. **Comparison notation:** the shared renderer accepts supplied spelling/key metadata; Aeolian Learning supplies reviewed spelling and a four-flat key. Describing all comparison notation as sharp-only was outdated. Durations and voices are still regenerated, with a 1/12-quarter grid; exceptional tuplets are not faithfully reproduced.
6. **Voice scope:** browser commands open a matching score; reason dictation fills Learning correction/rule forms. Voice next/previous-page commands are not implemented, despite an old mention in the following guide. This absence is not an existing roadmap commitment.
7. **Library snapshots:** the 42-reference, ten-volume and 193-page-link counts belong to dated acquisition/application records. They are not bundled assets or assertions about every installation's current state.
8. **Acquisition reproducibility:** the reference acquisition script resolves upstream `main` at run time. It records the resolved commit in source URLs, but is not pinned to the historical acquisition commit. Reviewed builders and page-link application instead require recorded fingerprints.

## Review of each document

| Document | Finding and disposition |
| --- | --- |
| [ACCEPTANCE](ACCEPTANCE.md) | Procedures remain manual/unverified. Updated disconnect/idle behavior and added microphone cleanup, Learning, speech and isolated-browser checks. |
| [AEOLIAN_LEARNING](aeolian_harp_etude_op25_no1_learning.md) | Current revision, correction inventory and pitch-only scope agree with bundled lesson/builder. Retained as a model-review record; visual correctness was not independently rechecked. |
| [AP470_AUDIO](AP470_AUDIO.md) | Playback, optional ALSA capture, WAV attachment, cancellation and recording exclusion match code. Retained; actual piano/manual specifications and acoustic routing were not revalidated. |
| [ARCHITECTURE](ARCHITECTURE.md) | Replaced obsolete milestone-1/future-component account; corrected sync wording and documented migrations through v5, microphone/cleanup, Learning and current service boundaries. |
| [AUTO_PAGE_TURNING](AUTO_PAGE_TURNING.md) | Marked the opening-only map inventory historical, removed unsupported voice page commands and retained the experimental follower/estimated-turn limits. |
| [LEARNING](LEARNING.md) | Corrected restart/failed-continuation wording, distinguished implemented hands/live staves/startup review from deferred extensions, and documented reason dictation. |
| [LIBRARY](LIBRARY.md) | Replaced eight-work/six-volume scope and future MusicXML/reference claims with the 44-work catalogue and implemented import/review/labelled-MIDI workflow. Distinguished editable edition text from full bibliography editing. |
| [LIMITATIONS](LIMITATIONS.md) | Corrected pitch-score and page-map claims; added current microphone, cleanup, comparison and Learning boundaries; separated missing development from acceptance. |
| [MICROPHONE_RECORDING](MICROPHONE_RECORDING.md) | Corrected uncertain-take/capture-error policy and shutdown-only wording; clarified open-score assumptions for otherwise unidentified activities. |
| [MUSICAL_COMPARISON](MUSICAL_COMPARISON.md) | Deterministic strict/context comparison and local PDF export match code. Corrected spelling limitations; retained missing OMR/faithful transcription/scan-coordinate scope. |
| [NOCTURNE_EDITION_PILOT](NOCTURNE_EDITION_PILOT.md) | Builder remains an opening-only standalone pilot, not integrated live following or a full Paderewski edition. Clarified generation prerequisites and historical review scope. |
| [RESEARCH](RESEARCH.md) | Marked milestone-1 notes historical and added current implemented-versus-researched status. No upstream documentation was fetched again. |
| [REVIEWED_PAGE_LINKS](REVIEWED_PAGE_LINKS.md) | Manifest and application guards match the record. Made historical database/settings claims explicit; retained unresolved numbering and withheld boundaries. |
| [ROADMAP](ROADMAP.md) | Replaced the old continuation/checkpoint narrative with current implemented workflows and deferred themes; retained commit/test counts as historical context. |
| [SOURCES](SOURCES.md) | Preserved dated acquisition provenance and gaps; corrected the implication of pinned reproducible reruns and distinguished the separate Learning counterpart. |
| [TODO](TODO.md) | Consolidated documented deferred plans, partially implemented extensions, missing content and acceptance into separate lists; removed stale future status for existing functionality. |
| [VALIDATION](VALIDATION.md) | Preserved chronological results and added a current-source preface explaining superseded policies/layouts and configured versus executed browser coverage. No new suite result is claimed. |

## Implementation evidence

| Area | Owning sources | Existing checks inspected |
| --- | --- | --- |
| Capture, lifecycle and recovery | [recorder.py](../backend/chopin/recorder.py), [app.py](../backend/chopin/app.py), [lifecycle.py](../backend/chopin/lifecycle.py) | [Recorder](../tests/test_recorder.py), [disconnect](../tests/test_disconnect_recording.py), [idle](../tests/test_idle_shutdown.py), [shutdown](../tests/test_shutdown.py) |
| Catalogue, references and acquisition | [catalogue.py](../backend/chopin/catalogue.py), [store.py](../backend/chopin/store.py), [symbolic.py](../backend/chopin/symbolic.py), [practice_api.py](../backend/chopin/practice_api.py), [acquire_references.py](../scripts/acquire_references.py), [acquire_scores.py](../scripts/acquire_scores.py) | [Practice/reference tests](../tests/test_practice.py), [staff assignment](../tests/test_reference_staves.py) |
| Organisation and technical/context comparison | [organisation.py](../backend/chopin/organisation.py), [assessment.py](../backend/chopin/assessment.py), [musical_comparison.py](../backend/chopin/musical_comparison.py), [comparisonScore.ts](../frontend/src/comparisonScore.ts), [comparisonPdf.ts](../frontend/src/comparisonPdf.ts) | [Boundaries](../tests/test_recognition_boundaries.py), [context comparison](../tests/test_musical_comparison.py), [notation](../frontend/src/comparisonScore.test.ts) |
| Microphone and audio cleanup | [microphone.py](../backend/chopin/microphone.py), [headphone_audio.py](../backend/chopin/headphone_audio.py), [retention.py](../backend/chopin/retention.py), [jobs.py](../backend/chopin/jobs.py) | [Microphone](../tests/test_microphone.py), [retention](../tests/test_retention.py), [inaudible piano](../tests/test_headphone_audio.py) |
| Following and maps | [live.py](../backend/chopin/live.py), [tempo.py](../backend/chopin/tempo.py), [Score.tsx](../frontend/src/Score.tsx), [page-link application](../scripts/apply_reviewed_page_links.py) | [Tempo/following](../tests/test_tempo_following.py), [page manifest](../tests/test_reviewed_page_links.py) |
| Learning | [learning.py](../backend/chopin/learning.py), [learning_api.py](../backend/chopin/learning_api.py), [learning_staves.py](../backend/chopin/learning_staves.py), [Learning.tsx](../frontend/src/Learning.tsx), [lesson builder](../scripts/aeolian_harp_etude_op25_no1_learning_builder.py) | [Learning tests](../tests/test_learning.py), [Learning browser definitions](../frontend/e2e/learning.spec.ts), [hands definitions](../frontend/e2e/learning-hands.spec.ts) |
| Audio/report adapters | [jobs.py](../backend/chopin/jobs.py), [hardware_audio.py](../backend/chopin/hardware_audio.py), [teacher.py](../backend/chopin/teacher.py), [provider/render routes](../backend/chopin/practice_api.py) | [Practice tests](../tests/test_practice.py): real optional FluidSynth, mocked hardware/OpenAI contracts |
| Voice and session grouping | [voiceCommands.ts](../frontend/src/voiceCommands.ts), [ReasonDictation.tsx](../frontend/src/ReasonDictation.tsx), [sessionGroups.ts](../frontend/src/sessionGroups.ts) | [Commands](../frontend/src/voiceCommands.test.ts), [dictation](../frontend/src/reasonDictation.test.ts), [grouping](../frontend/src/sessionGroups.test.ts) |

## Consistency checks performed

- The catalogue source defines **44 works**.
- The packaged `paderewski-attacks-v2` lesson has **35 chunks, 104 stages, 50 measure entries** (pickup 0 through 49), **2,209 required physical attacks** after shared-unison merging, and key signature **−4 fifths**.
- The reviewed page-link manifest has **41 works**, **191 ready links plus two printed-only links**, and **11 withheld boundaries**. Printed-only B.46 links cannot enable following without a compatible reference.
- Local Markdown link targets, newly used section anchors, code-fence balance and diff whitespace were checked. These checks do not establish that the external URLs are currently available.

## Reading the future list

[TODO](TODO.md) lists the actual deferred extensions: additional reviewed lessons/authoring; finer score regions and acquisition aids; spaced review and drill strategies; improved error feedback; edition/OMR/scan-coordinate work; repeat-aware following and scaling; alternative renderers and local LLM adapters. It also lists missing content and acceptance separately.

Capabilities such as acoustic note transcription, a physical headphone-jack sensor, continuous Practice pause/resume, a certified musical-quality grade and voice page-turn commands are not supplied. Their absence should not be converted into a delivery promise. Existing source/research documents do not establish a scheduled commitment to implement them.
