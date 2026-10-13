"""Stage scripts (waves -> incident -> boss) and the endless-mode director."""

import math
import random

from . import bossdefs
from .config import FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, H, RAINBOW, W
from .enemies import (border_run, bounce, chase, edge_point, fairy, far_side, kedama, leave, move_to, shoot_aimed,
                      shoot_ring, shoot_spiral)
from .util import TAU, angle_to, clamp


def seq(*gens):
    for g in gens:
        yield from g


# ======================================================================
# Wave templates
# ======================================================================


def _inward(side, x, y, depth):
    if side == "top":
        return x, y + depth
    if side == "bottom":
        return x, y - depth
    if side == "left":
        return x + depth, y
    return x - depth, y


def w_line(g, kind="sunny", n=5, side=None, hp=3, shots=2, spread_n=1, speed=110, bullet="orb", gap=10, depth=70):
    """A line of fairies enters, fires aimed shots, then leaves."""
    side = side or far_side(g)
    for i in range(n):
        x, y = edge_point(side, (i + 0.5) / n)
        e = fairy(g, x, y, kind, hp)
        tx, ty = _inward(side, x, y, depth + random.uniform(-12, 12))
        e.tasks.spawn(seq(move_to(e, tx, ty, 50),
                          shoot_aimed(e, g, n=spread_n, times=shots, interval=34, speed=speed, kind=bullet),
                          leave(e, 90)))
        yield gap


def w_stream(g, kind="luna", n=8, side=None, hp=2, speed=110, gap=14, shot_speed=120, bullet="orb"):
    """Fairies zip straight across the arena, firing one aimed shot."""
    side = side or random.choice(("left", "right", "top", "bottom"))
    lane = random.uniform(0.2, 0.8)
    for i in range(n):
        x, y = edge_point(side, clamp(lane + random.uniform(-0.08, 0.08), 0.05, 0.95))
        e = fairy(g, x, y, kind, hp, points=600, drops=(("point", 1),))
        vx, vy = {"top": (0, speed), "bottom": (0, -speed), "left": (speed, 0), "right": (-speed, 0)}[side]
        e.vx, e.vy = vx, vy
        e.tasks.spawn(shoot_aimed(e, g, delay=random.randint(40, 90), speed=shot_speed, kind=bullet))
        yield gap


def w_chasers(g, n=3, color="pink", speed=50, hp=2, gap=20, duration=8.0):
    """Kedama that slowly home in on you (the original game's chaser)."""
    side = far_side(g)
    for i in range(n):
        x, y = edge_point(side, random.uniform(0.15, 0.85))
        e = kedama(g, x, y, color, hp=hp)
        e.tasks.spawn(seq(chase(e, g, speed * (1 + 0.1 * g.diff), duration=int(duration * 60)), leave(e, 80)))
        yield gap


def w_bouncers(g, n=3, color="cyan", speed=85, hp=3, ring_n=8, gap=24, duration=9.0):
    """Kedama bouncing off the walls, popping rings (the original 'Enemy2')."""
    side = far_side(g)
    for i in range(n):
        x, y = edge_point(side, random.uniform(0.2, 0.8))
        e = kedama(g, x, y, color, hp=hp, r=8)
        a = angle_to(x, y, W / 2, H / 2) + random.uniform(-0.6, 0.6)
        e.tasks.spawn(seq(bounce(e, speed, int(duration * 60), a), leave(e, 120)))
        e.tasks.spawn(shoot_ring(e, g, n=g.d(ring_n - 2, ring_n, ring_n + 2, ring_n + 4), speed=80, kind="pellet",
                                 times=99, interval=g.d(110, 90, 75, 60), delay=60))
        yield gap


