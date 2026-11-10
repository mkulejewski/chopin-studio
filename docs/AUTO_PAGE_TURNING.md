# Automatic page turning: readiness review, 2026-11-03

The MIDI-to-page pipeline exists and can be exercised with simulated MIDI. The ordinary library is not yet configured for dependable automatic turns through complete works. A PDF image cannot supply playable note/measure information by itself.

The page-map snapshot below was superseded later on 2026-11-03: the [visual page-link review](REVIEWED_PAGE_LINKS.md) installed 193 links across the 41 available works, including three range corrections. Eleven boundaries remain withheld because of incompatible reference structure/numbering. Reference quality and live settings were not changed.

## Current library snapshot

Read-only inspection of the ordinary local database on 2026-11-03 found:

- 42 symbolic references, all marked provisional. Every reference contains measure numbers, but agreement with the displayed printed edition has not been established by this review.
- 41 works with page maps, each containing exactly one opening-page link. There are no later-page boundaries to follow.
- Live recognition and automatic turning enabled; provisional following disabled; no piece pinned. Consequently these provisional references cannot currently request automatic turns.
- Waltz B.133 (Sostenuto) and Waltz B.46 have no symbolic reference.

The database, reference quality, page links, and live settings were left unchanged. This is a snapshot of the saved database, not an assertion about every future running session.

## What the implementation does

`LiveFollowing` consumes note-on events from a separate MIDI queue. It keeps up to 32 recent onset groups within a 512-note cap and runs recognition at most twice per second. The recognizer searches the reference's sequence of highest pitches per onset, then combines melody similarity with chord-pitch overlap. Reference notes carry MusicXML measure numbers; the end of the matched reference span supplies the estimated current measure. After a confident current match supplies reliable timing anchors, tempo can carry the estimated measure through recognition gaps. This continuation is labelled estimated and limited to 30 seconds or eight measures; three seconds without note input pauses it until a fresh match.

A match needs at least eight onset groups. Stable following requires three consistent same-piece estimates, forward/nondecreasing progression of at most 16 measures, similarity at least 0.75, coverage of at least 80% of the input window, and inclusion of the latest input. A page request additionally needs similarity at least 0.9 and either a verified reference or explicit provisional-navigation opt-in. Similarity is not a calibrated probability of correct position. Estimated continuation uses the last match at similarity 0.9 or above and the same reference-quality/page-map gates; its decaying similarity is not a new recognition result.

The selected PDF page is the most recent mapped boundary whose measure is no greater than the estimate. The browser polls approximately every 1.1 seconds. Manual navigation suppresses automatic movement for ten seconds; calibration also pauses it. Requests for other works do not switch the displayed piece automatically: open the recognised work or select/pin it first.

Two-page view now puts the requested page on the left even if it was already visible on the right. Manual buttons, arrow keys, swipe and pedal/voice next/previous commands advance one page. The right page previews the next page; there is no predictive early page turn.

## Preparing one work for experimental use

1. Choose the work, open its actual PDF and check its start/end page range. Pin that work in Live controls to avoid competing work identities during the first trial.
2. Compare the symbolic reference with the printed score: pickup numbering, edition differences, ornaments, repeat endings, and the measure numbering at each page boundary. Keep it provisional unless it has actually been verified. Provisional following is an explicit option for a trial, not reference verification.
3. Use **Calibrate page** to enter the first measure on every PDF page. The link must use the symbolic reference's measure numbering. Where a measure crosses a printed page boundary, the existing integer measure-to-page map cannot represent the exact mid-measure boundary; choose and document a conservative boundary or extend the map to beat/onset positions.
4. Enable recognition and automatic turns, then verify the displayed measure against a known MIDI take, followed by a live MIDI trial. Watch page transitions, rather than just whether a piece is identified. Keep manual navigation available.

## What remains before dependable playing

- Validate references and complete page maps for the works to be played. MusicXML from another edition does not automatically give the scanned PDF's pagination. Neither PDF raster preloading nor tempo inference fills in these links.
- Validate continuous position on real performances: page-boundary measures, slow passages, rubato, grace notes, rolled chords, wrong/missing notes, left/right-hand-only practice, and input latency. Measure false turns, late turns and recovery times.
- Improve continuity and ambiguity handling within a work. Current matching searches a recent phrase globally; it does not retain multiple possible positions in repeated passages or use a repeat-aware score traversal. Stability checks delay backward jumps rather than resolving repeats/restarts explicitly. Note grouping and the highest-note fingerprint are sensitive to asynchronous chords and ornaments.
- Use the latest aligned note/beat as a position anchor, rather than assuming the end of a best matching reference span is always the played position. Evaluate a dedicated online score follower with explicit repeat/restart recovery against this baseline before relying on automatic turns.
- Validate physical AP-470 MIDI input and the actual display over full practice sessions. The implemented follower uses MIDI note events; acoustic audio alone does not provide score following.

Synthetic tests exercise the pipeline and UI; they do not establish accuracy on the imported Chopin catalogue. Until those musical checks pass, automatic following remains experimental.

Tempo is always score-relative quarter notes/minute (♩), using score-onset differences divided by elapsed seconds. Bass attack density is not treated as the beat: a bass sounding once per 4/4 bar and twice per bar can produce the same tempo. Compound-time dotted-quarter tempo is a different unit; the display continues to use quarter notes.


## Conservative estimated turns and tempo checks

Unconfirmed tempo-based turns now retain one full measure in single-page view or two measures in two-page view, then require a two-second dwell. They never reverse a page confirmed by notes or advance more than one page beyond that confirmation. Confirmed requests persist through estimate ticks so browser polling cannot miss them. Note-confirmed turns keep their existing confidence/reference gates.

Local tempo slopes outside a factor of 1.75 of the phrase's median are withheld from the prediction curve. If bass and whole-score timing disagree by approximately a factor of two, the estimate is labelled ambiguous and prediction is suspended. These guards reduce repeated-accompaniment alignment errors; they do not certify tempo or the provisional references. Extrapolation uses the lower of the phrase median and the most recent retained local tempo.

## Open-score context

The currently opened score is supplied independently of the manual piece pin. Live recognition still searches the catalogue, so a recognised different work takes precedence. If identity is unknown/ambiguous, the display says “assuming open score (unconfirmed)” with no invented measure or confirmed-match confidence. A trusted prior timing anchor can still continue within its existing limits; an assumed identity by itself cannot request a page turn.

New recordings journal the open-score context at start and when it changes. Offline organisation can assign an otherwise unidentified activity to that score only if its interval has a single consistent context. The assumption is explicit, remains incomplete, and requires review before automatic audio-retention eligibility. Recordings without context markers retain the previous behaviour.


The score toolbar includes **Auto turns: on/off** in both ordinary and score fullscreen views. Turning it on also enables live recognition; reference-quality gates and manual-navigation cooldowns still apply. **App fullscreen** keeps the complete application visible. **Score fullscreen** carries floating live controls inside the fullscreen score layer, so expanding recognition does not resize the PDF. **Clear score** clears the selected score and its open-score context while leaving library files intact.
