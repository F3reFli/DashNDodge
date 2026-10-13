import math

import pygame

from .. import assets, bullets, gfx
from ..config import GOLD, H, TEXT, TEXT_DIM, W
from ..scene import Scene, dim

CONTROLS = [
    ("Move", "Arrows · WASD · ZQSD", "Left stick / D-pad"),
    ("Focus", "Shift (hold)", "LB / RB"),
    ("Dash", "Space · K · C", "A"),
    ("Parry", "F · J · V", "B / X"),
    ("Spell", "X · L · E", "Y"),
    ("Pause", "Esc · P", "Start"),
]

MECHANICS = [
    ("DASH", (120, 220, 255),
     "A quick burst with invincibility frames. Dash THROUGH bullet walls, and smash fairies on contact. "
     "Dashing past bullets grazes them for double points."),
    ("PARRY", GOLD,
     "Press it just as bullets reach you: every bullet in the ring gets sent back at the nearest enemy. "
     "It's how you take down bosses faster. Whiff it and it goes on cooldown."),
    ("GRAZE", (255, 255, 255),
     "Brush past bullets without getting hit. Grazes give points, build your CHAIN multiplier "
     "and charge your SPELL gauge (the stars)."),
    ("SPELL", (120, 255, 140),
     "Each full star is one spell card: a screen-clearing super move unique to your character. "
     "Cast one within a split second of getting hit to cancel the hit (deathbomb)!"),
    ("INCIDENTS", (255, 120, 140),
     "Mid-stage, a troublemaker may start an incident: flipped screen, slippery ice, invisible bullets, "
     "camera flashes... Survive it. Laugh about it later."),
    ("SPELL CARDS", (200, 160, 255),
     "Bosses declare spell cards. Survive until the timer runs out or break them with parries and dashes. "
     "Don't get hit and don't use a spell to capture the card's bonus."),
]


class HowToScene(Scene):
    transparent = True

    def __init__(self, app):
        super().__init__(app)
        self.page = 0
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        inp = self.app.input
        if inp.was_pressed("back"):
            self.app.pop()
            return
        if inp.was_pressed("confirm") or inp.menu("right"):
            if self.page == 1 and inp.was_pressed("confirm"):
                self.app.pop()
                return
            self.page = min(1, self.page + 1)
            self.sfx("move")
        elif inp.menu("left"):
            self.page = max(0, self.page - 1)
            self.sfx("move")

    def draw(self, surf):
        surf.blit(gfx.blur(surf, 3), (0, 0))
        dim(surf, 200)
        assets.blit_text(surf, "遊び方 - How to Play", (W / 2, 12), 24, (255, 255, 255), "midtop")
        assets.blit_text(surf, f"Page {self.page + 1}/2   ←→ turn · Esc: back", (W / 2, H - 18), 12, TEXT_DIM, "midtop")
        if self.page == 0:
            self._controls(surf)
        else:
            self._mechanics(surf)

    def _controls(self, surf):
        y = 56
        assets.blit_text(surf, "Keyboard", (300, y), 12, GOLD)
        assets.blit_text(surf, "Gamepad", (480, y), 12, GOLD)
        y += 20
        for name, kb, pad in CONTROLS:
            assets.blit_text(surf, name, (120, y), 12, TEXT)
            assets.blit_text(surf, kb, (300, y), 12, TEXT)
            assets.blit_text(surf, pad, (480, y), 12, TEXT_DIM)
            y += 20
        y += 10
        # A tiny live demo of the hitbox concept.
        cx, cy = 150, y + 50
        art = gfx.CharArt.get("Reimu Hakurei", 2)
        art.draw(surf, cx, cy, self.t, 0, False)
        pygame.draw.circle(surf, (60, 50, 90), (cx, cy), 18, 1)
        pygame.draw.circle(surf, (255, 60, 80), (cx, cy), 4)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 2)
        a = self.t * 1.3
        bx, by = cx + math.cos(a) * 26, cy + math.sin(a) * 26
        b = bullets.sprite("orb", "blue")
        surf.blit(b, (bx - b.get_width() / 2, by - b.get_height() / 2))
        lines = [
            "Your hitbox is only the tiny white dot in the middle.",
            "Hold Focus to slow down and see it (and your graze ring).",
            "Bullets can touch your sprite - just not the dot. Live dangerously!",
        ]
        for i, l in enumerate(lines):
            assets.blit_text(surf, l, (200, cy - 22 + i * 16), 12, TEXT)

    def _mechanics(self, surf):
        y = 50
        for title, col, body in MECHANICS:
            assets.blit_text(surf, title, (40, y), 12, col)
            for i, line in enumerate(assets.wrap(body, 12, 470)):
                assets.blit_text(surf, line, (140, y + i * 14), 12, TEXT)
            y += 14 * max(1, len(assets.wrap(body, 12, 470))) + 10
