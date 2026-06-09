# Implementation notes

## Version 0.1.10 per-action playback modes and instrument tone test

The Options tab now contains separate playback backend selectors for each playback action: original MIDI, selected modified-version playback, current adjusted preview, EQ/Tone preview, channel test playback and instrument tone test playback.

Defaults are intentionally conservative: longer/full-song checks use the external system player because it is usually more timing-stable on Windows, while channel tests and instrument tone tests use the internal MIDI-output backend so the GUI does not open VLC or another player window for every short audition. The user can override each action independently.

The instrument replacement grid now has a per-row **Test tone** button. It writes a short temporary one-note MIDI file using the selected channel, Bank MSB/LSB, Program Change, channel volume, current channel octave shift and global EQ/Tone controller settings. The base note is middle C.

## Version 0.1.8 playback mode selection and internal player timing

The Main tab no longer exposes separate buttons for external preview and internal current-preview playback. It now uses one **Play MIDI** button for the current adjusted preview. The full-song playback backend is selected in the Options tab:

- external system player, recommended/default,
- internal MIDI output port.

The external system player is now the default for full-song style playback because it can be more timing-stable on Windows setups where Python-driven MIDI-port playback drifts. Once a file is handed to the operating system, the GUI cannot reliably stop the external player process. Since 0.1.10, every playback action has its own internal/external selector.

The internal player also received a timing scheduler fix in 0.1.8. Instead of sleeping every relative MIDI delay and then sending the next message, it precomputes absolute timestamps and schedules each message against a `time.perf_counter()` master clock. This avoids accumulating Python loop overhead across dense MIDI files, which can otherwise make internal playback drift slower than a media player such as VLC.

## Version 0.1.6 README cleanup

The README now opens with a plain-language project explanation and a basic workflow before listing detailed features. This makes the project purpose clearer for users who only want to understand what the tool is for before reading technical details.

## Version 0.1.5 timing preservation

The transformer still keeps source note delta times unchanged when **Song speed = 100%**. Octave changes only alter note numbers, and generated support notes are added on a separate track at tick positions derived from the source notes.

To avoid accidental speed changes in external players, the output MIDI now always starts with a dedicated Track-0 tempo/conductor track:

- source `set_tempo` events are collected with their absolute tick positions,
- tempo events are written to the first output track,
- time-signature and key-signature metadata are mirrored there as musical reference data,
- the original tracks are still transformed and kept after the setup track.

This is mainly for compatibility. Some Windows MIDI players and older tools treat Track 0 as the authoritative tempo map in Type-1 MIDI files. Earlier versions inserted the setup-controller track before the transformed source tracks, so such players could miss tempo changes that were present later in the file and fall back to their default tempo.

The Equalizer / Tone tab now includes **Song speed %**. It intentionally scales MIDI tempo values:

- 100% = original timing,
- 200% = approximately twice as fast,
- 50% = approximately half speed.

This is done by changing tempo meta values, not by moving existing notes.

## Version 0.1.4 setup auto-start

- `setup_online_windows.bat` now calls `run_windows.bat` after successful dependency installation.
- `setup_offline_windows.bat` now calls `run_windows.bat` after successful offline dependency installation, but only when `wheelhouse` exists and contains `.whl` files.
- Both setup scripts use a cancelable 10-second `choice` countdown before launching.
- If offline setup cannot find usable wheelhouse data, it stops and prints clear English instructions explaining how to create/copy the wheelhouse from an internet-connected machine.

## Channel analysis

The analyzer walks every MIDI track and records channel-specific data:

- note count and note range,
- explicit Program Change events,
- current Bank Select MSB/LSB around Program Change events,
- CC7 volume values,
- CC11 expression values,
- track names where a channel appears.

## Instrument replacement

For every unique original instrument reference per channel, the GUI creates a replacement row:

- original instrument info,
- new GM program dropdown,
- program slider,
- Bank MSB slider,
- Bank LSB slider.

When saving, the app inserts the selected bank/program immediately before each matching Program Change event. This keeps later instrument changes in the source MIDI meaningful while still allowing replacement.

## Octave shifting

Channel octave shifting is implemented by transposing note numbers by `octave * 12`, clamped to the MIDI note range 0-127. Event times are not changed by this operation.

## Procedural support notes

The support-note generator:

1. collects source note durations per channel,
2. estimates a simple major/minor key profile from pitch-class usage,
3. adds selected diatonic thirds/fifths at lower velocity,
4. writes them into a separate MIDI track.

The amount slider controls probability and density. This is intentionally conservative so generated notes are supportive rather than chaotic. Generated notes are placed by MIDI tick positions; they do not rewrite the timing of the existing song.

## Playback

Each playback action can use either the external system player or the internal mido/python-rtmidi output-port backend. Channel preview uses a temporary filtered MIDI file where non-selected channel messages are removed while timing is preserved. Instrument tone preview uses a temporary one-note MIDI file. In internal mode, the player emits start/finish/error signals so the triggering Play button can switch to Stop while playback is active and reset itself after playback ends. In external mode, Stop cannot control the external application after the file has been handed off to Windows or the desktop environment.

Version 0.1.3 replaces `MidiFile.play()` with a manual, interruptible timing loop. This matters for Windows MM / rtmidi ports because `MidiFile.play()` sleeps internally; if the user clicks another channel Play button during that sleep, the old output port may still be open and the next `open_output()` call can fail. The new player sends sustain-off, all-sounds-off, reset-all-controllers and all-notes-off controller messages, waits for the old worker thread to exit, and only then opens the next output port.

## Active element highlighting

The main window watches Qt focus changes and applies dynamic properties to the focused widget and relevant slider row parent. A short timer toggles a secondary focus color, producing a subtle pulsing border without requiring external assets or internet access.

## Windows batch color output

Version 0.1.2 removes direct ANSI escape output from the setup/run/build batch scripts. The scripts now print colored status lines through PowerShell `Write-Host` when available and use normal `echo` as a fallback. This keeps the colored section separation while avoiding broken `95m...0m` artifacts in cmd.exe windows without ANSI escape handling.

## Version 0.1.3 playback switching

Starting a different preview while another one is active is now treated as an explicit stop-then-play transition. The old preview is silenced first, the previous worker thread is joined, and the Windows MIDI output port is released before the next playback starts.


## Version 0.1.8 internal player timing notes

The internal MIDI player previously waited for every message's relative delay and then sent the message. For dense MIDI files this means Python loop overhead, Qt/thread scheduling and MIDI-port send overhead can accumulate across thousands of events. The audible result can be a playback that feels slightly slower than an external media player.

Version 0.1.8 precomputes an absolute list of non-meta MIDI events with cumulative timestamps in seconds. Playback uses `time.perf_counter()` as a master clock and waits until each absolute deadline. If a message send takes a little time, the next event is still scheduled against the original song clock instead of against the delayed send time.

On Windows the playback worker temporarily calls `timeBeginPeriod(1)` / `timeEndPeriod(1)` to request better timer granularity during internal playback. This is only active while a file is playing.
