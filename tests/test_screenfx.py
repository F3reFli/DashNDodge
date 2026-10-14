import pygame
import pytest

from dashndodge.config import PALETTE
from dashndodge.fx import Shockwaves
from dashndodge.screenfx import GRADES, MAX_WAVES, SPELL, Grade, LightMap, ScreenFX, bullet_lights


def test_grade_blend_endpoints_and_midpoint():
    a, b = Grade(1.0, 1.0, 1.0, (0, 0, 0), (0, 0, 0), 1.0), Grade(2.0, 3.0, 0.0, (1, 1, 1), (0.5, 0, 0), 0.0)
    assert a.blend(b, 0).exposure == 1.0
    assert a.blend(b, 1).contrast == 3.0
    mid = a.blend(b, 0.5)
    assert mid.exposure == pytest.approx(1.5)
    assert mid.shadows == pytest.approx((0.5, 0.5, 0.5))
    assert mid.bloom == pytest.approx(0.5)


def test_grade_blend_returns_new_object():
    g = GRADES["lake"]
    out = g.blend(SPELL, 0.3)
    assert out is not g and g.exposure == GRADES["lake"].exposure


def test_set_grade_eases_towards_target():
    fx = ScreenFX()
    fx.snap_grade("title")
    fx.set_grade(Grade(exposure=2.0), speed=4.0)
    before = fx.grade.exposure
    fx.update(1 / 60)
    assert before < fx.grade.exposure < 2.0
    for _ in range(600):
        fx.update(1 / 60)
    assert fx.grade.exposure == pytest.approx(2.0, abs=1e-3)


def test_unknown_grade_key_is_neutral():
    fx = ScreenFX()
    fx.snap_grade("does-not-exist")
    assert fx.grade.exposure == 1.0


def test_waves_are_capped():
    fx = ScreenFX()
    for i in range(MAX_WAVES + 5):
        fx.wave(i, i, 10)
    assert len(fx.waves) == MAX_WAVES


def test_punch_decays_and_keeps_strongest_position():
    fx = ScreenFX()
    fx.punch(0.4, 10, 10)
    fx.punch(0.9, 50, 60)
    fx.punch(0.2, 99, 99)
    assert fx.impact == 0.9 and fx.impact_pos == (50, 60)
    for _ in range(60):
        fx.update(1 / 60)
    assert fx.impact == 0.0


def test_begin_frame_clears_per_frame_inputs():
    fx = ScreenFX()
    fx.wave(1, 1, 5)
    fx.godray = (1, 1, 1, (255, 0, 0))
    fx.haze = 0.5
    fx.danger = 0.5
    fx.lights.add(100, 100, 40, (255, 255, 255))
    fx.begin_frame()
    assert fx.waves == [] and fx.godray is None and fx.haze == 0 and fx.danger == 0
    assert fx.lights.count == 0
    assert pygame.transform.average_color(fx.lights.surf)[:3] == (0, 0, 0)


def test_lightmap_adds_light_and_ignores_black():
    lm = LightMap()
    lm.add(320, 180, 80, (0, 0, 0))
    assert lm.count == 0
    lm.add(320, 180, 80, (255, 128, 64), 1.0)
    assert lm.count == 1
    r, g, b, _ = lm.surf.get_at((80, 45))
    assert r > g > b > 0


def test_waves_from_shockwaves():
    sw = Shockwaves()
    sw.add(100, 100, r1=80, life=0.5, width=3)
    sw.update(0.2)
    fx = ScreenFX()
    fx.waves_from(sw)
    assert len(fx.waves) == 1
    x, y, r, thick, strength = fx.waves[0]
    assert (x, y) == (100, 100) and 6 < r <= 80 and strength > 0


class _B:
    def __init__(self, i):
        self.x, self.y, self.r, self.color = i % 640, i % 360, 3, "red"
        self.dead = self.invisible = False


class _Bullets:
    def __init__(self, n):
        self.items = [_B(i) for i in range(n)]
        self.friendly = []
        self.lasers = []


def test_bullet_lights_are_subsampled():
    lm = LightMap()
    bullet_lights(lm, _Bullets(1000), PALETTE, limit=100)
    assert 0 < lm.count <= 100
