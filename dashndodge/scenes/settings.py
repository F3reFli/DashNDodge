from .. import assets, gfx
from ..config import GOLD, H, TEXT_DIM, W
from ..scene import Menu, MenuItem, Scene, dim
from ..util import clamp

SHAKE_LEVELS = [(0.0, "Off"), (0.5, "Low"), (1.0, "Full")]


class SettingsScene(Scene):
    transparent = True

    def __init__(self, app):
        super().__init__(app)
        s = app.save.settings
        self.menu = Menu(app, [
            MenuItem("Music volume", value=lambda: f"{round(s['music_volume'] * 100)}%", adjust=lambda d: self.vol("music_volume", d)),
            MenuItem("Sound effects", value=lambda: f"{round(s['sfx_volume'] * 100)}%", adjust=lambda d: self.vol("sfx_volume", d)),
            MenuItem("Fullscreen", value=lambda: "On" if app.fullscreen else "Off", adjust=lambda d: app.toggle_fullscreen(),
                     action=app.toggle_fullscreen),
            MenuItem("Screen shake", value=self.shake_label, adjust=self.shake),
            MenuItem("Background brightness", value=lambda: f"{round(s['bg_brightness'] * 100)}%",
                     adjust=lambda d: self.bright(d)),
            MenuItem("Visual effects", value=lambda: "On" if s["effects"] else "Off", adjust=lambda d: self.toggle("effects"),
                     action=lambda: self.toggle("effects"), sub=""),
            MenuItem("Scanlines", value=lambda: "On" if s["scanlines"] else "Off", adjust=lambda d: self.toggle("scanlines"),
                     action=lambda: self.toggle("scanlines")),
            MenuItem("Show FPS", value=lambda: "On" if s["show_fps"] else "Off", adjust=lambda d: self.toggle("show_fps"),
                     action=lambda: self.toggle("show_fps")),
            MenuItem("Back", self.close),
        ], W // 2 - 150, 104, spacing=21, width=300)

    def vol(self, key, d):
        s = self.app.save.settings
        s[key] = round(clamp(s[key] + d * 0.1, 0.0, 1.0), 2)
        self.app.audio.apply_volumes()
        if key == "sfx_volume":
            self.app.audio.play("item")

    def bright(self, d):
        s = self.app.save.settings
        s["bg_brightness"] = round(clamp(s["bg_brightness"] + d * 0.1, 0.4, 1.0), 2)

    def toggle(self, key):
        s = self.app.save.settings
        s[key] = not s[key]

    def shake_label(self):
        v = self.app.save.settings.get("screen_shake", 1.0)
        return min(SHAKE_LEVELS, key=lambda lv: abs(lv[0] - v))[1]

    def shake(self, d):
        s = self.app.save.settings
        levels = [lv[0] for lv in SHAKE_LEVELS]
        cur = min(range(len(levels)), key=lambda i: abs(levels[i] - s.get("screen_shake", 1.0)))
        s["screen_shake"] = levels[int(clamp(cur + d, 0, len(levels) - 1))]
        for sc in self.app.scenes:
            if hasattr(sc, "shake"):
                obj = getattr(sc, "shake")
                if hasattr(obj, "scale"):
                    obj.scale = s["screen_shake"]

    def close(self):
        self.app.save.write()
        self.app.pop()

    def update(self, dt):
        if self.app.input.was_pressed("back"):
            self.close()
            return
        self.menu.update(dt)

    def draw(self, surf):
        surf.blit(gfx.blur(surf, 3), (0, 0))
        dim(surf, 170)
        assets.blit_text(surf, "設定", (W / 2, 50), 24, (255, 255, 255), "midtop")
        assets.blit_text(surf, "Settings", (W / 2, 80), 12, GOLD, "midtop")
        self.menu.draw(surf)
        assets.blit_text(surf, "←→ change · Enter: toggle · Esc: back", (W / 2, H - 24), 12, TEXT_DIM, "midtop")
