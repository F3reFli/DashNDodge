"""Offline chiptune tracker: renders the game's original soundtrack into
vfx/musics/ as small 8-bit WAV files.

    python tools/compose.py            # render every song
    python tools/compose.py title      # render one

Each song is written as chords (one per bar) and a melody (one string per
bar, durations in sixteenth notes). The renderer adds arpeggios, a
triangle bass and drums. Every bar is checked to add up to 4/4, and melody
notes are checked against the song's scale."""

import math
import os
import random
import sys
import wave
from array import array

RATE = 22050
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "vfx", "musics")

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def midi(name):
    pitch, octave = name[:-1], int(name[-1])
    return 12 * (octave + 1) + NOTE[pitch]


def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord_notes(sym):
    root = sym[:2] if len(sym) > 1 and sym[1] in "#b" else sym[:1]
    quality = sym[len(root):]
    r = NOTE[root]
    if quality == "m":
        return [r, r + 3, r + 7]
    if quality == "7":
        return [r, r + 4, r + 7, r + 10]
    return [r, r + 4, r + 7]


# ======================================================================
# Songs (original compositions)
# ======================================================================

SONGS = {
    "title": {
        "file": "title - Invitation to the Scarlet Night",
        "bpm": 112,
        "scale": ("A", [0, 2, 3, 5, 7, 8, 10, 11]),  # A minor (+ G# leading tone)
        "drums": "soft",
        "sections": {
            "intro": (["Am", "Am"], ["r:16", "r:16"]),
            "A": (["Am", "F", "G", "Em", "Am", "F", "Dm", "E"], [
                "E5:4 A5:4 G5:2 E5:2 C5:4",
                "F5:6 E5:2 C5:4 A4:4",
                "D5:4 G5:4 F5:2 D5:2 B4:4",
                "E5:12 r:4",
                "A4:2 C5:2 E5:2 A5:2 B5:4 C6:4",
                "A5:6 G5:2 F5:4 E5:4",
                "F5:4 E5:4 D5:4 F5:4",
                "E5:4 G#5:4 B5:8",
            ]),
            "B": (["F", "G", "Em", "Am", "Dm", "G", "C", "E"], [
                "C6:4 A5:4 F5:4 A5:4",
                "B5:4 G5:4 D5:4 G5:4",
                "G5:6 E5:2 B4:8",
                "C5:4 E5:4 A5:8",
                "F5:4 A5:4 D6:4 C6:4",
                "B5:4 D6:4 G5:8",
                "E5:4 G5:4 C6:4 E6:4",
                "D6:4 B5:4 G#5:4 E5:4",
            ]),
        },
        "order": [("intro", 0), ("A", 1), ("B", 1), ("A", 2), ("B", 2)],
    },
    "boss": {
        "file": "boss - Danmaku Ballroom",
        "bpm": 150,
        "scale": ("D", [0, 2, 3, 5, 7, 8, 10, 1]),  # D minor (+ C# leading tone)
        "drums": "drive",
        "sections": {
            "A": (["Dm", "Bb", "C", "Am", "Dm", "Bb", "C", "A"], [
                "D5:2 F5:2 A5:2 D6:2 C6:2 A5:2 F5:2 A5:2",
                "Bb5:4 A5:2 G5:2 F5:4 D5:4",
                "E5:2 G5:2 C6:2 E6:2 D6:4 C6:4",
                "A5:8 G5:2 E5:2 C5:4",
                "D5:2 F5:2 A5:2 D6:2 E6:2 F6:2 E6:2 D6:2",
                "D6:4 Bb5:4 F5:4 D6:4",
                "C6:2 Bb5:2 A5:2 G5:2 E5:4 C5:4",
                "A5:4 C#6:4 E6:8",
            ]),
            "B": (["Gm", "Bb", "C", "A", "Gm", "Bb", "C", "A"], [
                "G5:4 Bb5:4 D6:4 G6:4",
                "F6:4 D6:4 Bb5:4 F5:4",
                "G5:2 C6:2 E6:2 G6:2 F6:2 E6:2 D6:2 C6:2",
                "C#6:4 E6:4 A5:8",
                "Bb5:2 A5:2 G5:2 D5:2 G5:4 Bb5:4",
                "D6:2 C6:2 Bb5:2 F5:2 D6:4 F6:4",
                "E6:4 C6:4 G5:4 E6:4",
                "E6:2 C#6:2 A5:2 E5:2 A5:8",
            ]),
        },
        "order": [("A", 1), ("B", 1), ("A", 2), ("B", 2)],
    },
    "boss_remilia": {
        "file": "boss_remilia - The Moon That Never Sets",
        "bpm": 160,
        "scale": ("C", [0, 2, 3, 5, 7, 8, 10, 11]),  # C harmonic minor
        "drums": "drive",
        "sections": {
            "A": (["Cm", "Ab", "Bb", "G", "Fm", "G", "Cm", "G"], [
                "C5:2 Eb5:2 G5:2 C6:2 B5:2 C6:2 D6:2 Eb6:2",
                "C6:4 Ab5:4 Eb5:4 C5:4",
                "D5:2 F5:2 Bb5:2 D6:2 C6:2 Bb5:2 F5:2 D5:2",
                "B4:4 D5:4 G5:4 B5:4",
                "Ab5:4 C6:4 F6:4 Eb6:2 D6:2",
                "D6:4 B5:4 G5:4 F5:4",
                "Eb5:2 G5:2 C6:2 Eb6:2 G6:4 Eb6:4",
                "D6:4 B5:2 G5:2 D6:8",
            ]),
            "B": (["Ab", "Bb", "Cm", "Cm", "Ab", "Bb", "G", "G"], [
                "Eb6:6 C6:2 Ab5:8",
                "F6:6 D6:2 Bb5:8",
                "G6:4 F6:2 Eb6:2 D6:2 Eb6:2 C6:4",
                "C6:12 r:4",
                "C6:2 Eb6:2 Ab6:4 G6:2 F6:2 Eb6:4",
                "D6:2 F6:2 Bb6:4 Ab6:2 G6:2 F6:4",
                "G6:4 F6:2 D6:2 B5:4 D6:4",
                "G5:2 B5:2 D6:2 F6:2 G6:8",
            ]),
        },
        "order": [("A", 1), ("B", 1), ("A", 2), ("B", 2)],
    },
    "boss_flandre": {
        "file": "boss_flandre - Four Hundred and Ninety-Five Years",
        "bpm": 168,
        "scale": ("E", [0, 2, 3, 5, 7, 8, 10, 11, 6, 9, 1]),  # E minor, plus the B and D chords' tones
        "drums": "frantic",
        "sections": {
            "A": (["Em", "C", "D", "B", "Am", "B", "Em", "Em"], [
                "E5:1 F#5:1 G5:2 B5:2 E6:2 D#6:2 E6:2 B5:2 G5:2",
                "C6:2 B5:2 G5:2 E5:2 C6:2 B5:2 G5:2 C6:2",
                "D6:2 A5:2 F#5:2 D5:2 F#5:2 A5:2 D6:2 F#6:2",
                "D#6:4 B5:4 F#5:4 D#5:4",
                "A5:2 C6:2 E6:2 A6:2 G6:2 E6:2 C6:2 E6:2",
                "F#6:4 D#6:4 B5:4 A5:4",
                "G5:2 B5:2 E6:2 G6:2 F#6:2 E6:2 D#6:2 E6:2",
                "B5:4 E6:4 E5:8",
            ]),
            "B": (["C", "D", "Bm", "Em", "C", "D", "B", "B"], [
                "G6:4 E6:4 C6:4 E6:4",
                "F#6:4 D6:4 A5:4 D6:4",
                "F#6:2 E6:2 D6:2 B5:2 F#5:4 B5:4",
                "E6:8 G6:4 B6:4",
                "C7:4 B6:4 G6:4 E6:4",
                "A6:4 F#6:4 D6:4 A5:4",
                "B5:2 D#6:2 F#6:2 B6:2 A6:2 F#6:2 D#6:2 B5:2",
                "F#6:8 D#6:4 B5:4",
            ]),
        },
        "order": [("A", 1), ("B", 1), ("A", 2), ("B", 2)],
    },
}


