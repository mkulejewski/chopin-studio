# TODO

Implemented, with hardware and musical-quality acceptance still open:

- [x] Investigate live score following: retain page requests across polling, reset stale state, shorten the following window, and display provisional positions without enabling their automatic turns.
- [x] Add AP-470 built-in sound production through explicit physical-piano MIDI playback, optional audio-interface capture, and USB-flash WAV attachment.
- [x] Allow any left-page number in two-page view; expose layout and options buttons in fullscreen/hidden-controls view.
- [x] Keep PDF documents warm across views and preload the following spread.
- [x] Automatically save structured preanalysis to JSON files and provide a session export for LLM integration.
- [x] Save automatic pitch precision/recall/F1 and practice/good/concert technical evaluations separately from personal notes and mastery. Retain the latest performance and latest eligible whole-piece level; suggest a personal-level review when they diverge.
- [x] Flag eligible high-scoring complete recordings as candidates for audio production, without automatically rendering them.
- [x] Fix handling of batched pedal page turns and add configurable controller selection.
- [x] Increase the separation cooldown to 20 seconds by default, combining short practice restarts into larger activities; retain optional timeline split/merge and configurable cooldown.

Remaining acceptance:

- [ ] Test live following, all physical pedals and page maps on the AP-470 with the actual repertoire.
- [ ] Test physical-piano MIDI playback, USB-flash recording and audio-interface capture, including cancellation, levels and routing.
- [ ] Review/verify symbolic references and calibrate technical thresholds with real performances. These scores do not certify interpretation or concert readiness.

See [validation](VALIDATION.md) for scoring definitions and [AP-470 audio](AP470_AUDIO.md) for setup.
