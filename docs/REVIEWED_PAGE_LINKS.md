# Reviewed measure-to-page links

Reviewed on 2026-11-03 by visually reading all 205 pages in the 41 indexed local work ranges. One page is blank; the resulting inventory contains 204 musical page boundaries. These are the exact local Paderewski scans, identified by SHA-256 in `data/reviewed_page_links.json`.

193 boundaries can be stored: 191 have a matching current reference ordinal (including work openings), and two later boundaries of Waltz B.46 have printed numbers only because that work has no symbolic reference. Eleven boundaries are withheld because the current reference cannot supply an unambiguous compatible measure. This is page-boundary and numbering review, not verification of all reference notes or real-performance following.

## Numbering

The current importer stores Partitura's ordinal bar count, which can differ from the MusicXML/printed measure label. Pickup and split bars can change the offset in the middle of a work. Links below use that stored numbering so the existing follower can consume them. For example, Nocturne Op. 9 No. 1 printed measure 13 becomes stored measure 14; Mazurka Op. 6 No. 1 printed 25 becomes 27 and printed 49 becomes 52. Waltz Op. 64 No. 2 PDF 61 starts with an unnumbered pickup before printed bar 65: it links to stored bar 66, preceding the full bar 65 at stored bar 67. An opening is linked to stored bar 1; an unprinted opening number is not invented.

## Corrections to seeded ranges

- Polonaise Op. 26 No. 2: PDF 17-27, extending the former 17-25 range. Pages 26-27 continue this work at printed measures 145 and 162.
- Polonaise Op. 40 No. 1: PDF 28-33, correcting the former 26-33 range. PDF 28 is its titled opening, printed page 24. The former opening link to PDF 26 is corrected only if it is still the original seeded link.
- Fantaisie-Impromptu: PDF 33-41. PDF 42 is a visually verified blank page and has no measure link.

## Page inventory

Each entry is `PDF page: printed measure -> stored measure`. `opening` means the work opening; `withheld` is intentionally absent from the live page map. B.46's printed-only links must be rechecked when a symbolic reference is imported.

