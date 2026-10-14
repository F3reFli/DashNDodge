"""Stage backgrounds: pseudo-3D flythroughs (Touhou style) with a dark,
ritualistic yabujin look - eclipsed suns, torii tunnels, kanji columns,
falling talismans. Everything is a pure function of time, so it never
drifts and can be rendered at any moment."""

import math
import random

import pygame

from . import assets, gfx
from . import textures as tx
from .config import H, MENU_BG, W
from .render3d import Camera, Plane, PropField
from .util import TAU, hsv, scale_color


# ======================================================================
# Shared yabujin overlays
# ======================================================================


class KanjiColumns:
    """Faint vertical lines of Japanese text drifting down the screen."""

    def __init__(self, phrases, color, seed, n=5, alpha=60, size=12):
        rng = random.Random(seed)
        self.cols = []
        xs = [rng.uniform(8, 120) for _ in range(n // 2 + 1)] + [rng.uniform(W - 120, W - 20) for _ in range(n - n // 2 - 1)]
        for i, x in enumerate(xs):
            surf = tx.kanji_column(phrases[i % len(phrases)], size, color).copy()
            surf.set_alpha(alpha)
            self.cols.append((surf, x, rng.uniform(6, 16) * rng.choice((1, -1)), rng.uniform(0, 400)))

    def draw(self, surf, t):
        for img, x, speed, phase in self.cols:
            h = img.get_height()
            y = (phase + t * speed) % (H + h) - h
            surf.blit(img, (int(x), int(y)))


class GiantGlyph:
    """A huge kanji that slowly breathes in and out of the background."""

    def __init__(self, chars, color, period=9.0, alpha=46, size=120):
        self.imgs = [tx.big_kanji(c, size, color) for c in chars]
        self.period = period
        self.alpha = alpha

    def draw(self, surf, t, x=W / 2, y=H / 2):
        n = len(self.imgs)
        k = int(t / self.period) % n
        phase = (t % self.period) / self.period
        a = math.sin(phase * math.pi) ** 2
        if a < 0.02:
            return
        img = self.imgs[k].copy()
        img.set_alpha(int(self.alpha * a))
        jitter = 2 if (int(t * 30) % 47) == 0 else 0
        surf.blit(img, (int(x - img.get_width() / 2 + jitter), int(y - img.get_height() / 2)))


class Talismans:
    """Ofuda paper talismans fluttering down."""

    def __init__(self, seed, n=10, speed=(18, 34)):
        rng = random.Random(seed)
        self.base = tx.ofuda()
        self.items = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(*speed), rng.uniform(0, TAU), rng.uniform(0.6, 1.0))
                      for _ in range(n)]
        self.rot = {}

    def _frame(self, deg, scale):
        key = (int(deg) // 15 * 15, round(scale, 1))
        img = self.rot.get(key)
        if img is None:
            img = pygame.transform.rotozoom(self.base, key[0], key[1])
            img.set_alpha(150)
            self.rot[key] = img
        return img

    def draw(self, surf, t):
        for x, y, sp, ph, sc in self.items:
            yy = (y + t * sp) % (H + 40) - 20
            xx = (x + math.sin(t * 0.9 + ph) * 24 + t * 6) % (W + 20) - 10
            img = self._frame(math.sin(t * 1.7 + ph) * 60, sc)
            surf.blit(img, (int(xx), int(yy)))


def drifting_dots(surf, t, seed, n, color, area=(0, 0, W, H), speed=(5, 15), twinkle=True, size=1):
    rng = random.Random(seed)
    x0, y0, w, h = area
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        vx, vy = rng.uniform(-speed[1], speed[1]), rng.uniform(speed[0], speed[1])
        ph = rng.uniform(0, TAU)
        xx = x0 + (x + vx * t + math.sin(t + ph) * 8) % w
        yy = y0 + (y + vy * t) % h
        k = 0.5 + 0.5 * math.sin(t * 2.3 + ph) if twinkle else 1.0
        surf.fill(scale_color(color, k), (int(xx), int(yy), size, size))


_grade_cache = {}


def grade(surf, color):
    g = _grade_cache.get(color)
    if g is None:
        g = pygame.Surface((W, H))
        g.fill(color)
        _grade_cache[color] = g
    surf.blit(g, (0, 0), special_flags=pygame.BLEND_MULT)


# ======================================================================
# Base classes
# ======================================================================


class Background:
    haze = 0.0  # heat-haze shader distortion (GPU renderer)

    def __init__(self, seed=1):
        self.rng = random.Random(seed)

    def draw(self, surf, t):
        surf.fill((8, 6, 14))

    def light_source(self, t):
        """(x, y, strength, colour) of the sky light that casts god rays, or None."""
        return None

    def lights(self, fx, t):
        """Feed the GPU renderer: god rays, haze and the lights of glowing props."""
        src = self.light_source(t)
        if src is not None:
            fx.godray = src
            x, y, k, col = src
            fx.lights.add(x, y, 150, col, 0.35 * k)
        if self.haze:
            fx.haze = max(fx.haze, self.haze)


class Scene3D(Background):
    horizon = 120
    cam_h = 1.0
    focal = 260.0
    ceiling = None
    speed = 2.4
    sway = 0.35
    fog = (0, 0, 0)
    tint = None

    def __init__(self, seed=1):
        super().__init__(seed)
        self.cam = Camera(self.horizon, self.cam_h, self.focal, self.ceiling)
        self.planes = []
        self.props = PropField(self.cam, 24.0, self.fog, 3.0, 30.0)
        self.build()

    def build(self):
        pass

    def move(self, t):
        cam = self.cam
        cam.scroll = t * self.speed + 3.0
        cam.x = math.sin(t * 0.31) * self.sway
        cam.bob = math.sin(t * 0.83) * 1.2

    def sky(self, surf, t):
        surf.fill(self.fog)

    def world(self, surf, t):
        for p in self.planes:
            p.draw(surf, t)
        self.props.draw(surf, t)

    def fx(self, surf, t):
        pass

    def lights(self, fx, t):
        super().lights(fx, t)
        for field in (self.props,):
            for x, y, r, col, k in field.lit:
                flicker = 0.85 + 0.15 * math.sin(t * 13 + x * 0.1)
                fx.lights.add(x, y, r * 1.7, col, min(1.0, k * flicker * 1.2))

    def draw(self, surf, t):
        self.move(t)
        self.sky(surf, t)
        self.world(surf, t)
        self.fx(surf, t)
        if self.tint:
            grade(surf, self.tint)


# ======================================================================
# Stage 1 - Twilight Path (Rumia): eclipse over a lantern-lit forest path
# ======================================================================


class Twilight(Scene3D):
    horizon = 118
    fog = (46, 10, 32)
    speed = 2.2

    def build(self):
        rng = self.rng
        self.skyg = gfx.vgradient((W, self.horizon + 4), (6, 0, 8), (70, 14, 36))
        self.sun = tx.black_sun(40, (210, 40, 50))
        self.planes.append(Plane(self.cam, tx.forest_floor(), 128, 30, fog=self.fog, fog_start=3))
        P = self.props
        for i in range(18):
            v = i * 24 / 18
            P.add(tx.pine() if rng.random() < 0.7 else tx.dead_tree(), rng.uniform(2.6, 3.6), -rng.uniform(2.0, 4.5), v)
            P.add(tx.pine() if rng.random() < 0.7 else tx.dead_tree(), rng.uniform(2.6, 3.6), rng.uniform(2.0, 4.5), v + 0.6)
        for i in range(8):
            P.add(tx.stone_lantern(), 0.9, -1.15, i * 3 + 1, glow=(255, 160, 70), glow_y=0.36)
            P.add(tx.stone_lantern(), 0.9, 1.15, i * 3 + 1, glow=(255, 160, 70), glow_y=0.36)
        for i in range(4):
            P.add(tx.jizo(), 0.38, rng.choice((-1.5, 1.5)), i * 6 + 2.3)
        P.add(tx.torii(), 2.7, 0.0, 6.0)
        P.add(tx.torii(), 2.7, 0.0, 18.0)
        self.kanji = KanjiColumns(["宵闇", "闇に喰われる", "人間か妖怪か", "宵闇の小道"], (190, 30, 50), 1, alpha=55)
        self.glyph = GiantGlyph("闇夜", (120, 10, 30), 11, 40)
        self.talismans = Talismans(5, 7)
        clouds = pygame.Surface((W * 2, 40), pygame.SRCALPHA)
        for _ in range(26):
            w = rng.randint(60, 180)
            pygame.draw.ellipse(clouds, (8, 0, 8, 170), (rng.uniform(0, W * 2 - w), rng.uniform(0, 26), w, 14))
        self.clouds = clouds

    def sky(self, surf, t):
        surf.blit(self.skyg, (0, 0))
        hz = self.cam.hz
        surf.blit(self.sun, (W / 2 - self.sun.get_width() / 2 + self.cam.x * -20, hz - self.sun.get_height() / 2 - 26))
        ox = -(t * 10) % (W * 2)
        for dx in (ox - W * 2, ox):
            surf.blit(self.clouds, (dx, hz - 70))
        self.glyph.draw(surf, t, W / 2, 56)

    def light_source(self, t):
        return (W / 2 + self.cam.x * -20, self.cam.hz - 26, 0.75, (255, 90, 80))

    def fx(self, surf, t):
        drifting_dots(surf, t, 11, 26, (200, 255, 120), (0, 140, W, H - 140), (-6, 6))
        drifting_dots(surf, t, 12, 30, (200, 50, 40), (0, 0, W, H), (14, 30), twinkle=False, size=2)
        self.talismans.draw(surf, t)
        self.kanji.draw(surf, t)


# ======================================================================
# Stage 2 - The Misty Lake (Cirno): rippling water, ice, a distant mansion
# ======================================================================


class Lake(Scene3D):
    horizon = 128
    fog = (34, 52, 86)
    speed = 2.6

    def build(self):
        rng = self.rng
        self.skyg = gfx.vgradient((W, self.horizon + 4), (2, 4, 14), (40, 56, 92))
        for _ in range(90):
            c = rng.randint(80, 200)
            self.skyg.set_at((rng.randrange(W), rng.randrange(self.horizon - 20)), (c, c, min(255, c + 40)))
        self.mansion = tx.mansion_silhouette((10, 12, 26), (220, 40, 50))
        self.planes.append(Plane(self.cam, tx.lake_water(), 96, 30, fog=self.fog, fog_start=2.5, wobble=0.07))
        P = self.props
        for i in range(14):
            v = i * 24 / 14
            P.add(tx.reeds(), rng.uniform(0.5, 0.8), -rng.uniform(1.6, 3.5), v)
            P.add(tx.reeds(), rng.uniform(0.5, 0.8), rng.uniform(1.6, 3.5), v + 0.9)
        for i in range(9):
            P.add(tx.ice_shard(), rng.uniform(0.6, 1.6), rng.choice((-1, 1)) * rng.uniform(1.0, 4.0), rng.uniform(0, 24))
        mist = pygame.Surface((W * 2, 70), pygame.SRCALPHA)
        for _ in range(40):
            w = rng.randint(80, 260)
            pygame.draw.ellipse(mist, (190, 210, 255, 16), (rng.uniform(0, W * 2 - w), rng.uniform(0, 50), w, 22))
        self.mist = mist
        self.kanji = KanjiColumns(["霧の湖", "凍てつく水面", "最強の妖精"], (150, 210, 255), 2, alpha=50)
        self.glyph = GiantGlyph("氷霧", (60, 110, 170), 10, 36)

    def sky(self, surf, t):
        surf.blit(self.skyg, (0, 0))
        hz = self.cam.hz
        pygame.draw.circle(surf, (190, 210, 240), (470, int(hz) - 76), 18)
        pygame.draw.circle(surf, (40, 56, 92), (476, int(hz) - 80), 16)
        surf.blit(self.mansion, (140 - self.cam.x * 30, hz - 86))
        self.glyph.draw(surf, t, 470, 60)

    def light_source(self, t):
        return (470, self.cam.hz - 76, 0.7, (170, 205, 255))

    def fx(self, surf, t):
        hz = self.cam.hz
        for y, sp in ((hz - 30, 9), (hz + 10, -14), (hz + 60, 20), (hz + 150, -26)):
            ox = -(t * sp) % (W * 2)
            for dx in (ox - W * 2, ox):
                surf.blit(self.mist, (dx, y))
        drifting_dots(surf, t, 21, 40, (220, 240, 255), (0, 0, W, H), (10, 26))
        self.kanji.draw(surf, t)


# ======================================================================
# Stage 3 - The Scarlet Gate (Meiling): blood sky, rose garden, the gate
# ======================================================================


class Gate(Scene3D):
    horizon = 124
    fog = (60, 8, 14)
    speed = 2.4

    def build(self):
        rng = self.rng
        self.skyg = gfx.vgradient((W, self.horizon + 4), (12, 0, 4), (110, 16, 24))
        self.mansion = pygame.transform.scale_by(tx.mansion_silhouette((10, 0, 4), (255, 60, 60)), 1.4)
        self.planes.append(Plane(self.cam, tx.garden_floor(), 128, 30, fog=self.fog, fog_start=3))
        P = self.props
        for i in range(12):
            v = i * 2
            P.add(tx.hedge(), 0.55, -1.6, v)
            P.add(tx.hedge(), 0.55, 1.6, v)
        for i in range(8):
            P.add(tx.red_lantern_post(), 1.1, -1.05, i * 3 + 1.5)
            P.add(tx.red_lantern_post(), 1.1, 1.05, i * 3 + 1.5)
        for i in range(10):
            P.add(tx.dead_tree((20, 2, 8)), rng.uniform(2.6, 3.4), rng.choice((-1, 1)) * rng.uniform(2.6, 4.8), rng.uniform(0, 24))
        P.add(tx.mansion_gate(), 2.6, 0.0, 12.0)
        self.kanji = KanjiColumns(["紅魔館", "門番は眠らない", "紅い霧"], (230, 60, 60), 3, alpha=60)
        self.glyph = GiantGlyph("紅門", (130, 10, 20), 10, 44)
        self.talismans = Talismans(7, 6)

    def sky(self, surf, t):
        surf.blit(self.skyg, (0, 0))
        hz = self.cam.hz
        gfx.blit_glow(surf, 120, int(hz) - 70, 60, (90, 10, 10), 1.0)
        pygame.draw.circle(surf, (200, 30, 36), (120, int(hz) - 70), 26)
        pygame.draw.circle(surf, (230, 60, 60), (120, int(hz) - 70), 22)
        surf.blit(self.mansion, (W / 2 - self.mansion.get_width() / 2 - self.cam.x * 25, hz - self.mansion.get_height() + 4))
        self.glyph.draw(surf, t, 520, 60)

    def light_source(self, t):
        return (120, self.cam.hz - 70, 0.8, (255, 90, 70))

    def fx(self, surf, t):
        drifting_dots(surf, t, 31, 40, (220, 40, 60), (0, 0, W, H), (16, 34), twinkle=False, size=2)
        self.talismans.draw(surf, t)
        self.kanji.draw(surf, t)


# ======================================================================
# Stage 4 - Voile, the Magic Library (Patchouli): an endless shelf corridor
# ======================================================================


class Library(Scene3D):
    horizon = 150
    ceiling = 3.0
    fog = (18, 8, 24)
    speed = 1.8
    sway = 0.25

    def build(self):
        rng = self.rng
        self.planes.append(Plane(self.cam, tx.library_ceiling(), 96, 26, ceiling=True, fog=self.fog, fog_start=2.5))
        self.planes.append(Plane(self.cam, tx.library_floor(), 128, 26, fog=self.fog, fog_start=2.5))
        self.props = PropField(self.cam, 24.0, self.fog, 2.5, 26.0)
        P = self.props
        for i in range(24):
            v = i
            for side in (-1, 1):
                P.add(tx.bookshelf(i % 6), 2.6, side * 1.75, v)
                P.add(tx.bookshelf((i + 3) % 6), 2.6, side * 2.4, v + 0.5)
        for i in range(8):
            P.add(tx.candelabra(), 0.7, -1.2, i * 3 + 0.5)
            P.add(tx.candelabra(), 0.7, 1.2, i * 3 + 0.5)
            P.add(tx.chandelier(), 0.45, 0.0, i * 3 + 2, hang=True, lift=0.2)
        cols = [(110, 30, 40), (40, 50, 110), (40, 90, 60), (130, 100, 40)]
        for i in range(14):
            P.add(tx.floating_book(rng.choice(cols)), 0.22, rng.uniform(-1.0, 1.0), rng.uniform(0, 24),
                  lift=rng.uniform(0.7, 2.0), bob=0.15, phase=rng.uniform(0, 6))
        self.kanji = KanjiColumns(["知識と日陰", "七曜の魔法", "静粛に", "火水木金土日月"], (190, 150, 255), 4, alpha=55)
        self.glyph = GiantGlyph("火水木金土", (90, 50, 140), 7, 40)

    def sky(self, surf, t):
        surf.fill(self.fog)

    def fx(self, surf, t):
        hz = self.cam.hz
        self.glyph.draw(surf, t, W / 2, hz - 10)
        drifting_dots(surf, t, 41, 50, (230, 210, 160), (0, 0, W, H), (-4, 6))
        self.kanji.draw(surf, t)


# ======================================================================
# Stage 5 - The Clock Tower (Sakuya): gears, pillars and a giant clock
# ======================================================================


class ClockTower(Scene3D):
    horizon = 136
    fog = (22, 20, 46)
    speed = 2.0

    def build(self):
        rng = self.rng
        self.skyg = gfx.vgradient((W, self.horizon + 4), (6, 4, 16), (40, 36, 72))
        self.planes.append(Plane(self.cam, tx.clock_floor(), 128, 30, fog=self.fog, fog_start=3))
        P = self.props
        for i in range(10):
            v = i * 2.4
            P.add(tx.clock_pillar(), 2.8, -1.7, v)
            P.add(tx.clock_pillar(), 2.8, 1.7, v + 1.2)
        for i in range(12):
            side = rng.choice((-1, 1))
            frames = tx.gear_frames(rng.choice((22, 30, 38)), rng.choice((10, 12, 14)), (70, 58, 40))
            P.add(frames, rng.uniform(0.9, 1.8), side * rng.uniform(2.2, 3.6), rng.uniform(0, 24),
                  lift=rng.uniform(0.4, 2.2), fps=rng.choice((-6, 6, 9)), phase=rng.uniform(0, 16))
        face = pygame.Surface((240, 240), pygame.SRCALPHA)
        pygame.draw.circle(face, (36, 32, 60), (120, 120), 118)
        pygame.draw.circle(face, (70, 64, 110), (120, 120), 118, 3)
        pygame.draw.circle(face, (70, 64, 110), (120, 120), 100, 1)
        for i, num in enumerate(["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]):
            a = TAU * i / 12
            img = assets.text(num, 12, (100, 92, 150), None)
            face.blit(img, (120 + math.sin(a) * 104 - img.get_width() / 2, 120 - math.cos(a) * 104 - img.get_height() / 2))
        self.face = face
        self.kanji = KanjiColumns(["時よ止まれ", "完全で瀟洒", "銀のナイフ"], (170, 180, 255), 5, alpha=55)
        self.glyph = GiantGlyph("時", (60, 60, 120), 8, 40)

    def sky(self, surf, t):
        surf.blit(self.skyg, (0, 0))
        hz = self.cam.hz
        cx, cy = W / 2 - self.cam.x * 20, hz - 20
        surf.blit(self.face, (cx - 120, cy - 120))
        for length, angle, width in ((60, t / 120 * TAU, 4), (90, t / 10 * TAU, 3), (100, int(t) * TAU / 60, 1)):
            pygame.draw.line(surf, (110, 100, 170), (cx, cy), (cx + math.sin(angle) * length, cy - math.cos(angle) * length), width)
        self.glyph.draw(surf, t, 90, 70)

    def light_source(self, t):
        return (W / 2 - self.cam.x * 20, self.cam.hz - 20, 0.45, (160, 160, 255))

    def fx(self, surf, t):
        drifting_dots(surf, t, 51, 30, (200, 200, 255), (0, 0, W, H), (6, 14))
        self.kanji.draw(surf, t)
        # every ~8 s the world stutters into a frozen monochrome instant
        if (t % 8.0) < 0.12:
            surf.blit(pygame.transform.grayscale(surf), (0, 0))


# ======================================================================
# Stage 6 - Under the Scarlet Moon (Remilia): above a sea of red clouds
# ======================================================================


class ScarletMoon(Scene3D):
    horizon = 150
    cam_h = 1.6
    fog = (50, 6, 14)
    speed = 3.2

    def build(self):
        rng = self.rng
        self.skyg = gfx.vgradient((W, self.horizon + 4), (8, 0, 4), (110, 14, 30))
        moon = pygame.Surface((300, 300), pygame.SRCALPHA)
        for i in range(30, 0, -1):
            pygame.draw.circle(moon, (160, 14, 24, int(70 * (1 - i / 30) ** 2)), (150, 150), 96 + i * 2)
        pygame.draw.circle(moon, (100, 10, 20), (150, 150), 96)
        pygame.draw.circle(moon, (128, 18, 30), (150, 150), 90)
        for _ in range(16):
            a, r = rng.uniform(0, TAU), rng.uniform(0, 80)
            pygame.draw.circle(moon, (108, 12, 24), (int(150 + math.cos(a) * r), int(150 + math.sin(a) * r)), rng.randint(4, 12))
        self.moon = moon
        self.planes.append(Plane(self.cam, tx.cloud_sea(), 80, 34, fog=self.fog, fog_start=3, wobble=0.04))
        self.props = PropField(self.cam, 24.0, self.fog, 3.0, 32.0)
        for i in range(12):
            self.props.add(tx.spire(), rng.uniform(3.0, 5.0), rng.choice((-1, 1)) * rng.uniform(2.2, 6.0), rng.uniform(0, 24), lift=-0.4)
        self.kanji = KanjiColumns(["紅い月", "運命を操る", "永遠に幼き月"], (255, 70, 80), 6, alpha=65)
        self.glyph = GiantGlyph("紅月", (110, 0, 14), 9, 46)
        self.talismans = Talismans(9, 5)

    def sky(self, surf, t):
        surf.blit(self.skyg, (0, 0))
        hz = self.cam.hz
        surf.blit(self.moon, (W / 2 - 150 - self.cam.x * 15, hz - 200))
        self.glyph.draw(surf, t, W / 2, 70)
        for k in range(9):
            r = random.Random(k)
            bx = (r.uniform(0, W) + t * r.uniform(30, 60)) % (W + 40) - 20
            by = r.uniform(30, hz - 20) + math.sin(t * 3 + k) * 6
            flap = 3 if int(t * 10 + k) % 2 else -1
            col = (10, 0, 4)
            pygame.draw.polygon(surf, col, [(bx, by), (bx - 7, by - flap), (bx - 3, by + 1)])
            pygame.draw.polygon(surf, col, [(bx, by), (bx + 7, by - flap), (bx + 3, by + 1)])

    def light_source(self, t):
        return (W / 2 - self.cam.x * 15, self.cam.hz - 50, 1.0, (255, 70, 80))

    def fx(self, surf, t):
        self.talismans.draw(surf, t)
        self.kanji.draw(surf, t)
        surf.blit(gfx.vignette((W, H), 150), (0, 0))


# ======================================================================
# Extra - The Forbidden Basement (Flandre): chains, crystals, glitches
# ======================================================================


class Basement(Scene3D):
    haze = 0.55
    horizon = 160
    ceiling = 2.4
    fog = (26, 4, 16)
    speed = 1.6
    sway = 0.5

    def build(self):
        rng = self.rng
        dark = tx.stone_floor().copy()
        dark.fill((120, 110, 120), special_flags=pygame.BLEND_MULT)
        self.planes.append(Plane(self.cam, dark, 110, 22, ceiling=True, fog=self.fog, fog_start=2))
        self.planes.append(Plane(self.cam, tx.sigil_floor(), 110, 22, fog=self.fog, fog_start=2))
        self.props = PropField(self.cam, 24.0, self.fog, 2.0, 22.0)
        P = self.props
        for i in range(12):
            P.add(tx.stone_pillar(), 2.4, -1.9, i * 2)
            P.add(tx.stone_pillar(), 2.4, 1.9, i * 2 + 1)
        for _ in range(22):
            P.add(tx.chain(), rng.uniform(0.8, 1.6), rng.uniform(-3, 3), rng.uniform(0, 24), hang=True)
        for _ in range(7):
            P.add(tx.cage(), 0.7, rng.uniform(-1.6, 1.6), rng.uniform(0, 24), hang=True, lift=0.6, bob=0.05, phase=rng.uniform(0, 6))
        for _ in range(18):
            P.add(tx.crystal_cluster(), rng.uniform(0.5, 1.0), rng.choice((-1, 1)) * rng.uniform(0.9, 2.8), rng.uniform(0, 24),
                  glow=hsv(rng.random(), 0.6, 1.0), glow_y=0.55)
        self.kanji = KanjiColumns(["禁忌", "四百九十五年", "壊れた玩具", "ありとあらゆるものを破壊する"], (255, 90, 90), 7, alpha=60)
        self.glyph = GiantGlyph("禁壊", (120, 0, 20), 7, 50)

    def fx(self, surf, t):
        hz = self.cam.hz
        self.glyph.draw(surf, t, W / 2, hz - 30)
        for k in range(14):
            r = random.Random(k * 7)
            a = 0.5 + 0.5 * math.sin(t * r.uniform(1, 3) + k)
            if a > 0.7:
                c = scale_color(hsv(r.random(), 0.7, 1.0), a)
                x, y = r.uniform(0, W), r.uniform(0, H)
                pygame.draw.polygon(surf, c, [(x, y - 4), (x + 2, y), (x, y + 4), (x - 2, y)])
        self.kanji.draw(surf, t)
        # background-only glitch tears
        if int(t * 10) % 37 < 2:
            r = random.Random(int(t * 30))
            for _ in range(4):
                y = r.randrange(0, H - 12)
                h = r.randint(2, 10)
                band = surf.subsurface((0, y, W, h)).copy()
                surf.blit(band, (r.randint(-24, 24), y))


# ======================================================================
# Endless / Title - Senbon torii: an infinite tunnel of shrine gates
# ======================================================================


class Torii(Scene3D):
    horizon = 126
    fog = (26, 2, 12)
    speed = 2.2
    sway = 0.15
    moon_color = (200, 30, 40)
    sky_colors = ((2, 0, 4), (60, 8, 20))
    gate_shade = (1.0, 0.85)
    kanji_color = (200, 30, 50)
    lantern_light = (255, 150, 70)
    phrases = ["千本鳥居", "終わらない夜", "幻想郷", "避ける"]
    glyphs = "鳥居夢"

    def build(self):
        rng = self.rng
        self.skyg = gfx.vgradient((W, self.horizon + 4), *self.sky_colors)
        for _ in range(60):
            c = rng.randint(60, 160)
            self.skyg.set_at((rng.randrange(W), rng.randrange(self.horizon - 30)), (c, c - 20, c - 10))
        self.sun = tx.black_sun(34, self.moon_color)
        self.planes.append(Plane(self.cam, tx.shrine_path(), 128, 30, fog=self.fog, fog_start=2.5))
        self.props = PropField(self.cam, 24.0, self.fog, 2.5, 30.0)
        P = self.props
        for i in range(20):
            P.add(tx.torii(self.gate_shade[i % 2]), 2.4, 0.0, i * 1.2)
        for i in range(12):
            P.add(tx.stone_lantern(), 0.8, -1.5, i * 2 + 0.6, glow=self.lantern_light, glow_y=0.36)
            P.add(tx.stone_lantern(), 0.8, 1.5, i * 2 + 0.6, glow=self.lantern_light, glow_y=0.36)
        for _ in range(16):
            P.add(tx.pine((6, 2, 6), (50, 10, 20)), rng.uniform(3, 4), rng.choice((-1, 1)) * rng.uniform(2.6, 5), rng.uniform(0, 24))
        self.kanji = KanjiColumns(self.phrases, self.kanji_color, 8, n=6, alpha=60)
        self.glyph = GiantGlyph(self.glyphs, (110, 0, 20), 9, 44)
        self.talismans = Talismans(13, 9)

    def sky(self, surf, t):
        surf.blit(self.skyg, (0, 0))
        hz = self.cam.hz
        surf.blit(self.sun, (W / 2 - self.sun.get_width() / 2, hz - self.sun.get_height() / 2 - 30))
        self.glyph.draw(surf, t, W / 2, 50)

    def light_source(self, t):
        return (W / 2, self.cam.hz - 30, 0.85, self.moon_color)

    def fx(self, surf, t):
        self.talismans.draw(surf, t)
        self.kanji.draw(surf, t)
        drifting_dots(surf, t, 81, 24, (255, 120, 120), (0, 0, W, H), (6, 18))


class Night(Torii):
    """Endless: the same infinite gates, under a violet night."""

    fog = (18, 8, 40)
    moon_color = (150, 90, 255)
    speed = 2.8
    sky_colors = ((2, 0, 10), (40, 18, 80))
    gate_shade = (0.75, 0.6)
    kanji_color = (150, 110, 255)
    lantern_light = (170, 120, 255)
    phrases = ["終わらない夜", "千本鳥居", "幻想郷の夜", "まだ避けるか"]
    glyphs = "夜終"
    tint = (200, 190, 255)


class Title(Torii):
    speed = 1.2


class Photo(Background):
    """The original game's menu picture."""

    def __init__(self):
        super().__init__(99)
        img = assets.image(MENU_BG, alpha=False)
        iw, ih = img.get_size()
        k = max(W / iw, H / ih) * 1.12
        self.img = pygame.transform.smoothscale(img, (int(iw * k), int(ih * k)))
        shade = pygame.Surface(self.img.get_size())
        shade.fill((150, 120, 150))
        self.img.blit(shade, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw(self, surf, t):
        ox = (self.img.get_width() - W) / 2 + math.sin(t * 0.15) * (self.img.get_width() - W) / 2.2
        oy = (self.img.get_height() - H) / 2 + math.cos(t * 0.11) * (self.img.get_height() - H) / 2.2
        surf.blit(self.img, (-ox, -oy))


BACKGROUNDS = {
    "twilight": Twilight,
    "lake": Lake,
    "gate": Gate,
    "library": Library,
    "clock": ClockTower,
    "moon": ScarletMoon,
    "basement": Basement,
    "night": Night,
    "title": Title,
    "photo": Photo,
}

_instances = {}


def get(name):
    bg = _instances.get(name)
    if bg is None:
        bg = BACKGROUNDS[name]()
        _instances[name] = bg
    return bg
