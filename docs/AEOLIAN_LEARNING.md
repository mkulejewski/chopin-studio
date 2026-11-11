# Aeolian Harp: Paderewski pitch/attack review and lesson analysis

Reviewed by Codex on 2026-11-11. Status: **model-reviewed**. This is a complete
pitch/attack counterpart for the Learning evaluator, not an independent critical
edition or a lossless transcription of every engraving detail.

## Inputs and review method

Printed source: local `paderewski_etudes.pdf`, PDF pages 64–68 (printed pages
63–67), covering the opening pickup and printed measures 1–49. Each full page was
rendered and visually compared with staff-by-staff attack inventories from the
converted source. Larger crops were examined for the altered pitches in measures
15–16, 21–26, 29–30 and 33–34, and the closing chords/ornaments. The review checked
pitches, octaves, chord membership, attack sequence, printed measure identity and
the staff-specific pattern changes across all five pages.

The base digital file is the existing NIFC first-edition → Music21 conversion,
reference `e1419432ded045abbb9a37cdd79086ee`, originally based on Lemoine
`025-1b-LE-001.krn`. It is not labelled a Paderewski transcription. Differences
listed below are differences from that converted file; this review does not
establish whether each originated in the edition, encoding or conversion.

PDF SHA-256:
`d88745ff8b7647759e000b5be8f8bd23b016bc77aacc5a8ceced3c4fa2d67ee3`

Converted XML SHA-256:
`81c15b3e01ab1db8074974cf2b3c1df351d97fbf4345324e45931ea18c8b64d1`

The original XML, stored analysis notes, provisional reference quality and page
maps are unchanged. Learning owns a separate revision:
`paderewski-attacks-v1`. It uses printed numbering, including pickup 0, rather
than the existing follower's ordinal offset. A matching PDF hash is required to
start an attempt and to award a pass. It does not depend on a global verified
flag on the old reference.

## Correction inventory

Attack indices below are zero-based within that staff's source measure, counting
all pitched notes before chord grouping. There are 28 pitch changes and one
six-note-group repair. They are replayed by the builder and checked at scan
landmarks by tests.

| Printed measure | Staff | Source attack | Converted source | Learning counterpart |
| --- | --- | --- | --- | --- |
| 15 | 2 | 15 | Db4 | D4 |
| 15 | 2 | 21 | Db4 | D4 |
| 22 | 1 | 9 | Db4 | D4 |
| 22 | 1 | 19 | G#4 | G4 |
| 22 | 1 | 22 | G#4 | G4 |
| 22 | 2 | 20 | G#3 | G3 |
| 22 | 2 | 22 | G#3 | G3 |
| 23 | 1 | 3 | Eb4 | E4 |
| 23 | 1 | 21 | Eb4 | E4 |
| 23 | 1 | 9 | Db4 | D4 |
| 23 | 2 | 15 | Db4 | D4 |
| 23 | 2 | 21 | Db4 | D4 |
| 24 | 1 | 3 | Eb4 | E4 |
| 24 | 1 | 21 | Eb4 | E4 |
| 24 | 1 | 9 | Db4 | D4 |
| 24 | 2 | 15 | Db4 | D4 |
| 24 | 2 | 21 | Db4 | D4 |
| 23 | 2 | 9 | Bb3 | B3 |
| 25 | 1 | 3 | Eb4 | E4 |
| 25 | 1 | 9 | Eb4 | E4 |
| 25 | 1 | 21 | A4 | Ab4 |
| 25 | 2 | 2 | Ab3 | A3 |
| 25 | 2 | 4 | Ab3 | A3 |
| 25 | 2 | 8 | Ab3 | A3 |
| 25 | 2 | 10 | Ab3 | A3 |
| 25 | 2 | 18 | A2 | Ab2 |
| 33 | 1 | 12 | Ab5 | A5 |
| 34 | 1 | 15 | Ab4 | A4 |
| 16 | 2 | last cell | C2 G2 C3 G3 C3 (five attacks) | C2 G2 C3 G3 C3 G2 (six attacks at sextuplet positions) |

The repaired last lower-staff cell in measure 16 is
`C2 G2 C3 G3 C3 G2`, six attacks rather than five. The canonical onset locations
are six evenly spaced positions within that beat. Onsets help represent note
order and shared unisons; elapsed performance timing is never graded.

The final lower-staff grace pair D2/Eb2 and the trill are explicitly flexible:
D2/Eb2 lead-in and trill alternations are optional around the required main Eb2.
No trill-speed or repetition-count target is inferred from the scan. Other notes,
including the final five physical chord tones across both staves, remain required.

