"""Procedural textures (tileable floors, noise) and pixel-art props for the
pseudo-3D stage backgrounds. Everything is generated once and cached."""

import math
import random

import pygame

from . import assets
from .util import TAU, mix, scale_color

_cache = {}


def cached(fn):
    def wrapper(*args):
        key = (fn.__name__,) + args
        if key not in _cache:
            _cache[key] = fn(*args)
        return _cache[key]

    wrapper.__name__ = fn.__name__
    return wrapper


# ======================================================================
# Noise
# ======================================================================


def _octave(size, cells, rng):
    """Tileable smooth value noise: a periodic random grid, upscaled, cropped."""
    g = pygame.Surface((cells, cells))
    for y in range(cells):
        for x in range(cells):
            v = rng.randint(0, 255)
            g.set_at((x, y), (v, v, v))
    tiled = pygame.Surface((cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            tiled.blit(g, (i * cells, j * cells))
    big = pygame.transform.smoothscale(tiled, (size * 3, size * 3))
    return big.subsurface((size, size, size, size)).copy()


@cached
def noise(size, seed, octaves=4, base_cells=4):
    rng = random.Random(seed)
    out = pygame.Surface((size, size))
    out.fill((0, 0, 0))
    amp = 0.5
    cells = base_cells
    total = 0.0
    for _ in range(octaves):
        o = _octave(size, min(cells, size), rng)
        o.fill((int(255 * amp),) * 3, special_flags=pygame.BLEND_MULT)
        out.blit(o, (0, 0), special_flags=pygame.BLEND_ADD)
        total += amp
        amp *= 0.5
        cells *= 2
    k = 1.0 / total
    if k > 1:
        boost = out.copy()
        boost.fill((int(255 * (k - 1)),) * 3, special_flags=pygame.BLEND_MULT)
        out.blit(boost, (0, 0), special_flags=pygame.BLEND_ADD)
    return out


def colorize(gray, c0, c1):
    """Map a grayscale surface to the c0 -> c1 gradient (per channel)."""
    w, h = gray.get_size()
    out = pygame.Surface((w, h))
    out.fill(c0)
    for ch in range(3):
        d = c1[ch] - c0[ch]
        if d == 0:
            continue
        part = gray.copy()
        mask = [0, 0, 0]
        mask[ch] = abs(d)
        part.fill(tuple(mask), special_flags=pygame.BLEND_MULT)
        out.blit(part, (0, 0), special_flags=pygame.BLEND_ADD if d > 0 else pygame.BLEND_SUB)
    return out


def speckle(surf, n, colors, rng, size=(1, 2)):
    w, h = surf.get_size()
    for _ in range(n):
        s = rng.randint(*size)
        surf.fill(rng.choice(colors), (rng.randrange(w), rng.randrange(h), s, s))


# ======================================================================
# Floor / ceiling tiles (width, height must tile)
# ======================================================================


@cached
def forest_floor():
    rng = random.Random(11)
    w, h = 512, 256
    n = noise(256, 101, 4, 4)
    base = colorize(n, (10, 6, 16), (40, 22, 46))
    tile = pygame.Surface((w, h))
    tile.blit(base, (0, 0))
    tile.blit(base, (256, 0))
    # the path, running forward through the middle
    path_n = colorize(noise(256, 102, 3, 8), (34, 22, 30), (70, 48, 56))
    path = pygame.Surface((150, h))
    path.blit(path_n, (0, 0), (0, 0, 150, h))
    tile.blit(path, (w // 2 - 75, 0))
    for y in range(0, h, 2):
        for side in (-1, 1):
            x = w // 2 + side * (75 + rng.randint(-3, 3))
            tile.fill((22, 12, 24), (x - 2, y, 4, 2))
    for _ in range(40):
        x = w // 2 + rng.randint(-60, 50)
        y = rng.randrange(h)
        r = rng.randint(3, 7)
        pygame.draw.ellipse(tile, (56, 42, 52), (x, y, r * 2, r))
        pygame.draw.ellipse(tile, (84, 64, 74), (x + 1, y, r * 2 - 3, r - 2))
    speckle(tile, 500, [(150, 40, 50), (120, 30, 40), (180, 90, 50), (60, 20, 30)], rng, (1, 2))
    return tile


@cached
def lake_water():
    rng = random.Random(22)
    n = noise(256, 201, 4, 4)
    tile = colorize(n, (6, 12, 30), (20, 44, 80))
    for _ in range(220):
        x, y = rng.randrange(256), rng.randrange(256)
        ln = rng.randint(4, 16)
        tile.fill(rng.choice([(50, 90, 140), (70, 120, 170), (30, 70, 110)]), (x, y, ln, 1))
    for _ in range(9):
        x, y = rng.randrange(20, 236), rng.randrange(20, 236)
        r = rng.randint(6, 11)
        pygame.draw.ellipse(tile, (14, 40, 30), (x - r, y - r // 2, r * 2, r))
        pygame.draw.ellipse(tile, (24, 64, 44), (x - r + 1, y - r // 2 + 1, r * 2 - 2, r - 2))
        pygame.draw.line(tile, (14, 40, 30), (x, y), (x + r, y - 1), 2)
        if rng.random() < 0.4:
            tile.fill((230, 160, 190), (x - 1, y - 2, 3, 2))
    speckle(tile, 120, [(200, 230, 255), (140, 190, 240)], rng, (1, 1))
    return tile


@cached
def garden_floor():
    rng = random.Random(33)
    w, h = 512, 256
    tile = pygame.Surface((w, h))
    grass = colorize(noise(256, 301, 4, 4), (10, 8, 8), (30, 22, 18))
    tile.blit(grass, (0, 0))
    tile.blit(grass, (256, 0))
    # brick path
    px0, pw = w // 2 - 70, 140
    pygame.draw.rect(tile, (40, 14, 14), (px0, 0, pw, h))
    for row in range(0, h, 12):
        off = 0 if (row // 12) % 2 == 0 else 14
        for x in range(px0 - off, px0 + pw, 28):
            c = rng.randint(70, 96)
            r = pygame.Rect(x + 1, row + 1, 26, 10).clip(pygame.Rect(px0, 0, pw, h))
            tile.fill((c, c // 3, c // 4), r)
    pygame.draw.rect(tile, (110, 100, 90), (px0 - 6, 0, 6, h))
    pygame.draw.rect(tile, (110, 100, 90), (px0 + pw, 0, 6, h))
    # rose beds
    for side in (-1, 1):
        bx = w // 2 + side * 120
        for _ in range(140):
            x = bx + rng.randint(-34, 34)
            y = rng.randrange(h)
            tile.fill((26, 40, 22), (x, y, 4, 3))
            if rng.random() < 0.45:
                tile.fill(rng.choice([(200, 20, 40), (150, 10, 30), (230, 60, 70)]), (x, y, 2, 2))
    return tile


@cached
def library_floor():
    w, h = 512, 256
    tile = pygame.Surface((w, h))
    # marble checker outside the carpet
    for y in range(0, h, 32):
        for x in range(0, w, 32):
            c = (34, 26, 40) if ((x + y) // 32) % 2 == 0 else (20, 14, 26)
            tile.fill(c, (x, y, 32, 32))
    rng = random.Random(44)
    for _ in range(300):
        x, y = rng.randrange(w), rng.randrange(h)
        pygame.draw.line(tile, (44, 36, 52), (x, y), (x + rng.randint(-8, 8), y + rng.randint(2, 10)))
    # carpet runner
    cx0, cw = w // 2 - 90, 180
    tile.fill((70, 10, 24), (cx0, 0, cw, h))
    for x in (cx0 + 6, cx0 + cw - 10):
        tile.fill((170, 130, 50), (x, 0, 4, h))
    for y in range(0, h, 64):
        c = (w // 2, y + 32)
        pts = [(c[0], c[1] - 26), (c[0] + 40, c[1]), (c[0], c[1] + 26), (c[0] - 40, c[1])]
        pygame.draw.polygon(tile, (110, 20, 40), pts)
        pygame.draw.polygon(tile, (170, 130, 50), pts, 2)
        pygame.draw.circle(tile, (170, 130, 50), c, 5, 1)
    return tile


@cached
def library_ceiling():
    w, h = 512, 256
    tile = pygame.Surface((w, h))
    tile.fill((12, 8, 12))
    for y in range(0, h, 64):
        tile.fill((30, 18, 14), (0, y, w, 12))
        tile.fill((44, 28, 20), (0, y + 2, w, 3))
    for x in range(0, w, 128):
        tile.fill((26, 16, 12), (x, 0, 10, h))
    return tile


@cached
def clock_floor():
    w, h = 512, 256
    tile = pygame.Surface((w, h))
    tile.fill((18, 18, 30))
    for y in range(0, h, 64):
        for x in range(0, w, 64):
            pygame.draw.rect(tile, (30, 30, 46), (x + 1, y + 1, 62, 62))
            for cx, cy in ((x + 6, y + 6), (x + 58, y + 6), (x + 6, y + 58), (x + 58, y + 58)):
                tile.fill((70, 70, 96), (cx, cy, 2, 2))
    for k in range(4):
        cx, cy = 64 + k * 128, 64 + (k % 2) * 128
        r = 40
        pts = []
        for i in range(48):
            a = TAU * i / 48
            rr = r + (6 if (i % 4) < 2 else 0)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        pygame.draw.polygon(tile, (110, 80, 40), pts, 2)
        pygame.draw.circle(tile, (110, 80, 40), (cx, cy), 14, 2)
    for x in range(0, w, 8):
        tile.fill((10, 10, 20), (x, 0, 1, h))
    return tile


@cached
def cloud_sea():
    n = noise(256, 601, 5, 4)
    tile = colorize(n, (8, 1, 4), (72, 12, 26))
    hi = noise(256, 602, 3, 8)
    hi = colorize(hi, (0, 0, 0), (34, 10, 18))
    tile.blit(hi, (0, 0), special_flags=pygame.BLEND_ADD)
    return tile


@cached
def stone_floor():
    rng = random.Random(77)
    tile = pygame.Surface((256, 256))
    tile.fill((8, 4, 8))
    for row in range(0, 256, 16):
        off = 0 if (row // 16) % 2 == 0 else 16
        for x in range(-off, 256, 32):
            c = rng.randint(24, 40)
            tile.fill((c + 6, c - 6, c), (x + 1, row + 1, 30, 14))
    for _ in range(12):
        x, y = rng.randrange(256), rng.randrange(256)
        for _ in range(5):
            nx, ny = x + rng.randint(-14, 14), y + rng.randint(-14, 14)
            pygame.draw.line(tile, (4, 0, 4), (x, y), (nx, ny))
            x, y = nx, ny
    speckle(tile, 40, [(200, 60, 60), (60, 200, 220), (230, 200, 60), (160, 80, 220)], rng, (1, 2))
    return tile


@cached
def sigil_floor():
    """Basement floor: stone with a glowing red summoning circle."""
    tile = stone_floor().copy()
    c = (128, 128)
    red = (170, 20, 30)
    pygame.draw.circle(tile, red, c, 92, 2)
    pygame.draw.circle(tile, red, c, 80, 1)
    pts = [(c[0] + math.cos(-math.pi / 2 + TAU * i / 5) * 80, c[1] + math.sin(-math.pi / 2 + TAU * i / 5) * 80) for i in range(5)]
    pygame.draw.polygon(tile, red, [pts[(i * 2) % 5] for i in range(5)], 2)
    for i in range(16):
        a = TAU * i / 16
        tile.fill((220, 50, 60), (c[0] + math.cos(a) * 86 - 1, c[1] + math.sin(a) * 86 - 1, 3, 3))
    return tile


@cached
def stone_pillar():
    s = pygame.Surface((24, 110), pygame.SRCALPHA)
    s.fill((34, 26, 32), (3, 8, 18, 102))
    s.fill((50, 40, 48), (3, 8, 4, 102))
    s.fill((24, 18, 22), (0, 0, 24, 10))
    s.fill((24, 18, 22), (0, 100, 24, 10))
    s.fill((150, 16, 30), (8, 30, 8, 40))
    s.fill((90, 8, 18), (8, 66, 8, 4))
    return s


@cached
def cage():
    s = pygame.Surface((26, 40), pygame.SRCALPHA)
    col = (60, 52, 60)
    s.fill(col, (12, 0, 2, 6))
    pygame.draw.ellipse(s, col, (1, 4, 24, 10), 1)
    for x in range(2, 25, 5):
        s.fill(col, (x, 9, 1, 26))
    s.fill(col, (1, 34, 24, 3))
    pygame.draw.circle(s, (255, 190, 80), (13, 26), 3)
    return s


@cached
def shrine_path():
    rng = random.Random(88)
    w, h = 512, 256
    tile = pygame.Surface((w, h))
    gravel = colorize(noise(256, 801, 3, 16), (24, 8, 10), (60, 18, 20))
    tile.blit(gravel, (0, 0))
    tile.blit(gravel, (256, 0))
    x0, pw = w // 2 - 60, 120
    for y in range(0, h, 32):
        c = rng.randint(50, 66)
        tile.fill((c, c - 6, c - 4), (x0, y + 1, pw, 30))
        tile.fill((c + 14, c + 8, c + 6), (x0, y + 1, pw, 2))
    return tile


# ======================================================================
# Props (pixel art, bottom-centre anchored)
# ======================================================================

VERMILION = (196, 40, 30)
VERMILION_DK = (130, 20, 18)


@cached
def torii(shade=1.0):
    s = pygame.Surface((72, 64), pygame.SRCALPHA)
    red = scale_color(VERMILION, shade)
    dk = scale_color(VERMILION_DK, shade)
    blk = (20, 10, 12)
    # pillars
    for x in (13, 53):
        s.fill(red, (x, 14, 7, 46))
        s.fill(dk, (x + 5, 14, 2, 46))
        s.fill(blk, (x - 1, 58, 9, 6))
    # kasagi (top beam with upturned tips) + shimaki
    s.fill(blk, (2, 3, 68, 5))
    s.fill(blk, (0, 1, 4, 4))
    s.fill(blk, (68, 1, 4, 4))
    s.fill(red, (4, 8, 64, 4))
    # gakuzuka + plaque
    s.fill(red, (33, 12, 6, 8))
    s.fill(blk, (31, 13, 10, 6))
    # nuki
    s.fill(red, (8, 21, 56, 4))
    s.fill(dk, (8, 24, 56, 1))
    # shimenawa rope + shide papers
    for x in range(14, 59):
        y = 28 + int(2 * math.sin((x - 14) / 45 * math.pi))
        s.fill((200, 180, 130), (x, y, 1, 2))
    for x in (22, 34, 46):
        for k in range(3):
            s.fill((240, 240, 236), (x + (k % 2), 31 + k * 3, 3, 3))
    return s


@cached
def stone_lantern():
    s = pygame.Surface((20, 44), pygame.SRCALPHA)
    st = (70, 66, 72)
    dk = (40, 36, 44)
    s.fill(dk, (3, 40, 14, 4))
    s.fill(st, (8, 24, 4, 16))
    s.fill(st, (4, 21, 12, 3))
    s.fill(dk, (4, 12, 12, 9))
    s.fill((255, 170, 70), (7, 14, 6, 5))
    pygame.draw.polygon(s, st, [(0, 12), (10, 4), (20, 12)])
    s.fill(st, (8, 0, 4, 4))
    return s


@cached
def pine(color=(14, 8, 18), rim=(60, 30, 70)):
    s = pygame.Surface((48, 100), pygame.SRCALPHA)
    s.fill(color, (21, 60, 6, 40))
    for i, (y, half) in enumerate(((8, 8), (22, 14), (38, 19), (54, 23))):
        pygame.draw.polygon(s, color, [(24, y - 10), (24 - half, y + 14), (24 + half, y + 14)])
        pygame.draw.line(s, rim, (24, y - 10), (24 + half, y + 14))
    return s


@cached
def dead_tree(color=(16, 8, 14)):
    rng = random.Random(5)
    s = pygame.Surface((56, 100), pygame.SRCALPHA)

    def branch(x, y, a, length, width):
        if length < 4 or width < 1:
            return
        nx, ny = x + math.cos(a) * length, y + math.sin(a) * length
        pygame.draw.line(s, color, (x, y), (nx, ny), width)
        for _ in range(2):
            branch(nx, ny, a + rng.uniform(-0.7, 0.7), length * 0.68, width - 1)

    branch(28, 100, -math.pi / 2, 34, 5)
    return s


@cached
def jizo():
    s = pygame.Surface((12, 18), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (90, 86, 92), (2, 0, 8, 8))
    s.fill((90, 86, 92), (1, 6, 10, 12))
    pygame.draw.polygon(s, (190, 20, 30), [(1, 8), (11, 8), (6, 14)])
    return s


@cached
def reeds():
    s = pygame.Surface((18, 44), pygame.SRCALPHA)
    for x, hgt in ((3, 40), (8, 44), (13, 36), (16, 30)):
        pygame.draw.line(s, (30, 46, 40), (x, 44), (x + 1, 44 - hgt), 1)
        if hgt > 34:
            s.fill((60, 40, 30), (x, 44 - hgt, 2, 6))
    return s


@cached
def ice_shard():
    s = pygame.Surface((26, 52), pygame.SRCALPHA)
    pygame.draw.polygon(s, (120, 200, 240, 200), [(13, 0), (24, 30), (16, 52), (6, 52), (2, 26)])
    pygame.draw.polygon(s, (220, 245, 255, 230), [(13, 4), (17, 28), (12, 48), (9, 28)])
    return s


@cached
def red_lantern_post():
    s = pygame.Surface((18, 60), pygame.SRCALPHA)
    s.fill((30, 14, 12), (8, 14, 2, 46))
    s.fill((30, 14, 12), (4, 12, 10, 2))
    pygame.draw.ellipse(s, (210, 30, 30), (2, 14, 14, 16))
    pygame.draw.ellipse(s, (255, 120, 60), (5, 17, 8, 10))
    s.fill((240, 200, 80), (6, 13, 6, 2))
    s.fill((240, 200, 80), (6, 30, 6, 2))
    return s


@cached
def hedge():
    rng = random.Random(9)
    s = pygame.Surface((60, 26), pygame.SRCALPHA)
    pygame.draw.rect(s, (14, 26, 14), (0, 2, 60, 24), border_radius=6)
    for _ in range(60):
        s.fill((24, 40, 22), (rng.randrange(2, 58), rng.randrange(3, 24), 2, 2))
    for _ in range(14):
        s.fill(rng.choice([(200, 20, 40), (240, 60, 70)]), (rng.randrange(3, 56), rng.randrange(4, 22), 2, 2))
    return s


@cached
def mansion_gate():
    s = pygame.Surface((96, 84), pygame.SRCALPHA)
    brick = (70, 22, 20)
    for x in (0, 80):
        s.fill(brick, (x, 10, 16, 74))
        for y in range(12, 84, 6):
            s.fill((50, 14, 14), (x, y, 16, 1))
        s.fill((40, 12, 12), (x - 2, 6, 20, 6))
        pygame.draw.circle(s, (255, 170, 80), (x + 8, 4), 3)
    for x in range(20, 78, 6):
        s.fill((18, 14, 18), (x, 26, 2, 58))
        pygame.draw.polygon(s, (18, 14, 18), [(x - 1, 26), (x + 1, 20), (x + 3, 26)])
    pygame.draw.arc(s, (18, 14, 18), (16, 10, 64, 40), 0, math.pi, 2)
    s.fill((18, 14, 18), (16, 44, 64, 2))
    return s


@cached
def bookshelf(seed=0):
    rng = random.Random(seed + 1000)
    s = pygame.Surface((44, 104), pygame.SRCALPHA)
    s.fill((40, 22, 14), (0, 0, 44, 104))
    s.fill((60, 34, 20), (0, 0, 44, 4))
    for shelf in range(6):
        y = 6 + shelf * 16
        x = 3
        while x < 40:
            bw = rng.randint(2, 5)
            bh = rng.randint(10, 14)
            c = rng.choice([(110, 30, 40), (40, 50, 110), (40, 90, 60), (130, 100, 40), (90, 40, 110), (40, 80, 110)])
            s.fill(scale_color(c, 0.75), (x, y + 14 - bh, bw, bh))
            s.fill(scale_color(c, 1.1), (x, y + 14 - bh, 1, bh))
            x += bw + rng.choice((0, 1))
        s.fill((30, 16, 10), (0, y + 14, 44, 2))
    return s


@cached
def floating_book(color=(110, 30, 40)):
    s = pygame.Surface((18, 12), pygame.SRCALPHA)
    pygame.draw.polygon(s, color, [(0, 2), (9, 4), (18, 2), (18, 10), (9, 12), (0, 10)])
    pygame.draw.polygon(s, (230, 220, 190), [(2, 3), (9, 5), (16, 3), (16, 9), (9, 10), (2, 9)])
    pygame.draw.line(s, (120, 100, 80), (9, 5), (9, 10))
    return s


@cached
def candelabra():
    s = pygame.Surface((20, 44), pygame.SRCALPHA)
    gold = (150, 110, 40)
    s.fill(gold, (9, 10, 2, 34))
    s.fill(gold, (3, 10, 14, 2))
    for x in (3, 9, 15):
        s.fill((230, 220, 200), (x, 4, 2, 6))
        s.fill((255, 180, 60), (x, 0, 2, 4))
    s.fill(gold, (5, 42, 10, 2))
    return s


def gear_frames(radius=30, teeth=12, color=(70, 58, 40), n=16):
    key = ("gear", radius, teeth, color, n)
    if key in _cache:
        return _cache[key]
    size = radius * 2 + 12
    frames = []
    for k in range(n):
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        rot = TAU * k / n / teeth
        pts = []
        for i in range(teeth * 4):
            a = TAU * i / (teeth * 4) + rot
            rr = radius + (5 if (i % 4) in (1, 2) else 0)
            pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
        pygame.draw.polygon(s, color, pts)
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), radius * 0.62)
        pygame.draw.circle(s, color, (c, c), radius * 0.62, 3)
        for j in range(5):
            a = TAU * j / 5 + rot
            pygame.draw.line(s, color, (c, c), (c + math.cos(a) * radius * 0.62, c + math.sin(a) * radius * 0.62), 3)
        pygame.draw.circle(s, scale_color(color, 1.4), (c, c), radius * 0.16)
        frames.append(s)
    _cache[key] = frames
    return frames


@cached
def clock_pillar():
    s = pygame.Surface((28, 120), pygame.SRCALPHA)
    s.fill((36, 34, 54), (4, 10, 20, 110))
    s.fill((50, 48, 72), (4, 10, 3, 110))
    s.fill((26, 24, 40), (0, 0, 28, 12))
    pygame.draw.circle(s, (180, 170, 140), (14, 36), 9)
    pygame.draw.circle(s, (40, 36, 50), (14, 36), 9, 1)
    pygame.draw.line(s, (40, 36, 50), (14, 36), (14, 30))
    pygame.draw.line(s, (40, 36, 50), (14, 36), (18, 38))
    return s


@cached
def spire():
    s = pygame.Surface((44, 150), pygame.SRCALPHA)
    dk = (14, 4, 8)
    s.fill(dk, (10, 50, 24, 100))
    pygame.draw.polygon(s, dk, [(6, 52), (22, 0), (38, 52)])
    for y in range(64, 140, 18):
        s.fill((200, 30, 40), (19, y, 6, 8))
    s.fill(dk, (4, 100, 36, 4))
    return s


@cached
def chain():
    s = pygame.Surface((8, 120), pygame.SRCALPHA)
    for y in range(0, 120, 6):
        if (y // 6) % 2:
            pygame.draw.ellipse(s, (70, 64, 70), (2, y, 4, 7), 1)
        else:
            pygame.draw.ellipse(s, (70, 64, 70), (1, y, 6, 7), 1)
    return s


@cached
def crystal_cluster():
    s = pygame.Surface((30, 36), pygame.SRCALPHA)
    cols = [(255, 80, 80), (255, 200, 60), (90, 220, 120), (80, 160, 255), (190, 90, 255)]
    for i, (x, hgt, lean) in enumerate(((6, 22, -3), (14, 34, 0), (22, 26, 3), (10, 14, -2), (19, 16, 2))):
        c = cols[i % len(cols)]
        pygame.draw.polygon(s, (*c, 220), [(x - 3, 36), (x + lean, 36 - hgt), (x + 3, 36)])
        pygame.draw.line(s, (255, 255, 255, 200), (x, 35), (x + lean, 37 - hgt))
    return s


@cached
def kanji_column(text, size=12, color=(170, 30, 40)):
    """Vertical Japanese text, one glyph per line."""
    glyphs = [assets.text(ch, size, color, None) for ch in text]
    w = max(g.get_width() for g in glyphs)
    h = sum(g.get_height() for g in glyphs)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    y = 0
    for g in glyphs:
        s.blit(g, ((w - g.get_width()) // 2, y))
        y += g.get_height()
    return s


@cached
def big_kanji(ch, size=96, color=(140, 20, 30)):
    return assets.text(ch, size, color, None)


@cached
def black_sun(radius=46, corona=(200, 30, 40)):
    size = radius * 4
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    for i in range(24, 0, -1):
        r = radius + i * radius / 14
        a = int(110 * (1 - i / 24) ** 2)
        pygame.draw.circle(s, (*corona, a), (c, c), int(r))
    pygame.draw.circle(s, (*mix(corona, (255, 230, 200), 0.5), 255), (c, c), radius + 2)
    pygame.draw.circle(s, (4, 0, 4, 255), (c, c), radius)
    return s


@cached
def chandelier():
    s = pygame.Surface((40, 30), pygame.SRCALPHA)
    gold = (150, 110, 40)
    s.fill(gold, (19, 0, 2, 10))
    pygame.draw.ellipse(s, gold, (2, 10, 36, 10), 2)
    for x in (4, 12, 20, 28, 35):
        s.fill((230, 220, 200), (x, 4, 2, 7))
        s.fill((255, 190, 70), (x, 1, 2, 3))
    s.fill(gold, (18, 20, 4, 10))
    return s


@cached
def ofuda():
    s = pygame.Surface((8, 20), pygame.SRCALPHA)
    s.fill((236, 228, 210), (0, 0, 8, 20))
    s.fill((170, 20, 30), (3, 2, 2, 16))
    s.fill((170, 20, 30), (1, 5, 6, 1))
    s.fill((170, 20, 30), (1, 12, 6, 1))
    pygame.draw.circle(s, (170, 20, 30), (4, 8), 2, 1)
    return s


@cached
def mansion_silhouette(color=(12, 2, 6), window=(200, 30, 40)):
    rng = random.Random(3)
    s = pygame.Surface((260, 90), pygame.SRCALPHA)
    s.fill(color, (20, 40, 220, 50))
    s.fill(color, (110, 6, 40, 84))
    pygame.draw.polygon(s, color, [(104, 8), (130, -14), (156, 8)])
    pygame.draw.circle(s, (170, 150, 130), (130, 26), 9)
    pygame.draw.circle(s, color, (130, 26), 9, 2)
    for x0, w in ((26, 30), (200, 30)):
        s.fill(color, (x0, 20, w, 70))
        pygame.draw.polygon(s, color, [(x0 - 4, 22), (x0 + w // 2, 2), (x0 + w + 4, 22)])
    for _ in range(46):
        x, y = rng.randrange(28, 236), rng.randrange(46, 84)
        if rng.random() < 0.6:
            s.fill(window, (x, y, 2, 4))
    return s