# ======================================================================
# Validation
# ======================================================================


def parse_bar(text):
    out = []
    for tok in text.split():
        name, dur = tok.split(":")
        out.append((None if name == "r" else midi(name), int(dur)))
    return out


def validate(key, song):
    root, steps = song["scale"]
    allowed = {(NOTE[root] + s) % 12 for s in steps}
    problems = []
    for sname, (chords, bars) in song["sections"].items():
        assert len(chords) == len(bars), f"{key}/{sname}: {len(chords)} chords vs {len(bars)} bars"
        for i, (ch, bar) in enumerate(zip(chords, bars)):
            notes = parse_bar(bar)
            total = sum(d for _n, d in notes)
            if total != 16:
                problems.append(f"{key}/{sname} bar {i + 1}: {total}/16 sixteenths")
            tones = {n % 12 for n in chord_notes(ch)}
            for n, _d in notes:
                if n is not None and n % 12 not in allowed and n % 12 not in tones:
                    problems.append(f"{key}/{sname} bar {i + 1}: note {n} outside the scale")
    return problems


# ======================================================================
# Synthesis
# ======================================================================


def add_tone(buf, start, length, f, vol, duty=0.25, wave_kind="pulse", vibrato=True, release=0.03, detune=0.0):
    n = len(buf)
    attack = int(0.004 * RATE)
    decay = int(0.06 * RATE)
    rel = int(release * RATE)
    phase = 0.0
    phase2 = 0.0
    vib_start = int(0.12 * RATE)
    for i in range(length):
        j = start + i
        if j >= n:
            break
        ff = f
        if vibrato and i > vib_start and length > vib_start * 2:
            ff = f * (1 + 0.004 * math.sin(i * 2 * math.pi * 5.5 / RATE))
        phase = (phase + ff / RATE) % 1.0
        if wave_kind == "tri":
            s = 4 * abs(phase - 0.5) - 1
        else:
            s = 1.0 if phase < duty else -1.0
            if detune:
                phase2 = (phase2 + ff * (1 + detune) / RATE) % 1.0
                s = 0.65 * s + 0.35 * (1.0 if phase2 < 0.5 else -1.0)
        if i < attack:
            env = i / attack
        elif i < attack + decay:
            env = 1 - 0.25 * (i - attack) / decay
        else:
            env = 0.75
        if i > length - rel:
            env *= max(0.0, (length - i) / rel)
        buf[j] += s * vol * env


