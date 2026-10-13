"""The gameplay scene: ties player, enemies, bosses, bullets, items,
incidents, effects and the stage scripts together."""

import math
import random

import pygame

from . import assets, backgrounds, charms, gfx, incidents, spellbg, stages
from .boss import Boss
from .bullets import Bullets
from .characters import BY_ID
from .config import ACCENT, FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, GOLD, H, PALETTE, TEXT, TEXT_DIM, W
from .dialogues import lines_for
from .fx import Banner, Flash, FloatTexts, Particles, Shake, Shockwaves
from .items import Items
from .player import Player
from .scene import Scene
from .script import Tasks
from .ui import HUD, BossIntro, CutIn, Dialogue, MusicToast, StageTitle
from .util import TAU, angle_to, clamp, fmt_score, scale_color

DIFFICULTY = ["Easy", "Normal", "Hard", "Lunatic"]
DIFF_COLORS = [(120, 230, 140), (120, 180, 255), (255, 170, 80), (255, 80, 160)]
DIFF_SCORE = [0.5, 1.0, 1.5, 2.0]


class Tally:
    """Stage-clear bonus breakdown."""

    def __init__(self, game, rows, title="Stage Clear!"):
        self.g = game
        self.rows = rows
        self.title = title
        self.total = sum(v for _l, _d, v in rows)
        self.t = 0.0
        self.done = False

    def update(self, dt):
        self.t += dt
        inp = self.g.app.input
        if self.t > 4.5 or (self.t > 1.2 and inp.was_pressed("confirm")):
            self.done = True

    def draw(self, surf):
        a = min(1.0, self.t / 0.3)
        panel = pygame.Surface((300, 40 + 16 * (len(self.rows) + 2)), pygame.SRCALPHA)
        panel.fill((8, 4, 16, int(200 * a)))
        x0 = W / 2 - panel.get_width() / 2
        y0 = 70
        surf.blit(panel, (x0, y0))
        pygame.draw.rect(surf, scale_color(GOLD, a), (x0, y0, panel.get_width(), panel.get_height()), 1)
        assets.blit_text(surf, self.title, (W / 2, y0 + 8), 24, GOLD, "midtop", alpha=255 * a)
        for i, (label, detail, value) in enumerate(self.rows):
            k = clamp((self.t - 0.4 - i * 0.25) / 0.3, 0, 1)
            if k <= 0:
                continue
            y = y0 + 40 + i * 16
            assets.blit_text(surf, label, (x0 + 14, y), 12, TEXT, alpha=255 * k)
            assets.blit_text(surf, detail, (x0 + 130, y), 12, TEXT_DIM, alpha=255 * k)
            assets.blit_text(surf, fmt_score(int(value * k)), (x0 + panel.get_width() - 14, y), 12, TEXT, "topright", alpha=255 * k)
        k = clamp((self.t - 0.6 - len(self.rows) * 0.25) / 0.4, 0, 1)
        if k > 0:
            y = y0 + 44 + len(self.rows) * 16
            pygame.draw.line(surf, TEXT_DIM, (x0 + 14, y - 2), (x0 + panel.get_width() - 14, y - 2))
            assets.blit_text(surf, "Total", (x0 + 14, y + 2), 12, GOLD, alpha=255 * k)
            assets.blit_text(surf, fmt_score(int(self.total * k)), (x0 + panel.get_width() - 14, y + 2), 12, GOLD, "topright", alpha=255 * k)


