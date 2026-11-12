# AP-470 and Linux Mint touchscreen acceptance

These tests require the physical piano and touchscreen; automated emulation is insufficient.

Checked for coverage against the working tree on 2026-11-12; none of these manual
checks was executed by that review. Use disposable test material/data for
interruption and deletion checks. Automated UI testing must follow `AGENTS.md`:
an isolated headless browser, temporary data/state, a dedicated port and
`CHOPIN_NO_HARDWARE=1`, including 1920×1080 for layout/fullscreen checks. Never
attach automated tests to the user's browser or use the production service.

- [ ] Desktop icon starts the backend/browser without a terminal. A second launch opens the same service. Fullscreen can be entered and exited by touch.
- [ ] AP-470 USB Type-B input appears. Tap device, save preference, reconnect. Confirm changing ALSA numeric suffix is handled by a stable name substring.
- [ ] Each key press/release appears; velocities change with touch. Rapid repetitions, held chords and all three pedals produce messages. Check whether CC64 supplies intermediate values on this setup.
- [ ] Record at least 2 hours. View/crop/pinch scores and switch tabs while playing. Compare the original against an independent capture, inspect timing and queue depth, and check RAM stays bounded.
- [ ] During MIDI-only recording, disconnect USB and reconnect within 15 seconds of detected loss: confirm the same session continues with dropout markers. Repeat beyond the grace period: confirm automatic stop/save and no automatic new recording on reconnection. With microphone enabled, confirm MIDI loss does not stop audio capture. A dropout cannot recover notes never received.
- [ ] Close/reopen Practice during recording. Capture continues; an active microphone session keeps the service running. Without a piano, microphone capture or frontend, confirm the five-minute idle shutdown. Confirm **Save & shut down** saves the active session; a save failure must remain visible and keep the service alive. Stop confirmation cancellation preserves capture. Learning has separate pause rules below.
- [ ] Kill backend during a disposable test session; relaunch and confirm recovered status, playable MIDI and explicit truncated-tail limitation.
- [ ] Import a PDF and assign ranges using touch only, including cover pages; printed labels remain separate. Test page buttons, swipe, pinch, pan, double tap, one/two-page, crop and persisted reading position.
- [ ] With a zoomed page, horizontal drag pans without turning pages. Vertical movement does not turn pages. At fit scale, deliberate horizontal swipe turns once. Browser/Cinnamon edge gestures do not steal ordinary score interaction; disable conflicting gestures in Settings as fallback.
- [ ] At 100%, 125%, 150% and 200% display scaling, test all navigation, file choosers, modal scrolling, stop confirmation, search and on-screen keyboard. System OSK support depends on browser and Cinnamon accessibility configuration.
- [ ] Enable CC66 only after calibration: single press next, two quick presses previous, hold controls. Check actual sostenuto acoustically. Receiving CC66 does NOT disable the piano's internal musical action. If unsuitable, disable the mapping and use page buttons, arrows or a USB pedal sending arrows.
- [ ] Import an existing MIDI, export it and compare hashes. Replay it into a disposable recording with the hardware disconnected; inspect original pedal values and measurements.
- [ ] Verify sleep/screen-lock policy before long sessions. The app cannot prevent suspend or recover events during OS sleep.
- [ ] Back up the data directory with the backend stopped and restore into `CHOPIN_DATA_DIR` for a separate test.

USB-MIDI carries MIDI events, not the AP-470's audio. Capturing its original timbre requires an appropriate audio-output/interface path. Hardware, internal sostenuto configuration and audio routing have not been validated by Codex.

## Version 0.2 advanced checks

- [ ] Confirm the 44 personal repertoire entries, mastery/liking/forgotten values and partial-learning notes. Check the Schott-only Raindrop preference and three missing exact printed-score slots.
- [ ] Open downloaded scores from the individual work cards. Check first/last pages and adjust any edition-specific bounds. Source MusicXML references are provisional first-edition/other-edition material, not certified copies of the printed Paderewski notes.
- [ ] Practise several different works/fragments; review proposed boundaries, identities and uncertainties. Split/merge with numerical controls, save, undo and export; confirm original MIDI unchanged.
- [ ] Compare reference accidentals, ties, ornaments, repeat order and measure numbers with the actual edition before marking it verified. Test source SVG preview and edited analysis-note representation separately.
- [ ] Enable live recognition without preselecting a piece. Try mid-piece starts, deliberate mistakes, repeats and unrelated improvisation; uncertain input should not force a page turn. Validate all measure/page links before allowing automatic turns.
- [ ] Manually turn while following and verify the 10-second override. Try a backward restart; automatic turning must reset stability. Keep it disabled if uncertain.
- [ ] Request a short FluidSynth render, listen, cancel another render, export FLAC and a session bundle. Check original MIDI and continuous pedal data remain present.
- [ ] Generate a local report; review evidence IDs, edit a new report revision and compare two activities. Treat potential discrepancies and local tempo as review aids, not certified mistakes or rigid metronomic judgements.
- [ ] If opting into OpenAI, configure a local key and explicitly choose to send structured evidence/question/recent reports. No cloud call should occur while simply recording, importing, opening or generating local reports.

## Microphone and cleanup checks

- [ ] Record MIDI and microphone together, then microphone only. Verify the actual input device, audibility, clipping indicators, FLAC playback and passage bounds. Compare a long take for drift; offset estimates are not hardware calibration.
- [ ] With disposable takes, confirm shutdown removes flagged surplus/partial audio, including flagged capture-error audio, while MIDI/history remain. Unknown/uncertain audio should remain for review; **Keep this audio** must protect a take across timeline edits/rebuild/undo.
- [ ] Check inaudible-piano detection with headphones/muted speakers, audible quiet piano and room noise. It can discard microphone intervals after analysis, before shutdown. Confirm Keep protection, neighbouring audible intervals and MIDI preservation. No physical jack-state detection is claimed.
- [ ] Check **Delete audio** separately from **Delete session**, then restore a disposable backup. Timeline undo cannot restore permanently deleted samples.

## Learning checks

- [ ] Import the exact reviewed Aeolian PDF. Test visible study, hidden recall/peek assistance, complete-passage evaluation, auto finish, two-second successful continuation and failed-take review with actual beginner pauses/errors.
- [ ] Try rolled chords, shared unisons, repeated patterns and wrong/missing/extra notes in each hand mode. Confirm independent saved progress and no rhythm/tempo grade.
- [ ] Use Restart take and the middle-pedal repeat shortcut, self-assessed take/stage advancement, selected-chunk/prefix review and Return to learning. Check that reviews and neutral restarts preserve the lesson position/streak as documented.
- [ ] Leave/hide Learning and restart the backend: capture must not resume automatically. With learned chunks, check startup review selection and explicit start/return controls.
- [ ] Test local reference correction separately from a personal note rule, invalidation of affected hand modes, preserved history and undo/revocation. Check the score-left divider, fullscreen controls and hidden live-staff privacy on the real display.
- [ ] If using browser speech recognition, test score-opening commands and reason dictation with microphone permission granted/denied. Check provider disclosure, cancellation and the typed/manual fallback. This is separate from local microphone capture.