| Work | Page links |
| --- | --- |
| Ballade “Ballade No. 1” Op. 23 (`b23`) | 7: opening -> 1; 8: 24 -> 24; 9: 44 -> 44; 10: 62 -> 62; 11: 86 -> 86; 12: 105 -> 105; 13: 122 -> 122; 14: 138 -> 138; 15: 155 -> 155; 16: 172 -> 172; 17: 187 -> withheld; 18: 206 -> withheld; 19: 223 -> withheld; 20: 243 -> 243 |
| Étude “Chromatique” Op. 10 · No. 2 (`e10-2`) | 14: opening -> 1; 15: 13 -> 13; 16: 25 -> 25; 17: 37 -> 37 |
| Étude “Tristesse” Op. 10 · No. 3 (`e10-3`) | 18: opening -> 1; 19: 24 -> 25; 20: 43 -> 44; 21: 59 -> 60 |
| Étude “Black Keys” Op. 10 · No. 5 (`e10-5`) | 28: opening -> 1; 29: 20 -> 20; 30: 37 -> 37; 31: 61 -> 61 |
| Étude Op. 10 · No. 11 (`e10-11`) | 56: opening -> 1; 57: 16 -> 17; 58: 36 -> 37 |
| Étude “Revolutionary” Op. 10 · No. 12 (`e10-12`) | 59: opening -> 1; 60: 19 -> 19; 61: 34 -> 34; 62: 50 -> 50; 63: 67 -> 67 |
| Étude “Aeolian Harp” Op. 25 · No. 1 (`e25-1`) | 64: opening -> 1; 65: 9 -> 10; 66: 19 -> 20; 67: 29 -> 30; 68: 39 -> 40 |
| Étude “Horseman” Op. 25 · No. 3 (`e25-3`) | 73: opening -> 1; 74: 16 -> 17; 75: 33 -> 34; 76: 53 -> 54 |
| Étude Op. 25 · No. 10 (`e25-10`) | 104: opening -> 1; 105: 11 -> 11; 106: 22 -> 22; 107: 39 -> withheld; 108: 64 -> withheld; 109: 89 -> 89; 110: 108 -> 108 |
| Impromptu “Fantaisie-Impromptu” Op. 66 (`i66`) | 33: opening -> 1; 34: 21 -> 21; 35: 37 -> 37; 36: 53 -> 53; 37: 71 -> 71; 38: 85 -> 85; 39: 95 -> 95; 40: 107 -> 107; 41: 119 -> 119 |
| Mazurka Op. 6 · No. 1 (`m6-1`) | 11: opening -> 1; 12: 25 -> 27; 13: 49 -> 52 |
| Mazurka Op. 7 · No. 1 (`m7-1`) | 20: opening -> 1; 21: 31 -> 32 |
| Mazurka Op. 24 · No. 2 (`m24-2`) | 42: opening -> 1; 43: 29 -> 29; 44: 57 -> 57; 45: 89 -> 89 |
| Mazurka Op. 30 · No. 2 (`m30-2`) | 56: opening -> 1; 57: 30 -> 31 |
| Mazurka Op. 68 · No. 2 (`m68-2`) | 162: opening -> 1; 163: 30 -> 31 |
| Mazurka Op. 68 · No. 3 (`m68-3`) | 164: opening -> 1; 165: 27 -> 27 |
| Nocturne “Lento con gran espressione” Op. B.49 · No. 20 · posth. (`n-b49`) | 43: opening -> 1; 44: 19 -> 19; 45: 45 -> 45 |
| Nocturne Op. 9 · No. 1 (`n9-1`) | 4: opening -> 1; 5: 13 -> 14; 6: 27 -> 28; 7: 42 -> 43; 8: 57 -> 58; 9: 72 -> 73 |
| Nocturne Op. 9 · No. 2 (`n9-2`) | 10: opening -> 1; 11: 14 -> 15; 12: 25 -> 26 |
| Nocturne Op. 15 · No. 1 (`n15-1`) | 22: opening -> 1; 23: 25 -> 26; 24: 37 -> 38; 25: 50 -> 51 |
| Nocturne Op. 27 · No. 2 (`n27-2`) | 39: opening -> 1; 40: 14 -> 14; 41: 25 -> 25; 42: 37 -> 37; 43: 50 -> 50; 44: 60 -> 60 |
| Nocturne Op. 48 · No. 1 (`n48-1`) | 65: opening -> 1; 66: 17 -> 17; 67: 37 -> 37; 68: 46 -> 46; 69: 53 -> 53; 70: 65 -> 67 |
| Nocturne Op. 55 · No. 1 (`n55-1`) | 78: opening -> 1; 79: 25 -> 26; 80: 45 -> 46; 81: 65 -> 66; 82: 83 -> 84 |
| Nocturne Op. 62 · No. 1 (`n62-1`) | 88: opening -> 1; 89: 20 -> withheld; 90: 35 -> withheld; 91: 52 -> 52; 92: 68 -> 68; 93: 81 -> 81 |
| Nocturne Op. 62 · No. 2 (`n62-2`) | 94: opening -> 1; 95: 25 -> 26; 96: 40 -> 41; 97: 50 -> 51; 98: 67 -> 68 |
| Nocturne Op. 72 · No. 1 (`n72-1`) | 99: opening -> 1; 100: 14 -> 14; 101: 29 -> 29; 102: 39 -> 39 |
| Polonaise Op. 26 · No. 1 (`p26-1`) | 11: opening -> 1; 12: 13 -> 13; 13: 31 -> 31; 14: 50 -> 50; 15: 65 -> 65; 16: 81 -> 81 |
| Polonaise Op. 26 · No. 2 (`p26-2`) | 17: opening -> 1; 18: 21 -> 21; 19: 34 -> 34; 20: 53 -> 53; 21: 69 -> 69; 22: 87 -> 87; 23: 105 -> 105; 24: 118 -> 118; 25: 134 -> 134; 26: 145 -> 145; 27: 162 -> 162 |
| Polonaise “Military” Op. 40 · No. 1 (`p40-1`) | 28: opening -> 1; 29: 14 -> 14; 30: 25 -> 25; 31: 42 -> 42; 32: 59 -> 60; 33: 76 -> 77 |
| Polonaise Op. 40 · No. 2 (`p40-2`) | 34: opening -> 1; 35: 22 -> 22; 36: 37 -> 37; 37: 56 -> 56; 38: 71 -> 71; 39: 86 -> 86; 40: 101 -> 101 |
| Polonaise “Heroic” Op. 53 (`p53`) | 60: opening -> 1; 61: 17 -> 17; 62: 31 -> 31; 63: 42 -> 42; 64: 53 -> 53; 65: 64 -> 64; 66: 74 -> 74; 67: 89 -> 89; 68: 105 -> 105; 69: 120 -> 121; 70: 130 -> 131; 71: 143 -> 144; 72: 158 -> 159; 73: 168 -> 169 |
| Prelude Op. 28 · No. 4 (`p28-4`) | 13: opening -> 1 |
| Sonata movement “Marche funèbre” Op. 35 · III (`s35-3`) | 59: opening -> 1; 60: 31 -> 31; 61: 61 -> 61 |
| Waltz “Minute” Op. 64 · No. 1 (`w64-1`) | 55: opening -> 1; 56: 29 -> 29; 57: 74 -> 75; 58: 99 -> 100 |
| Waltz Op. 64 · No. 2 (`w64-2`) | 59: opening -> 1; 60: 28 -> 29; 61: 65 -> 66; 62: 97 -> 99; 63: 127 -> 129; 64: 161 -> 163 |
| Waltz “Farewell” Op. 69 · No. 1 (`w69-1`) | 71: opening -> 1; 72: 28 -> 28; 73: 59 -> 59; 74: 92 -> 92 |
| Waltz Op. 69 · No. 2 (`w69-2`) | 79: opening -> 1; 80: 33 -> 33; 81: 72 -> 72; 82: 112 -> withheld |
| Waltz Op. 70 · No. 1 (`w70-1`) | 88: opening -> 1; 89: 23 -> 24; 90: 47 -> 48; 91: 72 -> 73 |
| Waltz Op. 70 · No. 3 (`w70-3`) | 99: opening -> 1; 100: 25 -> withheld; 101: 50 -> withheld; 102: 80 -> withheld |
| Waltz Op. B.56 · No. 14 · posth. (`w-b56`) | 103: opening -> 1; 104: 25 -> 26; 105: 53 -> 54; 106: 80 -> 81; 107: 106 -> 107 |
| Waltz Op. B.46 · No. 17 · posth. (`w-b46`) | 115: opening -> 1; 116: 27 -> 27 (printed only); 117: 51 -> 51 (printed only) |

