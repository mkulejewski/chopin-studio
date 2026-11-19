# Standalone Android port

Stage 2 is future work. Stage 1 provides the Linux host and shared Python
services described in [Architecture](ARCHITECTURE.md). The intended product is a
standalone phone connected directly by USB-C/OTG to a digital piano. Begin with the
Casio AP-470, then test generic class-compliant keyboards. Recording, recovery,
analysis and MIDI export must work offline without a laptop. The phone workspace
would show compact recording controls, take evidence and Learning views, with
score viewing available on demand.

## Adapter contract

- Compose `chopin.studio.Studio(app_private_root, StudioPlatform(...))`. The
  native host owns one instance per data directory, calls `start()`, schedules
  `check_disconnect()` and `tick_learning()` while relevant, and calls
  `prepare_shutdown()` and `close()` on orderly shutdown. Process death uses the
  same journal and SQLite startup recovery. Native foreground recording owns
  Practice across Activity/WebView destruction, screen lock and UI recreation.
  Learning visibility/pause and heartbeat are separate. Forwarding them is part
  of the UI bridge.
- Implement `MidiInputDriver.inputs()` and
  `open_input(port, receive, report_error)` from
  `chopin.platform.interfaces`. Use stable port identifiers where available.
  Translate permission/attach/detach into observable enumeration and errors.
  `MidiInput.request_reconnect()` can wake the monitor on a native event.
  Implement a closeable input connection. Close/detach must quiesce callbacks
  before the native resources are released. The shared monitor drops stale
  callbacks from earlier connections.
- Deliver per-port MIDI 1.0 messages in wire order as `MidiEvent(timestamp_ns,
  message)`. Anchor native timestamps to the same monotonic nanosecond clock as
  the recorder. Check offset, drift and ordering under load and across suspend.
  equal timestamps retain arrival order. Handle fragmented/multiple messages,
  running status, interleaved realtime bytes and SysEx boundaries in the
  native parser. Preserve channels, zero-velocity note-on, release velocities,
  CC88 and all transmitted controller values. Report stream errors/loss to
  `report_error`. Keep native callbacks free of SQLite, filesystem and analysis
  work. Keep queues bounded and make losses visible.
- If the instrument exposes output, implement `MidiOutputDriver.outputs()` and a
  closeable `OutputConnection.send(message)` that reports exceptions. Reuse
  shared timed playback and cancellation/controller cleanup. Keep playback
  mutually exclusive with authoritative recording. For the MIDI-first version,
  leave the optional microphone, renderer and hardware-audio adapters absent.
- Give SQLite and journals an app-private local filesystem and provide
  `StorageFiles` with same-directory temporary paths, durable flush,
  atomic replacement, directory synchronization and capacity reporting.
  Verify the guarantees on actual Android storage. Stage user-selected
  documents in local files before import. Pass those to
  `imports.import_midi_file`, `imports.import_pdf_file` or the existing symbolic
  reference importer. Use the Android system picker and export/share APIs at the
  host boundary. Preserve authoritative journals, original assets, schema history
  and profile/analysis revisions in backup and restore. A document-provider URI
  is a transport handle, not a SQLite path.
- Keep capability confirmations distinct from incoming evidence. Use the
  instrument profile and optional release calibration for monitor displays and
  explicit settings, and keep real controller bytes separate from Learning and
  page commands. Control identity and permission prompts at the native host.

## Porting checklist

1. Verify package and runtime compatibility for the target Android ABI and
   Python version. Prototype NumPy, SciPy, RapidFuzz, Partitura and its
   dependencies, SoundFile/libsndfile, SQLite WAL, Mido, pypdf and defusedxml.
   Test bundled score data inclusion and import, cold start, memory and latency.
   Test numerical and journal compatibility against desktop fixtures. Decide
   whether Chaquopy or another supported Python integration meets those needs.
2. Evaluate Kotlin and Android MidiManager versus lower-level USB MIDI APIs
   where required. Implement MIDI input/output, native stream parsing, USB
   permissions and attach/detach. Run the shared synthetic contracts before
   instrument tests.
3. Implement a reliable foreground service for Practice with visible recording
   state, explicit Stop, loss diagnostics and recovery after forced termination.
   Decide how Android should handle disconnect grace and power management, and
   run screen-lock, idle, process-death and long-take tests.
4. Implement app-private storage and SQLite ownership, document-picker staging,
   imports, exports and backup/restore. Run migration, full-disk, torn-journal,
   unsupported-schema and atomic-recovery tests on the phone.
5. Integrate the shared engine and choose a local UI bridge. Embedded React in
   a WebView with a constrained bridge is a candidate. Verify offline operation,
   platform lifecycle handling, Learning heartbeat/pause, compact touch
   controls and usable analysis summaries. Keep the shared musical algorithms
   outside the UI bridge.
6. Produce reproducible installable and signed APKs and test install, update
   and backup workflows. Validate direct AP-470 MIDI capture and optional
   output on a physical phone, then repeat with a generic keyboard. Check CC88,
   actual release velocity, sustain, sostenuto and soft pedal. Establish
   timing, long-duration, fault and power-loss acceptance before release.

Kotlin, Android MidiManager/USB APIs, a native foreground service, app-private
SQLite, embedded React and Chaquopy are candidates. Packaging, permissions,
device clock behavior and filesystem durability need evidence before committing
to a particular host design.

## Deferred after the initial phone release

- Full tablet-sized Android interface, including two-page PDF presentation and
  an adaptive multi-panel Learning workspace.
- Continuous horizontally scrolling phone notation and precise original-score
  measure cropping.
- Android microphone/audio enhancements beyond the MIDI-first port.
- Network synchronization and multi-device operation.