def w_border(g, n=2, kind="star", hp=4, speed=130, gap=40):
    """Fairies running along the walls, firing inward (the original 'BorderEnemy')."""
    for i in range(n):
        side = random.choice(("top", "bottom", "left", "right"))
        x, y = edge_point(side, random.choice((0.02, 0.98)))
        e = fairy(g, x, y, kind, hp)
        e.tasks.spawn(border_run(e, speed, clockwise=random.random() < 0.5, laps=0.75))
        e.tasks.spawn(shoot_aimed(e, g, n=g.d(1, 2, 3, 3), spread=0.3, times=99, interval=g.d(60, 48, 40, 32), delay=40, kind="rice"))
        yield gap


def w_big(g, kind="clown", hp=24, pattern="spiral", x=None, y=None, stay=6.0, color=None):
    """A sturdy fairy that parks somewhere and fires a pattern."""
    side = far_side(g)
    sx, sy = edge_point(side, random.uniform(0.3, 0.7))
    if x is None:
        tx, ty = _inward(side, sx, sy, random.uniform(90, 130))
    else:
        tx, ty = x, y
    e = fairy(g, sx, sy, kind, hp, points=3000, drops=(("point", 5), ("spell", 1)), color=color)
    if pattern == "spiral":
        attack = shoot_spiral(e, g, arms=g.d(2, 3, 4, 5), speed=85, step=0.21, kind="rice", duration=int(stay * 60), interval=6)
    elif pattern == "rings":
        attack = shoot_ring(e, g, n=g.d(12, 16, 20, 24), speed=85, times=int(stay * 60 / 40), interval=40, rotate=0.13, kind="orb")
    else:
        attack = shoot_aimed(e, g, n=g.d(3, 5, 5, 7), spread=0.8, times=int(stay * 60 / 30), interval=30, speed=130, kind="rice")
    e.tasks.spawn(seq(move_to(e, tx, ty, 60), attack, leave(e, 70)))
    yield 30


def w_circle(g, n=8, kind="dai", hp=2, radius=None):
    """Fairies appear all around you, each firing one shot, then vanish."""
    p = g.player
    r = radius or 150
    base = random.uniform(0, TAU)
    for i in range(n):
        a = base + TAU * i / n
        x = clamp(p.x + math.cos(a) * r, FIELD_LEFT + 10, FIELD_RIGHT - 10)
        y = clamp(p.y + math.sin(a) * r, FIELD_TOP + 10, FIELD_BOTTOM - 10)
        ox, oy = edge_point(random.choice(("top", "bottom", "left", "right")), random.random())
        e = fairy(g, ox, oy, kind, hp, points=800, drops=(("point", 1),))
        e.tasks.spawn(seq(move_to(e, x, y, 60), shoot_aimed(e, g, delay=20 + i * 4, speed=100, kind="orb"), leave(e, 100)))
    yield 30


def w_dive(g, n=6, kind="lily", hp=2, gap=16):
    """Fairies dive at where you are, scattering a few bullets on the way."""
    for i in range(n):
        side = random.choice(("top", "left", "right"))
        x, y = edge_point(side, random.random())
        e = fairy(g, x, y, kind, hp, points=700, drops=(("point", 1),))
        p = g.player
        a = angle_to(x, y, p.x, p.y)
        sp = 150 + 15 * g.diff
        e.vx, e.vy = math.cos(a) * sp, math.sin(a) * sp
        e.tasks.spawn(shoot_ring(e, g, n=g.d(4, 6, 8, 10), speed=70, kind="pellet", times=1, delay=50))
        yield gap


def heart_drop(g):
    p = g.player
    if p.hearts < p.max_hearts:
        g.items.spawn("heart", random.uniform(100, W - 100), random.uniform(90, H - 70), spread=0.2)


def with_hints(g):
    seen = g.save.stats.get("tutorial_seen", 0)
    if seen >= 2 and g.diff > 0:
        return
    g.save.stats["tutorial_seen"] = seen + 1
    hints = [
        (60, "Move: Arrows / WASD / ZQSD  ·  Hold SHIFT to focus (slow + see your hitbox)"),
        (420, "SPACE or K: DASH! You're invincible mid-dash and it smashes fairies."),
        (780, "F or J right as bullets reach you: PARRY sends them back at enemies!"),
        (1140, "Brush past bullets to GRAZE: points + spell power. X or L: cast your SPELL!"),
    ]
    t = 0
    for at, text in hints:
        yield at - t
        t = at
        g.show_hint(text, 5.5)


