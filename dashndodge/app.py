"""Window, main loop (fixed 60 Hz logic), scene stack and transitions."""

import os

import pygame

from .config import DT, FPS, H, TITLE, VERSION, W, resource_path
from .inputs import Input
from .save import SaveData
from .screenfx import ScreenFX


class App:
    def __init__(self, headless=False, save_path=None, gl=None):
        self.headless = headless
        # Headless runs (tests, fuzzing) skip the GPU unless asked for.
        self.want_gl = gl if gl is not None else (not headless or bool(os.environ.get("DND_GL")))
        self.renderer = None
        self.gl_failed = False
        self.fx = ScreenFX()
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.save = SaveData(save_path)
        from .post import Post

        self.post = Post(self.save.settings)
        self.screen = None
        self.fullscreen = False
        self.set_display(self.save.settings.get("fullscreen", False))
        pygame.display.set_caption(f"避ける - {TITLE}!  v{VERSION}")
        try:
            icon = pygame.image.load(resource_path("sprites/1. Mainline Games/[6] Koumakyou ~ Embodiment of Scarlet Devil/Cirno.png"))
            pygame.display.set_icon(pygame.transform.scale_by(icon, 4))
        except (pygame.error, FileNotFoundError):
            pass
        pygame.key.set_repeat()
        self.canvas = pygame.Surface((W, H)).convert()
        self.clock = pygame.time.Clock()
        self.input = Input()
        from .audio import Audio

        self.audio = Audio(self.save)
        self.scenes = []
        self.fading = None  # [t, duration, phase, action]
        self.fade_color = (255, 70, 110)
        # HUD layer: kept out of bloom/grading/distortion by the GPU renderer.
        self.ui = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ui_used = False
        self.running = True
        self.acc = 0.0

    # ------------------------------------------------------------------
    def set_display(self, fullscreen):
        self.fullscreen = fullscreen
        self.vsync = False
        if self.renderer is not None:
            self.renderer.release()
            self.renderer = None
        self.post.gpu = False
        if self.headless:
            self.screen = pygame.display.set_mode((W, H))
            if self._gpu_wanted():
                self._start_renderer(headless=True)
            return
        if self._gpu_wanted() and self._set_gl_mode(fullscreen):
            return
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        if self._screen_is_60hz():
            try:
                self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
                self.vsync = True
                return
            except pygame.error:
                pass
        self.screen = pygame.display.set_mode((W, H), flags)

    @staticmethod
    def _screen_is_60hz():
        """Logic runs at a fixed 60 Hz: VSync only paces frames nicely on a
        60 Hz screen; elsewhere the clock caps the frame rate instead."""
        try:
            rates = pygame.display.get_desktop_refresh_rates()
        except (AttributeError, pygame.error):
            rates = []
        return bool(rates) and 58 <= rates[0] <= 61

    def _window_size(self):
        """Largest whole multiple of the canvas that fits the desktop."""
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except (AttributeError, IndexError, pygame.error):
            return W * 2, H * 2
        k = max(1, min(int(dw * 0.9) // W, int(dh * 0.9) // H))
        return W * k, H * k

    def _set_gl_mode(self, fullscreen):
        """Open an OpenGL window and the shader pipeline; False on failure."""
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            flags = pygame.OPENGL | pygame.DOUBLEBUF
            flags |= pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
            size = (0, 0) if fullscreen else self._window_size()
            self.screen = None
            if self._screen_is_60hz():
                try:
                    self.screen = pygame.display.set_mode(size, flags, vsync=1)
                    self.vsync = True
                except pygame.error:
                    pass
            if self.screen is None:
                self.screen = pygame.display.set_mode(size, flags)
        except pygame.error as exc:
            print(f"[renderer] no OpenGL window ({exc}); using the classic renderer")
            return False
        if self._start_renderer(headless=False):
            return True
        # Shaders failed on this window: reopen it as a plain one (this
        # session only, so a one-off driver hiccup is not saved forever).
        self.gl_failed = True
        return False

    def _start_renderer(self, headless):
        from .renderer import GLRenderer

        try:
            self.renderer = GLRenderer(self.save.settings, headless=headless)
        except Exception as exc:  # missing moderngl, old driver, shader error...
            print(f"[renderer] GPU shaders unavailable ({exc}); using the classic renderer")
            self.renderer = None
            return False
        self.post.gpu = True
        return True

    def _gpu_wanted(self):
        return self.want_gl and not self.gl_failed and self.save.settings.get("renderer", "gpu") == "gpu"

    def set_renderer(self, mode, persist=True):
        """Switch between "gpu" and "classic" at runtime (Settings)."""
        if persist:
            self.save.settings["renderer"] = mode
            self.gl_failed = False
        self.post.gpu = False
        self.set_display(self.fullscreen)
        pygame.display.set_caption(f"避ける - {TITLE}!  v{VERSION}")

    def toggle_fullscreen(self):
        if self.headless:
            return
        if self.renderer is not None:
            self.set_display(not self.fullscreen)
        else:
            try:
                pygame.display.toggle_fullscreen()
                self.fullscreen = not self.fullscreen
            except pygame.error:
                self.set_display(not self.fullscreen)
        self.save.settings["fullscreen"] = self.fullscreen
        self.save.write()

    # ------------------------------------------------------------------
    @property
    def scene(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene):
        self.input.pressed.clear()
        self.scenes.append(scene)
        scene.enter()

    def pop(self):
        if self.scenes:
            self.scenes.pop().exit()
        self.input.pressed.clear()
        if self.scene:
            self.scene.resume()

    def replace(self, scene, fade=True):
        def swap():
            while self.scenes:
                self.scenes.pop().exit()
            self.scenes.append(scene)
            scene.enter()

        if fade:
            self.fade(swap)
        else:
            swap()

    def fade(self, action, duration=0.28, color=(255, 70, 110)):
        if self.fading is None:
            if self.renderer is not None:
                duration = max(duration, 0.42)  # the burn dissolve needs a little longer
            self.fade_color = color
            self.fading = [0.0, duration, "out", action]

    def hud_layer(self, scene, surf):
        """Where `scene` should draw its HUD: the crisp UI layer when it is the
        top scene on the GPU renderer, else straight onto the canvas."""
        if self.renderer is not None and scene is self.scene:
            self.ui_used = True
            return self.ui
        return surf

    def quit(self):
        self.running = False

    # ------------------------------------------------------------------
    def step(self, dt=DT):
        """One logic tick."""
        self.post.update()
        self.fx.update(dt)
        if self.fading is not None:
            f = self.fading
            f[0] += dt
            if f[2] == "out" and f[0] >= f[1]:
                f[3]()
                f[0] = 0.0
                f[2] = "in"
            elif f[2] == "in" and f[0] >= f[1]:
                self.fading = None
            if f[2] == "out":
                self.input.end_step(dt)
                return
        if self.scene:
            self.scene.update(dt)
        self.input.end_step(dt)

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN and (e.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
                continue
            self.input.handle_event(e)
            if self.scene:
                self.scene.handle_event(e)

    def render(self):
        surf = self.canvas
        fx = self.fx
        fx.begin_frame()
        if self.ui_used:
            self.ui.fill((0, 0, 0, 0))
            self.ui_used = False
        # Draw from the lowest visible scene up (scenes also feed self.fx).
        start = len(self.scenes) - 1
        while start > 0 and self.scenes[start].transparent:
            start -= 1
        for sc in self.scenes[start:]:
            sc.draw(surf)
        self.post.apply(surf)
        if self.ui_used and self.renderer is None:
            surf.blit(self.ui, (0, 0))
        fade = None
        if self.fading is not None:
            t, dur, phase, _ = self.fading
            k = min(1.0, t / dur)
            fade = k if phase == "out" else 1 - k
        ox, oy = self.scene.shake_offset() if self.scene else (0, 0)
        if self.renderer is not None:
            fx.offset = (float(ox), float(oy))
            fx.dissolve = (fade, self.fade_color) if fade is not None else None
            return
        if fade is not None:
            veil = pygame.Surface((W, H))
            veil.fill((6, 2, 12))
            veil.set_alpha(int(255 * fade))
            surf.blit(veil, (0, 0))
        self.screen.fill((0, 0, 0))
        self.screen.blit(surf, (ox, oy))

    def present(self):
        if self.renderer is not None:
            try:
                size = None if self.headless else pygame.display.get_window_size()
                self.renderer.present(self.canvas, self.fx, self.post, size, self.ui if self.ui_used else None)
            except Exception as exc:
                # A lost context or driver hiccup: keep the game running.
                print(f"[renderer] {exc}; switching to the classic renderer")
                self.gl_failed = True
                self.set_renderer("classic", persist=False)
                return
        if not self.headless or self.renderer is None:
            pygame.display.flip()

    def run(self):
        while self.running and self.scenes:
            ms = self.clock.tick(144) if self.vsync else self.clock.tick(FPS)
            self.acc += min(ms / 1000.0, 0.1)
            self.handle_events()
            steps = 0
            while self.acc >= DT and steps < 4:
                self.step(DT)
                self.acc -= DT
                steps += 1
            if steps == 4:
                self.acc = 0.0
            self.render()
            self.present()
        self.save.write()
        pygame.quit()


def main():
    app = App(headless=bool(os.environ.get("DND_HEADLESS")))
    from .scenes.title import TitleScene

    app.push(TitleScene(app))
    app.run()
