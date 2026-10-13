import math

import pygame

from .. import assets, backgrounds, gfx
from ..characters import CHARACTERS
from ..config import GOLD, H, TEXT, TEXT_DIM, W
from ..game import DIFF_COLORS, DIFFICULTY, GameScene
from ..scene import Scene, dim
from ..util import clamp, ease_out_back, scale_color

MODE_NAMES = {"story": "Story Mode", "extra": "Extra Stage", "endless": "Endless"}
DIFF_BLURB = [
    "Relaxed bullets. Perfect for learning to dash and parry.",
    "The intended experience. Fair, but it bites.",
    "Faster, denser bullets. For seasoned dodgers.",
    "Pure danmaku hell. Good luck. You'll need it.",
]


class CharSelectScene(Scene):
    def __init__(self, app, mode):
        super().__init__(app)
        self.mode = mode
        self.bg = backgrounds.get("night")
        self.t = 0.0
        self.add = pygame.Surface((W, H))
        save = app.save
        ids = [c.id for c in CHARACTERS]
        last = save.settings.get("last_character", "reimu")
        self.index = ids.index(last) if last in ids else 0
        if not self.unlocked(CHARACTERS[self.index]):
            self.index = 0
        self.diff = save.settings.get("last_difficulty", 1)
        if mode == "extra":
            self.diff = max(self.diff, 1)
        self.row = 0  # 0 = character, 1 = difficulty
        self.change_t = 0.0

    def unlocked(self, c):
        return not c.locked_by or self.app.save.unlocks.get(c.id, False)

    def update(self, dt):
        self.t += dt
        self.change_t += dt
        inp = self.app.input
        if inp.was_pressed("back"):
            from .title import TitleScene

            self.app.replace(TitleScene(self.app))
            return
        if inp.menu("up") or inp.menu("down"):
            self.row = 1 - self.row
            self.sfx("move")
        if inp.menu("left") or inp.menu("right"):
            d = 1 if inp.menu("right") else -1
            if self.row == 0:
                self.index = (self.index + d) % len(CHARACTERS)
                self.change_t = 0.0
            else:
                lo = 1 if self.mode == "extra" else 0
                self.diff = int(clamp(self.diff + d, lo, 3))
            self.sfx("move")
        if inp.was_pressed("confirm"):
            c = CHARACTERS[self.index]
            if not self.unlocked(c):
                self.sfx("parry_fail")
                return
            self.sfx("select")
            save = self.app.save
            save.settings["last_character"] = c.id
            save.settings["last_difficulty"] = self.diff
            save.stats["runs"] = save.stats.get("runs", 0) + 1
            save.write()
            self.app.replace(GameScene(self.app, self.mode, c.id, self.diff))

    def draw(self, surf):
        t = self.t
        self.bg.draw(surf, t)
        dim(surf, 90)
        c = CHARACTERS[self.index]
        unlocked = self.unlocked(c)
        add = self.add
        add.fill((0, 0, 0))
        col = c.color if unlocked else (80, 70, 100)
        gfx.draw_magic_circle(add, 130, 150, 100, scale_color(col, 0.5), t * 0.3, 1.0, 6)
        gfx.blit_glow(add, 130, 150, 80, scale_color(col, 0.3))
        surf.blit(add, (0, 0), special_flags=pygame.BLEND_ADD)
        assets.blit_text(surf, "キャラ選択 - Choose your dodger", (W / 2, 8), 12, TEXT_DIM, "midtop")
        assets.blit_text(surf, MODE_NAMES[self.mode], (W / 2, 22), 12, GOLD, "midtop")
        # Big portrait
        art = gfx.CharArt.get(c.sprite, 7)
        k = ease_out_back(min(1.0, self.change_t / 0.35))
        img = art.frame(t, 0, False)
        if not unlocked:
            img = gfx.silhouette(img, (30, 24, 44))
        if k < 1:
            img = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), img.get_height()))
        surf.blit(img, (130 - img.get_width() / 2, 150 - img.get_height() / 2 + math.sin(t * 2) * 3))
        # Info panel
        x0 = 262
        panel = pygame.Surface((W - x0 - 14, 206), pygame.SRCALPHA)
        panel.fill((10, 6, 20, 190))
        surf.blit(panel, (x0, 42))
        pygame.draw.rect(surf, scale_color(col, 0.8), (x0, 42, W - x0 - 14, 206), 1)
        if unlocked:
            assets.blit_text(surf, c.jp, (x0 + 10, 50), 12, scale_color(c.color, 1.2))
            assets.blit_text(surf, c.name, (x0 + 10, 64), 24, TEXT)
            y = 94
            for line in assets.wrap(c.blurb, 12, W - x0 - 34):
                assets.blit_text(surf, line, (x0 + 10, y), 12, TEXT_DIM)
                y += 14
            y += 4
            self._stat(surf, x0 + 10, y, "Hearts", None, c.hearts)
            self._stat(surf, x0 + 10, y + 14, "Speed", c.speed / 1.2)
            self._stat(surf, x0 + 10, y + 28, "Parry", (c.parry_window / 18) * 0.6 + (c.parry_r / 34) * 0.4)
            self._stat(surf, x0 + 10, y + 42, "Dash", min(1.0, c.dash_charges / 2 * 0.6 + 0.4))
            y += 62
            assets.blit_text(surf, c.spell_jp, (x0 + 10, y), 12, GOLD)
            y += 14
            assets.blit_text(surf, c.spell_name, (x0 + 10, y), 12, GOLD)
            y += 14
            for line in assets.wrap(c.spell_desc, 12, W - x0 - 34):
                assets.blit_text(surf, line, (x0 + 10, y), 12, TEXT)
                y += 14
            for line in assets.wrap(c.passive, 12, W - x0 - 34):
                assets.blit_text(surf, line, (x0 + 10, y), 12, (150, 220, 160))
                y += 14
        else:
            assets.blit_text(surf, "? ? ?", (x0 + 10, 64), 24, TEXT_DIM)
            assets.blit_text(surf, "Locked - " + c.locked_by, (x0 + 10, 100), 12, TEXT_DIM)
        # Roster strip
        n = len(CHARACTERS)
        sx = W / 2 - n * 22
        for i, ch in enumerate(CHARACTERS):
            x = sx + i * 44 + 22
            y = 274
            ok = self.unlocked(ch)
            a = gfx.CharArt.get(ch.sprite, 2)
            im = a.frame(t if i == self.index else 0, 0, i == self.index)
            if not ok:
                im = gfx.silhouette(im, (40, 34, 56))
            box = pygame.Rect(0, 0, 38, 38)
            box.center = (x, y)
            pygame.draw.rect(surf, (12, 8, 22), box)
            if i == self.index:
                pygame.draw.rect(surf, GOLD if self.row == 0 else TEXT, box, 2)
            else:
                pygame.draw.rect(surf, (60, 50, 80), box, 1)
            surf.blit(im, (x - im.get_width() / 2, y - im.get_height() / 2))
        # Difficulty
        y = 300
        dcol = DIFF_COLORS[self.diff]
        sel = self.row == 1
        label = f"◀  {DIFFICULTY[self.diff]}  ▶" if sel else DIFFICULTY[self.diff]
        assets.blit_text(surf, "Difficulty", (W / 2 - 110, y), 12, GOLD if sel else TEXT_DIM, "topright")
        assets.blit_text(surf, label, (W / 2 - 40, y), 12, dcol)
        assets.blit_text(surf, DIFF_BLURB[self.diff], (W / 2, y + 16), 12, TEXT_DIM, "midtop")
        assets.blit_text(surf, "←→ choose · ↑↓ switch row · Enter: start · Esc: back", (W / 2, H - 3), 12, (110, 95, 130), "midbottom")

    def _stat(self, surf, x, y, label, value, hearts=None):
        assets.blit_text(surf, label, (x, y), 12, TEXT_DIM)
        if hearts is not None:
            for i in range(hearts):
                surf.blit(gfx.heart_icon(), (x + 54 + i * 10, y + 2))
            return
        w = 110
        pygame.draw.rect(surf, (40, 30, 60), (x + 54, y + 5, w, 4))
        pygame.draw.rect(surf, GOLD, (x + 54, y + 5, int(w * clamp(value, 0, 1)), 4))
