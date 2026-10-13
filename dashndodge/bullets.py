"""Danmaku bullets: procedural sprites, movement, collision and rendering."""

import math

import pygame

from .config import H, PALETTE, W
from .util import TAU

SS = 4  # supersampling factor for bullet art
ANGLES = 64

# kind: (width, height, hit radius, oriented, capsule half-length)
KINDS = {
    "pellet": (7, 7, 2.0, False, 0),
    "orb": (11, 11, 3.5, False, 0),
    "big": (22, 22, 7.5, False, 0),
    "bubble": (30, 30, 11.0, False, 0),
    "rice": (12, 6, 2.3, True, 2.5),
    "knife": (17, 6, 2.2, True, 4.5),
    "amulet": (11, 8, 3.0, True, 1.5),
    "ice": (14, 6, 2.3, True, 3.5),
    "arrow": (10, 8, 2.6, True, 1.0),
    "star": (13, 13, 3.6, True, 0),
    "heart": (12, 12, 4.0, False, 0),
    "butterfly": (15, 15, 3.6, True, 0),
    "spear": (70, 14, 5.0, True, 26.0),
    "note": (10, 12, 3.0, False, 0),
}

_cache = {}


def _surf(w, h):
    return pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)


def _draw_kind(kind, rim, core):
    w, h = KINDS[kind][0], KINDS[kind][1]
    s = _surf(w, h)
    cx, cy = w * SS / 2, h * SS / 2
    R = min(w, h) * SS / 2
    if kind in ("pellet", "orb", "big"):
        pygame.draw.circle(s, (*rim, 60), (cx, cy), R)
        pygame.draw.circle(s, (*rim, 255), (cx, cy), R * 0.78)
        pygame.draw.circle(s, (*core, 255), (cx, cy), R * 0.48)
    elif kind == "bubble":
        pygame.draw.circle(s, (*rim, 70), (cx, cy), R)
        pygame.draw.circle(s, (*rim, 230), (cx, cy), R, SS * 2)
        pygame.draw.circle(s, (*core, 120), (cx, cy), R * 0.55)
        pygame.draw.ellipse(s, (255, 255, 255, 200), (cx - R * 0.6, cy - R * 0.7, R * 0.6, R * 0.35))
    elif kind == "rice":
        pygame.draw.ellipse(s, (*rim, 255), (0, 0, w * SS, h * SS))
        pygame.draw.ellipse(s, (*core, 255), (SS * 2.5, SS * 1.6, (w - 5) * SS, (h - 3.2) * SS))
    elif kind == "knife":
        pygame.draw.rect(s, (*rim, 255), (0, SS * 1.5, SS * 5, SS * 3))
        blade = [(w * SS, cy), (SS * 5, SS * 0.4), (SS * 5, h * SS - SS * 0.4)]
        pygame.draw.polygon(s, (*rim, 255), blade)
        inner = [(w * SS - SS * 2.2, cy), (SS * 6, SS * 1.6), (SS * 6, h * SS - SS * 1.6)]
        pygame.draw.polygon(s, (235, 240, 255, 255), inner)
    elif kind == "amulet":
        pygame.draw.rect(s, (*rim, 255), (0, 0, w * SS, h * SS), border_radius=SS)
        pygame.draw.rect(s, (*core, 255), (SS * 1.2, SS * 1.2, (w - 2.4) * SS, (h - 2.4) * SS))
        pygame.draw.rect(s, (*rim, 255), (cx - SS * 1.5, cy - SS * 1.5, SS * 3, SS * 3))
    elif kind == "ice":
        pts = [(0, cy), (w * SS * 0.45, 0), (w * SS, cy), (w * SS * 0.45, h * SS)]
        pygame.draw.polygon(s, (*rim, 255), pts)
        pts2 = [(SS * 2, cy), (w * SS * 0.45, SS * 1.5), (w * SS - SS * 2, cy), (w * SS * 0.45, h * SS - SS * 1.5)]
        pygame.draw.polygon(s, (*core, 255), pts2)
    elif kind == "arrow":
        pts = [(w * SS, cy), (0, 0), (SS * 3, cy), (0, h * SS)]
        pygame.draw.polygon(s, (*rim, 255), pts)
        pts2 = [(w * SS - SS * 2.5, cy), (SS * 2.5, SS * 1.8), (SS * 4, cy), (SS * 2.5, h * SS - SS * 1.8)]
        pygame.draw.polygon(s, (*core, 255), pts2)
    elif kind == "star":
        pts, pts2 = [], []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = R if i % 2 == 0 else R * 0.45
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
            r2 = R * 0.55 if i % 2 == 0 else R * 0.25
            pts2.append((cx + math.cos(a) * r2, cy + math.sin(a) * r2))
        pygame.draw.polygon(s, (*rim, 255), pts)
        pygame.draw.polygon(s, (*core, 255), pts2)
    elif kind == "heart":
        r = R * 0.5
        pygame.draw.circle(s, (*rim, 255), (cx - r * 0.85, cy - r * 0.4), r)
        pygame.draw.circle(s, (*rim, 255), (cx + r * 0.85, cy - r * 0.4), r)
        pygame.draw.polygon(s, (*rim, 255), [(cx - R * 0.92, cy - r * 0.1), (cx + R * 0.92, cy - r * 0.1), (cx, cy + R * 0.95)])
        pygame.draw.circle(s, (*core, 255), (cx - r * 0.7, cy - r * 0.5), r * 0.45)
    elif kind == "butterfly":
        for sy in (-1, 1):
            pygame.draw.ellipse(s, (*rim, 230), (cx - R * 0.9, cy + sy * R * 0.5 - R * 0.45, R * 1.1, R * 0.9))
            pygame.draw.ellipse(s, (*rim, 200), (cx - R * 0.05, cy + sy * R * 0.42 - R * 0.35, R * 0.9, R * 0.7))
        pygame.draw.line(s, (*core, 255), (cx - R * 0.6, cy), (cx + R * 0.8, cy), SS * 2)
    elif kind == "spear":
        pts = [(w * SS, cy), (w * SS * 0.25, 0), (0, cy), (w * SS * 0.25, h * SS)]
        pygame.draw.polygon(s, (*rim, 140), pts)
        pts2 = [(w * SS - SS * 3, cy), (w * SS * 0.28, SS * 3), (SS * 6, cy), (w * SS * 0.28, h * SS - SS * 3)]
        pygame.draw.polygon(s, (*rim, 255), pts2)
        pygame.draw.line(s, (*core, 255), (SS * 10, cy), (w * SS - SS * 6, cy), SS * 2)
    elif kind == "note":
        pygame.draw.ellipse(s, (*rim, 255), (0, h * SS * 0.55, w * SS * 0.7, h * SS * 0.45))
        pygame.draw.rect(s, (*rim, 255), (w * SS * 0.55, 0, SS * 2, h * SS * 0.8))
        pygame.draw.rect(s, (*rim, 255), (w * SS * 0.55, 0, w * SS * 0.45, SS * 2.5))
        pygame.draw.ellipse(s, (*core, 255), (SS * 2, h * SS * 0.65, w * SS * 0.35, h * SS * 0.2))
    return s


