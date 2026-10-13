"""The seven bosses of the Scarlet Mist incident and their spell cards.

Every pattern is a generator: `yield n` waits n frames. `g` is the game scene
and `b` the boss. Difficulty-dependent values use g.d(easy, normal, hard, lunatic)."""

import math
import random

from .boss import BossDef, SpellCard
from .config import FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, FIELD_TOP, H, RAINBOW, W
from .enemies import Enemy, move_to
from .util import TAU, angle_to, clamp


def cough(b, g, chance=0.15):
    """Patchouli's asthma. Gives the player a breather."""
    if random.random() < chance:
        g.texts.add("*cough* *cough*", b.x, b.y - 30, (210, 180, 255), 12, 1.2)
        g.sfx("cough")
        yield 55


# ======================================================================
# Stage 1 - Rumia
# ======================================================================


def night_bird(b, g):
    side = 1
    while True:
        base = g.aim(b.x, b.y)
        n = g.d(9, 13, 17, 21)
        for i in range(n):
            a = base - side * 1.2 + side * 2.4 * i / (n - 1)
            for k in range(g.d(1, 2, 2, 3)):
                g.bullets.shoot(b.x, b.y, (95 + k * 22 + i * 3) * g.speed_mult, a, "orb", "blue")
            g.sfx("shot")
            yield 2
        side = -side
        yield g.d(42, 32, 26, 20)
        if random.random() < 0.6:
            b.wander(45)


def demarcation(b, g):
    g.darkness = 1
    turns = (("blue", 1.2), ("purple", -1.2), ("red", 0.0))
    while True:
        for color, turn in turns:
            n = g.d(16, 22, 28, 34)
            off = random.uniform(0, TAU)

            def fn(bl, g, turn=turn):
                if bl.age == 50:
                    bl.set_angle(bl.angle + turn)
                    bl.accel = 80
                    bl.max_speed = 120 * g.speed_mult
                    bl.min_speed = 0

            for i in range(n):
                g.bullets.shoot(b.x, b.y, 170, off + TAU * i / n, "rice", color, accel=-190, min_speed=24, fn=fn)
            g.sfx("shot2")
            yield g.d(34, 28, 24, 20)
        b.wander(50)
        yield 30


RUMIA = BossDef(
    "rumia", "Rumia", "Youkai of the Dusk", "Rumia", (130, 110, 255), jp="宵闇の妖怪", cards=[
        SpellCard('Night Sign "Night Bird"', night_bird, hp=34, time=26, bonus=300_000),
        SpellCard('Darkness Sign "Demarcation"', demarcation, hp=42, time=30, bonus=400_000),
    ],
)


# ======================================================================
# Stage 2 - Cirno
# ======================================================================


def icicle_fall(b, g):
    b.go(W / 2, 100, 40)
    wave = 0
    while True:
        for side in (-1, 1):
            n = g.d(5, 7, 9, 11)
            for i in range(n):
                base = 0.0 if side > 0 else math.pi
                a = base + side * (-0.9 + 1.8 * i / (n - 1))

                def fn(bl, g):
                    if bl.age == 34:
                        p = g.player
                        bl.aim(p.x + random.uniform(-50, 50), p.y + random.uniform(-50, 50))
                        bl.accel = 140
                        bl.max_speed = 150 * g.speed_mult
                        bl.min_speed = 0

                g.bullets.shoot(b.x + side * 8, b.y, 190, a, "ice", "cyan", accel=-260, min_speed=12, fn=fn)
            g.sfx("shot")
            yield 8
        wave += 1
        if wave % 3 == 0:
            g.bullets.fan(b.x, b.y, g.d(3, 5, 5, 7), 130 * g.speed_mult, g.aim(b.x, b.y), 0.5, "orb", "blue")
            g.sfx("shot2")
        yield g.d(26, 18, 14, 10)


