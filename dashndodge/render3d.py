"""Pseudo-3D rendering for stage backgrounds.

A Plane is an infinite textured floor (or ceiling) drawn scanline by
scanline, mode-7 style: each screen row samples one row of a mipmapped,
horizontally tiled texture strip and stretches it across the screen.
Props are sprites standing on the plane, projected and scaled by depth,
so torii gates, trees and bookshelves rush past the camera."""

import math

import pygame

from .config import H, W
from .util import clamp


class Camera:
    def __init__(self, horizon=110, height=1.0, focal=250.0, ceiling=None):
        self.horizon = horizon
        self.height = height  # above the floor
        self.focal = focal
        self.ceiling = ceiling  # ceiling height above the floor (interiors)
        self.x = 0.0
        self.scroll = 0.0
        self.bob = 0.0

    @property
    def hz(self):
        return self.horizon + self.bob


class Plane:
    def __init__(self, cam, tile, ppu=128, z_far=36.0, step=2, ceiling=False, fog=(0, 0, 0), fog_start=4.0, wobble=0.0):
        self.cam = cam
        self.ppu = ppu
        self.z_far = z_far
        self.step = step
        self.ceiling = ceiling
        self.fog = fog
        self.fog_start = fog_start
        self.wobble = wobble
        self.levels = []
        self.u_center = tile.get_width() / 2  # texture centre sits under the camera
        lvl = tile.convert()
        k = 1
        while True:
            w, h = lvl.get_size()
            reps = math.ceil(1.7 * W / w) + 2
            wide = pygame.Surface((w * reps, h)).convert()
            for i in range(reps):
                wide.blit(lvl, (i * w, 0))
            self.levels.append((wide, w, h, k))
            if w <= 16 or h <= 16 or len(self.levels) >= 8:
                break
            lvl = pygame.transform.smoothscale(lvl, (w // 2, h // 2))
            k *= 2
        self.row = pygame.Surface((W, step)).convert()
        self._fog_cache = {}

    def _fog_overlay(self, hz):
        key = int(hz)
        surf = self._fog_cache.get(key)
        if surf is None:
            surf = pygame.Surface((W, H), pygame.SRCALPHA)
            cam = self.cam
            h_eff = (cam.ceiling - cam.height) if self.ceiling else cam.height
            for y in range(H):
                dy = (hz - y) if self.ceiling else (y - hz)
                if dy <= 0:
                    continue
                z = h_eff * cam.focal / (dy + 0.5)
                a = clamp((z - self.fog_start) / (self.z_far - self.fog_start), 0.0, 1.0)
                a = a ** 0.8
                surf.fill((*self.fog, int(255 * a)), (0, y, W, 1))
            self._fog_cache[key] = surf
        return surf

    def draw(self, surf, t=0.0):
        cam = self.cam
        hz = cam.hz
        f = cam.focal
        ppu = self.ppu
        cx = W / 2
        h_eff = (cam.ceiling - cam.height) if self.ceiling else cam.height
        step = self.step
        levels = self.levels
        nlev = len(levels)
        if self.ceiling:
            rows = range(int(hz) - step, -step, -step)
        else:
            rows = range(int(hz) + 1, H, step)
        row = self.row
        maxspan = 1.6 * W
        for y in rows:
            dy = (hz - y) if self.ceiling else (y - hz)
            if dy <= 0.5:
                continue
            z = h_eff * f / dy
            if z > self.z_far:
                surf.fill(self.fog, (0, max(0, y), W, step))
                continue
            span0 = W * z / f * ppu
            L = 0
            while L < nlev - 1 and span0 / levels[L][3] > maxspan:
                L += 1
            wide, tw, th, k = levels[L]
            span = span0 / k
            u = ((cam.x - cx * z / f) * ppu + self.u_center) / k
            if self.wobble:
                u += math.sin(y * 0.09 + t * 2.2) * self.wobble * (6 / (z + 1)) * ppu / k
            ui = int(u) % tw
            si = max(1, int(span))
            if ui + si > wide.get_width():
                si = wide.get_width() - ui
            vi = int((z + cam.scroll) * ppu / k) % th
            strip = wide.subsurface((ui, vi, si, 1))
            pygame.transform.scale(strip, (W, step), row)
            surf.blit(row, (0, y))
        surf.blit(self._fog_overlay(hz), (0, 0))


# Scaled prop sprites are cached across every PropField, under a byte budget.
_cache = {}
_cache_bytes = 0
CACHE_BUDGET = 48 * 1024 * 1024
MAX_CACHED_H = 200  # taller (= very close) props are scaled on the fly
MAX_DRAW_H = 2.6 * H  # closer than this, a prop is past the screen edges


def _cache_put(key, img):
    global _cache_bytes
    size = img.get_width() * img.get_height() * 4
    if _cache_bytes + size > CACHE_BUDGET:
        _cache.clear()
        _cache_bytes = 0
    _cache[key] = img
    _cache_bytes += size


class Prop:
    __slots__ = ("frames", "world_h", "x", "v", "lift", "hang", "fps", "phase", "bob", "cache_id", "glow", "glow_y")

    def __init__(self, frames, world_h, x, v, lift=0.0, hang=False, fps=0.0, phase=0.0, bob=0.0, glow=None,
                 glow_y=0.5):
        self.frames = frames if isinstance(frames, list) else [frames]
        self.world_h = world_h
        self.x = x
        self.v = v
        self.lift = lift
        self.hang = hang
        self.fps = fps
        self.phase = phase
        self.bob = bob
        self.cache_id = id(self.frames[0])
        self.glow = glow  # light colour emitted by this prop (lanterns, crystals)
        self.glow_y = glow_y  # where the light sits, as a fraction of the height from the top


class PropField:
    """Props repeating every `period` world units along the travel axis."""

    def __init__(self, cam, period, fog=(0, 0, 0), fog_start=4.0, z_far=30.0, z_near=0.45):
        self.cam = cam
        self.period = period
        self.fog = fog
        self.fog_start = fog_start
        self.z_far = z_far
        self.z_near = z_near
        self.props = []
        self.uid = id(self)
        self.lit = []  # (x, y, radius, colour, intensity) of glowing props drawn this frame

    def add(self, frames, world_h, x, v, **kw):
        p = Prop(frames, world_h, x, v, **kw)
        self.props.append(p)
        return p

    def _scaled(self, p, frame_i, hpx, z):
        if hpx < 64:
            hq = int(hpx)
        else:
            hq = int(hpx) // 4 * 4
        cacheable = hq <= MAX_CACHED_H
        key = (self.uid, p.cache_id, frame_i, hq)
        if cacheable:
            img = _cache.get(key)
            if img is not None:
                return img
        base = p.frames[frame_i]
        bw, bh = base.get_size()
        wq = max(1, int(bw * hq / bh))
        img = pygame.transform.scale(base, (wq, max(1, hq)))
        fogk = clamp((z - self.fog_start) / (self.z_far - self.fog_start), 0.0, 1.0)
        if fogk > 0.01:
            keep = int(255 * (1 - fogk))
            img.fill((keep, keep, keep, 255), special_flags=pygame.BLEND_RGBA_MULT)
            img.fill((int(self.fog[0] * fogk), int(self.fog[1] * fogk), int(self.fog[2] * fogk), 0),
                     special_flags=pygame.BLEND_RGBA_ADD)
        if cacheable:
            _cache_put(key, img)
        return img

    def draw(self, surf, t=0.0):
        cam = self.cam
        hz = cam.hz
        f = cam.focal
        cx = W / 2
        period = self.period
        vis = []
        for p in self.props:
            z = (p.v - cam.scroll) % period
            if self.z_near < z < self.z_far:
                vis.append((z, p))
        vis.sort(key=lambda a: -a[0])
        self.lit = []
        for z, p in vis:
            scale = f / z
            hpx = p.world_h * scale
            if hpx < 2 or hpx > MAX_DRAW_H:
                continue
            sx = cx + (p.x - cam.x) * scale
            half_w = hpx * p.frames[0].get_width() / p.frames[0].get_height() / 2
            if sx + half_w < 0 or sx - half_w > W:
                continue
            fi = int(t * p.fps + p.phase) % len(p.frames) if p.fps else 0
            img = self._scaled(p, fi, hpx, z)
            w = img.get_width()
            if sx + w / 2 < 0 or sx - w / 2 > W:
                continue
            lift = p.lift + (math.sin(t * 2 + p.phase) * p.bob if p.bob else 0.0)
            if p.hang:
                top = hz - (cam.ceiling - cam.height - lift) * scale
            else:
                top = hz + (cam.height - lift) * scale - img.get_height()
            surf.blit(img, (int(sx - w / 2), int(top)))
            if p.glow is not None:
                near = 1.0 - clamp((z - self.fog_start) / (self.z_far - self.fog_start), 0.0, 1.0)
                if near > 0.05:
                    self.lit.append((sx, top + img.get_height() * p.glow_y, 10 + hpx * 1.1, p.glow, near))
