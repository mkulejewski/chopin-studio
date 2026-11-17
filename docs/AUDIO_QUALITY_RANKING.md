# Selecting the two best complete audio takes

The automatic audio shortlist uses a musical-evidence proxy, not performance
date or pitch accuracy alone. It does not certify interpretation or musical
quality. Explicit Keep/remove choices still win. Original MIDI, journals,
analyses and session history remain separate from audio retention.

## Why the former notice appeared

The previous implementation ranked only a verified-reference pitch score with a
technical level. All ordinary installed Practice references were provisional,
so their otherwise available pitch measurements were excluded. The fallback
ranked recording health/clipping and then date. It had no combined timing,
dynamics or voicing score. The notice described an implementation limitation,
not merely stale wording.

Read-only diagnosis also found missing written dynamics in the older MusicXML
conversions of Nocturnes Op. 9 Nos. 1–2 and Op. 72 No. 1. Saved velocity curves
alone could not establish whether written contrasts were followed. A packaged
CC BY 4.0 source-derived supplement now preserves 45, 30 and 18 staff-specific
dynamic changes respectively, keyed by exact original MusicXML SHA-256. It comes
from the same pinned native encodings used by the
[counterpart builder](RECOGNITION.md#three-complete-source-derived-nocturne-counterparts).
It supplements the read-time ranking without rewriting source files, reference
notes, historical analyses or reference quality. Existing comparison evidence
can use it immediately; new analysis is needed when alignment/capture evidence
itself is absent or stale. Missing score markings are never invented from how
expressively a take was played.

Later measured Practice scan audits are tracked [per piece](LIBRARY_COUNTERPART_AUDIT.md). They add separate references with written dynamics; they do not relabel the acquired originals or regenerate historical analyses. Complete references cannot compensate for missing capture/alignment/timing evidence.

## Evidence and weights

Only complete performances or confirmed full-piece exercises enter the automatic
competition. Near-complete partials no longer qualify automatically. The analysis
must be current for the segment and reference fingerprint, have healthy capture,
unambiguous alignment, at least 80% of reference groups paired, at least 70% query
coverage, and span the first/last 10% of the reference.

| Component | Default weight | Meaning |
| --- | ---: | --- |
| Notes | 35 | Pitch F1 against the entire reference, including unmatched score material |
| Local timing | 35 | Irregularity remaining after a smooth tempo trend fitted independently inside each measure |
| Written dynamics | 25 | Relative velocity contrasts between written p/pp/mf/f/etc. levels within the same part/staff/voice |
| Recording quality | 5, when available | Clipped-sample penalty |
| Voicing | 10, when explicitly targeted | Melody separation relative to the chosen margin; absent targets are not guessed |

Available weights are normalised. Notes, local timing and written dynamics are
mandatory; the last two components are optional. Takes with different reference
identities/revisions, optional-component sets or voicing targets do not compete
automatically. Audio cleanup shows the composite and component values.

Timing uses exact-pitch adjacent onset anchors within a measure, omitting grace
measures and source-marked fermata/tempo-change measures. At least three measures
and half the eligible measures need four usable intervals each. A robust linear
trend in log seconds per score beat is fitted per measure; RMS residuals measure
irregularity. The timing score is `100 * exp(-3 * mean(residuals))`. Different
overall tempos, between-measure tempo changes and gradual intra-measure changes
are therefore not penalised as metronomic deviations. Complex intentional rubato
can still affect residuals and needs listening; the numerical scale is heuristic.

Dynamics uses median matched-note velocities for each written level, separately
within each voice. Each level needs three samples. Pairwise contrasts score
`50 + 50 * tanh(velocity_difference / 6)` in the written soft-to-loud direction.
A flat contrast scores 50, a reversed contrast below 50, and a correctly ordered
contrast approaches 100. There is no absolute p/f MIDI-velocity target and no
reward for simply playing the entire piece louder. CC88-normalised velocities
are used where captured. Device/tone calibration remains unverified.

## Selection, uncertainty and protections

The best two comparable complete takes win; manually pinned complete takes
occupy available slots as before. Extra manually kept audio remains protected.
Unscored or incomparable complete takes remain in **Needs review**, outside the
automatic competition. Scores within 0.25 points of each other at the shortlist
boundary remain for review rather than being selected by date or ID. Lower
scored comparable takes can be flagged under the existing shutdown-only cleanup
policy. Inaudible-piano detection remains a separate policy.

Provisional references retain that status. The score is a relative selection
aid, not the verified technical level or personal mastery. Hairpin shape,
phrase-level interpretation, pedal intention, articulation, acoustic tone and
unannotated fermatas/tempo changes are not fully assessed. Ranking weights and
thresholds need calibration against listening judgments. The UI must not describe
the resulting number as a calibrated overall musical-quality percentage.
