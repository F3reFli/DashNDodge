"""Incidents (異変): chaotic modifiers that hit mid-stage, WarioWare style."""

import math
import random

import pygame

from . import gfx
from .config import FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, H, W
from .util import TAU, clamp


class Actor:
    """A non-hostile character wandering the arena during an incident."""

    def __init__(self, sprite, x, y, scale=2):
        self.art = gfx.CharArt.get(sprite, scale)
        self.x, self.y = x, y
        self.tx, self.ty = x, y
        self.speed = 120
        self.t = random.uniform(0, 5)
        self.lean = 0
        self.alpha = 255
        self.gone = False

    def update(self, dt):
        self.t += dt
        dx, dy = self.tx - self.x, self.ty - self.y
        d = math.hypot(dx, dy)
        if d > 1:
            step = min(d, self.speed * dt)
            self.x += dx / d * step
            self.y += dy / d * step
            self.lean = 1 if dx > 2 else -1 if dx < -2 else 0
        else:
            self.lean = 0

    def at_target(self):
        return math.hypot(self.tx - self.x, self.ty - self.y) < 3

    def draw(self, surf):
        self.art.draw(surf, self.x, self.y + math.sin(self.t * 3) * 2, self.t, self.lean, self.lean != 0, alpha=self.alpha)


class Incident:
    id = ""
    who = ""
    sprite = ""
    title = ""
    desc = ""
    color = (255, 255, 255)
    duration = 15.0

    def __init__(self, g):
        self.g = g
        self.t = 0
        self.frames = int(self.duration * 60)
        self.actors = []

    @property
    def remaining(self):
        return max(0.0, 1 - self.t / self.frames)

    def start(self):
        pass

    def update(self):
        self.t += 1
        for a in self.actors:
            a.update(1 / 60)
        return self.t < self.frames

    def end(self):
        pass

    def draw(self, surf, add):
        for a in self.actors:
            a.draw(surf)

    def overlay(self, surf):
        pass

    def post(self, surf):
        return surf

    def actor_from_edge(self, sprite):
        side = random.choice(("left", "right"))
        x = -20 if side == "left" else W + 20
        a = Actor(sprite, x, random.uniform(80, H - 80))
        self.actors.append(a)
        return a


# ----------------------------------------------------------------------


class ReverseIdeology(Incident):
    id = "seija"
    who = "Seija Kijin"
    sprite = "Seija Kijin"
    title = "Reverse Ideology!"
    desc = "Seija flipped the world. Left is right. Up is... wait."
    color = (255, 90, 110)
    duration = 14.0

    def start(self):
        a = self.actor_from_edge(self.sprite)
        a.tx, a.ty = W / 2, 60
        self.g.texts.add("Everything's upside down~!", W / 2, 90, self.color, 12, 2.0)

    def update(self):
        if self.t == self.frames // 2:
            self.g.texts.add("...and now the other way!", W / 2, H / 2, self.color, 12, 1.6)
            self.g.sfx("boing")
        if self.actors:
            a = self.actors[0]
            if a.at_target():
                a.tx = random.uniform(80, W - 80)
                a.ty = random.uniform(50, 120)
        return super().update()

    def post(self, surf):
        vertical = self.t >= self.frames // 2
        return pygame.transform.flip(surf, not vertical, vertical)


class DrunkenHaze(Incident):
    id = "suika"
    who = "Suika Ibuki"
    sprite = "Suika Ibuki"
    title = "Drunken Haze!"
    desc = "Suika spiked the air with sake. Everything's spinning~"
    color = (255, 170, 90)
    duration = 14.0

    def start(self):
        a = self.actor_from_edge(self.sprite)
        a.tx, a.ty = W / 2, H - 50
        a.speed = 70

    def update(self):
        p = self.g.player
        k = min(1.0, self.t / 60) * min(1.0, (self.frames - self.t) / 60)
        if p.alive and p.dash_t == 0:
            p.x = clamp(p.x + math.sin(self.t * 0.035) * 0.55 * k, FIELD_LEFT, FIELD_RIGHT)
            p.y = clamp(p.y + math.cos(self.t * 0.027) * 0.35 * k, FIELD_TOP + 6, FIELD_BOTTOM)
        if self.t % 90 == 0 and self.actors:
            self.g.texts.add(random.choice(("*hic*", "One more cup~", "*hic* Ehehe")), self.actors[0].x, self.actors[0].y - 24, self.color, 12, 1.2)
        return super().update()

    def post(self, surf):
        k = min(1.0, self.t / 60) * min(1.0, (self.frames - self.t) / 60)
        angle = math.sin(self.t * 0.03) * 5 * k
        zoom = 1.0 + 0.09 * k
        out = pygame.transform.rotozoom(surf, angle, zoom)
        res = pygame.Surface((W, H))
        res.blit(out, (W / 2 - out.get_width() / 2 + math.sin(self.t * 0.05) * 6 * k, H / 2 - out.get_height() / 2))
        return res


