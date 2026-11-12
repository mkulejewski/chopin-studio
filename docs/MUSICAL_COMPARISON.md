# Strict and musical-context comparison

Session review offers two deterministic comparison methods, defaulting to musical context. Neither calls an LLM or changes the original MIDI, the reference, personal mastery, or the saved strict pitch assessment.

- **Strict digital reference** marks exact missing and extra pitches against the selected digital reference. This includes octave moves, omitted chord tones and edition variants.
- **Musical context (conservative)** keeps all differences visible. Red means a likely pitch/chord error supported by a verified reference and stable local alignment. Blue means a plausible adaptation or uncertainty, not a confirmed mistake or a confirmed intentional change.

The method applies to the overlaid/stacked staff score, piano roll and discrepancy explanations. Staff notation places the played pitches on reference beats and note lengths; it is not a transcription of performance timing. The strict F1 pitch score remains labelled as strict in either method.

## Algorithm, version musical-context-v1

The backend saves the decisions with each analysis, including the reason and explanation for each differing pitch. New analyses include source note lengths/staff data and original played onset/duration data. Old analyses need to be run again for full explanations; musical mode defaults to blue when those decisions are absent.

1. Compare pitch classes (pitch modulo 12) as well as exact MIDI pitches. The same pitch class in another octave is blue: possible octave redistribution or doubling.
2. A played subset of the reference chord's pitch classes is blue: possible hand-span reduction. This can also be an accidental omission; the algorithm does not infer intent.
3. Unaligned score groups, nearby grace-note material, possible short ornaments, nearby reference pitches and small pitch substitutions remain blue.
4. Red additionally requires `reference_quality == verified`, retrieval confidence at least 0.85, and at least two matching pitch-class anchors on each side within three groups. Passage edges, unlocated surrounding material and neighbouring onset gaps over eight seconds do not support red.
5. Within that context, chords with at least three expected and played pitch classes, at least two new played classes and at most 34% expected-class overlap can be marked likely wrong chords. An unrelated substitution can be marked a likely wrong pitch after the ambiguity rules above have been checked.

These are conservative heuristics, not full functional-harmony analysis or evidence that all editions and intentional reharmonisations have been excluded. A reference being verified must mean its musical content has been reviewed; page-link verification alone does not qualify. The current library's provisional references will generally keep musical differences blue. Confirmed personal variants could later be stored per piece and measure rather than inferred anew; this version labels plausible adaptations but does not create an approved personal edition automatically.

## Timing

Compare elapsed recording time per score beat between matched pitch-class anchors. Flag a local interval only when at least four neighbouring intervals within four groups are available, the neighbours' maximum/minimum ratio is at most 1.8, and the interval is over 4 times or under one quarter of their median. Uniform tempo scaling and smooth rubato are left alone.

Timing flags stay blue, with their recording time, measure, ratio and explanation. An isolated large interval can still be a pause, fermata, repeat/alignment problem or deliberate phrasing. MIDI alone cannot certify a red rhythm error without additional reliable score annotations or a chosen practice-tempo target. Unaligned played groups remain separately counted, not silently classified as wrong notes.

## Reading and navigating the comparison

The activity editor and Analyse activity button appear before the analysis. Previous/Next notes navigation appears immediately below the staff comparison and above the piano roll, updating both views together.

Eighth notes and shorter use explicit beams in both layers. The compiler preserves reference beam groups and source voice identity where those metadata are available; otherwise it groups contiguous short notes by metrical beats, including compound subdivisions. Quarter notes retain normal separate stems. Source beaming is shared by screen notation, MusicXML and PDF export. Existing saved analyses use beat-based grouping until analysed again to load their reference's beam and meter metadata.

## Reference staves and PDF export

The comparison uses an explicit display-staff assignment while retaining the original part and staff numbers. Two separate MusicXML parts can both use local staff 1; reference G/F clefs identify the treble/bass roles. Within a grand-staff part, the source staff numbers remain authoritative even across clef changes. Two single-staff parts with the same clef retain their source order. When XML is unavailable, a two-part register inference is labelled as inferred. Old saved analyses must be run again to include the resolved staff metadata.

