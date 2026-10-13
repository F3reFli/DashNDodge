"""Scene base class and a reusable vertical menu widget."""

import math

import pygame

from . import assets
from .config import GOLD, TEXT, TEXT_DIM
from .util import ease_out_cubic


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
    def __init__(self, app, items, x, y, spacing=18, size=12, align="left", width=0):
        self.app = app
        self.items = items
        self.index = 0
        self.x, self.y = x, y
        self.spacing = spacing
        self.size = size
        self.align = align
        self.width = width
        self.t = 0.0
        while not self.items[self.index].enabled:
            self.index = (self.index + 1) % len(self.items)

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
            item.action()
        for i, it in enumerate(self.items):
            target = 1.0 if i == self.index else 0.0
            it.anim += (target - it.anim) * min(1.0, dt * 14)

    def draw(self, surf, alpha=255):
        for i, it in enumerate(self.items):
            y = self.y + i * self.spacing
            sel = i == self.index
            if not it.enabled:
                col = (90, 80, 105)
            elif sel:
                col = GOLD
            else:
                col = TEXT
            offset = it.anim * 8
            label = it.label
            if it.value:
                label = f"{it.label}"
            if self.align == "left":
                x = self.x + offset
                r = assets.blit_text(surf, label, (x, y), self.size, col, "topleft", alpha=alpha)
                if it.value:
                    val = it.value()
                    vx = self.x + self.width if self.width else r.right + 12
                    shown = f"◀ {val} ▶" if sel and it.adjust else val
                    assets.blit_text(surf, shown, (vx, y), self.size, col if sel else TEXT_DIM, "topright" if self.width else "topleft", alpha=alpha)
            else:
                r = assets.blit_text(surf, label, (self.x, y), self.size, col, "midtop", alpha=alpha)
            if sel and it.enabled:
                bob = math.sin(self.t * 8) * 1.5
                assets.blit_text(surf, "▶", (r.left - 12 + bob, y), self.size, ACCENT_CURSOR, "topleft", alpha=alpha)
                if it.sub:
                    assets.blit_text(surf, it.sub, (r.right + 10, y), 12, TEXT_DIM, "topleft", alpha=alpha)


ACCENT_CURSOR = (255, 90, 130)


def fade_in_alpha(t, dur=0.4):
    return int(255 * ease_out_cubic(min(1.0, t / dur)))


def dim(surf, alpha=150, color=(6, 2, 12)):
    s = pygame.Surface(surf.get_size())
    s.fill(color)
    s.set_alpha(alpha)
    surf.blit(s, (0, 0))