def perfect_freeze(b, g):
    while True:
        group = []
        total = g.d(60, 90, 120, 150)
        for i in range(total):
            a = random.uniform(0, TAU)
            s = random.uniform(50, 180) * g.speed_mult
            group.append(g.bullets.shoot(b.x, b.y, s, a, "orb", random.choice(RAINBOW)))
            if i % 6 == 0:
                g.sfx("shot")
                yield 1
        yield 36
        g.sfx("freeze")
        g.flash.trigger((180, 230, 255), 90, 400)
        g.texts.add("FREEZE!", b.x, b.y - 32, (160, 230, 255), 12, 1.0)
        for bl in group:
            if not bl.dead:
                bl.frozen = True
                bl.color = "white"
                bl.spr_idx = -1
        for _ in range(g.d(2, 3, 4, 5)):
            g.bullets.fan(b.x, b.y, g.d(3, 5, 5, 7), 150 * g.speed_mult, g.aim(b.x, b.y), 0.6, "pellet", "blue")
            g.sfx("shot2")
            yield 18
        yield 24
        for bl in group:
            if not bl.dead:
                bl.frozen = False
                bl.set_angle(random.uniform(0, TAU))
                bl.set_speed(0)
                bl.accel = random.uniform(25, 55)
                bl.max_speed = 130 * g.speed_mult
        b.wander(60)
        yield 110


NINE = [
    ".###.",
    "#...#",
    "#...#",
    ".####",
    "....#",
    "#...#",
    ".###.",
]