# ======================================================================
# Story stages
# ======================================================================


def stage1(g):
    g.tasks.spawn(with_hints(g))
    yield 120
    yield from w_line(g, "sunny", 5, "top", shots=1)
    yield 140
    yield from w_chasers(g, 3, "pink", speed=45)
    yield 150
    yield from w_line(g, "luna", 5, "left", shots=1)
    yield 100
    yield from w_stream(g, "star", 7, "top", speed=100, gap=18)
    yield 160
    yield from w_bouncers(g, 2, "cyan", speed=70)
    yield 200
    g.tasks.spawn(w_line(g, "sunny", 4, "bottom", shots=2))
    yield from w_line(g, "luna", 4, "right", shots=2)
    yield 180
    heart_drop(g)
    yield from w_big(g, "dai", 18, "rings", stay=5)
    yield 300
    yield from w_dive(g, 5, "lily")
    yield 200
    yield from g.boss_sequence(bossdefs.RUMIA)
    yield from g.stage_clear()


def stage2(g):
    yield 120
    yield from w_stream(g, "dai", 8, "left", speed=120)
    yield 60
    yield from w_stream(g, "dai", 8, "right", speed=120)
    yield 120
    yield from w_bouncers(g, 3, "cyan", speed=85, ring_n=8)
    yield 120
    yield from w_line(g, "star", 6, "top", shots=2, spread_n=3, bullet="ice")
    yield 160
    g.start_incident()
    yield 120
    yield from w_chasers(g, 4, "blue", speed=50)
    yield 200
    yield from g.boss_sequence(bossdefs.DAIYOUSEI, y=110)
    yield 90
    yield from w_dive(g, 6, "luna")
    yield 200
    yield from w_big(g, "clown", 22, "spiral", stay=5.5, color="cyan")
    yield 260
    heart_drop(g)
    yield from w_circle(g, 8, "dai")
    yield 240
    yield from g.boss_sequence(bossdefs.CIRNO)
    yield from g.stage_clear()


def stage3(g):
    yield 120
    yield from w_line(g, "sunny", 6, "top", shots=2, spread_n=3)
    yield 80
    yield from w_border(g, 2, "star")
    yield 160
    yield from w_stream(g, "lily", 8, None, speed=130)
    yield 140
    g.start_incident()
    yield 100
    yield from w_bouncers(g, 3, "yellow", speed=95)
    yield 160
    yield from w_big(g, "clown", 26, "rings", stay=6, color="green")
    yield 200
    heart_drop(g)
    g.tasks.spawn(w_chasers(g, 3, "orange", speed=55))
    yield from w_line(g, "luna", 6, "bottom", shots=2, spread_n=3)
    yield 200
    yield from w_dive(g, 7, "sunny")
    yield 220
    yield from g.boss_sequence(bossdefs.MEILING)
    yield from g.stage_clear()


def stage4(g):
    yield 120
    yield from w_big(g, "star", 20, "spiral", stay=5)
    yield 60
    yield from w_line(g, "dai", 6, "left", shots=2, spread_n=3, bullet="rice")
    yield 160
    yield from w_border(g, 3, "luna", speed=150)
    yield 140
    g.start_incident()
    yield 120
    yield from w_stream(g, "star", 9, None, speed=130)
    yield 120
    yield from g.boss_sequence(bossdefs.KOAKUMA, y=110)
    yield 90
    yield from w_bouncers(g, 4, "purple", speed=95)
    yield 200
    heart_drop(g)
    yield from w_circle(g, 10, "lily")
    yield 160
    yield from w_big(g, "clown", 30, "aimed", stay=6, color="purple")
    yield 280
    yield from g.boss_sequence(bossdefs.PATCHOULI)
    yield from g.stage_clear()


