# Nocturne Op. 9 No. 1: digital edition pilot

Full source-derived first-edition exports are now available for Op. 9 Nos. 1–2
and Op. 72 No. 1 through the [Practice counterpart builder](RECOGNITION.md#three-complete-source-derived-nocturne-counterparts).
Those native scores/MIDI do not extend this pilot's exact Paderewski audit or
silently replace application references.

The builder writes the local study to `output/edition-pilot/index.html`. After
building it, open it in a browser. It contains a selectable digital opening, the actual Paderewski opening
scan, editable MusicXML, provenance/duration checks, and a separate full engraving
of the NIFC first-edition source. Generated assets are excluded from Git because
they include a private cached scan. No library records or application references
are modified.

The 2026-11-12 documentation review checked the builder's scope, without
regenerating assets or repeating the historical visual edition review. This is
a standalone pilot; the application does not provide this edition's full digital
score, live MIDI integration or highlights on the scan. Deferred extensions are
listed in [TODO](TODO.md).

## Edition identity

The cached NIFC Humdrum identifies itself as `009-1b-Sm-001.krn`, with publisher
`M. Schlesinger`, Paris, RISM ID `1001019586`, shelfmark `PL-Wbfc 1662/n`.
NIFC's repository describes first-edition encodings, not transcriptions of the
Paderewski/Bronarski/Turczyński collected edition. Institutional provenance alone
does not establish edition equivalence.

Source: [NIFC first-edition repository](https://github.com/pl-wnifc/humdrum-chopin-first-editions),
pinned locally to `95dfb105c1669c72d10b04088566154f12d3dc1c`.
Attribution: First Editions of Fryderyk Chopin's Music; copyright 2017–2021
The Fryderyk Chopin Institute; https://nifc.pl; https://chopinscores.org;
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Scope and findings

The adapted opening covers the pickup (printed measure 0) and printed measures
1–4 on PDF page 4 / printed page 7. Pitches and rhythms were visually compared
with that scan. This is a pitch/rhythm pilot, not a finished edition transcription:
slurs, dynamics, fingering, pedal and original spacing/layout are omitted.
Source articulations are retained. The remainder of the piece has not been
reviewed for edition equivalence.

The existing Music21 conversion introduces additional differences that should
not be attributed to the musical editions:

- Pickup left-hand rests are three quarter rests, versus Paderewski's half rest
  and quarter rest. The pilot uses the printed notation.
- Measure 2's eleven-note group uses dotted sixteenths with an 11:8 ratio and
  rounded duration 2749 at 10080 divisions per quarter. The pilot uses eighths
  with an 11:6 ratio, matching the scan and retaining exact duration.
- Measure 3 is represented as two groups of eleven. Paderewski shows a single
  22-note group. The pilot uses eighths with a 22:12 ratio, with one continuous
  beam and bracket.
- The reference's pickup is stored as follower ordinal 1. Consequently printed
  measure 3 is follower ordinal 4. The study labels both; it does not change the
  live follower or saved page mappings.

These findings do not establish pitch differences between Schlesinger and
Paderewski. They demonstrate why conversion, edition identity and musical
verification need separate checks.

Every pilot staff is checked for an exact total of three quarter-note beats in
the pickup and six in each complete bar. Divisions of 1320 give integer durations
for ordinary notes and these tuplets. Both source PDF and converted MusicXML
hashes must match the existing reviewed-source inventory before generation.

The complete NIFC engraving is rendered directly from the original Humdrum using
Verovio, preserving more notation than routing through Music21. It is provided
for inspection, not certified as Paderewski or exhaustively checked for engraving
quality. The selectable opening is a manual interaction demonstration, not live
MIDI integration or a mapping onto PDF coordinates.

## Rebuild

The script needs the project's Python environment, Poppler's `pdftoppm`, and the
optional Verovio Python package. The application itself does not acquire a new
runtime dependency. The example was built with Verovio 6.4.1.

```bash
uv --cache-dir /tmp/chopin-uv-cache pip install --target /tmp/chopin-engraving-deps verovio==6.4.1
PYTHONPATH=/tmp/chopin-engraving-deps .venv/bin/python scripts/build_nocturne_edition_pilot.py
```

Use `--data-dir` and `--output` for other local paths. The reviewed hashes and
reference identity intentionally limit this script to the inspected source.

A full Paderewski counterpart would extend this review through PDF pages 4–9,
preserving original source files, recording corrections and unresolved passages,
and checking expressive/editorial notation if that fidelity is required. Digital
note IDs make highlights straightforward on the re-engraved staves; overlaying
the original scan additionally requires page/system/measure coordinates.
