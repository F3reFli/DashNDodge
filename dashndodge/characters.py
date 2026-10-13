"""Playable characters and their spell cards (bombs)."""

import math
import random
from dataclasses import dataclass, field

import pygame

from . import gfx
from .config import PALETTE, RAINBOW, W
from .util import TAU, angle_to, hsv, scale_color


@dataclass
class CharDef:
    id: str
    name: str
    jp: str
    sprite: str
    color: tuple
    spell_name: str
    spell_jp: str
    spell_desc: str
    passive: str
    blurb: str
    hearts: int = 5
    speed: float = 1.0
    hitbox: float = 2.2
    graze: float = 1.0
    magnet: float = 1.0
    dash_cd: float = 0.55
    dash_charges: int = 1
    parry_window: int = 12
    parry_r: float = 26.0
    spell_cls: type = None
    locked_by: str = ""
    death_quotes: list = field(default_factory=list)
    ending: list = field(default_factory=list)


# ======================================================================
# Player spell cards
# ======================================================================


class PlayerSpell:
    duration = 120
    invuln = 120

    def __init__(self, game, player):
        self.game = game
        self.p = player
        self.t = 0
        player.iframes = max(player.iframes, self.invuln)

    def update(self):
        self.t += 1
        return self.t < self.duration

    def draw(self, surf, add):
        pass

    def target_angle(self, default=None):
        t = self.game.nearest_target(self.p.x, self.p.y)
        if t is not None:
            return angle_to(self.p.x, self.p.y, t.x, t.y)
        if default is not None:
            return default
        fx, fy = self.p.facing
        return math.atan2(fy, fx)


class FantasySeal(PlayerSpell):
    duration = 170
    invuln = 170

    class Orb:
        def __init__(self, x, y, color, phase):
            self.x, self.y = x, y
            self.color = color
            self.phase = phase
            self.vx = self.vy = 0.0
            self.speed = 60.0
            self.dead = False
            self.target = None

    def __init__(self, game, player):
        super().__init__(game, player)
        game.bullets.cancel_all(True, player.x, player.y, 110)
        self.orbs = [self.Orb(player.x, player.y, PALETTE[c][0], TAU * i / 7) for i, c in enumerate(RAINBOW)]

    def update(self):
        g = self.game
        for i, o in enumerate(self.orbs):
            if o.dead:
                continue
            if self.t < 36:
                a = o.phase + self.t * 0.12
                r = 8 + self.t * 0.9
                o.x = self.p.x + math.cos(a) * r
                o.y = self.p.y + math.sin(a) * r
                continue
            if o.target is None or not getattr(o.target, "alive", False):
                o.target = g.nearest_target(o.x, o.y, rank=i)
            if o.target is not None:
                tx, ty = o.target.x, o.target.y
            else:
                tx = W / 2 + math.cos(o.phase) * 260
                ty = 180 + math.sin(o.phase) * 140
            a = angle_to(o.x, o.y, tx, ty)
            o.speed = min(420, o.speed + 9)
            o.vx += (math.cos(a) * o.speed - o.vx) * 0.12
            o.vy += (math.sin(a) * o.speed - o.vy) * 0.12
            o.x += o.vx / 60
            o.y += o.vy / 60
            g.bullets.cancel_all(True, o.x, o.y, 26)
            if (o.x - tx) ** 2 + (o.y - ty) ** 2 < 14 ** 2 or self.t > 150:
                self.explode(o)
        return super().update() and not all(o.dead for o in self.orbs)

    def explode(self, o):
        o.dead = True
        g = self.game
        g.damage_area(o.x, o.y, 52, 7, boss_damage=4)
        g.bullets.cancel_all(True, o.x, o.y, 60)
        g.waves.add(o.x, o.y, 60, 0.4, o.color, 4)
        g.particles.burst(o.x, o.y, 18, o.color, (60, 220), kind="glow", size=(3, 6))
        g.shake.add(4)
        g.sfx("explode")

    def draw(self, surf, add):
        for o in self.orbs:
            if o.dead:
                continue
            gfx.blit_glow(add, o.x, o.y, 22, o.color, 1.0)
            gfx.blit_glow(add, o.x, o.y, 9, (255, 255, 255), 1.0)


