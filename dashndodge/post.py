"""Screen-space post effects: scanlines, film grain, glitch tears and
chromatic aberration. Toggleable in Settings (Visual effects / Scanlines)."""

import random

import pygame

from .config import H, W


class Post:
    def __init__(self, settings):
        self.settings = settings
        self.gpu = False  # the GPU renderer does aberration, grain and scanlines in shaders
        self.rng = random.Random(7)
        self.scan = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 2):
            self.scan.fill((0, 0, 0, 34), (0, y, W, 1))
        self.grain = []
        for k in range(4):
            g = pygame.Surface((W, H), pygame.SRCALPHA)
            r = random.Random(100 + k)
            for _ in range(2600):
                v = r.choice((0, 255))
                g.fill((v, v, v, r.randint(10, 26)), (r.randrange(W), r.randrange(H), 1, 1))
            self.grain.append(g)
        self.glitch_t = 0
        self.glitch_power = 0.0
        self.aberr_t = 0
        self.aberr_px = 0
        self.frame = 0
        self._r = pygame.Surface((W, H))
        self._gb = pygame.Surface((W, H))

    @property
    def enabled(self):
        return self.settings.get("effects", True)

    def glitch(self, frames, power=1.0):
        if self.enabled:
            self.glitch_t = max(self.glitch_t, frames)
            self.glitch_power = max(self.glitch_power if self.glitch_t else 0.0, power)

    def aberration(self, frames, px=2):
        if self.enabled:
            self.aberr_t = max(self.aberr_t, frames)
            self.aberr_px = max(self.aberr_px if self.aberr_t else 0, px)

    def update(self):
        self.frame += 1
        if self.glitch_t > 0:
            self.glitch_t -= 1
            if self.glitch_t == 0:
                self.glitch_power = 0.0
        if self.aberr_t > 0:
            self.aberr_t -= 1
            if self.aberr_t == 0:
                self.aberr_px = 0

    def apply(self, surf):
        if self.enabled:
            if self.aberr_t > 0 and not self.gpu:
                self._aberration(surf, max(1, int(self.aberr_px * min(1.0, self.aberr_t / 8))))
            if self.glitch_t > 0:
                self._glitch(surf, self.glitch_power)
            if not self.gpu:
                surf.blit(self.grain[(self.frame // 2) % 4], (0, 0))
        if self.settings.get("scanlines", True) and not self.gpu:
            surf.blit(self.scan, (0, 0))

    def _aberration(self, surf, d):
        r, gb = self._r, self._gb
        r.blit(surf, (0, 0))
        gb.blit(surf, (0, 0))
        r.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)
        gb.fill((0, 255, 255), special_flags=pygame.BLEND_MULT)
        surf.fill((0, 0, 0))
        surf.blit(r, (-d, 0), special_flags=pygame.BLEND_ADD)
        surf.blit(gb, (d, 0), special_flags=pygame.BLEND_ADD)

    def _glitch(self, surf, power):
        rng = self.rng
        n = int(2 + 6 * power)
        for _ in range(n):
            h = rng.randint(1, int(4 + 14 * power))
            y = rng.randrange(0, H - h)
            dx = rng.randint(-int(6 + 30 * power), int(6 + 30 * power))
            band = surf.subsurface((0, y, W, h)).copy()
            if rng.random() < 0.25:
                band.fill((rng.choice((255, 120)), rng.choice((40, 255)), rng.choice((60, 255))), special_flags=pygame.BLEND_MULT)
            surf.blit(band, (dx, y))
        if rng.random() < 0.3 * power:
            y = rng.randrange(0, H - 3)
            surf.fill((255, 255, 255) if rng.random() < 0.5 else (200, 20, 40), (0, y, W, rng.randint(1, 2)))
