"""Stage enemies (fairies, kedama fuzzballs) and their behaviour scripts."""

import math
import random

import pygame

from . import gfx
from .config import FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, H, PALETTE, W
from .script import Tasks
from .util import TAU, angle_to, clamp, ease_in_out, ease_out_cubic

FAIRIES = {
    "sunny": ("Sunny Milk", "orange"),
    "luna": ("Luna Child", "yellow"),
    "star": ("Star Sapphire", "blue"),
    "dai": ("Daiyousei", "green"),
    "lily": ("Lily White", "pink"),
    "larva": ("Eternity Larva", "green"),
    "clown": ("Clownpiece", "purple"),
}


class Enemy:
    is_boss = False

    def __init__(self, game, x, y, hp=3, sprite="Sunny Milk", scale=2, r=8, points=1000,
                 drops=(("point", 2),), color="blue", kedama=False):
        self.game = game
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.hp = self.max_hp = hp
        self.r = r
        self.points = points
        self.drops = drops
        self.color = color
        self.kedama = kedama
        self.art = None if kedama else gfx.CharArt.get(sprite, scale)
        self.tasks = Tasks()
        self.alive = True
        self.hittable = True
        self.contact = True
        self.entered = False
        self.flash = 0
        self.frozen = 0
        self.t = random.uniform(0, 10)
        self.age = 0
        self.last_x = self.x
        self.lean = 0
        self.dash_hit_id = -1
        self.squash = 0.0

    # ------------------------------------------------------------------
    def update(self, dt):
        if self.frozen > 0:
            self.frozen -= 1
            return
        self.tasks.update()
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.t += dt
        self.age += 1
        dx = self.x - self.last_x
        self.lean = 1 if dx > 0.4 else -1 if dx < -0.4 else 0
        self.last_x = self.x
        if self.flash > 0:
            self.flash -= 1
        if self.squash > 0:
            self.squash = max(0.0, self.squash - dt * 4)
        on_screen = -8 < self.x < W + 8 and -8 < self.y < H + 8
        if on_screen:
            self.entered = True
        elif self.entered and not (-60 < self.x < W + 60 and -60 < self.y < H + 60):
            self.remove()
        elif not self.entered and self.age > 60 * 12:
            self.remove()

    def remove(self):
        self.alive = False
        self.tasks.clear()

    def damage(self, amount, source="shot"):
        if not self.alive or not self.hittable:
            return
        self.hp -= amount
        self.flash = 4
        self.squash = 1.0
        if self.hp <= 0:
            self.die()

    def die(self):
        if not self.alive:
            return
        self.alive = False
        self.tasks.clear()
        self.game.on_enemy_killed(self)

    # ------------------------------------------------------------------
    def draw(self, surf, add):
        if self.kedama:
            self._draw_kedama(surf)
            return
        sq = 1.0 + 0.2 * self.squash
        self.art.draw(
            surf, self.x, self.y, self.t, lean=self.lean, moving=bool(self.lean),
            white=self.flash > 0 or (self.frozen > 0 and self.frozen % 20 < 3),
            squash=(sq, 2 - sq) if self.squash else (1.0, 1.0),
        )
        if self.frozen > 0:
            pygame.draw.circle(add, (30, 70, 90), (int(self.x), int(self.y)), self.r + 6, 2)
        if self.max_hp >= 10 and self.hp < self.max_hp:
            w = 22
            frac = clamp(self.hp / self.max_hp, 0, 1)
            y = int(self.y + self.art.h / 2 + 2)
            pygame.draw.rect(surf, (20, 10, 30), (int(self.x - w / 2) - 1, y - 1, w + 2, 4))
            pygame.draw.rect(surf, PALETTE[self.color][0], (int(self.x - w / 2), y, int(w * frac), 2))

    def _draw_kedama(self, surf):
        x, y, r, t = self.x, self.y, self.r, self.t
        col = PALETTE[self.color][0]
        if self.flash > 0:
            col = (255, 255, 255)
        dark = (20, 10, 30)
        pts_o, pts = [], []
        n = 22
        for i in range(n):
            a = TAU * i / n + t * 0.7
            rr = r + (2.2 if i % 2 == 0 else 0) + math.sin(t * 7 + i * 1.7) * 0.6
            pts_o.append((x + math.cos(a) * (rr + 1.2), y + math.sin(a) * (rr + 1.2)))
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        pygame.draw.polygon(surf, dark, pts_o)
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.circle(surf, tuple(min(255, c + 60) for c in col), (int(x - r * 0.3), int(y - r * 0.35)), max(1, int(r * 0.3)))
        p = self.game.player
        la = angle_to(x, y, p.x, p.y) if p else 0
        lx, ly = math.cos(la), math.sin(la)
        blink = (int(t * 10) % 37) == 0
        for ex in (-3, 3):
            cx, cy = int(x + ex), int(y - 0.5)
            if blink:
                pygame.draw.line(surf, dark, (cx - 1, cy), (cx + 1, cy))
                continue
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 2)
            surf.set_at((int(cx + lx * 1.2 + 0.5), int(cy + ly * 1.2 + 0.5)), dark)


