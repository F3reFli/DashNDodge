"""Procedural graphics: animated character frames, glows, magic circles,
pixel-art icons and a few post-processing helpers."""

import math
import random

import pygame

from . import assets
from .util import TAU, scale_color

# --------------------------------------------------------------------------
# Character sprites
# --------------------------------------------------------------------------


def silhouette(surf, color):
    mask = pygame.mask.from_surface(surf)
    out = mask.to_surface(setcolor=(*color[:3], 255), unsetcolor=(0, 0, 0, 0))
    return out.convert_alpha()


def _pad(surf):
    out = pygame.Surface((surf.get_width() + 2, surf.get_height()), pygame.SRCALPHA)
    out.blit(surf, (1, 0))
    return out


def _shear(base, direction):
    """Lean the head 1px towards `direction` (pixel-perfect, no rotation)."""
    out = pygame.Surface((base.get_width() + 2, base.get_height()), pygame.SRCALPHA)
    h = base.get_height()
    cut = int(h * 0.62)
    out.blit(base, (1 + direction, 0), pygame.Rect(0, 0, base.get_width(), cut))
    out.blit(base, (1, cut), pygame.Rect(0, cut, base.get_width(), h - cut))
    return out


def _crouch(padded):
    """Squash the body 1px down while the feet stay planted."""
    w, h = padded.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    legs = 3
    out.blit(padded, (0, h - legs), pygame.Rect(0, h - legs, w, legs))
    out.blit(padded, (0, 1), pygame.Rect(0, 0, w, h - legs))
    return out


class CharArt:
    """Animated version of a static 16x16 sprite, scaled for display."""

    _cache = {}

    @classmethod
    def get(cls, name, scale=2):
        key = (name, scale)
        art = cls._cache.get(key)
        if art is None:
            art = cls(name, scale)
            cls._cache[key] = art
        return art

    def __init__(self, name, scale):
        base = assets.sprite(name)
        self.name = name
        self.scale = scale
        padded = _pad(base)
        frames = {
            "idle0": padded,
            "idle1": _crouch(padded),
            "lean_r0": _shear(base, 1),
            "lean_l0": _shear(base, -1),
        }
        frames["lean_r1"] = _crouch(frames["lean_r0"])
        frames["lean_l1"] = _crouch(frames["lean_l0"])
        self.frames = {k: pygame.transform.scale_by(v, scale) for k, v in frames.items()}
        self.white = {k: silhouette(v, (255, 255, 255)) for k, v in self.frames.items()}
        self.w, self.h = self.frames["idle0"].get_size()
        self._tints = {}
        sw, sh = int(self.w * 0.7), max(3, int(self.h * 0.22))
        self.shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(self.shadow, (0, 0, 0, 90), self.shadow.get_rect())

    def frame(self, t, lean=0, moving=False, white=False):
        speed = 9.0 if moving else 2.2
        phase = int(t * speed) % 2
        if lean > 0:
            key = f"lean_r{phase}"
        elif lean < 0:
            key = f"lean_l{phase}"
        else:
            key = f"idle{phase}"
        return (self.white if white else self.frames)[key]

    def tint(self, color, alpha=120):
        key = (color, alpha)
        surf = self._tints.get(key)
        if surf is None:
            surf = silhouette(self.frames["idle0"], color)
            surf.set_alpha(alpha)
            self._tints[key] = surf
        return surf

    def draw(self, surf, x, y, t, lean=0, moving=False, white=False, squash=(1.0, 1.0), shadow=True, alpha=255):
        img = self.frame(t, lean, moving, white)
        if squash != (1.0, 1.0):
            img = pygame.transform.scale(img, (max(1, int(self.w * squash[0])), max(1, int(self.h * squash[1]))))
        w, h = img.get_size()
        if shadow:
            surf.blit(self.shadow, (int(x - self.shadow.get_width() / 2), int(y + self.h / 2 - self.shadow.get_height() / 2)))
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        # Anchor at the feet so squash/stretch keeps them on the ground.
        surf.blit(img, (int(x - w / 2), int(y + self.h / 2 - h)))