class ClosedEye(Incident):
    id = "koishi"
    who = "Koishi Komeiji"
    sprite = "Koishi Komeiji"
    title = "Closed Eye!"
    desc = "Koishi made the bullets shy. You only see them up close."
    color = (120, 230, 140)
    duration = 13.0

    def update(self):
        p = self.g.player
        r = 62 + 6 * math.sin(self.t * 0.08)
        self.g.visible = (p.x, p.y, r)
        if self.t % 120 == 30:
            # Koishi pops up somewhere random, giggles, vanishes.
            self.actors = [Actor(self.sprite, random.uniform(80, W - 80), random.uniform(60, H - 60))]
            self.g.texts.add("Hehe~", self.actors[0].x, self.actors[0].y - 22, self.color, 12, 1.0)
        for a in self.actors:
            a.alpha = max(0, a.alpha - 4)
        return super().update()

    def end(self):
        self.g.visible = None

    def draw(self, surf, add):
        super().draw(surf, add)
        if self.g.visible:
            x, y, r = self.g.visible
            gfx.ring(add, x, y, r, (60, 140, 80), 1)


class BottomlessAppetite(Incident):
    id = "yuyuko"
    who = "Yuyuko Saigyouji"
    sprite = "Yuyuko Saigyouji"
    title = "Bottomless Appetite!"
    desc = "Yuyuko smells snacks. Grab the items before she does!"
    color = (255, 150, 200)
    duration = 15.0

    def start(self):
        g = self.g
        self.yu = self.actor_from_edge(self.sprite)
        self.yu.speed = 95
        self.snatch_cd = 0
        for _ in range(14):
            g.items.spawn("point", random.uniform(60, W - 60), random.uniform(60, H - 60), spread=0.3)
        for _ in range(3):
            g.items.spawn("big", random.uniform(60, W - 60), random.uniform(60, H - 60), spread=0.3)
        g.items.spawn("heart", random.uniform(100, W - 100), random.uniform(80, H - 80), spread=0.3)
        for it in g.items.items:
            it.life = max(it.life, 13.0)
        g.texts.add("Feast time~!", W / 2, 80, self.color, 12, 1.8)

    def update(self):
        g = self.g
        yu = self.yu
        food = [it for it in g.items.items if it.kind in ("point", "big", "heart", "spell") and not it.auto]
        if food:
            target = min(food, key=lambda it: (it.x - yu.x) ** 2 + (it.y - yu.y) ** 2)
            yu.tx, yu.ty = target.x, target.y
            if (target.x - yu.x) ** 2 + (target.y - yu.y) ** 2 < 12 ** 2:
                target.dead = True
                g.sfx("chomp")
                g.texts.add("nom", yu.x, yu.y - 20, self.color, 12, 0.6)
        elif yu.at_target():
            yu.tx, yu.ty = random.uniform(60, W - 60), random.uniform(60, H - 60)
        if self.t % 70 == 0:
            for k in range(3):
                g.bullets.shoot(yu.x, yu.y, 60 * g.speed_mult, random.uniform(0, TAU), "butterfly", "pink")
        p = g.player
        if self.snatch_cd > 0:
            self.snatch_cd -= 1
        elif p.dashing() and (p.x - yu.x) ** 2 + (p.y - yu.y) ** 2 < 22 ** 2:
            self.snatch_cd = 60
            g.items.spawn("big", yu.x, yu.y, 3)
            g.texts.add("Hey! My snack!", yu.x, yu.y - 24, self.color, 12, 1.2)
            g.sfx("boing")
        return super().update()


class LuckyRabbit(Incident):
    id = "tewi"
    who = "Tewi Inaba"
    sprite = "Tewi Inaba"
    title = "Lucky Rabbit?"
    desc = "Free hearts! ...Some of them might be a teeny bit fake."
    color = (255, 190, 210)
    duration = 13.0

    def start(self):
        g = self.g
        self.tewi = self.actor_from_edge(self.sprite)
        self.tewi.tx, self.tewi.ty = W / 2, 70
        kinds = ["heart", "heart", "fake_heart", "fake_heart", "fake_heart"]
        random.shuffle(kinds)
        for i, k in enumerate(kinds):
            x = 90 + i * (W - 180) / 4
            y = random.uniform(120, H - 60)
            g.items.spawn(k, x, y, spread=0.1)

    def update(self):
        a = self.tewi
        if a.at_target():
            a.tx = random.uniform(60, W - 60)
            a.ty = random.uniform(40, 100)
        return super().update()


