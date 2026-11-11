# Learning: memorizing notes separately from performance

Learning is a separate workspace. Its first approved lesson is Étude Op. 25 No. 1,
Aeolian Harp, in the exact cached Paderewski Études scan. It starts with no learned
chunks, independently of the Library's personal mastery and Practice history.

Open **Learning**, connect MIDI, and start an attempt. The initial routine uses
three consecutive correct visible attempts, three correct hidden attempts and two
correct connection attempts. Change these in **Edit routine & chunks**. Learning
always records MIDI only; it neither opens the microphone nor renders audio.

A chunk has visible study and hidden recall stages. Later chunks are connected
cumulatively from the start of their section. Each section after the first ends
with a cumulative recall from the pickup. The final stage covers the entire piece.
The default 35 chunks yield 104 stages. The initial lesson analysis is recorded in
[the Aeolian review](AEOLIAN_LEARNING.md).

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
material. An attempt longer than 6,000 attacks asks for a shorter passage rather
than truncating it. The closing D2/Eb2 trill has an explicit local policy; no
blanket ornament exemption applies elsewhere.

**Automatic finish** recognizes a complete correct passage, waits for key release
and 1.5 seconds to settle, then saves and evaluates the authoritative MIDI journal.
Release is an attempt-boundary aid, not a duration grade. Long thinking pauses do
not end incomplete attempts. Use **Finish & evaluate** for mistakes, an omitted
ending or a restart. This first implementation does not automatically segment
failed repetitions: finish the failed attempt before replaying the whole passage.

**Automatic continuation** starts another attempt after a two-second result
interval, advancing stages when their configured consecutive-pass count is met.
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

## Adding another piece

Every proper Learning piece must receive in-depth model (or equivalent human)
analysis of structure, exact edition, boundaries, exceptional notation and a
beginner learning path. Musical-content review and lesson-plan review are
separate responsibilities. Page-map calibration alone is insufficient. The
current API declines pieces without an approved lesson; it does not silently
generate a provisional plan. A future algorithmic proposal must be visibly
flagged **provisional**, and must not earn trusted automatic advancement before
edition review. Reference changes require a new revision and fresh affected
progress; old evidence remains historical.

## Deferred features

- [ ] Chunk-only PDF regions/masking, digital excerpt engraving and note overlays.
- [ ] Within-measure and note-level chunk boundaries; overlapping boundary drills.
- [ ] Dedicated guided note-by-note acquisition with prompts (separate from tests).
- [ ] Hands/voices separately, followed by combined recall.
- [ ] Independent/random starts and backward or alternative connection strategies.
- [ ] Delayed retention checks, spaced review and a due-for-review map.
- [ ] Adaptive chunk splitting and workload suggestions.
- [ ] Harmonic annotations, fingering notes and silent study tasks.
- [ ] Optional MIDI demonstration, with playback excluded from evaluated input.
- [ ] A lesson authoring/review interface and explicitly provisional algorithmic plans.
- [ ] Automatic failed-attempt segmentation, richer substitution explanations and
      evidence playback directly from each discrepancy.
- [ ] Optional elementary rhythmic-order checks; no rhythm grading in this version.

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

Failed takes now wait for review rather than automatically starting another take.
Successful and self-assessed takes continue after a two-second break when automatic
continuation is enabled. The earlier five-second interval is replaced by two seconds.

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
in take history. They do not automatically repeat. **Return to learning** stops
and saves an active review and restores the original assignment and streak. Review
is temporary; a backend restart resumes normal Learning at its saved position.

Future plans (not implemented): automatic review suggestions after a break,
spaced/due-for-review scheduling, and an option to open a piece directly in review
mode after a period without learning. These are not automatic actions today.

The **Previously learned chunks** panel sits below the attempt/score controls and
feedback and is collapsed during ordinary Learning. Expand it when beginning a
review; it opens automatically while review is active so Return to learning stays
available, then collapses when you return.