def add_noise(buf, start, length, vol, lowpass, rng, pitch_tone=0.0):
    n = len(buf)
    y = 0.0
    phase = 0.0
    for i in range(length):
        j = start + i
        if j >= n:
            break
        y += lowpass * (rng.uniform(-1, 1) - y)
        env = (1 - i / length) ** 2
        s = y
        if pitch_tone:
            phase = (phase + pitch_tone / RATE) % 1.0
            s = 0.6 * y + 0.4 * math.sin(phase * 2 * math.pi)
        buf[j] += s * vol * env


def add_kick(buf, start, vol):
    length = int(0.13 * RATE)
    phase = 0.0
    for i in range(length):
        j = start + i
        if j >= len(buf):
            break
        f = 150 * (1 - i / length) + 45
        phase = (phase + f / RATE) % 1.0
        buf[j] += math.sin(phase * 2 * math.pi) * vol * (1 - i / length) ** 1.5


DRUMS = {
    # 16 steps per bar: K kick, S snare, h hat, . nothing
    "soft": ["K.......S.......", "K.....K.S.....h."],
    "drive": ["K.h.S.h.K.hKS.h.", "K.h.S.hKK.h.S.hS"],
    "frantic": ["KhhhShhhKhKhShhh", "KhKhShhhKhhhShSS"],
}


def render(key):
    song = SONGS[key]
    bpm = song["bpm"]
    six = 60.0 / bpm / 4  # seconds per sixteenth
    bar_len = 16 * six
    bars = []
    for sname, variant in song["order"]:
        chords, mel = song["sections"][sname]
        for c, m in zip(chords, mel):
            bars.append((c, m, sname, variant))
    total = int(len(bars) * bar_len * RATE) + 1
    lead = [0.0] * total
    rest = [0.0] * total
    rng = random.Random(7)
    pattern = DRUMS[song["drums"]]
    for b, (chord, mel, sname, variant) in enumerate(bars):
        t0 = b * bar_len
        tones = chord_notes(chord)
        root = tones[0]
        # melody
        pos = 0
        if sname != "intro":
            for note, dur in parse_bar(mel):
                if note is not None:
                    start = int((t0 + pos * six) * RATE)
                    length = int(dur * six * RATE * 0.92)
                    add_tone(lead, start, length, freq(note), 0.30, duty=0.25 if variant == 1 else 0.125, detune=0.004)
                pos += dur
        # arpeggio (16ths) around octave 4-5
        arp = [60 + ((t - 0) % 12) for t in tones] + [72 + (tones[0] % 12)]
        arp = sorted(arp)
        for s in range(16):
            n = arp[s % len(arp)] if (s // 4) % 2 == 0 else arp[(len(arp) - 1 - s) % len(arp)]
            start = int((t0 + s * six) * RATE)
            add_tone(rest, start, int(six * RATE * 0.8), freq(n), 0.10 if variant == 1 else 0.12, duty=0.125, vibrato=False, release=0.01)
        # bass (8ths, octave bounce)
        for s in range(0, 16, 2):
            n = 36 + (root % 12) + (12 if (s // 2) % 2 else 0)
            start = int((t0 + s * six) * RATE)
            add_tone(rest, start, int(2 * six * RATE * 0.85), freq(n), 0.30, wave_kind="tri", vibrato=False, release=0.02)
        # drums (lighter on the first pass of each section)
        if sname != "intro":
            pat = pattern[b % 2] if variant == 2 or song["drums"] != "soft" else pattern[0]
            for s, ch in enumerate(pat):
                start = int((t0 + s * six) * RATE)
                if ch == "K":
                    add_kick(rest, start, 0.45)
                elif ch == "S":
                    add_noise(rest, start, int(0.12 * RATE), 0.26 if variant == 2 else 0.18, 0.55, rng, pitch_tone=190)
                elif ch == "h" and variant == 2:
                    add_noise(rest, start, int(0.03 * RATE), 0.07, 0.95, rng)
    # echo on the lead
    delay = int(3 * six * RATE)
    for i in range(total - 1, delay - 1, -1):
        lead[i] += lead[i - delay] * 0.28
    mix = [lead[i] + rest[i] for i in range(total)]
    peak = max(abs(v) for v in mix) or 1.0
    k = 0.92 / peak
    data = array("B", (int(128 + 127 * max(-1.0, min(1.0, v * k))) for v in mix))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, song["file"] + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    return path, total / RATE, peak


def main():
    keys = sys.argv[1:] or list(SONGS)
    problems = []
    for key in SONGS:
        problems += validate(key, SONGS[key])
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    for key in keys:
        path, seconds, peak = render(key)
        print(f"{key:14s} {seconds:5.1f}s  peak(before norm) {peak:.2f}  -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
