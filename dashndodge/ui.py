"""In-game UI: HUD, dialogue box, spell card cut-ins, stage title cards."""


import pygame

from . import assets, charms, gfx
from .config import ACCENT, GOLD, H, TEXT, TEXT_DIM, W
from .util import clamp, ease_in_cubic, ease_out_back, ease_out_cubic, fmt_score, scale_color


# ======================================================================
# HUD
# ======================================================================


class HUD:
    def __init__(self, game):
        self.g = game
        self.score_shown = 0.0
        self.bar = pygame.Surface((W, 20), pygame.SRCALPHA)
        self.bar.fill((8, 4, 16, 190))
        pygame.draw.line(self.bar, (70, 50, 100, 255), (0, 19), (W, 19))

    def update(self, dt):
        diff = self.g.score - self.score_shown
        self.score_shown += diff * min(1.0, dt * 12) if abs(diff) > 1 else diff

    def draw(self, surf):
        g = self.g
        p = g.player
        surf.blit(self.bar, (0, 0))
        # hearts
        x = 6
        for i in range(p.max_hearts):
            surf.blit(gfx.heart_icon(empty=i >= p.hearts), (x, 6))
            x += 10
        # spell stock + gauge
        x += 8
        stock = int(p.spell // 100)
        for i in range(3):
            surf.blit(gfx.star_icon(empty=i >= stock), (x + i * 10, 5))
        frac = (p.spell % 100) / 100 if stock < 3 else 1.0
        pygame.draw.rect(surf, (40, 30, 60), (x, 16, 29, 2))
        pygame.draw.rect(surf, (120, 255, 140) if stock < 3 else GOLD, (x, 16, int(29 * frac), 2))
        x += 38
        # graze
        assets.blit_text(surf, f"Graze {g.graze}", (x, 4), 12, TEXT_DIM)
        # score
        score = int(self.score_shown)
        s = f"{score:011,}".replace(",", " ")
        assets.blit_text(surf, s, (W - 6, 4), 12, TEXT, "topright")
        assets.blit_text(surf, "SCORE", (W - 6 - assets.font(12).size(s)[0] - 6, 4), 12, TEXT_DIM, "topright")
        # chain
        if g.chain > 1:
            k = g.chain_timer / g.CHAIN_TIME
            col = GOLD if g.chain_mult() >= 3 else TEXT
            txt = f"x{g.chain_mult():.1f}  {g.chain} CHAIN"
            r = assets.blit_text(surf, txt, (W - 6, 22), 12, col, "topright")
            pygame.draw.rect(surf, scale_color(col, 0.8), (r.left, r.bottom, int(r.width * k), 1))
        if g.score_mult > 1:
            assets.blit_text(surf, f"⑨ x{g.score_mult} SCORE", (W - 6, 38), 12, (120, 220, 255), "topright")
        # center: stage / boss
        if g.boss and g.boss.alive and g.boss.state != "enter":
            self._boss(surf, g.boss)
        elif g.stage_label:
            assets.blit_text(surf, g.stage_label, (W / 2, 4), 12, TEXT_DIM, "midtop")
        if g.incident and g.incident_active:
            inc = g.incident
            y = 22 if not (g.boss and g.boss.alive) else 54
            r = assets.blit_text(surf, f"異変  {inc.title}", (W / 2, y), 12, inc.color, "midtop")
            pygame.draw.rect(surf, (30, 20, 40), (r.left, r.bottom + 1, r.width, 2))
            pygame.draw.rect(surf, inc.color, (r.left, r.bottom + 1, int(r.width * inc.remaining), 2))
        for i, cid in enumerate(p.charms):
            c = charms.BY_ID.get(cid)
            if c is not None:
                surf.blit(charms.icon(c), (4 + i * 19, 22))
        if g.app.save.settings.get("show_fps"):
            assets.blit_text(surf, f"{g.app.clock.get_fps():.0f} FPS", (W - 4, H - 4), 12, TEXT_DIM, "bottomright")

    def _boss(self, surf, b):
        # name + remaining cards
        assets.blit_text(surf, b.d.name, (W / 2 - 160, 22), 12, scale_color(b.d.color, 1.1), "topleft")
        remaining = len(b.cards) - max(0, b.card_index) - (0 if b.state in ("card", "declare") else 0)
        for i in range(max(0, remaining - 1)):
            surf.blit(gfx.star_icon(), (W / 2 - 160 + assets.font(12).size(b.d.name)[0] + 6 + i * 10, 24))
        if b.card and b.state in ("card", "declare"):
            secs = max(0, b.card_time) / 60
            col = ACCENT if secs < 5 else TEXT
            whole = int(secs)
            frac = int((secs - whole) * 100)
            r = assets.blit_text(surf, f"{whole:02d}", (W / 2, 1), 24, col, "midtop")
            assets.blit_text(surf, f".{frac:02d}", (r.right, 13), 12, col, "topleft")
            # spell card name (top right, under the bar)
            name = b.card.name
            t = b.card_frames / 60
            slide = ease_out_cubic(clamp((t - 0.6) / 0.5, 0, 1))
            y = int(H * 0.8 + (40 - H * 0.8) * slide) if t < 1.1 else 40
            nr = assets.blit_text(surf, name, (W - 6, y), 12, (255, 236, 240), "topright", shadow=(120, 20, 50))
            pygame.draw.line(surf, scale_color(b.d.color, 0.9), (nr.left - 10, nr.bottom), (W - 4, nr.bottom))
            if b.card_clean:
                bonus = self.g.card_bonus_value(b)
                assets.blit_text(surf, f"Bonus {fmt_score(bonus)}", (W - 6, nr.bottom + 2), 12, TEXT_DIM, "topright")
            else:
                assets.blit_text(surf, "Bonus Failed", (W - 6, nr.bottom + 2), 12, (150, 90, 110), "topright")


# ======================================================================
# Dialogue
# ======================================================================


class Dialogue:
    CPS = 55  # characters per second

    def __init__(self, game, lines, player_cdef, boss_def):
        self.g = game
        self.lines = lines
        self.i = 0
        self.chars = 0.0
        self.done = not lines
        self.t = 0.0
        self.left = gfx.CharArt.get(player_cdef.sprite, 5)
        self.right = gfx.CharArt.get(boss_def.sprite, 5)
        self.left_name = player_cdef.name
        self.right_name = boss_def.name
        self.left_col = player_cdef.color
        self.right_col = boss_def.color
        self.wrapped = [assets.wrap(text, 12, 440) for _side, text in lines]

    def update(self, inp, dt):
        if self.done:
            return
        self.t += dt
        total = len(self.lines[self.i][1])
        self.chars = min(total, self.chars + self.CPS * dt)
        fast = inp.held("focus") and int(self.t * 60) % 4 == 0
        if fast or any(inp.was_pressed(a) for a in ("confirm", "dash", "spell")):
            if self.chars < total and not fast:
                self.chars = total
            else:
                self.i += 1
                self.chars = 0
                self.g.sfx("menu_move")
                if self.i >= len(self.lines):
                    self.done = True

    def draw(self, surf):
        if self.done:
            return
        side, _text = self.lines[self.i]
        intro = ease_out_cubic(min(1.0, self.t / 0.35))
        # portraits
        for art, is_left in ((self.left, True), (self.right, False)):
            active = (side == "P") == is_left
            x = 70 if is_left else W - 70
            x += (-120 if is_left else 120) * (1 - intro)
            y = H - 95 + (0 if active else 8)
            img = art.frame(self.t, 0, active)
            if not active:
                img = img.copy()
                img.fill((110, 100, 130, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))
        # box
        box = pygame.Rect(90, H - 74, W - 180, 64)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((10, 6, 20, 215))
        surf.blit(panel, box)
        col = self.left_col if side == "P" else self.right_col
        pygame.draw.rect(surf, col, box, 1)
        name = self.left_name if side == "P" else self.right_name
        tag = assets.text(name, 12, col)
        tx = box.left + 8 if side == "P" else box.right - 8 - tag.get_width()
        pygame.draw.rect(surf, (10, 6, 20), (tx - 4, box.top - 8, tag.get_width() + 8, 14))
        pygame.draw.rect(surf, col, (tx - 4, box.top - 8, tag.get_width() + 8, 14), 1)
        surf.blit(tag, (tx, box.top - 8))
        remaining = int(self.chars)
        y = box.top + 10
        for line in self.wrapped[self.i]:
            if remaining <= 0:
                break
            part = line[:remaining]
            remaining -= len(line) + 1
            assets.blit_text(surf, part, (box.left + 10, y), 12, TEXT)
            y += 15
        if self.chars >= len(self.lines[self.i][1]) and int(self.t * 3) % 2 == 0:
            assets.blit_text(surf, "▼", (box.right - 10, box.bottom - 4), 12, col, "bottomright")
        assets.blit_text(surf, "Hold Shift: skip", (box.right, box.bottom + 2), 12, (110, 95, 130), "topright")


# ======================================================================
# Spell card cut-in
# ======================================================================


class CutIn:
    DURATION = 1.25

    def __init__(self, sprite, color, name, from_right=True):
        self.art = gfx.CharArt.get(sprite, 7)
        self.color = color
        self.name = name
        self.t = 0.0
        self.right = from_right
        self.done = False

    def update(self, dt):
        self.t += dt
        if self.t >= self.DURATION:
            self.done = True

    def draw(self, surf):
        t = self.t / self.DURATION
        if t < 0.18:
            a = ease_out_cubic(t / 0.18)
        elif t > 0.8:
            a = 1 - ease_in_cubic((t - 0.8) / 0.2)
        else:
            a = 1.0
        direction = -1 if self.right else 1
        # diagonal band
        band = pygame.Surface((W, 110), pygame.SRCALPHA)
        band.fill((*scale_color(self.color, 0.35), int(150 * a)))
        for i in range(0, W, 16):
            x = (i + direction * self.t * 400) % W
            pygame.draw.line(band, (*scale_color(self.color, 0.7), int(120 * a)), (x, 0), (x - 30, 110), 2)
        txt = assets.text(self.name, 12, (255, 255, 255), None)
        tile = txt.get_width() + 40
        n = W // tile + 2
        total = n * tile
        for k in range(n):
            band.blit(txt, ((k * tile + direction * self.t * 120) % total - tile, 6))
            band.blit(txt, ((k * tile - direction * self.t * 120) % total - tile, 90))
        rot = pygame.transform.rotate(band, 8 * (1 if self.right else -1))
        surf.blit(rot, (W / 2 - rot.get_width() / 2, H / 2 - rot.get_height() / 2 - 10))
        # portrait sliding slowly across
        img = self.art.frame(0, 0, False)
        start = W + 40 if self.right else -40 - img.get_width()
        mid = W * 0.62 - img.get_width() / 2 if self.right else W * 0.38 - img.get_width() / 2
        x = start + (mid - start) * ease_out_cubic(min(1.0, t / 0.25)) + direction * 30 * t
        img = img.copy()
        img.set_alpha(int(235 * a))
        surf.blit(img, (int(x), int(H / 2 - img.get_height() / 2 - 10)))


# ======================================================================
# Boss intro card
# ======================================================================


class BossIntro:
    """Letterboxed, glitchy title card when a boss (or midboss) shows up."""

    def __init__(self, bdef, short=False):
        self.d = bdef
        self.duration = 1.9 if short else 2.9
        self.t = 0.0
        self.done = False
        col = bdef.color
        self.jp = assets.text(bdef.jp or bdef.name, 36, (255, 236, 236), (60, 0, 10))
        self.jp_r = assets.text(bdef.jp or bdef.name, 36, (255, 30, 60), None)
        self.jp_c = assets.text(bdef.jp or bdef.name, 36, (40, 230, 255), None)
        self.name = assets.text("  ".join(bdef.name.upper().split()), 24, scale_color(col, 1.15), (20, 0, 10))
        self.title = assets.text(bdef.title, 12, (220, 200, 220))
        self.tag = assets.text("MIDBOSS" if short else "BOSS", 12, (255, 60, 80))

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration:
            self.done = True

    def draw(self, surf):
        t, D = self.t, self.duration
        a = ease_out_cubic(min(1.0, t / 0.3)) * (1 - ease_in_cubic(max(0.0, (t - (D - 0.4)) / 0.4)))
        if a <= 0:
            return
        bh = int(40 * a)
        surf.fill((0, 0, 0), (0, 0, W, bh))
        surf.fill((0, 0, 0), (0, H - bh, W, bh))
        cy = H // 2 - 10
        band = pygame.Surface((W, 92), pygame.SRCALPHA)
        band.fill((40, 0, 10, int(180 * a)))
        surf.blit(band, (0, cy - 46))
        col = scale_color(self.d.color, a)
        sweep = int(W * ease_out_cubic(min(1.0, t / 0.5)))
        pygame.draw.line(surf, col, (0, cy - 46), (sweep, cy - 46), 2)
        pygame.draw.line(surf, col, (W - sweep, cy + 45), (W, cy + 45), 2)
        drift = t * 12
        jx = W - 40 - self.jp.get_width() - (1 - ease_out_cubic(min(1.0, t / 0.45))) * -200 - drift
        jy = cy - 42
        glitchy = t < 0.35 or (int(t * 30) % 23 == 0)
        if glitchy:
            surf.blit(self.jp_r, (jx - 3, jy))
            surf.blit(self.jp_c, (jx + 3, jy + 1))
        img = self.jp.copy()
        img.set_alpha(int(255 * a))
        surf.blit(img, (jx, jy))
        nx = 40 + (1 - ease_out_cubic(min(1.0, max(0.0, t - 0.15) / 0.45))) * -300 + drift
        surf.blit(self.name, (nx, cy + 2))
        surf.blit(self.title, (nx + 2, cy + 28))
        surf.blit(self.tag, (nx + 2, cy - 40))


# ======================================================================
# Stage title card
# ======================================================================


class StageTitle:
    def __init__(self, number, name, jp, subtitle="", glyph=""):
        self.number = number
        self.name = name
        self.jp = jp
        self.sub = subtitle
        self.glyph = assets.text(glyph, 120, (120, 10, 30), None) if glyph else None
        self.t = 0.0
        self.done = False

    def update(self, dt):
        self.t += dt
        if self.t > 3.2:
            self.done = True

    def draw(self, surf):
        t = self.t
        a = min(1.0, t / 0.4) * min(1.0, (3.2 - t) / 0.5)
        if a <= 0:
            return
        y = H * 0.36
        if self.glyph is not None:
            g = self.glyph.copy()
            g.set_alpha(int(70 * a))
            surf.blit(g, (W / 2 - g.get_width() / 2 + t * 4, y - 48))
        k = ease_out_back(min(1.0, t / 0.5))
        label = assets.text(self.number, 12, GOLD)
        jp = assets.text(self.jp, 24, TEXT)
        en = assets.text(self.name, 12, TEXT_DIM)
        for img, yy in ((label, y - 24), (jp, y), (en, y + 28)):
            im = img.copy()
            im.set_alpha(int(255 * a))
            if img is jp and k != 1:
                im = pygame.transform.scale(im, (max(1, int(im.get_width() * k)), im.get_height()))
            surf.blit(im, (int(W / 2 - im.get_width() / 2), int(yy)))
        w = int(220 * ease_out_cubic(min(1.0, t / 0.6)))
        pygame.draw.line(surf, scale_color(GOLD, a), (W / 2 - w / 2, y + 25), (W / 2 + w / 2, y + 25))
        if self.sub:
            assets.blit_text(surf, self.sub, (W / 2, y + 46), 12, (200, 180, 220), "midtop", alpha=255 * a)


class MusicToast:
    def __init__(self, name):
        self.img = assets.text(f"♪ {name}", 12, TEXT)
        self.t = 0.0
        self.done = False

    def update(self, dt):
        self.t += dt
        if self.t > 4.0:
            self.done = True

    def draw(self, surf):
        t = self.t
        if t < 0.4:
            k = ease_out_cubic(t / 0.4)
        elif t > 3.5:
            k = 1 - ease_in_cubic((t - 3.5) / 0.5)
        else:
            k = 1.0
        x = W - 8 - self.img.get_width() * k
        surf.blit(self.img, (int(x), H - 20))
