"""Boss entity: spell card flow, movement, HP ring and magic circle."""

import math
import random

import pygame

from . import gfx
from .config import FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, W
from .enemies import Enemy
from .script import Tasks
from .util import TAU, clamp, ease_in_out, scale_color


class SpellCard:
    def __init__(self, name, pattern, hp=60, time=30, bonus=500_000, survival=False, bg=None):
        self.name = name
        self.pattern = pattern
        self.hp = hp
        self.time = time
        self.bonus = bonus
        self.survival = survival  # can't be damaged, only outlasted
        self.bg = bg


class BossDef:
    def __init__(self, id, name, title, sprite, color, cards, circle_points=6, scale=3, jp="", midboss=False):
        self.id = id
        self.name = name
        self.title = title
        self.sprite = sprite
        self.color = color
        self.cards = cards
        self.circle_points = circle_points
        self.scale = scale
        self.jp = jp
        self.midboss = midboss

    def with_cards(self, cards, **kw):
        """A copy of this boss using only the given spell cards."""
        args = dict(circle_points=self.circle_points, scale=self.scale, jp=self.jp, midboss=self.midboss)
        args.update(kw)
        return BossDef(self.id, self.name, self.title, self.sprite, self.color, cards, **args)


class Boss(Enemy):
    is_boss = True

    def __init__(self, game, bdef, x=W / 2, y=-30, hp_mult=1.0):
        super().__init__(game, x, y, hp=1, sprite=bdef.sprite, scale=bdef.scale, r=13, points=0, drops=())
        self.d = bdef
        self.hp_mult = hp_mult
        self.cards = list(bdef.cards)
        self.card_index = -1
        self.card = None
        self.card_time = 0
        self.card_frames = 0
        self.card_hp = self.card_hp_max = 1
        self.card_clean = True
        self.state = "enter"
        self.ptasks = Tasks()
        self.hittable = False
        self.contact = True
        self.move_from = self.move_to_pos = None
        self.move_t = self.move_dur = 0
        self.circle_angle = 0.0
        self.hp_display = 0.0
        self.invisible = False
        self.on_defeat = None
        self.label_t = 0.0
        self.escaped = False

    # ------------------------------------------------------------------
    # Movement
    def go(self, x, y, frames=40):
        x = clamp(x, FIELD_LEFT + 30, FIELD_RIGHT - 30)
        y = clamp(y, FIELD_TOP + 24, FIELD_BOTTOM - 30)
        self.move_from = (self.x, self.y)
        self.move_to_pos = (x, y)
        self.move_t = 0
        self.move_dur = max(1, frames)

    def wander(self, frames=50, region=(140, 60, 500, 170)):
        x0, y0, x1, y1 = region
        nx = random.uniform(x0, x1)
        ny = random.uniform(y0, y1)
        # Prefer to move away from the player a little.
        p = self.game.player
        if abs(nx - p.x) < 80:
            nx = clamp(nx + (80 if nx > p.x else -80), x0, x1)
        self.go(nx, ny, frames)

    def moving(self):
        return self.move_to_pos is not None

    # ------------------------------------------------------------------
    def start(self):
        self.next_card()

    def next_card(self):
        self.ptasks.clear()
        self.card_index += 1
        if self.card_index >= len(self.cards):
            self.defeat()
            return
        self.card = self.cards[self.card_index]
        self.card_frames = 0
        self.card_time = int(self.card.time * 60)
        self.card_hp = self.card_hp_max = self.card.hp * self.hp_mult
        self.hp_display = 0.0
        self.card_clean = True
        self.state = "declare"
        self.hittable = False
        self.game.declare_spell(self)
        self.ptasks.spawn(self._run_card(self.card))

    def _run_card(self, card):
        yield 50
        self.state = "card"
        self.hittable = not card.survival
        yield from card.pattern(self, self.game)
        while True:
            yield 60

    def end_card(self, timeout):
        g = self.game
        self.ptasks.clear()
        self.state = "between"
        self.hittable = False
        captured = self.card_clean and (not timeout or self.card.survival)
        g.end_spell(self, captured, timeout)
        self.invisible = False
        if self.d.midboss and self.card_index >= len(self.cards) - 1:
            # Midbosses leave after their card, defeated or not.
            self.escaped = timeout and not self.card.survival
            self.defeat()
            return
        self.ptasks.spawn(self._between())

    def _between(self):
        self.go(W / 2, 110, 50)
        yield 75
        self.next_card()

    def defeat(self):
        self.state = "dead"
        self.alive = False
        self.ptasks.clear()
        self.tasks.clear()
        self.game.on_boss_defeated(self)

    # ------------------------------------------------------------------
    def damage(self, amount, source="shot"):
        if self.state != "card" or not self.hittable or self.card.survival:
            return
        self.card_hp -= amount
        self.flash = 3
        if self.card_hp <= 0:
            self.end_card(timeout=False)

    def die(self):
        pass

    def update(self, dt):
        self.t += dt
        self.circle_angle += dt * 1.2
        self.label_t += dt
        if self.flash > 0:
            self.flash -= 1
        if self.frozen > 0:
            self.frozen -= 1
            return
        # movement interpolation
        if self.move_to_pos is not None:
            self.move_t += 1
            k = ease_in_out(self.move_t / self.move_dur)
            (sx, sy), (tx, ty) = self.move_from, self.move_to_pos
            nx = sx + (tx - sx) * k
            self.lean = 1 if nx > self.x + 0.3 else -1 if nx < self.x - 0.3 else 0
            self.x, self.y = nx, sy + (ty - sy) * k
            if self.move_t >= self.move_dur:
                self.move_to_pos = None
                self.lean = 0
        self.tasks.update()
        self.ptasks.update()
        if self.state in ("card", "declare"):
            self.card_frames += 1
            if self.state == "card":
                self.card_time -= 1
                if 0 < self.card_time <= 300 and self.card_time % 60 == 0:
                    self.game.sfx("tick")
                if self.card_time <= 0:
                    self.end_card(timeout=True)
        target = self.card_hp / self.card_hp_max if self.card_hp_max else 0
        self.hp_display += (target - self.hp_display) * 0.12

    # ------------------------------------------------------------------
    def draw(self, surf, add):
        if self.state == "dead":
            return
        color = self.d.color
        gfx.draw_magic_circle(add, self.x, self.y + 4, 46, scale_color(color, 0.8), self.circle_angle, 0.9, self.d.circle_points, 0.55)
        gfx.draw_magic_circle(add, self.x, self.y, 30, scale_color(color, 0.55), -self.circle_angle * 1.6, 0.6, 5)
        if self.invisible:
            if int(self.t * 20) % 7 == 0:
                gfx.blit_glow(add, self.x, self.y, 10, color, 0.4)
            return
        gfx.blit_glow(add, self.x, self.y, 30, scale_color(color, 0.5), 0.8)
        bob = math.sin(self.t * 2.4) * 2
        self.art.draw(surf, self.x, self.y + bob, self.t, self.lean, self.moving(), self.flash > 0 or (self.frozen and self.frozen % 20 < 3))
        if self.state in ("card", "declare") and self.card and not self.card.survival:
            self._hp_ring(surf)

    def _hp_ring(self, surf):
        r = 30
        rect = pygame.Rect(int(self.x - r), int(self.y - r), r * 2, r * 2)
        frac = clamp(self.hp_display, 0, 1)
        if frac <= 0:
            return
        start = math.pi / 2
        pygame.draw.arc(surf, (30, 10, 30), rect.inflate(2, 2), 0, TAU, 4)
        col = (255, 90, 110) if frac < 0.25 else (255, 236, 236)
        pygame.draw.arc(surf, col, rect, start, start + TAU * frac, 2)
