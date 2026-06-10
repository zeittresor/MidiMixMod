# MidiMixMod - MIDI Channel Workbench

MidiMixMod is an offline MIDI editing tool for quickly inspecting and changing existing `.mid` / `.midi` songs without opening a full DAW. You load a MIDI file, see which channels and instruments it uses, adjust the parts you want, preview the result, and save a new modified MIDI file next to the original.

It is useful when you want to:

- find out which MIDI channels and instruments a song uses,
- rebalance channel volumes,
- try other instruments or GM/GS/XG banks,
- move a channel up or down by octaves,
- add simple supporting melody notes,
- make alternate MIDI versions while keeping the original file untouched.

The project is designed for local Windows use. After setup, it does not need internet access to edit or play MIDI files.

<img width="1179" height="833" alt="MidiMixMod_Channel_Workbench_v0_1_10" src="https://github.com/user-attachments/assets/71fb8836-109f-4c0e-93a5-919882ba9daf" />

## Input Example:

https://github.com/user-attachments/assets/c521607a-535b-40ab-8488-3bf4328672da

## Output Example:

https://github.com/user-attachments/assets/7ac17b06-8bc9-460b-945e-c577fb764fc2


## Basic workflow

1. Open a MIDI file on the **Main** tab.
2. Review and change channels on the **Channels / Instruments** tab.
3. Optionally adjust global tone and speed on the **Equalizer / Tone** tab.
4. Choose the playback mode per action in **Options**. Full-song previews default to the external system player; short tests default to the internal MIDI output port.
5. Preview the original, the current edit, individual channels, individual instrument tones, or older modified versions.
6. Save the result as a new file such as `filename_modified_v001.mid`.

## What it does

- Load a `.mid` / `.midi` file with a file dialog.
- Analyze all active MIDI channels in the selected song.
- Show every channel separately in a scrollable channel/instrument tab.
- Show original Program Change events per channel, including raw Bank Select MSB/LSB when present.
- Replace instruments per originally used channel instrument.
- Edit raw Bank Select MSB/LSB for GM/GS/XG-capable synthesizers.
- Change channel volume with sliders.
- Shift a channel by octaves with sliders.
- Optionally generate procedural melody-supporting extra notes per channel.
- Test-play each channel individually.
- Test-play a single selected instrument/bank/program with one middle-C tone, including the current channel octave setting.
- Playback backend can be selected separately for original playback, saved modified playback, current preview, EQ/Tone preview, channel test playback and instrument tone test playback.
- Internal playback: the triggering Play button becomes Stop while that preview is running.
- Switching directly from one internal Play button to another stops the previous playback and releases the MIDI port before starting the next one.
- External playback: the app writes/uses the MIDI file and opens it with the system default player, which is usually more timing-stable on Windows setups where internal MIDI-port playback drifts.
- Main-tab MIDI player for:
  - original MIDI,
  - previously saved modified versions via dropdown,
  - current unsaved adjusted preview via one **Play MIDI** button.
- Playback mode can be selected in Options per action:
  - original MIDI,
  - selected modified file,
  - current adjusted preview,
  - EQ/Tone preview,
  - channel test,
  - instrument tone test.
- Defaults:
  - full-song playback uses the external system player,
  - channel and instrument tests use the internal MIDI output port.
- Equalizer / Tone tab with MIDI-controller based global tone shaping:
  - global volume,
  - song speed percentage,
  - brightness / filter cutoff CC74,
  - resonance CC71,
  - reverb CC91,
  - chorus CC93,
  - pan CC10.
- Save modified files next to the source file as:
  - `filename_modified_v001.mid`
  - `filename_modified_v002.mid`
  - etc.
- Never overwrites existing output files.
- Interface language: English / German.
- Themes: Light, Dark, Sepia, Ocean, Matrix, Hellfire / Hölle, Purple.
- Focused/active controls get a pulsing accent border so it is easier to see where keyboard/mouse focus currently is.
- Vertical scrollbars for long channel lists.

## Important MIDI note about timing

