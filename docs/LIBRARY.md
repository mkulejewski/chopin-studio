# Scores, repertoire and digital references

Reviewed against the working tree on 2026-11-12. The catalogue contains **44 Chopin works**, grouped by composer, genre and opus/catalogue number. It is a personal starter repertoire, not a complete catalogue of Chopin or of every work in the source volumes.

## PDF scores

The library has slots for ten Paderewski volumes and a separate user-supplied Schott edition. The Raindrop Prelude retains its Schott preference. Score files are not bundled or downloaded on ordinary startup. The explicit acquisition scripts and the dated local collection inventory are documented in [Sources](SOURCES.md).

Obtain a PDF through permitted access or use your own copy. Library → the relevant volume → Import PDF opens a file chooser. Files are checked for PDF format, encryption and pages, assigned generated storage names and stored outside Git. The upload limit is 50 MiB. PDF.js and its workers are bundled locally. Imported PDFs must still be trusted documents; this is not a malware scanner.

For each piece, use its edit button to set the first and last **PDF page, counted from 1**, inclusive. Include covers in this count. The printed first-page label is separate text and is never a PDF index. Both range endpoints must be supplied together. Without a range, the viewer exposes the whole volume. Replacing a PDF may change pagination: recheck linked pieces and page maps.

Title, genre, opus, key, linked volume, notes, favourite, learning status, personal mastery, liking, forgotten flag, intention and preferred-edition text are editable. Preferred-edition text does not edit a volume's bibliographic metadata or establish edition equivalence. Page/zoom/crop and one/two-page reading state are saved independently per piece. A full bibliographic/edition editor and comprehensive volume indexing remain future work.

## Digital references

A PDF scan does not provide symbolic notes. Library → **Machine references** already supports MusicXML/XML/MXL import, source/edition/quality review, symbolic preview and corrections to the analysis-note representation. Imports begin provisional. Mark a reference verified only after musical-content review; correct page links alone are insufficient. Previous analysis-note snapshots are retained when editing notes, while the source MusicXML download and preview retain the imported source representation.

Confirmed session passages can also be saved as reusable labelled MIDI references. They can help identify a piece, but do not establish score measures or qualify as a verified score. [Implementation scope](LIMITATIONS.md)

The recorded 2026-10-30 acquisition supplied provisional MusicXML for 42 of the 44 works; B.46 and Sostenuto B.133 were missing. It also left three exact requested printed-score gaps: Schott Raindrop, B.150 and B.133. This is a dated acquisition result, not a check of today's installation. [Sources and provenance](SOURCES.md)

## Page links and Learning

Pieces with a registered Learning lesson show **Open in Learning** on their cards.
This selects that piece's saved lesson without starting an attempt. Availability
comes from the Learning catalogue, independently of the Library's editable learning
status or personal mastery. Every new Learning piece must use its Library piece ID
so this link appears automatically; see [Adding another piece](LEARNING.md#adding-another-piece).

Measure-to-PDF-page links support experimental automatic turning. Use **Calibrate page** beside the PDF or the page-map editor under Machine references. The reviewed link manifest covers exact source fingerprints and deliberately withholds incompatible boundaries. [Following guide](AUTO_PAGE_TURNING.md) · [Reviewed links](REVIEWED_PAGE_LINKS.md)

Learning uses a separate packaged, model-reviewed Aeolian Harp pitch/attack counterpart and requires the exact reviewed Paderewski PDF. It does not verify or replace the general-purpose provisional reference. [Learning guide](LEARNING.md)

## Future score work

Automatic scan-to-MusicXML/OMR integration, complete edition-faithful transcription, coordinates for overlays on the original scan, missing-source acquisition and broader catalogue/bibliographic coverage remain deferred. Existing MusicXML import, reference-quality editing, page calibration and labelled MIDI references are implemented. See the consolidated [future-work checklist](TODO.md).
