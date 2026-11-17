# Library Practice counterpart audit

The user narrowed the 17 November 2026 request to **nine pieces**: the four already audited works, plus Polonaises Op.40 Nos.1–2, Nocturne B.49, Waltz Op.64 No.2 and Étude Op.10 No.12. Mazurka Op.30 No.2 was already among those four. **All nine now have complete model scan audits and separately installed measured Practice counterparts.** The other 31 works from the original batch are deferred by the user, not outstanding production work in this batch. B.46/B.133 remain excluded; Schott Raindrop and B.150 remain deferred.

## Completed counterparts and edition

Every counterpart was checked measure by measure on both staves against the exact local **Paderewski / Bronarski / Turczyński (PWM)** scan. PDF page numbers below are one-based. Counts are stored note events after sustained ties are joined; simultaneous independent unisons remain separate.

| Piece | Scan volume and PDF pages | Printed bars / entries | Note events |
| --- | --- | --- | --- |
| Prelude Op.28 No.4 | Preludes, 13 (printed 11) | Pickup 0–25 / 26 | 599 |
| Mazurka Op.68 No.3 | Mazurkas, 164–165 (printed 160–161) | 1–60 / 60 | 780 |
| Mazurka Op.68 No.2 | Mazurkas, 162–163 (printed 158–159) | Pickup 0–65 / 66 | 738 |
| Mazurka Op.30 No.2 | Mazurkas, 56–57 (printed 52–53) | Pickup 0–64 / 65 | 810 |
| Nocturne B.49, C-sharp minor | Minor Works, 43–45 | 1–65 / 65 | 823 |
| Polonaise Op.40 No.1, “Military” | Polonaises, 28–33 (printed 24–29) | 1–88 / 88 | 3,126 |
| Polonaise Op.40 No.2, C minor | Polonaises, 34–40 (printed 30–36) | 1–117 / 117 | 2,903 |
| Waltz Op.64 No.2 | Waltzes, 59–64 | Pickup 0–192 / 193 | 1,851 |
| Étude Op.10 No.12, “Revolutionary” | Études, 59–63 (printed 58–62) | 1–84 / 84 | 2,077 |

These are model-reviewed measured note references, not independent editorial certification or facsimile engravings. Review covers pitches, accidentals, sounding octaves, chords, attack order, rhythm/durations, ties, written small notes, marked ornaments, independent voices and crossings. Descriptors record reviewed constant dynamic levels and tempo words. Phrase slurs, fingering, hairpin endpoints, pedal interpretation, accent strength and flexible ornament realization are excluded. A verified note reference does not certify an interpretation or guarantee an available musical-quality score.

## Material corrections

- Prelude: restored the B4 tie across 12–13, edition spellings and final staff crossing; corrected converted beam/tuplet display. The shared importer now preserves the already-encoded small notes.
- Mazurkas: removed nonmatching ties in Op.68 No.3; restored trill endings and repeat endings in Op.68 No.2; corrected grace pitches and missing LH G#3 chord members in Op.30 No.2.
- Nocturne B.49: removed extra lead-in graces absent from this edition, restored the small-note pair in 57, corrected three 17-note flourishes, split the source’s combined 5/4 into printed 2/4 and 3/4 bars, and checked the final 18/35/11/13-note runs. Flexible cadenza passages are exempt from a metronomic timing comparison.
- Military Polonaise: folded the literally expanded repeat into printed bars, removed the empty inserted bar, corrected opening octave chords, restored sustained octaves in 33/57 and staff crossings. The optional second-pass grace in 25 is recorded as a variant rather than a mandatory first-pass attack.
- C-minor Polonaise: folded its expanded repeat, restored missing sustained voices/ties, corrected pitches in 68/80, the dotted-quarter voice in 66, the C-minor return and final fermatas.
- Waltz: placed the Più lento pickup in bar 64 instead of an extra rest bar, restored missing ties and the G#4 voice at 159–160, corrected bar 93 rhythm, the eight-note figure at 84 and the printed upper mordents.
- Revolutionary Étude: recovered four ending bars incorrectly collapsed into simultaneous voices in bar 80, rebuilt missing voices in 70–72/80, corrected chromatic pitches in both hands, restored ties and checked the E-natural/Db closing runs. Standalone fingerings were distinguished from actual triplet notation.

The machine-readable scope is `data/library_counterpart_audit.json`. Individual audits in `backend/chopin/reference_reviews/` contain source/scan SHA-256 values, every measure’s both-staff coverage, corrections, review date, note counts and excluded scope. Deferred inventory entries have no completed descriptor.

## Rebuild, installation and use

```sh
.venv/bin/python scripts/build_verified_practice_counterparts.py \
  --data-dir /path/to/chopin-studio-data --piece e10-12
```

Builders cover only the nine pieces listed above. Without `--apply`, the command produces corrected MusicXML and a JSON note/review inventory under ignored `output/verified-counterparts/`. It requires the exact pinned source XML and scan. Append `--apply` to install a new verified reference and adjacent review sidecar. Installation is additive, checks schema 6 and refuses edited installed notes; it neither seeds nor migrates the personal database. Original acquired files/reference rows, recordings, journals, mastery and historical analyses remain unchanged. Superseded generated exports are retained as rejected. Reapplying an identical score can refresh review metadata while preserving its saved pre-installation page-map baseline. No network requests run.

Library cards show verified/provisional/rejected counts. In **Machine references & page maps**, choose **Review reference → Scan review coverage and limits**. Equal identity evidence for editions of the same piece prefers the verified reference; stronger identity evidence still wins. Existing takes need explicit reanalysis to use the new reference. Old reports remain historical and stale-reference gates still apply. This batch adds Practice references, not Learning lessons or automatic Learning passes.

For the five references whose bar layout changed, live following uses the matched reference’s reviewed page map while the saved legacy map is unchanged. Subsequent explicit page calibration remains effective. A missing/invalid review or a different selected scan withholds those automatic turns. The saved global map is preserved. Both direct and tempo-estimated turns use the same rule. Measure-only page maps cannot express a page break inside a measure; manual navigation remains available.

## Importer and remaining limits

Partitura represents small notes as a `GraceNote` subclass. The old importer iterated only exact `Note` objects and dropped them. Rebuilt/new imports preserve grace-chord membership, attack order and ornament symbols. Tiny negative score offsets put grace attacks before their anchor and are not measured performance timing targets. Original stored references are not silently reparsed. Strict technical levels are withheld where ornament realization requires review; timing ranking excludes those measures.

Alternative repeat-expanded assessment routes remain an alignment limitation. Some engravers position mid-measure key/clef changes differently; pitches and fractional timing are explicit, but these exports do not replace the scan for reading. A complete verified reference cannot supply missing capture health, whole-take alignment, timing coverage or expressive velocity evidence. Physical piano acceptance and independent editorial review remain unperformed. Three separate Learning studies and three source-derived Op.9/Op.72 Nocturne exports retain their own distinct review scopes.
