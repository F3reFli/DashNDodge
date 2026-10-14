"""Music and sound effects with per-sound throttling."""

import os

import pygame

from . import synth
from .config import MUSIC_DIR, SFX_DIR, resource_path

FILE_SFX = {
    "parry": "parry.mp3",
    "select": "select.mp3",
    "move": "schange.mp3",
    "explode": "8-bit-explosion-10-340462.mp3",
    "blip": "8-bit-game-sfx-sound-2-269966.mp3",
}

# Relative volume of each effect, so bullet spam doesn't drown everything.
LEVELS = {
    "shot": 0.35,
    "shot2": 0.45,
    "graze": 0.35,
    "item": 0.30,
    "move": 0.6,
    "explode": 0.75,
    "blip": 0.5,
    "tick": 0.6,
}

# Minimum ms between two plays of the same effect.
THROTTLE = {"shot": 55, "shot2": 70, "graze": 40, "item": 45, "kill": 40, "tick": 200}


class Audio:
    def __init__(self, save):
        self.save = save
        self.ok = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.last = {}
        self.music_name = None
        self.music_path = None
        self.paused = False
        if not self.ok:
            return
        pygame.mixer.set_num_channels(32)
        freq, _size, channels = pygame.mixer.get_init()
        for name, samples in synth.build_all().items():
            try:
                self.sounds[name] = pygame.mixer.Sound(buffer=synth.to_bytes(samples, freq, channels))
            except pygame.error:
                pass
        for name, fname in FILE_SFX.items():
            try:
                self.sounds[name] = pygame.mixer.Sound(resource_path(os.path.join(SFX_DIR, fname)))
            except (pygame.error, FileNotFoundError):
                pass
        self.apply_volumes()

    def apply_volumes(self):
        if not self.ok:
            return
        sfx = self.save.settings["sfx_volume"]
        for name, snd in self.sounds.items():
            snd.set_volume(sfx * LEVELS.get(name, 0.8))
        music = 0.0 if self.paused else self.save.settings["music_volume"] * 0.8
        pygame.mixer.music.set_volume(music)

    def play(self, name, volume=1.0):
        if not self.ok:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = pygame.time.get_ticks()
        gap = THROTTLE.get(name, 25)
        if now - self.last.get(name, -10000) < gap:
            return
        self.last[name] = now
        ch = snd.play()
        if ch is not None and volume != 1.0:
            ch.set_volume(volume)

    def music_tracks(self):
        folder = resource_path(MUSIC_DIR)
        try:
            files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".mp3", ".ogg", ".wav")))
        except OSError:
            files = []
        return [os.path.join(folder, f) for f in files]

    def play_music(self, track=None, fade_ms=800, keep_if_missing=False):
        """Play a track from vfx/musics. `track` is a file-name prefix or a list
        of prefixes tried in order (e.g. ["boss_remilia", "boss"]). If none
        matches, the default (first) track plays, or, with keep_if_missing,
        whatever is playing keeps going. Returns the new track's name."""
        if not self.ok:
            return None
        tracks = self.music_tracks()
        if not tracks:
            return None
        path = None
        keys = [track] if isinstance(track, str) else list(track or [])
        for key in keys:
            for t in tracks:
                if os.path.basename(t).lower().startswith(key.lower()):
                    path = t
                    break
            if path:
                break
        if path is None:
            if keep_if_missing and pygame.mixer.music.get_busy():
                return None
            special = ("title", "stage", "boss", "extra", "endless", "ending")
            plain = [t for t in tracks if not os.path.basename(t).lower().startswith(special)]
            path = (plain or tracks)[0]
        if path == self.music_path and pygame.mixer.music.get_busy():
            return None
        try:
            # Halt first: loading over a track that is still fading out makes
            # SDL_mixer block until the fade ends (a freeze of up to 1.8 s).
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1, fade_ms=fade_ms)
        except pygame.error:
            return None
        self.music_path = path
        self.music_name = os.path.splitext(os.path.basename(path))[0].split(" - ", 1)[-1]
        self.apply_volumes()
        return self.music_name

    def fade_music(self, ms=800):
        if self.ok:
            pygame.mixer.music.fadeout(ms)
            self.music_path = None

    def pause_music(self, paused):
        # Muted rather than paused: pygame-ce's music.pause()/unpause() keep the
        # GIL while waiting for the audio lock, and deadlock against the audio
        # thread whenever a sound effect finishes at the same moment.
        if not self.ok or paused == self.paused:
            return
        self.paused = paused
        self.apply_volumes()
