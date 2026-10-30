# Local score acquisition and provenance

Executed on 30 October 2026. Files live in XDG data, never in Git.

## Paderewski scans

Ten complete volumes downloaded through the normal public IMSLP → IMSLP EU flow, without authentication or restricted-download bypass: I Preludes, II Études, III Ballades, IV Impromptus, VI Sonatas, VII Nocturnes, VIII Polonaises, IX Waltzes, X Mazurkas and XVIII Minor Works. The exact URLs are recorded in `scripts/acquire_scores.py`; every cached PDF has a `.source.json` sidecar containing its URL, SHA-256, page count, download date and rights notice.

The [IMSLP collection listing](https://imslp.org/wiki/Chopin_-_Paderewski_Complete_Edition) identifies these urtext editions with its public-domain/edition notes. This app caches the requested files for the user's local library and does not redistribute them. No scans are committed or packaged in the application source.

`python scripts/index_downloaded_scores.py` fills 41 unset per-work ranges for the exact hashed downloads. The printed tables of contents and actual PDF page offsets were visually inspected; Étude bookmarks were also used. The script never overwrites existing user bounds or applies its indices to a replaced scan. First-measure page links are supplied; comprehensive measure-to-page maps still require review before automatic turning can be useful across an entire piece.

The Schott preference for Op.28 No.15 is retained. No Schott scan has been downloaded or substituted with Paderewski. The cached Waltzes volume contains B.46 but does not contain B.150 or Sostenuto B.133; those works point to a supplementary score slot instead of falsely displaying another work as their score.

## Symbolic references

40 of the repertoire works were downloaded from [The Fryderyk Chopin Institute's first-edition encodings](https://github.com/pl-wnifc/humdrum-chopin-first-editions), pinned to commit `95dfb105c1669c72d10b04088566154f12d3dc1c`. Source licence: CC BY 4.0. Full attribution:

First Editions of Fryderyk Chopin's Music; Copyright 2017–2021 The Fryderyk Chopin Institute (https://nifc.pl); https://chopinscores.org; https://github.com/pl-wnifc/humdrum-chopin-first-editions; https://creativecommons.org/licenses/by/4.0.

The downloaded Humdrum encodings were converted with Music21 into MusicXML and parsed with Partitura. Their original encodings and attribution are cached alongside the XML. Selection uses the repository's documented opus/publisher/work naming convention. The conversions remain **provisional**; their measures, repeats, ties, accidentals, voices and ornaments have not all been checked against the printed Paderewski pages. Source MusicXML is immutable; the reference review editor changes a versioned analysis representation, explicitly separate from source rendering.

Two additional provisional CC0 MusicXML references were downloaded from the score publisher Noctave: [C-sharp-minor Nocturne B.49](https://noctavepiano.com/partitions/chopin-nocturne-b49/) and [A-minor Waltz B.150](https://noctavepiano.com/partitions/chopin-valse-b150/). Their pages state the CC0 terms and underlying edition/transcription sources. They are not asserted to be Paderewski transcriptions.

Thus **42 of 44 repertoire works currently have provisional MusicXML references**. No legitimate suitable MusicXML for B.46 and Sostenuto B.133 was imported in this pass. Those missing references are explicitly shown in the library. The app accepts user-supplied XML/MXL and labelled MIDI references for future recognition; labelled MIDI does not invent score measures.

## Reproducing downloads

```sh
uv pip install -e '.[acquisition]'
.venv/bin/python scripts/acquire_scores.py
.venv/bin/python scripts/acquire_references.py
.venv/bin/python scripts/index_downloaded_scores.py
```

The first two scripts are explicit network operations, never run during ordinary startup or recording. Re-running does not replace already imported score/reference files. Failed or unavailable sources are reported; restrictions are never bypassed.
