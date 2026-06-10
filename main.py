# source: https://github.com/zeittresor
# MidiMixMod Channel Workbench - PyQt6 offline MIDI channel/instrument editor
# Runtime is fully local after dependencies are installed into the local .venv.

from __future__ import annotations

import copy
import hashlib
import os
import random
import sys
import tempfile
import threading
import traceback
import subprocess
import time
import ctypes
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import mido
except Exception as exc:  # pragma: no cover - shown in GUI startup fallback
    mido = None
    MIDO_IMPORT_ERROR = exc
else:
    MIDO_IMPORT_ERROR = None
    try:
        mido.set_backend('mido.backends.rtmidi')
    except Exception:
        pass

from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "MidiMixMod - MIDI Channel Workbench"
APP_VERSION = "0.1.11"
SOURCE_NOTICE = "Original source / updates: github.com/zeittresor"

GM_INSTRUMENTS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
    "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavinet",
    "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ", "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)", "Electric Guitar (jazz)", "Electric Guitar (clean)",
    "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar", "Guitar Harmonics",
    "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)", "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2",
    "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "Synth Strings 1", "Synth Strings 2", "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit",
    "Trumpet", "Trombone", "Tuba", "Muted Trumpet", "French Horn", "Brass Section", "Synth Brass 1", "Synth Brass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe", "English Horn", "Bassoon", "Clarinet",
    "Piccolo", "Flute", "Recorder", "Pan Flute", "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)", "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)", "Lead 7 (fifths)", "Lead 8 (bass + lead)",
    "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)",
    "FX 1 (rain)", "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)", "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bagpipe", "Fiddle", "Shanai",
    "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring", "Helicopter", "Applause", "Gunshot",
]

DRUM_NAMES = [
    "Acoustic Bass Drum", "Bass Drum 1", "Side Stick", "Acoustic Snare", "Hand Clap", "Electric Snare",
    "Low Floor Tom", "Closed Hi-Hat", "High Floor Tom", "Pedal Hi-Hat", "Low Tom", "Open Hi-Hat",
    "Low-Mid Tom", "Hi-Mid Tom", "Crash Cymbal 1", "High Tom", "Ride Cymbal 1", "Chinese Cymbal",
    "Ride Bell", "Tambourine", "Splash Cymbal", "Cowbell", "Crash Cymbal 2", "Vibraslap",
    "Ride Cymbal 2", "Hi Bongo", "Low Bongo", "Mute Hi Conga", "Open Hi Conga", "Low Conga",
    "High Timbale", "Low Timbale", "High Agogo", "Low Agogo", "Cabasa", "Maracas",
    "Short Whistle", "Long Whistle", "Short Guiro", "Long Guiro", "Claves", "Hi Wood Block",
    "Low Wood Block", "Mute Cuica", "Open Cuica", "Mute Triangle", "Open Triangle",
]

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


@dataclass(frozen=True)
class InstrumentRef:
    channel: int
    program: int
    bank_msb: Optional[int]
    bank_lsb: Optional[int]

    def key(self) -> str:
        msb = -1 if self.bank_msb is None else self.bank_msb
        lsb = -1 if self.bank_lsb is None else self.bank_lsb
        return f"{self.channel}:{msb}:{lsb}:{self.program}"

    def short_name(self) -> str:
        bank = f"Bank {self.bank_msb if self.bank_msb is not None else '-'} / {self.bank_lsb if self.bank_lsb is not None else '-'}"
        return f"P{self.program + 1:03d} {GM_INSTRUMENTS[self.program]} ({bank})"


@dataclass
class ProgramEvent:
    abs_tick: int
    track_index: int
    track_name: str
    ref: InstrumentRef


@dataclass
class ChannelAnalysis:
    channel: int
    note_count: int = 0
    min_note: Optional[int] = None
    max_note: Optional[int] = None
    program_events: List[ProgramEvent] = field(default_factory=list)
    volume_values: List[int] = field(default_factory=list)
    expression_values: List[int] = field(default_factory=list)
    used_tracks: List[str] = field(default_factory=list)

    @property
    def unique_refs(self) -> List[InstrumentRef]:
        seen = {}
        for event in self.program_events:
            seen.setdefault(event.ref.key(), event.ref)
        if not seen:
            seen[InstrumentRef(self.channel, 0, None, None).key()] = InstrumentRef(self.channel, 0, None, None)
        return list(seen.values())


@dataclass
class InstrumentOverride:
    program: int
    bank_msb: int = 0
    bank_lsb: int = 0


@dataclass
class ChannelSettings:
    channel: int
    volume_percent: int = 100
    octave_shift: int = 0
    add_notes_enabled: bool = False
    add_notes_amount: int = 0
    overrides: Dict[str, InstrumentOverride] = field(default_factory=dict)


@dataclass
class EqSettings:
    global_volume_percent: int = 100
    song_speed_percent: int = 100
    brightness: int = 64
    resonance: int = 64
    reverb: int = 40
    chorus: int = 0
    pan: int = 64


class MidiAnalyzer:
    @staticmethod
    def analyze(mid) -> Dict[int, ChannelAnalysis]:
        channels = {ch: ChannelAnalysis(channel=ch) for ch in range(16)}
        for track_index, track in enumerate(mid.tracks):
            abs_tick = 0
            track_name = f"Track {track_index + 1}"
            bank_msb = {ch: None for ch in range(16)}
            bank_lsb = {ch: None for ch in range(16)}
            for msg in track:
                abs_tick += int(msg.time)
                if msg.is_meta:
                    if msg.type == "track_name" and getattr(msg, "name", ""):
                        track_name = msg.name
                    continue
                if not hasattr(msg, "channel"):
                    continue
                ch = int(msg.channel)
                analysis = channels[ch]
                if track_name not in analysis.used_tracks:
                    analysis.used_tracks.append(track_name)
                if msg.type == "control_change":
                    if msg.control == 0:
                        bank_msb[ch] = int(msg.value)
                    elif msg.control == 32:
                        bank_lsb[ch] = int(msg.value)
                    elif msg.control == 7:
                        analysis.volume_values.append(int(msg.value))
                    elif msg.control == 11:
                        analysis.expression_values.append(int(msg.value))
                elif msg.type == "program_change":
                    ref = InstrumentRef(ch, int(msg.program), bank_msb[ch], bank_lsb[ch])
                    analysis.program_events.append(ProgramEvent(abs_tick, track_index, track_name, ref))
                elif msg.type == "note_on" and int(msg.velocity) > 0:
                    note = int(msg.note)
                    analysis.note_count += 1
                    analysis.min_note = note if analysis.min_note is None else min(analysis.min_note, note)
                    analysis.max_note = note if analysis.max_note is None else max(analysis.max_note, note)
        return {ch: a for ch, a in channels.items() if a.note_count or a.program_events or a.volume_values or a.expression_values}


