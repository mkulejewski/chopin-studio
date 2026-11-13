# Heroic Polonaise Op. 53: section-based Learning

The lesson uses the cached Paderewski Polonaises scan, PDF pages 60–73
(printed pages 56–69), printed measures 1–181. There is no opening pickup.
All fourteen pages were inspected for form, page starts, section boundaries,
notation hazards and this proposed learning path on 2026-11-13.
This is a model-designed proposal, not a prescribed fingering or performance course.

## Completed pitch/attack counterpart

Revision **`paderewski-attacks-v1`** covers all **181 printed measures** and
**5,892 required physical key attacks**, including **82 printed grace-note tones**.
All fourteen Paderewski pages were compared with the per-measure digital pitch
inventory for accidentals, sounding octaves, ties, small notes, staff ownership
and attack order. The bundle records **103 occurrence-specific corrections or
decisions**, fourteen reviewed page ranges and no outstanding pitch-review gaps.
Both the plan and the pitch/attack reference are **model-reviewed**. This is not
independent editorial certification.

The NIFC Schlesinger encoding supplied a starting inventory, not evidence of
Paderewski equivalence. The separate [scan correction script](../scripts/heroic_scan_review.py)
checks original chords before replacing them, and the
[complete readable inventory](../data/heroic_review_inventory.txt) makes every
measure inspectable. Important resolved differences include:

| Area | Scan-based decision |
| --- | --- |
| 5, 35, 37, 39 and later returns | Restore chromatic accidentals, chord tones and sounding octaves |
| 26, 42, 47, 74, 165–166, 179 | Correct occurrence-specific chord membership |
| 46, 78, 168 | Continue the ascending scale through its staff crossing |
| 49–50, 53–54, 62–63, 97, 129, 151 | Suppress tied continuations rather than requiring duplicate attacks |
| 33–38 and corresponding returns | Correct grace-note lead-ins and require printed terminations |
| 31, 47, 79, 83–84, 91–92, 103–104, 111–112, 169 | Restore printed staff ownership for separate-hand study |
| 119–120 | Resolve the synthetic conversion bar and the actual mid-bar key change |
| 162 | Recover the complete lower-staff accompaniment |

Automatic pitch evaluation, finishing, continuation, optional mismatch restart
and visible staff comparison are enabled with the exact reviewed PDF. Manual
finishing and explicit self-assessment remain available. Live comparison remains
provisional display evidence; only the authoritative captured passage can earn
an automatic pass.

Download the JSON reference or **MusicXML attack study** from **Lesson analysis &
edition evidence**. The MusicXML is deliberately labelled **unmeasured**: each
staff displays its ordered attacks, printed grace notes and ornament symbols,
without claiming notated durations or exact coordination. Consult the Paderewski
scan for rhythm, sustain, fingering, pedal and expression. Learning does not grade
these performance dimensions.

The source scan and original XML are unchanged. The checked-in JSON is licensed
derived note data; downloaded score PDFs stay outside Git. The reproducible
read-only builder regenerates both the JSON and readable inventory:

```sh
.venv/bin/python scripts/build_heroic_learning.py --data-dir /path/to/source-library
```

Exact inputs:

