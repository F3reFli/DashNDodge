"""GPU renderer: the 640x360 canvas goes through OpenGL shaders (bloom, god
rays, 2D lighting, shockwave refraction, colour grading, vignette, grain,
scanlines, CRT curvature) and is upscaled with sharp-bilinear filtering.

Everything degrades gracefully: if OpenGL or moderngl is unavailable the
App falls back to the classic CPU renderer."""

import struct

import pygame

from . import shaders
from .config import H, W
from .screenfx import LIGHT_H, LIGHT_W, MAX_WAVES

try:
    import moderngl
except ImportError:  # pragma: no cover - optional dependency
    moderngl = None

BLOOM_LEVELS = {0: 0.0, 1: 0.5, 2: 0.85}


class GLRenderer:
    def __init__(self, settings, headless=False, size=(1280, 720)):
        if moderngl is None:
            raise RuntimeError("moderngl is not installed")
        self.settings = settings
        self.headless = headless
        if headless:
            try:
                self.ctx = moderngl.create_standalone_context(backend="egl")
            except Exception:
                self.ctx = moderngl.create_standalone_context()
            self.offscreen_size = size
        else:
            self.ctx = moderngl.create_context()
            self.offscreen_size = None
        ctx = self.ctx
        self._objects = []
        quad = self._keep(ctx.buffer(struct.pack("8f", -1, -1, 1, -1, -1, 1, 1, 1)))
        self.progs = {}
        self.vaos = {}
        for name in ("BRIGHT", "BLUR", "RAYS", "COMPOSITE"):
            prog = self._keep(ctx.program(vertex_shader=shaders.VERT, fragment_shader=getattr(shaders, name)))
            self.progs[name] = prog
            self.vaos[name] = self._keep(ctx.vertex_array(prog, [(quad, "2f", "in_pos")]))
        self.scene = self._tex((W, H), filtered=True)
        self.light = self._tex((LIGHT_W, LIGHT_H), filtered=True)
        self.half = [self._target((W // 2, H // 2)) for _ in range(3)]  # bright, ping, pong
        self.quarter = [self._target((W // 4, H // 4)) for _ in range(2)]
        self.black = self._target((4, 4))
        self.black[1].clear(0.0, 0.0, 0.0)
        self.out = self._target(size) if headless else None
        c = self.progs["COMPOSITE"]
        for unit, name in enumerate(("u_scene", "u_light", "u_bloom1", "u_bloom2", "u_rays", "u_ui")):
            c[name].value = unit
        self.ui = self._keep(self.ctx.texture((W, H), 4))
        self.ui.repeat_x = self.ui.repeat_y = False
        self.ui.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._light_count = -1

    # ------------------------------------------------------------------
    def _keep(self, obj):
        self._objects.append(obj)
        return obj

    def _tex(self, size, filtered):
        t = self._keep(self.ctx.texture(size, 3))
        t.repeat_x = t.repeat_y = False
        f = moderngl.LINEAR if filtered else moderngl.NEAREST
        t.filter = (f, f)
        return t

    def _target(self, size):
        t = self._tex(size, True)
        return t, self._keep(self.ctx.framebuffer(color_attachments=[t]))

    def release(self):
        """Free every GL object (the window's context may be reused)."""
        for obj in reversed(self._objects):
            try:
                obj.release()
            except Exception:
                pass
        self._objects = []
        if self.headless:
            try:
                self.ctx.release()
            except Exception:
                pass

    def _pass(self, name, target, **uniforms):
        tex, fbo = target
        fbo.use()
        fbo.viewport = (0, 0, *tex.size)
        prog = self.progs[name]
        for k, v in uniforms.items():
            prog[k].value = v
        self.vaos[name].render(moderngl.TRIANGLE_STRIP)

    def _blur(self, src, ping, dst):
        w, h = src[0].size
        src[0].use(0)
        self._pass("BLUR", ping, u_src=0, u_dir=(1.0 / w, 0.0))
        ping[0].use(0)
        self._pass("BLUR", dst, u_src=0, u_dir=(0.0, 1.0 / h))

    # ------------------------------------------------------------------
    def present(self, canvas, fx, post, window_size=None, ui=None):
        s = self.settings
        bloom_k = BLOOM_LEVELS.get(s.get("bloom", 2), 1.0) * fx.grade.bloom
        lighting = s.get("lighting", True)
        effects = s.get("effects", True)

        self.scene.write(pygame.image.tobytes(canvas, "RGB"))
        if lighting and fx.lights.count:
            self.light.write(pygame.image.tobytes(fx.lights.surf, "RGB"))
            self._light_count = fx.lights.count
        elif self._light_count != 0:
            self.light.write(bytes(LIGHT_W * LIGHT_H * 3))
            self._light_count = 0

        bright, ping, pong = self.half
        q_ping, q_out = self.quarter
        if bloom_k > 0:
            self.scene.use(0)
            self._pass("BRIGHT", bright, u_src=0, u_threshold=0.7)
        if bloom_k > 0:
            self._blur(bright, ping, pong)  # half-res bloom -> pong
            pong[0].use(0)
            self._blur(pong, q_ping, q_out)  # quarter-res bloom -> q_out
        rays = self.black
        if fx.godray and effects:
            x, y, strength, color = fx.godray
            self.scene.use(0)
            self._pass("RAYS", ping, u_src=0, u_pos=(x / W, 1.0 - y / H), u_density=0.9,
                       u_color=tuple(c / 255 * strength for c in color))
            rays = ping

        # --- composite into the window (letterboxed) or the offscreen target
        if self.out is not None:
            out_w, out_h = self.out[0].size
            fbo = self.out[1]
        else:
            out_w, out_h = window_size
            fbo = self.ctx.screen
        scale = min(out_w / W, out_h / H)
        vw, vh = int(W * scale), int(H * scale)
        fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0)
        fbo.viewport = ((out_w - vw) // 2, (out_h - vh) // 2, vw, vh)

        self.scene.use(0)
        self.light.use(1)
        (pong[0] if bloom_k > 0 else self.black[0]).use(2)
        (q_out[0] if bloom_k > 0 else self.black[0]).use(3)
        rays[0].use(4)
        if ui is not None:
            self.ui.write(pygame.image.tobytes(ui, "RGBA"))
            self.ui.use(5)
        c = self.progs["COMPOSITE"]
        g = fx.grade
        waves = fx.waves[:MAX_WAVES] if effects else []
        packed = [0.0] * (MAX_WAVES * 4)
        strengths = [0.0] * MAX_WAVES
        for i, (x, y, r, thick, st) in enumerate(waves):
            packed[i * 4:i * 4 + 4] = (x, y, r, max(1.0, thick))
            strengths[i] = st
        c["u_has_ui"].value = 1.0 if ui is not None else 0.0
        c["u_tex"].value = (float(W), float(H))
        c["u_scale"].value = (vw / W, vh / H)
        c["u_offset"].value = fx.offset
        c["u_time"].value = fx.t % 1000.0
        c["u_waves"].write(struct.pack(f"{MAX_WAVES * 4}f", *packed))
        c["u_wave_str"].write(struct.pack(f"{MAX_WAVES}f", *strengths))
        c["u_nwaves"].value = len(waves)
        c["u_impact"].value = fx.impact if effects else 0.0
        c["u_impact_pos"].value = fx.impact_pos
        c["u_aberr"].value = float(post.aberr_px * min(1.0, post.aberr_t / 8)) if (effects and post.aberr_t) else 0.0
        c["u_haze"].value = fx.haze if effects else 0.0
        c["u_exposure"].value = g.exposure
        c["u_contrast"].value = g.contrast
        c["u_saturation"].value = g.saturation
        c["u_shadows"].value = g.shadows
        c["u_highlights"].value = g.highlights
        c["u_desat"].value = fx.desaturate
        c["u_bloom"].value = bloom_k
        c["u_light_k"].value = 1.0 if lighting else 0.0
        c["u_rays_k"].value = 1.0 if (fx.godray and effects) else 0.0
        c["u_vignette"].value = fx.vignette
        c["u_danger"].value = fx.danger
        c["u_grain"].value = 1.0 if effects else 0.0
        c["u_scan"].value = 1.0 if s.get("scanlines", True) else 0.0
        c["u_crt"].value = 1.0 if s.get("crt", False) else 0.0
        if fx.dissolve is not None:
            c["u_dissolve"].value = fx.dissolve[0]
            c["u_dissolve_col"].value = tuple(v / 255 for v in fx.dissolve[1])
        else:
            c["u_dissolve"].value = -1.0
        self.vaos["COMPOSITE"].render(moderngl.TRIANGLE_STRIP)

    def snapshot(self):
        """The last offscreen frame as a pygame Surface (headless only)."""
        tex = self.out[0]
        data = tex.read()
        surf = pygame.image.frombytes(data, tex.size, "RGB")
        return pygame.transform.flip(surf, False, True)
