# AP-470 built-in sound

The AP-470 can record its sound while you play; another performance is unnecessary if you record audio at that time. Its USB flash recorder creates stereo, 16-bit, 44.1 kHz WAV files (up to about 25 minutes each). The computer USB connection carries MIDI, rather than the piano's audio. See the [Casio AP-470 manual](https://www.casio.com/content/dam/casio/global/support/manuals/electronic-musical-instruments/pdf/008-en/w/Web_AP470-E-3A_EN.pdf), “Recording to a USB Flash Drive (Audio Recorder)” and “Connecting to a Computer”.

To keep audio of the original playing, use the piano's AUDIO REC function with a flash drive, alongside Chopin Studio MIDI recording. Follow Casio's recording/stop procedure. Copy the resulting `TAKE*.WAV` to the computer, then open Sessions → activity → Optional audio → Attach AP-470 WAV. Attachment associates the file with the chosen activity; it does not automatically trim or synchronise a longer recording.

To produce AP-470 audio from a saved MIDI take, open its activity's Optional audio panel and select the piano's MIDI output. The piano must be connected and switched on. Select the intended tone/effects on the piano before playback; recorded program/controller messages can also affect its sound. Production runs in real time, followed by a three-second release tail. MIDI recording is unavailable during hardware playback to avoid recording playback loopback as another performance.

Two recording choices are available:

1. Leave the ALSA input blank, start the piano's USB-flash audio recorder using Casio's procedure, then press **Play through AP-470**. Stop the piano's recorder after playback and attach its WAV later. Chopin Studio cannot start/stop the piano's flash recorder remotely.
2. Connect the piano's PHONES/OUTPUT to an audio interface's suitable line inputs. Enter its ALSA recording device, such as `plughw:CARD=YourInterface,DEV=0` (replace this with the actual device; `arecord -L` lists available devices). Press **Play through AP-470 and capture audio**. The application starts stereo `arecord` capture before MIDI playback and stops it after the release tail. Install ALSA utilities if `arecord` is missing. Check routing and recording levels using a short take first. The USB MIDI cable alone does not provide this audio path.

Use **Cancel job** to stop application playback/capture. Cleanup sends pedal releases and all-notes/sound-off; incomplete captured audio is removed. If using the piano's flash recorder, stop it on the piano as well. The original MIDI and journal stay intact.

High-scoring whole-piece activities are automatically flagged as **Candidates for audio production** after preanalysis when the reference and capture meet the documented checks. This flag helps choose takes; it does not automatically play, capture or render anything. Review the musical performance and actual audio before sharing.

Physical-piano playback and audio routing still require acceptance on your AP-470/interface. Mocked tests check scheduling boundaries, recording exclusion, WAV attachment and cancellation cleanup; they cannot verify the instrument's acoustic result.
