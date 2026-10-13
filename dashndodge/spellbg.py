"""Spell card backgrounds: the enigmatic, layered, rotating patterns Touhou
swaps in when a boss declares a card. One composition per boss.

Rendered at half resolution (320x180) and scaled up: cheap, and the
chunky pixels suit the look."""

import math
import random

import pygame

from . import assets, gfx
from . import textures as tx
from .config import H, W
from .util import TAU, hsv, scale_color

SW, SH = W // 2, H // 2


# ----------------------------------------------------------------------
# Pattern builders (all cached through textures.cached)
# ----------------------------------------------------------------------


@tx.cached
def kanji_ring(text, radius, color, size=12):
    d = radius * 2 + 24
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = d / 2
    n = max(len(text), int(TAU * radius / (size + 4)))
    for i in range(n):
        ch = text[i % len(text)]
        a = TAU * i / n
        g = assets.text(ch, size, color, None)
        g = pygame.transform.rotate(g, -math.degrees(a) - 90)
        x = c + math.cos(a) * radius - g.get_width() / 2
        y = c + math.sin(a) * radius - g.get_height() / 2
        s.blit(g, (x, y))
    pygame.draw.circle(s, color, (c, c), radius - size, 1)
    pygame.draw.circle(s, color, (c, c), radius + size - 2, 1)
    return s


