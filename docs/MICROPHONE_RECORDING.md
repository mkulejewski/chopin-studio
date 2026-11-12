# Microphone and MIDI recordings

At the top of Practice, above the score, **Recording sources** has independent **Record cable MIDI** (on by default) and
**Record laptop microphone** (on by default) switches. Choose at least one
before starting a session. **Record microphone** (or **Record microphone + MIDI**) starts microphone capture directly; the regular Record session button uses the switches. Choices are fixed for that session. The microphone
uses the laptop running the backend, including when controlling it from another
browser. Select the built-in microphone in the operating system's input settings;
`default` follows that input. An ALSA device name can select a different input.
Linux `alsa-utils` (`arecord`) is required. No cloud service is used for capture
or acoustic analysis. Browser voice commands remain a separate feature.

Microphone capture is 48 kHz, 16-bit, mono. Raw PCM is written during recording
and converted in blocks to lossless FLAC on stop. Raw PCM is removed only after
the FLAC and metadata are saved. Interrupted raw files are recovered at startup;
recordings with capture faults are marked incomplete. A cable disconnection
retains the existing 15-second stop-and-save behavior for MIDI-only sessions.
Sessions with microphone enabled continue until stopped, including with the
window closed; they keep the backend alive during idle shutdown.

## Piece boundaries and listening

When MIDI is present, existing MIDI recognition and activity boundaries are the
single timeline for both sources. In Sessions → selected activity, microphone
playback and Download activity FLAC extract that exact saved interval, using the
estimated audio sample-zero offset. Splitting, merging, relabelling and undoing
use the same timeline. Saving edits generates new analyses. Audio exports are
temporary request-owned files, deleted after the response finishes. No separate piece audio files are kept in addition to the source. Retained session audio is also downloadable. A cut may truncate room reverberation; extend its
end in the timeline when a longer release tail is wanted.

With no captured MIDI notes, energy above a room-noise estimate proposes activity
intervals, separated by the configured silence cooldown (default 20 seconds).
These intervals are **unidentified material**, not recognized compositions. Noise
can create false activities, while quiet playing and short pauses can conceal
boundaries. Confirm the piece and edit/split/merge the activities manually. Silence
can produce no activities. Audio-only capture does not transcribe piano notes.

## Evidence and correlation

Every activity analysis includes microphone coverage, RMS and peak dBFS,
near-full-scale sample fraction, quiet fraction and detected acoustic attacks.
MIDI chord/onset groups are compared with rises in the acoustic energy envelope.
A one-to-one match estimates a constant audio-minus-MIDI offset within ±0.5 seconds.
It needs at least five matches, 45% MIDI-group coverage and a distinct best lag;
periodic or weak evidence is reported as uncertain/unavailable. Capture errors
prevent alignment claims. Matched timestamps, MIDI velocity, acoustic attack
level and residual milliseconds are shown together and included in JSON reports.
The UI shows the first 100 events; JSON retains up to 2,000.

This supplements score/MIDI evidence; it does not modify pitch scoring. Attack
residuals include detection and device errors and are not a judgement of the
player's timing. No per-note acoustic pitch, pedalling clarity, voice balance,
calibrated SPL or interpretation accuracy is claimed. Laptop automatic gain,
noise suppression, room sound and reverb affect measurements. Hardware sample
zero and clock drift are not calibrated; long takes need listening review.
For better results select a stable input, disable automatic input processing
where the operating system permits, and avoid clipping. Validate with a real
piano before relying on attack correlation as practice evidence.

## Storage budget

Decimal MB, excluding small headers:

| Length | Mono 48 kHz / 16-bit PCM | Stereo equivalent |
| --- | ---: | ---: |
| 1 minute | 5.76 MB | 11.52 MB |
| 5 minutes | 28.8 MB | 57.6 MB |
| 10 minutes | 57.6 MB | 115.2 MB |
| 1 hour | 345.6 MB | 691.2 MB |