def stage5(g):
    yield 120
    yield from w_stream(g, "luna", 10, "top", speed=140, gap=10, bullet="knife")
    yield 80
    yield from w_line(g, "star", 7, "right", shots=3, spread_n=3, bullet="knife")
    yield 160
    yield from w_chasers(g, 5, "blue", speed=60)
    yield 120
    g.start_incident()
    yield 120
    yield from w_border(g, 3, "sunny", speed=160)
    yield 160
    yield from w_big(g, "clown", 32, "spiral", stay=6, color="blue")
    yield 200
    heart_drop(g)
    yield from w_dive(g, 8, "lily")
    yield 120
    yield from w_circle(g, 10, "dai")
    yield 240
    yield from g.boss_sequence(bossdefs.SAKUYA)
    yield from g.stage_clear()


def stage6(g):
    yield 120
    g.tasks.spawn(w_line(g, "sunny", 6, "top", shots=3, spread_n=3))
    yield from w_line(g, "luna", 6, "bottom", shots=3, spread_n=3)
    yield 120
    yield from w_bouncers(g, 4, "red", speed=100)
    yield 140
    g.start_incident()
    yield 120
    yield from w_big(g, "clown", 34, "rings", stay=6, color="red")
    yield 140
    yield from w_stream(g, "star", 10, None, speed=150, gap=9)
    yield 120
    yield from g.boss_sequence(bossdefs.SAKUYA_MID, y=110)
    yield 90
    heart_drop(g)
    yield from w_chasers(g, 5, "red", speed=62)
    yield 200
    yield from w_circle(g, 12, "lily")
    yield 260
    yield from g.boss_sequence(bossdefs.REMILIA)
    yield from g.stage_clear()


def stage_extra(g):
    yield 60
    if g.mode == "extra" and not g.player.charms:
        yield from g.charm_pick()
    yield 60
    yield from w_big(g, "clown", 30, "spiral", stay=5, color="red")
    yield 40
    yield from w_stream(g, "sunny", 10, None, speed=150, gap=8)
    yield 100
    g.start_incident()
    yield 100
    yield from w_bouncers(g, 5, "yellow", speed=110)
    yield 160
    yield from g.boss_sequence(bossdefs.PATCHOULI_MID, y=110)
    yield 90
    heart_drop(g)
    yield from w_circle(g, 12, "dai")
    yield 200
    yield from w_big(g, "clown", 34, "rings", stay=6, color="purple")
    yield 280
    yield from g.boss_sequence(bossdefs.FLANDRE)
    yield from g.stage_clear()


def boss_only(g, bdef):
    yield 30
    yield from g.boss_sequence(bdef)
    yield from g.stage_clear()


# ======================================================================
# Endless mode
# ======================================================================

ENDLESS_WAVES = [
    (lambda g: w_line(g, random.choice(("sunny", "luna", "star")), 6, None, shots=2, spread_n=random.choice((1, 3)))),
    (lambda g: w_stream(g, random.choice(("dai", "lily", "luna")), 9, None, speed=130)),
    (lambda g: w_chasers(g, 4, random.choice(("pink", "blue", "orange")), speed=55)),
    (lambda g: w_bouncers(g, 3, random.choice(("cyan", "yellow", "purple")), speed=95)),
    (lambda g: w_border(g, 2, random.choice(("star", "sunny")))),
    (lambda g: w_big(g, "clown", 26, random.choice(("spiral", "rings", "aimed")), stay=5, color=random.choice(RAINBOW))),
    (lambda g: w_circle(g, 9, random.choice(("dai", "lily")))),
    (lambda g: w_dive(g, 7, random.choice(("lily", "sunny")))),
]


