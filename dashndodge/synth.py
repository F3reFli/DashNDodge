"""Tiny procedural sound synthesizer for retro sound effects.

Everything is generated at startup, so the game needs no extra audio files
for these (and there is no licensing question about them)."""

import math
import random
from array import array

RATE = 22050


def _env(i, n, attack, release):
    a = int(attack * RATE)
    r = int(release * RATE)
    if a and i < a:
        return i / a
    if r and i > n - r:
        return max(0.0, (n - i) / r)
    return 1.0


def tone(f0, f1, dur, wave="square", vol=0.5, attack=0.002, release=0.05, curve=1.0, vibrato=0.0, duty=0.5):
    n = int(dur * RATE)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / max(1, n - 1)
        f = f0 + (f1 - f0) * (t ** curve)
        if vibrato:
            f *= 1 + 0.03 * math.sin(i / RATE * TAU_VIB * vibrato)
        phase = (phase + f / RATE) % 1.0
        if wave == "square":
            s = 1.0 if phase < duty else -1.0
        elif wave == "tri":
            s = 4 * abs(phase - 0.5) - 1
        elif wave == "saw":
            s = 2 * phase - 1
        else:
            s = math.sin(phase * math.tau)
        out[i] = s * vol * _env(i, n, attack, release)
    return out


TAU_VIB = math.tau


def noise(dur, vol=0.5, lowpass=1.0, attack=0.001, release=0.05, sweep=None, seed=1):
    rng = random.Random(seed)
    n = int(dur * RATE)
    out = [0.0] * n
    y = 0.0
    for i in range(n):
        a = lowpass
        if sweep:
            a = sweep[0] + (sweep[1] - sweep[0]) * (i / max(1, n - 1))
        y += a * (rng.uniform(-1, 1) - y)
        out[i] = y * vol * _env(i, n, attack, release)
    return out


def mix(*parts, offsets=None):
    offsets = offsets or [0.0] * len(parts)
    n = max(int(o * RATE) + len(p) for p, o in zip(parts, offsets))
    out = [0.0] * n
    for p, o in zip(parts, offsets):
        start = int(o * RATE)
        for i, s in enumerate(p):
            out[start + i] += s
    return out


def seq(*parts, gap=0.0):
    out = []
    pad = [0.0] * int(gap * RATE)
    for p in parts:
        out.extend(p)
        out.extend(pad)
    return out


def to_bytes(samples, rate, channels):
    """Convert mono float samples (at RATE) to 16-bit PCM for the mixer."""
    buf = array("h")
    step = RATE / rate
    n = int(len(samples) / step)
    for i in range(n):
        s = samples[int(i * step)]
        v = int(max(-1.0, min(1.0, s)) * 30000)
        for _ in range(channels):
            buf.append(v)
    return buf.tobytes()


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + (octave - 4) * 12) / 12)