@tx.cached
def kanji_tile(text, color, cell=22, size=12):
    n = len(text)
    s = pygame.Surface((cell * n, cell * n), pygame.SRCALPHA)
    for j in range(n):
        for i in range(n):
            g = assets.text(text[(i + j) % n], size, color, None)
            s.blit(g, (i * cell + (cell - g.get_width()) // 2, j * cell + (cell - g.get_height()) // 2))
    return s


@tx.cached
def rays(n, radius, color, width=0.5):
    d = radius * 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = radius
    for i in range(n):
        a0 = TAU * i / n
        a1 = a0 + TAU / n * width
        pygame.draw.polygon(s, color, [(c, c), (c + math.cos(a0) * radius, c + math.sin(a0) * radius),
                                       (c + math.cos(a1) * radius, c + math.sin(a1) * radius)])
    return s


@tx.cached
def mandala(radius, color, petals=12, seed=0):
    rng = random.Random(seed)
    d = radius * 2 + 4
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = d / 2
    for r in (radius, radius * 0.82, radius * 0.5, radius * 0.22):
        pygame.draw.circle(s, color, (c, c), int(r), 1)
    for i in range(petals):
        a = TAU * i / petals
        px, py = c + math.cos(a) * radius * 0.66, c + math.sin(a) * radius * 0.66
        petal = pygame.Surface((int(radius * 0.34), int(radius * 0.14)), pygame.SRCALPHA)
        pygame.draw.ellipse(petal, color, petal.get_rect(), 1)
        petal = pygame.transform.rotate(petal, -math.degrees(a))
        s.blit(petal, (px - petal.get_width() / 2, py - petal.get_height() / 2))
        pygame.draw.line(s, color, (c + math.cos(a) * radius * 0.22, c + math.sin(a) * radius * 0.22),
                         (c + math.cos(a) * radius * 0.5, c + math.sin(a) * radius * 0.5))
    for i in range(petals * 3):
        a = TAU * i / (petals * 3)
        r = radius * 0.91
        s.fill(color, (c + math.cos(a) * r - 1, c + math.sin(a) * r - 1, rng.choice((1, 2, 3)), 2))
    return s


@tx.cached
def snowflake(radius, color):
    d = radius * 2 + 4
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = d / 2
    for i in range(6):
        a = TAU * i / 6
        ex, ey = c + math.cos(a) * radius, c + math.sin(a) * radius
        pygame.draw.line(s, color, (c, c), (ex, ey), 2)
        for k in (0.35, 0.6, 0.82):
            bx, by = c + math.cos(a) * radius * k, c + math.sin(a) * radius * k
            L = radius * (0.32 - k * 0.2)
            for side in (-1, 1):
                b = a + side * 0.7
                pygame.draw.line(s, color, (bx, by), (bx + math.cos(b) * L, by + math.sin(b) * L), 1)
    pygame.draw.circle(s, color, (c, c), int(radius * 0.18), 1)
    return s


@tx.cached
def taijitu(radius, c1, c2):
    d = radius * 2 + 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = radius + 1
    pygame.draw.circle(s, c1, (c, c), radius)
    pygame.draw.rect(s, (0, 0, 0, 0), (c, 0, radius + 1, d))
    pygame.draw.circle(s, c2, (c, c), radius, draw_top_right=True, draw_bottom_right=True)
    pygame.draw.circle(s, c1, (c, c - radius / 2), radius / 2)
    pygame.draw.circle(s, c2, (c, c + radius / 2), radius / 2)
    pygame.draw.circle(s, c2, (c, c - radius / 2), radius / 7)
    pygame.draw.circle(s, c1, (c, c + radius / 2), radius / 7)
    return s


@tx.cached
def element_circle(radius, color):
    d = radius * 2 + 30
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = d / 2
    pts = [(c + math.cos(-math.pi / 2 + TAU * i / 5) * radius, c + math.sin(-math.pi / 2 + TAU * i / 5) * radius) for i in range(5)]
    pygame.draw.circle(s, color, (c, c), radius, 1)
    pygame.draw.polygon(s, color, [pts[(i * 2) % 5] for i in range(5)], 1)
    cols = [(255, 120, 60), (90, 160, 255), (100, 220, 120), (230, 220, 140), (190, 140, 80)]
    for (x, y), ch, col in zip(pts, "火水木金土", cols):
        pygame.draw.circle(s, (0, 0, 0, 0), (x, y), 10)
        pygame.draw.circle(s, col, (x, y), 10, 1)
        g = assets.text(ch, 12, col, None)
        s.blit(g, (x - g.get_width() / 2, y - g.get_height() / 2))
    return s


@tx.cached
def clock_face(radius, color):
    d = radius * 2 + 4
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = d / 2
    pygame.draw.circle(s, color, (c, c), radius, 2)
    pygame.draw.circle(s, color, (c, c), int(radius * 0.86), 1)
    for i in range(60):
        a = TAU * i / 60
        r0 = radius * (0.8 if i % 5 == 0 else 0.86)
        pygame.draw.line(s, color, (c + math.cos(a) * r0, c + math.sin(a) * r0), (c + math.cos(a) * radius * 0.95, c + math.sin(a) * radius * 0.95))
    return s


@tx.cached
def spiral(radius, color, arms=4):
    d = radius * 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = radius
    for k in range(arms):
        pts = []
        for i in range(80):
            t = i / 79
            a = TAU * k / arms + t * 5.0
            r = t * radius
            pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
        pygame.draw.lines(s, color, False, pts, 3)
    return s


@tx.cached
def shards(seed, radius):
    rng = random.Random(seed)
    d = radius * 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    for i in range(26):
        a = rng.uniform(0, TAU)
        r = rng.uniform(radius * 0.2, radius * 0.95)
        x, y = radius + math.cos(a) * r, radius + math.sin(a) * r
        col = hsv(rng.random(), 0.5, 0.32)
        L = rng.uniform(6, 18)
        b = a + rng.uniform(-0.5, 0.5)
        pygame.draw.polygon(s, (*col, 200), [(x, y), (x + math.cos(b) * L, y + math.sin(b) * L),
                                             (x + math.cos(b + 0.4) * L * 0.5, y + math.sin(b + 0.4) * L * 0.5)])
    return s


# ----------------------------------------------------------------------
# Layer helpers
# ----------------------------------------------------------------------


def rot(buf, img, angle, x=SW / 2, y=SH / 2, scale=1.0, add=True, alpha=None):
    r = pygame.transform.rotozoom(img, math.degrees(angle), scale) if (angle or scale != 1.0) else img
    if alpha is not None and not add:
        r = r.copy()
        r.set_alpha(alpha)
    buf.blit(r, (x - r.get_width() / 2, y - r.get_height() / 2), special_flags=pygame.BLEND_ADD if add else 0)


def scroll(buf, tile, t, vx, vy, add=True):
    tw, th = tile.get_size()
    ox = int(t * vx) % tw
    oy = int(t * vy) % th
    for x in range(-ox, SW, tw):
        for y in range(-oy, SH, th):
            buf.blit(tile, (x, y), special_flags=pygame.BLEND_ADD if add else 0)


def dim(c, k):
    return scale_color(c, k)


# ----------------------------------------------------------------------
# Compositions
# ----------------------------------------------------------------------


class SpellBG:
    base = (6, 2, 10)

    def __init__(self, color):
        self.color = color
        self.buf = pygame.Surface((SW, SH)).convert()
        self.big = pygame.Surface((W, H)).convert()
        self.build()

    def build(self):
        c = self.color
        self.m1 = mandala(80, dim(c, 0.5), 12, 1)
        self.m2 = mandala(46, dim(c, 0.35), 8, 2)
        self.ring = kanji_ring("符符符", 62, dim(c, 0.4))

    def layers(self, buf, t):
        rot(buf, self.m1, t * 0.2)
        rot(buf, self.ring, -t * 0.12)
        rot(buf, self.m2, -t * 0.4)

    def draw(self, surf, t, alpha=1.0):
        buf = self.buf
        buf.fill(self.base)
        self.layers(buf, t)
        pygame.transform.scale(buf, (W, H), self.big)
        if alpha < 0.999:
            self.big.set_alpha(int(255 * alpha))
        else:
            self.big.set_alpha(None)
        surf.blit(self.big, (0, 0))


class RumiaBG(SpellBG):
    base = (4, 0, 6)

    def build(self):
        self.clouds = tx.colorize(tx.noise(128, 901, 4, 4), (0, 0, 0), (40, 6, 40))
        self.sun = pygame.transform.smoothscale(tx.black_sun(26, (200, 30, 50)), (104, 104))
        self.rays = rays(24, 150, (24, 2, 10))
        self.ring = kanji_ring("闇夜宵闇", 70, (120, 10, 30))
        self.ring2 = kanji_ring("人喰い", 48, (80, 6, 24))

    def layers(self, buf, t):
        scroll(buf, self.clouds, t, 10, 4)
        rot(buf, self.rays, t * 0.08)
        rot(buf, self.ring, -t * 0.15)
        rot(buf, self.ring2, t * 0.25)
        buf.blit(self.sun, (SW / 2 - 52, SH / 2 - 52))


class CirnoBG(SpellBG):
    base = (2, 8, 22)

    def build(self):
        self.tile = kanji_tile("氷", (14, 34, 60), 20)
        self.flake = snowflake(80, (40, 96, 150))
        self.flake2 = snowflake(40, (90, 170, 220))
        self.m = mandala(86, (20, 50, 90), 6, 3)

    def layers(self, buf, t):
        scroll(buf, self.tile, t, 14, -10)
        rot(buf, self.m, -t * 0.1)
        rot(buf, self.flake, t * 0.18, scale=1 + 0.05 * math.sin(t))
        rot(buf, self.flake2, -t * 0.5)
        for i in range(30):
            r = random.Random(i)
            x = (r.uniform(0, SW) + t * r.uniform(-8, 8)) % SW
            y = (r.uniform(0, SH) + t * r.uniform(10, 25)) % SH
            buf.fill((150, 200, 240), (int(x), int(y), 1, 1))


class MeilingBG(SpellBG):
    base = (4, 8, 6)

    def build(self):
        self.tile = kanji_tile("気功", (10, 30, 16), 22)
        self.tai = taijitu(34, (78, 84, 74), (10, 12, 12))
        self.ring = kanji_ring("華人小娘", 60, (50, 120, 70))

    def layers(self, buf, t):
        scroll(buf, self.tile, t, -12, 6)
        r = rays(18, 170, scale_color(hsv(int(t * 0.05 * 24) / 24, 0.8, 1.0), 0.09))
        rot(buf, r, t * 0.15)
        rot(buf, self.ring, -t * 0.2)
        rot(buf, self.tai, t * 0.8, add=False)
        for i in range(7):
            a = t * 0.6 + TAU * i / 7
            x, y = SW / 2 + math.cos(a) * 52, SH / 2 + math.sin(a) * 52
            pygame.draw.circle(buf, scale_color(hsv(i / 7, 0.8, 1.0), 0.8), (int(x), int(y)), 3)


class PatchouliBG(SpellBG):
    base = (8, 3, 16)

    def build(self):
        self.tile = kanji_tile("魔法書", (24, 12, 40), 22)
        self.elem = element_circle(64, (120, 80, 200))
        self.m = mandala(84, (50, 26, 90), 16, 4)
        self.hexa = gfx.magic_circle(40, (90, 60, 160), 6)

    def layers(self, buf, t):
        scroll(buf, self.tile, t, 0, 12)
        rot(buf, self.m, t * 0.07)
        rot(buf, self.elem, -t * 0.25, add=False)
        rot(buf, self.hexa, t * 0.6)
        for i in range(8):
            r = random.Random(i + 40)
            x = (r.uniform(0, SW) + t * r.uniform(-6, 6)) % SW
            y = (r.uniform(0, SH) - t * r.uniform(6, 14)) % SH
            pygame.draw.rect(buf, (60, 40, 70), (int(x), int(y), 8, 6), 1)


class SakuyaBG(SpellBG):
    base = (4, 4, 16)

    def build(self):
        self.tile = kanji_tile("時", (14, 14, 40), 20)
        self.c1 = clock_face(84, (50, 50, 110))
        self.c2 = clock_face(52, (80, 80, 150))
        self.c3 = clock_face(26, (120, 120, 200))

    def layers(self, buf, t):
        scroll(buf, self.tile, t, 8, 8)
        rot(buf, self.c1, t * 0.05)
        rot(buf, self.c2, -t * 0.15, SW / 2 - 70, SH / 2 + 20)
        rot(buf, self.c3, -int(t) * TAU / 60, SW / 2 + 80, SH / 2 - 30)
        cx, cy = SW / 2, SH / 2
        for length, ang, col in ((60, t * 0.05, (90, 90, 170)), (76, t * 0.6, (140, 140, 220)), (80, int(t * 2) * TAU / 60, (220, 220, 255))):
            pygame.draw.line(buf, col, (cx, cy), (cx + math.sin(ang) * length, cy - math.cos(ang) * length), 1)


class RemiliaBG(SpellBG):
    base = (12, 0, 4)

    def build(self):
        self.clouds = tx.colorize(tx.noise(128, 902, 4, 4), (0, 0, 0), (70, 6, 16))
        self.spiral = spiral(120, (90, 6, 20), 5)
        self.ring = kanji_ring("紅紅月", 66, (150, 20, 30))
        moon = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(moon, (150, 10, 24), (35, 35), 34)
        pygame.draw.circle(moon, (200, 30, 40), (35, 35), 30)
        self.moon = moon

    def layers(self, buf, t):
        scroll(buf, self.clouds, t, 18, 0)
        rot(buf, self.spiral, t * 0.35)
        rot(buf, self.ring, -t * 0.12)
        buf.blit(self.moon, (SW / 2 - 35, SH / 2 - 35))
        for k in range(10):
            r = random.Random(k + 70)
            a = t * r.uniform(0.3, 0.8) + r.uniform(0, TAU)
            rr = r.uniform(50, 100)
            x, y = SW / 2 + math.cos(a) * rr, SH / 2 + math.sin(a) * rr * 0.6
            f = 2 if int(t * 8 + k) % 2 else -1
            pygame.draw.polygon(buf, (20, 0, 6), [(x, y), (x - 5, y - f), (x - 2, y + 1)])
            pygame.draw.polygon(buf, (20, 0, 6), [(x, y), (x + 5, y - f), (x + 2, y + 1)])


class FlandreBG(SpellBG):
    base = (6, 0, 6)

    def build(self):
        self.tile = kanji_tile("禁壊", (40, 4, 14), 22)
        self.sh = shards(5, 110)
        self.sh2 = shards(6, 70)
        self.ring = kanji_ring("四百九十五年", 74, (140, 30, 50))

    def layers(self, buf, t):
        scroll(buf, self.tile, t, -20, 14)
        r = rays(14, 170, scale_color(hsv(int(t * 0.08 * 24) / 24, 0.7, 1.0), 0.07))
        rot(buf, r, -t * 0.2)
        rot(buf, self.sh, t * 0.25)
        rot(buf, self.sh2, -t * 0.6)
        rot(buf, self.ring, t * 0.1)
        if int(t * 12) % 9 == 0:
            rng = random.Random(int(t * 40))
            for _ in range(5):
                y = rng.randrange(0, SH - 6)
                h = rng.randint(1, 6)
                band = buf.subsurface((0, y, SW, h)).copy()
                buf.blit(band, (rng.randint(-14, 14), y))


BY_BOSS = {
    "rumia": RumiaBG,
    "cirno": CirnoBG,
    "meiling": MeilingBG,
    "patchouli": PatchouliBG,
    "sakuya": SakuyaBG,
    "remilia": RemiliaBG,
    "flandre": FlandreBG,
}

_instances = {}


def get(boss_id, color):
    key = boss_id if boss_id in BY_BOSS else (boss_id, color)
    bg = _instances.get(key)
    if bg is None:
        bg = BY_BOSS.get(boss_id, SpellBG)(color)
        _instances[key] = bg
    return bg