## Digital representation and checks

`backend/chopin/learning_data/aeolian.json` is the full machine-readable counterpart.
It stores 50 measure entries (pickup plus 49), two staff sequences, exact rational
score positions and MIDI pitches for simultaneous attack groups, plus the source,
licence, correction log, ornament policy and lesson analysis. It covers 2,209
required physical key attacks after simultaneous cross-staff unisons are merged;
optional ornament attacks are not included in that count.

`data/aeolian_review_inventory.txt` is a human-readable rendering of every required
attack, with chord brackets and exact positions. The JSON is downloadable from
Learning. It intentionally omits expression, original spacing, fingering, pedal,
and sustained melodic-voice durations: the unchanged PDF remains the displayed
score. It must not be advertised as a publication-quality engraved MusicXML edition.

Rebuild from the exact cached sources:

```bash
.venv/bin/python scripts/build_aeolian_learning.py
```

`--data-dir`, `--output` and `--inventory` select alternate locations. Hash mismatch
or an unexpected source pitch stops the builder. Neither source file is rewritten.
The default output is packaged with the backend, so ordinary Learning does not
need Music21, Verovio, OMR or network access.

Tests establish inventory integrity, complete coverage, specific visual-review
landmarks, correct whole-piece consumption and rejection of corrupt attempts.
They do not automatically compare pixels with notes and do not constitute an
independent musician's review. Further corrections must create a new reference
revision, preserve history and cause affected learning to be checked again.

## Attribution