The app changes instruments, controllers, octave-transposed note numbers and optional generated support notes, but it does not change existing note delta times at **Song speed = 100%**. To make saved Type-1 MIDI files more robust across Windows MIDI players, it also writes a dedicated first tempo map track. This matters because some players behave as if tempo belongs in Track 0 even though source MIDI files can store tempo events elsewhere.

## Important MIDI note about GM / GS / XG

The app writes standard MIDI Program Change and Bank Select controller messages:

- CC0 = Bank Select MSB
- CC32 = Bank Select LSB
- Program Change = instrument number 0-127

That means the file can address GM-compatible presets and bank-based GS/XG-like presets. The actual sound still depends on the MIDI synthesizer, SoundFont, or hardware module used for playback.

## Equalizer limitation

A `.mid` file is not rendered audio. Therefore the Equalizer tab cannot apply a true audio EQ directly to a MIDI file. It writes MIDI controller values that many synths interpret as tone/filter/reverb/chorus/pan settings. The Song speed slider is different: it changes MIDI tempo events. At 100%, tempo is left at the original timing. For true bass/mid/treble EQ, render the MIDI to WAV/MP3 first and process the audio.

## Windows setup

### Online setup, once

Run:

```bat
setup_online_windows.bat
```

This will:

1. create `.venv`,
2. upgrade pip inside `.venv`,
3. download binary wheels into `wheelhouse`,
4. install dependencies from `wheelhouse`.

After this, the project can be copied together with `wheelhouse` to an offline machine. When setup succeeds, the script offers a cancelable 10-second countdown and then starts the app automatically via `run_windows.bat`.

### Offline setup

Run:

```bat
setup_offline_windows.bat
```

This installs only from the local `wheelhouse` folder. If `wheelhouse` is missing or empty, the script stops and explains how to create/copy it from an online machine.

### Start app

```bat
run_windows.bat
```

### Build EXE

```bat
build_exe_windows.bat
```

The executable will be placed in `dist\MidiMixMod_Channel_Workbench.exe`.

## MIDI playback on Windows

Playback mode is selected in **Options** separately for each action: original MIDI, selected modified file, current adjusted preview, EQ/Tone preview, channel test playback and instrument tone test playback.

The default and recommended mode for full-song playback is **External system player**. In this mode MidiMixMod writes or reuses the MIDI file and opens it with the Windows default MIDI application, for example VLC or another player. This is often the most timing-stable route because mature media players keep their own playback clock.

The default for channel tests and single-instrument tone tests is **Internal MIDI output port**, because short auditions should not open a new external player window every time. Advanced users can still change those test actions to external playback in Options.

The internal backend sends MIDI messages to an available output port via `mido` / `python-rtmidi`. Since version 0.1.8 it uses absolute `perf_counter()` scheduling instead of sleeping one relative MIDI delay after another, so loop/send overhead should no longer accumulate and gradually stretch dense MIDI files. Internal playback is useful for quick channel tests, but it still depends on the installed Windows MIDI output driver/synth.

Depending on your Windows setup, internal playback may need:

- Microsoft GS Wavetable Synth enabled/available,
- a virtual MIDI synth,
- an external MIDI device,
- or a DAW / FluidSynth / SoundFont-based MIDI output.

If no MIDI output port is detected, use the external playback mode or install/enable a MIDI synthesizer/virtual port for internal playback.

## Project source notice

Original source / updates: github.com/zeittresor

## Changelog

### Version 0.1.11 Options cleanup, output folder controls and optional WAV render

- Removed the static Source and Offline install info blocks from the Options tab.
- Added output/export settings to Options. Modified MIDI files can now be saved beside the original, into an `output` folder beside the app, or into a custom folder.
- Added an optional checkbox to also save a copy next to the source MIDI when the main output folder is somewhere else.
- Added **Open current output folder**.
- Added optional WAV rendering for the current adjusted preview using a local FluidSynth executable plus a selected local `.sf2` / `.sf3` SoundFont.
- WAV files use versioned names such as `filename_rendered_v001.wav` and existing files are not overwritten.

### Version 0.1.10 per-action playback modes and instrument tone test