Formula: seconds × sample rate × channels × bits / 8. FLAC size depends on room
noise and signal content; budget the PCM size rather than assuming a compression
ratio. For a five-minute piece, allow **30 MB for its mono audio**, plus MIDI,
the durable MIDI JSON journal and reports. There is **one stored audio copy**;
piece clips and ZIP bundles are temporary and cleaned after downloads. During
conversion or manual compaction, reserve space for both the old and replacement
file (roughly twice the PCM budget). MIDI is normally far smaller but its JSON
journal can be much larger than the `.mid` file.

## Audio retention and removal

**Sessions → Audio cleanup · kept & flagged recordings** applies the two-take
shortlist **only to stored audio** (microphone capture and rendered/attached audio).
MIDI-only takes never appear in this cleanup list or consume audio shortlist slots.
MIDI sessions, event journals, imported MIDI/CSV sources, MIDI exports, analyses
and session history are normally kept indefinitely, including incomplete practice
attempts. The piece library and take comparison show all MIDI performances,
regardless of the corresponding audio's keep/remove flag.

Audio qualifies for automatic keeping when its take is labelled complete
(automatically or manually). A partial can also qualify as near-complete when at
least 80% of reference onset groups match, the opening is within the first 10%
and the ending reaches the last 10%, with confidence at least .75 and at least
eight reference groups. Short exercises and uncertain/unidentified performances
have their **audio** flagged. Audio-only performances need a manually assigned
piece and completeness decision. MIDI is retained regardless of these criteria.

Ranking uses capture health first, then the reliable verified-reference pitch
score, then clipping, then recency. With no reliable score, recency breaks ties;
this is a labelled fallback, not a judgement of musical interpretation.
**Keep this audio** overrides the shortlist and can keep any extra audio, including partial or unidentified material, without changing completeness. Keep protection follows overlapping intervals across timeline edits, rebuilds and undo.
**Flag audio for removal** and **Use automatic choice** change the recommendation.
**Mark complete** corrects false partial classifications; **Mark partial** reverses
that classification (near-complete partials can still qualify for audio retention).

Surplus eligible audio and explicit removal choices are removed automatically
only at application shutdown. No timer removes audio while the app stays open. Open Audio cleanup
after stopping to protect takes with **Keep this audio**. Unknown/uncertain takes
remain for manual review; sessions with capture errors are excluded. Cleanup
defers while recording, playing through the piano, saving or running background
jobs. Overlapping takes are left intact for correction. Keep flags are rechecked
under the same lock used for deletion.

**Delete audio** confirms an exact interval, removes its microphone samples and
generated/attached audio files, and packs retained audio into one FLAC file. A
span map preserves original timestamps for correlation. Samples are copied as
16-bit integers without resampling or quality loss. The old audio generation is
removed only after a durable metadata swap. Interrupted
cleanup resumes at startup as audio-only cleanup, including pending cleanup from
the earlier whole-recording policy.

Audio cleanup leaves MIDI files, event journals, CSV imports, MIDI exports,
segment labels, analyses and reports intact. MIDI playback/export, timeline edits,
undo and rebuild remain available. Rebuilding a MIDI timeline cannot restore
erased acoustic samples. Historical audio metrics can remain in saved analyses
even when the corresponding source audio has been removed.

**Delete session**, on every saved session row and in session detail, is a separate
explicit action for removing the entire session, including MIDI. Its confirmation
lists MIDI, audio, activities and reports. It also handles empty/no-MIDI sessions.
Recording/playback, saving or queued/running jobs must finish before deletion.
Database errors restore staged files. User notes, piece scores, learned references
and files already downloaded outside the app remain independent.

## FLAC quality