class MidiTransformer:
    def __init__(self, mid, settings: Dict[int, ChannelSettings], eq: EqSettings):
        self.mid = mid
        self.settings = settings
        self.eq = eq

    @staticmethod
    def clamp_midi(value: int) -> int:
        return max(0, min(127, int(value)))

    @staticmethod
    def _find_override_for_program(settings: ChannelSettings, ch: int, program: int, bank_msb: Optional[int], bank_lsb: Optional[int]) -> Optional[InstrumentOverride]:
        exact = InstrumentRef(ch, program, bank_msb, bank_lsb).key()
        if exact in settings.overrides:
            return settings.overrides[exact]
        for key, override in settings.overrides.items():
            parts = key.split(":")
            if len(parts) == 4 and int(parts[0]) == ch and int(parts[3]) == program:
                return override
        if settings.overrides:
            return next(iter(settings.overrides.values()))
        return None

    def transformed(self):
        if mido is None:
            raise RuntimeError(f"mido import failed: {MIDO_IMPORT_ERROR}")
        # Type 1 keeps the injected setup/additional-note tracks legal even when the input was Type 0.
        # Track 0 is deliberately a tempo/conductor track. Some Windows players and older
        # MIDI devices only look for tempo changes in the first track of a Type-1 file.
        # Keeping the tempo map there prevents accidental speed changes after modification.
        new_mid = mido.MidiFile(type=1, ticks_per_beat=self.mid.ticks_per_beat, clip=getattr(self.mid, "clip", False))
        new_mid.tracks.append(self._make_tempo_map_track())
        setup_track = self._make_setup_track()
        new_mid.tracks.append(setup_track)
        for track in self.mid.tracks:
            new_mid.tracks.append(self._transform_track(track))
        extra_track = self._make_additional_notes_track()
        if extra_track is not None:
            new_mid.tracks.append(extra_track)
        return new_mid

    @staticmethod
    def _scaled_tempo(tempo: int, speed_percent: int) -> int:
        speed = max(1, min(400, int(speed_percent or 100)))
        return max(1, int(round(int(tempo) * 100 / speed)))

    def _make_tempo_map_track(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="MidiMixMod tempo map", time=0))
        events: List[Tuple[int, int, object]] = []
        seq = 0
        seen = set()
        for source_track in self.mid.tracks:
            abs_tick = 0
            for msg in source_track:
                abs_tick += int(msg.time)
                if not msg.is_meta:
                    continue
                if msg.type == "set_tempo":
                    tempo = self._scaled_tempo(int(msg.tempo), self.eq.song_speed_percent)
                    key = (abs_tick, "set_tempo", tempo)
                    if key in seen:
                        continue
                    seen.add(key)
                    events.append((abs_tick, seq, mido.MetaMessage("set_tempo", tempo=tempo, time=0)))
                    seq += 1
                elif msg.type in {"time_signature", "key_signature"}:
                    # Keep musical reference metadata in the conductor track as well.
                    key = (abs_tick, msg.type, repr(msg.copy(time=0)))
                    if key in seen:
                        continue
                    seen.add(key)
                    events.append((abs_tick, seq, msg.copy(time=0)))
                    seq += 1

        if not any(getattr(event[2], "type", None) == "set_tempo" for event in events) and self.eq.song_speed_percent != 100:
            events.append((0, seq, mido.MetaMessage("set_tempo", tempo=self._scaled_tempo(500000, self.eq.song_speed_percent), time=0)))

        events.sort(key=lambda item: (item[0], item[1]))
        last_tick = 0
        for abs_tick, _seq, msg in events:
            track.append(msg.copy(time=max(0, abs_tick - last_tick)))
            last_tick = abs_tick
        track.append(mido.MetaMessage("end_of_track", time=0))
        return track

    def _make_setup_track(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="MidiMixMod setup controllers", time=0))
        for ch, setting in sorted(self.settings.items()):
            first_override = next(iter(setting.overrides.values()), InstrumentOverride(0, 0, 0))
            volume = self.clamp_midi(round(100 * setting.volume_percent / 100 * self.eq.global_volume_percent / 100))
            for msg in [
                mido.Message("control_change", channel=ch, control=0, value=first_override.bank_msb, time=0),
                mido.Message("control_change", channel=ch, control=32, value=first_override.bank_lsb, time=0),
                mido.Message("program_change", channel=ch, program=first_override.program, time=0),
                mido.Message("control_change", channel=ch, control=7, value=volume, time=0),
                mido.Message("control_change", channel=ch, control=74, value=self.eq.brightness, time=0),
                mido.Message("control_change", channel=ch, control=71, value=self.eq.resonance, time=0),
                mido.Message("control_change", channel=ch, control=91, value=self.eq.reverb, time=0),
                mido.Message("control_change", channel=ch, control=93, value=self.eq.chorus, time=0),
                mido.Message("control_change", channel=ch, control=10, value=self.eq.pan, time=0),
            ]:
                track.append(msg)
        track.append(mido.MetaMessage("end_of_track", time=0))
        return track

    def _transform_track(self, track):
        new_track = mido.MidiTrack()
        bank_msb = {ch: None for ch in range(16)}
        bank_lsb = {ch: None for ch in range(16)}
        for msg in track:
            if msg.is_meta:
                if msg.type == "set_tempo":
                    new_track.append(msg.copy(tempo=self._scaled_tempo(int(msg.tempo), self.eq.song_speed_percent)))
                else:
                    new_track.append(msg.copy())
                continue
            if not hasattr(msg, "channel"):
                new_track.append(msg.copy())
                continue
            ch = int(msg.channel)
            setting = self.settings.get(ch)
            if setting is None:
                new_track.append(msg.copy())
                continue

            if msg.type == "control_change":
                if msg.control == 0:
                    bank_msb[ch] = int(msg.value)
                    new_track.append(msg.copy())
                    continue
                if msg.control == 32:
                    bank_lsb[ch] = int(msg.value)
                    new_track.append(msg.copy())
                    continue
                if msg.control == 7:
                    value = self.clamp_midi(round(msg.value * setting.volume_percent / 100 * self.eq.global_volume_percent / 100))
                    new_track.append(msg.copy(value=value))
                    continue
                if msg.control == 11:
                    value = self.clamp_midi(round(msg.value * self.eq.global_volume_percent / 100))
                    new_track.append(msg.copy(value=value))
                    continue
                if msg.control in {10, 71, 74, 91, 93}:
                    # Existing values stay intact; setup-track values define the initial global tone.
                    new_track.append(msg.copy())
                    continue
                new_track.append(msg.copy())
                continue

            if msg.type == "program_change":
                override = self._find_override_for_program(setting, ch, int(msg.program), bank_msb[ch], bank_lsb[ch])
                if override is None:
                    new_track.append(msg.copy())
                    continue
                # Insert selected bank/program immediately before the original program-change time.
                new_track.append(mido.Message("control_change", channel=ch, control=0, value=override.bank_msb, time=msg.time))
                new_track.append(mido.Message("control_change", channel=ch, control=32, value=override.bank_lsb, time=0))
                new_track.append(msg.copy(program=override.program, time=0))
                continue

            if msg.type in {"note_on", "note_off", "polytouch"} and hasattr(msg, "note"):
                new_note = self.clamp_midi(int(msg.note) + setting.octave_shift * 12)
                new_track.append(msg.copy(note=new_note))
                continue

            new_track.append(msg.copy())
        return new_track

    def _collect_note_pairs(self) -> Dict[int, List[Tuple[int, int, int, int]]]:
        notes_by_channel: Dict[int, List[Tuple[int, int, int, int]]] = {ch: [] for ch in range(16)}
        for track in self.mid.tracks:
            abs_tick = 0
            active: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
            for msg in track:
                abs_tick += int(msg.time)
                if msg.is_meta or not hasattr(msg, "channel"):
                    continue
                ch = int(msg.channel)
                if msg.type == "note_on" and int(msg.velocity) > 0:
                    active.setdefault((ch, int(msg.note)), []).append((abs_tick, int(msg.velocity)))
                elif msg.type in {"note_off", "note_on"} and hasattr(msg, "note"):
                    key = (ch, int(msg.note))
                    if key in active and active[key]:
                        start, vel = active[key].pop(0)
                        duration = max(1, abs_tick - start)
                        notes_by_channel[ch].append((start, duration, int(msg.note), vel))
        return notes_by_channel

    @staticmethod
    def _infer_key(notes: List[Tuple[int, int, int, int]]) -> Tuple[int, str, List[int]]:
        histogram = [0.0] * 12
        for _start, duration, note, velocity in notes:
            histogram[note % 12] += max(1, duration) * max(1, velocity)
        best_score = float("-inf")
        best_root = 0
        best_mode = "major"
        for root in range(12):
            major_score = sum(histogram[(root + i) % 12] * MAJOR_PROFILE[i] for i in range(12))
            minor_score = sum(histogram[(root + i) % 12] * MINOR_PROFILE[i] for i in range(12))
            if major_score > best_score:
                best_score = major_score
                best_root = root
                best_mode = "major"
            if minor_score > best_score:
                best_score = minor_score
                best_root = root
                best_mode = "minor"
        scale = MAJOR_SCALE if best_mode == "major" else MINOR_SCALE
        return best_root, best_mode, scale

    @staticmethod
    def _scale_note(note: int, root: int, scale: List[int], steps: int) -> int:
        # Pick a diatonic pitch steps above the source note and keep it close enough to function as a support melody.
        source_pc = note % 12
        source_oct = note // 12
        candidates = []
        for octave in range(source_oct - 1, source_oct + 3):
            for degree_index, degree in enumerate(scale):
                pitch = octave * 12 + root + degree
                candidates.append((abs(pitch - note), pitch, degree_index, octave))
        candidates.sort(key=lambda item: item[0])
        _, base_pitch, base_degree, base_oct = candidates[0]
        target_degree_total = base_degree + steps
        target_oct = base_oct + target_degree_total // len(scale)
        target_degree = target_degree_total % len(scale)
        target_pitch = target_oct * 12 + root + scale[target_degree]
        while target_pitch <= note:
            target_pitch += 12
        return max(0, min(127, target_pitch))

    def _make_additional_notes_track(self):
        active_channels = [ch for ch, setting in self.settings.items() if setting.add_notes_enabled and setting.add_notes_amount > 0]
        if not active_channels:
            return None
        notes_by_channel = self._collect_note_pairs()
        events: List[Tuple[int, int, object]] = []
        for ch in active_channels:
            setting = self.settings[ch]
            notes = notes_by_channel.get(ch, [])
            if not notes:
                continue
            root, _mode, scale = self._infer_key(notes)
            seed_source = f"{len(notes)}:{ch}:{setting.add_notes_amount}:{self.mid.ticks_per_beat}".encode("utf-8")
            seed = int(hashlib.sha256(seed_source).hexdigest()[:16], 16)
            rng = random.Random(seed)
            probability = setting.add_notes_amount / 100.0
            max_per_channel = max(8, int(len(notes) * probability * 0.45))
            added = 0
            first_override = next(iter(setting.overrides.values()), InstrumentOverride(0, 0, 0))
            events.append((0, 0, mido.Message("control_change", channel=ch, control=0, value=first_override.bank_msb, time=0)))
            events.append((0, 1, mido.Message("control_change", channel=ch, control=32, value=first_override.bank_lsb, time=0)))
            events.append((0, 2, mido.Message("program_change", channel=ch, program=first_override.program, time=0)))
            for start, duration, note, velocity in notes:
                if added >= max_per_channel:
                    break
                if rng.random() > probability:
                    continue
                steps = 2 if rng.random() < 0.70 else 4  # diatonic third/fifth
                new_note = self._scale_note(note + setting.octave_shift * 12, root, scale, steps)
                delay = 0 if rng.random() < 0.65 else max(1, self.mid.ticks_per_beat // 4)
                new_start = start + delay
                new_duration = max(1, min(duration, self.mid.ticks_per_beat))
                new_velocity = self.clamp_midi(round(velocity * 0.58 * self.eq.global_volume_percent / 100))
                events.append((new_start, 3, mido.Message("note_on", channel=ch, note=new_note, velocity=new_velocity, time=0)))
                events.append((new_start + new_duration, 2, mido.Message("note_off", channel=ch, note=new_note, velocity=0, time=0)))
                added += 1
        if len(events) <= 3:
            return None
        events.sort(key=lambda item: (item[0], item[1]))
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="MidiMixMod procedural support notes", time=0))
        last_tick = 0
        for abs_tick, _order, msg in events:
            msg = msg.copy(time=max(0, abs_tick - last_tick))
            track.append(msg)
            last_tick = abs_tick
        track.append(mido.MetaMessage("end_of_track", time=0))
        return track


