"""Collectible items: point gems, gold coins, spell stars, hearts and the
little sparkles that cancelled bullets turn into."""

import math
import random

import pygame

from . import gfx
from .util import TAU

ITEM_LIFE = {"point": 9.0, "big": 10.0, "spell": 9.0, "heart": 13.0, "fake_heart": 13.0, "mini": 6.0}


class Item:
    __slots__ = ("kind", "x", "y", "vx", "vy", "age", "life", "auto", "dead", "phase", "eaten")

    def __init__(self, kind, x, y, vx, vy):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.age = 0.0
        self.life = ITEM_LIFE.get(kind, 9.0)
        self.auto = False
        self.dead = False
        self.eaten = False
        self.phase = random.uniform(0, TAU)


class Items:
    def __init__(self, game):
        self.game = game
        self.items = []

    def spawn(self, kind, x, y, n=1, spread=1.0):
        for _ in range(n):
            if kind == "mini":
                a = random.uniform(0, TAU)
                s = random.uniform(10, 40)
            else:
                a = random.uniform(0, TAU)
                s = random.uniform(40, 130) * spread
            self.items.append(Item(kind, x, y, math.cos(a) * s, math.sin(a) * s))
        if len(self.items) > 500:
            self.items = self.items[-500:]

    def collect_all(self):
        for it in self.items:
            if it.kind != "fake_heart":
                it.auto = True

    def update(self, dt):
        game = self.game
        p = game.player
        magnet = p.magnet_r if p and p.alive else 0
        for it in self.items:
            it.age += dt
            if it.age > it.life and not it.auto:
                it.dead = True
                continue
            if p and p.alive:
                dx, dy = p.x - it.x, p.y - it.y
                d = math.hypot(dx, dy) or 1.0
                if it.kind == "mini" and it.age > 0.35:
                    it.auto = True
                if it.auto or (d < magnet and it.kind != "fake_heart"):
                    sp = 260 + it.age * 120 if not it.auto else 420
                    it.vx = dx / d * sp
                    it.vy = dy / d * sp
                    it.x += it.vx * dt
                    it.y += it.vy * dt
                    if d < 10:
                        it.dead = True
                        game.collect(it)
                    continue
                if d < 12:
                    it.dead = True
                    game.collect(it)
                    continue
            k = max(0.0, 1 - 3.5 * dt)
            it.vx *= k
            it.vy *= k
            it.x += it.vx * dt
            it.y += it.vy * dt
        if any(it.dead for it in self.items):
            self.items = [it for it in self.items if not it.dead]

    def draw(self, surf, add):
        t = self.game.frame / 60.0
        for it in self.items:
            remaining = it.life - it.age
            if not it.auto and remaining < 2.5 and int(remaining * 10) % 2 == 0:
                continue
            bob = math.sin(t * 4 + it.phase) * 1.5
            x, y = int(it.x), int(it.y + bob)
            if it.kind == "mini":
                add.fill((255, 230, 120), (x - 1, y - 1, 3, 3), special_flags=pygame.BLEND_ADD)
                continue
            if it.kind == "point":
                img = gfx.pixel_art(gfx.GEM)
                glow_col = (40, 80, 200)
            elif it.kind == "big":
                img = gfx.pixel_art(gfx.COIN)
                glow_col = (200, 150, 30)
            elif it.kind == "spell":
                img = gfx.pixel_art(gfx.STAR, remap={"y": "g"})
                glow_col = (40, 180, 60)
            else:  # heart / fake_heart
                img = gfx.heart_icon(scale=1)
                glow_col = (200, 40, 80)
                if it.kind == "fake_heart" and int(t * 6 + it.phase) % 9 == 0:
                    # The tell: Tewi's fake hearts twitch every now and then.
                    x += 1
            gfx.blit_glow(add, x, y, 9, glow_col, 0.8)
            surf.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))

    def clear(self):
        self.items = []