def tewi_trap(g, x, y):
    """Called when a fake heart is picked up."""
    g.texts.add("Tricked! ♪", x, y - 20, (255, 190, 210), 12, 1.4)
    g.sfx("boing")
    g.player.stun = 30
    g.killer_hint = ("Tewi Inaba", g.frame)
    p = g.player
    n = g.d(10, 14, 18, 22)
    for ring in range(2):
        R = 95 + ring * 30
        for k in range(n):
            a = TAU * k / n + ring * 0.3
            bx, by = p.x + math.cos(a) * R, p.y + math.sin(a) * R
            g.bullets.shoot(bx, by, 50 + ring * 15, a + math.pi, "pellet", "pink", accel=25, max_speed=120, grace=90)


class IceAge(Incident):
    id = "cirno"
    who = "Cirno"
    sprite = "Cirno"
    title = "Ice Age ⑨!"
    desc = "The floor froze solid. Slippery! But every point is worth ⑨x!"
    color = (120, 220, 255)
    duration = 14.0

    def start(self):
        g = self.g
        g.ice = True
        g.score_mult = 9
        a = self.actor_from_edge(self.sprite)
        a.tx, a.ty = W / 2, 50
        g.texts.add("I'm the strongest!", W / 2, 80, self.color, 12, 1.6)

    def update(self):
        g = self.g
        if self.t % 6 == 0:
            g.particles.emit(random.uniform(0, W), -4, random.uniform(-15, 15), random.uniform(30, 60), 6.0, 2, (220, 240, 255), "spark")
        if self.actors and self.actors[0].at_target():
            self.actors[0].tx = random.uniform(80, W - 80)
        return super().update()

    def end(self):
        self.g.ice = False
        self.g.score_mult = 1

    def overlay(self, surf):
        tint = pygame.Surface((W, H))
        tint.fill((20, 50, 70))
        surf.blit(tint, (0, 0), special_flags=pygame.BLEND_ADD)


class BreakingNews(Incident):
    id = "aya"
    who = "Aya Shameimaru"
    sprite = "Aya Shameimaru"
    title = "Breaking News!"
    desc = "Aya wants a scoop. Stay out of the camera frame!"
    color = (255, 120, 90)
    duration = 15.0

    def start(self):
        self.aya = self.actor_from_edge(self.sprite)
        self.aya.speed = 380
        self.frames_list = []  # [x, y, w, h, timer]
        self.next_shot = 50

    def update(self):
        g = self.g
        p = g.player
        aya = self.aya
        if aya.at_target():
            aya.tx = random.uniform(40, W - 40)
            aya.ty = random.uniform(40, H - 40)
        self.next_shot -= 1
        if self.next_shot <= 0 and self.t < self.frames - 60:
            w, h = random.choice(((110, 80), (140, 90), (90, 120)))
            x = clamp(p.x + random.uniform(-30, 30), w / 2, W - w / 2)
            y = clamp(p.y + random.uniform(-25, 25), h / 2 + 20, H - h / 2)
            self.frames_list.append([x, y, w, h, g.d(60, 50, 44, 38)])
            self.next_shot = g.d(80, 65, 55, 45)
            aya.tx, aya.ty = x + random.choice((-1, 1)) * (w / 2 + 30), y
        for fr in self.frames_list:
            fr[4] -= 1
            if fr[4] == 0:
                x, y, w, h, _ = fr
                rect = pygame.Rect(int(x - w / 2), int(y - h / 2), int(w), int(h))
                g.sfx("camera")
                g.photo_flashes.append([rect, 12])
                g.bullets.cancel([b for b in g.bullets.items if rect.collidepoint(b.x, b.y)])
                if rect.collidepoint(p.x, p.y) and p.alive:
                    p.stun = 26
                    g.stats["photos"] += 1
                    g.texts.add("SCOOP!", p.x, p.y - 22, self.color, 12, 1.2)
                    g.flash.trigger((255, 255, 255), 120, 500)
        self.frames_list = [f for f in self.frames_list if f[4] > 0]
        return super().update()

    def draw(self, surf, add):
        super().draw(surf, add)
        for x, y, w, h, timer in self.frames_list:
            col = (255, 255, 255) if timer < 12 and timer % 4 < 2 else (255, 110, 90)
            r = pygame.Rect(int(x - w / 2), int(y - h / 2), int(w), int(h))
            L = 10
            for cx, cy, dx, dy in ((r.left, r.top, 1, 1), (r.right - 1, r.top, -1, 1), (r.left, r.bottom - 1, 1, -1), (r.right - 1, r.bottom - 1, -1, -1)):
                pygame.draw.line(surf, col, (cx, cy), (cx + dx * L, cy), 2)
                pygame.draw.line(surf, col, (cx, cy), (cx, cy + dy * L), 2)
            pygame.draw.line(surf, col, (r.centerx - 4, r.centery), (r.centerx + 4, r.centery))
            pygame.draw.line(surf, col, (r.centerx, r.centery - 4), (r.centerx, r.centery + 4))
            if timer < 30:
                pygame.draw.circle(surf, (255, 60, 60), (r.right - 8, r.top + 8), 2)