class MasterSpark(PlayerSpell):
    duration = 165
    invuln = 175

    def __init__(self, game, player):
        super().__init__(game, player)
        self.angle = self.target_angle()
        game.sfx("laser")
        game.flash.trigger((255, 255, 220), 120, 300)

    def width(self):
        t = self.t
        if t < 18:
            return 64 * t / 18
        if t > self.duration - 24:
            return 64 * max(0, self.duration - t) / 24
        return 64 + math.sin(t * 0.9) * 4

    def update(self):
        g = self.game
        target = g.nearest_target(self.p.x, self.p.y)
        if target is not None:
            want = angle_to(self.p.x, self.p.y, target.x, target.y)
            diff = (want - self.angle + math.pi) % TAU - math.pi
            self.angle += max(-0.012, min(0.012, diff))
        w = self.width()
        ux, uy = math.cos(self.angle), math.sin(self.angle)
        px, py = self.p.x, self.p.y
        half = w / 2

        def in_beam(x, y, r):
            dx, dy = x - px, y - py
            along = dx * ux + dy * uy
            if along < -6:
                return False
            perp = abs(-dx * uy + dy * ux)
            return perp < half + r

        g.bullets.cancel([b for b in g.bullets.items if in_beam(b.x, b.y, b.r)])
        if self.t % 4 == 0 and w > 10:
            for e in g.all_enemies():
                if in_beam(e.x, e.y, e.r):
                    e.damage(0.7 if e.is_boss else 2.0, "spell")
        g.shake.add(2.5)
        if self.t % 3 == 0:
            d = random.uniform(30, 600)
            g.particles.emit(px + ux * d, py + uy * d, ux * 300 + random.uniform(-60, 60), uy * 300 + random.uniform(-60, 60),
                             0.4, 3, hsv(random.random(), 0.5, 1), "glow")
        return super().update()

    def draw(self, surf, add):
        w = self.width()
        if w <= 0:
            return
        ux, uy = math.cos(self.angle), math.sin(self.angle)
        nx, ny = -uy, ux
        L = 900
        px, py = self.p.x, self.p.y
        layers = [(1.0, hsv(self.t * 0.02, 0.7, 0.45)), (0.75, hsv(self.t * 0.02 + 0.3, 0.6, 0.7)), (0.45, (255, 250, 230)), (0.22, (255, 255, 255))]
        for k, col in layers:
            hw = w / 2 * k
            pts = [
                (px + nx * hw * 0.4, py + ny * hw * 0.4),
                (px + ux * 30 + nx * hw, py + uy * 30 + ny * hw),
                (px + ux * L + nx * hw, py + uy * L + ny * hw),
                (px + ux * L - nx * hw, py + uy * L - ny * hw),
                (px + ux * 30 - nx * hw, py + uy * 30 - ny * hw),
                (px - nx * hw * 0.4, py - ny * hw * 0.4),
            ]
            pygame.draw.polygon(add, col, pts)
        gfx.blit_glow(add, px, py, int(w * 0.8), (255, 240, 200), 1.0)


class TheWorld(PlayerSpell):
    duration = 200
    invuln = 215

    def __init__(self, game, player):
        super().__init__(game, player)
        game.timestop = 170
        game.timestop_owner = "player"
        game.bullets.cancel_all(True, player.x, player.y, 70)
        game.sfx("timestop")
        game.flash.trigger((200, 200, 255), 160, 500)
        self.knives = []

    def update(self):
        g = self.game
        if self.t < 160 and self.t % 8 == 0:
            for k in range(2):
                a = self.t * 0.21 + TAU * k / 2
                x = self.p.x + math.cos(a) * (22 + self.t * 0.25)
                y = self.p.y + math.sin(a) * (22 + self.t * 0.25)
                target = g.nearest_target(x, y)
                ang = angle_to(x, y, target.x, target.y) if target else a
                b = g.bullets.shoot(x, y, 0, ang, "knife", "cyan", friendly=True, damage=1.0, grace=60)
                b.frozen = True
                self.knives.append(b)
        if self.t == 170:
            for b in self.knives:
                b.frozen = False
                b.set_speed(420)
                b.home = 2.5
            g.sfx("whoosh")
        return super().update()


