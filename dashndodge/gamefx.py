"""Turns the gameplay state into screen effects for the GPU renderer:
light sources, colour grade, shockwave refraction, god rays and the
low-health pulse. Called once per drawn frame by GameScene."""

from .config import PALETTE
from .screenfx import GRADES, NEUTRAL, SPELL, bullet_lights


def feed(game, fx, t):
    if game.app.renderer is None:
        return
    _grade(game, fx)
    game.bg.lights(fx, t)
    _lights(game, fx)
    fx.waves_from(game.waves)
    p = game.player
    if p.alive and p.hearts == 1 and game.state == "play":
        fx.danger = 0.75
    boss = game.boss
    if boss is not None and game.spell_dark > 0.3 and boss.state in ("card", "declare") and not boss.invisible:
        # During a spell card the light pours out of the boss instead of the sky.
        fx.godray = (boss.x, boss.y, 0.55 * game.spell_dark, boss.d.color)
    if game.timestop > 0:
        fx.desaturate = 0.6


def _grade(game, fx):
    base = GRADES.get(game.stage.bg, NEUTRAL)
    k = min(1.0, game.spell_dark * 1.2)
    fx.set_grade(base.blend(SPELL, k) if k > 0.02 else base, speed=3.0)


def _lights(game, fx):
    L = fx.lights
    p = game.player
    if p.alive:
        L.add(p.x, p.y, 60, p.c.color, 0.55)
        if p.parry_t > 0:
            L.add(p.x, p.y, 80, (255, 210, 90), 0.9)
        if p.dashing():
            L.add(p.x, p.y, 70, (255, 255, 255), 0.6)
    for s in game.player_spells:
        L.add(p.x, p.y, 170, game.cdef.color, 0.8)
    boss = game.boss
    if boss is not None and boss.state != "dead":
        L.add(boss.x, boss.y, 120, boss.d.color, 0.45 if boss.invisible else 0.85)
    for e in game.enemies:
        if e.alive and -20 < e.x < 660 and -20 < e.y < 380:
            col = PALETTE.get(e.color, PALETTE["white"])[0]
            L.add(e.x, e.y, 34, col, 0.4)
    bullet_lights(L, game.bullets, PALETTE)
    for w in game.waves.items:
        k = w.life / w.max_life
        L.add(w.x, w.y, 40 + w.r1 * (1 - k), w.color, 0.7 * k)
    if game.boss_explosion:
        x, y, bt, col = game.boss_explosion
        L.add(x, y, 200 + bt * 200, col, max(0.0, 1 - bt / 1.6))
