import pytest

from conftest import run_frames
from dashndodge.game import GameScene
from dashndodge.scenes.charselect import CharSelectScene
from dashndodge.scenes.pause import PauseScene
from dashndodge.scenes.settings import SettingsScene


@pytest.mark.parametrize("mode,char,kw", [
    ("story", "marisa", {"start_stage": 5}),
    ("extra", "sakuya", {}),
    ("endless", "cirno", {}),
    ("practice", "meiling", {"practice": ("sakuya", 2)}),
])
def test_modes_run_without_errors(app, mode, char, kw):
    app.push(GameScene(app, mode, char, 2, **kw))
    run_frames(app, 600)


def test_gpu_story_stage_with_pause_and_settings(gl_app):
    g = GameScene(gl_app, "story", "remilia", 3, start_stage=2)
    gl_app.push(g)
    run_frames(gl_app, 300, present=True)
    gl_app.push(PauseScene(gl_app, g))
    run_frames(gl_app, 30, present=True)
    gl_app.push(SettingsScene(gl_app))
    run_frames(gl_app, 30, present=True)
    gl_app.pop()
    gl_app.pop()
    run_frames(gl_app, 60, present=True)


def test_charselect_effects(gl_app):
    gl_app.push(CharSelectScene(gl_app, "story"))
    for _ in range(5):
        gl_app.input.pressed.add("right")
        run_frames(gl_app, 20, present=True)
    assert gl_app.fx.godray is not None