def baka_baka(b, g):
    lines = ["I'm the strongest!", "Baka? YOU'RE the baka!", "⑨ ⑨ ⑨ !!", "Eat this, eat this!"]
    k = 0
    while True:
        if k % 2 == 0:
            g.texts.add(lines[(k // 2) % len(lines)], b.x, b.y - 34, (140, 230, 255), 12, 1.4)
        volley = g.d(1, 2, 2, 3)
        for v in range(volley):
            a = g.aim(b.x, b.y) + (v - (volley - 1) / 2) * 0.55
            for row, line in enumerate(NINE):
                for col, ch in enumerate(line):
                    if ch != "#":
                        continue
                    x = b.x + (col - 2) * 8
                    y = b.y + (row - 3) * 8
                    g.bullets.shoot(x, y, 105 * g.speed_mult, a, "orb", "cyan", grace=40)
        g.sfx("shot2")
        yield 36
        g.bullets.ring(b.x, b.y, g.d(10, 14, 18, 22), 80 * g.speed_mult, random.uniform(0, TAU), "ice", "blue")
        yield g.d(40, 32, 26, 22)
        b.wander(40)
        k += 1


CIRNO = BossDef(
    "cirno", "Cirno", "The Strongest Fairy (self-proclaimed)", "Cirno", (110, 220, 255),
    [
        SpellCard('Ice Sign "Icicle Fall"', icicle_fall, hp=40, time=28, bonus=400_000),
        SpellCard('Freeze Sign "Perfect Freeze"', perfect_freeze, hp=50, time=32, bonus=500_000),
        SpellCard('⑨ Sign "Baka Baka Barrage"', baka_baka, hp=46, time=30, bonus=499_999),
    ],
)


# ======================================================================
# Stage 3 - Hong Meiling
# ======================================================================


def colorful_rain(b, g):
    a = 0.0
    t = 0
    while True:
        arms = g.d(4, 5, 6, 7)
        for k in range(arms):
            c = RAINBOW[(k + t // 8) % 7]
            g.bullets.shoot(b.x, b.y, 80 * g.speed_mult, a + TAU * k / arms, "rice", c, accel=22, max_speed=150 * g.speed_mult)
        a += 0.17
        if t % 3 == 0:
            for _ in range(g.d(1, 1, 2, 2)):
                x = random.uniform(20, W - 20)
                g.bullets.shoot(x, -6, 50, math.pi / 2 + random.uniform(-0.25, 0.25), "pellet", random.choice(RAINBOW),
                                accel=50, max_speed=140 * g.speed_mult, grace=60)
        if t % 2 == 0:
            g.sfx("shot")
        t += 1
        if t % 70 == 0:
            b.wander(60)
        yield 6


def taichi_dash(b, g):
    while True:
        p = g.player
        a = angle_to(b.x, b.y, p.x, p.y)
        warn = g.d(46, 38, 30, 26)
        g.telegraph_line(b.x, b.y, a, warn, (120, 255, 160))
        g.sfx("warn")
        yield warn
        dist = math.hypot(p.x - b.x, p.y - b.y) + 90
        ex = clamp(b.x + math.cos(a) * dist, FIELD_LEFT + 30, FIELD_RIGHT - 30)
        ey = clamp(b.y + math.sin(a) * dist, FIELD_TOP + 20, FIELD_BOTTOM - 20)
        sx, sy = b.x, b.y
        frames = 20
        g.sfx("whoosh")
        for i in range(1, frames + 1):
            b.x = sx + (ex - sx) * i / frames
            b.y = sy + (ey - sy) * i / frames
            b.lean = 1 if ex > sx else -1
            if i % 2 == 0:
                for side in (-1, 1):

                    def fn(bl, g):
                        if bl.age == 28:
                            bl.accel = 120
                    g.bullets.shoot(b.x, b.y, 0, a + side * math.pi / 2, "orb", "green", max_speed=g.d(90, 110, 130, 150), fn=fn, grace=60)
            yield 1
        b.lean = 0
        g.shake.add(5)
        g.waves.add(b.x, b.y, 50, 0.4, (120, 255, 160), 3)
        g.bullets.ring(b.x, b.y, g.d(10, 14, 18, 22), 90 * g.speed_mult, random.uniform(0, TAU), "pellet", "yellow")
        g.sfx("shot2")
        yield g.d(40, 32, 26, 20)


def nap_on_duty(b, g):
    b.go(W / 2, 110, 40)
    g.texts.add("...zzz...", b.x, b.y - 30, (200, 220, 255), 12, 1.6)
    yield 40
    g.texts.add("Sakuya: ...Meiling.", W / 2, 70, (190, 200, 255), 12, 2.0)
    t = 0
    edges = ("top", "left", "right", "bottom")
    while True:
        if t % 50 == 0:
            g.texts.add("z", b.x + 10 + random.uniform(-3, 3), b.y - 20, (200, 220, 255), 12, 1.4, vy=-22)
            g.sfx("zzz")
        if t % g.d(26, 20, 15, 12) == 0:
            g.bullets.shoot(b.x, b.y, random.uniform(25, 45), random.uniform(0, TAU), "bubble",
                            random.choice(("cyan", "blue", "pink")), accel=10, max_speed=70 * g.speed_mult)
        if t % g.d(44, 34, 28, 22) == 0:
            side = random.choice(edges)
            n = g.d(3, 4, 5, 6)
            for i in range(n):
                k = (i + 0.5) / n
                if side == "top":
                    x, y = FIELD_LEFT + k * (FIELD_RIGHT - FIELD_LEFT), -12
                elif side == "bottom":
                    x, y = FIELD_LEFT + k * (FIELD_RIGHT - FIELD_LEFT), H + 12
                elif side == "left":
                    x, y = -12, FIELD_TOP + k * (FIELD_BOTTOM - FIELD_TOP)
                else:
                    x, y = W + 12, FIELD_TOP + k * (FIELD_BOTTOM - FIELD_TOP)
                a = angle_to(x, y, b.x, b.y) + random.uniform(-0.2, 0.2)
                g.bullets.shoot(x, y, 200 * g.speed_mult, a, "knife", "cyan", grace=120)
            g.sfx("whoosh")
        t += 2
        yield 2


MEILING = BossDef(
    "meiling", "Hong Meiling", "Chinese Girl (Gatekeeper)", "Hong Meiling", (90, 220, 140),
    [
        SpellCard('Rainbow Sign "Colorful Rain"', colorful_rain, hp=50, time=30, bonus=500_000),
        SpellCard('Fist Sign "Taichi Dash"', taichi_dash, hp=50, time=30, bonus=550_000),
        SpellCard('Sleep Sign "Nap on Duty"', nap_on_duty, time=20, bonus=600_000, survival=True),
    ],
)


# ======================================================================
# Stage 4 - Patchouli Knowledge
# ======================================================================


def agni_shine(b, g):
    a = 0.0
    while True:
        n = g.d(5, 7, 9, 11)
        for k in range(n):
            g.bullets.shoot(b.x, b.y, 30, a + TAU * k / n, "big", "orange", accel=70,
                            max_speed=g.d(100, 120, 140, 160) * g.speed_mult, turn=0.45)
            g.bullets.shoot(b.x, b.y, 30, -a + TAU * k / n + math.pi / n, "orb", "red", accel=80,
                            max_speed=g.d(110, 130, 150, 170) * g.speed_mult, turn=-0.45)
        g.sfx("shot2")
        a += 0.37
        yield g.d(30, 24, 19, 15)
        yield from cough(b, g, 0.08)
        if random.random() < 0.15:
            b.wander(50)


def princess_undine(b, g):
    while True:
        for _ in range(g.d(5, 7, 9, 11)):
            g.bullets.shoot(b.x, b.y, random.uniform(35, 65), random.uniform(0, TAU), "bubble", "blue",
                            accel=10, max_speed=85 * g.speed_mult)
        for _w in range(3):
            a = g.aim(b.x, b.y)
            for k in range(g.d(8, 12, 16, 20)):
                g.bullets.shoot(b.x, b.y, (80 + k * 6) * g.speed_mult, a + math.sin(k * 0.8) * 0.45, "rice", "cyan")
            g.sfx("shot")
            yield 14
        yield 46
        yield from cough(b, g, 0.2)
        b.wander(50)


def royal_flare(b, g):
    b.go(W / 2, H / 2 - 10, 60)
    yield 60
    while True:
        g.flash.trigger((255, 200, 120), 70, 300)
        for layer in range(g.d(2, 3, 3, 4)):
            n = g.d(14, 20, 24, 28)
            off = random.uniform(0, TAU)
            for k in range(n):
                g.bullets.shoot(b.x, b.y, 45 + layer * 22, off + TAU * k / n, "big", "orange" if layer % 2 else "yellow",
                                accel=14, max_speed=140 * g.speed_mult)
        g.sfx("explode")
        g.shake.add(4)
        for _ in range(4):
            g.bullets.fan(b.x, b.y, g.d(3, 3, 5, 5), 150 * g.speed_mult, g.aim(b.x, b.y), 0.35, "pellet", "red")
            g.sfx("shot")
            yield 15
        yield g.d(66, 52, 44, 38)
        yield from cough(b, g, 0.25)


PATCHOULI = BossDef(
    "patchouli", "Patchouli Knowledge", "The Unmoving Great Library", "Patchouli Knowledge", (200, 120, 255),
    [
        SpellCard('Fire Sign "Agni Shine"', agni_shine, hp=56, time=32, bonus=600_000),
        SpellCard('Water Sign "Princess Undine"', princess_undine, hp=58, time=32, bonus=650_000),
        SpellCard('Sun Sign "Royal Flare"', royal_flare, hp=66, time=36, bonus=700_000),
    ],
    circle_points=5,
)


# ======================================================================
# Stage 5 - Sakuya Izayoi
# ======================================================================


def killing_doll(b, g):
    while True:
        n = g.d(14, 20, 26, 30)
        off = random.uniform(0, TAU)
        group = [g.bullets.shoot(b.x, b.y, 230, off + TAU * k / n, "knife", "blue", accel=-320, min_speed=0) for k in range(n)]
        g.sfx("shot2")
        yield 38
        p = g.player
        for bl in group:
            if not bl.dead:
                bl.aim(p.x + random.uniform(-14, 14), p.y + random.uniform(-14, 14))
                bl.set_speed(10)
                bl.accel = 240
                bl.max_speed = g.d(160, 190, 220, 250) * g.speed_mult
                bl.color = "red"
                bl.spr_idx = -1
        g.sfx("whoosh")
        b.wander(30)
        yield g.d(44, 34, 28, 22)


def private_square(b, g):
    t = 0
    a = 0.0
    while True:
        if t % 140 == 0:
            g.slow = 1.0
            g.sfx("tick")
        elif t % 140 == 70:
            g.slow = 0.3
            g.sfx("timestop")
            g.flash.trigger((160, 140, 255), 60, 400)
        if t % 4 == 0:
            arms = g.d(2, 3, 3, 4)
            for k in range(arms):
                g.bullets.shoot(b.x, b.y, 120 * g.speed_mult, a + TAU * k / arms, "knife", "purple")
            a += 0.23
        if t % 34 == 0:
            g.bullets.fan(b.x, b.y, g.d(3, 5, 5, 7), 140 * g.speed_mult, g.aim(b.x, b.y), 0.5, "orb", "blue")
            g.sfx("shot2")
        if t % 8 == 0:
            g.sfx("shot")
        t += 1
        yield 1


def the_world(b, g):
    while True:
        g.start_timestop(110, "boss")
        g.texts.add("The World!", b.x, b.y - 34, (200, 210, 255), 12, 1.2)
        yield 16
        p = g.player
        for ring in range(g.d(1, 2, 2, 3)):
            cx, cy = p.x, p.y
            n = g.d(12, 16, 20, 24)
            R = 72 + ring * 28
            for k in range(n):
                a = TAU * k / n + ring * 0.25
                x, y = cx + math.cos(a) * R, cy + math.sin(a) * R
                bl = g.bullets.shoot(x, y, 0, a + math.pi, "knife", "cyan", grace=240)
                bl.age = 6  # skip the spawn flash: time is stopped, they must be visible
                bl.data = (150 + ring * 35) * g.speed_mult
            g.sfx("shot2")
            # Sakuya blinks somewhere else.
            g.particles.burst(b.x, b.y, 10, (180, 190, 255), (30, 90), kind="glow", size=(2, 4))
            b.x = random.uniform(160, W - 160)
            b.y = random.uniform(60, 150)
            yield 26
        while g.timestop > 0:
            yield 1
        for bl in g.bullets.items:
            if bl.data and bl.speed == 0:
                bl.set_speed(bl.data)
                bl.data = None
        g.sfx("whoosh")
        yield 50
        for _ in range(g.d(1, 2, 3, 3)):
            g.bullets.fan(b.x, b.y, g.d(5, 7, 9, 11), 170 * g.speed_mult, g.aim(b.x, b.y), 0.8, "knife", "blue")
            g.sfx("shot2")
            yield 16
        yield g.d(40, 30, 24, 20)


SAKUYA = BossDef(
    "sakuya", "Sakuya Izayoi", "Perfect and Elegant Maid", "Sakuya Izayoi", (170, 190, 255),
    [
        SpellCard('Illusion Sign "Killing Doll"', killing_doll, hp=64, time=32, bonus=700_000),
        SpellCard('Time Sign "Private Square"', private_square, hp=68, time=34, bonus=750_000),
        SpellCard('Illusion World "The World"', the_world, hp=72, time=38, bonus=800_000),
    ],
)


# ======================================================================
# Stage 6 - Remilia Scarlet
# ======================================================================


def gungnir(b, g):
    while True:
        a = g.aim(b.x, b.y)
        warn = g.d(36, 30, 26, 22)
        g.telegraph_line(b.x, b.y, a, warn, (255, 60, 80))
        g.sfx("warn")
        yield warn
        spear = g.bullets.shoot(b.x, b.y, 80, a, "spear", "red", accel=1000, max_speed=g.d(420, 480, 540, 600) * g.speed_mult, grace=120)
        g.sfx("whoosh")
        g.shake.add(4)
        for i in range(34):
            if spear.dead:
                break
            if i % 2 == 0:
                for side in (-1, 1):

                    def fn(bl, g):
                        if bl.age == 22:
                            bl.accel = 90
                    g.bullets.shoot(spear.x, spear.y, 0, spear.angle + side * (math.pi / 2 - 0.35), "rice", "red",
                                    max_speed=g.d(90, 110, 125, 140) * g.speed_mult, fn=fn, grace=60)
            yield 1
        yield g.d(30, 24, 18, 14)
        b.wander(36)


def scarlet_shoot(b, g):
    while True:
        a = g.aim(b.x, b.y)
        n = g.d(3, 5, 5, 7)
        spread = 1.1

        def fn(bl, g):
            if bl.age % 5 == 0 and bl.age < 100:
                g.bullets.shoot(bl.x, bl.y, 25, bl.angle + math.pi + random.uniform(-0.7, 0.7), "pellet", "red",
                                accel=45, max_speed=95 * g.speed_mult)

        for k in range(n):
            g.bullets.shoot(b.x, b.y, 150 * g.speed_mult, a - spread / 2 + spread * k / (n - 1), "big", "red", fn=fn)
        g.sfx("shot2")
        yield g.d(54, 44, 38, 32)
        if random.random() < 0.5:
            b.wander(40)


def scarlet_gensokyo(b, g):
    g.red_mist = 1
    b.go(W / 2, H / 2 - 20, 60)
    yield 60
    t = 0
    a = 0.0
    while True:
        if t % 7 == 0:
            for k in range(4):
                g.bullets.shoot(b.x, b.y, 95 * g.speed_mult, a + TAU * k / 4, "big", "red", accel=10, max_speed=140 * g.speed_mult)
            a += 0.23
            g.sfx("shot")
        if t % g.d(56, 46, 36, 30) == 0:
            g.bullets.ring(b.x, b.y, g.d(18, 24, 30, 36), 70 * g.speed_mult, random.uniform(0, TAU), "rice", "pink",
                           accel=30, max_speed=150 * g.speed_mult)
            g.sfx("shot2")
        if t % 150 == 75:

            def bat(bl, g):
                if 20 < bl.age < 100:
                    p = g.player
                    want = math.atan2(p.y - bl.y, p.x - bl.x)
                    diff = (want - bl.angle + math.pi) % TAU - math.pi
                    bl.set_angle(bl.angle + max(-0.025, min(0.025, diff)))

            for _ in range(g.d(4, 6, 8, 10)):
                g.bullets.shoot(b.x, b.y, 95 * g.speed_mult, random.uniform(0, TAU), "butterfly", "purple", fn=bat)
        if t % 330 == 200:
            base = random.uniform(0, TAU)
            for k in range(g.d(1, 2, 2, 3)):
                g.bullets.laser(b.x, b.y, base + k * TAU / g.d(1, 2, 2, 3), width=14, warn=60, active=150,
                                color="red", turn=0.45 * (1 if k % 2 else -1), owner=b)
        t += 1
        yield 1


REMILIA = BossDef(
    "remilia", "Remilia Scarlet", "The Eternally Young Scarlet Moon", "Remilia Scarlet", (235, 50, 80),
    [
        SpellCard('Divine Spear "Spear the Gungnir"', gungnir, hp=74, time=34, bonus=800_000),
        SpellCard('Scarlet Sign "Scarlet Shoot"', scarlet_shoot, hp=78, time=34, bonus=850_000),
        SpellCard('"Scarlet Gensokyo"', scarlet_gensokyo, hp=100, time=44, bonus=1_200_000),
    ],
)


# ======================================================================
# Extra - Flandre Scarlet
# ======================================================================


def _clone_fire(e, g, k):
    a = random.uniform(0, TAU)
    while e.alive:
        if k % 2 == 0:
            for j in range(3):
                g.bullets.shoot(e.x, e.y, 85 * g.speed_mult, a + TAU * j / 3, "orb", ("red", "blue", "green", "yellow")[k])
            a += 0.2 if k == 0 else -0.2
            yield 5
        else:
            g.bullets.fan(e.x, e.y, g.d(3, 4, 5, 6), 120 * g.speed_mult, g.aim(e.x, e.y), 0.5, "rice", ("red", "blue", "green", "yellow")[k])
            yield g.d(44, 36, 30, 26)


def four_of_a_kind(b, g):
    b.go(W / 2, 80, 40)
    spots = [(110, H / 2 + 20), (W - 110, H / 2 + 20), (W / 2, H - 50)]
    for k, (x, y) in enumerate(spots):
        e = Enemy(g, b.x, b.y, hp=1, sprite="Flandre Scarlet", scale=3, r=12, drops=())
        e.hittable = False
        e.clone = True
        g.spawn_enemy(e)
        e.tasks.spawn(move_to(e, x, y, 45))
        e.tasks.spawn(_clone_fire(e, g, k + 1))
        g.particles.burst(b.x, b.y, 16, (255, 120, 120), (40, 120), kind="glow", size=(2, 4))
    g.texts.add("Let's play together~!", b.x, b.y - 34, (255, 170, 170), 12, 1.6)
    yield from _clone_fire(b, g, 0)


def cranberry_trap(b, g):
    t = 0
    per = 2 * ((W - 20) + (H - 40))

    def perimeter(u):
        d = (u % 1.0) * per
        w, h = W - 20, H - 40
        if d < w:
            return 10 + d, 24
        d -= w
        if d < h:
            return W - 10, 24 + d
        d -= h
        if d < w:
            return W - 10 - d, H - 16
        d -= w
        return 10, H - 16 - d

    while True:
        for k in range(2):
            if t % g.d(9, 7, 5, 4) == 0:
                x, y = perimeter(t * 0.0035 + k * 0.5)
                a = angle_to(x, y, g.player.x, g.player.y)
                g.bullets.shoot(x, y, 25, a, "orb", "red" if k == 0 else "blue", accel=70,
                                max_speed=g.d(100, 120, 140, 160) * g.speed_mult, grace=80)
        if t % 100 == 0:
            g.bullets.ring(b.x, b.y, g.d(12, 16, 20, 24), 90 * g.speed_mult, g.aim(b.x, b.y), "pellet", "purple")
            g.sfx("shot2")
        if t % 6 == 0:
            g.sfx("shot")
        t += 1
        yield 1


def _ripple(bl, g):
    if bl.data:
        return
    hit = False
    if bl.x < 4 or bl.x > W - 4:
        bl.set_angle(math.pi - bl.angle)
        bl.x = clamp(bl.x, 4, W - 4)
        hit = True
    if bl.y < FIELD_TOP - 2 or bl.y > H - 4:
        bl.set_angle(-bl.angle)
        bl.y = clamp(bl.y, FIELD_TOP - 2, H - 4)
        hit = True
    if hit:
        bl.data = 1


def qed(b, g):
    i = 0
    while True:
        n = g.d(22, 28, 34, 40)
        off = random.uniform(0, TAU)
        color = RAINBOW[i % 7]
        for k in range(n):
            g.bullets.shoot(b.x, b.y, g.d(65, 75, 85, 95) * g.speed_mult, off + TAU * k / n, "orb", color, fn=_ripple)
        g.sfx("shot2")
        i += 1
        yield g.d(58, 48, 40, 34)
        if i % 2 == 0:
            b.wander(40)


def and_then_none(b, g):
    b.invisible = True
    g.texts.add("Where did I go~?", b.x, b.y - 30, (255, 170, 170), 12, 1.6)
    t = 0
    while True:
        if t % g.d(70, 56, 46, 38) == 0:
            x = random.uniform(80, W - 80)
            y = random.uniform(60, H - 60)
            if (x - g.player.x) ** 2 + (y - g.player.y) ** 2 > 110 ** 2:
                g.telegraph_circle(x, y, 18, 30, (255, 120, 120))
                g.tasks.spawn(_delayed_ring(g, x, y, 30))
        if t % 4 == 0:
            a = t * 0.05
            g.bullets.shoot(b.x, b.y, 70 * g.speed_mult, a, "rice", "red")
            g.bullets.shoot(b.x, b.y, 70 * g.speed_mult, a + math.pi, "rice", "blue")
        if t % 120 == 0:
            b.wander(80, (100, 60, W - 100, H - 80))
        t += 1
        yield 1


def laevatein(b, g):
    b.go(W / 2, 90, 40)
    yield 40
    side = 1
    while True:
        a0 = g.aim(b.x, b.y) - side * 1.35
        lz = g.bullets.laser(b.x, b.y, a0, length=820, width=g.d(26, 30, 34, 38), warn=g.d(62, 54, 46, 40),
                             active=g.d(80, 92, 104, 116), color="orange", turn=side * g.d(1.05, 1.15, 1.25, 1.35),
                             owner=b, grow=10)
        g.texts.add("Laevatein!", b.x, b.y - 34, (255, 190, 90), 12, 1.0)
        while not lz.dead:
            if lz.lethal() and lz.t % g.d(6, 5, 4, 3) == 0:
                d = random.uniform(60, 520)
                x, y = b.x + lz.cos * d, b.y + lz.sin * d
                g.bullets.shoot(x, y, 25, lz.angle + side * math.pi / 2 + random.uniform(-0.3, 0.3), "rice", "red",
                                accel=45, max_speed=110 * g.speed_mult)
            if lz.t == lz.warn:
                g.shake.add(6)
            yield 1
        side = -side
        g.bullets.ring(b.x, b.y, g.d(12, 16, 20, 24), 90 * g.speed_mult, random.uniform(0, TAU), "star", "yellow")
        g.sfx("shot2")
        yield g.d(40, 32, 26, 20)
        b.wander(30, (200, 70, W - 200, 130))
        yield 30


def _delayed_ring(g, x, y, delay):
    yield delay
    n = g.d(14, 18, 22, 26)
    g.bullets.ring(x, y, n, 75 * g.speed_mult, random.uniform(0, TAU), "big", random.choice(("red", "pink", "purple")),
                   accel=20, max_speed=130 * g.speed_mult)
    g.sfx("explode")


FLANDRE = BossDef(
    "flandre", "Flandre Scarlet", "Sister of the Devil", "Flandre Scarlet", (255, 190, 80),
    [
        SpellCard('Forbidden "Four of a Kind"', four_of_a_kind, hp=90, time=40, bonus=1_000_000),
        SpellCard('Taboo "Laevatein"', laevatein, hp=95, time=40, bonus=1_200_000),
        SpellCard('Taboo "Cranberry Trap"', cranberry_trap, hp=90, time=38, bonus=1_100_000),
        SpellCard('Q.E.D. "Ripples of 495 Years"', qed, hp=100, time=40, bonus=1_300_000),
        SpellCard('Secret Barrage "And Then Will There Be None?"', and_then_none, time=30, bonus=1_500_000, survival=True),
    ],
    circle_points=7,
)

# ======================================================================
# Midbosses
# ======================================================================


def mischievous_warp(b, g):
    while True:
        g.particles.burst(b.x, b.y, 12, (120, 255, 160), (30, 100), kind="glow", size=(2, 4))
        b.x = random.uniform(120, W - 120)
        b.y = random.uniform(60, 170)
        g.particles.burst(b.x, b.y, 12, (120, 255, 160), (30, 100), kind="glow", size=(2, 4))
        g.sfx("whoosh")
        yield 14
        g.bullets.ring(b.x, b.y, g.d(12, 16, 20, 24), 90 * g.speed_mult, random.uniform(0, TAU), "orb", "green")
        g.bullets.fan(b.x, b.y, g.d(3, 3, 5, 5), 140 * g.speed_mult, g.aim(b.x, b.y), 0.4, "rice", "cyan")
        g.sfx("shot2")
        yield g.d(56, 46, 38, 32)


def overdue_notice(b, g):
    while True:
        a = g.aim(b.x, b.y)
        for off in (-0.6, 0.0, 0.6):
            g.bullets.laser(b.x, b.y, a + off, width=10, warn=g.d(52, 44, 38, 32), active=40, color="red")
        yield 34
        for _ in range(g.d(6, 9, 12, 15)):
            g.bullets.shoot(b.x, b.y, 120, random.uniform(0, TAU), "amulet", random.choice(("orange", "red", "purple")),
                            turn=random.choice((-1, 1)) * 0.8, accel=-30, min_speed=50)
        g.sfx("shot2")
        yield 50
        b.wander(40)


def eternal_meek(b, g):
    t = 0
    while True:
        for _ in range(g.d(2, 3, 4, 5)):
            g.bullets.shoot(b.x, b.y, random.uniform(110, 210) * g.speed_mult, random.uniform(0, TAU), "knife",
                            random.choice(("blue", "cyan", "purple")))
        if t % 6 == 0:
            g.sfx("shot")
        t += 1
        if t % 90 == 0:
            b.wander(30)
        yield 2


def lava_cromlech(b, g):
    while True:
        for _ in range(g.d(4, 6, 8, 10)):
            x = random.uniform(20, W - 20)
            g.bullets.shoot(x, -10, 40, math.pi / 2 + random.uniform(-0.2, 0.2), "big", "orange", accel=60,
                            max_speed=150 * g.speed_mult, grace=60)
        g.bullets.ring(b.x, b.y, g.d(10, 14, 18, 22), 70 * g.speed_mult, random.uniform(0, TAU), "orb", "yellow")
        g.sfx("shot2")
        yield g.d(50, 40, 34, 28)
        yield from cough(b, g, 0.15)


DAIYOUSEI = BossDef("daiyousei", "Daiyousei", "Great Fairy of the Lake", "Daiyousei", (110, 230, 150),
                    [SpellCard('Fairy Sign "Mischievous Warp"', mischievous_warp, hp=30, time=20, bonus=150_000)],
                    jp="湖の大妖精", midboss=True)
KOAKUMA = BossDef("koakuma", "Koakuma", "Little Devil of the Library", "Koakuma", (220, 70, 90),
                  [SpellCard('Devil Sign "Overdue Notice"', overdue_notice, hp=38, time=24, bonus=250_000)],
                  jp="図書館の小悪魔", midboss=True)
SAKUYA_MID = BossDef("sakuya", "Sakuya Izayoi", "Perfect and Elegant Maid", "Sakuya Izayoi", (170, 190, 255),
                     [SpellCard('Conjuring "Eternal Meek"', eternal_meek, hp=44, time=20, bonus=300_000)],
                     jp="完全で瀟洒な従者", midboss=True)
PATCHOULI_MID = BossDef("patchouli", "Patchouli Knowledge", "Girl of Knowledge and Shade", "Patchouli Knowledge",
                        (200, 120, 255),
                        [SpellCard('Fire & Earth Sign "Lava Cromlech"', lava_cromlech, hp=50, time=24, bonus=350_000)],
                        circle_points=5, jp="知識と日陰の少女", midboss=True)

CIRNO.jp = "湖上の氷精"
MEILING.jp = "華人小娘"
PATCHOULI.jp = "動かない大図書館"
SAKUYA.jp = "完全で瀟洒な従者"
REMILIA.jp = "永遠に紅い幼き月"
FLANDRE.jp = "悪魔の妹"

ALL = {d.id: d for d in (RUMIA, CIRNO, MEILING, PATCHOULI, SAKUYA, REMILIA, FLANDRE)}
# Spell Practice order: (key, boss) in the order you meet them.
PRACTICE = [("rumia", RUMIA), ("daiyousei", DAIYOUSEI), ("cirno", CIRNO), ("meiling", MEILING), ("koakuma", KOAKUMA),
            ("patchouli", PATCHOULI), ("sakuya", SAKUYA), ("sakuya_mid", SAKUYA_MID), ("remilia", REMILIA),
            ("patchouli_mid", PATCHOULI_MID), ("flandre", FLANDRE)]
PRACTICE_BY_KEY = dict(PRACTICE)
