"""Particles, floating texts, shockwaves, screen shake and flashes."""

import math
import random

import pygame

from . import assets, gfx
from .config import GOLD, OUTLINE, TEXT
from .util import TAU, clamp, ease_out_back, ease_out_cubic, scale_color


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "kind", "drag", "grav", "angle", "spin")

    def __init__(self, x, y, vx, vy, life, size, color, kind, drag, grav):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size, self.color, self.kind = size, color, kind
        self.drag, self.grav = drag, grav
        self.angle = random.uniform(0, TAU)
        self.spin = random.uniform(-6, 6)


class Particles:
    """kinds: 'spark' (additive square), 'glow' (additive soft dot),
    'petal' (alpha sakura petal), 'smoke' (dark puff), 'shard' (white line)."""

    def __init__(self, limit=1400):
        self.items = []
        self.limit = limit

    def emit(self, x, y, vx=0.0, vy=0.0, life=0.6, size=2, color=(255, 255, 255), kind="spark", drag=0.0, grav=0.0):
        if len(self.items) >= self.limit:
            return
        self.items.append(Particle(x, y, vx, vy, life, size, color, kind, drag, grav))

    def burst(self, x, y, n=12, color=(255, 255, 255), speed=(40, 160), life=(0.25, 0.6), size=(1, 3), kind="spark", drag=2.5, grav=0.0):
        for _ in range(n):
            a = random.uniform(0, TAU)
            s = random.uniform(*speed)
            self.emit(
                x,
                y,
                math.cos(a) * s,
                math.sin(a) * s,
                random.uniform(*life),
                random.randint(*size) if isinstance(size, tuple) else size,
                color,
                kind,
                drag,
                grav,
            )

    def update(self, dt):
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            if p.drag:
                k = max(0.0, 1 - p.drag * dt)
                p.vx *= k
                p.vy *= k
            p.vy += p.grav * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.angle += p.spin * dt
            alive.append(p)
        self.items = alive

    def draw(self, surf, add):
        for p in self.items:
            t = p.life / p.max_life
            if p.kind == "spark":
                c = scale_color(p.color, t * 1.2)
                s = max(1, int(p.size * (0.5 + t * 0.5)))
                add.fill(c, (int(p.x - s / 2), int(p.y - s / 2), s, s), special_flags=pygame.BLEND_ADD)
            elif p.kind == "glow":
                gfx.blit_glow(add, p.x, p.y, max(2, int(p.size * (0.4 + 0.6 * t))), p.color, t)
            elif p.kind == "petal":
                c = p.color
                w = max(1, int(abs(math.cos(p.angle)) * p.size) + 1)
                pygame.draw.ellipse(surf, c, (int(p.x), int(p.y), w, max(1, p.size - 1)))
            elif p.kind == "smoke":
                r = max(1, int(p.size * (1.6 - t)))
                pygame.draw.circle(surf, scale_color(p.color, 0.6 + 0.4 * t), (int(p.x), int(p.y)), r)
            elif p.kind == "shard":
                length = p.size * 2
                dx, dy = math.cos(p.angle) * length, math.sin(p.angle) * length
                pygame.draw.line(add, scale_color(p.color, t), (p.x - dx, p.y - dy), (p.x + dx, p.y + dy), 1)

    def clear(self):
        self.items.clear()


class FloatText:
    __slots__ = ("surf", "x", "y", "vy", "life", "max_life", "pop")

    def __init__(self, surf, x, y, life, vy, pop):
        self.surf, self.x, self.y = surf, x, y
        self.life = self.max_life = life
        self.vy = vy
        self.pop = pop


class FloatTexts:
    def __init__(self):
        self.items = []

    def add(self, s, x, y, color=TEXT, size=12, life=0.9, vy=-28, pop=True, outline=OUTLINE):
        surf = assets.text(s, size, color, outline)
        self.items.append(FloatText(surf, x, y, life, vy, pop))
        if len(self.items) > 60:
            self.items.pop(0)

    def update(self, dt):
        for f in self.items:
            f.life -= dt
            f.y += f.vy * dt
            f.vy *= max(0.0, 1 - 3 * dt)
        self.items = [f for f in self.items if f.life > 0]

    def draw(self, surf):
        for f in self.items:
            age = f.max_life - f.life
            img = f.surf
            if f.pop and age < 0.18:
                k = 0.4 + 0.6 * ease_out_back(age / 0.18)
                img = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            if f.life < 0.3:
                img = img.copy() if img is f.surf else img
                img.set_alpha(int(255 * f.life / 0.3))
            surf.blit(img, (int(f.x - img.get_width() / 2), int(f.y - img.get_height() / 2)))

    def clear(self):
        self.items.clear()


