"""Window, main loop (fixed 60 Hz logic), scene stack and transitions."""

import os

import pygame

from .config import DT, FPS, H, TITLE, VERSION, W, resource_path
from .inputs import Input
from .save import SaveData


class App:
    def __init__(self, headless=False, save_path=None):
        self.headless = headless
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
        from .post import Post

        self.audio = Audio(self.save)
        self.post = Post(self.save.settings)
        self.scenes = []
        self.fading = None  # [t, duration, phase, action]
        self.running = True
        self.acc = 0.0

    # ------------------------------------------------------------------
    def set_display(self, fullscreen):
        self.fullscreen = fullscreen
        self.vsync = False
        if self.headless:
            self.screen = pygame.display.set_mode((W, H))
            return
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        # Logic runs at a fixed 60 Hz. VSync only paces frames nicely on a
        # 60 Hz screen; elsewhere the clock caps the frame rate instead.
        try:
            rates = pygame.display.get_desktop_refresh_rates()
        except (AttributeError, pygame.error):
            rates = []
        want_vsync = bool(rates) and 58 <= rates[0] <= 61
        if want_vsync:
            try:
                self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
                self.vsync = True
                return
            except pygame.error:
                pass
        self.screen = pygame.display.set_mode((W, H), flags)

    def toggle_fullscreen(self):
        if self.headless:
            return
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

    def fade(self, action, duration=0.28):
        if self.fading is None:
            self.fading = [0.0, duration, "out", action]

    def quit(self):
        self.running = False

    # ------------------------------------------------------------------
    def step(self, dt=DT):
        """One logic tick."""
        self.post.update()
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
        # Draw from the lowest visible scene up.
        start = len(self.scenes) - 1
        while start > 0 and self.scenes[start].transparent:
            start -= 1
        for sc in self.scenes[start:]:
            sc.draw(surf)
        self.post.apply(surf)
        if self.fading is not None:
            t, dur, phase, _ = self.fading
            k = min(1.0, t / dur)
            a = k if phase == "out" else 1 - k
            veil = pygame.Surface((W, H))
            veil.fill((6, 2, 12))
            veil.set_alpha(int(255 * a))
            surf.blit(veil, (0, 0))
        ox, oy = self.scene.shake_offset() if self.scene else (0, 0)
        self.screen.fill((0, 0, 0))
        self.screen.blit(surf, (ox, oy))

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
            pygame.display.flip()
        self.save.write()
        pygame.quit()


def main():
    app = App(headless=bool(os.environ.get("DND_HEADLESS")))
    from .scenes.title import TitleScene

    app.push(TitleScene(app))
    app.run()
