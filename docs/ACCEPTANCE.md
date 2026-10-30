# AP-470 and Linux Mint touchscreen acceptance

These tests require the physical piano and touchscreen; automated emulation is insufficient.

- [ ] Desktop icon starts the backend/browser without a terminal. A second launch opens the same service. Fullscreen can be entered and exited by touch.
- [ ] AP-470 USB Type-B input appears. Tap device, save preference, reconnect. Confirm changing ALSA numeric suffix is handled by a stable name substring.
- [ ] Each key press/release appears; velocities change with touch. Rapid repetitions, held chords and all three pedals produce messages. Check whether CC64 supplies intermediate values on this setup.
- [ ] Record at least 2 hours. View/crop/pinch scores and switch tabs while playing. Compare the original against an independent capture, inspect timing and queue depth, and check RAM stays bounded.
- [ ] Disconnect USB during recording. Confirm reconnection markers, visible disconnected state, previously captured MIDI preservation and fresh messages after reconnect. A dropout cannot recover notes never received.
- [ ] Close/reopen the browser during recording. Recording continues. Stop requires touch confirmation; cancel preserves the active session.
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