class MidiPlayer(QObject):
    playback_started = pyqtSignal(str)
    playback_finished = pyqtSignal(str)
    playback_error = pyqtSignal(str, str)

    def __init__(self, log_callback):
        super().__init__()
        self.log = log_callback
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._play_token = 0
        self._token_lock = threading.Lock()
        self._port_lock = threading.RLock()
        self._current_port = None

    def output_names(self) -> List[str]:
        if mido is None:
            return []
        try:
            return list(mido.get_output_names())
        except Exception as exc:
            self.log(f"MIDI output listing failed: {exc}")
            return []

    def is_playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def stop(self, wait: bool = True) -> bool:
        """Request a hard stop and optionally wait until the MIDI port is released.

        mido.MidiFile.play() sleeps internally and cannot be interrupted quickly.
        This player therefore uses its own interruptible timing loop in _play_worker.
        stop() also sends panic/all-notes-off/reset-controller messages to avoid
        hanging notes when the user jumps directly from one channel preview to another.
        """
        self._stop_event.set()
        self._panic_current_port()

        thread = self._thread
        if wait and thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3.0)
            if thread.is_alive():
                # Last resort: close the still-open port so Windows MM/rtmidi releases it.
                # The worker will notice this and exit; the next playback should not try
                # to open a second Windows MIDI port while the old one is still active.
                self._close_current_port()
                thread.join(timeout=1.0)
        return self._thread is None or not self._thread.is_alive()

    def _panic_current_port(self):
        with self._port_lock:
            port = self._current_port
        if port is None:
            return
        try:
            if hasattr(port, "panic"):
                port.panic()
        except Exception:
            pass
        try:
            self._send_all_notes_off(port)
        except Exception:
            pass
        try:
            if hasattr(port, "reset"):
                port.reset()
        except Exception:
            pass

    def _close_current_port(self):
        with self._port_lock:
            port = self._current_port
        if port is None:
            return
        try:
            port.close()
        except Exception:
            pass

    @staticmethod
    def _send_all_notes_off(port):
        if mido is None:
            return
        for channel in range(16):
            # Pedal off, all sounds off, reset all controllers, all notes off.
            for control, value in ((64, 0), (120, 0), (121, 0), (123, 0)):
                try:
                    port.send(mido.Message("control_change", channel=channel, control=control, value=value, time=0))
                except Exception:
                    # Some MIDI backends/devices are strict; keep trying the remaining channels.
                    pass

    def play_file(self, path: Path, output_name: Optional[str] = None, label: Optional[str] = None):
        if mido is None:
            raise RuntimeError(f"mido import failed: {MIDO_IMPORT_ERROR}")
        if not path.exists():
            raise FileNotFoundError(path)

        stopped = self.stop(wait=True)
        if not stopped:
            raise RuntimeError(
                "The previous MIDI playback is still shutting down. Please try again in a moment."
            )

        stop_event = threading.Event()
        self._stop_event = stop_event
        with self._token_lock:
            self._play_token += 1
            token = self._play_token
        display_label = label or path.name
        self.playback_started.emit(display_label)
        self._thread = threading.Thread(
            target=self._play_worker,
            args=(token, path, output_name, display_label, stop_event),
            daemon=True,
        )
        self._thread.start()

    def _is_current_token(self, token: int) -> bool:
        with self._token_lock:
            return token == self._play_token

    @staticmethod
    def _build_playback_events(path: Path) -> Tuple[List[Tuple[float, object]], float]:
        """Return non-meta MIDI events with absolute playback timestamps in seconds.

        mido exposes msg.time as a relative delay in seconds during iteration.
        Summing those delays once up front lets the player use absolute deadlines.
        That prevents Python/send overhead from accumulating and slowly stretching
        dense MIDI files during internal playback.
        """
        mid = mido.MidiFile(path)
        absolute_seconds = 0.0
        events: List[Tuple[float, object]] = []
        for msg in mid:
            absolute_seconds += float(getattr(msg, "time", 0) or 0.0)
            if not msg.is_meta:
                # The output port ignores msg.time, but keep it at zero so the event
                # object clearly represents an immediate send at its scheduled deadline.
                events.append((absolute_seconds, msg.copy(time=0)))
        return events, absolute_seconds

    @staticmethod
    def _begin_high_resolution_timer() -> bool:
        """Ask Windows for 1 ms timer resolution while internal playback is active."""
        if not sys.platform.startswith("win"):
            return False
        try:
            return ctypes.windll.winmm.timeBeginPeriod(1) == 0  # type: ignore[attr-defined]
        except Exception:
            return False

    @staticmethod
    def _end_high_resolution_timer(active: bool):
        if not active or not sys.platform.startswith("win"):
            return
        try:
            ctypes.windll.winmm.timeEndPeriod(1)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _play_worker(self, token: int, path: Path, output_name: Optional[str], label: str, stop_event: threading.Event):
        port = None
        timer_active = False
        try:
            events, duration = self._build_playback_events(path)
            if output_name:
                out_ctx = mido.open_output(output_name)
            else:
                out_ctx = mido.open_output()
            with out_ctx as port:
                with self._port_lock:
                    self._current_port = port
                self.log(f"Playing: {path.name} ({len(events)} events, {duration:.2f}s)")

                # Timing fix: older builds slept for each message delay separately.
                # That makes send/loop overhead accumulate, so dense songs can drift
                # slower than external players. Here every event is sent against an
                # absolute perf_counter() deadline, similar in spirit to how real
                # media players keep a master clock.
                timer_active = self._begin_high_resolution_timer()
                start_time = time.perf_counter()
                max_late = 0.0

                for target_seconds, msg in events:
                    target_time = start_time + target_seconds
                    while True:
                        if stop_event.is_set():
                            break
                        remaining = target_time - time.perf_counter()
                        if remaining <= 0:
                            break
                        # Keep Stop responsive while still avoiding a CPU-heavy busy wait.
                        if stop_event.wait(min(remaining, 0.005)):
                            break
                    if stop_event.is_set():
                        break
                    late = time.perf_counter() - target_time
                    if late > max_late:
                        max_late = late
                    try:
                        port.send(msg)
                    except Exception:
                        if stop_event.is_set():
                            break
                        raise

                if max_late > 0.030:
                    self.log(f"Internal player timing note: max scheduling lag was {max_late * 1000:.1f} ms.")

                try:
                    self._send_all_notes_off(port)
                except Exception:
                    pass
                try:
                    if hasattr(port, "reset"):
                        port.reset()
                except Exception:
                    pass
            self.log("Playback stopped/finished.")
        except Exception as exc:
            self.log(f"MIDI playback failed: {exc}")
            if self._is_current_token(token):
                self.playback_error.emit(label, str(exc))
        finally:
            self._end_high_resolution_timer(timer_active)
            with self._port_lock:
                if self._current_port is port:
                    self._current_port = None
            if self._is_current_token(token):
                self.playback_finished.emit(label)