FLAC is lossless compression: decoding reconstructs the exact captured samples.
It reduces how many bytes represent them, not the audio information or quality.
It does not lower sample rate or bit depth. Higher compression effort trades
encoding time for size, without changing the decoded samples. It cannot repair
noise or clipping already present in the recording. See the
[official FLAC FAQ](https://www.xiph.org/flac/faq.html).

## Catalog and naming

Internal storage keeps identity stable:

```text
$CHOPIN_DATA_DIR/                         # default ~/.local/share/chopin-studio
  studio.sqlite3                        # piece labels, takes, boundaries, reports
  sessions/<session UUID>/
    events.jsonl                        # MIDI + session markers
    original.mid
    microphone.json                     # device, format, timing, faults
    microphone.flac                     # one source; before any manual removals
    microphone-retained-<UUID>.flac      # replaces the source after removals
                                        # only one of these generations is retained
    microphone.log
    microphone.pcm                      # only during capture / failed conversion
  exports/<activity UUID>/
    segment.mid
  reports/<analysis UUID>.json
```

Human-facing MIDI and microphone activity downloads share this stem:

```text
20261109T140500Z__n9-2__a1b2c3d4__e5f60718__12.500-312.500s__microphone.flac
20261109T140500Z__n9-2__a1b2c3d4__e5f60718__12.500-312.500s__midi.mid
```

Fields: UTC session start, stable piece ID (or `unidentified`), session ID prefix,
activity/take ID prefix, original-session bounds, source and extension. Timestamp
and IDs distinguish repeated attempts; bounds distinguish edits. The full UUIDs
remain authoritative in the database. Titles and inferred completeness are not
used as filesystem identity, so corrected labels do not move session masters.

For a manually curated archive, use `Recordings/Chopin/n9-2/2026/` and keep each
paired download together. Keep the same stem for a report or personal notes.
Treat different attempts as separate takes; do not overwrite the previous take
with a new “best” performance. Back up the full data directory to preserve the
catalog and all remaining recordings. Permanent deletions cannot be undone by timeline history. Downloaded exports are optional copies outside app-managed storage.


## Activity labels and full-piece practice

**Partial exercise** means work on a section or technical practice. **Full-piece exercise** is a whole-piece lesson/practice run, with mistakes, hesitations or restarts allowed; it sets the coverage flag while keeping an exercise label. **Complete performance** is a whole take and does not certify musical quality. These activity labels remain separate from the technical pitch assessment and capture-health status. Grouping attempts no longer changes their activity type. A user-confirmed full-piece exercise survives an equivalent timeline rebuild.

## Automatic headphone-style audio exclusion

After saving, background analysis compares sustained MIDI playing with the
microphone signal. When there is no discernible piano tone, the microphone
interval is automatically removed and excluded from the two-take audio shortlist.
The analysis and microphone metadata explain the decision. MIDI, its journal,
score analysis, labels and progress remain intact. MIDI-generated renders are
independent of the microphone source and remain usable.

This is an inference of inaudible piano, not a confirmed headphone-jack sensor:
headphones, muted piano output and a muted input can produce similar evidence.
The AP-470's published [MIDI implementation](https://www.casio.com/content/dam/casio/global/support/manuals/electronic-musical-instruments/pdf/008-en/a/AP470_midiimplementation_EN.pdf)
does not document a jack-status message, so the application does not infer a
physical plug from MIDI volume, pedal controllers, or the computer's audio jack.

The first detector requires at least eight reasonably played MIDI onset groups
spanning four seconds, at least 95% microphone coverage, no capture fault, and
no tonal evidence across a range of plausible MIDI/audio offsets. Quiet audio
or steady moderate background noise is discarded only after those checks.
Even very quiet tonal sound protects a take. Short/sparse MIDI, missing coverage,
loud/variable background sound and capture errors remain for review. Synthetic
fixtures validate the policy; actual piano/microphone acceptance remains pending.

**Keep this audio** overrides automatic deletion; a detected inaudible microphone
take still does not consume a shortlist slot. Overlapping intervals are left
intact. Mixed sessions are compacted losslessly so audible neighbouring takes
keep their samples and original timestamps. Cleanup uses a durable deletion
record and can resume after failure. Existing saved microphone recordings are
checked in the background after restart once per audio-file version. Recordings
are never stopped or muted globally based on one take's detection.
