# Piece recognition and repeated takes

Recognition identifies MIDI passages using symbolic sources. It does not transcribe
microphone audio, and similarity is not a calibrated probability or a performance
grade. The recording journal remains independent of recognition and alignment.

## Discrepancy investigation (2026-11-17)

The reported double performance of Nocturne Op. 72 No. 1 was stored as one long
partial activity. Read-only inspection established that a complete digital source
was already installed and that local windows identified the work consistently.
The failure involved several independent implementation limits:

- Restart detection allowed only early aborted openings and short mid-piece
  retries. It excluded full ending-to-opening returns and later abandoned runs.
- All pre-restart activities were forced partial, even when they covered the
  entire work. Each derived take now gets its own completeness check.
- One whole-activity partial alignment selected one traversal from several,
  suppressing query coverage. Long individual takes now use independently matched
  windows to support a monotonic span alignment. Unmatched input cannot supply
  a missing score opening or ending; backward windows withhold that extension.
- Provisional-reference similarities were capped before ranking, creating false
  ties. Candidate ranking and identity margins now use uncapped underlying
  `identity_similarity`. The existing reported-confidence cap, provisional status,
  technical-assessment gates and explicit provisional-following choice remain.
- Exact four-note fingerprints and an eight-reference fallback could omit the
  intended work after frequent errors. Two-note retrieval broadens the shortlist;
  an unindexed phrase searches the catalogue rather than its first eight works.
- Live rolling windows and tempo anchors could retain the previous take after a
  rewind. Confident recent 8/12/16-onset evidence can reacquire position, trim old
  notes and invalidate the previous tempo/page anchor before rebuilding stability.

New opening boundaries need independent evidence on both sides, chord support
at the opening, and a check against a continuous written passage. This keeps
ordinary written theme returns intact in covered cases. Exact short mid-piece
retry detection remains available. Ambiguous recurring passages, severe errors,
edition differences and general repeat/ornament traversal remain experimental.

These changes do not rewrite existing timelines or analyses. A user-requested
timeline rebuild uses revision/undo history and preserves Keep protections and
original MIDI/journals. Rebuild after loading the new application code to apply
the recognizer to a previously organised session. No recordings were deleted or
personal session records changed during this investigation.

## Rolled opening chords and missed retakes (2026-11-19)

A further saved-recording investigation found an opening restart that the detector rejected before its phrase matcher could examine it. The fixed-length twelve-onset maximum-pitch signature was disrupted by additional attacks, although the full opening phrase had strong chord evidence. A short repeated motif in the score also disabled the separate early-opening detector. These were structural proposal limits, not evidence that the pianist had continued the first take.

Restart proposals now use the opening chord, allowing closely spaced rolled attacks, followed by independent phrase alignment and coherent opening anchors. Anchors keep a coincidental preceding note from moving the boundary before the actual opening. Earlier abandoned attempts no longer need to reach an arbitrary fraction of the complete score. Both sides still require recognized score evidence; comparable forward-passage evidence and continuous score context withhold a split for a plausible written return. The recognizer remains experimental and can withhold uncertain cases.

Independent edge-window evidence remains available, but a repeated motif located in a disjoint later span cannot overwrite the displayed endpoint of a partial take. Such an extension requires the existing monotonic-window support. New timelines/analyses identify this behavior as `symbolic-edit-v9-chord-supported-restarts-experimental`; existing data is not silently rebuilt. Original MIDI, journals, audio and historical analyses remain separate from corrected derived results. The reported latest recording received a separate revision-checked, undoable two-take correction and fresh derived analyses; original capture hashes and historical analyses were verified unchanged. Other saved sessions were not rewritten.

## Three complete source-derived Nocturne counterparts

The installed references already contain the full works, rather than just opening
fingerprints. A separate rebuild now exports native digital scores for Op. 9
Nos. 1 and 2 and Op. 72 No. 1. It reads the pinned licensed Humdrum sources
directly with Verovio, bypassing the older Music21 engraving conversion.

| Piece | Source measure entries | Note attacks after ties | Native engraving pages |
| --- | ---: | ---: | ---: |
| Op. 9 No. 1 | 86 | 1,727 | 6 |
| Op. 9 No. 2 | 35 | 1,246 | 3 |
| Op. 72 No. 1 | 57 | 1,091 | 4 |

Measure entries include pickups, so they need not equal printed bar counts.
Each native export includes both staves, MEI, reference MIDI, SVG pages and an
ID-based attack inventory with source fingerprints. Tie continuations extend
durations rather than becoming new attacks. MIDI note-on counts agree with the
inventories for all three works. The existing MusicXML conversion is provided
separately and copied byte for byte, without replacing the original.

These are **provisional first-edition counterparts**, not fully audited Paderewski
transcriptions or new Learning lessons. Structural coverage of every measure and
inspection of all generated pages do not establish exact pitch/notation agreement
with the Paderewski scans. The existing Op. 9 No. 1 scan-reviewed pilot still
covers only pickup/printed measures 1–4. Native source problem markers remain
visible and are listed individually in each report (16, 10 and 12 respectively).
Verovio also reports mixed-beam placement and crowded-system warnings. No
reference is promoted to verified and these exports are not silently installed
as replacement app references. The recognition fixes work with existing sources.

The local viewer is `output/edition-pilot/nocturne-counterparts/index.html`.
Generated source-derived assets stay outside Git. Rebuild without opening or
changing the personal database:

```sh
uv --cache-dir /tmp/chopin-uv-cache pip install --target /tmp/chopin-engraving-deps verovio==6.4.1
PYTHONPATH=/tmp/chopin-engraving-deps .venv/bin/python scripts/build_nocturne_practice_counterparts.py \
  --data-dir "$HOME/.local/share/chopin-studio"
```

Use `--output` to choose another destination. Both cached Humdrum and converted
MusicXML fingerprints must match the pinned inputs. Verovio is an optional build
dependency; ordinary recognition does not import it or contact a network.

Source: the NIFC first-edition encodings pinned to commit
`95dfb105c1669c72d10b04088566154f12d3dc1c`, with full CC BY 4.0 attribution in every
report and viewer. See [source provenance](SOURCES.md) and the
[separate Paderewski pilot](NOCTURNE_EDITION_PILOT.md).
