# Nocturne Op. 15 No. 1: scan-reviewed Learning course

Choose **Nocturne · Op. 15 No. 1** in Learning or **Open in Learning** on its
Library card. Both use the existing piece ID `n15-1`. Its progress, hand selection,
routine, corrections and take history remain separate from other lessons.

The lesson follows the cached Paderewski Nocturnes volume, PDF pages **22–25**,
printed pages **25–28**. All four pages were visually inspected for the form,
page map, notation hazards and this proposed progression on 2026-11-14.
The one-quarter opening pickup is **0**; full measures run **1–74**. Measure 49
starts at the bottom of PDF page 24; page 25 starts at 50. Measures 36 and 48
change to 6/8, returning to 3/4 in the next bar.

## Digital counterpart and evidence

Revision **`paderewski-attacks-v1`** contains a **complete model-reviewed
pitch/attack counterpart**, with **1,801 required attacks** across the pickup
and all 74 full measures. Both staves of every measure were visually compared
with the four Paderewski pages for pitches, accidentals, sounding octaves, chords,
attack ordering, ties, written small notes and staff crossings.
The [readable inventory](../data/nocturne_op15_no1_review_inventory.txt) exposes every
attack. Download JSON or the **unmeasured MusicXML attack study** under
**Lesson analysis & edition evidence**. These are derived studies; the original
PDF and cached encoding are unchanged.

The cached NIFC conversion supplies the complete upper-staff starting inventory,
but its lower part stops at measure 14. The builder transcribes the complete
lower staff separately from the scans. Explicit upper-staff decisions restore
D natural / E-flat in measure 43, G-sharp in the nine-note small-note run at 68
(including the smaller repeated E), and printed staff ownership in 73–74. The
last measure has three lower-staff attacks F2/C3/A3; C4 is on an upper-staff
ledger line. The previous draft had incorrectly removed the repeated E, changed
the run to F-sharp/E, and assigned final C4 to the lower staff. Tied continuations do not become new key
attacks. Staff ownership supports separate-staff study, not prescribed fingering
or a claim that one hand must play every note on its staff.

**The plan and digital counterpart are model-reviewed.** The
[per-measure scan-review ledger](../data/nocturne_op15_no1_scan_review.json) records
all 75 audited measure identities, source hashes, decisions and inventory hashes.
The reproducible builder checks this ledger and rejects a changed transcription
until the affected measure is reviewed again. It does not generate its own approval.
This is visual model review, not independent editorial certification; a performance
by the learner is neither required nor evidence for the transcription audit.

With the exact reviewed PDF, automatic pitch evaluation, finishing, continuation,
optional mismatch restart and staff comparison are enabled. Only the authoritative
captured take can grant an automatic pass; the live display remains provisional
alignment evidence. Manual finishing and explicit self-assessment remain available.

The old `paderewski-scan-study-v1` profile is archived in the new profile, along
with its chunk map, decisions and progress; previous takes remain in history.
Routine preferences and hand selection carry over. New reviewed-reference stages
begin fresh so old manual scan-study completions do not become automatic pitch
passes. The builder never writes personal application data.

Positions are nominal display anchors, not a rhythm transcription. MusicXML does
not certify sustain, coordination, pedal, fingering, rubato, dynamics or voicing.
The scan remains the source for those dimensions.

Rebuild without modifying the library:

```sh
.venv/bin/python scripts/nocturne_op15_no1_learning_builder.py --data-dir /path/to/source-library
```

Inputs are hash-pinned; changed inputs are rejected rather than silently accepted:

