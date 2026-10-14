"""Scene base class and a reusable vertical menu widget."""

import math
import random

import pygame

from . import assets
from .config import GOLD, TEXT, TEXT_DIM
from .util import ease_out_back, ease_out_cubic


class Scene:
    transparent = False  # draw the scene below this one first

    def __init__(self, app):
        self.app = app

    def enter(self):
        pass

    def exit(self):
        pass

    def resume(self):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def handle_event(self, e):
        pass

    def shake_offset(self):
        return 0, 0

    def sfx(self, name):
        self.app.audio.play(name)


class MenuItem:
    def __init__(self, label, action=None, enabled=True, value=None, adjust=None, sub=""):
        self.label = label
        self.action = action
        self.enabled = enabled
        self.value = value  # callable -> str shown on the right
        self.adjust = adjust  # callable(direction)
        self.sub = sub
        self.anim = 0.0


class Menu:
    """Vertical menu with a sliding, glowing selection bar, a staggered
    slide-in on open and sparkles + a shockwave when an item is picked."""

    def __init__(self, app, items, x, y, spacing=18, size=12, align="left", width=0, intro=0.0):
        self.app = app
        self.items = items
        self.index = 0
        self.x, self.y = x, y
        self.spacing = spacing
        self.size = size
        self.align = align
        self.width = width
        self.t = 0.0
        self.intro = intro  # delay before the items slide in
        self.sparks = []  # [x, y, vx, vy, life]
        self.pulse = 0.0  # flash of the bar after a confirm
        while not self.items[self.index].enabled:
            self.index = (self.index + 1) % len(self.items)
        self.bar_y = float(self.y + self.index * self.spacing)

    def _appear(self, i):
        """0..1 slide-in progress of item i."""
        return ease_out_cubic((self.t - self.intro - i * 0.055) / 0.35)

    def update(self, dt):
        inp = self.app.input
        self.t += dt
        n = len(self.items)
        moved = 0
        if inp.menu("down"):
            moved = 1
        elif inp.menu("up"):
            moved = -1
        if moved:
            for _ in range(n):
                self.index = (self.index + moved) % n
                if self.items[self.index].enabled:
                    break
            self.app.audio.play("move")
        item = self.items[self.index]
        if item.adjust:
            if inp.menu("left"):
                item.adjust(-1)
                self.app.audio.play("menu_move")
            elif inp.menu("right"):
                item.adjust(1)
                self.app.audio.play("menu_move")
        if inp.was_pressed("confirm") and item.action and item.enabled:
            self.app.audio.play("select")
            self._confirm_fx()
            item.action()
        for i, it in enumerate(self.items):
            target = 1.0 if i == self.index else 0.0
            it.anim += (target - it.anim) * min(1.0, dt * 14)
        target_y = self.y + self.index * self.spacing
        self.bar_y += (target_y - self.bar_y) * min(1.0, dt * 18)
        self.pulse = max(0.0, self.pulse - dt * 3)
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[3] += 30 * dt
            sp[4] -= dt
        self.sparks = [sp for sp in self.sparks if sp[4] > 0]
        if random.random() < 0.35:
            x0 = self.x - 14 if self.align == "left" else self.x - 60
            self.sparks.append([x0 + random.uniform(0, 110), self.bar_y + random.uniform(2, self.size),
                                random.uniform(-8, 8), random.uniform(-22, -8), random.uniform(0.4, 0.9)])

    def _confirm_fx(self):
        self.pulse = 1.0
        cy = self.bar_y + self.size / 2 + 2
        cx = self.x + 40 if self.align == "left" else self.x
        for _ in range(16):
            a = random.uniform(0, math.tau)
            sp = random.uniform(40, 130)
            self.sparks.append([cx + random.uniform(-40, 40), cy, math.cos(a) * sp, math.sin(a) * sp * 0.5,
                                random.uniform(0.3, 0.7)])
        fx = self.app.fx
        fx.punch(0.2, cx, cy)
        self.app.post.aberration(6, 1)

    def _draw_bar(self, surf, alpha):
        it = self.items[self.index]
        label_w = assets.text(it.label, self.size).get_width()
        y = int(self.bar_y) - 1
        h = self.size + 6
        if self.align == "left":
            x0 = self.x - 18
            w = max(label_w + 150, self.width + 40 if self.width else 0)
        else:
            w = label_w + 80
            x0 = self.x - w // 2
        a = alpha / 255
        k = 0.75 + 0.25 * math.sin(self.t * 5) + self.pulse * 0.6
        bar = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(w):
            if self.align == "left":
                f = (1 - i / w) ** 1.3
            else:
                f = 1 - abs(i / w - 0.5) * 2
            bar.fill((200, 30, 80, int(190 * f * a * min(1.0, k))), (i, 0, 1, h))
        # A bright sweep running along the bar.
        sweep = (self.t * 0.9) % 1.6 - 0.3
        sx = int(sweep * w)
        for i in range(-10, 11):
            if 0 <= sx + i < w:
                bar.fill((255, 170, 200, int(110 * (1 - abs(i) / 10) * a)), (sx + i, 0, 1, h), special_flags=pygame.BLEND_RGBA_ADD)
        surf.blit(bar, (x0, y))
        edge = (255, 140, 170) if self.pulse < 0.3 else (255, 255, 255)
        if self.align == "left":
            surf.fill(edge, (x0, y, 2, h))
        line = pygame.Surface((int(w * 0.85), 1), pygame.SRCALPHA)
        for i in range(line.get_width()):
            line.fill((255, 120, 160, int(255 * a * (1 - i / line.get_width()))), (i, 0, 1, 1))
        surf.blit(line, (x0, y + h))
        lights = self.app.fx.lights
        lights.add(x0 + 30, y + h / 2, 70 + 40 * self.pulse, (255, 70, 120), 0.5 + 0.4 * self.pulse)

    def draw(self, surf, alpha=255):
        self._draw_bar(surf, alpha * self._appear(self.index))
        for sp in self.sparks:
            c = int(255 * min(1.0, sp[4] * 2))
            surf.fill((255, c // 2 + 120, min(255, c // 2 + 150)), (int(sp[0]), int(sp[1]), 1, 1))
        for i, it in enumerate(self.items):
            k = self._appear(i)
            if k <= 0:
                continue
            a = alpha * k
            slide = (1 - k) * -50
            y = self.y + i * self.spacing
            sel = i == self.index
            if not it.enabled:
                col = (90, 80, 105)
            elif sel:
                col = GOLD
            else:
                col = TEXT
            offset = it.anim * 8 + slide
            label = it.label
            if self.align == "left":
                x = self.x + offset
                if sel and it.enabled:
                    # Selected label: each glyph rides a small wave.
                    r = self._wave_text(surf, label, x, y, col, a)
                else:
                    r = assets.blit_text(surf, label, (x, y), self.size, col, "topleft", alpha=a)
                if it.value:
                    val = it.value()
                    vx = self.x + self.width + slide if self.width else r.right + 12
                    shown = f"◀ {val} ▶" if sel and it.adjust else val
                    assets.blit_text(surf, shown, (vx, y), self.size, col if sel else TEXT_DIM, "topright" if self.width else "topleft", alpha=a)
            else:
                r = assets.blit_text(surf, label, (self.x + slide, y), self.size, col, "midtop", alpha=a)
            if sel and it.enabled:
                bob = math.sin(self.t * 8) * 1.5
                assets.blit_text(surf, "▶", (r.left - 12 + bob, y), self.size, ACCENT_CURSOR, "topleft", alpha=a)
                if it.sub:
                    assets.blit_text(surf, it.sub, (r.right + 10, y), 12, TEXT_DIM, "topleft", alpha=a * min(1.0, it.anim * 1.5))

    def _wave_text(self, surf, label, x, y, col, alpha):
        x0 = x
        h = 0
        for j, ch in enumerate(label):
            img = assets.text(ch, self.size, col)
            if alpha < 255:
                img = img.copy()
                img.set_alpha(int(alpha))
            dy = math.sin(self.t * 7 - j * 0.6) * 1.2
            surf.blit(img, (int(x), int(y + dy)))
            x += img.get_width() - 2
            h = img.get_height()
        return pygame.Rect(int(x0), int(y), int(x - x0 + 2), h)


ACCENT_CURSOR = (255, 90, 130)


def overlay_open(surf, t, title_jp, title_en, color=GOLD, y=50, dim_alpha=160):
    """Animated backdrop for pause-style overlays: the game blurs and darkens,
    two slanted light bands sweep in and the title zooms into place."""
    from . import gfx

    k = ease_out_cubic(min(1.0, t / 0.3))
    surf.blit(gfx.blur(surf, 2 + int(2 * k)), (0, 0))
    dim(surf, int(dim_alpha * k))
    w, h = surf.get_size()
    band = pygame.Surface((w, 34), pygame.SRCALPHA)
    for i in range(34):
        a = int(55 * (1 - abs(i - 17) / 17) ** 1.5 * k)
        band.fill((*color, a), (0, i, w, 1))
    off = (1 - k) * w
    for by, direction in ((y - 4, -1), (y + 26, 1)):
        surf.blit(band, (off * direction, by))
    pygame.draw.line(surf, color, (w / 2 - 150 * k, y + 44), (w / 2 + 150 * k, y + 44))
    sc = 1.6 - 0.6 * ease_out_back(min(1.0, t / 0.35))
    img = assets.text(title_jp, 24, (255, 255, 255))
    if sc != 1:
        img = pygame.transform.scale(img, (max(1, int(img.get_width() * sc)), max(1, int(img.get_height() * sc))))
    img = img.copy()
    img.set_alpha(int(255 * k))
    surf.blit(img, (w / 2 - img.get_width() / 2, y + 12 - img.get_height() / 2))
    spaced = " ".join(title_en)
    assets.blit_text(surf, spaced, (w / 2, y + 30), 12, color, "midtop", alpha=255 * min(1.0, max(0.0, t - 0.12) / 0.3))


def fade_in_alpha(t, dur=0.4):
    return int(255 * ease_out_cubic(min(1.0, t / dur)))


def dim(surf, alpha=150, color=(6, 2, 12)):
    s = pygame.Surface(surf.get_size())
    s.fill(color)
    s.set_alpha(alpha)
    surf.blit(s, (0, 0))
