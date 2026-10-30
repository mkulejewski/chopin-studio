# Continued implementation plan

All existing work committed before this continuation as f701e29.

1. Repertoire schema migration; preserve all 44 user-listed works, mastery, liking, forgotten flags, future priorities, partial-learning notes, Schott exception; composer/genre/work grouping.
2. Source acquisition with provenance: locally cache legally available Paderewski volumes and provisional machine references; record exact successes/failures rather than inventing edition equivalence.
3. Safe MusicXML/MXL and reference MIDI ingestion. Evaluate Partitura and Matchmaker; explicit reference verification and page/measure links.
4. Offline organisation with conservative activity boundaries, reference retrieval, partial matching, repeated attempts, confidence, reversible touch timeline and state-correct segment exports.
5. Deterministic alignment evidence, note mismatches, timing/velocity/pedal metrics, per-take and historical comparisons; local reports.
6. Optional audio jobs: lazy FluidSynth subprocess, cancellation, local soundfont configuration, audio audition. Optional explicitly requested OpenAI report adapter with historical evidence.
7. Live piece recognition and score following as an independent consumer; unknown/ambiguous state, manual override and confidence-gated page maps. Compare references and report experimentally validated limits.
8. Run Python, TypeScript/build, and touch browser tests per increment. Commit logical changes. Preserve originals and avoid uploading practice data except explicit configured AI requests.