Played notes inherit the matching reference note's staff. For an octave substitution, the matching reference pitch class takes precedence over the nearest absolute pitch, keeping a relocated bass note in the reference bass staff. MIDI does not identify physical hands; ambiguous unisons and unfamiliar extra pitches still require a best-match assignment.

**Download full comparison PDF** engraves the entire selected activity as an A4 PDF using the chosen comparison method and overlay/stacked/reference/played layout. Screen pagination, zoom and measure filters do not trim the exported activity. Colours, measure labels, both staves, a comparison legend and page numbers are included. Engraving and PDF conversion run locally in the browser; no external conversion service receives the recording. Long exports show progress and can be cancelled. The MusicXML download beside it continues to cover the displayed passage.

## Reconstructing edition-specific digital references from scans

A strict **musical-content counterpart** of a particular PDF is feasible through optical music recognition (OMR) plus correction and verification. Automatic lossless reconstruction, or pixel-identical re-engraving from MusicXML, is a different and much stronger claim and is not provided by this project. The current comparison renderer regenerates voices and rounds durations on a 1/12-quarter grid; it cannot faithfully re-engrave the scan's 11- or 22-note tuplets. It preserves supplied pitch spelling and can use a key signature; where those are absent, the default spelling is sharp-based. Aeolian Learning supplies its four-flat key and reviewed spellings, including matched played notes. A fully faithful edition comparison would retain the source MusicXML notation structure and attach performance annotations to it. The original source MusicXML remains separately preserved on import.

The local Nocturne Op. 9 No. 1 opening is a clear printed scan, but already contains 11- and 22-note tuplets, accidentals, grace notes, multiple voices, ties, fingering and pedal annotations. Those features make unattended conversion unsuitable as evidence of exactness. The current Audiveris limitations explicitly exclude tuplets other than triplets and sextuplets and document problems with opposed stems. A conversion experiment would need manual reconstruction of unsupported notation, not just an import that reports success.

A practical future workflow for the Paderewski volumes or another uploaded scan:

1. Preserve the exact PDF and hash, selected work/page range and edition metadata. Retain the scan as the visual authority.
2. Run a local OMR engine on a small representative excerpt before processing a volume. Audiveris accepts printed images/PDFs and exports MusicXML; keep its editable OMR project too.
3. Correct and compare pitches, accidentals, durations, voices, ties, tuplets, ornaments, repeats, alternate endings, ossias and measure numbering against every relevant system. A notation editor can handle structures unsupported by the OMR engine. MIDI playback and measure/voice duration checks help find problems, but are not proof of completeness.
4. Import the corrected MusicXML as a separate edition-specific reference. Add PDF page/system/note links and per-measure verification, rather than treating the existing provisional references or reviewed page boundaries as fully verified scores.
5. Mark it verified only after musical-content review; retain revisions and unresolved measures. A useful comparison reference can focus on notes, rhythm and form before reproducing all fingering/dynamics/layout.

There is no OMR engine integration or automatic scan conversion added by this change. Existing MusicXML import and symbolic preview remain the route for importing an externally corrected transcription.

Current source audit: 2026-11-12. The separate Aeolian Learning attack counterpart
and live staves do not provide a general OMR pipeline or note-coordinate overlays
on scanned PDFs. The consolidated deferred work is in [TODO](TODO.md).

Sources checked 2026-11-06:

- [Audiveris handbook](https://audiveris.github.io/audiveris/_pages/handbook/)
- [MusicXML export](https://audiveris.github.io/audiveris/_pages/tutorials/quick/export/)
- [Current limitations, including tuplets and opposed stems](https://audiveris.github.io/audiveris/_pages/reference/limitations/)
- [Piano-score correction example](https://audiveris.github.io/audiveris/_pages/guides/ui/ui_examples/moonlight/README/)
- Existing local numbering/content issues: [reviewed page links](REVIEWED_PAGE_LINKS.md).