def endless(g):
    g.show_hint("ENDLESS: survive as long as you can. It only gets worse~", 4.5)
    yield 120
    level = 0
    t0 = g.frame
    next_incident = g.frame + 60 * 35
    next_boss = g.frame + 60 * 70
    base_speed = g.speed_mult
    while True:
        level = (g.frame - t0) // (60 * 30)
        g.speed_mult = base_speed * (1 + min(0.5, level * 0.05))
        g.stage_label = f"Endless - Wave {level + 1}"
        for _ in range(1 + min(2, level // 3)):
            g.tasks.spawn(random.choice(ENDLESS_WAVES)(g))
            yield 50
        yield max(110, 260 - level * 15)
        if g.frame >= next_incident and g.incident is None:
            g.start_incident()
            next_incident = g.frame + 60 * random.randint(32, 45)
        if random.random() < 0.15:
            heart_drop(g)
        if g.frame >= next_boss:
            yield from g.wait_clear(240)
            src = random.choice(list(bossdefs.ALL.values()))
            card = random.choice(src.cards)
            bd = src.with_cards([card], midboss=False)
            yield from g.boss_sequence(bd, dialogue=False, hp_mult=0.8 + level * 0.05)
            g.app.audio.play_music(["endless"])
            heart_drop(g)
            yield 60
            yield from g.charm_pick()
            next_boss = g.frame + 60 * random.randint(55, 75)
            yield 120


# ======================================================================
# Spell practice
# ======================================================================

BOSS_BG = {"rumia": "twilight", "daiyousei": "lake", "cirno": "lake", "meiling": "gate", "koakuma": "library",
           "patchouli": "library", "sakuya": "clock", "sakuya_mid": "moon", "remilia": "moon",
           "patchouli_mid": "basement", "flandre": "basement"}


def practice_stage(key, card_index):
    src = bossdefs.PRACTICE_BY_KEY[key]
    boss_id = key
    card = src.cards[card_index]
    bd = src.with_cards([card])

    def script(g):
        yield 40
        yield from g.boss_sequence(bd, dialogue=False)
        yield 150
        g.finish(cleared=True)

    return StageDef("SP", "Spell Practice", card.name, "スペルプラクティス", BOSS_BG[boss_id], script, boss_id, src.name)


# ======================================================================
# Stage table
# ======================================================================


class StageDef:
    def __init__(self, num, label, name, jp, bg, script, boss_id, sub="", music=None, glyph=""):
        self.num = num
        self.label = label
        self.name = name
        self.jp = jp
        self.bg = bg
        self.script = script
        self.boss_id = boss_id
        self.sub = sub
        self.music = music
        self.glyph = glyph


STORY = [
    StageDef(1, "Stage 1", "Twilight Path", "宵闇の小道", "twilight", stage1, "rumia", "Bring a lantern. Or don't.", glyph="宵"),
    StageDef(2, "Stage 2", "The Misty Lake", "霧の湖", "lake", stage2, "cirno", "Beware of strong fairies (self-proclaimed).", glyph="霧"),
    StageDef(3, "Stage 3", "The Scarlet Gate", "紅魔館の門", "gate", stage3, "meiling", "The gatekeeper is (probably) awake.", glyph="門"),
    StageDef(4, "Stage 4", "Voile, the Magic Library", "ヴワル魔法図書館", "library", stage4, "patchouli", "Please dash quietly.", glyph="書"),
    StageDef(5, "Stage 5", "The Clock Tower", "時計塔", "clock", stage5, "sakuya", "It's always tea time somewhere.", glyph="時"),
    StageDef(6, "Final Stage", "Under the Scarlet Moon", "紅い月の下で", "moon", stage6, "remilia", "The source of the mist awaits.", glyph="月"),
]
EXTRA = StageDef("EX", "Extra Stage", "The Forbidden Basement", "禁忌の地下室", "basement", stage_extra, "flandre", "Do not open. Seriously.", glyph="禁")
ENDLESS = StageDef("∞", "Endless", "Gensokyo After Dark", "幻想郷の夜", "night", endless, None, "How long can you dodge?", glyph="夜")
