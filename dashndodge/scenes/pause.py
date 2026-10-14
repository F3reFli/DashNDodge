
from .. import assets, charms
from ..config import GOLD, H, TEXT_DIM, W
from ..scene import Menu, MenuItem, Scene, overlay_open


class PauseScene(Scene):
    transparent = True

    def __init__(self, app, game):
        super().__init__(app)
        self.game = game
        self.t = 0.0
        self.menu = Menu(app, [
            MenuItem("Resume", self.resume_game, sub="再開"),
            MenuItem("Restart", self.restart, sub="リトライ"),
            MenuItem("How to Play", self.howto, sub="遊び方"),
            MenuItem("Settings", self.settings, sub="設定"),
            MenuItem("Quit to Title", self.to_title, sub="タイトルへ"),
        ], W // 2 - 70, 140, spacing=20, intro=0.08)

    def enter(self):
        self.app.audio.pause_music(True)
        self.sfx("select")

    def exit(self):
        self.app.audio.pause_music(False)

    def resume_game(self):
        self.app.pop()

    def restart(self):
        from ..game import GameScene

        g = self.game
        self.app.audio.pause_music(False)
        self.app.replace(GameScene(self.app, g.mode, g.cdef.id, g.diff, practice=g.practice))

    def howto(self):
        from .howto import HowToScene

        self.app.push(HowToScene(self.app))

    def settings(self):
        from .settings import SettingsScene

        self.app.push(SettingsScene(self.app))

    def to_title(self):
        from .title import TitleScene

        self.app.audio.pause_music(False)
        self.app.replace(TitleScene(self.app))

    def update(self, dt):
        self.t += dt
        inp = self.app.input
        if inp.was_pressed("back") or (inp.was_pressed("pause") and self.t > 0.1):
            self.app.pop()
            return
        self.menu.update(dt)

    def draw(self, surf):
        overlay_open(surf, self.t, "一時停止", "PAUSED", GOLD, y=62, dim_alpha=150)
        self.app.fx.desaturate = 0.35 * min(1.0, self.t / 0.3)
        self.menu.draw(surf)
        g = self.game
        info = f"{g.cdef.name} · {g.stage.label} · Score {g.score:,}".replace(",", " ")
        assets.blit_text(surf, info, (W / 2, H - 30), 12, TEXT_DIM, "midtop")
        owned = [charms.BY_ID[c] for c in g.player.charms if c in charms.BY_ID]
        if owned:
            x0 = W / 2 - len(owned) * 11
            for i, c in enumerate(owned):
                surf.blit(charms.icon(c), (x0 + i * 22, H - 64))
            sel = owned[int(self.t * 0.5) % len(owned)]
            assets.blit_text(surf, f"{sel.name}: {sel.desc}", (W / 2, H - 46), 12, sel.color, "midtop")
