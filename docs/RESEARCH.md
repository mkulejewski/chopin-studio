# Integration research — 30 October 2026

These are inspected primary-source entry points and design decisions, not tested integrations.

## Catalogue

[IMSLP Paderewski Complete Edition](https://imslp.org/wiki/Chopin_-_Paderewski_Complete_Edition) currently lists the requested six identifiers: I Preludes #964318, II Studies #964316, VII Nocturnes #972729, VIII Polonaises #964068, IX Walzer #964071 and X Mazurkas #964319. The listing credits the complete edition's editors and PWM publication information. Its manually maintained contents are explicitly incomplete. Therefore the eight starter pieces must not be mistaken for an exhaustive catalogue or a verified mapping to particular pages. Imported documents determine actual PDF pagination.

No access restrictions are bypassed. No PDFs are downloaded or distributed by this application. Listing an edition does not decide the rights to every commentary or scan; the user-supplied importer is the implemented path.

## Symbolic processing and following

[Partitura documentation](https://partitura.readthedocs.io/en/latest/) exposes score/performance structures, MusicXML processing and alignment (match-file) representations. Planned boundary: a reference importer should convert these into a versioned local reference with explicit provisional/verified quality. Keeping a score representation is separate from establishing its correctness.

[Matchmaker upstream](https://github.com/pymatchmaker/matchmaker) provides real-time score-following methods and MIDI stream integration. Its stream and evaluation interfaces are promising for live following once a verified reference exists. It should run as a separate consumer, never own the authoritative capture journal. A follower's location confidence must not be equated with a robust multi-piece catalogue recogniser. Offline candidate retrieval, partial-excerpt evaluation and repeated-passage ambiguity still need experiments.

No new alignment algorithm was implemented in milestone 1. No recognition success is claimed from the supplied performance, which has no verified symbolic score attached.

## Piano

[Casio AP-470 user manual](https://www.casio.com/content/dam/casio/global/support/manuals/electronic-musical-instruments/pdf/008-en/w/Web_AP470-E-1A_2A_EN.pdf) and [shared MIDI implementation](https://support.casio.com/storage/en/manual/pdf/EN/008/PX770_midiimplementation_EN.pdf) are the hardware validation sources. The UI records CC64/66/67 as actual values. Mapping an incoming CC66 event into a page command is a computer-side action and cannot itself disable the local piano's sostenuto. No selective hardware-disable configuration has been verified; touch buttons or a USB pedal remain the practical fallback. No USB audio transport is assumed.

Audiveris, legal MusicXML source selection, FluidSynth/sfizz/Pianoteq rendering and AI integration still require dedicated implementation research and acceptance work.