class Wave:
    __slots__ = ("x", "y", "r0", "r1", "life", "max_life", "color", "width")

    def __init__(self, x, y, r0, r1, life, color, width):
        self.x, self.y, self.r0, self.r1 = x, y, r0, r1
        self.life = self.max_life = life
        self.color, self.width = color, width


class Shockwaves:
    def __init__(self):
        self.items = []

    def add(self, x, y, r1=60, life=0.4, color=(255, 255, 255), width=3, r0=2):
        self.items.append(Wave(x, y, r0, r1, life, color, width))

    def update(self, dt):
        for w in self.items:
            w.life -= dt
        self.items = [w for w in self.items if w.life > 0]

    def draw(self, add):
        for w in self.items:
            t = 1 - w.life / w.max_life
            r = w.r0 + (w.r1 - w.r0) * ease_out_cubic(t)
            width = max(1, int(w.width * (1 - t) + 0.5))
            gfx.ring(add, w.x, w.y, r, w.color, width, 1 - t)

    def clear(self):
        self.items.clear()


class Shake:
    def __init__(self):
        self.amount = 0.0
        self.scale = 1.0

    def add(self, amount):
        self.amount = min(14.0, max(self.amount, amount))

    def update(self, dt):
        self.amount = max(0.0, self.amount - dt * 30 * (0.4 + self.amount / 10))

    def offset(self):
        a = self.amount * self.scale
        if a < 0.5:
            return 0, 0
        return int(random.uniform(-a, a)), int(random.uniform(-a, a))


class Flash:
    def __init__(self):
        self.color = (255, 255, 255)
        self.alpha = 0.0
        self.decay = 600.0

    def trigger(self, color=(255, 255, 255), alpha=180, decay=600):
        self.color = color
        self.alpha = max(self.alpha, alpha)
        self.decay = decay

    def update(self, dt):
        self.alpha = max(0.0, self.alpha - self.decay * dt)

    def draw(self, surf):
        if self.alpha > 1:
            overlay = pygame.Surface(surf.get_size())
            overlay.fill(self.color)
            overlay.set_alpha(int(clamp(self.alpha, 0, 255)))
            surf.blit(overlay, (0, 0))


class Banner:
    """Big centred announcement that slides in, holds, then slides out."""

    def __init__(self, title, subtitle="", color=GOLD, duration=2.4, y=150, size=24):
        self.title = assets.text(title, size, color)
        self.sub = assets.text(subtitle, 12, TEXT) if subtitle else None
        self.t = 0.0
        self.duration = duration
        self.y = y
        self.done = False

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration:
            self.done = True

    def draw(self, surf):
        W = surf.get_width()
        t = self.t
        if t < 0.3:
            k = ease_out_cubic(t / 0.3)
            x_off = (1 - k) * W * 0.6
            alpha = k
        elif t > self.duration - 0.3:
            k = ease_out_cubic((self.duration - t) / 0.3)
            x_off = -(1 - k) * W * 0.6
            alpha = k
        else:
            x_off, alpha = 0, 1
        band_h = 40 if self.sub else 30
        band = pygame.Surface((W, band_h), pygame.SRCALPHA)
        band.fill((10, 4, 20, int(170 * alpha)))
        surf.blit(band, (0, self.y - band_h // 2))
        pygame.draw.line(surf, scale_color(GOLD, alpha), (0, self.y - band_h // 2), (W, self.y - band_h // 2))
        pygame.draw.line(surf, scale_color(GOLD, alpha), (0, self.y + band_h // 2 - 1), (W, self.y + band_h // 2 - 1))
        ty = self.y - (8 if self.sub else 0)
        surf.blit(self.title, (int(W / 2 - self.title.get_width() / 2 + x_off), int(ty - self.title.get_height() / 2)))
        if self.sub:
            surf.blit(self.sub, (int(W / 2 - self.sub.get_width() / 2 - x_off), int(self.y + 11 - self.sub.get_height() / 2)))
