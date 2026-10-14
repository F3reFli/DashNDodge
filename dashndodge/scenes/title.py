import math
import random

import pygame

from .. import assets, backgrounds, gfx
from ..characters import CHARACTERS
from ..config import H, TEXT_DIM, VERSION, W
from ..fx import Particles, Shockwaves
from ..scene import Menu, MenuItem, Scene, dim
from ..util import clamp, ease_out_back, ease_out_cubic, scale_color

# Intro timeline (seconds).
KANJI_AT = (0.25, 0.47, 0.69)  # each glyph of 避ける slams in
LETTERS_AT = 1.0  # DASH N DODGE! drops in, one letter at a time
TAGLINE_AT = 1.55
MENU_AT = 1.6
PARADE_AT = 1.9
INTRO_END = 2.6
LOGO = "避ける"
WORD = "DASH N DODGE!"
TAGLINE = "～ 東方 inspired dash'em-up ～"


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = backgrounds.get("title")
        self.t = 0.0
        self.petals = Particles(300)
        self.waves = Shockwaves()
        self.add = pygame.Surface((W, H))
        # Intro sequence (skippable): kanji slam in, letters drop, menu slides in.
        self.intro_done = bool(getattr(app, "title_seen", False))
        if self.intro_done:
            self.t = INTRO_END
        app.title_seen = True  # the intro plays once per launch
        self.slammed = set()
        self.embers = Particles(160)
        self._masks = {}
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
        self.menu = Menu(self.app, items, 76, 160, spacing=19, intro=max(0.0, MENU_AT - self.t))
        if old is not None:
            self.menu.index = old.index
            self.menu.t = old.t
            self.menu.intro = old.intro
            self.menu.bar_y = old.bar_y

    def enter(self):
        self.app.audio.play_music(["title"])
        self.app.fx.snap_grade("title")

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
        inp = self.app.input
        if not self.intro_done:
            if self.t < MENU_AT and (inp.was_pressed("confirm") or inp.was_pressed("back")):
                self.t = MENU_AT  # skip the intro (the press must not pick a menu item)
                self.menu.intro = 0.0
                self.slammed.update(range(len(LOGO)))
                inp.pressed.clear()
            self._slams()
            if self.t >= INTRO_END:
                self.intro_done = True
        self._ambient(dt)
        if self.t >= PARADE_AT:
            self.parade_t += dt
            if self.parade_t > 4.0:
                self.parade_t = 0.0
                self.parade_i = (self.parade_i + 1) % len(self.roster())
                self.petals.burst(W - 130, 200, 18, (255, 200, 230), (30, 120), kind="glow", size=(2, 4))
                self.waves.add(W - 130, 210, 110, 0.6, (255, 160, 200), 3)
        if self.t < MENU_AT:
            self.menu.t += dt
            return
        if inp.was_pressed("back"):
            self.menu.index = len(self.menu.items) - 1
        # The odd yabujin glitch burst.
        if int(self.t * 60) % 400 == 200:
            self.app.post.glitch(10, 0.7)
            self.app.post.aberration(14, 2)
        self.menu.update(dt)

    def _slams(self):
        for i, at in enumerate(KANJI_AT):
            if i not in self.slammed and self.t >= at + 0.16:
                self.slammed.add(i)
                x, y = self._glyph_pos(i)
                self.waves.add(x, y, 70, 0.45, (255, 60, 90), 4)
                self.petals.burst(x, y, 14, (255, 120, 140), (60, 200), kind="spark", size=(1, 2))
                self.app.fx.punch(0.35, x, y)
                self.app.post.aberration(8, 2)
                self.sfx("dash")

    def _ambient(self, dt):
        if random.random() < 0.35:
            self.petals.emit(random.uniform(-40, W), -6, random.uniform(10, 40), random.uniform(25, 55),
                             random.uniform(6, 11), random.randint(2, 3), random.choice(((255, 190, 215), (255, 220, 235), (240, 160, 200))), "petal")
        if random.random() < 0.3:
            # Embers rising from the shrine path.
            self.embers.emit(random.uniform(120, W - 60), H + 4, random.uniform(-8, 8), random.uniform(-45, -20),
                             random.uniform(3, 6), random.randint(2, 3), random.choice(((255, 110, 60), (255, 160, 80), (255, 70, 90))), "glow")
        for e in self.embers.items:
            e.vx += math.sin(self.t * 2 + e.y * 0.05) * 6 * dt
        self.embers.update(dt)
        self.petals.update(dt)
        self.waves.update(dt)

    # ------------------------------------------------------------------
    def _glyph_pos(self, i):
        x = 64
        for ch in LOGO[:i]:
            x += assets.text(ch, 48, (255, 255, 255), (90, 0, 20)).get_width() - 2
        img = assets.text(LOGO[i], 48, (255, 255, 255), (90, 0, 20))
        return x + img.get_width() / 2, 22 + img.get_height() / 2

    def _shine(self, img, x, y, phase):
        """Additive diagonal light band sweeping across a glyph."""
        key = id(img)
        mask = self._masks.get(key)
        if mask is None:
            mask = pygame.mask.from_surface(img).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
            self._masks[key] = mask
        w, h = img.get_size()
        band = pygame.Surface((w, h), pygame.SRCALPHA)
        bx = phase - x
        pygame.draw.polygon(band, (255, 255, 255, 170), [(bx, 0), (bx + 14, 0), (bx - 6, h), (bx - 20, h)])
        pygame.draw.polygon(band, (255, 255, 255, 80), [(bx + 18, 0), (bx + 22, 0), (bx + 2, h), (bx - 2, h)])
        band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return band

    def _draw_logo(self, surf, add):
        t = self.t
        shine_x = ((t - INTRO_END) % 5.0) / 1.1 * 520 - 40 if t > INTRO_END else -999
        # 避ける: each glyph slams down from big to normal size.
        x = 64
        for i, ch in enumerate(LOGO):
            img = assets.text(ch, 48, (255, 244, 240), (90, 0, 20))
            k = clamp((t - KANJI_AT[i]) / 0.2, 0.0, 1.0)
            if k > 0:
                sc = 1 + (1 - ease_out_cubic(k)) * 1.8
                gw, gh = img.get_size()
                cx, cy = x + gw / 2, 22 + gh / 2
                shown = img if sc == 1 else pygame.transform.scale(img, (int(gw * sc), int(gh * sc)))
                if k < 1:
                    shown = shown.copy()
                    shown.set_alpha(int(255 * k))
                glitchy = int(t * 30) % 97 < 3 or (t - KANJI_AT[i]) < 0.35
                if glitchy:
                    for dx, col in ((-3, (255, 30, 60)), (3, (40, 220, 255))):
                        ghost = assets.text(ch, 48, col, None)
                        if sc != 1:
                            ghost = pygame.transform.scale(ghost, (int(ghost.get_width() * sc), int(ghost.get_height() * sc)))
                        add.blit(ghost, (cx - ghost.get_width() / 2 + dx, cy - ghost.get_height() / 2))
                surf.blit(shown, (cx - shown.get_width() / 2, cy - shown.get_height() / 2))
                if shine_x > -999 and sc == 1:
                    surf.blit(self._shine(img, x, 22, shine_x), (x, 22), special_flags=pygame.BLEND_RGBA_ADD)
                self.app.fx.lights.add(cx, cy, 70, (255, 60, 90), 0.35 * k)
            x += img.get_width() - 2
        # DASH N DODGE!: letters drop in with a bounce.
        x = 68
        for i, ch in enumerate(WORD):
            if ch == " ":
                x += 10
                continue
            flick = (int(t * 12) + i * 5) % 41 == 0
            col = (255, 255, 255) if flick else (235, 40, 60) if i % 2 else (255, 90, 100)
            img = assets.text(ch, 24, col, (20, 0, 8))
            k = clamp((t - LETTERS_AT - i * 0.045) / 0.4, 0.0, 1.0)
            if k > 0:
                drop = (1 - ease_out_back(k, 2.4)) * -36
                y = 88 + math.sin(t * 3 + i * 0.5) * 2 + drop
                if k < 1:
                    img = img.copy()
                    img.set_alpha(int(255 * min(1.0, k * 2)))
                surf.blit(img, (x, y))
                if shine_x > -999:
                    surf.blit(self._shine(img, x, 88, shine_x - 30), (x, y), special_flags=pygame.BLEND_RGBA_ADD)
            x += img.get_width() - 2
        # Tagline types itself in.
        n = int(clamp((t - TAGLINE_AT) / 0.6, 0.0, 1.0) * len(TAGLINE))
        if n:
            assets.blit_text(surf, TAGLINE[:n], (70, 118), 12, (220, 170, 190))

    def _draw_parade(self, surf, add):
        t = self.t
        roster = self.roster()
        c = roster[self.parade_i % len(roster)]
        enter = ease_out_cubic(clamp((t - PARADE_AT) / 0.5, 0.0, 1.0))
        px = W - 130 + (1 - enter) * 200
        gfx.draw_magic_circle(add, px, 210, 90, scale_color(c.color, 0.45 * enter), t * 0.4, 1.0, 6, 1.0)
        art = gfx.CharArt.get(c.sprite, 6)
        k = ease_out_back(min(1.0, self.parade_t / 0.45))
        bob = math.sin(t * 2) * 3
        img = art.frame(t, 0, False)
        # Card-flip entrance: the sprite spins in around its vertical axis.
        flip = abs(math.cos((1 - k) * math.pi * 1.5)) if k < 1 else 1.0
        if k < 1 or flip < 1:
            img = pygame.transform.scale(img, (max(1, int(img.get_width() * k * flip)), max(1, int(img.get_height() * k))))
        surf.blit(img, (px - img.get_width() / 2, 210 - img.get_height() / 2 + bob))
        assets.blit_text(surf, c.jp, (px, 268), 12, scale_color(c.color, 1.2), "midtop", alpha=255 * enter)
        assets.blit_text(surf, c.name, (px, 283), 12, TEXT_DIM, "midtop", alpha=255 * enter)
        self.app.fx.lights.add(px, 210, 150, c.color, 0.7 * enter)

    def draw(self, surf):
        t = self.t
        fx = self.app.fx
        self.bg.draw(surf, t)
        self.bg.lights(fx, t)
        fx.set_grade("title")
        dim(surf, 60)
        surf.blit(self.panel, (0, 0))
        add = self.add
        add.fill((0, 0, 0))
        # The colour orb from the original title screen, now a slow red pulse.
        pulse = 0.35 + 0.1 * math.sin(t * 1.5)
        gfx.blit_glow(add, 180, 70, 90, scale_color((200, 20, 40), pulse), 1.0)
        fx.lights.add(180, 70, 220, (220, 30, 60), pulse)
        if t >= PARADE_AT:
            self._draw_parade(surf, add)
        self.embers.draw(surf, add)
        for e in self.embers.items[::6]:
            fx.lights.add(e.x, e.y, 26, e.color, 0.5 * e.life / e.max_life)
        self.waves.draw(add)
        fx.waves_from(self.waves, 0.8)
        self._draw_logo(surf, add)
        surf.blit(add, (0, 0), special_flags=pygame.BLEND_ADD)
        self.petals.draw(surf, add)
        if t >= MENU_AT:
            self.menu.draw(surf)
        a = 255 * clamp((t - INTRO_END + 0.6) / 0.6, 0.0, 1.0)
        if a > 0:
            assets.blit_text(surf, f"1llumni 2025 · v{VERSION} · sprites: Majstek · Touhou (c) ZUN", (6, H - 16), 12, (130, 110, 150), alpha=a)
            assets.blit_text(surf, "Enter: select · F11: fullscreen", (W - 6, H - 16), 12, (130, 110, 150), "topright", alpha=a)