- Paderewski PDF SHA-256: `b1ea18ef7892aaafe9c7aa668ecf0b137c7bc9ee37ea54a6067377351681a8b7`.
- Converted MusicXML SHA-256: `d9aaafb60e118510a992c14eb9821d6d674ddbd2e5e90a1900a4424fc3ec5703`.
- [NIFC Schlesinger encoding at the pinned source revision](https://raw.githubusercontent.com/pl-wnifc/humdrum-chopin-first-editions/95dfb105c1669c72d10b04088566154f12d3dc1c/kern/053-1-Sm.krn),
  adapted under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Attribution: First Editions of Fryderyk Chopin’s Music, Copyright 2017–2021
  The Fryderyk Chopin Institute, [NIFC](https://nifc.pl), [Chopin Scores](https://chopinscores.org).
- [Paderewski scan source](https://imslp.eu/files/imglnks/euimg/c/c3/IMSLP964068-PMLP209085-Chopin_Paderewski_No_8_Polonaises_scan.pdf).
  The app does not redistribute the scan.

The source conversion has an extra synthetic measure labelled 0 between 119 and
120. Direct scan comparison resolves it: printed 119 contains the complete
chromatic exit corresponding to 99; printed 120 begins with D#5/Fx4/D#4 above
D#3/D#2 in four sharps, then changes to four flats after its opening eighth.
The synthetic bar is discarded, the complete 119 restored and the mid-bar change
recorded explicitly in 120. Later printed labels and page links remain unchanged.

## Grace notes and ornaments

Written small-note lead-ins and terminations are required attacks. Their fractional
positions encode order, not performance timing. The parenthesized Gb4 at 21 is an
optional editorial addition; the principal upper chord remains required. Replacing
it needs an explicit personal rule.

The reference enumerates 45 local trill/short-trill occurrences, plus that one
editorial option. At each trill slot, the principal attack and printed small notes
remain mandatory; extra principal/upper-neighbour alternations are allowed only
there. Realization count, speed and ornament rhythm are not graded. This is an
explicit matching policy, not a claim that playing an unornamented principal is a
complete musical realization. A trill pitch elsewhere remains an error. No Aeolian
ornament allowance is inherited by this lesson.

## Proposed chunks and form

The chunk map stays in printed order for navigation and editing; acquisition order
is separate. Two-bar chunks suit most gestures. Four-bar groups in the octave trio
keep a recognisable melodic phrase together; shorten them with the editor if
needed. The final bar is a separate chunk. These choices yield **82 editable chunks**
and **248 assignments**, including ten boundary drills and five larger assemblies.

| Part | Printed measures | Default chunks | What to distinguish |
| --- | --- | --- | --- |
| Introduction | 1–16 | 1–2, 3–4, …, 15–16 | Chromatic gestures and preparation for the theme |
| A: first statement | 17–32 | 17–18, …, 31–32 | Main melody, bass route, chord shapes, independent starts |
| A: ornamented continuation | 33–48 | 33–34, …, 47–48 | Turns, trills, register changes and the outgoing scale |
| A: contrasting episode | 49–64 | 49–50, …, 63–64 | Repeated-note dialogue, then sostenuto at 57 and its link |
| A: return and close | 65–80 | 65–66, …, 79–80 | Returning material and the route into the trio |
| B: entrance | 81–84 | 81–82, 83–84 | Four sharps, repeated chords, quiet octave launch |
| B: first octave episode | 85–100 | 85–88, 89–92, 93–96, 97–100 | Melody above octave cells, then chromatic exit |
| B: second episode | 101–120 | 101–104, …, 117–120 | Relaunch, corresponding phrases, exit and key reset |
| C: chordal transition | 121–128 | 121–122, …, 127–128 | Four flats, moving upper voice within repeated chords |
| C: flowing development | 129–144 | 129–130, …, 143–144 | Chromatic contours, bass landmarks, trills and sextuplets |
| C: retransition | 145–154 | 145–146, …, 153–154 | Sequential easing, low-register descent, landing at 155 |
| A′: final reprise | 155–168 | 155–156, …, 167–168 | Familiar theme with the final outgoing route |
| Coda | 169–181 | 169–170, …, 179–180, 181 | Secure ending, octave signs, altered closing harmony |

These are teaching subdivisions, rather than a claim that every boundary is an
independent large-scale formal section. The introduction / A group / octave trio /
contrasting development / reprise / coda give the larger map.

## Proposed acquisition order

1. **17–32**, then **33–48**: establish the theme and its ornamented continuation.
   Learn melody, bass destinations and chord shapes separately before both hands.
2. **65–80**: compare the return while the theme is fresh. Explicitly name its
   ending and next destination. Do not assume repeated-looking bars are identical.
3. **49–64**, then **1–16**: fill in the contrasting episode and attach the
   introduction once the main-theme landmarks are reliable.
4. **Coda 169–181 early**: acquire **181**, then **179–180**, **177–178**,
   **175–176**, **173–174**, **171–172**, **169–170**. Each connection prepends
   the new chunk to the already learned ending, played in normal score order.
5. **81–84**, **85–100**, **101–120**: learn the octave trio as a separate branch.
   First map the octave cell and upper melody separately, then the chromatic exits.
   Use short relaxed sets and rests. This lesson neither requires concert tempo
   nor treats endurance as a memory test.
6. **121–128**, **129–144**, **145–154**: acquire the contrasting development,
   including independent starts at its phrase landmarks and the return landing.
7. **155–168**: consolidate the final reprise and distinguish its coda route from
   the earlier return into the trio.

Each chunk has visible study and hidden recall (default three repetitions each).
Connections grow **within that section only** (default two repetitions); the trio
is not repeatedly tested as a gigantic prefix beginning at measure 1.
Independent starts are encouraged in the guidance. Random-start scheduling and
within-measure drills are not implemented.

After the independent sections, practise ten explicit routes:
**13–20, 29–36, 45–52, 61–68, 77–88, 97–106, 117–124, 125–132, 149–158,
165–174**. They join the last phrase of one part to the first phrase of the next,
including re-entry and changed-return destinations.

Then assemble **1–80**, **81–120**, **121–154**, **155–181**, and finally **1–181**.
The whole-piece inventory has 5,892 required attacks. Op. 53 permits up to 8,000
captured attacks to leave room for ornament repetitions; longer takes return an
uncertain verdict rather than being truncated. The full inventory passes the
matching integration check, which verifies software behavior rather than serving
as independent musical evidence.

## Separate persistence and review

Choose a piece with **Learning piece**. The server remembers the last selection;
the same browser opens Learning on the next app startup after Learning has been
viewed. Each piece retains its chunks, repetition settings, selected hand,
per-hand stage/streak/completion, personal rules, reference corrections and history
independently. Existing Aeolian profiles retain their revision and stage IDs.
No schema migration is needed: profiles and attempts were already keyed by piece.

On upgrading from the earlier provisional revision, the entire old profile is
retained under `previous_profile`, including custom chunks, rules and every hand's
progress. Attempts remain historical. Routine preferences and the selected hand
carry forward, while reviewed pitch progression starts fresh. Old self-assessed
progress and rules cannot silently become evidence against changed note IDs.
The interface explains this reset. Aeolian progress is unaffected.

Switching pieces pauses and saves an active Learning take without grading it and
cancels automatic continuation. It does not stop an unrelated Practice recording.
Late requests for the previous piece receive a conflict instead of starting a
recording under the wrong piece. Restarting Studio restores selection and saved
progress without starting capture.

For this non-linear plan, **Review learned in this section** selects the acquired
contiguous span in the current branch, not every printed bar before it. During
backward coda acquisition that means the learned tail. Learned chunk buttons remain
available across sections. Review never changes the saved acquisition position.

## Review and acceptance limits

All 181 measures of the exported attack study were engraved with OSMD; selected
excerpts covering every page and the corrected notation hazards were visually
inspected. Automated checks cover scan fingerprint gating, mandatory graces,
local ornament boundaries, full-piece matching, export pitch preservation and
historical profile retention. Tests use synthetic capture and temporary data.

Independent musician review, physical piano, real beginner performances,
repeated-octave comfort, touchscreen and long-duration acceptance remain
unverified. The counterpart is complete for Learning's pitch/attack scope, not a
facsimile engraving or a rhythm/interpretation assessment.
