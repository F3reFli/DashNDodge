"""Per-frame screen effect state, written by scenes and read by the GPU renderer.

Scenes describe *what* the screen should look like (colour grade, light
sources, shockwave ripples, impacts...); renderer.py turns it into shader
uniforms. Nothing here touches OpenGL, so the game runs the same with the
classic (CPU) renderer, where these effects are simply skipped."""

import math

import pygame

from .config import H, W
from .util import clamp, lerp

MAX_WAVES = 8
LIGHT_W, LIGHT_H = W // 4, H // 4


class Grade:
    """Colour grade: exposure, contrast, saturation and split toning."""

    __slots__ = ("exposure", "contrast", "saturation", "shadows", "highlights", "bloom")

    def __init__(self, exposure=1.0, contrast=1.08, saturation=1.1, shadows=(0.0, 0.0, 0.0),
                 highlights=(0.0, 0.0, 0.0), bloom=1.0):
        self.exposure = exposure
        self.contrast = contrast
        self.saturation = saturation
        self.shadows = shadows  # added to dark tones (RGB, about -0.1..0.1)
        self.highlights = highlights  # added to bright tones
        self.bloom = bloom

    def blend(self, other, k):
        return Grade(
            lerp(self.exposure, other.exposure, k),
            lerp(self.contrast, other.contrast, k),
            lerp(self.saturation, other.saturation, k),
            tuple(lerp(a, b, k) for a, b in zip(self.shadows, other.shadows)),
            tuple(lerp(a, b, k) for a, b in zip(self.highlights, other.highlights)),
            lerp(self.bloom, other.bloom, k),
        )


NEUTRAL = Grade()

# One mood per background (stages, menus, endings).
GRADES = {
    "title": Grade(1.02, 1.14, 1.12, (0.03, -0.01, 0.03), (0.05, 0.0, -0.02), 1.15),
    "night": Grade(1.0, 1.1, 1.05, (-0.01, 0.0, 0.05), (0.0, 0.02, 0.04), 1.1),
    "twilight": Grade(1.04, 1.1, 1.15, (0.04, -0.01, 0.04), (0.07, 0.02, -0.04), 1.1),
    "lake": Grade(1.02, 1.08, 1.08, (-0.02, 0.01, 0.06), (0.0, 0.03, 0.06), 1.15),
    "gate": Grade(1.04, 1.14, 1.12, (0.04, 0.0, -0.01), (0.06, 0.03, -0.03), 1.05),
    "library": Grade(1.0, 1.1, 1.05, (0.02, -0.01, 0.05), (0.06, 0.04, -0.02), 1.1),
    "clock": Grade(1.0, 1.12, 1.0, (-0.01, 0.0, 0.05), (0.03, 0.03, 0.05), 1.1),
    "moon": Grade(1.02, 1.16, 1.18, (0.05, -0.01, 0.0), (0.07, 0.0, 0.0), 1.2),
    "basement": Grade(1.0, 1.18, 1.15, (0.05, -0.02, 0.0), (0.06, 0.02, -0.03), 1.2),
}
SPELL = Grade(1.04, 1.22, 1.25, (0.02, -0.02, 0.03), (0.05, 0.03, 0.0), 1.35)