# ----------------------------------------------------------------------
# Spawning
# ----------------------------------------------------------------------


def fairy(game, x, y, kind="sunny", hp=3, **kw):
    name, color = FAIRIES[kind]
    e = Enemy(game, x, y, hp=hp, sprite=name, color=kw.pop("color", None) or color, **kw)
    game.spawn_enemy(e)
    return e


def kedama(game, x, y, color="pink", hp=1, r=7, **kw):
    e = Enemy(game, x, y, hp=hp, r=r, color=color, kedama=True, points=kw.pop("points", 500),
              drops=kw.pop("drops", (("point", 1),)), **kw)
    game.spawn_enemy(e)
    return e


def edge_point(side, t):
    """Point just outside an edge. side in 'top','bottom','left','right', t in 0..1."""
    if side == "top":
        return FIELD_LEFT + t * (FIELD_RIGHT - FIELD_LEFT), -14
    if side == "bottom":
        return FIELD_LEFT + t * (FIELD_RIGHT - FIELD_LEFT), H + 14
    if side == "left":
        return -14, FIELD_TOP + t * (FIELD_BOTTOM - FIELD_TOP)
    return W + 14, FIELD_TOP + t * (FIELD_BOTTOM - FIELD_TOP)


def far_side(game):
    """Edge furthest from the player, so enemies don't spawn on top of them."""
    p = game.player
    opts = {
        "top": p.y,
        "bottom": H - p.y,
        "left": p.x * (H / W),
        "right": (W - p.x) * (H / W),
    }
    return max(opts, key=opts.get)


# ----------------------------------------------------------------------
# Behaviours (generators run by enemy.tasks)
# ----------------------------------------------------------------------


def move_to(e, x, y, frames, ease=ease_out_cubic):
    sx, sy = e.x, e.y
    for i in range(1, frames + 1):
        k = ease(i / frames)
        e.x = sx + (x - sx) * k
        e.y = sy + (y - sy) * k
        yield 1


def drift(e, vx, vy):
    e.vx, e.vy = vx, vy
    while True:
        yield 60


def leave(e, speed=110):
    """Fly off through the nearest edge."""
    dists = {"l": e.x, "r": W - e.x, "t": e.y, "b": H - e.y}
    side = min(dists, key=dists.get)
    e.vx, e.vy = {"l": (-speed, 0), "r": (speed, 0), "t": (0, -speed), "b": (0, speed)}[side]
    while True:
        yield 60


def chase(e, game, speed=55, turn=1.6, duration=None):
    """Slow homing, like the original game's red enemy."""
    a = angle_to(e.x, e.y, game.player.x, game.player.y)
    n = 0
    while duration is None or n < duration:
        want = angle_to(e.x, e.y, game.player.x, game.player.y)
        diff = (want - a + math.pi) % TAU - math.pi
        a += clamp(diff, -turn / 60, turn / 60)
        e.vx, e.vy = math.cos(a) * speed, math.sin(a) * speed
        n += 1
        yield 1


