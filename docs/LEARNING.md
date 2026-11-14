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
ending. Failed repetitions are not automatically segmented: use **Finish &
evaluate** to grade one or **Restart take** (also available through the middle
pedal) to save it without grading and immediately start again.

**Automatic continuation** starts another attempt after a two-second result
interval after a successful or explicitly self-assessed take, advancing stages
when their configured consecutive-pass count is met. Failed takes wait for review.
Use **Pause learning** to stop the countdown or save an unfinished attempt. There
is no completion-by-silence rule. The server pauses after 15 seconds without a
Learning heartbeat; switching away or hiding the browser also pauses. Progress
survives refresh and restart, but interrupted attempts do not earn passes. There
is no automatic recording restart after a backend restart.

**Peek at score** marks an active hidden attempt assisted. Assisted hidden
attempts do not count toward advancement. The PDF canvas is removed during hidden
stages. Visible study is meant to use the score. Consulting it between attempts
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
correct-attempt streak. Restarting a hidden attempt hides the score again and
clears assistance for the new take. Restarted takes remain labelled in history.
Paused/abandoned takes do not receive misleading missing-note error lists.

**Automatically restart takes on mistakes** is an optional setting in
**Edit routine & chunks**, off by default and saved with the routine. A definite
pitch or note-order mismatch restarts the same assignment once all keys are
released. It works independently of automatic finish and continuation, including
manual review and hidden recall. The interrupted take's MIDI is saved and labelled
as automatically restarted; learning position and the correct-attempt streak stay
unchanged. The new hidden take hides the score and clears assistance as usual.
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

Each mode keeps its own learning position, completed chunks, streak and history.
Switching modes restores that progress and remembers the selection. Finish or
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