class ScreenFX:
    def __init__(self):
        self.grade = Grade()
        self.target = Grade()
        self.grade_speed = 2.0
        self.waves = []  # (x, y, radius, thickness, strength)
        self.impact = 0.0  # radial zoom-blur punch, decays
        self.impact_pos = (W / 2, H / 2)
        self.godray = None  # (x, y, strength, colour)
        self.haze = 0.0  # heat-haze distortion (0..1)
        self.danger = 0.0  # red pulsing vignette (low health)
        self.vignette = 0.55
        self.offset = (0.0, 0.0)  # sub-pixel screen shake
        self.dissolve = None  # (progress 0..1, edge colour) for scene transitions
        self.desaturate = 0.0
        self.lights = LightMap()
        self.t = 0.0

    # --- called by scenes -------------------------------------------------
    def set_grade(self, key_or_grade, speed=2.0):
        g = GRADES.get(key_or_grade, NEUTRAL) if isinstance(key_or_grade, str) else key_or_grade
        self.target = g
        self.grade_speed = speed

    def snap_grade(self, key_or_grade):
        self.set_grade(key_or_grade)
        self.grade = self.target

    def wave(self, x, y, radius, thickness=10.0, strength=1.0):
        if len(self.waves) < MAX_WAVES:
            self.waves.append((x, y, radius, thickness, strength))

    def punch(self, amount=1.0, x=W / 2, y=H / 2):
        if amount >= self.impact:
            self.impact_pos = (x, y)
        self.impact = max(self.impact, amount)

    def begin_frame(self):
        """Clear the per-frame inputs (waves, lights, godray, haze)."""
        self.waves = []
        self.godray = None
        self.haze = 0.0
        self.danger = 0.0
        self.desaturate = 0.0
        self.lights.clear()

    def update(self, dt):
        self.t += dt
        self.impact = max(0.0, self.impact - dt * 3.2)
        k = clamp(dt * self.grade_speed, 0.0, 1.0)
        self.grade = self.grade.blend(self.target, k)

    # --- helpers --------------------------------------------------------------
    def waves_from(self, shockwaves, strength=1.0):
        """Turn fx.Shockwaves rings into refraction ripples."""
        from .util import ease_out_cubic

        for w in shockwaves.items:
            t = 1 - w.life / w.max_life
            r = w.r0 + (w.r1 - w.r0) * ease_out_cubic(t)
            if r > 6:
                self.wave(w.x, w.y, r, 6 + w.width * 3, strength * (1 - t) * min(1.0, w.width / 3))


class LightMap:
    """Low-resolution additive light buffer (1/4 of the canvas).

    Each light is a soft radial glow; the shader adds it to the scene so
    bullets, spells and characters tint the stage around them."""

    _cache = {}

    def __init__(self):
        self.surf = pygame.Surface((LIGHT_W, LIGHT_H))
        self.count = 0
        self.dirty = False

    def clear(self):
        if self.count:
            self.surf.fill((0, 0, 0))
        self.count = 0
        self.dirty = True

    @classmethod
    def _sprite(cls, radius, color):
        key = (radius, color)
        s = cls._cache.get(key)
        if s is None:
            size = radius * 2 + 1
            s = pygame.Surface((size, size))
            s.fill((0, 0, 0))
            steps = max(2, min(radius, 10))
            for i in range(steps, 0, -1):
                k = (1 - i / steps) ** 2
                c = (int(color[0] * k), int(color[1] * k), int(color[2] * k))
                pygame.draw.circle(s, c, (radius, radius), max(1, int(radius * i / steps)))
            if len(cls._cache) > 600:
                cls._cache.clear()
            cls._cache[key] = s
        return s

    def add(self, x, y, radius, color, intensity=1.0):
        """Light at canvas coordinates; radius in canvas pixels."""
        r = max(1, int(radius / 4))
        q = 16  # quantise colours (rounding) so the sprite cache stays small
        k = clamp(intensity, 0.0, 1.0)
        col = tuple(min(255, int(c * k / q + 0.5) * q) for c in color[:3])
        if col == (0, 0, 0):
            return
        s = self._sprite(r, col)
        self.surf.blit(s, (int(x / 4) - r, int(y / 4) - r), special_flags=pygame.BLEND_ADD)
        self.count += 1


def bullet_lights(lights, bullets, palette, limit=220):
    """Every on-screen bullet casts a little coloured light."""
    items = bullets.items
    n = len(items)
    step = max(1, math.ceil(n / limit))
    for i in range(0, n, step):
        b = items[i]
        if b.dead or b.invisible:
            continue
        col = palette.get(b.color, palette["white"])[0]
        lights.add(b.x, b.y, 16 + b.r * 3, col, 0.4)
    for b in bullets.friendly:
        if not b.dead:
            lights.add(b.x, b.y, 22, (255, 210, 120), 0.6)
    for lz in bullets.lasers:
        w = lz.current_width()
        if w > 1:
            col = palette.get(lz.color, palette["white"])[0]
            for k in range(0, int(lz.length), 60):
                lights.add(lz.x + lz.cos * k, lz.y + lz.sin * k, 26 + w * 2, col, 0.7)