- PDF SHA-256: `fbf6809027b4bd91e80864c5f43a16f78710f2f429fd234e839810ed9ddc9a6a`.
- Cached MusicXML SHA-256: `72398391f632561807898732beeeeacec32ca70ca886a3e9331dfacb4b5b1df1`.
- [Paderewski scan](https://imslp.eu/files/imglnks/euimg/1/1d/IMSLP972729-PMLP209085-ChopinPaderewskiPWM_VII_Nocturnes.pdf).
- [Pinned NIFC Schlesinger encoding](https://raw.githubusercontent.com/pl-wnifc/humdrum-chopin-first-editions/95dfb105c1669c72d10b04088566154f12d3dc1c/kern/015-1b-Sm-001.krn).
  Adapted under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  First Editions of Fryderyk Chopin's Music, Copyright 2017–2021 The Fryderyk
  Chopin Institute; [NIFC](https://nifc.pl), [Chopin Scores](https://chopinscores.org).
  The app does not redistribute the PDF.

## Chunk division

There are **37 editable chunks**, generally two measures each. The first includes
the pickup plus 1–2. These subdivisions are practice units, not claims of unique
formal boundaries. Shorten dense chunks if recall or physical ease deteriorates.

| Part | Measures | Chunks | Main work |
| --- | --- | --- | --- |
| A: opening sentence | pickup–8 | pickup + 1–2; 3–4; 5–6; 7–8 | Singing line over independent triplets; first harmonic route |
| A: decorated answer | 9–16 | 9–10; 11–12; 13–14; 15–16 | Small-note lead-ins, chromatic bass and destinations |
| A: close and stillness | 17–24 | 17–18; 19–20; 21–22; 23–24 | Related endings, cadence, fermata and preparation |
| B: Con fuoco launch | 25–28 | 25–26; 27–28 | Bass sweeps, alternating intervals, relaxed coordination |
| B: expansion and withdrawal | 29–36 | 29–30; 31–32; 33–34; 35–36 | Melody within figuration, chromatic changes, first 6/8 exit |
| B: relaunch | 37–40 | 37–38; 39–40 | Compare with 25–28; learn its different continuation |
| B: sequential climb | 41–44 | 41–42; 43–44 | Harmonic blocks, bass destinations and naturals |
| B: dissolve and return | 45–48 | 45–46; 47–48 | Tied melody, moving bass, 6/8 and release into Tempo I |
| A′: varied return | 49–56 | 49–50; 51–52; 53–54; 55–56 | New entry, seven-note run and rewritten answer |
| A′: decorated answer | 57–64 | 57–58; 59–60; 61–62; 63–64 | Compare with 9–16; distinguish the entrance |
| A′: final closing sentence | 65–70 | 65–66; 67–68; 69–70 | Nested small-note lead-in and G-sharp at 68; final destination |
| Ending | 71–74 | 71–72; 73–74 | Quiet release and the two different final arpeggios |

## Proposed acquisition order

1. **Pickup–8 → 9–16 → 17–24.** Sing the melody first; learn bass destinations
   and accompaniment separately. Coordinate slowly, listening for a sustained
   melody above even, quiet triplets. For ornaments, learn the landing note,
   then the lead-in, then reconnect the phrase.
2. **73–74 → 71–72.** Secure the ending early. After learning 71–72, connect
   **71–74 in printed order**. Name the two final harmonies and their different
   arpeggio notes; a relaxed ending is more useful than a rushed full run.
3. **49–56 → 57–64 → 65–70.** Compare each return against its opening partner.
   Explicitly learn changed notes at 49, 54–56 and 68. Recall a return from its
   own starting point before trying to reach it through the storm.
4. **25–28 → 29–36.** First play the left-hand routes and landing notes; block
   the right-hand alternating intervals; extract the melody from the dense
   texture. Add figuration in short relaxed sets with rests. Concert tempo and
   endurance are not prerequisites for memory work.
5. **37–40 → 41–44 → 45–48.** Compare the relaunch with 25–28, then learn its
   new continuation. Block the harmony of 41–44 and isolate the natural signs.
   Learn the thinning texture, meter change and soft landing at 49 as a route.
6. Practise **boundary passages**, then assemble **pickup–24**, **25–48**,
   **49–74**, and finally **pickup–74**.

Every chunk gets visible study and hidden recall, default **three repetitions
of each**, followed by **two section connections** once a previous chunk exists.
Connections grow only within the current section. The course does not demand a
run from the opening for each new storm chunk. The full proposed schedule has
**114 assignments**. Repetitions are editable. They can be earned from recorded pitch checks or
explicit self-assessment; musical interpretation remains a separate judgement.

Boundary drills: **7–10, 15–18, 23–26, 27–30, 35–38, 39–42, 43–46, 47–50,
55–58, 63–66, 69–74**. Prioritize **23–26** (stillness to storm), **35–38**
(withdrawal to relaunch), and **47–50** (storm to Tempo I). Name the next entry,
key and character before starting; do not bridge these by reflex alone.

Use independent starts at **pickup, 9, 17, 25, 29, 37, 41, 45, 49, 57, 65 and 73**.
A suggested review sequence is to revisit these later in the same session, on the
next day, and after several days, mixing quiet and storm material. This is practice
guidance; randomized starts and spaced-review scheduling are not implemented.

Musical self-checks remain separate from note recall: audible melodic line,
controlled accompaniment, phrase direction, supple releases, deliberate pedal
changes, and convincing contrast between A and B. Never force the Con fuoco
figuration through fatigue or tension. Choose a comfortable tempo and reduce the
chunk when necessary.

## Initial scan-study software validation, 2026-11-14

- Backend: **271 passed** (`.venv/bin/python -m pytest -q`); focused Learning
  coverage also passed (**88 tests**). Synthetic tests cover section ordering,
  page/meter landmarks, export preservation, exact-scan gating, separate progress,
  manual advancement and prevention of automatic passes/restarts from the draft.
- Frontend: **44 tests passed** and `pnpm build` passed.
- Isolated headless Playwright at **1920×1080**: Library links select the matching
  lesson, show its proposed progression and expose its labelled provisional
  MusicXML download. Fresh temporary data/state; hardware disabled.
- Local documentation links and `git diff --check` passed.

The initial sandboxed TestClient and browser-server readiness checks stalled;
rerunning the isolated checks outside that sandbox succeeded. Existing dependency
warnings remain (Python parser deprecations and a large frontend bundle).
These checks do not establish transcription accuracy, physical MIDI/touchscreen
acceptance or long-duration performance. The running personal app was not restarted.

## Completed visual note audit and reviewed-reference validation

Later on 2026-11-14 the note audit was completed by direct visual comparison of
both staves in all 75 measure entries with the four scan pages. The audit corrected
the nested E / G-sharp run at 68 and the upper-staff C4 at 74. All per-measure
review decisions are recorded in the ledger, and the bundle is now
`paderewski-attacks-v1`, `reference_status: model-reviewed`, with no outstanding
pitch-review gaps. This supersedes the earlier provisional-reference status.

- **92 focused Learning tests passed**, including a complete 1,801-attack matching
  check, complete separate-hand checks, rejection of omitted/wrong notes in the
  printed run, an authoritative synthetic capture earning a pass, the exact PDF
  gate, old-profile archival and detection of inventory changes after review.
- The isolated **1920×1080 headless browser check passed** for Library selection,
  proposed progression and the reviewed MusicXML download link.
- The builder reproduced the JSON and readable inventory byte for byte; local
  documentation links and `git diff --check` passed.

The visual audit supplies the musical transcription evidence. Synthetic capture,
matching and browser checks validate software integration; no performance by the
learner is needed to certify the reference. Independent editorial certification
and physical-piano/touchscreen acceptance are separate from this model note audit.
The running personal app was not restarted or its database changed during this work.
