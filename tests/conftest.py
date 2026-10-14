import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


def _make_app(tmp_path, gl):
    from dashndodge.app import App

    app = App(headless=True, save_path=str(tmp_path / "save.json"), gl=gl)
    app.save.unlocks.update({"remilia": True, "extra": True})
    return app


@pytest.fixture
def app(tmp_path):
    """Headless app with the classic (CPU) renderer."""
    return _make_app(tmp_path, gl=False)


@pytest.fixture
def gl_app(tmp_path):
    """Headless app with the GPU renderer (offscreen); skipped without OpenGL."""
    a = _make_app(tmp_path, gl=True)
    if a.renderer is None:
        pytest.skip("no OpenGL context available")
    yield a
    a.renderer.release()


def run_frames(app, n, god=True, present=False):
    """Step + render n frames with a simple deterministic bot."""
    for f in range(n):
        g = app.scene
        if god and hasattr(g, "god"):
            g.god = True
        inp = app.input
        inp.held_keys.clear()
        inp.held_keys.add(("left", "up", "right", "down")[(f // 30) % 4])
        if f % 23 == 0:
            inp.pressed.add("dash")
        if f % 29 == 0:
            inp.pressed.add("parry")
        if f % 41 == 0:
            inp.pressed.add("confirm")
        app.step()
        app.render()
        if present:
            app.present()