def sprite(kind, color, idx=0):
    key = (kind, color, idx)
    surf = _cache.get(key)
    if surf is not None:
        return surf
    base_key = (kind, color, "base")
    base = _cache.get(base_key)
    if base is None:
        rim, core = PALETTE.get(color, PALETTE["white"])
        base = _draw_kind(kind, rim, core)
        _cache[base_key] = base
    img = base
    if KINDS[kind][3] and idx:
        img = pygame.transform.rotate(base, -idx * 360.0 / ANGLES)
    surf = pygame.transform.smoothscale(img, (max(1, img.get_width() // SS), max(1, img.get_height() // SS)))
    _cache[key] = surf
    return surf


_spawn_cache = {}


def spawn_sprite(color, step):
    key = (color, step)
    surf = _spawn_cache.get(key)
    if surf is None:
        rim = PALETTE.get(color, PALETTE["white"])[0]
        r = 4 + step * 3
        surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*rim, 110 - step * 15), (r + 1, r + 1), r)
        pygame.draw.circle(surf, (255, 255, 255, 160), (r + 1, r + 1), max(1, r // 2))
        _spawn_cache[key] = surf
    return surf


class Bullet:
    __slots__ = (
        "x", "y", "speed", "angle", "vx", "vy", "cos", "sin", "accel", "turn", "min_speed", "max_speed",
        "kind", "color", "r", "half_len", "reach", "oriented", "spin", "age", "grace", "fn", "data",
        "dead", "grazed", "friendly", "damage", "frozen", "wrapped", "spr", "spr_idx", "pierce", "hits",
        "home", "invisible",
    )

    def __init__(self, x, y, speed, angle, kind, color, accel=0.0, turn=0.0, min_speed=0.0, max_speed=1e9,
                 fn=None, data=None, friendly=False, damage=1.0, spin=0.0, grace=30, pierce=False):
        self.x, self.y = float(x), float(y)
        self.kind, self.color = kind, color
        size = KINDS[kind]
        self.r = size[2]
        self.oriented = size[3]
        self.half_len = size[4]
        self.reach = self.r + self.half_len
        self.accel, self.turn = accel, turn
        self.min_speed, self.max_speed = min_speed, max_speed
        self.fn, self.data = fn, data
        self.friendly, self.damage = friendly, damage
        self.spin = spin if spin else (4.0 if kind == "star" else 0.0)
        self.age = 0
        self.grace = grace
        self.dead = self.grazed = self.frozen = self.wrapped = False
        self.pierce = pierce
        self.hits = None
        self.home = 0.0
        self.invisible = False
        self.spr = None
        self.spr_idx = -1
        self.speed = speed
        self.angle = angle
        self._dir()

    def _dir(self):
        self.cos = math.cos(self.angle)
        self.sin = math.sin(self.angle)
        self.vx = self.cos * self.speed
        self.vy = self.sin * self.speed

    def set_speed(self, s):
        self.speed = s
        self.vx = self.cos * s
        self.vy = self.sin * s

    def set_angle(self, a):
        self.angle = a
        self._dir()

    def aim(self, x, y):
        self.set_angle(math.atan2(y - self.y, x - self.x))

    def sprite(self):
        if self.oriented:
            a = self.angle if not self.spin else self.age * self.spin / 60.0
            idx = int(round(a * ANGLES / TAU)) % ANGLES
        else:
            idx = 0
        if idx != self.spr_idx:
            self.spr_idx = idx
            self.spr = sprite(self.kind, self.color, idx)
        return self.spr


class Laser:
    """A straight beam: a flickering warning line, then a deadly ray.

    Phases (frames): warn -> grow -> active -> fade. Lasers can rotate and
    follow an owner (e.g. a boss). They can't be parried, only dodged,
    dashed through or bombed."""

    __slots__ = ("x", "y", "angle", "length", "width", "warn", "grow", "active", "fade", "color", "turn",
                 "owner", "t", "dead", "graze_cd", "cos", "sin")

    def __init__(self, x, y, angle, length=760, width=12, warn=45, active=70, color="red", turn=0.0, owner=None,
                 grow=8, fade=12):
        self.x, self.y = x, y
        self.angle = angle
        self.length = length
        self.width = width
        self.warn, self.grow, self.active, self.fade = warn, grow, active, fade
        self.color = color
        self.turn = turn
        self.owner = owner
        self.t = 0
        self.dead = False
        self.graze_cd = 0
        self.cos = math.cos(angle)
        self.sin = math.sin(angle)

    @property
    def total(self):
        return self.warn + self.grow + self.active + self.fade

    def current_width(self):
        t = self.t - self.warn
        if t < 0:
            return 0.0
        if t < self.grow:
            return self.width * t / self.grow
        t -= self.grow
        if t < self.active:
            return self.width
        t -= self.active
        return self.width * max(0.0, 1 - t / self.fade)

    def lethal(self):
        return self.current_width() > self.width * 0.5

    def update(self, dt):
        if self.owner is not None and getattr(self.owner, "alive", False):
            self.x, self.y = self.owner.x, self.owner.y
        if self.turn:
            self.angle += self.turn * dt
            self.cos = math.cos(self.angle)
            self.sin = math.sin(self.angle)
        self.t += 1
        if self.graze_cd > 0:
            self.graze_cd -= 1
        if self.t >= self.total:
            self.dead = True

    def cancel(self):
        """Skip straight to fading out."""
        done = self.warn + self.grow + self.active
        if self.t < done:
            self.t = max(self.t, done) if self.t >= self.warn else self.total

    def distance(self, px, py):
        dx, dy = px - self.x, py - self.y
        along = dx * self.cos + dy * self.sin
        if along < 0:
            return math.hypot(dx, dy), along
        if along > self.length:
            along = self.length
        perp = abs(-dx * self.sin + dy * self.cos)
        return perp, along

    def draw(self, add):
        rim, core = PALETTE.get(self.color, PALETTE["white"])
        ex, ey = self.x + self.cos * self.length, self.y + self.sin * self.length
        if self.t < self.warn:
            k = 0.35 + 0.65 * (1 if (self.t // 3) % 2 else 0.3)
            pygame.draw.line(add, tuple(int(c * k * 0.8) for c in rim), (self.x, self.y), (ex, ey), 1)
            return
        w = self.current_width()
        if w <= 0.3:
            return
        nx, ny = -self.sin, self.cos
        for k, col in ((1.0, tuple(c // 3 for c in rim)), (0.7, rim), (0.32, core)):
            hw = max(0.5, w / 2 * k)
            pts = [(self.x + nx * hw, self.y + ny * hw), (ex + nx * hw, ey + ny * hw),
                   (ex - nx * hw, ey - ny * hw), (self.x - nx * hw, self.y - ny * hw)]
            pygame.draw.polygon(add, col, pts)
        r = int(w * 0.45)
        if r > 1:
            pygame.draw.circle(add, core, (int(self.x), int(self.y)), r)


class GrazePoint:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y


class Bullets:
    def __init__(self, game):
        self.game = game
        self.items = []
        self.friendly = []
        self.lasers = []

    def laser(self, x, y, angle, **kw):
        lz = Laser(x, y, angle, **kw)
        self.lasers.append(lz)
        return lz

    def shoot(self, x, y, speed, angle, kind="orb", color="red", **kw):
        b = Bullet(x, y, speed, angle, kind, color, **kw)
        (self.friendly if b.friendly else self.items).append(b)
        return b

    def ring(self, x, y, n, speed, angle=0.0, kind="orb", color="red", **kw):
        return [self.shoot(x, y, speed, angle + TAU * i / n, kind, color, **kw) for i in range(n)]

    def fan(self, x, y, n, speed, angle, spread, kind="orb", color="red", **kw):
        if n == 1:
            return [self.shoot(x, y, speed, angle, kind, color, **kw)]
        return [self.shoot(x, y, speed, angle - spread / 2 + spread * i / (n - 1), kind, color, **kw) for i in range(n)]

    def update(self, dt, timestop=False, slow=1.0, wrap=False):
        game = self.game
        m = 48
        for group, is_friendly in ((self.items, False), (self.friendly, True)):
            for b in group:
                if b.dead:
                    continue
                if b.frozen or (timestop and not is_friendly):
                    continue
                k = dt * (slow if not is_friendly else 1.0)
                if b.accel:
                    s = b.speed + b.accel * k
                    if s < b.min_speed:
                        s = b.min_speed
                    elif s > b.max_speed:
                        s = b.max_speed
                    b.speed = s
                    b.vx = b.cos * s
                    b.vy = b.sin * s
                if b.turn:
                    b.angle += b.turn * k
                    b._dir()
                if b.home and is_friendly:
                    target = game.nearest_target(b.x, b.y)
                    if target is not None:
                        want = math.atan2(target.y - b.y, target.x - b.x)
                        diff = (want - b.angle + math.pi) % TAU - math.pi
                        b.angle += max(-b.home * k, min(b.home * k, diff))
                        b._dir()
                b.x += b.vx * k
                b.y += b.vy * k
                b.age += 1
                if b.fn is not None:
                    b.fn(b, game)
                x, y = b.x, b.y
                if x < -m or x > W + m or y < -m or y > H + m:
                    if b.age > b.grace:
                        b.dead = True
                elif wrap and not b.wrapped and not is_friendly and b.age > 10:
                    if x < -4 or x > W + 4 or y < -4 or y > H + 4:
                        b.x = x % W
                        b.y = y % H
                        b.wrapped = True
        if self.lasers:
            if not timestop:
                for lz in self.lasers:
                    lz.update(dt * slow)
                    if lz.t == lz.warn:
                        game.sfx("beam")
            self.lasers = [lz for lz in self.lasers if not lz.dead]
        if any(b.dead for b in self.items):
            self.items = [b for b in self.items if not b.dead]
        if any(b.dead for b in self.friendly):
            self.friendly = [b for b in self.friendly if not b.dead]

    # ------------------------------------------------------------------
    def collide_player(self, p):
        """Returns (hit_bullet_or_None, list_of_grazed_bullets)."""
        px, py = p.x, p.y
        hr = p.hit_r
        gr = p.graze_r
        grazed = []
        hit = None
        vulnerable = p.vulnerable()
        for b in self.items:
            if b.age < 5 or b.dead:
                continue
            dx = px - b.x
            dy = py - b.y
            reach = gr + b.reach
            if dx > reach or dx < -reach or dy > reach or dy < -reach:
                continue
            if b.half_len:
                t = dx * b.cos + dy * b.sin
                hl = b.half_len
                if t > hl:
                    t = hl
                elif t < -hl:
                    t = -hl
                dx -= b.cos * t
                dy -= b.sin * t
            d2 = dx * dx + dy * dy
            rr = b.r + hr
            if d2 < rr * rr and vulnerable and hit is None:
                hit = b
            elif not b.grazed and d2 < (b.r + gr) ** 2:
                b.grazed = True
                grazed.append(b)
        for lz in self.lasers:
            w = lz.current_width()
            if w <= 0.5:
                continue
            perp, along = lz.distance(px, py)
            if along < 0:
                continue
            if lz.lethal() and perp < w * 0.36 + hr and vulnerable and hit is None:
                hit = lz
            elif perp < w * 0.5 + gr and lz.graze_cd == 0:
                lz.graze_cd = 6
                grazed.append(GrazePoint(lz.x + lz.cos * along, lz.y + lz.sin * along))
        return hit, grazed

    def in_radius(self, x, y, radius, friendly=False):
        out = []
        for b in self.friendly if friendly else self.items:
            if b.dead:
                continue
            dx, dy = b.x - x, b.y - y
            if dx * dx + dy * dy < (radius + b.r) ** 2:
                out.append(b)
        return out

    def reflect(self, b, angle, speed):
        """Turn an enemy bullet into a friendly one."""
        b.dead = True
        nb = Bullet(b.x, b.y, speed, angle, b.kind if b.kind not in ("bubble", "spear") else "orb", "gold",
                    friendly=True, damage=1.0, grace=10)
        nb.home = 5.0
        self.friendly.append(nb)
        return nb

    def collide_enemies(self, enemies, on_hit):
        if not self.friendly or not enemies:
            return
        for b in self.friendly:
            if b.dead or b.frozen:
                continue
            for e in enemies:
                if not e.alive or not e.hittable:
                    continue
                dx, dy = b.x - e.x, b.y - e.y
                if b.half_len:
                    t = -(dx * b.cos + dy * b.sin)
                    t = max(-b.half_len, min(b.half_len, t))
                    dx += b.cos * t
                    dy += b.sin * t
                rr = e.r + b.r
                if dx * dx + dy * dy < rr * rr:
                    if b.pierce:
                        if b.hits is None:
                            b.hits = set()
                        if id(e) in b.hits:
                            continue
                        b.hits.add(id(e))
                    else:
                        b.dead = True
                    on_hit(b, e)
                    if b.dead:
                        break

    def cancel(self, bullets, to_items=True):
        game = self.game
        for b in bullets:
            if b.dead:
                continue
            b.dead = True
            if to_items:
                game.items.spawn("mini", b.x, b.y)
            game.particles.emit(b.x, b.y, 0, 0, 0.25, 4, PALETTE.get(b.color, PALETTE["white"])[0], "glow")

    def cancel_all(self, to_items=True, x=None, y=None, radius=None):
        if radius is None:
            for lz in self.lasers:
                lz.cancel()
            targets = self.items
        else:
            r2 = radius * radius
            targets = [b for b in self.items if (b.x - x) ** 2 + (b.y - y) ** 2 < r2]
        self.cancel(list(targets), to_items)

    def clear(self):
        self.items = []
        self.friendly = []
        self.lasers = []

    def draw_lasers(self, add):
        for lz in self.lasers:
            lz.draw(add)

    def draw(self, surf, visible=None):
        blits = []
        for group in (self.friendly, self.items):
            for b in group:
                if b.dead or b.invisible:
                    continue
                if visible is not None and group is self.items:
                    vx, vy, vr = visible
                    if (b.x - vx) ** 2 + (b.y - vy) ** 2 > vr * vr:
                        continue
                if b.age < 6 and not b.friendly:
                    s = spawn_sprite(b.color, (6 - b.age) // 2)
                    blits.append((s, (b.x - s.get_width() / 2, b.y - s.get_height() / 2)))
                    continue
                spr = b.sprite()
                blits.append((spr, (b.x - spr.get_width() / 2, b.y - spr.get_height() / 2)))
        if blits:
            surf.fblits(blits)