def bounce(e, speed=90, duration=None, angle=None):
    """Bounce around the arena (the original 'Enemy2')."""
    a = angle if angle is not None else random.uniform(0, TAU)
    e.vx, e.vy = math.cos(a) * speed, math.sin(a) * speed
    n = 0
    while duration is None or n < duration:
        if (e.x < FIELD_LEFT + e.r and e.vx < 0) or (e.x > FIELD_RIGHT - e.r and e.vx > 0):
            e.vx = -e.vx
            e.squash = 1.0
        if (e.y < FIELD_TOP + e.r and e.vy < 0) or (e.y > FIELD_BOTTOM - e.r and e.vy > 0):
            e.vy = -e.vy
            e.squash = 1.0
        n += 1
        yield 1
    e.vx = e.vy = 0


def border_run(e, speed=120, clockwise=True, laps=1.0):
    """Run along the arena border (the original 'BorderEnemy')."""
    inset = 14
    corners = [
        (FIELD_LEFT + inset, FIELD_TOP + inset),
        (FIELD_RIGHT - inset, FIELD_TOP + inset),
        (FIELD_RIGHT - inset, FIELD_BOTTOM - inset),
        (FIELD_LEFT + inset, FIELD_BOTTOM - inset),
    ]
    if not clockwise:
        corners.reverse()
    # Start from the corner nearest to the enemy.
    i = min(range(4), key=lambda k: (corners[k][0] - e.x) ** 2 + (corners[k][1] - e.y) ** 2)
    dist_total = 0.0
    perimeter = 2 * ((FIELD_RIGHT - FIELD_LEFT - 2 * inset) + (FIELD_BOTTOM - FIELD_TOP - 2 * inset))
    yield from move_to(e, corners[i][0], corners[i][1], 30, ease_in_out)
    while dist_total < perimeter * laps:
        tx, ty = corners[(i + 1) % 4]
        d = math.hypot(tx - e.x, ty - e.y)
        frames = max(1, int(d / speed * 60))
        sx, sy = e.x, e.y
        for k in range(1, frames + 1):
            e.x = sx + (tx - sx) * k / frames
            e.y = sy + (ty - sy) * k / frames
            yield 1
        dist_total += d
        i = (i + 1) % 4
    yield from leave(e)


def path(e, points, speed=100):
    for (x, y) in points:
        d = math.hypot(x - e.x, y - e.y)
        yield from move_to(e, x, y, max(1, int(d / speed * 60)), ease_in_out)


# ----------------------------------------------------------------------
# Shooting helpers
# ----------------------------------------------------------------------


def can_shoot(e, game, min_dist=46):
    p = game.player
    if not e.alive or not p.alive:
        return False
    if not (FIELD_LEFT < e.x < FIELD_RIGHT and FIELD_TOP - 6 < e.y < FIELD_BOTTOM):
        return False
    return (e.x - p.x) ** 2 + (e.y - p.y) ** 2 > min_dist * min_dist


def shoot_aimed(e, game, n=1, spread=0.35, speed=110, kind="orb", color=None, times=1, interval=24, delay=0, sound="shot"):
    if delay:
        yield delay
    for _ in range(times):
        if can_shoot(e, game):
            a = game.aim(e.x, e.y)
            game.bullets.fan(e.x, e.y, n, speed * game.speed_mult, a, spread if n > 1 else 0, kind, color or e.color)
            game.sfx(sound)
        yield interval


def shoot_ring(e, game, n=12, speed=90, kind="orb", color=None, times=1, interval=40, delay=0, rotate=0.0, aimed=True):
    if delay:
        yield delay
    a = game.aim(e.x, e.y) if aimed else random.uniform(0, TAU)
    for _ in range(times):
        if can_shoot(e, game, 30):
            game.bullets.ring(e.x, e.y, n, speed * game.speed_mult, a, kind, color or e.color)
            game.sfx("shot2")
        a += rotate
        yield interval


def shoot_spiral(e, game, arms=3, speed=90, step=0.22, kind="rice", color=None, duration=180, interval=5):
    a = random.uniform(0, TAU)
    for _ in range(duration // interval):
        if can_shoot(e, game, 30):
            for k in range(arms):
                game.bullets.shoot(e.x, e.y, speed * game.speed_mult, a + TAU * k / arms, kind, color or e.color)
            game.sfx("shot")
        a += step
        yield interval
