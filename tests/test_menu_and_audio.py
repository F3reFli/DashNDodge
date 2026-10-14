import pygame

from dashndodge.scene import Menu, MenuItem
from dashndodge.scenes.title import INTRO_END, TitleScene


def _menu(app, picked):
    items = [MenuItem("A", lambda: picked.append("A")), MenuItem("B", enabled=False), MenuItem("C", lambda: picked.append("C"))]
    return Menu(app, items, 50, 50)


def test_menu_skips_disabled_items_and_confirms(app):
    picked = []
    m = _menu(app, picked)
    app.input.pressed.add("down")
    m.update(1 / 60)
    assert m.index == 2
    app.input.pressed.clear()
    app.input.pressed.add("confirm")
    m.update(1 / 60)
    assert picked == ["C"] and m.pulse > 0.9 and m.sparks


def test_menu_bar_slides_and_draws(app):
    m = _menu(app, [])
    app.input.pressed.add("down")
    m.update(1 / 60)
    app.input.pressed.clear()
    for _ in range(60):
        m.update(1 / 60)
    assert abs(m.bar_y - (50 + 2 * m.spacing)) < 0.5
    m.draw(pygame.Surface((640, 360)))


def test_menu_intro_staggers_items(app):
    m = Menu(app, [MenuItem(str(i)) for i in range(5)], 0, 0, intro=1.0)
    assert m._appear(0) == 0
    m.t = 1.2
    assert m._appear(0) > m._appear(4)


def test_title_intro_is_skippable_and_plays_once(app):
    t = TitleScene(app)
    app.push(t)
    for _ in range(3):
        app.step()
    assert t.t < 0.1
    app.input.pressed.add("confirm")
    t.update(1 / 60)
    assert t.t >= 1.6 and len(t.slammed) == 3
    for _ in range(int(INTRO_END * 60) + 10):
        app.step()
        app.render()
    assert t.intro_done
    assert TitleScene(app).t == INTRO_END  # second visit skips the intro


def test_pause_mutes_music_instead_of_pausing(app, monkeypatch):
    audio = app.audio
    if not audio.ok:
        return
    calls = []
    monkeypatch.setattr(pygame.mixer.music, "pause", lambda: calls.append("pause"))
    monkeypatch.setattr(pygame.mixer.music, "unpause", lambda: calls.append("unpause"))
    audio.pause_music(True)
    assert pygame.mixer.music.get_volume() == 0.0
    audio.pause_music(True)  # redundant call is a no-op
    audio.pause_music(False)
    assert pygame.mixer.music.get_volume() > 0.0
    assert calls == []


def test_single_track_plays_everywhere(app):
    audio = app.audio
    if not audio.ok:
        return
    assert audio.play_music(["title"]) is not None
    assert audio.play_music(["stage1"]) is None  # same track keeps playing
    assert audio.play_music(["boss_remilia", "boss"], keep_if_missing=True) is None