## Reference issues

- **b23**: Reference treble part has 179 bars; bass has 264. Simultaneous notes disagree on stored measure numbers in part of the later music. Page boundaries inside that interval are withheld; the final boundary follows the conflicting part's last note.
- **e10-12**: Reference treble part has 80 bars; bass has 84. Simultaneous notes disagree after bar 80; all page boundaries precede this mismatch.
- **e25-10**: Reference treble part has 38 bars; bass has 119. Simultaneous notes disagree on stored measure numbers in the middle section. Page boundaries inside that interval are withheld.
- **n62-1**: Reference bass part has four bars containing later-time notes. Simultaneous notes disagree on stored measure numbers in the opening section. Page boundaries inside that interval are withheld.
- **w69-2**: PDF ends at printed bar 144; reference ends at 177. PDF bar 112 melody does not match reference bar 112; that final page boundary is withheld pending edition/form alignment.
- **w70-3**: PDF ends at printed bar 105; reference ends at printed bar 74. Later boundaries are withheld pending edition/form alignment.
- **w-b46**: No symbolic reference: links use printed measure numbering and cannot enable following; recheck numbering when importing a reference.

For references with differently numbered simultaneous notes, only boundaries outside the conflicting interval were retained. A finished companion part without later notes does not itself create a numbering conflict. Neither this distinction nor the numeric links certify completeness of the reference's musical content.

The withheld pages are b23 PDF 17-19; e25-10 PDF 107-108; n62-1 PDF 89-90; w69-2 PDF 82; w70-3 PDF 100-102. Their printed numbers are preserved in the manifest. In incomplete works the viewer cannot automatically visit every page; manual navigation remains necessary through the gaps. The current runtime has no per-page reference-quality block, so keep these works out of unattended automatic-following trials until their references are repaired.

Waltz B.46 has PDF pages but no symbolic reference. The selected Schott Raindrop PDF and the B.150/B.133 PDFs are unavailable in the library, so no links were invented or alternative editions assigned.

## Applying and preserving data

Run `.venv/bin/python scripts/apply_reviewed_page_links.py` for a dry run and add `--apply` to install the compatible links. `--data-dir`, `--manifest` and `--backup` are explicit overrides. Application requires exact PDF hashes, exact reference XML/stored-note fingerprints and matching seeded/reviewed ranges. Changed files or references are skipped. Existing custom calibration wins over proposed links; a conflicting page order skips the whole work. Updates are transactional and write a timestamped backup of affected page maps/ranges to the library's `exports/` directory before the first mutation. A second application makes no changes.

The script does not alter references, their quality, live settings, personal notes, mastery, recordings or PDFs. Provisional following remains an explicit user option. Reload the application after application so its cached library ranges refresh.

Validation covers manifest invariants, custom-link/range preservation, hash/reference mismatch rejection, idempotence, backup and transaction rollback. Musical performance and physical MIDI acceptance remain separate checks.

## Applied-library verification

Applied on 2026-11-03: 152 new links, one corrected seeded opening link, three range corrections and one printed-page-label correction. The ordinary library now contains exactly 193 links for these 41 works; 36 works have complete maps and five have the 11 withheld boundaries above. A normal SQLite read-only connection, including the live WAL, confirmed every saved link and range against the manifest. A second dry run proposed zero changes and reported no skipped works.

The backup is `page-links-backup-20261103T162331187696Z.json` in the ordinary library's `exports/` directory. All 42 references remain provisional; provisional following remains disabled. Five new importer/manifest tests and the seven existing focused following/tempo tests passed (12 total); compilation and `git diff --check` passed. Synthetic tests validate data application and the follower pipeline, not performance accuracy on these scans.