Adapted from [First Editions of Fryderyk Chopin's Music](https://github.com/pl-wnifc/humdrum-chopin-first-editions),
pinned at `95dfb105c1669c72d10b04088566154f12d3dc1c`,
`kern/025-1b-LE-001.krn`. Copyright 2017–2021 The Fryderyk Chopin Institute;
https://nifc.pl; https://chopinscores.org.
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Changes: the pitch/group repairs above, normalization to a compact attack model,
explicit ornament policy and the added lesson plan. The private scan is not
redistributed in the repository or browser tests.

## Beginner lesson plan

Every occurrence is learned, even when a pattern returns. Self-similarity is used
to explain comparisons, not to mark later passages learned automatically.
Sections are deliberately chosen for the learning routine rather than presented
as a definitive scholarly formal analysis:

- Pickup–8: acquire the Ab arpeggio and the first departures/descent.
- 9–16: varied return, altered upper line and preparation for the middle.
- 17–25: changing lower-hand patterns, then chromatic sequences.
- 26–35: sequential expansion, bass/register changes and climax.
- 36–43: returning patterns, changed high points and descent.
- 44–49: sweeping registers, narrowing figuration and closing gestures.

The opening and return use mainly two-measure chunks. The changing middle uses
single measures, avoiding the assumption that familiar texture means familiar
notes. The coda separates the large register sweeps from the closing gestures.
Each chunk has study and recall stages. Connections grow from the beginning of
the current section; after completing later sections, cumulative recalls begin
at the pickup. The last assignment covers the complete piece.

| Chunk | Specific learning focus |
| --- | --- |
| Pickup–2 | Learn the Eb5 pickup, then the Ab/C/Eb arpeggio. The first bass is Ab1; later bass attacks rise to Ab2. Notice F5 at the start of measure 2. |
| 3–4 | Learn the G/Db inner pattern in measure 3, then the Bb5-to-Ab5 melody in measure 4. E naturals change both staves halfway through measure 4. |
| 5–6 | Anchor the low Db2 entry and higher Db3 repetitions. Measure 6 changes its bass on each beat and introduces Cb; name each six-note cell. |
| 7–8 | Follow the descending upper line into the lower register. Keep the D naturals in measure 7 distinct from the Db material in measure 8. |
| 9–10 | Rebuild the opening Ab arpeggio as a separate occurrence. Recall the low Ab1 entry rather than assuming every bass is Ab2. |
| 11–12 | Compare with measures 3–4: the inner pattern returns, but measure 11 now reaches Bb5 and C6 before G5. Measure 12 restores the E naturals. |
| 13–14 | Compare with measures 5–6. Measure 14 reaches C6 then repeats G5 over a changing F-to-E inner pattern; do not copy measure 6 unchanged. |
| 15–16 | Learn B, D and E naturals explicitly. The lower D4 is natural in the last two cells of measure 15. All four lower-staff cells in measure 16 have six attacks. |
| 17 | Learn the repeating E2–C3–Bb3–C3 lower pattern independently of the six-note upper cells. The upper melody changes to Db5 on beat 3. |
| 18 | The bass stays F2 while the upper lower-staff tone descends Bb3, Ab3, G3, F3. The upper staff changes C5, D5, E5, F5. |
| 19 | Remember G2–Eb3–Db4–Eb3 below the six-note upper pattern. The upper first note changes to F5 on beat 3. |
| 20 | The Ab2 bass returns. The upper lower-staff tone descends Db4–C4–Bb3–Ab3 while the upper melody rises Eb5–F5–G5–Ab5. |
| 21 | Learn the four changing lower cells separately: Eb2, C3, F2, then G2 entries. The last lower group has five attacks. Watch D and B naturals. |
| 22 | Both staves return to six-note cells. Learn the explicit E, D and B naturals; the last G pitches in both staves are natural, not sharp. |
| 23 | Anchor the B2 bass after the first cell. Learn the G sharps and the low E4/D4 naturals; the lower-staff B3 and D4 are also natural. |
| 24 | Anchor A2. Name C# and F# while keeping the low E4 and D4 natural. The last cell introduces G# in both staves. |
| 25 | Begin with A and E naturals and C#. Rise through the chromatic sequence, then flatten A to Ab in the last cell in both staves. |
| 26 | Alternate low Db2 and Db3 bass entries. The upper line C6–Bb5–Db6–F5 changes its inner pattern halfway through the measure. |
| 27 | Alternate Eb2 and C3 in the bass. Learn the upper Bb5–Ab5–C6–Eb5 outline and the inner-pattern change on beat 3. |
| 28 | Alternate Eb2 and Bb2 below. The upper outline Eb5–E5–F5–Eb5 requires restoring Eb after the natural. |
| 29 | Learn the shorter lower groups around F2/C3 separately. The upper staff descends Db5 to C5 before leaping to C6 in the last cell. |
| 30 | Alternate Bb1 and Bb2. The last two cells flatten F in both staves; do not reuse the unaltered pattern from measure 26. |
| 31 | Relearn the returning measure-27 pattern at this occurrence. Connect its Eb2/C3 bass alternation to the altered pattern in measure 32. |
| 32 | The lower pattern now uses A3 and C4, with F4 at the end. Learn the upper Eb5–F5–Gb5–F5 outline and A naturals. |
| 33 | Name the B and D naturals below. The third upper cell starts on A5 natural and uses B4 natural; keep its F4 inner attack. |
| 34 | The Eb bass supports widening register changes. The third cell has A naturals in two octaves; the last cell leaps to Gb6. |
| 35 | Learn the high F6 entry and the changes from D natural to Db below and F to Fb above. Finish the descent to G5 before returning to Ab. |
| 36–37 | Reconnect the Ab return to the changing upper line in measure 37: F5, Eb5, C6, G5. Keep every inner arpeggio attack. |
| 38–39 | The return repeats, but measure 39 reaches F6 rather than the previous C6. Learn this changed summit as its own landmark. |
| 40–41 | Recall the returning Ab pattern with its F5 change, then descend through the alternating Db5/C5 cells in measure 41. |
| 42–43 | Learn the low Ab1 accompaniment and alternating Bb4/Ab4 upper cells. Measures 42–43 repeat the same note pattern before the register sweep. |
| 44 | The upper staff begins with a rest, then joins the rising sweep. Read the actual sounding octaves under the ottava marking; both staves change register. |
| 45 | Connect the continuing high-to-low and low-to-high sweeps. Keep the lower staff a distinct sequence; avoid shifting either hand an octave. |
| 46–47 | After the first descending cell of measure 46, settle into the narrower repeating Ab pattern. Carry it through all of measure 47. |
| 48–49 | Recall the closing single attacks and rolled chords in any chord-tone order. The D2/Eb2 grace lead-in and trill length are flexible; the main Eb2 and final chord remain required. |

The defaults are three correct visible attempts, three correct hidden attempts,
and two correct connection/cumulative attempts. These are configurable starting
values, not a claim that a particular repetition count guarantees durable memory.
Delayed retention checks and independent starts remain planned; see
[Learning](LEARNING.md).

## Acceptance record

The software was checked with synthetic correct/corrupted full-piece sequences
and simulated MIDI through the recorder. Browser acceptance uses the actual
reviewed PDF in isolated data, landscape and compact viewports. All real-edition
assets are read locally, not acquired during a lesson. Physical AP-470 input,
actual beginner pauses/errors and real hand-coordination ambiguity remain for
user acceptance. The bounded matcher can report uncertainty and should not be
treated as an infallible musical judge.