# --------------------------------------------------------------------------
# Glow sprites (for the additive layer: RGB intensity, no alpha needed)
# --------------------------------------------------------------------------

_glow_cache = {}


def glow(radius, color, intensity=1.0):
    radius = max(1, int(radius))
    key = (radius, color, round(intensity, 2))
    surf = _glow_cache.get(key)
    if surf is None:
        size = radius * 2 + 1
        surf = pygame.Surface((size, size))
        surf.fill((0, 0, 0))
        steps = min(radius, 24)
        for i in range(steps, 0, -1):
            r = radius * i / steps
            k = (1 - i / steps) ** 1.6 * intensity
            pygame.draw.circle(surf, scale_color(color, k), (radius, radius), max(1, int(r)))
        _glow_cache[key] = surf
    return surf


def blit_glow(layer, x, y, radius, color, intensity=1.0):
    g = glow(radius, color, intensity)
    layer.blit(g, (int(x - g.get_width() / 2), int(y - g.get_height() / 2)), special_flags=pygame.BLEND_ADD)


# --------------------------------------------------------------------------
# Magic circles (Touhou boss / focus circles)
# --------------------------------------------------------------------------

_circle_cache = {}


def magic_circle(radius, color, points=6, runes=True):
    key = (radius, color, points, runes)
    surf = _circle_cache.get(key)
    if surf is not None:
        return surf
    ss = 2
    size = (radius * 2 + 4) * ss
    big = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    r = radius * ss
    col = (*color, 255)
    dim = (*scale_color(color, 0.6), 255)
    pygame.draw.circle(big, col, (c, c), r, ss + 1)
    pygame.draw.circle(big, dim, (c, c), r * 0.84, ss)
    pygame.draw.circle(big, dim, (c, c), r * 0.34, ss)
    # Star polygon.
    step = 2 if points in (5, 7) else 1
    verts = [
        (c + math.cos(-math.pi / 2 + TAU * i / points) * r * 0.84, c + math.sin(-math.pi / 2 + TAU * i / points) * r * 0.84)
        for i in range(points)
    ]
    if points == 6:
        pygame.draw.polygon(big, col, verts[0::2], ss)
        pygame.draw.polygon(big, col, verts[1::2], ss)
    else:
        order = [verts[(i * (step + 1)) % points] for i in range(points)]
        pygame.draw.polygon(big, col, order, ss)
    if runes:
        rng = random.Random(radius * 31 + points)
        n = max(12, int(radius / 2.2))
        for i in range(n):
            a = TAU * i / n
            rr = r * 0.92
            x, y = c + math.cos(a) * rr, c + math.sin(a) * rr
            length = rng.choice((2, 3, 4)) * ss
            ta = a + math.pi / 2
            pygame.draw.line(
                big,
                col,
                (x - math.cos(ta) * length / 2, y - math.sin(ta) * length / 2),
                (x + math.cos(ta) * length / 2, y + math.sin(ta) * length / 2),
                ss,
            )
            if rng.random() < 0.4:
                pygame.draw.circle(big, dim, (x + math.cos(a) * ss * 2, y + math.sin(a) * ss * 2), ss)
    surf = pygame.transform.smoothscale(big, (size // ss, size // ss))
    _circle_cache[key] = surf
    return surf


def draw_magic_circle(layer, x, y, radius, color, angle, intensity=1.0, points=6, squash=1.0):
    base = magic_circle(int(radius), color, points)
    img = pygame.transform.rotozoom(base, math.degrees(angle), 1.0)
    if squash != 1.0:
        img = pygame.transform.smoothscale(img, (img.get_width(), max(1, int(img.get_height() * squash))))
    if intensity < 1.0:
        img.fill((int(255 * intensity),) * 3 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    layer.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)), special_flags=pygame.BLEND_ADD)


# --------------------------------------------------------------------------
# Pixel-art icons
# --------------------------------------------------------------------------

HEART = [
    ".oo...oo.",
    "orro.orro",
    "owrrorrro",
    "orrrrrrro",
    ".orrrrro.",
    "..orrro..",
    "...oro...",
    "....o....",
]