class BoundaryOfWrap(Incident):
    id = "yukari"
    who = "Yukari Yakumo"
    sprite = "Yukari Yakumo"
    title = "Boundary of Wrap!"
    desc = "Yukari opened gaps at the edges. Everything loops around!"
    color = (200, 120, 255)
    duration = 14.0

    def start(self):
        self.g.wrap = True
        a = self.actor_from_edge(self.sprite)
        a.tx, a.ty = W / 2, H / 2
        a.speed = 60
        self.g.texts.add("Ufufu~", W / 2, H / 2 - 30, self.color, 12, 1.6)

    def update(self):
        if self.t == 90 and self.actors:
            self.actors[0].tx = W + 40
        return super().update()

    def end(self):
        self.g.wrap = False

    def draw(self, surf, add):
        super().draw(surf, add)
        t = self.t
        for i in range(0, W, 24):
            o = math.sin(t * 0.05 + i * 0.1) * 2
            pygame.draw.ellipse(add, (90, 30, 120), (i + 4, 1 + o, 14, 5))
            pygame.draw.ellipse(add, (90, 30, 120), (i + 4, H - 6 + o, 14, 5))
        for j in range(0, H, 24):
            o = math.sin(t * 0.05 + j * 0.1) * 2
            pygame.draw.ellipse(add, (90, 30, 120), (1 + o, j + 4, 5, 14))
            pygame.draw.ellipse(add, (90, 30, 120), (W - 6 + o, j + 4, 5, 14))


class FiveFingerDiscount(Incident):
    id = "marisa"
    who = "Marisa Kirisame"
    sprite = "Marisa Kirisame"
    title = "Five-Finger Discount!"
    desc = "Marisa is 'borrowing' your spell power. Dash into her to take it back!"
    color = (255, 220, 90)
    duration = 15.0

    def start(self):
        self.ma = self.actor_from_edge(self.sprite)
        self.ma.speed = 150
        self.loot = 0.0
        self.cool = 0

    def update(self):
        g = self.g
        p = g.player
        ma = self.ma
        if self.cool > 0:
            self.cool -= 1
            if ma.at_target():
                ma.tx, ma.ty = random.uniform(60, W - 60), random.uniform(50, H - 50)
        else:
            ma.tx, ma.ty = p.x, p.y
            ma.speed = 150 + 40 * math.sin(self.t * 0.05)
        if self.t % 40 == 0:
            g.bullets.shoot(ma.x, ma.y, 70 * g.speed_mult, random.uniform(0, TAU), "star", "yellow")
        d2 = (p.x - ma.x) ** 2 + (p.y - ma.y) ** 2
        if d2 < 18 ** 2 and p.alive:
            if p.dashing() and self.loot > 0:
                p.spell = min(p.max_spell, p.spell + self.loot * 1.5)
                g.add_score(20000, ma.x, ma.y - 20, show=True)
                g.texts.add("Hey, that's mine-- ow!", ma.x, ma.y - 34, self.color, 12, 1.2)
                g.sfx("heal")
                self.loot = 0
                self.cool = 120
            elif not p.dashing() and self.cool == 0:
                stolen = min(50.0, p.spell)
                if stolen > 0:
                    p.spell -= stolen
                    self.loot += stolen
                    g.texts.add("Just borrowing it, ze!", ma.x, ma.y - 24, self.color, 12, 1.4)
                    g.sfx("steal")
                else:
                    g.texts.add("You're broke, ze...", ma.x, ma.y - 24, self.color, 12, 1.2)
                self.cool = 150
                ma.tx = random.uniform(60, W - 60)
                ma.ty = random.uniform(50, H - 50)
        return super().update()

    def draw(self, surf, add):
        super().draw(surf, add)
        if self.loot > 0:
            img = gfx.star_icon()
            surf.blit(img, (int(self.ma.x - 4), int(self.ma.y - 30)))


ALL = [ReverseIdeology, DrunkenHaze, ClosedEye, BottomlessAppetite, LuckyRabbit, IceAge, BreakingNews, BoundaryOfWrap, FiveFingerDiscount]
BY_ID = {c.id: c for c in ALL}
