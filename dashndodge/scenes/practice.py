"""Spell Practice: replay any spell card you have already met."""

import math

import pygame

from .. import assets, backgrounds, bossdefs, gfx
from ..characters import CHARACTERS
from ..config import GOLD, H, TEXT, TEXT_DIM, W
from ..game import DIFF_COLORS, DIFFICULTY, GameScene
from ..scene import Scene, dim
from ..util import scale_color

VISIBLE = 13


class PracticeScene(Scene):
    def __init__(self, app, selected=None):
        super().__init__(app)
        self.bg = backgrounds.get("night")
        self.t = 0.0
        self.entries = [(key, b, i, c) for key, b in bossdefs.PRACTICE for i, c in enumerate(b.cards)]
        self.sel = 0
        if selected is not None:
            for k, (key, _b, i, _c) in enumerate(self.entries):
                if (key, i) == tuple(selected):
                    self.sel = k
        s = app.save.settings
        self.chars = [c for c in CHARACTERS if not c.locked_by or app.save.unlocks.get(c.id)]
        ids = [c.id for c in self.chars]
        self.ci = ids.index(s.get("last_character")) if s.get("last_character") in ids else 0
        self.diff = s.get("last_difficulty", 1)

    def seen(self, card):
        return self.app.save.captured.get(card.name, [0, 0])[1] > 0

    def update(self, dt):
        self.t += dt
        inp = self.app.input
        if inp.was_pressed("back"):
            from .title import TitleScene

            self.app.replace(TitleScene(self.app))
            return
        n = len(self.entries)
        if inp.menu("down"):
            self.sel = (self.sel + 1) % n
            self.sfx("move")
        elif inp.menu("up"):
            self.sel = (self.sel - 1) % n
            self.sfx("move")
        if inp.menu("left") or inp.menu("right"):
            self.ci = (self.ci + (1 if inp.menu("right") else -1)) % len(self.chars)
            self.sfx("menu_move")
        if inp.was_pressed("spell"):
            self.diff = (self.diff + 1) % 4
            self.sfx("menu_move")
        if inp.was_pressed("confirm"):
            key, b, i, card = self.entries[self.sel]
            if not self.seen(card):
                self.sfx("parry_fail")
                return
            self.sfx("select")
            c = self.chars[self.ci]
            self.app.save.settings["last_character"] = c.id
            self.app.save.settings["last_difficulty"] = self.diff
            self.app.replace(GameScene(self.app, "practice", c.id, self.diff, practice=(key, i)))

    def draw(self, surf):
        self.bg.draw(surf, self.t)
        dim(surf, 120)
        assets.blit_text(surf, "スペルプラクティス", (W / 2, 6), 12, TEXT_DIM, "midtop")
        assets.blit_text(surf, "Spell Practice", (W / 2, 18), 24, (255, 255, 255), "midtop")
        top = max(0, min(self.sel - VISIBLE // 2, len(self.entries) - VISIBLE))
        y = 52
        for k in range(top, min(len(self.entries), top + VISIBLE)):
            _key, b, i, card = self.entries[k]
            sel = k == self.sel
            seen = self.seen(card)
            cap, att = self.app.save.captured.get(card.name, [0, 0])
            if sel:
                pygame.draw.rect(surf, (40, 26, 60), (24, y - 2, 420, 17))
                pygame.draw.rect(surf, scale_color(b.color, 0.9), (24, y - 2, 420, 17), 1)
            icon = gfx.CharArt.get(b.sprite, 1).frames["idle0"]
            if not seen:
                icon = gfx.silhouette(icon, (60, 50, 80))
            surf.blit(icon, (30, y - 2))
            name = card.name if seen else "？？？？？？？？"
            col = GOLD if sel else (TEXT if seen else TEXT_DIM)
            assets.blit_text(surf, name, (52, y), 12, col)
            stat = f"{cap}/{att}" if seen else "-"
            assets.blit_text(surf, stat, (438, y), 12, GOLD if cap else TEXT_DIM, "topright")
            y += 20
        # side panel: character + difficulty
        c = self.chars[self.ci]
        x = 540
        art = gfx.CharArt.get(c.sprite, 4)
        img = art.frame(self.t, 0, False)
        surf.blit(img, (x - img.get_width() / 2, 90 + math.sin(self.t * 2) * 2))
        assets.blit_text(surf, f"◀ {c.name} ▶", (x, 170), 12, scale_color(c.color, 1.2), "midtop")
        assets.blit_text(surf, DIFFICULTY[self.diff], (x, 190), 12, DIFF_COLORS[self.diff], "midtop")
        _key, b, i, card = self.entries[self.sel]
        if self.seen(card):
            assets.blit_text(surf, b.name, (x, 220), 12, TEXT_DIM, "midtop")
            assets.blit_text(surf, f"{card.time}s{'  · survival' if card.survival else ''}", (x, 234), 12, TEXT_DIM, "midtop")
        assets.blit_text(surf, "↑↓ card · ←→ character · X: difficulty · Enter: go · Esc: back", (W / 2, H - 16), 12, (120, 105, 140), "midtop")
