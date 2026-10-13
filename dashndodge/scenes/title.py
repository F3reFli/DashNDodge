import math
import random

import pygame

from .. import assets, backgrounds, gfx
from ..characters import CHARACTERS
from ..config import H, TEXT_DIM, VERSION, W
from ..fx import Particles
from ..scene import Menu, MenuItem, Scene, dim
from ..util import ease_out_back, ease_out_cubic, scale_color


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = backgrounds.get("title")
        self.t = 0.0
        self.petals = Particles(300)
        self.add = pygame.Surface((W, H))
        self.build_menu()
        self.parade_i = random.randrange(len(self.roster()))
        self.parade_t = 0.0
        # Dark gradient panel so the menu stays readable over the torii.
        self.panel = pygame.Surface((W, H), pygame.SRCALPHA)
        for x in range(0, 360, 2):
            a = int(200 * max(0.0, 1 - x / 360) ** 1.3)
            self.panel.fill((6, 0, 6, a), (x, 0, 2, H))

    def roster(self):
        return [c for c in CHARACTERS if not c.locked_by or self.app.save.unlocks.get(c.id)]

    def build_menu(self):
        save = self.app.save
        extra = save.unlocks.get("extra", False)
        items = [
            MenuItem("Story Mode", lambda: self.select("story"), sub="ストーリー"),
            MenuItem("Extra Stage" if extra else "Extra Stage  ???", lambda: self.select("extra"), enabled=extra, sub="エクストラ"),
            MenuItem("Endless", lambda: self.select("endless"), sub="エンドレス"),
            MenuItem("Spell Practice", self.practice, enabled=any(v[1] > 0 for v in save.captured.values()), sub="スペルプラクティス"),
            MenuItem("High Scores", self.scores, sub="スコア"),
            MenuItem("How to Play", self.howto, sub="遊び方"),
            MenuItem("Settings", self.settings, sub="設定"),
            MenuItem("Quit", self.app.quit, sub="終了"),
        ]
        old = getattr(self, "menu", None)
        self.menu = Menu(self.app, items, 76, 160, spacing=19)
        if old is not None:
            self.menu.index = old.index

    def enter(self):
        self.app.audio.play_music(["title"])

    def resume(self):
        self.build_menu()

    def select(self, mode):
        from .charselect import CharSelectScene

        self.app.replace(CharSelectScene(self.app, mode))

    def practice(self):
        from .practice import PracticeScene

        self.app.replace(PracticeScene(self.app))

    def scores(self):
        from .scores import ScoresScene

        self.app.push(ScoresScene(self.app))

    def howto(self):
        from .howto import HowToScene

        self.app.push(HowToScene(self.app))

    def settings(self):
        from .settings import SettingsScene

        self.app.push(SettingsScene(self.app))

    def update(self, dt):
        self.t += dt
        self.parade_t += dt
        if self.parade_t > 4.0:
            self.parade_t = 0.0
            self.parade_i = (self.parade_i + 1) % len(self.roster())
            self.petals.burst(W - 130, 200, 18, (255, 200, 230), (30, 120), kind="glow", size=(2, 4))
        if random.random() < 0.35:
            self.petals.emit(random.uniform(-40, W), -6, random.uniform(10, 40), random.uniform(25, 55),
                             random.uniform(6, 11), random.randint(2, 3), random.choice(((255, 190, 215), (255, 220, 235), (240, 160, 200))), "petal")
        self.petals.update(dt)
        if self.app.input.was_pressed("back"):
            self.menu.index = len(self.menu.items) - 1
        # The odd yabujin glitch burst.
        if int(self.t * 60) % 400 == 200:
            self.app.post.glitch(10, 0.7)
            self.app.post.aberration(14, 2)
        self.menu.update(dt)

    def draw(self, surf):
        t = self.t
        self.bg.draw(surf, t)
        dim(surf, 60)
        surf.blit(self.panel, (0, 0))
        add = self.add
        add.fill((0, 0, 0))
        # The colour orb from the original title screen, now a slow red pulse.
        gfx.blit_glow(add, 180, 70, 90, scale_color((200, 20, 40), 0.35 + 0.1 * math.sin(t * 1.5)), 1.0)
        # Character parade
        roster = self.roster()
        c = roster[self.parade_i % len(roster)]
        gfx.draw_magic_circle(add, W - 130, 210, 90, scale_color(c.color, 0.45), t * 0.4, 1.0, 6, 1.0)
        surf.blit(add, (0, 0), special_flags=pygame.BLEND_ADD)
        self.petals.draw(surf, add)
        art = gfx.CharArt.get(c.sprite, 6)
        k = ease_out_back(min(1.0, self.parade_t / 0.45))
        bob = math.sin(t * 2) * 3
        img = art.frame(t, 0, False)
        if k < 1:
            img = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
        surf.blit(img, (W - 130 - img.get_width() / 2, 210 - img.get_height() / 2 + bob))
        assets.blit_text(surf, c.jp, (W - 130, 268), 12, scale_color(c.color, 1.2), "midtop")
        assets.blit_text(surf, c.name, (W - 130, 283), 12, TEXT_DIM, "midtop")
        # Logo
        intro = ease_out_cubic(min(1.0, t / 0.8))
        ly = 22 - (1 - intro) * 30
        glitchy = t < 0.5 or int(t * 30) % 97 < 3
        if glitchy:
            assets.blit_text(surf, "避ける", (61, ly), 48, (255, 30, 60), outline=None, alpha=200 * intro)
            assets.blit_text(surf, "避ける", (67, ly + 1), 48, (40, 220, 255), outline=None, alpha=160 * intro)
        assets.blit_text(surf, "避ける", (64, ly), 48, (255, 244, 240), outline=(90, 0, 20), alpha=255 * intro)
        x = 68
        word = "DASH N DODGE!"
        for i, ch in enumerate(word):
            if ch == " ":
                x += 10
                continue
            flick = (int(t * 12) + i * 5) % 41 == 0
            col = (255, 255, 255) if flick else (235, 40, 60) if i % 2 else (255, 90, 100)
            img = assets.text(ch, 24, col, (20, 0, 8))
            y = 88 + math.sin(t * 3 + i * 0.5) * 2
            surf.blit(img, (x, y))
            x += img.get_width() - 2
        assets.blit_text(surf, "～ 東方 inspired dash'em-up ～", (70, 118), 12, (220, 170, 190))
        self.menu.draw(surf)
        assets.blit_text(surf, f"1llumni 2025 · v{VERSION} · sprites: Majstek · Touhou (c) ZUN", (6, H - 16), 12, (130, 110, 150))
        assets.blit_text(surf, "Enter: select · F11: fullscreen", (W - 6, H - 16), 12, (130, 110, 150), "topright")