class SliderRow(QWidget):
    def __init__(self, minimum: int, maximum: int, value: int, suffix: str = "", orientation=Qt.Orientation.Horizontal):
        super().__init__()
        self.setObjectName("sliderRow")
        self.slider = QSlider(orientation)
        self.slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setValue(value)
        self.suffix = suffix
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)

    def value(self) -> int:
        return int(self.spin.value())

    def setValue(self, value: int):
        self.spin.setValue(value)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1180, 820)
        self.mid = None
        self.source_path: Optional[Path] = None
        self.analysis: Dict[int, ChannelAnalysis] = {}
        self.channel_settings: Dict[int, ChannelSettings] = {}
        self.eq_settings = EqSettings()
        self.channel_widgets: Dict[int, Dict[str, object]] = {}
        self.instrument_widgets: Dict[Tuple[int, str], Dict[str, object]] = {}
        self.player = MidiPlayer(self.log)
        self.player.playback_finished.connect(self._on_playback_finished)
        self.player.playback_error.connect(self._on_playback_error)
        self.language = "English"
        self.theme_name = "Dark"
        self.active_play_key: Optional[str] = None
        self.active_play_button: Optional[QPushButton] = None
        self.play_button_base_texts: Dict[QPushButton, str] = {}
        self.playback_mode_combos: Dict[str, QComboBox] = {}
        self.playback_mode_labels: Dict[str, QLabel] = {}
        self.output_mode = "source"
        self.output_custom_dir: Optional[Path] = None
        self._focus_targets: List[QWidget] = []
        self._focus_pulse = False
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._pulse_focused_widget)
        self._focus_timer.start(520)
        QApplication.instance().focusChanged.connect(self._on_focus_changed)
        self._build_menu()
        self._build_ui()
        self.apply_theme("Dark")
        self.refresh_ports()
        if mido is None:
            self.log(f"ERROR: mido could not be imported: {MIDO_IMPORT_ERROR}")

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        open_action = QAction("Open MIDI...", self)
        open_action.triggered.connect(self.browse_midi)
        file_menu.addAction(open_action)
        save_action = QAction("Save modified MIDI", self)
        save_action.triggered.connect(self.save_modified)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        playback_menu = menu.addMenu("Playback")
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.stop_playback)
        playback_menu.addAction(stop_action)

        help_menu = menu.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _build_ui(self):
        root = QWidget()
        main_layout = QVBoxLayout(root)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        self.setCentralWidget(root)
        self._build_main_tab()
        self._build_channels_tab()
        self._build_eq_tab()
        self._build_options_tab()

    def _build_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        source_group = QGroupBox("MIDI file")
        source_layout = QGridLayout(source_group)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse MIDI...")
        self.browse_button.clicked.connect(self.browse_midi)
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.clicked.connect(self.analyze_current)
        source_layout.addWidget(QLabel("Source MIDI:"), 0, 0)
        source_layout.addWidget(self.path_edit, 0, 1)
        source_layout.addWidget(self.browse_button, 0, 2)
        source_layout.addWidget(self.analyze_button, 0, 3)
        layout.addWidget(source_group)

        player_group = QGroupBox("Player")
        player_layout = QGridLayout(player_group)
        self.port_combo = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh MIDI outputs")
        self.refresh_ports_button.clicked.connect(self.refresh_ports)
        self.play_original_button = QPushButton("Play original")
        self.play_original_button.clicked.connect(lambda _checked=False: self.play_original(self.play_original_button))
        self.modified_combo = QComboBox()
        self.play_modified_button = QPushButton("Play selected modified")
        self.play_modified_button.clicked.connect(lambda _checked=False: self.play_selected_modified(self.play_modified_button))
        self.play_current_button = QPushButton("Play MIDI")
        self.play_current_button.clicked.connect(lambda _checked=False: self.play_current_preview(self.play_current_button))
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_playback)
        player_layout.addWidget(QLabel("MIDI output:"), 0, 0)
        player_layout.addWidget(self.port_combo, 0, 1)
        player_layout.addWidget(self.refresh_ports_button, 0, 2)
        player_layout.addWidget(self.play_original_button, 1, 0)
        player_layout.addWidget(QLabel("Previous modified:"), 1, 1)
        player_layout.addWidget(self.modified_combo, 1, 2)
        player_layout.addWidget(self.play_modified_button, 1, 3)
        player_layout.addWidget(self.play_current_button, 2, 0)
        player_layout.addWidget(self.stop_button, 2, 1)
        layout.addWidget(player_group)

        save_group = QGroupBox("Save")
        save_layout = QHBoxLayout(save_group)
        self.save_button = QPushButton("Save as new modified MIDI")
        self.save_button.clicked.connect(self.save_modified)
        save_layout.addWidget(self.save_button)
        save_layout.addWidget(QLabel("Existing files are never overwritten; names use _modified_v001.mid, _modified_v002.mid, ..."))
        layout.addWidget(save_group)

        self.summary_box = QPlainTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setPlaceholderText("Load a MIDI file to see analysis and status messages.")
        layout.addWidget(self.summary_box, 1)
        self.tabs.addTab(tab, "Main")

    def _build_channels_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.channel_scroll = QScrollArea()
        self.channel_scroll.setWidgetResizable(True)
        self.channel_container = QWidget()
        self.channel_layout = QVBoxLayout(self.channel_container)
        self.channel_layout.addWidget(QLabel("Load and analyze a MIDI file first."))
        self.channel_layout.addStretch(1)
        self.channel_scroll.setWidget(self.channel_container)
        layout.addWidget(self.channel_scroll)
        self.tabs.addTab(tab, "Channels / Instruments")

    def _build_eq_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        self.eq_global_volume = SliderRow(0, 200, self.eq_settings.global_volume_percent)
        self.eq_song_speed = SliderRow(50, 200, self.eq_settings.song_speed_percent)
        self.eq_brightness = SliderRow(0, 127, self.eq_settings.brightness)
        self.eq_resonance = SliderRow(0, 127, self.eq_settings.resonance)
        self.eq_reverb = SliderRow(0, 127, self.eq_settings.reverb)
        self.eq_chorus = SliderRow(0, 127, self.eq_settings.chorus)
        self.eq_pan = SliderRow(0, 127, self.eq_settings.pan)
        form.addRow("Global volume %", self.eq_global_volume)
        form.addRow("Song speed % (100 = original timing)", self.eq_song_speed)
        form.addRow("Brightness / filter cutoff CC74", self.eq_brightness)
        form.addRow("Resonance CC71", self.eq_resonance)
        form.addRow("Reverb send CC91", self.eq_reverb)
        form.addRow("Chorus send CC93", self.eq_chorus)
        form.addRow("Pan CC10", self.eq_pan)
        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(145)
        info.setPlainText(
            "MIDI files do not contain rendered audio, so this tab writes MIDI controller values instead of applying a real audio EQ. "
            "Song speed changes are implemented by scaling MIDI tempo events; at 100% the original timing is preserved exactly. "
            "The audible tone result depends on the selected synthesizer or SoundFont. For true bass/mid/treble EQ, render the MIDI to WAV first and process that audio."
        )
        form.addRow("Info", info)
        play_row = QHBoxLayout()
        self.eq_preview_button = QPushButton("Play with current EQ settings")
        self.eq_preview_button.clicked.connect(lambda _checked=False: self.play_eq_preview(self.eq_preview_button))
        self.eq_save_button = QPushButton("Save with current EQ settings")
        self.eq_save_button.clicked.connect(self.save_modified)
        play_row.addWidget(self.eq_preview_button)
        play_row.addWidget(self.eq_save_button)
        form.addRow(play_row)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "Equalizer / Tone")

    def _build_options_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Deutsch"])
        self.language_combo.currentTextChanged.connect(self.apply_language)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Sepia", "Ocean", "Matrix", "Hellfire / Hölle", "Purple"])
        self.theme_combo.setCurrentText("Dark")
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        form.addRow("Interface language", self.language_combo)
        form.addRow("Theme", self.theme_combo)
        self._add_playback_mode_row(form, "original", "Playback mode: original MIDI", "Wiedergabe: Original-MIDI", "external")
        self._add_playback_mode_row(form, "modified", "Playback mode: selected modified file", "Wiedergabe: gewählte modifizierte Datei", "external")
        self._add_playback_mode_row(form, "current_preview", "Playback mode: current adjusted preview", "Wiedergabe: aktuelle angepasste Vorschau", "external")
        self._add_playback_mode_row(form, "eq_preview", "Playback mode: EQ/Tone preview", "Wiedergabe: EQ/Klang-Vorschau", "external")
        self._add_playback_mode_row(form, "channel_test", "Playback mode: channel test", "Wiedergabe: Channel-Test", "internal")
        self._add_playback_mode_row(form, "instrument_test", "Playback mode: instrument tone test", "Wiedergabe: Instrument-Tontest", "internal")
        form.addRow(self._make_separator_label("Output / Export"))
        self.output_mode_combo = QComboBox()
        self._populate_output_mode_combo(self.language)
        self.output_mode_combo.currentIndexChanged.connect(self._on_output_mode_changed)
        form.addRow("Save modified MIDI to", self.output_mode_combo)

        custom_output_row = QHBoxLayout()
        self.output_custom_edit = QLineEdit()
        self.output_custom_edit.setPlaceholderText("Optional custom output folder")
        self.output_custom_browse_button = QPushButton("Browse output folder...")
        self.output_custom_browse_button.clicked.connect(self.browse_output_folder)
        custom_output_row.addWidget(self.output_custom_edit, 1)
        custom_output_row.addWidget(self.output_custom_browse_button)
        form.addRow("Custom output folder", custom_output_row)

        self.output_copy_source_checkbox = QCheckBox("Also save a copy next to the source MIDI")
        self.output_copy_source_checkbox.setChecked(False)
        form.addRow("Extra copy", self.output_copy_source_checkbox)

        self.open_output_folder_button = QPushButton("Open current output folder")
        self.open_output_folder_button.clicked.connect(self.open_current_output_folder)
        form.addRow("Output folder", self.open_output_folder_button)

        form.addRow(self._make_separator_label("Optional WAV rendering"))
        self.fluidsynth_path_edit = QLineEdit()
        self.fluidsynth_path_edit.setPlaceholderText("fluidsynth.exe or leave empty to search PATH")
        fluidsynth_row = QHBoxLayout()
        self.fluidsynth_browse_button = QPushButton("Browse FluidSynth...")
        self.fluidsynth_browse_button.clicked.connect(self.browse_fluidsynth_exe)
        fluidsynth_row.addWidget(self.fluidsynth_path_edit, 1)
        fluidsynth_row.addWidget(self.fluidsynth_browse_button)
        form.addRow("FluidSynth executable", fluidsynth_row)

        self.soundfont_path_edit = QLineEdit()
        self.soundfont_path_edit.setPlaceholderText("Select .sf2 / .sf3 SoundFont")
        soundfont_row = QHBoxLayout()
        self.soundfont_browse_button = QPushButton("Browse SoundFont...")
        self.soundfont_browse_button.clicked.connect(self.browse_soundfont_file)
        soundfont_row.addWidget(self.soundfont_path_edit, 1)
        soundfont_row.addWidget(self.soundfont_browse_button)
        form.addRow("SoundFont", soundfont_row)

        self.render_samplerate_combo = QComboBox()
        self.render_samplerate_combo.addItems(["22050", "44100", "48000", "96000"])
        self.render_samplerate_combo.setCurrentText("44100")
        form.addRow("WAV sample rate", self.render_samplerate_combo)

        render_row = QHBoxLayout()
        self.render_current_wav_button = QPushButton("Render current adjusted preview as WAV")
        self.render_current_wav_button.clicked.connect(self.render_current_preview_wav)
        render_row.addWidget(self.render_current_wav_button)
        form.addRow(render_row)

        self._on_output_mode_changed()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "Options")

    def _make_separator_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        return label

    def _output_mode_text(self, mode: str, language: Optional[str] = None) -> str:
        language = language or self.language
        if language == "Deutsch":
            return {
                "source": "Original-MIDI-Ordner",
                "project_output": "Output-Ordner im Programmverzeichnis",
                "custom": "Eigener Ausgabeordner",
            }.get(mode, mode)
        return {
            "source": "Original MIDI folder",
            "project_output": "Output folder in program directory",
            "custom": "Custom output folder",
        }.get(mode, mode)

    def _populate_output_mode_combo(self, language: str):
        if not hasattr(self, "output_mode_combo"):
            return
        current_mode = self.output_mode_combo.currentData() or getattr(self, "output_mode", "source")
        if current_mode not in {"source", "project_output", "custom"}:
            current_mode = "source"
        self.output_mode_combo.blockSignals(True)
        self.output_mode_combo.clear()
        for mode in ["source", "project_output", "custom"]:
            self.output_mode_combo.addItem(self._output_mode_text(mode, language), mode)
        idx = self.output_mode_combo.findData(current_mode)
        self.output_mode_combo.setCurrentIndex(max(0, idx))
        self.output_mode_combo.blockSignals(False)

    def _on_output_mode_changed(self):
        if not hasattr(self, "output_mode_combo"):
            return
        data = self.output_mode_combo.currentData()
        self.output_mode = str(data) if data in {"source", "project_output", "custom"} else "source"
        custom = self.output_mode == "custom"
        if hasattr(self, "output_custom_edit"):
            self.output_custom_edit.setEnabled(custom)
        if hasattr(self, "output_custom_browse_button"):
            self.output_custom_browse_button.setEnabled(custom)
        if hasattr(self, "output_copy_source_checkbox"):
            self.output_copy_source_checkbox.setEnabled(self.output_mode != "source")
        if getattr(self, "source_path", None) is not None and hasattr(self, "modified_combo"):
            self.refresh_modified_history()

    def browse_output_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select output folder", str(self.current_output_directory(create=False)))
        if not directory:
            return
        self.output_custom_dir = Path(directory)
        self.output_custom_edit.setText(str(self.output_custom_dir))

    def current_output_directory(self, create: bool = True) -> Path:
        mode = getattr(self, "output_mode", "source")
        if hasattr(self, "output_mode_combo"):
            data = self.output_mode_combo.currentData()
            if data in {"source", "project_output", "custom"}:
                mode = str(data)
        if mode == "source":
            if self.source_path is not None:
                directory = self.source_path.parent
            else:
                directory = Path.cwd()
        elif mode == "project_output":
            directory = Path(__file__).resolve().parent / "output"
        else:
            text = self.output_custom_edit.text().strip() if hasattr(self, "output_custom_edit") else ""
            if text:
                directory = Path(text)
            elif self.output_custom_dir is not None:
                directory = self.output_custom_dir
            else:
                directory = Path(__file__).resolve().parent / "output"
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        return directory

    def open_current_output_folder(self):
        try:
            self._open_file_external(self.current_output_directory(create=True))
        except Exception as exc:
            QMessageBox.critical(self, "Open output folder failed", str(exc))

    def browse_fluidsynth_exe(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select FluidSynth executable", "", "Executable files (*.exe);;All files (*.*)")
        if file_name:
            self.fluidsynth_path_edit.setText(file_name)

    def browse_soundfont_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select SoundFont", "", "SoundFont files (*.sf2 *.sf3);;All files (*.*)")
        if file_name:
            self.soundfont_path_edit.setText(file_name)

    def _playback_mode_text(self, mode: str, language: Optional[str] = None) -> str:
        language = language or self.language
        if language == "Deutsch":
            if mode == "external":
                return "Externer System-Player (empfohlen)"
            return "Interner MIDI-Ausgangsport"
        if mode == "external":
            return "External system player (recommended)"
        return "Internal MIDI output port"

    def _add_playback_mode_row(self, form: QFormLayout, key: str, label_en: str, label_de: str, default_mode: str):
        label = QLabel(label_en)
        label.setProperty("label_en", label_en)
        label.setProperty("label_de", label_de)
        combo = QComboBox()
        combo.setProperty("default_mode", default_mode)
        self.playback_mode_labels[key] = label
        self.playback_mode_combos[key] = combo
        self._populate_playback_mode_combo(combo, self.language, default_mode)
        form.addRow(label, combo)

    def _populate_playback_mode_combo(self, combo: QComboBox, language: str, fallback_mode: str = "external"):
        """Populate one playback-mode combo while preserving its current value."""
        current_mode = combo.currentData()
        if current_mode not in {"external", "internal"}:
            current_mode = combo.property("default_mode") or fallback_mode
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(self._playback_mode_text("external", language), "external")
        combo.addItem(self._playback_mode_text("internal", language), "internal")
        idx = combo.findData(current_mode)
        if idx < 0:
            idx = combo.findData(fallback_mode)
        if idx < 0:
            idx = 0
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _populate_all_playback_mode_combos(self, language: str):
        for key, combo in self.playback_mode_combos.items():
            fallback = combo.property("default_mode") or "external"
            self._populate_playback_mode_combo(combo, language, str(fallback))
        for key, label in self.playback_mode_labels.items():
            text = label.property("label_de") if language == "Deutsch" else label.property("label_en")
            if text:
                label.setText(str(text))

    def playback_mode_for(self, key: str) -> str:
        combo = self.playback_mode_combos.get(key)
        if combo is not None:
            data = combo.currentData()
            if data in {"external", "internal"}:
                return str(data)
        # Safe defaults: full-song playback external for better timing on many Windows setups;
        # short auditions internal so they remain quick and don't spawn player windows by default.
        if key in {"channel_test", "instrument_test"}:
            return "internal"
        return "external"

    def _open_file_external(self, path: Path):
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def log(self, message: str):
        def append():
            self.summary_box.appendPlainText(str(message))
        if hasattr(self, "summary_box"):
            QTimer.singleShot(0, append)

    def show_about(self):
        QMessageBox.information(
            self,
            "About",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "PyQt6 + mido based local MIDI channel/instrument editor.\n"
            "Supports GM Program Change plus raw Bank Select MSB/LSB for GS/XG-capable synths.\n\n"
            f"{SOURCE_NOTICE}",
        )

    def _repolish(self, widget: Optional[QWidget]):
        if widget is None:
            return
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _focus_related_widgets(self, widget: Optional[QWidget]) -> List[QWidget]:
        if widget is None:
            return []
        targets: List[QWidget] = []
        current = widget
        while current is not None and current is not self:
            if isinstance(current, (QPushButton, QComboBox, QSpinBox, QLineEdit, QTextEdit, QPlainTextEdit, QSlider, QCheckBox, SliderRow)):
                targets.append(current)
            if isinstance(current, SliderRow):
                break
            current = current.parentWidget()
        return targets

    def _on_focus_changed(self, old: Optional[QWidget], new: Optional[QWidget]):
        for target in self._focus_targets:
            target.setProperty("activeFocus", False)
            target.setProperty("focusPulse", False)
            self._repolish(target)
        self._focus_targets = self._focus_related_widgets(new)
        self._focus_pulse = False
        for target in self._focus_targets:
            target.setProperty("activeFocus", True)
            target.setProperty("focusPulse", False)
            self._repolish(target)

    def _pulse_focused_widget(self):
        if not self._focus_targets:
            return
        self._focus_pulse = not self._focus_pulse
        for target in self._focus_targets:
            target.setProperty("focusPulse", self._focus_pulse)
            self._repolish(target)

    def browse_midi(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open MIDI file", "", "MIDI files (*.mid *.midi);;All files (*.*)")
        if not file_name:
            return
        self.load_midi(Path(file_name))

    def load_midi(self, path: Path):
        if mido is None:
            QMessageBox.critical(self, "Missing dependency", f"mido could not be imported:\n{MIDO_IMPORT_ERROR}")
            return
        try:
            self.mid = mido.MidiFile(path)
            self.source_path = path
            self.path_edit.setText(str(path))
            self.log(f"Loaded: {path}")
            self.analyze_current()
            self.refresh_modified_history()
        except Exception as exc:
            QMessageBox.critical(self, "MIDI load failed", str(exc))
            self.log(traceback.format_exc())

    def analyze_current(self):
        if self.mid is None:
            QMessageBox.warning(self, "No MIDI", "Please load a MIDI file first.")
            return
        self.analysis = MidiAnalyzer.analyze(self.mid)
        self._make_default_settings()
        self.rebuild_channel_tab()
        self.print_analysis_summary()

    def _make_default_settings(self):
        self.channel_settings = {}
        for ch, analysis in self.analysis.items():
            setting = ChannelSettings(channel=ch)
            for ref in analysis.unique_refs:
                setting.overrides[ref.key()] = InstrumentOverride(
                    program=ref.program,
                    bank_msb=0 if ref.bank_msb is None else ref.bank_msb,
                    bank_lsb=0 if ref.bank_lsb is None else ref.bank_lsb,
                )
            self.channel_settings[ch] = setting

    def print_analysis_summary(self):
        if self.source_path is None:
            return
        lines = [
            "",
            f"Analysis for {self.source_path.name}",
            f"MIDI type: {self.mid.type} | tracks: {len(self.mid.tracks)} | ticks/beat: {self.mid.ticks_per_beat}",
            f"Detected active channels: {', '.join(str(ch + 1) for ch in sorted(self.analysis)) or 'none'}",
        ]
        for ch, analysis in sorted(self.analysis.items()):
            note_range = "-" if analysis.min_note is None else f"{analysis.min_note}..{analysis.max_note}"
            refs = ", ".join(ref.short_name() for ref in analysis.unique_refs)
            lines.append(f"Channel {ch + 1:02d}: notes={analysis.note_count}, range={note_range}, instruments={refs}")
        self.log("\n".join(lines))

    def rebuild_channel_tab(self):
        while self.channel_layout.count():
            item = self.channel_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.channel_widgets.clear()
        self.instrument_widgets.clear()
        if not self.analysis:
            self.channel_layout.addWidget(QLabel("No channel data found."))
            self.channel_layout.addStretch(1)
            return
        for ch, analysis in sorted(self.analysis.items()):
            self.channel_layout.addWidget(self._make_channel_group(ch, analysis))
        self.channel_layout.addStretch(1)

    def _make_channel_group(self, ch: int, analysis: ChannelAnalysis) -> QGroupBox:
        group = QGroupBox(f"Channel {ch + 1:02d}" + (" / Drums" if ch == 9 else ""))
        outer = QVBoxLayout(group)
        top = QGridLayout()
        note_range = "-" if analysis.min_note is None else f"{analysis.min_note}..{analysis.max_note}"
        tracks = ", ".join(analysis.used_tracks) if analysis.used_tracks else "-"
        top.addWidget(QLabel(f"Notes: {analysis.note_count}"), 0, 0)
        top.addWidget(QLabel(f"Note range: {note_range}"), 0, 1)
        top.addWidget(QLabel(f"Tracks: {tracks}"), 0, 2)
        outer.addLayout(top)

        controls = QGridLayout()
        volume = SliderRow(0, 200, 100)
        octave = SliderRow(-4, 4, 0)
        add_enabled = QCheckBox("Generate support notes")
        add_amount = SliderRow(0, 100, 0)
        test_button = QPushButton("Test-play this channel")
        test_button.clicked.connect(lambda _checked=False, channel=ch, button=test_button: self.play_channel_preview(channel, button))
        controls.addWidget(QLabel("Volume %"), 0, 0)
        controls.addWidget(volume, 0, 1)
        controls.addWidget(QLabel("Octave shift"), 0, 2)
        controls.addWidget(octave, 0, 3)
        controls.addWidget(add_enabled, 1, 0)
        controls.addWidget(QLabel("Support influence %"), 1, 1)
        controls.addWidget(add_amount, 1, 2)
        controls.addWidget(test_button, 1, 3)
        outer.addLayout(controls)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(120)
        event_lines = []
        for event in analysis.program_events:
            event_lines.append(
                f"tick {event.abs_tick:>7} | {event.track_name} | {event.ref.short_name()}"
            )
        if not event_lines:
            event_lines.append("No explicit Program Change found. MIDI default is usually Program 1 / Acoustic Grand Piano.")
        if analysis.volume_values:
            event_lines.append(f"Original CC7 volume values: {analysis.volume_values[:16]}" + (" ..." if len(analysis.volume_values) > 16 else ""))
        info.setPlainText("\n".join(event_lines))
        outer.addWidget(QLabel("Original instrument/reference info"))
        outer.addWidget(info)

        inst_group = QGroupBox("Instrument replacement per original instrument")
        grid = QGridLayout(inst_group)
        grid.addWidget(QLabel("Original"), 0, 0)
        grid.addWidget(QLabel("New instrument"), 0, 1)
        grid.addWidget(QLabel("Program slider"), 0, 2)
        grid.addWidget(QLabel("Bank MSB"), 0, 3)
        grid.addWidget(QLabel("Bank LSB"), 0, 4)
        grid.addWidget(QLabel("Tone test"), 0, 5)
        for row, ref in enumerate(analysis.unique_refs, start=1):
            combo = QComboBox()
            for idx, name in enumerate(GM_INSTRUMENTS):
                combo.addItem(f"{idx + 1:03d} - {name}", idx)
            combo.setCurrentIndex(ref.program)
            program_slider = SliderRow(0, 127, ref.program)
            bank_msb = SliderRow(0, 127, 0 if ref.bank_msb is None else ref.bank_msb)
            bank_lsb = SliderRow(0, 127, 0 if ref.bank_lsb is None else ref.bank_lsb)
            tone_button = QPushButton("Test tone")
            ref_key = ref.key()
            tone_button.clicked.connect(lambda _checked=False, channel=ch, key=ref_key, button=tone_button: self.play_instrument_tone_preview(channel, key, button))
            program_slider.slider.valueChanged.connect(combo.setCurrentIndex)
            combo.currentIndexChanged.connect(program_slider.setValue)
            grid.addWidget(QLabel(ref.short_name()), row, 0)
            grid.addWidget(combo, row, 1)
            grid.addWidget(program_slider, row, 2)
            grid.addWidget(bank_msb, row, 3)
            grid.addWidget(bank_lsb, row, 4)
            grid.addWidget(tone_button, row, 5)
            self.instrument_widgets[(ch, ref.key())] = {
                "combo": combo,
                "program": program_slider,
                "bank_msb": bank_msb,
                "bank_lsb": bank_lsb,
                "tone_button": tone_button,
            }
        outer.addWidget(inst_group)
        self.channel_widgets[ch] = {
            "volume": volume,
            "octave": octave,
            "add_enabled": add_enabled,
            "add_amount": add_amount,
        }
        return group

    def sync_settings_from_ui(self):
        for ch, widgets in self.channel_widgets.items():
            setting = self.channel_settings.setdefault(ch, ChannelSettings(channel=ch))
            setting.volume_percent = widgets["volume"].value()
            setting.octave_shift = widgets["octave"].value()
            setting.add_notes_enabled = widgets["add_enabled"].isChecked()
            setting.add_notes_amount = widgets["add_amount"].value()
        for (ch, ref_key), widgets in self.instrument_widgets.items():
            setting = self.channel_settings.setdefault(ch, ChannelSettings(channel=ch))
            setting.overrides[ref_key] = InstrumentOverride(
                program=widgets["program"].value(),
                bank_msb=widgets["bank_msb"].value(),
                bank_lsb=widgets["bank_lsb"].value(),
            )
        self.eq_settings.global_volume_percent = self.eq_global_volume.value()
        self.eq_settings.song_speed_percent = self.eq_song_speed.value()
        self.eq_settings.brightness = self.eq_brightness.value()
        self.eq_settings.resonance = self.eq_resonance.value()
        self.eq_settings.reverb = self.eq_reverb.value()
        self.eq_settings.chorus = self.eq_chorus.value()
        self.eq_settings.pan = self.eq_pan.value()

    def build_modified_mid(self):
        if self.mid is None:
            raise RuntimeError("No MIDI loaded")
        self.sync_settings_from_ui()
        transformer = MidiTransformer(copy.deepcopy(self.mid), copy.deepcopy(self.channel_settings), copy.deepcopy(self.eq_settings))
        return transformer.transformed()

    def next_versioned_path(self, directory: Path, suffix: str = "_modified_v", extension: str = ".mid") -> Path:
        if self.source_path is None:
            raise RuntimeError("No source path")
        directory.mkdir(parents=True, exist_ok=True)
        stem = self.source_path.stem
        for idx in range(1, 10000):
            candidate = directory / f"{stem}{suffix}{idx:03d}{extension}"
            if not candidate.exists():
                return candidate
        raise RuntimeError("Could not find free output filename")

    def next_modified_path(self) -> Path:
        return self.next_versioned_path(self.current_output_directory(create=True), "_modified_v", ".mid")

    def save_modified(self):
        if self.mid is None or self.source_path is None:
            QMessageBox.warning(self, "No MIDI", "Please load a MIDI file first.")
            return
        try:
            out = self.next_modified_path()
            modified = self.build_modified_mid()
            modified.save(out)
            saved_paths = [out]
            if (hasattr(self, "output_copy_source_checkbox") and self.output_copy_source_checkbox.isChecked()
                    and out.parent.resolve() != self.source_path.parent.resolve()):
                copy_path = self.next_versioned_path(self.source_path.parent, "_modified_v", ".mid")
                modified.save(copy_path)
                saved_paths.append(copy_path)
            self.log("Saved modified MIDI:\n" + "\n".join(str(path) for path in saved_paths))
            self.refresh_modified_history(select_path=out)
            QMessageBox.information(self, "Saved", "Saved as:\n" + "\n".join(str(path) for path in saved_paths))
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            self.log(traceback.format_exc())

    def refresh_modified_history(self, select_path: Optional[Path] = None):
        self.modified_combo.clear()
        if self.source_path is None:
            return
        pattern = f"{self.source_path.stem}_modified_v*.mid"
        directories = [self.source_path.parent]
        try:
            out_dir = self.current_output_directory(create=False)
            if out_dir not in directories:
                directories.append(out_dir)
        except Exception:
            pass
        seen = set()
        files = []
        for directory in directories:
            try:
                for path in directory.glob(pattern):
                    resolved = str(path.resolve())
                    if resolved not in seen:
                        seen.add(resolved)
                        files.append(path)
            except Exception:
                continue
        for path in sorted(files):
            label = path.name if path.parent == self.source_path.parent else f"{path.name}  [{path.parent}]"
            self.modified_combo.addItem(label, str(path))
        if select_path:
            idx = self.modified_combo.findData(str(select_path))
            if idx >= 0:
                self.modified_combo.setCurrentIndex(idx)

    def render_current_preview_wav(self):
        if self.mid is None or self.source_path is None:
            QMessageBox.warning(self, "No MIDI", "Please load a MIDI file first.")
            return
        try:
            synth_text = self.fluidsynth_path_edit.text().strip() if hasattr(self, "fluidsynth_path_edit") else ""
            synth = Path(synth_text) if synth_text else None
            if synth is None:
                found = shutil.which("fluidsynth")
                if found:
                    synth = Path(found)
            if synth is None or not synth.exists():
                raise RuntimeError("FluidSynth executable not found. Select fluidsynth.exe in Options or add it to PATH.")
            sf_text = self.soundfont_path_edit.text().strip() if hasattr(self, "soundfont_path_edit") else ""
            if not sf_text:
                raise RuntimeError("No SoundFont selected. Select a local .sf2 or .sf3 file in Options.")
            soundfont = Path(sf_text)
            if not soundfont.exists():
                raise RuntimeError(f"SoundFont not found: {soundfont}")
            midi_path = self._write_preview_file()
            wav_path = self.next_versioned_path(self.current_output_directory(create=True), "_rendered_v", ".wav")
            sample_rate = int(self.render_samplerate_combo.currentText()) if hasattr(self, "render_samplerate_combo") else 44100
            cmd = [str(synth), "-ni", "-F", str(wav_path), "-r", str(sample_rate), str(soundfont), str(midi_path)]
            creationflags = 0
            if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            self.log("Rendering WAV with FluidSynth...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=creationflags)
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "FluidSynth render failed").strip())
            self.log(f"Rendered WAV: {wav_path}")
            QMessageBox.information(self, "Rendered", f"Rendered WAV as:\n{wav_path}")
            self.refresh_modified_history()
        except Exception as exc:
            QMessageBox.critical(self, "WAV render failed", str(exc))
            self.log(traceback.format_exc())

    def current_output_name(self) -> Optional[str]:
        text = self.port_combo.currentText().strip()
        if not text or text.startswith("<"):
            return None
        return text

    def refresh_ports(self):
        self.port_combo.clear()
        names = self.player.output_names()
        if names:
            self.port_combo.addItems(names)
            self.log(f"Detected MIDI outputs: {', '.join(names)}")
        else:
            self.port_combo.addItem("<no MIDI output detected>")
            self.log("No MIDI output detected. Use external playback mode in Options or install/enable a MIDI synthesizer/virtual port for internal playback.")

    def stop_playback(self):
        self.player.stop(wait=True)
        self._reset_active_play_button()

    def _stop_label(self) -> str:
        return "Stopp" if self.language == "Deutsch" else "Stop"

    def _remember_button_text(self, button: QPushButton):
        if button not in self.play_button_base_texts or button.text() != self._stop_label():
            self.play_button_base_texts.setdefault(button, button.text())

    def _set_active_play_button(self, key: str, button: QPushButton):
        if self.active_play_button is not None and self.active_play_button is not button:
            self._reset_active_play_button()
        self.play_button_base_texts.setdefault(button, button.text())
        self.active_play_key = key
        self.active_play_button = button
        button.setProperty("playing", True)
        button.setText(self._stop_label())
        self._repolish(button)

    def _reset_active_play_button(self):
        button = self.active_play_button
        if button is not None:
            button.setProperty("playing", False)
            button.setText(self.play_button_base_texts.get(button, button.text()))
            self._repolish(button)
        self.active_play_key = None
        self.active_play_button = None

    def _on_playback_finished(self, _label: str):
        self._reset_active_play_button()

    def _on_playback_error(self, label: str, error: str):
        QMessageBox.warning(self, "Playback failed", f"{label}\n\n{error}")

    def _toggle_playback(self, key: str, button: QPushButton, path_factory, label: str, error_title: str, playback_role: Optional[str] = None):
        mode = self.playback_mode_for(playback_role or key)

        if mode == "external":
            if self.player.is_playing():
                self.stop_playback()
            try:
                path = path_factory()
                if path is None:
                    return
                self._open_file_external(Path(path))
                self.log(f"Opened externally: {Path(path).name}")
            except Exception as exc:
                QMessageBox.critical(self, "External playback failed", str(exc))
                self.log(traceback.format_exc())
            return

        if self.active_play_key == key and self.player.is_playing():
            self.stop_playback()
            return
        if self.player.is_playing():
            self.stop_playback()
        try:
            path = path_factory()
            if path is None:
                return
            self._set_active_play_button(key, button)
            self.player.play_file(Path(path), self.current_output_name(), label=label)
        except Exception as exc:
            self._reset_active_play_button()
            QMessageBox.critical(self, error_title, str(exc))
            self.log(traceback.format_exc())

    def play_original(self, button: QPushButton):
        if self.source_path is None:
            QMessageBox.warning(self, "No MIDI", "Please load a MIDI file first.")
            return
        self._toggle_playback("original", button, lambda: self.source_path, "Original MIDI", "Playback failed", playback_role="original")

    def play_selected_modified(self, button: QPushButton):
        data = self.modified_combo.currentData()
        if not data:
            QMessageBox.warning(self, "No modified file", "No previous modified file is selected.")
            return
        label = f"Modified: {Path(data).name}"
        self._toggle_playback("modified", button, lambda: Path(data), label, "Playback failed", playback_role="modified")

    def _write_preview_file(self) -> Path:
        modified = self.build_modified_mid()
        preview_dir = Path(tempfile.gettempdir()) / "midimixmod_channel_workbench"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_path = preview_dir / "current_adjusted_preview.mid"
        modified.save(preview_path)
        return preview_path

    def play_current_preview(self, button: QPushButton):
        if self.mid is None:
            QMessageBox.warning(self, "No MIDI", "Please load a MIDI file first.")
            return
        self._toggle_playback("current_preview", button, self._write_preview_file, "Current adjusted preview", "Preview failed", playback_role="current_preview")

    def play_eq_preview(self, button: QPushButton):
        if self.mid is None:
            QMessageBox.warning(self, "No MIDI", "Please load a MIDI file first.")
            return
        self._toggle_playback("eq_preview", button, self._write_preview_file, "EQ/Tone preview", "Preview failed", playback_role="eq_preview")

    def _write_channel_preview_file(self, channel: int) -> Path:
        modified = self.build_modified_mid()
        filtered = self.filter_mid_to_channel(modified, channel)
        preview_dir = Path(tempfile.gettempdir()) / "midimixmod_channel_workbench"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_path = preview_dir / f"channel_{channel + 1:02d}_preview.mid"
        filtered.save(preview_path)
        return preview_path

    def play_channel_preview(self, channel: int, button: QPushButton):
        if self.mid is None:
            return
        self._toggle_playback(
            f"channel_{channel}",
            button,
            lambda: self._write_channel_preview_file(channel),
            f"Channel {channel + 1:02d} preview",
            "Channel preview failed",
            playback_role="channel_test",
        )

    def _write_instrument_tone_file(self, channel: int, ref_key: str) -> Path:
        if mido is None:
            raise RuntimeError(f"mido import failed: {MIDO_IMPORT_ERROR}")
        if self.mid is None:
            raise RuntimeError("No MIDI loaded")
        self.sync_settings_from_ui()
        setting = self.channel_settings.get(channel, ChannelSettings(channel=channel))
        override = setting.overrides.get(ref_key)
        if override is None:
            widgets = self.instrument_widgets.get((channel, ref_key))
            if widgets is None:
                raise RuntimeError("Instrument setting not found")
            override = InstrumentOverride(
                program=widgets["program"].value(),
                bank_msb=widgets["bank_msb"].value(),
                bank_lsb=widgets["bank_lsb"].value(),
            )

        ticks_per_beat = int(getattr(self.mid, "ticks_per_beat", 480) or 480)
        out = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
        track = mido.MidiTrack()
        out.tracks.append(track)
        track.append(mido.MetaMessage("track_name", name=f"MidiMixMod instrument tone test ch {channel + 1:02d}", time=0))
        track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
        track.append(mido.Message("control_change", channel=channel, control=0, value=override.bank_msb, time=0))
        track.append(mido.Message("control_change", channel=channel, control=32, value=override.bank_lsb, time=0))
        track.append(mido.Message("program_change", channel=channel, program=override.program, time=0))
        channel_volume = MidiTransformer.clamp_midi(round(100 * setting.volume_percent / 100 * self.eq_settings.global_volume_percent / 100))
        track.append(mido.Message("control_change", channel=channel, control=7, value=channel_volume, time=0))
        track.append(mido.Message("control_change", channel=channel, control=10, value=self.eq_settings.pan, time=0))
        track.append(mido.Message("control_change", channel=channel, control=71, value=self.eq_settings.resonance, time=0))
        track.append(mido.Message("control_change", channel=channel, control=74, value=self.eq_settings.brightness, time=0))
        track.append(mido.Message("control_change", channel=channel, control=91, value=self.eq_settings.reverb, time=0))
        track.append(mido.Message("control_change", channel=channel, control=93, value=self.eq_settings.chorus, time=0))
        note = MidiTransformer.clamp_midi(60 + setting.octave_shift * 12)
        track.append(mido.Message("note_on", channel=channel, note=note, velocity=100, time=0))
        track.append(mido.Message("note_off", channel=channel, note=note, velocity=0, time=max(1, ticks_per_beat * 4)))
        track.append(mido.Message("control_change", channel=channel, control=123, value=0, time=0))
        track.append(mido.MetaMessage("end_of_track", time=0))
        preview_dir = Path(tempfile.gettempdir()) / "midimixmod_channel_workbench"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_path = preview_dir / f"instrument_tone_ch{channel + 1:02d}_{hashlib.sha1(ref_key.encode('utf-8')).hexdigest()[:8]}.mid"
        out.save(preview_path)
        return preview_path

    def play_instrument_tone_preview(self, channel: int, ref_key: str, button: QPushButton):
        if self.mid is None:
            return
        self._toggle_playback(
            f"instrument_tone_{channel}_{ref_key}",
            button,
            lambda: self._write_instrument_tone_file(channel, ref_key),
            f"Instrument tone test ch {channel + 1:02d}",
            "Instrument tone test failed",
            playback_role="instrument_test",
        )

    @staticmethod
    def filter_mid_to_channel(mid, channel: int):
        out = mido.MidiFile(type=1, ticks_per_beat=mid.ticks_per_beat, clip=getattr(mid, "clip", False))
        for source_track in mid.tracks:
            track = mido.MidiTrack()
            pending = 0
            has_end = False
            for msg in source_track:
                pending += int(msg.time)
                keep = msg.is_meta or (hasattr(msg, "channel") and int(msg.channel) == channel)
                if keep:
                    copied = msg.copy(time=pending)
                    track.append(copied)
                    pending = 0
                    if copied.is_meta and copied.type == "end_of_track":
                        has_end = True
            if not has_end:
                track.append(mido.MetaMessage("end_of_track", time=pending))
            out.tracks.append(track)
        return out

    def open_current_external(self):
        try:
            if self.mid is None:
                return
            path = self._write_preview_file()
            self._open_file_external(path)
        except Exception as exc:
            QMessageBox.critical(self, "Open externally failed", str(exc))

    def apply_language(self, language: str):
        self.language = language
        if language == "Deutsch":
            self.tabs.setTabText(0, "Haupttab")
            self.tabs.setTabText(1, "Channels / Instrumente")
            self.tabs.setTabText(2, "Equalizer / Klang")
            self.tabs.setTabText(3, "Optionen")
            self.browse_button.setText("MIDI laden...")
            self.analyze_button.setText("Analysieren")
            self.play_original_button.setText("Original abspielen")
            self.play_modified_button.setText("Gewählte Modifikation abspielen")
            self.play_current_button.setText("MIDI abspielen")
            self.stop_button.setText("Stopp")
            self.save_button.setText("Als neue modifizierte MIDI speichern")
            self.refresh_ports_button.setText("MIDI-Ausgänge aktualisieren")
            self.eq_preview_button.setText("Mit aktuellen EQ/Klangwerten abspielen")
            self.eq_save_button.setText("Mit aktuellen EQ/Klangwerten speichern")
            if hasattr(self, "output_custom_browse_button"):
                self.output_custom_browse_button.setText("Ausgabeordner wählen...")
            if hasattr(self, "open_output_folder_button"):
                self.open_output_folder_button.setText("Aktuellen Ausgabeordner öffnen")
            if hasattr(self, "fluidsynth_browse_button"):
                self.fluidsynth_browse_button.setText("FluidSynth wählen...")
            if hasattr(self, "soundfont_browse_button"):
                self.soundfont_browse_button.setText("SoundFont wählen...")
            if hasattr(self, "render_current_wav_button"):
                self.render_current_wav_button.setText("Aktuelle Vorschau als WAV rendern")
            if hasattr(self, "output_copy_source_checkbox"):
                self.output_copy_source_checkbox.setText("Zusätzlich Kopie neben der Original-MIDI speichern")
        else:
            self.tabs.setTabText(0, "Main")
            self.tabs.setTabText(1, "Channels / Instruments")
            self.tabs.setTabText(2, "Equalizer / Tone")
            self.tabs.setTabText(3, "Options")
            self.browse_button.setText("Browse MIDI...")
            self.analyze_button.setText("Analyze")
            self.play_original_button.setText("Play original")
            self.play_modified_button.setText("Play selected modified")
            self.play_current_button.setText("Play MIDI")
            self.stop_button.setText("Stop")
            self.save_button.setText("Save as new modified MIDI")
            self.refresh_ports_button.setText("Refresh MIDI outputs")
            self.eq_preview_button.setText("Play with current EQ settings")
            self.eq_save_button.setText("Save with current EQ settings")
            if hasattr(self, "output_custom_browse_button"):
                self.output_custom_browse_button.setText("Browse output folder...")
            if hasattr(self, "open_output_folder_button"):
                self.open_output_folder_button.setText("Open current output folder")
            if hasattr(self, "fluidsynth_browse_button"):
                self.fluidsynth_browse_button.setText("Browse FluidSynth...")
            if hasattr(self, "soundfont_browse_button"):
                self.soundfont_browse_button.setText("Browse SoundFont...")
            if hasattr(self, "render_current_wav_button"):
                self.render_current_wav_button.setText("Render current adjusted preview as WAV")
            if hasattr(self, "output_copy_source_checkbox"):
                self.output_copy_source_checkbox.setText("Also save a copy next to the source MIDI")

        if hasattr(self, "output_mode_combo"):
            self._populate_output_mode_combo(language)
        if hasattr(self, "playback_mode_combos"):
            self._populate_all_playback_mode_combos(language)

        for button in [self.play_original_button, self.play_modified_button, self.play_current_button, self.eq_preview_button]:
            self.play_button_base_texts[button] = button.text()
        if self.active_play_button is not None:
            self.active_play_button.setText(self._stop_label())
            self._repolish(self.active_play_button)

    def apply_theme(self, theme: str):
        self.theme_name = theme
        palettes = {
            "Light": ("#f7f7f7", "#ffffff", "#202124", "#d0d0d0", "#1f6feb"),
            "Dark": ("#1e1f22", "#2b2d31", "#eeeeee", "#555a64", "#8ab4f8"),
            "Sepia": ("#efe4cc", "#f8edd6", "#3b2f22", "#c8b894", "#8a5a20"),
            "Ocean": ("#0e2433", "#16384d", "#e6f7ff", "#2f6f91", "#66d9ef"),
            "Matrix": ("#061006", "#0b1f0b", "#9cff9c", "#1f5f1f", "#00ff66"),
            "Hellfire / Hölle": ("#180805", "#30100a", "#ffe7d1", "#7f2a16", "#ff5a1f"),
            "Purple": ("#191326", "#2a1f3d", "#f1e8ff", "#604b80", "#c58cff"),
        }
        bg, panel, text, border, accent = palettes.get(theme, palettes["Dark"])
        focus_a = accent
        focus_b = "#ffd54a" if theme not in {"Sepia", "Hellfire / Hölle"} else "#66d9ef"
        playing = "#ff5252"
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {bg}; color: {text}; }}
            QTabWidget::pane {{ border: 1px solid {border}; }}
            QTabBar::tab {{ background: {panel}; color: {text}; padding: 8px 12px; border: 1px solid {border}; }}
            QTabBar::tab:selected {{ border-bottom: 2px solid {accent}; }}
            QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 10px; padding: 8px; background: {panel}; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {accent}; }}
            QPushButton {{ background: {panel}; color: {text}; border: 1px solid {border}; border-radius: 5px; padding: 6px 10px; }}
            QPushButton:hover {{ border-color: {accent}; }}
            QPushButton[playing="true"] {{ border: 2px solid {playing}; font-weight: bold; }}
            QPushButton[activeFocus="true"], QComboBox[activeFocus="true"], QSpinBox[activeFocus="true"],
            QLineEdit[activeFocus="true"], QTextEdit[activeFocus="true"], QPlainTextEdit[activeFocus="true"],
            QCheckBox[activeFocus="true"] {{ border: 2px solid {focus_a}; }}
            QPushButton[activeFocus="true"][focusPulse="true"], QComboBox[activeFocus="true"][focusPulse="true"],
            QSpinBox[activeFocus="true"][focusPulse="true"], QLineEdit[activeFocus="true"][focusPulse="true"],
            QTextEdit[activeFocus="true"][focusPulse="true"], QPlainTextEdit[activeFocus="true"][focusPulse="true"],
            QCheckBox[activeFocus="true"][focusPulse="true"] {{ border: 2px solid {focus_b}; }}
            QWidget#sliderRow[activeFocus="true"] {{ border: 2px solid {focus_a}; border-radius: 5px; padding: 2px; }}
            QWidget#sliderRow[activeFocus="true"][focusPulse="true"] {{ border: 2px solid {focus_b}; }}
            QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {{ background: {panel}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 3px; }}
            QPushButton[activeFocus="true"], QComboBox[activeFocus="true"], QSpinBox[activeFocus="true"],
            QLineEdit[activeFocus="true"], QTextEdit[activeFocus="true"], QPlainTextEdit[activeFocus="true"],
            QCheckBox[activeFocus="true"] {{ border: 2px solid {focus_a}; }}
            QPushButton[activeFocus="true"][focusPulse="true"], QComboBox[activeFocus="true"][focusPulse="true"],
            QSpinBox[activeFocus="true"][focusPulse="true"], QLineEdit[activeFocus="true"][focusPulse="true"],
            QTextEdit[activeFocus="true"][focusPulse="true"], QPlainTextEdit[activeFocus="true"][focusPulse="true"],
            QCheckBox[activeFocus="true"][focusPulse="true"] {{ border: 2px solid {focus_b}; }}
            QSlider::groove:horizontal {{ height: 6px; background: {border}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {accent}; width: 14px; margin: -5px 0; border-radius: 7px; }}
            QSlider[activeFocus="true"]::groove:horizontal {{ height: 9px; background: {focus_a}; border-radius: 4px; }}
            QSlider[activeFocus="true"][focusPulse="true"]::groove:horizontal {{ background: {focus_b}; }}
            QMenuBar, QMenu {{ background: {panel}; color: {text}; }}
        """)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
