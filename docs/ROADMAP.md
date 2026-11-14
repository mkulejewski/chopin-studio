# Roadmap and implementation status

Reviewed against the working tree on **2026-11-12**. This file describes the current scope; [TODO](TODO.md) lists deferred work and [the documentation review](IMPLEMENTATION_REVIEW.md) records the evidence and corrections. The [next Learning pieces](TODO.md#next-pieces-to-implement) have a user-requested priority order recorded on **2026-11-14**; no delivery dates are assigned.

## Implemented workflows

| Area | Available now | Current boundary |
| --- | --- | --- |
| Recording | Durable MIDI capture/import/recovery; optional local microphone capture; desktop start/shutdown and disconnect handling | Physical-device, power-loss and long-session acceptance remains open |
| Library and scores | 44-work personal repertoire; PDF import/viewer; explicit acquisition scripts; MusicXML/MXL and labelled MIDI references; quality editor and page calibration | Source files are separate from the app; content/edition verification and catalogue expansion remain incomplete |
| Session organisation | Candidate piece/attempt timeline; editable boundaries, split/merge, groups, undo and MIDI/audio passage exports | Recognition, some aborted-opening splits and completeness labels remain heuristic |
| Analysis and progress | Strict pitch proxy, local tempo/velocity/pedal evidence; conservative musical comparison; staff/PDF exports; history and take comparison | A verified-reference technical level is not a musical-quality grade |
| Audio and reports | FluidSynth rendering; physical-piano playback/capture; WAV attachment; local reports and optional explicit OpenAI reports | sfizz/Pianoteq and local LLM adapters are absent; physical audio and real cloud acceptance remains open |
| Live following | MIDI phrase recognition, manual pin/open-score context, estimated continuation and gated page turns | Custom experimental follower; no repeat-aware Matchmaker integration or predictive early turns |
| Learning | Aeolian Harp visible/hidden chunks, connections, per-hand progress, manual reviews, self-assessment, note rules/corrections, live staves and pedal repeat | One approved model-reviewed lesson; pitch recall only; no spaced-review scheduler |
| Voice | Browser score-opening commands and Learning reason dictation | Browser recognition availability/privacy varies; this is separate from local microphone capture |

## Deferred development

The full checklist lives in [TODO](TODO.md). Its main themes are:

1. Extend Learning with reviewed new-piece lessons and authoring tools.
2. Add spaced/delayed review, independent starts and more flexible drill strategies.
3. Improve score-region display, guided acquisition and mistake review beyond the existing live staves.
4. Establish edition-specific references and scan coordinates, with a reviewed OMR workflow rather than unattended conversion.
5. Evaluate specialist repeat/restart following, finer page anchors and more robust ambiguity handling.
6. Add alternative renderer/provider adapters and benchmark offline processing at larger scales.

Missing PDFs/XML and unresolved page boundaries are **content/review work**. AP-470, touchscreen, audio-routing, soak and real-cloud checks are **acceptance work**. They are listed separately from absent software features.

## Historical plan

The original continuation began from `f701e29`, followed by backend commit `6cdef78` and later integrated changes. Its eight steps covered repertoire migration, acquisition, reference ingestion, offline organisation, analysis, optional audio/reports, live following and incremental validation. Those broad paths now exist. Counts such as “32 Python / 3 frontend / 14 browser tests” describe that earlier checkpoint; they are not current suite results. The chronological record remains in [VALIDATION](VALIDATION.md).
