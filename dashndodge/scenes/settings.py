from .. import assets
from ..config import GOLD, H, TEXT_DIM, W
from ..scene import Menu, MenuItem, Scene, overlay_open
from ..util import clamp

SHAKE_LEVELS = [(0.0, "Off"), (0.5, "Low"), (1.0, "Full")]
BLOOM_NAMES = ["Off", "Low", "High"]


class SettingsScene(Scene):
    transparent = True

    def __init__(self, app):
        super().__init__(app)
        self.t = 0.0
        s = app.save.settings
        self.menu = Menu(app, [
            MenuItem("Music volume", value=lambda: f"{round(s['music_volume'] * 100)}%", adjust=lambda d: self.vol("music_volume", d)),
            MenuItem("Sound effects", value=lambda: f"{round(s['sfx_volume'] * 100)}%", adjust=lambda d: self.vol("sfx_volume", d)),
            MenuItem("Fullscreen", value=lambda: "On" if app.fullscreen else "Off", adjust=lambda d: app.toggle_fullscreen(),
                     action=app.toggle_fullscreen),
            MenuItem("Screen shake", value=self.shake_label, adjust=self.shake),
            MenuItem("Background brightness", value=lambda: f"{round(s['bg_brightness'] * 100)}%",
                     adjust=lambda d: self.bright(d)),
            MenuItem("Renderer", value=self.renderer_label, adjust=lambda d: self.switch_renderer(),
                     action=self.switch_renderer),
            MenuItem("Bloom", value=lambda: BLOOM_NAMES[int(s.get("bloom", 2))], adjust=self.bloom),
            MenuItem("Dynamic lighting", value=lambda: "On" if s.get("lighting", True) else "Off",
                     adjust=lambda d: self.toggle("lighting"), action=lambda: self.toggle("lighting")),
            MenuItem("CRT screen", value=lambda: "On" if s.get("crt", False) else "Off",
                     adjust=lambda d: self.toggle("crt"), action=lambda: self.toggle("crt")),
            MenuItem("Visual effects", value=lambda: "On" if s["effects"] else "Off", adjust=lambda d: self.toggle("effects"),
                     action=lambda: self.toggle("effects"), sub=""),
            MenuItem("Scanlines", value=lambda: "On" if s["scanlines"] else "Off", adjust=lambda d: self.toggle("scanlines"),
                     action=lambda: self.toggle("scanlines")),
            MenuItem("Show FPS", value=lambda: "On" if s["show_fps"] else "Off", adjust=lambda d: self.toggle("show_fps"),
                     action=lambda: self.toggle("show_fps")),
            MenuItem("Back", self.close),
        ], W // 2 - 150, 84, spacing=18, width=300, intro=0.1)

    def vol(self, key, d):
        s = self.app.save.settings
        s[key] = round(clamp(s[key] + d * 0.1, 0.0, 1.0), 2)
        self.app.audio.apply_volumes()
        if key == "sfx_volume":
            self.app.audio.play("item")

    def bright(self, d):
        s = self.app.save.settings
        s["bg_brightness"] = round(clamp(s["bg_brightness"] + d * 0.1, 0.4, 1.0), 2)

    def renderer_label(self):
        if self.app.renderer is not None:
            return "GPU shaders"
        return "Classic (no GPU)" if self.app.gl_failed else "Classic"

    def switch_renderer(self):
        self.app.set_renderer("classic" if self.app.renderer is not None else "gpu")

    def bloom(self, d):
        s = self.app.save.settings
        s["bloom"] = int(clamp(int(s.get("bloom", 2)) + d, 0, 2))

    def toggle(self, key):
        s = self.app.save.settings
        s[key] = not s.get(key, False)

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
        self.t += dt
        if self.app.input.was_pressed("back"):
            self.close()
            return
        self.menu.update(dt)

    def draw(self, surf):
        overlay_open(surf, self.t, "設定", "SETTINGS", GOLD, y=30, dim_alpha=175)
        self.menu.draw(surf)
        assets.blit_text(surf, "←→ change · Enter: toggle · Esc: back", (W / 2, H - 24), 12, TEXT_DIM, "midtop")
