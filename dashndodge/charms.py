"""Omamori (お守り) charms: pick one of three after each stage. Each charm
permanently tweaks the current run, roguelite style."""

import math
import random

import pygame

from . import assets
from .config import GOLD, H, TEXT, TEXT_DIM, W
from .util import clamp, ease_out_back, ease_out_cubic, scale_color


class Charm:
    def __init__(self, id, kanji, name, color, desc, apply):
        self.id = id
        self.kanji = kanji
        self.name = name
        self.color = color
        self.desc = desc
        self.apply = apply


def _vitality(g, p):
    p.max_hearts += 1
    p.hearts = min(p.max_hearts, p.hearts + 1)


def _gale(g, p):
    p.dash_cd_mult *= 0.7


def _guardian(g, p):
    p.parry_window += 5
    p.parry_r += 8


def _grazer(g, p):
    p.graze_r *= 1.3


def _spirit(g, p):
    p.spell_gain *= 1.4


def _fortune(g, p):
    p.item_mult *= 1.5
    p.magnet_r *= 1.6


def _mirror(g, p):
    p.reflect_mult *= 1.6


def _luck(g, p):
    p.heart_luck *= 2.0
    p.spell = min(p.max_spell, p.spell + 100)


def _swift(g, p):
    p.speed *= 1.12


def _oni(g, p):
    p.dash_dmg_mult *= 2.0


def _chrono(g, p):
    p.focus_slow = True


def _renewal(g, p):
    p.regen_capture = True


CHARMS = [
    Charm("vitality", "健", "Vitality", (240, 70, 90), "+1 max heart, and heal one now.", _vitality),
    Charm("gale", "疾", "Gale", (110, 220, 255), "Dash recharges 30% faster.", _gale),
    Charm("guardian", "守", "Guardian", (255, 210, 90), "Wider, longer parry window.", _guardian),
    Charm("grazer", "掠", "Grazer", (235, 235, 255), "Graze zone +30%.", _grazer),
    Charm("spirit", "霊", "Spirit", (120, 255, 150), "Spell gauge fills 40% faster.", _spirit),
    Charm("fortune", "金", "Fortune", (255, 200, 60), "Items worth +50%, pulled from further away.", _fortune),
    Charm("mirror", "鏡", "Mirror", (150, 220, 230), "Parried bullets hit 60% harder.", _mirror),
    Charm("luck", "運", "Luck", (255, 130, 200), "Twice the heart drops, plus a free spell star.", _luck),
    Charm("swift", "速", "Swift", (120, 150, 255), "Move 12% faster.", _swift),
    Charm("oni", "鬼", "Oni", (255, 110, 60), "Dash strikes deal double damage.", _oni),
    Charm("chrono", "時", "Chrono", (180, 140, 255), "Enemy bullets slow down while you focus.", _chrono),
    Charm("renewal", "癒", "Renewal", (150, 255, 210), "Capturing a spell card heals a heart.", _renewal),
]
BY_ID = {c.id: c for c in CHARMS}

_icons = {}


def icon(charm, scale=1):
    """A little omamori pouch with the charm's kanji on it."""
    key = (charm.id, scale)
    surf = _icons.get(key)
    if surf is None:
        s = pygame.Surface((18, 24), pygame.SRCALPHA)
        col = charm.color
        dark = scale_color(col, 0.45)
        pygame.draw.rect(s, dark, (1, 6, 16, 18), border_radius=3)
        pygame.draw.rect(s, col, (2, 7, 14, 16), border_radius=3)
        pygame.draw.rect(s, scale_color(col, 1.25), (3, 8, 3, 13), border_radius=1)
        pygame.draw.ellipse(s, (240, 230, 210), (5, 0, 4, 6), 1)
        pygame.draw.ellipse(s, (240, 230, 210), (9, 0, 4, 6), 1)
        s.fill((240, 230, 210), (6, 5, 6, 2))
        k = assets.text(charm.kanji, 12, (255, 255, 250), (40, 10, 20))
        s.blit(k, (9 - k.get_width() // 2, 10))
        surf = pygame.transform.scale_by(s, scale) if scale != 1 else s
        _icons[key] = surf
    return surf


def offer(owned, rng=random, n=3):
    pool = [c for c in CHARMS if c.id not in owned]
    rng.shuffle(pool)
    return pool[:n]


def give(game, charm):
    p = game.player
    charm.apply(game, p)
    p.charms.append(charm.id)


class CharmPick:
    """Overlay shown between stages. Left/right to choose, confirm to take."""

    def __init__(self, game, choices):
        self.g = game
        self.choices = choices
        self.index = 1 if len(choices) > 2 else 0
        self.t = 0.0
        self.done = len(choices) == 0
        self.taken = None
        self.closing = 0.0

    def update(self, dt):
        self.t += dt
        if self.taken is not None:
            self.closing += dt
            if self.closing > 0.5:
                self.done = True
            return
        inp = self.g.app.input
        if inp.menu("left"):
            self.index = (self.index - 1) % len(self.choices)
            self.g.sfx("move")
        elif inp.menu("right"):
            self.index = (self.index + 1) % len(self.choices)
            self.g.sfx("move")
        elif self.t > 0.5 and inp.was_pressed("confirm"):
            self.taken = self.choices[self.index]
            give(self.g, self.taken)
            self.g.sfx("capture")
            self.g.particles.burst(self._card_x(self.index), H / 2, 40, self.taken.color, (60, 240), kind="spark", size=(1, 3))

    def _card_x(self, i):
        n = len(self.choices)
        return W / 2 + (i - (n - 1) / 2) * 180

    def draw(self, surf):
        a = ease_out_cubic(min(1.0, self.t / 0.3)) * (1 - clamp(self.closing / 0.5, 0, 1))
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((8, 2, 14, int(190 * a)))
        surf.blit(shade, (0, 0))
        assets.blit_text(surf, "お守りを一つ選べ", (W / 2, 40), 12, (220, 120, 140), "midtop", alpha=255 * a)
        assets.blit_text(surf, "Choose an Omamori", (W / 2, 54), 24, GOLD, "midtop", alpha=255 * a)
        for i, c in enumerate(self.choices):
            sel = i == self.index
            k = ease_out_back(clamp((self.t - 0.1 * i) / 0.4, 0, 1))
            x = self._card_x(i)
            y = H / 2 + 10 + (1 - k) * 80 - (8 if sel else 0) + math.sin(self.t * 3 + i) * (2 if sel else 0)
            if self.taken is not None and c is not self.taken:
                continue
            card = pygame.Rect(0, 0, 150, 170)
            card.center = (int(x), int(y))
            panel = pygame.Surface(card.size, pygame.SRCALPHA)
            panel.fill((16, 8, 26, int(235 * a)))
            surf.blit(panel, card)
            pygame.draw.rect(surf, c.color if sel else (70, 60, 90), card, 2 if sel else 1)
            ic = icon(c, 3)
            surf.blit(ic, (card.centerx - ic.get_width() // 2, card.top + 12))
            assets.blit_text(surf, c.name, (card.centerx, card.top + 90), 12, c.color if sel else TEXT, "midtop")
            for j, line in enumerate(assets.wrap(c.desc, 12, 136)):
                assets.blit_text(surf, line, (card.centerx, card.top + 108 + j * 14), 12, TEXT if sel else TEXT_DIM, "midtop")
        if self.taken is None:
            assets.blit_text(surf, "←→ choose · Enter: take it", (W / 2, H - 30), 12, TEXT_DIM, "midtop", alpha=255 * a)
