# Learning: memorizing notes separately from performance

Learning is a separate workspace with per-piece profiles. Étude Op. 25 No. 1,
Aeolian Harp, uses the exact cached Paderewski Études scan and a model-reviewed
pitch counterpart. The Heroic Polonaise Op. 53 has a complete model-reviewed
pitch/attack counterpart for all 181 printed measures and a section-based plan.
Both support automatic pitch checks. See [the Heroic lesson](heroic_polonaise_op53_learning.md).
Nocturne Op. 15 No. 1 adds a [Paderewski scan-study course](nocturne_op15_no1_learning.md)
with a complete model-reviewed pitch/attack counterpart and automatic pitch
checks against the exact reviewed scan, alongside explicit self-assessment.
All lessons begin independently of the Library's personal mastery and Practice history.

Piece-specific files use a shared descriptive stem: `aeolian_harp_etude_op25_no1`,
`heroic_polonaise_op53`, or `nocturne_op15_no1`. The pattern is
`nickname_genre_op<number>_no<number>`, omitting the nickname or piece number when
absent. Bundled references, review inventories, scan ledgers, builders, lesson
documentation and downloaded references use these stems, with descriptive suffixes
such as `_scan_review` or `_paderewski_attacks`. Stable catalogue IDs (`e25-1`,
`p53`, `n15-1`) continue to identify saved progress and history.

Choose **Learning piece** to switch. The server saves the last choice; after
Learning has been viewed, the same browser opens Learning at the next startup.
Library cards for available lessons also have **Open in Learning**, which selects
that piece and opens its saved Learning workspace without starting capture.
Each piece keeps its routine, chunks, selected hand, per-hand progression,
corrections, personal rules and attempt history separately. Switching saves any
active Learning take without grading it and cancels its pending continuation.
Restarting the app never starts capture automatically.

Reviewed against the working tree on 2026-11-13. The detailed deferred list is
below; the consolidated project checklist is in [TODO](TODO.md).

Open **Learning**, connect MIDI, and start an attempt. The initial routine uses
three consecutive correct visible attempts, three correct hidden attempts and two
correct connection attempts. Change these in **Edit routine & chunks**. Learning
always records MIDI only; it neither opens the microphone nor renders audio.

In Aeolian Harp, a chunk has visible study and hidden recall stages. Later chunks are connected
cumulatively from the start of their section. Each section after the first ends
with a cumulative recall from the pickup. The final stage covers the entire piece.
The default 35 chunks yield 104 stages. The initial lesson analysis is recorded in
[the Aeolian review](aeolian_harp_etude_op25_no1_learning.md).

A pass requires every assigned attack, the correct octave and no unexplained
extras. Notes remain ordered within each staff; coordination between the staves
is flexible. Chord tones can be rolled in any order. A shared notated unison is
one physical key attack. The matcher does not receive timestamps and cannot grade
tempo, duration, rubato, velocity or pedal. MIDI cannot identify physical hands.
This is note recall under these conditions, not performance readiness.

The complete passage is evaluated, including both boundaries. A fixed-size beam
search compares pitch sequences; if ambiguous exact paths exceed its limit and no
complete zero-edit path survives, the result is uncertain rather than a pass.
Discrepancy localization is a best alignment and may need review in repetitive
material. An attempt longer than the lesson's attack limit asks for a shorter
passage rather than truncating it: 6,000 for Aeolian, 8,000 for Heroic (5,892
required attacks plus room for ornament repetitions). Aeolian's closing D2/Eb2
trill and Heroic's enumerated trill/short-trill slots have explicit local policies;
no blanket ornament exemption applies elsewhere. Heroic's printed grace notes
are required, apart from the parenthesized editorial Gb4 at 21. Trill realization
count and speed are not graded.