def build_all():
    """name -> mono float samples"""
    s = {}
    s["shot"] = tone(1300, 700, 0.045, "square", 0.16, release=0.03, duty=0.25)
    s["shot2"] = mix(tone(500, 260, 0.06, "square", 0.14, release=0.04), noise(0.03, 0.10, 0.6))
    s["graze"] = noise(0.035, 0.22, 0.9, release=0.03, seed=7)
    s["dash"] = noise(0.20, 0.34, sweep=(0.05, 0.6), attack=0.01, release=0.12, seed=3)
    s["parry_fail"] = tone(170, 120, 0.14, "square", 0.22, release=0.08, duty=0.3)
    s["kill"] = mix(tone(900, 160, 0.12, "square", 0.22, release=0.06, curve=0.5), noise(0.10, 0.25, 0.5, release=0.08, seed=11))
    s["item"] = seq(tone(1568, 1568, 0.035, "square", 0.10, release=0.01, duty=0.25), tone(2093, 2093, 0.05, "square", 0.10, release=0.03, duty=0.25))
    s["heal"] = seq(*[tone(note(n), note(n), 0.07, "square", 0.16, release=0.02, duty=0.25) for n in ("C5", "E5", "G5", "C6", "E6")])
    s["pichuun"] = mix(tone(2000, 90, 0.45, "square", 0.30, release=0.15, curve=0.35, duty=0.5), noise(0.40, 0.25, 0.35, release=0.3, seed=5))
    s["spell"] = mix(tone(220, 1760, 0.55, "saw", 0.16, attack=0.02, release=0.2, curve=1.6, vibrato=9), noise(0.55, 0.14, sweep=(0.02, 0.5), release=0.25, seed=9))
    s["capture"] = seq(*[tone(note(n), note(n), d, "square", 0.17, release=0.03, duty=0.25) for n, d in (("G5", 0.08), ("C6", 0.08), ("E6", 0.08), ("G6", 0.08), ("C7", 0.25))])
    s["timestop"] = mix(tone(2400, 200, 0.7, "sine", 0.30, release=0.3, curve=0.6, vibrato=30), noise(0.5, 0.08, 0.2, seed=13))
    s["freeze"] = mix(*[tone(f, f, 0.6, "sine", 0.12, release=0.5) for f in (2349, 3136, 3729, 4699)], offsets=[0, 0.03, 0.06, 0.09])
    s["camera"] = seq(noise(0.018, 0.5, 1.0, release=0.01, seed=2), [0.0] * int(0.05 * RATE), noise(0.03, 0.4, 0.8, release=0.02, seed=4))
    s["incident"] = seq(*[tone(f, f, 0.09, "square", 0.17, release=0.02, duty=0.5) for f in (880, 660, 880, 660, 880, 660)])
    s["boss_die"] = mix(noise(1.4, 0.45, sweep=(0.6, 0.02), release=1.0, seed=17), tone(120, 30, 1.2, "sine", 0.45, release=0.8))
    s["tick"] = tone(1000, 1000, 0.04, "square", 0.12, release=0.02, duty=0.25)
    s["warn"] = seq(tone(1200, 1200, 0.06, "square", 0.12, release=0.02), tone(1200, 1200, 0.06, "square", 0.12, release=0.02), gap=0.04)
    s["cough"] = seq(noise(0.09, 0.4, 0.25, attack=0.005, release=0.06, seed=21), noise(0.12, 0.35, 0.2, attack=0.005, release=0.09, seed=22), gap=0.06)
    s["laser"] = mix(noise(1.8, 0.30, 0.18, attack=0.05, release=0.6, seed=19), tone(70, 55, 1.8, "saw", 0.22, attack=0.05, release=0.6))
    s["whoosh"] = noise(0.35, 0.3, sweep=(0.6, 0.03), attack=0.02, release=0.2, seed=23)
    s["card_break"] = mix(noise(0.5, 0.35, sweep=(0.7, 0.05), release=0.35, seed=29), tone(1400, 300, 0.4, "tri", 0.2, release=0.2))
    s["menu_move"] = tone(880, 880, 0.03, "square", 0.08, release=0.015, duty=0.25)
    s["boing"] = tone(300, 600, 0.12, "sine", 0.3, release=0.05, curve=0.5, vibrato=20)
    s["steal"] = seq(tone(1200, 1500, 0.06, "square", 0.14, duty=0.25), tone(1500, 900, 0.1, "square", 0.14, duty=0.25))
    s["zzz"] = tone(140, 120, 0.4, "tri", 0.15, attack=0.1, release=0.2, vibrato=4)
    s["beam"] = mix(noise(0.5, 0.28, sweep=(0.7, 0.15), attack=0.01, release=0.3, seed=41), tone(90, 60, 0.5, "saw", 0.2, release=0.3))
    s["boss_intro"] = mix(tone(55, 50, 1.4, "saw", 0.28, attack=0.05, release=0.8, vibrato=3), tone(110, 104, 1.4, "square", 0.08, attack=0.3, release=0.8, duty=0.3),
                          noise(1.2, 0.18, sweep=(0.02, 0.4), attack=0.4, release=0.6, seed=43))
    s["chomp"] = seq(noise(0.04, 0.4, 0.3, seed=31), noise(0.05, 0.35, 0.25, seed=32), gap=0.05)
    return s
