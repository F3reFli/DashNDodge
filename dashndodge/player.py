"""The player: movement, focus, dash, parry, spell activation, damage."""

import math
import random

import pygame

from . import gfx
from .config import FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, H, W
from .util import clamp, scale_color

BASE_SPEED = 160.0
FOCUS_MULT = 0.45
DASH_FRAMES = 9
DASH_SPEED = 560.0
DEATHBOMB_FRAMES = 9
HIT_IFRAMES = 120
NAP_FRAMES = 60 * 5


class Player:
    def __init__(self, game, cdef):
        self.game = game
        self.c = cdef
        self.art = gfx.CharArt.get(cdef.sprite, 2)
        self.x, self.y = W / 2, H * 0.72
        self.alive = True
        self.max_hearts = cdef.hearts
        self.hearts = cdef.hearts
        self.spell = 100.0
        self.max_spell = 300.0
        self.speed = BASE_SPEED * cdef.speed
        self.hit_r = cdef.hitbox
        self.graze_r = 18 * cdef.graze
        self.magnet_r = 34 * cdef.magnet
        self.max_charges = cdef.dash_charges
        self.charges = cdef.dash_charges
        self.dash_cd = 0
        self.dash_t = 0
        self.dash_dir = (0.0, -1.0)
        self.dash_id = 0
        self.iframes = 60
        self.parry_t = 0
        self.parry_cd = 0
        self.parry_hits = 0
        self.focus = False
        self.facing = (0.0, -1.0)
        self.vx = self.vy = 0.0
        self.t = 0.0
        self.lean = 0
        self.moving = False
        self.hit_pending = 0
        self.stun = 0
        self.squash = 0.0
        self.squash_axis = (1.0, 1.0)
        self.afterimages = []
        self.idle = 0
        self.asleep = False
        self.zzz_t = 0
        self.spell_cd = 0
        # Run-modifiable stats (omamori charms change these).
        self.parry_window = cdef.parry_window
        self.parry_r = cdef.parry_r
        self.dash_cd_mult = 1.0
        self.spell_gain = 1.0
        self.reflect_mult = 1.0
        self.dash_dmg_mult = 1.0
        self.item_mult = 1.0
        self.heart_luck = 1.0
        self.focus_slow = False
        self.regen_capture = False
        self.charms = []

    # ------------------------------------------------------------------
    def vulnerable(self):
        return self.alive and self.iframes <= 0 and self.dash_t <= 0 and self.hit_pending <= 0

    def dashing(self):
        return self.dash_t > 0

    def update(self, inp, dt):
        g = self.game
        self.t += dt
        if not self.alive:
            return
        if self.iframes > 0:
            self.iframes -= 1
        if self.parry_cd > 0:
            self.parry_cd -= 1
        if self.spell_cd > 0:
            self.spell_cd -= 1
        if self.squash > 0:
            self.squash = max(0.0, self.squash - dt * 5)

        # Death-bomb window: a hit only lands if no spell is used right after.
        if self.hit_pending > 0:
            if inp.was_pressed("spell") and self.spell >= 100:
                self.hit_pending = 0
                g.player_spell(deathbomb=True)
                return
            self.hit_pending -= 1
            if self.hit_pending == 0:
                self.take_damage()
            return

        mx, my = inp.move_vector()
        if self.stun > 0:
            self.stun -= 1
            mx = my = 0.0
        self.focus = inp.held("focus")
        moving = abs(mx) > 0.05 or abs(my) > 0.05
        if moving:
            self.facing = (mx, my)
        self._nap(moving, inp)

        # --- dash charges
        if self.charges < self.max_charges:
            self.dash_cd -= 1
            if self.dash_cd <= 0:
                self.charges += 1
                g.particles.burst(self.x, self.y, 6, self.c.color, (20, 60), kind="glow", size=(2, 3))
                if self.charges < self.max_charges:
                    self.dash_cd = int(self.c.dash_cd * 60 * self.dash_cd_mult)

        if inp.was_pressed("dash") and self.charges > 0 and self.dash_t == 0 and self.stun == 0:
            self.start_dash(mx, my)

        if inp.was_pressed("parry") and self.parry_cd == 0 and self.parry_t == 0:
            self.parry_t = self.parry_window
            self.parry_hits = 0
            g.sfx("blip")

        if inp.was_pressed("spell") and self.spell_cd == 0:
            g.player_spell()

        # --- movement
        if self.dash_t > 0:
            self.dash_t -= 1
            dx, dy = self.dash_dir
            self.x += dx * DASH_SPEED * dt
            self.y += dy * DASH_SPEED * dt
            self.afterimages.append([self.x, self.y, 0.25])
            if self.dash_t == 0:
                self.squash = 0.6
                self.squash_axis = (1.25, 0.8)
        else:
            sp = self.speed * (FOCUS_MULT if self.focus else 1.0)
            if g.timestop > 0 and g.timestop_owner == "boss":
                sp *= 0.5
            if g.ice:
                accel = 2.2 * dt
                self.vx += (mx * sp - self.vx) * accel
                self.vy += (my * sp - self.vy) * accel
            else:
                self.vx, self.vy = mx * sp, my * sp
            self.x += self.vx * dt
            self.y += self.vy * dt

        self.lean = 1 if self.vx > 20 else -1 if self.vx < -20 else 0
        self.moving = moving or self.dash_t > 0
        if g.wrap:
            if self.x < FIELD_LEFT - 6:
                self.x = FIELD_RIGHT + 4
            elif self.x > FIELD_RIGHT + 6:
                self.x = FIELD_LEFT - 4
            if self.y < FIELD_TOP - 6:
                self.y = FIELD_BOTTOM + 4
            elif self.y > FIELD_BOTTOM + 6:
                self.y = FIELD_TOP - 4
        else:
            nx = clamp(self.x, FIELD_LEFT, FIELD_RIGHT)
            ny = clamp(self.y, FIELD_TOP + 6, FIELD_BOTTOM)
            if g.ice and (nx != self.x):
                self.vx = -self.vx * 0.5
            if g.ice and (ny != self.y):
                self.vy = -self.vy * 0.5
            self.x, self.y = nx, ny

        # --- parry window
        if self.parry_t > 0:
            n = g.try_parry(self)
            self.parry_hits += n
            self.parry_t -= 1
            if self.parry_t == 0:
                if self.parry_hits == 0:
                    self.parry_cd = 48
                    g.sfx("parry_fail")
                else:
                    self.parry_cd = 8

        for a in self.afterimages:
            a[2] -= dt
        self.afterimages = [a for a in self.afterimages if a[2] > 0]

    def _nap(self, moving, inp):
        if self.c.id != "meiling":
            return
        busy = moving or any(inp.held(a) for a in ("dash", "parry", "spell", "focus"))
        if busy:
            if self.asleep:
                self.asleep = False
                self.game.texts.add("I'm awake!!", self.x, self.y - 22, (255, 220, 120), 12, 1.0)
            self.idle = 0
            return
        self.idle += 1
        if self.idle == NAP_FRAMES:
            self.asleep = True
            self.game.sfx("zzz")
            self.game.on_meiling_nap()
        if self.asleep:
            self.zzz_t += 1
            if self.zzz_t % 45 == 0:
                self.game.texts.add("z", self.x + 8 + random.uniform(-2, 2), self.y - 16, (200, 220, 255), 12, 1.2, vy=-20)

    def start_dash(self, mx, my):
        g = self.game
        if abs(mx) < 0.05 and abs(my) < 0.05:
            mx, my = self.facing
        mag = math.hypot(mx, my) or 1.0
        self.dash_dir = (mx / mag, my / mag)
        self.dash_t = DASH_FRAMES
        self.dash_id += 1
        self.charges -= 1
        if self.dash_cd <= 0:
            self.dash_cd = int(self.c.dash_cd * 60 * self.dash_cd_mult)
        self.iframes = max(self.iframes, DASH_FRAMES + 5)
        self.squash = 1.0
        self.squash_axis = (0.75, 1.3)
        g.sfx("dash")
        g.waves.add(self.x, self.y, 18, 0.2, self.c.color, 2)
        g.particles.burst(self.x, self.y, 8, (255, 255, 255), (30, 90), kind="spark", size=(1, 2))
        g.stats["dashes"] += 1

    def hit(self, source=None):
        if not self.vulnerable():
            return
        self.hit_pending = DEATHBOMB_FRAMES
        self.game.last_hit_source = source
        self.game.flash.trigger((255, 40, 60), 90, 900)

    def take_damage(self):
        g = self.game
        self.hearts -= 1
        self.iframes = HIT_IFRAMES
        g.on_player_damaged()
        if self.hearts <= 0:
            self.alive = False
            g.on_player_death()
            return
        if self.spell < 100:
            self.spell = min(self.max_spell, self.spell + 35)

    # ------------------------------------------------------------------
    def draw(self, surf, add):
        if not self.alive:
            return
        for x, y, life in self.afterimages:
            img = self.art.tint(self.c.color, int(150 * life / 0.25))
            surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))
        if self.focus:
            gfx.draw_magic_circle(add, self.x, self.y + 2, 26, scale_color(self.c.color, 0.7), self.t * 2.0, 0.8, 6, 1.0)
        blink = self.iframes > 0 and self.dash_t == 0 and (self.iframes // 4) % 2 == 0
        white = self.hit_pending > 0 and (self.hit_pending // 2) % 2 == 0
        if self.squash > 0:
            sx = 1 + (self.squash_axis[0] - 1) * self.squash
            sy = 1 + (self.squash_axis[1] - 1) * self.squash
        else:
            sx = sy = 1.0
        self.art.draw(surf, self.x, self.y, self.t if not self.asleep else 0, self.lean, self.moving, white,
                      (sx, sy), alpha=100 if blink else 255)
        # Dash charge pips under the character.
        if self.max_charges and self.charges < self.max_charges:
            for i in range(self.max_charges):
                c = self.c.color if i < self.charges else (60, 50, 80)
                px = int(self.x - (self.max_charges - 1) * 3 + i * 6)
                pygame.draw.rect(surf, c, (px - 1, int(self.y + 18), 3, 2))
        if self.parry_t > 0:
            k = self.parry_t / self.parry_window
            gfx.ring(add, self.x, self.y, self.parry_r * (1.1 - 0.25 * k), (255, 210, 90), 2, 0.6 + 0.4 * k)
        if self.parry_cd > 10:
            # cooldown arc
            frac = self.parry_cd / 48
            pygame.draw.arc(surf, (120, 100, 140), (int(self.x - 13), int(self.y - 13), 26, 26), math.pi / 2, math.pi / 2 + frac * math.tau, 1)

    def draw_hitbox(self, surf, add):
        if not self.alive:
            return
        if self.focus:
            gfx.ring(add, self.x, self.y, self.graze_r, (60, 50, 90), 1)
            pygame.draw.circle(surf, (255, 60, 80), (int(self.x), int(self.y)), int(self.hit_r) + 2)
            pygame.draw.circle(surf, (255, 255, 255), (int(self.x), int(self.y)), max(1, int(self.hit_r)))