**Automatic finish** recognizes a complete correct passage, waits for key release
and 1.5 seconds to settle, then saves and evaluates the authoritative MIDI journal.
Release is an attempt-boundary aid, not a duration grade. Long thinking pauses do
not end incomplete attempts. Use **Finish & evaluate** for mistakes, an omitted
ending. Ordinary Learning repetitions are not automatically segmented: use **Finish &
evaluate** to grade one or **Restart take** (also available through the middle
pedal) to save it without grading and immediately start again. Reviews instead
default to [measure retries](#measure-retries-in-review).

**Automatic continuation** starts another attempt after a two-second result
interval after a successful or explicitly self-assessed take, advancing stages
when their configured consecutive-pass count is met. Failed takes wait for review.
Use **Pause learning** to stop the countdown or save an unfinished attempt. There
is no completion-by-silence rule. The server pauses after 15 seconds without a
Learning heartbeat; switching away or hiding the browser also pauses. Progress
survives refresh and restart, but interrupted attempts do not earn passes. There
is no automatic recording restart after a backend restart.

**Peek at score** marks an active hidden attempt assisted. It stays open when
restarting the current take with the button, middle pedal or automatic retry.
These retakes retain assisted status, even if you subsequently hide the score;
finish or pause and start a fresh attempt for unassisted recall. Finishing,
pausing, changing hand or assignment, and starting a fresh attempt reset peek
visibility. Assisted hidden attempts do not count toward advancement. The PDF canvas is removed from the visible/accessibility DOM during hidden
stages. The assigned PDF pages still render into the bounded, detached canvas
cache in the background, including when Learning opens directly into recall.
Peek and return to visible study reuse warmed pages; a new page or viewport
may still need rendering, and revealing before preload finishes can still wait. Visible study is meant to use the score. Consulting it between attempts
is allowed. Full-page PDF navigation, zoom, fit and fullscreen are supported;
only the assigned chunk is evaluated. Symbolic preview and experimental live
following are not used by Learning. The reviewed scan hash gates starting and
passing: replacing the PDF with another edition requires new review.

**Overrule error** applies to one missing expected note occurrence. Save either an
omission or a replacement pitch with your reason. Octave and accidental spelling
can be entered as `C4`, `F#4` or `Bb3`. A wrong-pitch substitution normally produces
a missing expected note and an extra observed note; overrule the expected note
with your intended replacement. This is a personal adaptation, not a correction
to the shared score. Rules apply to later chunk connections, can be revoked, and
are bound to the lesson revision. The affected chunk and all dependent later
stages need fresh attempts. Earlier unaffected progress and all historical
recordings/results survive; automatic pitch verdicts are never overwritten.

Chunks can be split or merged within the six reviewed sections. Ranges must
cover pickup 0 through printed measure 49 exactly once, with no gaps or overlaps.
Changing ranges restarts progression, retaining attempts and personal note rules.
Changing repetition settings resets only the current streak. Restarting the
lesson also preserves attempts and note rules. Deleting a recording through the
normal Sessions controls leaves its Learning result but removes its MIDI link.
Learning capture is tagged separately and is not automatically fed into generic
Practice analysis or automatic performance-level updates.

## Section-based Heroic progression

Op. 53 uses 82 chunks across 13 teaching sections, with 248 assignments. It starts
with the main theme at 17–32, compares 33–48 and 65–80, fills in 49–64 and the
introduction, then learns the coda backwards. The octave trio, development and
final reprise follow as independent branches. Connections grow within a section;
ten explicit boundary drills and five assemblies join the form afterward.
There is no repeated cumulative test from measure 1 after every new part.
The plan and exact proposed ranges are in [HEROIC_LEARNING](heroic_polonaise_op53_learning.md).

The exact PDF hash gates starting and passing. The reviewed counterpart supports
automatic evaluation, finish, optional mismatch restart and visible staff
comparison. **Count take as remembered** records your judgement separately from
the automatic verdict. JSON and an explicitly unmeasured MusicXML attack study
are downloadable under **Lesson analysis & edition evidence**; the scan remains
the source for rhythm, sustain and expression.

Upgrading the earlier provisional Heroic profile retains its entire state under
`previous_profile` and keeps all attempts historical. Routine preferences and the
selected hand carry forward; reviewed progression starts fresh, with a notice in
the interface. Old self-assessed progress and old note rules do not become
verified pitch evidence. Aeolian progress retains its original revision.
For non-linear lessons, learned-span review covers the current section's acquired
range, including a learned tail during backward coda study. Individual learned
chunks across sections remain reviewable.

## Adding another piece

Every newly added Learning piece must also have an **Open in Learning** button
on its Library card. Register the lesson in the Learning catalogue with the same
piece ID as its Library entry; the Library derives its buttons from that catalogue.
Verify that the button opens the intended lesson, including when another lesson
was previously selected.

Every proper Learning piece must receive in-depth model (or equivalent human)
analysis of structure, exact edition, boundaries, exceptional notation and a
beginner learning path. Musical-content review and lesson-plan review are
separate responsibilities. Page-map calibration alone is insufficient. The
current API declines pieces without an explicit reviewed lesson plan; it does not silently
generate a provisional plan. A future algorithmic proposal must be visibly
flagged **provisional**, and must not earn trusted automatic advancement before
edition review. Reference changes require a new revision and fresh affected
progress; old evidence remains historical.

## Deferred features

- [ ] Chunk-only PDF regions/masking, faithful digital excerpts and overlays on
      the original scan. Passage-scoped live comparison staves already exist.
- [ ] Within-measure and note-level chunk boundaries; overlapping boundary drills.
- [ ] Dedicated guided note-by-note acquisition with prompts (separate from tests).
- [x] Separate right-hand and left-hand practice, plus both-hands recall.
- [ ] Individual voices within a staff; the hand selector already isolates staves.
- [ ] Random-start scheduling and general editable alternative connection strategies.
      The Heroic plan already has independent sections and backward coda acquisition.
- [ ] Delayed retention checks, spaced review and a due-for-review map.
- [ ] Gap-based review suggestions and configurable startup review. Learned-prefix
      review after backend restart is already selected when learned chunks exist;
      it does not measure time away or start a recording automatically.
- [ ] Adaptive chunk splitting and workload suggestions.
- [ ] Harmonic annotations, fingering notes and silent study tasks.
- [ ] Optional MIDI demonstration, with playback excluded from evaluated input.
- [ ] A lesson authoring/review interface and explicitly provisional algorithmic plans.
- [ ] Automatic failed-attempt segmentation, richer substitution explanations and
      evidence playback directly from each discrepancy.
- [ ] Optional elementary rhythmic-order checks; no rhythm grading in this version.

Current whole-measure chunk editing, selected learned-chunk review, local
reference corrections, self-assessment and separate-hand progress are implemented
and should not be treated as pending work.

## Validation

Backend tests cover full-piece recall and deliberately bad variants, polyphony,
unisons, rolled chords, trill scope, authoritative capture failures, peeks,
consecutive-pass resets, advancement, source gating, edition-bound personal rules,
chunk coverage, pause and restart. Real-edition browser tests cover the PDF, hiding,
auto finish, peek, note overrule, resume and leaving Learning in two viewports.
These use simulated MIDI and isolated data. Actual piano input, real imperfect
beginner performances, all hand spans and real-world error localization still
require user acceptance. Model score review is not independent editorial certification.

### Score-centered fullscreen

Learning has one persistent score workspace. Enter **Score fullscreen** from its
page toolbar, then start, finish or pause attempts there. Visible repetitions,
hidden recall, peeking and stage changes all remain inside that same fullscreen
workspace; only the notation is removed during recall. The attempt controls,
current measures, repetition count, result feedback and fullscreen exit remain
available. Exiting score fullscreen returns to app fullscreen when that was
entered first. Passage guidance is collapsible so the score has more space.

### Counting a take as remembered

After an accidental-key error, choose **Count take as remembered** on the finished
result. This applies your memory judgement to that take, restores the streak that
existed before it, and counts one successful repetition. It can advance a stage.
The automatic pitch verdict and all discrepancies remain unchanged and visible;
history labels it self-assessed. It does not create or change personal note rules.
The operation is idempotent, applies only to the latest finished unassisted take
in the unchanged lesson, and requires intact capture and the reviewed score.

By default, failed takes wait for review rather than automatically starting another take.
The optional auto-restart-on-mistakes setting is described below.
Successful and self-assessed takes continue after a two-second break when automatic
continuation is enabled.

**Next stage** advances one assignment by your own assessment without requiring
all configured repetitions. It records a separate self-assessed stage event.
If a take is recording, its MIDI is saved as a paused take before advancement;
it is not graded correct. The current streak starts fresh in the next stage.
Repeated delivery of the same stage request cannot accidentally skip two stages.
The button works inside score fullscreen as well as the normal Learning view.

The shared PDF viewer also has **First score page** in both Practice and Learning.
It returns to the selected piece's opening page (for Aeolian Harp, PDF page 64),
resets panning and preserves zoom. It counts as manual navigation for automatic
page-following override purposes.

### Side-by-side score layout

Learning uses two columns in normal and score-fullscreen views: a full-height
score sits on the left, occupying about two-thirds of the space by default; the
current chunk, repetition status, feedback and controls occupy the right third.
The divider is adjustable and its position is saved. The controls panel scrolls independently, so feedback
and note-rule forms do not reduce the page height. Learning opens with one page.
**Two-page view** remains optional and places both pages in the same score area,
so the notation is smaller. Score rendering uses narrow margins in Learning to
make the available page larger. Practice keeps its existing viewer layout.

**Restart take** is separate from Finish & evaluate. It saves the abandoned MIDI
without evaluating it and immediately starts a new take of the same assignment,
with no review break. A restart is neutral: it neither increments nor resets the
correct-attempt streak. Restarting a take while peeking keeps the score open and
retains assistance; stopping and starting afresh clears the peek. Restarted takes
remain labelled in history. In reviews, the primary button is **Retake last measure**;
**Restart whole review** remains available explicitly.
Paused/abandoned takes do not receive misleading missing-note error lists.

**Automatically restart takes on mistakes** is an optional setting in
**Edit routine & chunks**, off by default and saved with the routine. A definite
pitch or note-order mismatch restarts the same assignment once all keys are
released. It works independently of automatic finish and continuation, including
ordinary visible and hidden recall. Reviews use the separate, default-on measure
retry option instead. The interrupted take's MIDI is saved and labelled
as automatically restarted; learning position and the correct-attempt streak stay
unchanged. An exposed score and its assistance flag stay with an immediate retry.
Pause learning still stops recording and prevents further automatic starts.

Detection uses zero-edit prefixes of the reviewed reference, selected hand and
approved note rules, allowing rolled chords and flexible ordering between hands.
Pauses, note duration, tempo and unplayed trailing notes never trigger a restart.
A skipped note is detectable only when a later attack no longer fits any valid
prefix. Ambiguity beyond the matcher limit disables automatic restarts for that
take; capture faults and an unreviewed edition also prevent automatic restarts.
The provisional live staff display does not drive this setting or grant a pass.

### Adjustable score-first split

The score now sits on the **left** and defaults to roughly two-thirds of the
workspace; the controls occupy the right third. The middle divider can be dragged
with a mouse or touch. Its position is saved in this browser and reused after
reload, in normal and fullscreen views. Minimum pane widths keep the controls
usable on narrower displays. Focus the divider and use Left/Right arrows to adjust
(Shift makes larger steps), Home/End for the limits, or Enter to reset. Double-click
also restores the default split. The page stays fitted to the available height,
with blank side padding when appropriate, rather than stretching the notation.

### Previously learned chunks review

Use **Review learned chunks** to record a manual review from the pickup through
all consecutively learned chunks. A chunk is learned after its hidden-recall stage
has been completed, either by successful takes or explicit self-assessment. The
review button starts a MIDI-only take immediately. **Include the current chunk**
optionally extends the review to the passage currently being learned; without it,
uncompleted material is excluded. Initially there is nothing to review unless you
include the current chunk. A completed lesson can review the whole piece.

Review uses the same full-passage pitch evaluation, personal note rules, score
viewer, peek, immediate restart and finish controls. It has no repetition quota
and never changes the saved learning position, correct-attempt streak or completed
stages, regardless of success, mistakes or pausing. Reviews are saved separately
in take history. They do not automatically repeat. **Return to learning**, beside
**Start review** in the main attempt controls (also available during recording),
stops and saves an active review and restores the original assignment and streak.
Review is temporary. After a backend restart, Learning defaults to review from the pickup
through the last consecutively learned chunk, without starting a recording. Press
**Start review** when ready, or **Return to learning** to resume the saved assignment.
With no learned chunks, the current lesson remains the default. Leaving review
stays in normal Learning for the rest of that app run, including subsequent visits.

Future plans (not implemented): gap-based review suggestions/configuration and
spaced/due-for-review scheduling. Startup review selection described above is
already implemented and is independent of elapsed time away.

### Daily Learning entries in Sessions

Sessions combines Learning takes into one **Learning [piece] Session** per piece
and local calendar day, including review and restarted takes. Each collapsed entry
shows the number of takes, combined recorded time (excluding breaks), date, opus
and recording issues. Expand it to open an individual take, export its original
MIDI or delete only that take. Returning from a take reopens its daily group.
Grouping applies to existing recordings as well as new ones and does not change
Learning progress, original capture files, timestamps or assessment history.
Unattributed recordings and ordinary Practice/imported sessions remain individual
entries. The browser's local timezone determines calendar-day boundaries.

The **Previously learned chunks** panel sits below the attempt/score controls and
feedback and is collapsed during ordinary Learning. Expand it when beginning a
review; it opens automatically while review is active, then collapses when you
return. **Return to learning** stays in the main attempt controls above the panel.

### Live staves in Review this attempt

**Review this attempt** now shows live staff notation for the current Learning
assignment (including connections and manual review ranges). Grey notes are
expected/pending; played notes appear dark, with provisional pitch differences in
red. It follows the current passage one measure at a time, scaled to fit the controls
panel width, with previous/next measure browsing and a return-to-live button. The same comparison engraver as
Practice supports overlay, expected-above-played and individual layers.

During hidden recall, sounded notes use the same reference positions, staff
assignment, spelling and rhythmic beaming as the visible live comparison. Only
played pitches are sent to the engraver: upcoming notes, missing notes and live
error hints remain hidden until a peek is explicitly requested or the take is
finished. The display follows the latest played measure; alignment around
mistakes remains provisional. Upcoming hidden attempts do not inherit an old comparison. The normal
peek/assistance rules still apply. Notes come from the authoritative capture
journal; the incremental display matcher never grants passes or changes progress.
Full-take evaluation remains the pass boundary. Staff notation uses reference
positions and regenerated spelling/durations rather than transcribing or grading
performance rhythm. Live alignment is provisional, especially around mistakes or
repeated figures. Abandoned takes do not label the unplayed ending as missing.

Completed chunks in **Your chunk map** are clickable. Select a checked chunk to
review that chunk alone (the separate Review learned chunks button still covers
the entire learned prefix). If a take is recording, its MIDI is saved without
evaluation before switching to review, preserving the correct-attempt streak.
Return to learning restores the original assignment. Unlearned chunks remain
non-interactive; reviewing does not mark them learned or advance the lesson.

During review, the chunk belonging to the current Learning assignment is also
clickable in the map (↩). It returns to Learning with the original position and
correct-attempt streak, just like the Return to learning control.

### Correcting a reference note

A note difference with an identified score occurrence offers **Fix reference note**
separately from **Overrule error**. Enter the corrected pitch (for example `Eb5`)
and a reason. This saves a local reference correction for that one occurrence;
future Learning evaluation and staves use it. The PDF and previous takes retain
their original content. Corrections persist across app restarts and are listed
under **Reference note corrections**, with **Undo correction**. Personal playing
adaptations remain under **Personal note rules**. Changing or undoing a correction
rechecks the affected chunk and later dependent stages while retaining earlier
progress. Finish or pause a take before editing; revoke a personal rule on the
same occurrence before correcting its reference. Corrections are scoped to the
current lesson revision, like personal rules.

### Learning pedal and compact score controls

**Middle pedal: repeat attempt** is enabled when Learning is open. Press and
release CC66 to restart a recording take without grading it or losing the
existing streak; while idle it starts the current assignment. The raw pedal
messages remain recorded and the piano's sostenuto function is unchanged.
Learning's middle-pedal control is independent of Practice's pedal-page-turn
setting. Uncheck it to disable the Learning shortcut. It is released when leaving
Learning or when its short frontend heartbeat expires; pedal gestures collected
before opening Learning are not replayed. Note editing and routine editing do not
trigger pedal repeats.

The Learning score toolbar uses inline controls, with larger buttons, text and
spacing on Full HD displays and a tighter layout on smaller screens. In score fullscreen,
reference-review metadata and the redundant PDF-start location are omitted;
notation explanations are under **Notation key**. Opening score fullscreen
returns the control panel to the top so the live staves can be seen without
scrolling at laptop sizes.

### Hands separately

The **Hands** selector offers **Both hands** (the default), **Right hand**, and
**Left hand**. Existing profiles keep their both-hands progress. Right hand uses
the upper-staff attack sequence; left hand uses the lower staff. This follows
score ownership rather than splitting pitches at middle C, and shared unisons
remain required when practising either staff alone. The printed PDF remains
complete; live comparison and pitch evaluation use only the selected hand.

Completed both-hands stages also count toward right-hand and left-hand progress.
Each separate hand uses at least the both-hands learning position and completed
chunks, including progress saved before this behavior was introduced. Higher
separate-hand progress is preserved; separate-hand progress never advances both
hands or the other hand. This applies to both assessed takes and explicit
self-assessment. Repetition streaks and take histories remain specific to each
mode: catching up starts the inherited position with a zero streak and does not
create separate-hand takes. An equal or higher separate-hand position keeps its
own streak.

Switching modes restores that progress and remembers the selection. Restarting
a separate-hand mode still respects completed both-hands stages; restarting both
hands does not erase progress already credited to the separate hands. Finish or
pause the current take before switching. Reviews, auto finish and middle-pedal
repeat use the selected mode. Saved takes retain their original hand selection.
Reference corrections and personal note rules remain shared, but recheck only
modes that include the changed staff. Changing chunk boundaries resets progress
for all three modes.

### Dictating a correction reason

Personal note-rule and reference-correction forms offer **Dictate reason**. Final
recognized text fills the reason field for review/editing before saving; **Stop
dictation** finishes recognition and **Cancel dictation** keeps the existing text.
The current language is English (`en-US`). This uses browser speech recognition,
which may process audio through the browser provider's online service and needs
microphone permission. It is separate from Learning's MIDI-only capture and the
optional OpenAI report adapter. Typing remains available when recognition is
unsupported or denied.


### Nocturne Op. 15 No. 1

[The Paderewski scan-study course](nocturne_op15_no1_learning.md) adds 37 editable
chunks, a proposed section progression, early backwards acquisition of the ending,
return comparisons and transition drills. Open it from the Library card or the
Learning piece selector. Its complete 1,801-attack counterpart has been visually model-reviewed against
all four scan pages; automatic pitch checks, finish, optional mismatch restart
and staff comparison are available with the exact reviewed PDF.

### Aeolian Harp: build backward review

Alongside the existing full-span review, **Review all learned · build backward** starts with the final two chunks of the learned prefix for the selected hand. An unassisted, capture-healthy, reviewed-reference pass expands backward by two chunks: 2, 4, 6… capped at the full learned prefix. One learned chunk is reviewed alone; odd totals finish with the exact total. The current unlearned chunk is excluded regardless of the existing include-current checkbox. Edited chunk boundaries are respected.

Each longer range waits for **Start review**; there is no automatic capture countdown. Failures, peeks, pauses and retakes do not automatically expand the range. Finished build-backward takes can also be explicitly marked correct as described below. A final full-prefix pass shows completion; Return to learning restores the saved assignment. Learning position, streak and mastery remain unchanged; each take and its actual range remain in history. The review sequence is temporary, like existing review selection, and restarts from two chunks when selected again. Startup still uses the existing full-span review. Other Learning pieces are planned in TODO and cannot select this mode yet.

Build-backward reviews allow score peeks: after finishing a take, choose **Mark review take correct** to prepare the next length (or complete the full span) by your own judgement. The assisted flag, pitch verdict and errors remain in history. This manual action does not change learning mastery or streaks; aborted takes, capture faults and obsolete assignments cannot be accepted. Ordinary learning recall still requires unassisted takes for counted repetitions.

Learning offers **Turn score pages automatically while peeking**, on by default and remembered in this browser. During an active peek it follows the latest matched attack in the reviewed lesson’s PDF map. Hidden recall never reveals page position; uncertain or unmatched latest notes hold the page. Manual navigation pauses automatic turns for ten seconds. This display aid does not change assessment or enable Practice recognition; provisional lessons do not turn automatically.


### Measure retries in review

Reviews have **Sound and retake the measure on review mistakes** enabled by default in **Edit routine & chunks**, independently of the existing opt-in whole-take restart for ordinary Learning stages. The reviewed-reference pitch/order matcher reads authoritative saved capture events. After a definite mismatch, Learning displays an error and plays a short, locally synthesized browser tone. The error pauses the run at the affected measure. Release all keys to save the interrupted MIDI and immediately resume capture from the beginning of that measure through the original review end. Click or press a key in Learning first to enable browser audio; muted/blocked audio does not prevent the visible notice or retry. Pauses, incomplete passages and uncertainty do not trigger retries. No MIDI output, cloud service or microphone is used for the cue.

During a review, **Retake last measure** saves the active take and rewinds to that measure, continuing through the original review end. At an exact completed barline, manual retake returns to the last played measure; a wrong first attack of the next bar automatically retries the next bar. When the staves overlap a boundary, unfinished earlier staff notes keep the retry at the earlier measure. Uncertain locations are not guessed: finish or use **Restart whole review**. The manual button is also available after a finished current review when its capture is intact. Provisional lessons cannot locate measures for retry; whole-review restart remains available.

Replay from the beginning of the indicated measure and keep playing the remaining passage uninterrupted. Recording stays active across barlines: there is no **Finish & evaluate** or **Start review** step between the repaired bar and the following measures. Automatic finish waits for the full remaining range; if automatic finish is off, finish manually at the end. Another detected mistake rewinds again to its affected measure. **Pause learning** still saves and stops the run without restarting it. Score peeks stay visible and recorded as assistance. Finishing the remaining passage makes the original review range available again; **Restart whole review** returns to that original range immediately.

Every interrupted take and resumed range retains its own actual range and MIDI. They never replace the original performance or combine into a fabricated whole-range assessment. Consequently, retrying part of a build-backward review does not automatically expand it: a complete original-range pass or explicit manual acceptance is required. After a pitch-correct run from the rewind point to the end, **Mark review sequence correct** lets you expand by your own judgement without repeating the original range. This records acceptance of the separate parts and preserves every part’s pitch verdict. Learning mastery, stage position and streaks stay unchanged. Capture/storage faults and unsupported references prevent automatic retries. Physical piano, touchscreen and audible-output acceptance remains open.


## Score certification

Use **Score certification** on a Learning-grade piece in Score Library or
under **Score tools** below the main Learning controls. The exact reviewed
Paderewski PDF is required to begin. Set **From** and **Through** to select any
inclusive measure range. **Use learned range** fills the contiguous prefix
covered by completed both-hands hidden stages, including the pickup where
applicable. Start opens the reviewed PDF page for the first selected measure.

Read both staves in written attack order. Within one attack you can play a chord
together or press its keys individually in any order. Play a shared unison once,
follow the printed measures once, and play the written attacks of ornaments.
The capture is MIDI only. The live staves and pitch labels show the eight most
recent registered attacks, schematically spaced in arrival order.

**Finish and review** includes every written attack in the selected range.
**Pause and review up to here** ends capture and saves a partial review through
the last matched written attack. Check the displayed measure and attack number
when the last passage contains repeated pitches or playing mistakes. Later
written attacks and any unplayed keys of the final partially played chord are
outside this review. Earlier omitted pitches and trailing played-only notes remain visible. A pause with no identifiable matched attack
still preserves the MIDI for inspection.

Use the measure selector to see matching and differing notes throughout the
review. Red diamonds mark reference-only pitches and red crosses mark
played-only pitches. Isolated differences with nearby matches can yield a
proposed replacement, removal or addition. Compare each proposal with the scan.
Ordering differences, repeated figures, played ornament realizations and
incomplete passages can make localization uncertain. Interrupted captures
retain available MIDI for inspection. Reviews use saved MIDI journals and the
reference revision recorded for the take. The comparison handles up to 12,000
played attacks.

The optional **Include saved Learning score corrections** setting snapshots
confirmed local reference pitch corrections in the selected range. Personal
Learning note rules, such as accepting an omitted note, are separate. Saving
or reviewing a certification take records its own evidence and suggestions.
Lesson progress, rules, original scores and existing Learning recordings keep
their own records.