class RainbowTaikyoku(PlayerSpell):
    duration = 70
    invuln = 95

    def __init__(self, game, player):
        super().__init__(game, player)
        self.hit = set()
        self.cx, self.cy = player.x, player.y
        game.sfx("explode")
        game.flash.trigger((255, 230, 200), 100, 400)

    def radius(self):
        return 440 * (self.t / 55) ** 0.8 if self.t < 55 else 440

    def update(self):
        g = self.game
        r = self.radius()
        r_in = max(0, r - 26)
        for b in g.bullets.items[:]:
            d2 = (b.x - self.cx) ** 2 + (b.y - self.cy) ** 2
            if r_in * r_in <= d2 <= r * r:
                target = g.nearest_target(b.x, b.y)
                a = angle_to(b.x, b.y, target.x, target.y) if target else angle_to(self.cx, self.cy, b.x, b.y)
                g.bullets.reflect(b, a, 330)
                g.stats["reflects"] += 1
        for e in g.all_enemies():
            if id(e) in self.hit:
                continue
            d2 = (e.x - self.cx) ** 2 + (e.y - self.cy) ** 2
            if d2 <= r * r:
                self.hit.add(id(e))
                e.damage(8 if e.is_boss else 6, "spell")
        if self.t % 6 == 0:
            g.waves.add(self.cx, self.cy, r + 10, 0.25, PALETTE[RAINBOW[(self.t // 6) % 7]][0], 3, r0=r)
        return super().update()

    def draw(self, surf, add):
        r = self.radius()
        for i, c in enumerate(RAINBOW):
            rr = r - i * 3
            if rr > 1:
                gfx.ring(add, self.cx, self.cy, rr, PALETTE[c][0], 2, 1 - self.t / self.duration * 0.6)


class PerfectFreeze(PlayerSpell):
    duration = 150
    invuln = 110

    def __init__(self, game, player):
        super().__init__(game, player)
        for b in game.bullets.items:
            b.frozen = True
            b.color = "white"
            b.spr_idx = -1
        for e in game.all_enemies():
            e.frozen = max(e.frozen, 150)
        game.sfx("freeze")
        game.flash.trigger((160, 230, 255), 190, 350)
        game.freeze_tint = 150

    def update(self):
        g = self.game
        if self.t < 120:
            for b in g.bullets.items:
                if not b.frozen:
                    b.frozen = True
                    b.color = "white"
                    b.spr_idx = -1
        if self.t % 8 == 0:
            g.particles.emit(random.uniform(0, W), -4, random.uniform(-20, 20), random.uniform(40, 90), 3.0, 2, (220, 245, 255), "spark")
        if self.t == 120:
            for b in g.bullets.items:
                g.particles.emit(b.x, b.y, random.uniform(-80, 80), random.uniform(-80, 80), 0.5, 3, (200, 240, 255), "shard")
            g.bullets.cancel_all(True)
            for e in g.all_enemies():
                e.frozen = 0
                e.damage(20 if e.is_boss else 8, "spell")
            g.texts.add("⑨", self.p.x, self.p.y - 30, (120, 230, 255), 36, 1.4)
            g.sfx("card_break")
            g.shake.add(6)
        return super().update()


class Gungnir(PlayerSpell):
    duration = 120
    invuln = 120

    def __init__(self, game, player):
        super().__init__(game, player)
        self.spears = []
        self.throw(0)
        game.sfx("whoosh")
        game.flash.trigger((255, 60, 60), 120, 400)

    def throw(self, offset):
        a = self.target_angle() + offset
        b = self.game.bullets.shoot(self.p.x, self.p.y, 120, a, "spear", "red", friendly=True, damage=10,
                                    accel=900, max_speed=700, pierce=True, grace=120)
        self.spears.append(b)

    def update(self):
        g = self.game
        if self.t in (24, 40):
            self.throw(random.uniform(-0.15, 0.15))
            g.sfx("whoosh")
        for s in self.spears:
            if not s.dead:
                g.bullets.cancel_all(True, s.x, s.y, 34)
                g.particles.emit(s.x, s.y, random.uniform(-40, 40), random.uniform(-40, 40), 0.5, 5, (255, 40, 60), "glow")
                if random.random() < 0.3:
                    g.particles.emit(s.x, s.y, random.uniform(-90, 90), random.uniform(-90, 90), 0.8, 3, (30, 10, 20), "smoke")
        return super().update()


# ======================================================================
# Roster
# ======================================================================

CHARACTERS = [
    CharDef(
        "reimu", "Reimu Hakurei", "博麗 霊夢", "Reimu Hakurei", (230, 60, 80),
        "Spirit Sign \"Fantasy Seal\"", "霊符「夢想封印」",
        "Seven homing orbs that wipe bullets and blow up whatever they touch.",
        "Shrine Maiden's Intuition: bigger graze zone.",
        "The shrine maiden of paradise. Broke, lazy, scarily good at dodging.",
        hearts=5, graze=1.4, spell_cls=FantasySeal,
        death_quotes=["\"I'll be back once I find a donation.\"", "\"This is so not worth the zero yen.\""],
        ending=["The red mist clears. Reimu goes home,", "checks the donation box: still empty.", "\"...I'm sending them a bill.\""],
    ),
    CharDef(
        "marisa", "Marisa Kirisame", "霧雨 魔理沙", "Marisa Kirisame", (255, 214, 80),
        "Love Sign \"Master Spark\"", "恋符「マスタースパーク」",
        "A huge laser that follows the nearest enemy. Hold still... or don't.",
        "Ordinary Magician: faster, items fly to her from further away.",
        "An ordinary magician. Power is everything, and so is 'borrowing'.",
        hearts=4, speed=1.15, magnet=2.2, spell_cls=MasterSpark,
        death_quotes=["\"I'm just borrowing this defeat, ze.\"", "\"That one didn't count!\""],
        ending=["Marisa leaves the mansion with 'only' a few books.", "Twelve. It was twelve books.", "\"I'll return them when I die, ze!\""],
    ),
    CharDef(
        "sakuya", "Sakuya Izayoi", "十六夜 咲夜", "Sakuya Izayoi", (170, 190, 255),
        "Time Sign \"The World\"", "時符「ザ・ワールド」",
        "Stops time for 3 seconds. Knives placed meanwhile fly when it resumes.",
        "Perfect Maid: two dash charges.",
        "Head maid of the Scarlet Devil Mansion. Never late. Time-wise, she can't be.",
        hearts=4, dash_charges=2, dash_cd=0.7, spell_cls=TheWorld,
        death_quotes=["\"I needed more time. Ironic.\"", "\"Mistress will NOT be pleased.\""],
        ending=["Sakuya fixes the mist, serves tea and polishes", "every knife in the mansion. Twice.", "Somehow, it is still 3pm."],
    ),
    CharDef(
        "meiling", "Hong Meiling", "紅 美鈴", "Hong Meiling", (90, 200, 120),
        "Rainbow Sign \"Taikyoku Shockwave\"", "彩符「極彩颱風」",
        "A rainbow shockwave that sends every bullet it touches back at the enemy.",
        "Gatekeeper: 6 hearts, bigger parry window. Naps if left idle.",
        "Gatekeeper of the mansion. Martial artist. Professional napper.",
        hearts=6, speed=0.93, parry_window=18, parry_r=34, spell_cls=RainbowTaikyoku,
        death_quotes=["\"I was... just resting my eyes...\"", "\"Don't tell Sakuya-san!\""],
        ending=["Meiling returns to the gate, victorious.", "She falls asleep within seven seconds.", "A knife lands gently in her hat. Business as usual."],
    ),
    CharDef(
        "cirno", "Cirno", "チルノ", "Cirno", (110, 220, 255),
        "Freeze Sign \"Perfect Freeze\"", "凍符「パーフェクトフリーズ」",
        "Freezes every bullet and enemy on screen, then shatters them all.",
        "The Strongest: every 9th graze pays ⑨x. Hitbox is... generous.",
        "The strongest. She'll tell you herself. Repeatedly.",
        hearts=4, hitbox=3.2, graze=1.1, spell_cls=PerfectFreeze,
        death_quotes=["\"That was a warm-up! A WARM-UP!\"", "\"I let you win because I'm nice.\""],
        ending=["Cirno defeats the Scarlet Devil.", "Nobody believes her.", "She freezes a frog about it. ⑨"],
    ),
    CharDef(
        "remilia", "Remilia Scarlet", "レミリア・スカーレット", "Remilia Scarlet", (220, 40, 70),
        "Divine Spear \"Spear the Gungnir\"", "神槍「スピア・ザ・グングニル」",
        "Throws three piercing spears of scarlet light. Bullets don't survive the trail.",
        "Night Queen: every 20 kills restores a heart.",
        "The Scarlet Devil herself. 500 years old. Still 'five hundred and cute'.",
        hearts=4, speed=1.05, spell_cls=Gungnir, locked_by="Clear the story mode once.",
        death_quotes=["\"How... uncouth.\"", "\"Sakuya! My parasol! ...Sakuya?\""],
        ending=["Remilia defeats... herself? The mist stays.", "It was her mist all along.", "\"Fate is SO convenient.\""],
    ),
]

BY_ID = {c.id: c for c in CHARACTERS}


def tint_color(cdef, k=1.0):
    return scale_color(cdef.color, k)