STAR = [
    "....o....",
    "...oyo...",
    "oooywyooo",
    "oyywyyyyo",
    ".oyyyyyo.",
    "..oyyyo..",
    ".oyyoyyo.",
    ".oyo.oyo.",
    ".oo...oo.",
]

GEM = [
    "...o...",
    "..obo..",
    ".obwbo.",
    "obwbbbo",
    ".obbbo.",
    "..obo..",
    "...o...",
]

COIN = [
    "..ooo..",
    ".oyyyo.",
    "oywyyyo",
    "oyyoyyo",
    "oyyyyyo",
    ".oyyyo.",
    "..ooo..",
]

ICON_COLORS = {
    "o": (24, 10, 30),
    "r": (240, 50, 80),
    "w": (255, 240, 245),
    "y": (255, 214, 64),
    "b": (80, 140, 255),
    "g": (90, 230, 110),
    "e": (70, 60, 90),
    "c": (110, 230, 255),
}

_icon_cache = {}


def pixel_art(rows, colors=None, scale=1, remap=None):
    key = (tuple(rows), scale, tuple(sorted((remap or {}).items())))
    surf = _icon_cache.get(key)
    if surf is None:
        pal = dict(ICON_COLORS)
        if colors:
            pal.update(colors)
        if remap:
            for k, v in remap.items():
                pal[k] = pal.get(v, v) if isinstance(v, str) else v
        surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    surf.set_at((x, y), pal[ch])
        if scale != 1:
            surf = pygame.transform.scale_by(surf, scale)
        _icon_cache[key] = surf
    return surf


def heart_icon(empty=False, scale=1):
    if empty:
        return pixel_art(HEART, remap={"r": "e", "w": "e"}, scale=scale)
    return pixel_art(HEART, scale=scale)


def star_icon(empty=False, scale=1):
    if empty:
        return pixel_art(STAR, remap={"y": "e", "w": "e"}, scale=scale)
    return pixel_art(STAR, scale=scale)


# --------------------------------------------------------------------------
# Misc drawing helpers
# --------------------------------------------------------------------------


def vgradient(size, top, bottom):
    w, h = size
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        surf.fill(
            (
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            ),
            (0, y, w, 1),
        )
    return surf


_vignette_cache = {}


def vignette(size, strength=170):
    key = (size, strength)
    surf = _vignette_cache.get(key)
    if surf is None:
        w, h = size
        small = pygame.Surface((w // 8, h // 8), pygame.SRCALPHA)
        cx, cy = small.get_width() / 2, small.get_height() / 2
        math.hypot(cx, cy)
        for y in range(small.get_height()):
            for x in range(small.get_width()):
                d = math.hypot((x + 0.5 - cx) / cx, (y + 0.5 - cy) / cy) / 1.41
                a = int(strength * max(0.0, d - 0.45) / 0.55)
                small.set_at((x, y), (0, 0, 0, min(255, a)))
        surf = pygame.transform.smoothscale(small, (w, h))
        _vignette_cache[key] = surf
    return surf


BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def newspaper_photo(src, size, ink=(36, 28, 24), paper=(232, 222, 196)):
    """Turn a screenshot into a 2-tone ordered-dither newspaper photo."""
    img = pygame.transform.smoothscale(src, size)
    out = pygame.Surface(size)
    w, h = size
    img.lock()
    out.lock()
    for y in range(h):
        row = BAYER4[y & 3]
        for x in range(w):
            r, g, b, *_ = img.get_at((x, y))
            lum = (r * 0.3 + g * 0.59 + b * 0.11) / 255.0
            lum = min(1.0, lum * 1.6 + 0.04)
            out.set_at((x, y), paper if lum * 16 > row[x & 3] + 0.5 else ink)
    img.unlock()
    out.unlock()
    return out


def blur(surf, factor=4):
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


def ring(layer, x, y, radius, color, width=2, intensity=1.0):
    if radius < 1:
        return
    pygame.draw.circle(layer, scale_color(color, intensity), (int(x), int(y)), int(radius), max(1, int(width)))
