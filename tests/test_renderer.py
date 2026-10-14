import pygame
import pytest

from conftest import run_frames
from dashndodge.config import H, W
from dashndodge.game import GameScene
from dashndodge.scenes.title import TitleScene


def _avg(surf):
    return sum(pygame.transform.average_color(surf)[:3]) / 3


def test_gpu_title_renders_a_frame(gl_app):
    gl_app.push(TitleScene(gl_app))
    run_frames(gl_app, 120, present=True)
    snap = gl_app.renderer.snapshot()
    assert snap.get_size() == (1280, 720)
    assert _avg(snap) > 5  # not a black screen


def test_gpu_output_tracks_canvas_with_neutral_grade(gl_app):
    from dashndodge.screenfx import Grade

    gl_app.save.settings.update(bloom=0, lighting=False, effects=False, scanlines=False)
    gl_app.push(TitleScene(gl_app))
    run_frames(gl_app, 30)
    gl_app.fx.snap_grade(Grade(1.0, 1.0, 1.0))
    gl_app.fx.vignette = 0.0
    gl_app.render()
    gl_app.fx.godray = None
    gl_app.present()
    assert _avg(gl_app.renderer.snapshot()) == pytest.approx(_avg(gl_app.canvas), abs=4)


def test_dissolve_fully_burnt_is_dark(gl_app):
    gl_app.push(TitleScene(gl_app))
    run_frames(gl_app, 30)
    gl_app.render()
    gl_app.fx.dissolve = (1.0, (255, 70, 110))
    gl_app.present()
    assert _avg(gl_app.renderer.snapshot()) < 15


@pytest.mark.parametrize("bloom,lighting,crt,effects", [(0, False, False, False), (1, True, True, True), (2, True, False, True)])
def test_gpu_gameplay_settings_combinations(gl_app, bloom, lighting, crt, effects):
    gl_app.save.settings.update(bloom=bloom, lighting=lighting, crt=crt, effects=effects)
    gl_app.push(GameScene(gl_app, "practice", "reimu", 2, practice=("flandre", 4)))
    run_frames(gl_app, 200, present=True)
    assert gl_app.renderer is not None
    assert _avg(gl_app.renderer.snapshot()) > 1


def test_hud_layer_goes_to_ui_only_on_gpu_top_scene(gl_app, app):
    g = GameScene(gl_app, "story", "reimu", 1)
    gl_app.push(g)
    assert gl_app.hud_layer(g, gl_app.canvas) is gl_app.ui
    c = GameScene(app, "story", "reimu", 1)
    app.push(c)
    assert app.hud_layer(c, app.canvas) is app.canvas


def test_switching_renderer_at_runtime(gl_app):
    gl_app.push(TitleScene(gl_app))
    gl_app.set_renderer("classic")
    assert gl_app.renderer is None and gl_app.post.gpu is False
    run_frames(gl_app, 10)
    gl_app.set_renderer("gpu")
    assert gl_app.renderer is not None and gl_app.post.gpu is True
    run_frames(gl_app, 10, present=True)
    assert gl_app.canvas.get_size() == (W, H)