- Options now contains separate internal/external playback choices for original MIDI, selected modified files, current adjusted preview, EQ/Tone preview, channel test playback and instrument tone test playback.
- Defaults keep the practical behavior: full-song playback opens the external system player, while channel tests and instrument tone tests use the internal MIDI output port.
- The Channels / Instruments tab now adds a **Test tone** button for each instrument replacement row.
- Instrument tone test writes a short temporary MIDI file using the selected channel, selected Bank MSB/LSB, selected Program Change, current channel volume, current octave shift and EQ/Tone controller values.
- The test note is based on middle C so users can quickly audition whether the selected instrument/bank sounds useful before modifying a whole channel.

### Version 0.1.9 channel test playback stays internal

- Channel test playback now always uses the internal MIDI output port, regardless of the full-song playback mode selected in Options.
- This prevents VLC or another external player from opening for every short channel preview.
- This behavior was superseded in 0.1.10 by per-action playback mode selectors, but internal remains the default for channel tests.

### Version 0.1.8 playback mode selection and internal timing scheduler

- The separate **Open externally** and **Play current adjusted preview** buttons were replaced by one **Play MIDI** button for the current adjusted preview.
- The full-song playback method is now selected in **Options**:
  - External system player, recommended/default.
  - Internal MIDI output port.
- In 0.1.8 this selection also affected channel tests; 0.1.9 forced channel tests internal; 0.1.10 replaced that with per-action selectors and kept internal as the default for channel tests.
- External playback is preferred for timing-critical checking, because players such as VLC can keep MIDI playback locked to their own clock.
- Internal playback now builds an absolute event schedule before starting playback.
- Events are sent against a `time.perf_counter()` master clock instead of sleeping each relative MIDI delay separately.
- This avoids accumulated Python loop/send overhead that could make dense MIDI files drift slower than external players.
- On Windows, internal playback temporarily requests 1 ms multimedia timer resolution while a song is playing.
- The player logs a timing note if scheduling lag exceeds roughly 30 ms.

### Version 0.1.7 main player button order

- In the Main tab player row, **Open externally** was placed before **Play current adjusted preview**.
- This made the external player workflow easier to reach before version 0.1.8 replaced the two-button workflow with one Play button and an Options playback-mode selector.

### Version 0.1.6 README cleanup

- README now starts with a simple explanation of what the project is for and what a user can do with it.
- Detailed feature notes were moved below the basic purpose/workflow section.

### Version 0.1.5 timing preservation and song speed

- Modified MIDI files now write a Track-0 tempo map / conductor track.
- Original `set_tempo` events are copied into that tempo map at their original tick positions.
- This avoids accidental playback speed changes in MIDI players that expect tempo events in the first track of a Type-1 MIDI file.
- At the default **Song speed = 100%**, the original tempo/timing is preserved.
- The Equalizer / Tone tab now has **Song speed % (100 = original timing)**.
- Song speed changes are intentional and are implemented by scaling MIDI tempo values, not by moving notes around.
- Note: If it still changes the speed during replay, use external playback instead of the internal player.

### Version 0.1.4 setup auto-start

After a successful setup, both `setup_online_windows.bat` and `setup_offline_windows.bat` now offer a cancelable 10-second countdown and then call `run_windows.bat`. Offline setup only does this when the local `wheelhouse` exists and contains `.whl` files. If the wheelhouse is missing or empty, the script explains in English that the user must run `setup_online_windows.bat` once on an internet-connected Windows machine and then copy the complete project folder including `wheelhouse` to the offline machine.

### Version 0.1.3 playback switching fix

The internal MIDI player no longer relies on `MidiFile.play()` for timing, because that method sleeps internally and is not ideal when a user quickly switches between channel previews. Playback now uses an interruptible timing loop. When another Play button is pressed, the app first sends sustain-off, all-sounds-off, reset-controllers and all-notes-off messages, waits for the old playback thread to exit, and only then opens the MIDI output port again.

### Version 0.1.2 setup-script fix

The Windows batch files no longer emit raw ANSI escape sequences. They now use PowerShell `Write-Host` for colored section/status/error lines and automatically fall back to plain `echo` if PowerShell is unavailable. This avoids broken output such as `95m...0m` in older or differently configured `cmd.exe` sessions.
