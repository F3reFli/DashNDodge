from .. import assets, gfx
from ..characters import BY_ID
from ..config import GOLD, H, TEXT, TEXT_DIM, W
from ..game import DIFF_COLORS, DIFFICULTY
from ..scene import Scene, dim
from ..util import fmt_score

TABS = [("story", "Story"), ("extra", "Extra"), ("endless", "Endless")]


class ScoresScene(Scene):
    transparent = True

    def __init__(self, app, tab="story", highlight=None):
        super().__init__(app)
        self.tab = [k for k, _ in TABS].index(tab)
        self.highlight = highlight
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        inp = self.app.input
        if inp.was_pressed("back") or inp.was_pressed("confirm"):
            self.app.pop()
            return
        if inp.menu("left"):
            self.tab = (self.tab - 1) % len(TABS)
            self.sfx("move")
        elif inp.menu("right"):
            self.tab = (self.tab + 1) % len(TABS)
            self.sfx("move")

    def draw(self, surf):
        surf.blit(gfx.blur(surf, 3), (0, 0))
        dim(surf, 185)
        assets.blit_text(surf, "スコア", (W / 2, 16), 24, (255, 255, 255), "midtop")
        x = W / 2 - 120
        for i, (_k, name) in enumerate(TABS):
            sel = i == self.tab
            r = assets.blit_text(surf, name, (x + i * 120, 48), 12, GOLD if sel else TEXT_DIM, "midtop")
            if sel:
                surf.fill(GOLD, (r.left, r.bottom + 1, r.width, 1))
        mode = TABS[self.tab][0]
        table = self.app.save.scores.get(mode, [])
        y = 74
        cols = (60, 90, 240, 330, 430, 560)
        for label, cx in zip(("#", "Name", "Character", "Difficulty", "Reached", "Score"), cols):
            assets.blit_text(surf, label, (cx, y), 12, TEXT_DIM, "topright" if label == "Score" else "topleft")
        y += 18
        if not table:
            assets.blit_text(surf, "No scores yet. Go make some history!", (W / 2, y + 40), 12, TEXT_DIM, "midtop")
        for i, e in enumerate(table):
            hl = self.highlight is not None and i == self.highlight and int(self.t * 4) % 2 == 0
            col = GOLD if i == 0 else TEXT
            if hl:
                col = (255, 255, 255)
            ch = BY_ID.get(e.get("char"))
            d = e.get("difficulty", 1)
            assets.blit_text(surf, f"{i + 1}.", (cols[0], y), 12, col)
            assets.blit_text(surf, e.get("name", "???")[:12], (cols[1], y), 12, col)
            if ch:
                art = gfx.CharArt.get(ch.sprite, 1)
                surf.blit(art.frames["idle0"], (cols[2] - 20, y - 2))
                assets.blit_text(surf, ch.name.split()[0], (cols[2], y), 12, col)
            assets.blit_text(surf, DIFFICULTY[d], (cols[3], y), 12, DIFF_COLORS[d])
            assets.blit_text(surf, e.get("stage", "?"), (cols[4], y), 12, TEXT_DIM)
            assets.blit_text(surf, fmt_score(e.get("score", 0)), (cols[5], y), 12, col, "topright")
            y += 22
        assets.blit_text(surf, "←→ switch table · Esc: back", (W / 2, H - 20), 12, TEXT_DIM, "midtop")