class GameScene(Scene):
    CHAIN_TIME = 150

    def __init__(self, app, mode="story", char_id="reimu", difficulty=1, start_stage=0, practice=None, continues=0,
                 charm_ids=()):
        super().__init__(app)
        self.practice = practice
        self.continues = continues
        self.picker = None
        self.save = app.save
        self.mode = mode
        self.cdef = BY_ID[char_id]
        self.diff = difficulty
        self.speed_mult = (0.85, 1.0, 1.12, 1.25)[difficulty]
        self.rng = random.Random()
        self.add = pygame.Surface((W, H))
        self.player = Player(self, self.cdef)
        self.bullets = Bullets(self)
        self.items = Items(self)
        self.enemies = []
        self.boss = None
        self.particles = Particles()
        self.texts = FloatTexts()
        self.waves = Shockwaves()
        self.shake = Shake()
        self.shake.scale = self.save.settings.get("screen_shake", 1.0)
        self.flash = Flash()
        self.tasks = Tasks()
        self.hud = HUD(self)
        self.frame = 0
        self.score = 0
        self.chain = 0
        self.chain_timer = 0
        self.graze = 0
        self.stats = {k: 0 for k in ("grazes", "parries", "reflects", "kills", "hits", "spells", "photos", "dashes",
                                      "captures", "cards", "max_chain", "frames", "naps")}
        self.hitstop = 0
        self.timestop = 0
        self.timestop_owner = None
        self.invert_t = 0
        self.slow = 1.0
        self.wrap = False
        self.ice = False
        self.visible = None
        self.darkness = 0
        self.red_mist = 0
        self.freeze_tint = 0
        self.score_mult = 1
        self.player_spells = []
        self.telegraphs = []
        self.overlays = []
        self.cutins = []
        self.photo_flashes = []
        self.dialogue = None
        self.incident = None
        self.incident_active = False
        self.used_incidents = []
        self.state = "play"
        self.death_t = 0
        self.last_hit_source = None
        self.killer_hint = None
        self.killer = "a stray bullet"
        self.photo = None
        self.want_photo = False
        self.boss_explosion = None
        self.kills_since_heal = 0
        self.hint = None
        self.hint_t = 0.0
        self.hint_total = 1.0
        self.debug = False
        self.god = False
        self.spell_dark = 0.0
        self.spell_bg = None
        self.dimmer = pygame.Surface((W, H))
        self.dimmer.fill((0, 0, 0))
        self.pending_stage = None
        self.stage_graze_start = 0
        self.bosses_beaten = 0
        if mode == "story":
            self.stage_list = stages.STORY
        elif mode == "extra":
            self.stage_list = [stages.EXTRA]
        elif mode == "practice":
            self.stage_list = [stages.practice_stage(*practice)]
        else:
            self.stage_list = [stages.ENDLESS]
        for cid in charm_ids:
            if cid in charms.BY_ID:
                charms.give(self, charms.BY_ID[cid])
        self.stage = None
        self.stage_i = start_stage
        self.stage_label = ""
        self.start_stage(start_stage)

    # ==================================================================
    # Helpers used by scripts and patterns
    # ==================================================================
    def d(self, easy, normal, hard, lunatic):
        return (easy, normal, hard, lunatic)[self.diff]

    def sfx(self, name):
        self.app.audio.play(name)

    def aim(self, x, y):
        return math.atan2(self.player.y - y, self.player.x - x)

    def spawn_enemy(self, e):
        self.enemies.append(e)
        return e

    def all_enemies(self):
        out = [e for e in self.enemies if e.alive]
        if self.boss is not None and self.boss.alive:
            out.append(self.boss)
        return out

    def nearest_target(self, x, y, rank=0):
        cands = [e for e in self.enemies if e.alive and e.hittable and -10 < e.x < W + 10 and -10 < e.y < H + 10]
        if self.boss is not None and self.boss.alive and self.boss.hittable:
            cands.append(self.boss)
        if not cands:
            return None
        cands.sort(key=lambda e: (e.x - x) ** 2 + (e.y - y) ** 2)
        return cands[rank % len(cands)]

    def damage_area(self, x, y, r, dmg, boss_damage=None):
        for e in self.all_enemies():
            if (e.x - x) ** 2 + (e.y - y) ** 2 < (r + e.r) ** 2:
                e.damage(boss_damage if (e.is_boss and boss_damage is not None) else dmg, "spell")

    def telegraph_line(self, x, y, angle, frames, color):
        self.telegraphs.append(["line", x, y, angle, frames, frames, color])

    def telegraph_circle(self, x, y, r, frames, color):
        self.telegraphs.append(["circle", x, y, r, frames, frames, color])

    def start_timestop(self, frames, owner="boss"):
        self.timestop = frames
        self.timestop_owner = owner
        self.invert_t = 8
        self.sfx("timestop")

    def show_hint(self, text, seconds=5.0):
        self.hint = text
        self.hint_t = seconds
        self.hint_total = seconds

    def chain_mult(self):
        return 1.0 + min(self.chain, 200) / 50.0

    def bump_chain(self, n=1):
        self.chain += n
        self.chain_timer = self.CHAIN_TIME
        if self.chain > self.stats["max_chain"]:
            self.stats["max_chain"] = self.chain

    def add_score(self, points, x=None, y=None, show=False, mult=True, color=GOLD):
        pts = points * (self.chain_mult() if mult else 1.0) * self.score_mult * DIFF_SCORE[self.diff]
        pts = int(pts) // 10 * 10
        self.score += pts
        if show and x is not None:
            self.texts.add(fmt_score(pts), x, y, color, 12, 1.0)
        return pts

    # ==================================================================
    # Stage flow
    # ==================================================================
    def start_stage(self, i):
        self.stage_i = i
        st = self.stage_list[i]
        self.stage = st
        self.bg = backgrounds.get(st.bg)
        self.stage_label = f"{st.label} - {st.name}"
        self.tasks.clear()
        for e in self.enemies:
            e.remove()
        self.enemies = []
        self.bullets.clear()
        self.boss = None
        self.end_incident()
        self.overlays.append(StageTitle(st.label, st.name, st.jp, st.sub, st.glyph))
        self.app.post.glitch(12, 0.6)
        self.tasks.spawn(st.script(self))
        key = st.music or (f"stage{st.num}" if isinstance(st.num, int) else self.mode)
        name = self.app.audio.play_music([key])
        if name:
            self.overlays.append(MusicToast(name))
        self.stage_graze_start = self.graze
        self.state = "play"

    def wait_clear(self, timeout=360):
        n = 0
        while any(e.alive for e in self.enemies) and n < timeout:
            n += 1
            yield 1

    def boss_sequence(self, bdef, dialogue=True, hp_mult=1.0, x=W / 2, y=100):
        midboss = bdef.midboss
        yield from self.wait_clear(180 if midboss else 300)
        for e in self.enemies:
            if e.alive:
                e.die()
        if not midboss:
            self.end_incident()
        self.bullets.cancel_all(True)
        b = Boss(self, bdef, x=W / 2, y=-40, hp_mult=hp_mult * (0.85, 1.0, 1.1, 1.2)[self.diff])
        self.boss = b
        b.go(x, y, 70)
        self.overlays.append(BossIntro(bdef, short=midboss))
        self.sfx("boss_intro")
        self.app.post.glitch(16, 0.9)
        self.app.post.aberration(20, 3)
        yield 75 if not midboss else 60
        b.state = "idle"
        if midboss:
            b.start()
            while b.alive:
                yield 1
            return
        lines = lines_for(bdef.id, self.cdef.id) if dialogue else []
        if lines:
            self.dialogue = Dialogue(self, lines, self.cdef, bdef)
            while self.dialogue is not None and not self.dialogue.done:
                yield 1
            self.dialogue = None
        name = self.app.audio.play_music([f"boss_{bdef.id}", "boss"], fade_ms=400, keep_if_missing=True)
        if name:
            self.overlays.append(MusicToast(name))
        b.start()
        while b.alive:
            yield 1

    def charm_pick(self):
        choices = charms.offer(self.player.charms, self.rng)
        if not choices:
            return
        self.picker = charms.CharmPick(self, choices)
        while self.picker is not None:
            yield 1

    def stage_clear(self):
        yield 100
        self.items.collect_all()
        yield 50
        p = self.player
        st = self.stage
        num = st.num if isinstance(st.num, int) else 7
        rows = [
            ("Graze", f"{self.graze - self.stage_graze_start} x 500", (self.graze - self.stage_graze_start) * 500),
            ("Hearts", f"{p.hearts} x 200 000", p.hearts * 200_000),
            ("Spell stock", f"{int(p.spell // 100)} x 100 000", int(p.spell // 100) * 100_000),
            ("Clear bonus", f"Stage {st.num}", num * 500_000),
        ]
        mult = DIFF_SCORE[self.diff]
        rows = [(lbl, det, int(v * mult)) for lbl, det, v in rows]
        tally = Tally(self, rows)
        self.score += tally.total
        self.overlays.append(tally)
        self.sfx("capture")
        while not tally.done:
            yield 1
        if self.stage_i + 1 < len(self.stage_list):
            yield from self.charm_pick()
            self.pending_stage = self.stage_i + 1
        else:
            self.finish(cleared=True)

    def finish(self, cleared):
        from .scenes.results import NewspaperScene, VictoryScene

        if self.photo is None:
            self.want_photo = True
            self.draw(pygame.Surface((W, H)))

        result = self.result(cleared)
        if self.mode == "practice":
            from .scenes.practice import PracticeScene

            self.app.replace(PracticeScene(self.app, self.practice))
            return
        if cleared:
            self.app.replace(VictoryScene(self.app, result))
        else:
            self.app.replace(NewspaperScene(self.app, result))

    def result(self, cleared):
        self.stats["frames"] = self.frame
        st = self.stage
        return {
            "mode": self.mode,
            "char": self.cdef.id,
            "difficulty": self.diff,
            "score": self.score,
            "stage": self.stage_label.split(" - ")[-1] if self.mode == "endless" else st.label,
            "stage_name": st.name,
            "stage_num": st.num,
            "killer": self.killer,
            "stats": dict(self.stats, graze=self.graze),
            "photo": self.photo,
            "cleared": cleared,
            "time": self.frame / 60.0,
            "stage_index": self.stage_i,
            "charms": list(self.player.charms),
            "continues": self.continues,
        }

    # ==================================================================
    # Incidents
    # ==================================================================
    def start_incident(self, inc_id=None):
        if self.incident is not None:
            return
        pool = [c for c in incidents.ALL if c.id not in self.used_incidents] or list(incidents.ALL)
        if self.cdef.id in [c.id for c in pool] and len(pool) > 1:
            pool = [c for c in pool if c.id != self.cdef.id]
        cls = incidents.BY_ID.get(inc_id) if inc_id else self.rng.choice(pool)
        self.used_incidents.append(cls.id)
        if len(self.used_incidents) >= len(incidents.ALL):
            self.used_incidents = []
        self.incident = cls(self)
        self.incident_active = False
        self.incident_delay = 150
        self.overlays.append(Banner(f"異変発生!  {cls.title}", cls.desc, cls.color, 2.6, y=H // 2 - 30))
        self.sfx("incident")
        self.app.post.glitch(14, 0.8)

    def end_incident(self):
        if self.incident is not None:
            if self.incident_active:
                self.incident.end()
            self.incident = None
            self.incident_active = False
        self.visible = None
        self.wrap = False
        self.ice = False
        self.score_mult = 1

    # ==================================================================
    # Combat events
    # ==================================================================
    def on_graze(self, b):
        p = self.player
        self.graze += 1
        self.stats["grazes"] += 1
        dash = p.dashing()
        pts = 120 * (2 if dash else 1)
        if self.cdef.id == "cirno" and self.graze % 9 == 0:
            pts *= 9
            self.texts.add("⑨", b.x, b.y - 8, (120, 230, 255), 12, 0.7)
        self.add_score(pts)
        p.spell = min(p.max_spell, p.spell + (2.6 if dash else 1.5) * p.spell_gain)
        self.bump_chain()
        self.sfx("graze")
        a = angle_to(p.x, p.y, b.x, b.y)
        for _ in range(2):
            s = random.uniform(60, 140)
            aa = a + random.uniform(-0.5, 0.5)
            self.particles.emit(b.x, b.y, math.cos(aa) * s, math.sin(aa) * s, 0.25, 2, (255, 255, 255), "spark", drag=4)

    def try_parry(self, p):
        cands = self.bullets.in_radius(p.x, p.y, p.parry_r)
        n = 0
        for b in cands:
            t = self.nearest_target(b.x, b.y)
            a = angle_to(b.x, b.y, t.x, t.y) if t else angle_to(p.x, p.y, b.x, b.y)
            self.bullets.reflect(b, a, 360)
            n += 1
        if n:
            self._parry_effects(p, n)
        return n

    def _parry_effects(self, p, n):
        first = p.parry_hits == 0
        if first:
            self.hitstop = max(self.hitstop, 4)
            self.sfx("parry")
            self.waves.add(p.x, p.y, 46, 0.3, (255, 210, 90), 3)
            self.flash.trigger((255, 230, 160), 50, 500)
            self.texts.add("PARRY!", p.x, p.y - 24, GOLD, 12, 0.8)
            self.stats["parries"] += 1
        self.particles.burst(p.x, p.y, 4 + n * 2, (255, 210, 90), (80, 200), kind="spark", size=(1, 3))
        p.spell = min(p.max_spell, p.spell + 2.5 * n * p.spell_gain)
        self.add_score(300 * n)
        self.bump_chain(n)
        self.stats["reflects"] += n
        p.iframes = max(p.iframes, 18)

    def dash_strike(self, e):
        p = self.player
        e.damage((4.0 if e.is_boss else 3.5) * p.dash_dmg_mult, "dash")
        self.hitstop = max(self.hitstop, 2)
        self.particles.burst(e.x, e.y, 10, self.cdef.color, (60, 180), kind="spark", size=(1, 3))
        self.waves.add(e.x, e.y, 22, 0.2, (255, 255, 255), 2)
        self.add_score(200)
        self.bump_chain()
        self.sfx("shot2")
        if e.is_boss:
            p.dash_t = 0
            a = angle_to(e.x, e.y, p.x, p.y)
            p.x = clamp(p.x + math.cos(a) * 18, FIELD_LEFT, FIELD_RIGHT)
            p.y = clamp(p.y + math.sin(a) * 18, FIELD_TOP + 6, FIELD_BOTTOM)
            p.iframes = max(p.iframes, 20)

    def parry_body(self, e):
        p = self.player
        e.damage(3.0 if e.is_boss else 4.0, "parry")
        if not e.is_boss:
            a = angle_to(p.x, p.y, e.x, e.y)
            e.x += math.cos(a) * 20
            e.y += math.sin(a) * 20
        self._parry_effects(p, 1)
        p.parry_hits += 1

    def on_friendly_hit(self, b, e):
        dmg = b.damage * (0.6 if e.is_boss else 1.0) * self.player.reflect_mult
        e.damage(dmg, "reflect")
        self.particles.burst(b.x, b.y, 3, (255, 220, 120), (40, 120), kind="spark", size=(1, 2))
        self.add_score(100)

    def on_enemy_killed(self, e):
        self.stats["kills"] += 1
        self.add_score(e.points)
        for kind, n in e.drops:
            self.items.spawn(kind, e.x, e.y, n)
        r = self.rng.random()
        if r < 0.07:
            self.items.spawn("spell", e.x, e.y)
        elif r < 0.07 + 0.02 * self.player.heart_luck and self.player.hearts < self.player.max_hearts:
            self.items.spawn("heart", e.x, e.y)
        col = PALETTE.get(e.color, PALETTE["white"])[0]
        self.particles.burst(e.x, e.y, 14, col, (40, 160), kind="spark", size=(1, 3))
        self.particles.burst(e.x, e.y, 5, col, (10, 50), kind="glow", size=(4, 7))
        self.waves.add(e.x, e.y, 20, 0.25, col, 2)
        self.sfx("kill")
        self.bump_chain()
        if self.cdef.id == "remilia":
            self.kills_since_heal += 1
            if self.kills_since_heal >= 20:
                self.kills_since_heal = 0
                if self.player.hearts < self.player.max_hearts:
                    self.player.hearts += 1
                    self.texts.add("+1 ♥", self.player.x, self.player.y - 24, (255, 90, 120), 12, 1.0)
                    self.sfx("heal")

    def collect(self, it):
        p = self.player
        k = it.kind
        if k == "point":
            self.add_score((1500 + int(2500 * max(0.0, 1 - it.age / 5))) * p.item_mult)
            self.sfx("item")
        elif k == "big":
            self.add_score(10000 * p.item_mult, it.x, it.y - 10, show=True)
            self.sfx("item")
        elif k == "mini":
            self.add_score(100)
            self.sfx("item")
        elif k == "spell":
            p.spell = min(p.max_spell, p.spell + 12 * p.spell_gain)
            self.texts.add("+Spell", it.x, it.y - 10, (120, 255, 140), 12, 0.8)
            self.sfx("item")
        elif k == "heart":
            if p.hearts < p.max_hearts:
                p.hearts += 1
                self.texts.add("+1 ♥", it.x, it.y - 12, (255, 90, 120), 12, 1.0)
            else:
                self.add_score(50000, it.x, it.y - 12, show=True)
                self.texts.add("MAX!", it.x, it.y - 24, (255, 90, 120), 12, 1.0)
            self.particles.burst(it.x, it.y, 10, (255, 90, 120), (30, 90), kind="glow", size=(2, 4))
            self.sfx("heal")
        elif k == "fake_heart":
            incidents.tewi_trap(self, it.x, it.y)

    def player_spell(self, deathbomb=False):
        p = self.player
        if not p.alive or self.state != "play":
            return False
        if p.spell < 100:
            if not deathbomb:
                self.sfx("parry_fail")
                self.texts.add("No spell!", p.x, p.y - 22, TEXT_DIM, 12, 0.7)
                p.spell_cd = 20
            return False
        p.spell -= 100
        p.spell_cd = 40
        self.stats["spells"] += 1
        if self.boss is not None:
            self.boss.card_clean = False
        self.player_spells.append(self.cdef.spell_cls(self, p))
        self.cutins.append(CutIn(self.cdef.sprite, self.cdef.color, self.cdef.spell_name, from_right=False))
        self.sfx("spell")
        self.shake.add(3)
        if deathbomb:
            self.texts.add("DEATHBOMB!", p.x, p.y - 26, ACCENT, 12, 1.0)
        return True

    def on_player_damaged(self):
        p = self.player
        self.stats["hits"] += 1
        self.chain = 0
        self.chain_timer = 0
        self.sfx("pichuun")
        self.app.post.glitch(10, 0.7)
        self.app.post.aberration(16, 3)
        self.shake.add(9)
        self.hitstop = max(self.hitstop, 8)
        self.particles.burst(p.x, p.y, 30, self.cdef.color, (60, 240), kind="spark", size=(1, 3))
        self.particles.burst(p.x, p.y, 8, (255, 255, 255), (20, 80), kind="glow", size=(4, 8))
        self.waves.add(p.x, p.y, 90, 0.5, (255, 255, 255), 4)
        self.bullets.cancel_all(False, p.x, p.y, 100)
        if self.boss is not None:
            self.boss.card_clean = False

    def on_player_death(self):
        p = self.player
        self.state = "dying"
        self.death_t = 0
        self.want_photo = True
        self.killer = self.resolve_killer()
        self.app.audio.fade_music(1800)
        self.sfx("explode")
        self.app.post.glitch(45, 1.2)
        self.app.post.aberration(70, 4)
        self.shake.add(14)
        self.flash.trigger((255, 255, 255), 230, 260)
        for i in range(3):
            self.waves.add(p.x, p.y, 120 + i * 60, 0.6 + i * 0.2, self.cdef.color, 4)
        self.particles.burst(p.x, p.y, 60, self.cdef.color, (60, 300), kind="spark", size=(1, 4), life=(0.4, 1.0))
        self.save.stats["deaths"] = self.save.stats.get("deaths", 0) + 1

    def resolve_killer(self):
        src = self.last_hit_source
        if self.killer_hint and self.frame - self.killer_hint[1] < 240:
            return self.killer_hint[0]
        if src is not None and hasattr(src, "is_boss"):
            if src.is_boss:
                return src.d.name
            if getattr(src, "clone", False):
                return "Flandre Scarlet (a clone of)"
            return "a kedama" if src.kedama else "a fairy"
        if self.boss is not None:
            return self.boss.d.name
        if self.incident is not None:
            return self.incident.who
        return "a fairy"

    def on_meiling_nap(self):
        self.stats["naps"] += 1
        p = self.player
        self.texts.add("Zzz...", p.x, p.y - 24, (200, 220, 255), 12, 1.4)
        self.tasks.spawn(self._sakuya_wakeup())

    def _sakuya_wakeup(self):
        yield 100
        p = self.player
        if not p.asleep or not p.alive:
            return
        a = random.uniform(0, TAU)
        x, y = p.x + math.cos(a) * 340, p.y + math.sin(a) * 340
        self.texts.add("Sakuya: MEILING.", W / 2, 60, (190, 200, 255), 12, 1.8)
        b = self.bullets.shoot(x, y, 420, angle_to(x, y, p.x, p.y), "knife", "cyan", grace=120)
        b.data = "sakuya"

    # ==================================================================
    # Spell cards (boss side)
    # ==================================================================
    def declare_spell(self, boss):
        self.spell_bg = spellbg.get(boss.d.id, boss.d.color)
        self.app.post.glitch(8, 0.5)
        self.app.post.aberration(12, 2)
        self.cutins.append(CutIn(boss.d.sprite, boss.d.color, boss.card.name, True))
        self.sfx("spell")
        self.flash.trigger(scale_color(boss.d.color, 0.8), 70, 400)
        self.slow = 1.0
        self.darkness = 0
        self.red_mist = 0
        self.stats["cards"] += 1

    def card_bonus_value(self, boss):
        card = boss.card
        if card.survival:
            v = card.bonus
        else:
            v = card.bonus * (0.35 + 0.65 * max(0, boss.card_time) / (card.time * 60))
        return int(v * DIFF_SCORE[self.diff]) // 10 * 10

    def end_spell(self, boss, captured, timeout):
        self.bullets.cancel_all(True)
        for e in self.enemies:
            if getattr(e, "clone", False) and e.alive:
                self.particles.burst(e.x, e.y, 16, (255, 120, 120), (40, 140), kind="glow", size=(2, 5))
                e.remove()
        self.slow = 1.0
        self.darkness = 0
        self.red_mist = 0
        if self.timestop_owner == "boss":
            self.timestop = 0
            self.timestop_owner = None
        self.items.collect_all()
        if captured:
            bonus = self.card_bonus_value(boss)
            self.score += bonus
            self.overlays.append(Banner("Get Spell Card Bonus!!", fmt_score(bonus), GOLD, 2.2, y=96))
            self.particles.burst(W / 2, 96, 40, (255, 220, 120), (60, 260), kind="spark", size=(1, 3))
            self.sfx("capture")
            self.stats["captures"] += 1
            p = self.player
            if p.regen_capture and p.hearts < p.max_hearts:
                p.hearts += 1
                self.texts.add("+1 ♥", p.x, p.y - 24, (255, 90, 120), 12, 1.0)
        else:
            self.overlays.append(Banner("Bonus Failed...", "", TEXT_DIM, 1.4, y=96, size=12))
        self.save.record_card(boss.card.name, captured)
        self.sfx("card_break")
        self.waves.add(boss.x, boss.y, 160, 0.6, boss.d.color, 4)
        self.shake.add(5)

    def on_boss_defeated(self, boss):
        if boss.d.midboss:
            self.bullets.cancel_all(True)
            if boss.escaped:
                self.texts.add("Escaped...", boss.x, boss.y - 24, TEXT_DIM, 12, 1.4)
                self.particles.burst(boss.x, boss.y, 30, boss.d.color, (40, 200), kind="glow", size=(2, 5))
                self.sfx("whoosh")
            else:
                self.sfx("explode")
                self.app.post.aberration(18, 3)
                self.flash.trigger((255, 255, 255), 150, 400)
                self.shake.add(8)
                for i in range(2):
                    self.waves.add(boss.x, boss.y, 90 + i * 60, 0.5 + i * 0.2, boss.d.color, 4)
                self.particles.burst(boss.x, boss.y, 50, boss.d.color, (60, 280), kind="spark", size=(1, 3))
                self.items.spawn("big", boss.x, boss.y, 3, spread=1.2)
                self.items.spawn("point", boss.x, boss.y, 10, spread=1.4)
                self.items.spawn("spell", boss.x, boss.y, 1)
                self.add_score(300_000, boss.x, boss.y - 30, show=True, mult=False)
            self.boss = None
            return
        self.bullets.cancel_all(True)
        self.sfx("boss_die")
        self.app.post.glitch(18, 0.9)
        self.app.post.aberration(36, 4)
        self.flash.trigger((255, 255, 255), 230, 200)
        self.shake.add(12)
        for i in range(4):
            self.waves.add(boss.x, boss.y, 80 + i * 70, 0.5 + i * 0.25, boss.d.color, 5)
        self.particles.burst(boss.x, boss.y, 90, boss.d.color, (60, 360), kind="spark", size=(1, 4), life=(0.5, 1.4))
        self.particles.burst(boss.x, boss.y, 20, (255, 255, 255), (20, 120), kind="glow", size=(5, 10), life=(0.5, 1.2))
        self.items.spawn("big", boss.x, boss.y, 6, spread=1.4)
        self.items.spawn("point", boss.x, boss.y, 20, spread=1.6)
        self.items.spawn("heart", boss.x, boss.y, 1)
        self.add_score(1_000_000 * (1 + self.bosses_beaten * 0.25), boss.x, boss.y - 30, show=True, mult=False)
        self.bosses_beaten += 1
        self.boss_explosion = [boss.x, boss.y, 0, boss.d.color]
        self.boss = None

    # ==================================================================
    # Update
    # ==================================================================
    def handle_event(self, e):
        if e.type == pygame.WINDOWFOCUSLOST and self.state == "play" and not self.app.headless:
            self.pause()
        elif e.type == pygame.KEYDOWN and self.debug:
            if e.key == pygame.K_F4 and self.boss is None:
                self._debug_skip()
            elif e.key == pygame.K_F5:
                self.god = not self.god

    def pause(self):
        from .scenes.pause import PauseScene

        self.app.push(PauseScene(self.app, self))

    def update(self, dt):
        inp = self.app.input
        if self.pending_stage is not None:
            i = self.pending_stage
            self.pending_stage = None
            self.app.fade(lambda: self.start_stage(i))
            return
        if inp.was_pressed("pause") and self.state == "play":
            self.pause()
            return
        if inp.was_pressed("debug"):
            self.debug = not self.debug
        self.hud.update(dt)
        self._update_fx(dt)
        if self.picker is not None:
            self.picker.update(dt)
            if self.picker.done:
                self.picker = None
            return
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        if self.state == "dying":
            self.death_t += 1
            if self.death_t % 2 == 0:
                self._step_world(dt, inp)
            if self.death_t > 150:
                self.state = "over"
                self.finish(cleared=False)
            return
        if self.state != "play":
            return
        self.frame += 1
        if self.dialogue is not None:
            self.dialogue.update(inp, dt)
            if self.dialogue.done:
                self.dialogue = None
            # During dialogue the player can move but not act.
            for a in ("dash", "parry", "spell", "confirm"):
                inp.pressed.discard(a)
        if self.god:
            self.player.iframes = max(self.player.iframes, 2)
        self.player.update(inp, dt)
        self._step_world(dt, inp)
        self._collide()

    def _step_world(self, dt, inp):
        ts_player = self.timestop > 0 and self.timestop_owner == "player"
        if self.timestop > 0:
            self.timestop -= 1
            if self.timestop == 0:
                self.timestop_owner = None
                self.sfx("tick")
        if self.invert_t > 0:
            self.invert_t -= 1
        if not ts_player:
            self.tasks.update()
            for e in self.enemies:
                if e.alive:
                    e.update(dt)
            if any(not e.alive for e in self.enemies):
                self.enemies = [e for e in self.enemies if e.alive]
            if self.boss is not None:
                self.boss.update(dt)
        p = self.player
        slow = self.slow * (0.8 if (p.focus_slow and p.focus) else 1.0)
        self.bullets.update(dt, timestop=self.timestop > 0, slow=slow, wrap=self.wrap)
        self.player_spells = [s for s in self.player_spells if s.update()]
        self.items.update(dt)
        if self.incident is not None:
            if not self.incident_active:
                self.incident_delay -= 1
                if self.incident_delay <= 0:
                    self.incident_active = True
                    self.incident.start()
            elif not ts_player and not self.incident.update():
                self.end_incident()
        if self.chain_timer > 0:
            self.chain_timer -= 1
            if self.chain_timer == 0:
                self.chain = 0
        for tg in self.telegraphs:
            tg[4] -= 1
        self.telegraphs = [tg for tg in self.telegraphs if tg[4] > 0]
        if self.freeze_tint > 0:
            self.freeze_tint -= 1
        target_dark = 1.0 if (self.boss is not None and self.boss.state in ("card", "declare")) else 0.0
        self.spell_dark += (target_dark - self.spell_dark) * 0.04

    def _update_fx(self, dt):
        self.particles.update(dt)
        self.texts.update(dt)
        self.waves.update(dt)
        self.shake.update(dt)
        self.flash.update(dt)
        for o in self.overlays:
            o.update(dt)
        self.overlays = [o for o in self.overlays if not o.done]
        for c in self.cutins:
            c.update(dt)
        self.cutins = [c for c in self.cutins if not c.done]
        for pf in self.photo_flashes:
            pf[1] -= 1
        self.photo_flashes = [pf for pf in self.photo_flashes if pf[1] > 0]
        if self.hint_t > 0:
            self.hint_t -= dt
        if self.boss_explosion:
            self.boss_explosion[2] += dt
            if self.boss_explosion[2] > 1.6:
                self.boss_explosion = None

    def _collide(self):
        p = self.player
        if not p.alive or p.hit_pending > 0:
            return
        hit, grazed = self.bullets.collide_player(p)
        for b in grazed:
            self.on_graze(b)
        if hit is not None:
            if hit.data == "sakuya":
                hit.dead = True
                p.asleep = False
                p.idle = 0
                self.texts.add("OW! I'm awake! I'm awake!", p.x, p.y - 26, (255, 200, 120), 12, 1.4)
                self.shake.add(4)
                self.sfx("boing")
            else:
                p.hit(hit)
        for e in self.all_enemies():
            if not e.alive or not e.contact:
                continue
            if e.is_boss and (e.state in ("enter", "dead") or e.invisible):
                continue
            reach = e.r * 0.8 + p.hit_r + (10 if p.dashing() else 0)
            if (e.x - p.x) ** 2 + (e.y - p.y) ** 2 < reach * reach:
                if p.dashing():
                    if e.dash_hit_id != p.dash_id and e.hittable:
                        e.dash_hit_id = p.dash_id
                        self.dash_strike(e)
                elif p.parry_t > 0 and e.dash_hit_id != -p.dash_id - 1000:
                    e.dash_hit_id = -p.dash_id - 1000
                    self.parry_body(e)
                elif p.vulnerable():
                    p.hit(e)
                    break
        self.bullets.collide_enemies(self.all_enemies(), self.on_friendly_hit)

    def _debug_skip(self):
        # Jump straight to this stage's boss (debug only).
        st = self.stage
        from . import bossdefs

        bdef = bossdefs.ALL.get(st.boss_id)
        if bdef is not None and self.mode != "practice":
            self.tasks.clear()
            for e in self.enemies:
                e.remove()
            self.enemies = []
            self.tasks.spawn(stages.boss_only(self, bdef))

    # ==================================================================
    # Draw
    # ==================================================================
    def shake_offset(self):
        return self.shake.offset()

    def draw(self, surf):
        add = self.add
        add.fill((0, 0, 0))
        t = self.frame / 60.0
        self.bg.draw(surf, t)
        self._draw_ambience(surf, add, t)
        for tg in self.telegraphs:
            self._draw_telegraph(add, tg)
        self.items.draw(surf, add)
        for e in self.enemies:
            if e.alive:
                e.draw(surf, add)
        if self.boss is not None:
            self.boss.draw(surf, add)
        if self.incident is not None and self.incident_active:
            self.incident.draw(surf, add)
        self.player.draw(surf, add)
        for s in self.player_spells:
            s.draw(surf, add)
        self.bullets.draw(surf, self.visible)
        self.bullets.draw_lasers(add)
        self.particles.draw(surf, add)
        self.waves.draw(add)
        if self.boss_explosion:
            x, y, bt, col = self.boss_explosion
            r = 20 + bt * 260
            gfx.blit_glow(add, x, y, int(40 + bt * 60), scale_color(col, max(0, 1 - bt / 1.6)), 1.0)
            gfx.ring(add, x, y, r, (255, 255, 255), 3, max(0, 1 - bt / 1.6))
        surf.blit(add, (0, 0), special_flags=pygame.BLEND_ADD)
        self.player.draw_hitbox(surf, add)
        for rect, life in self.photo_flashes:
            fl = pygame.Surface(rect.size)
            fl.fill((255, 255, 255))
            fl.set_alpha(int(255 * life / 12))
            surf.blit(fl, rect)
        if self.timestop > 0:
            gray = pygame.transform.grayscale(surf)
            if self.invert_t > 0:
                gray = pygame.transform.invert(gray)
            tint = pygame.Surface((W, H))
            tint.fill((170, 160, 210))
            gray.blit(tint, (0, 0), special_flags=pygame.BLEND_MULT)
            surf.blit(gray, (0, 0))
            self.player.draw(surf, add)
            self.player.draw_hitbox(surf, add)
        if self.freeze_tint > 0:
            tint = pygame.Surface((W, H))
            k = min(1.0, self.freeze_tint / 30)
            tint.fill((int(20 * k), int(50 * k), int(70 * k)))
            surf.blit(tint, (0, 0), special_flags=pygame.BLEND_ADD)
        if self.incident is not None and self.incident_active:
            self.incident.overlay(surf)
        if self.want_photo:
            self.photo = surf.copy()
            self.want_photo = False
        self.texts.draw(surf)
        for c in self.cutins:
            c.draw(surf)
        self.hud.draw(surf)
        if self.dialogue is not None:
            self.dialogue.draw(surf)
        for o in self.overlays:
            if self.dialogue is not None and isinstance(o, MusicToast):
                continue
            o.draw(surf)
        if self.hint and self.hint_t > 0:
            elapsed = self.hint_total - self.hint_t
            a = clamp(min(self.hint_t / 0.5, elapsed / 0.3), 0.0, 1.0)
            r = assets.text(self.hint, 12, TEXT)
            box = pygame.Rect(0, 0, r.get_width() + 16, 18)
            box.midbottom = (W // 2, H - 8)
            panel = pygame.Surface(box.size, pygame.SRCALPHA)
            panel.fill((10, 6, 20, int(200 * a)))
            surf.blit(panel, box)
            pygame.draw.rect(surf, scale_color(GOLD, a), box, 1)
            img = r.copy()
            img.set_alpha(int(255 * a))
            surf.blit(img, (box.x + 8, box.y + 2))
        if self.picker is not None:
            self.picker.draw(surf)
        if self.incident is not None and self.incident_active:
            out = self.incident.post(surf)
            if out is not surf:
                surf.blit(out, (0, 0))
        self.flash.draw(surf)
        if self.debug:
            self._draw_debug(surf)

    def _draw_ambience(self, surf, add, t):
        if self.spell_dark > 0.02 and self.spell_bg is not None:
            self.spell_bg.draw(surf, t, min(1.0, self.spell_dark * 1.15))
        k = self.save.settings.get("bg_brightness", 0.8)
        if k < 0.99:
            self.dimmer.set_alpha(int(255 * (1 - k)))
            surf.blit(self.dimmer, (0, 0))
        if self.darkness:
            dark = pygame.Surface((W, H), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 190))
            for x, y, r in ((self.player.x, self.player.y, 80), ((self.boss.x, self.boss.y, 60) if self.boss else (0, 0, 0))):
                if r <= 0:
                    continue
                for k in range(8, 0, -1):
                    pygame.draw.circle(dark, (0, 0, 0, int(190 * (k / 8) ** 1.5)), (int(x), int(y)), int(r * k / 8))
            surf.blit(dark, (0, 0))
        if self.red_mist:
            mist = pygame.Surface((W, H))
            pulse = 0.5 + 0.5 * math.sin(t * 1.3)
            mist.fill((int(30 + 20 * pulse), 0, 6))
            surf.blit(mist, (0, 0), special_flags=pygame.BLEND_ADD)
            surf.blit(gfx.vignette((W, H), 200), (0, 0))

    def _draw_telegraph(self, add, tg):
        kind, x, y, p, life, maxlife, col = tg
        k = life / maxlife
        flick = 0.45 + 0.55 * (1 if (life // 3) % 2 else 0.4)
        if kind == "line":
            ex, ey = x + math.cos(p) * 800, y + math.sin(p) * 800
            pygame.draw.line(add, scale_color(col, flick * (0.4 + 0.6 * (1 - k))), (x, y), (ex, ey), 1 if k > 0.4 else 3)
        else:
            r = p * (1.4 - 0.4 * k)
            gfx.ring(add, x, y, r, col, 2, flick)
            gfx.ring(add, x, y, p * (1 - k), col, 1, flick)

    def _draw_debug(self, surf):
        lines = [
            f"FPS {self.app.clock.get_fps():.0f}  bullets {len(self.bullets.items)}+{len(self.bullets.friendly)}",
            f"enemies {len(self.enemies)}  particles {len(self.particles.items)}  items {len(self.items.items)}",
            f"F4: skip to boss   F5: god mode [{'ON' if self.god else 'off'}]",
        ]
        for i, l in enumerate(lines):
            assets.blit_text(surf, l, (6, H - 50 + i * 14), 12, (180, 255, 180))
