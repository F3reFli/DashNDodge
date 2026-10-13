"""After a run: the Bunbunmaru newspaper (game over), the ending + credits
(victory) and the high score name entry."""

import math
import random

import pygame

from .. import assets, backgrounds, gfx
from ..characters import BY_ID
from ..config import GOLD, H, TEXT, TEXT_DIM, W
from ..fx import Particles
from ..game import DIFF_COLORS, DIFFICULTY
from ..scene import Scene, dim
from ..util import clamp, ease_out_back, ease_out_cubic, fmt_score

INK = (34, 26, 24)
INK_SOFT = (90, 78, 70)
PAPER = (234, 224, 198)
RED_INK = (170, 30, 40)


def first_name(cdef):
    parts = cdef.name.split()
    return parts[0] if cdef.id not in ("meiling",) else "Meiling"


def headline(result):
    c = BY_ID[result["char"]]
    me = first_name(c).upper()
    killer = result["killer"]
    k = killer.upper()
    st = result["stats"]
    options = {
        "a fairy": [f"{me} DEFEATED BY A FAIRY", f"FAIRY BEATS {me}, CLAIMS IT WAS 'TOTALLY ON PURPOSE'", f"SHAME! {me} LOSES TO A FAIRY"],
        "a kedama": [f"{me} TAKEN OUT BY A FLUFFBALL", f"KEDAMA 1, {me} 0", f"FUZZY MENACE DEFEATS {me}"],
        "Rumia": [f"IS THAT SO? {me} SWALLOWED BY THE DARK", f"RUMIA: '{me} WAS CRUNCHY'"],
        "Cirno": ["CIRNO WINS - FIRST TIME IN RECORDED HISTORY", f"'I TOLD YOU I'M THE STRONGEST' - CIRNO DEFEATS {me}"],
        "Hong Meiling": ["GATEKEEPER ACTUALLY DOES HER JOB", f"MEILING STAYS AWAKE LONG ENOUGH TO STOP {me}"],
        "Patchouli Knowledge": [f"LIBRARIAN SHUSHES {me}, PERMANENTLY", f"{me} OVERDUE AT THE LIBRARY"],
        "Sakuya Izayoi": [f"{me} RUNS OUT OF TIME", f"MAID SERVES {me} - WITH KNIVES"],
        "Remilia Scarlet": [f"SCARLET DEVIL CLAIMS {me}", f"'FATE DECIDED IT' - REMILIA ON {me}'S DEFEAT"],
        "Flandre Scarlet": [f"{me} BROKEN. FLANDRE: 'AGAIN! AGAIN!'", f"BASEMENT VISIT ENDS BADLY FOR {me}"],
        "Flandre Scarlet (a clone of)": [f"{me} BEATEN BY ONE OF FOUR FLANDRES", "FOUR OF A KIND BEATS A PAIR"],
        "Tewi Inaba": [f"SCAMMED! {me} FALLS FOR TEWI'S FAKE HEART", "LUCKY RABBIT? MORE LIKE LUCKY SCAM"],
        "Seija Kijin": [f"{me} DEFEATED... OR WAS IT {me} WHO WON? (SEIJA)"],
        "Suika Ibuki": [f"{me} DEFEATED WHILE 'TOTALLY SOBER'"],
        "Koishi Komeiji": [f"{me} HIT BY BULLETS SHE COULDN'T SEE", "NOBODY SAW IT COMING. LITERALLY."],
        "Yuyuko Saigyouji": [f"YUYUKO ATE THE SNACKS, {me} ATE THE BULLETS"],
        "Aya Shameimaru": ["REPORTER CAUSES THE NEWS SHE REPORTS (EXCLUSIVE!)"],
        "Yukari Yakumo": [f"{me} LOST IN THE BOUNDARY", "WRAP-AROUND BULLETS STRIKE FROM BEHIND"],
        "Marisa Kirisame": [f"MARISA 'BORROWS' {me}'S LAST LIFE"],
    }
    if killer == c.name:
        return f"{me} DEFEATED BY... {me}?!"
    if c.id == "meiling" and st.get("naps", 0):
        return "GATEKEEPER NAPS THROUGH OWN DEFEAT"
    pool = options.get(killer) or [f"{me} DEFEATED BY {k}"]
    return random.choice(pool)


def aya_comment(result):
    st = result["stats"]
    lines = [
        "Exclusive photos! Totally not staged.",
        "I was there. I took pictures instead of helping. Journalism!",
        "Another day, another pichuun. Subscribe for more!",
        "Great angle on that last bullet, if I may say so.",
    ]
    if st.get("photos"):
        lines.append(f"Thanks for posing for {st['photos']} of my photos today~!")
    if st.get("graze", 0) > 250:
        lines.append(f"Grazed {st['graze']} bullets and STILL lost. Honestly impressive.")
    if st.get("parries", 0) > 15:
        lines.append(f"{st['parries']} perfect parries! Shame about the last bullet, though.")
    if st.get("spells", 0) == 0 and result["stats"].get("hits", 0) > 0:
        lines.append("Fun fact: spell cards exist. Just saying.")
    return random.choice(lines)


def fake_text(surf, rect, rng, rows=None):
    y = rect.top
    while y + 3 <= rect.bottom:
        w = rect.width if rng.random() > 0.15 else int(rect.width * rng.uniform(0.4, 0.85))
        x = rect.left
        while x < rect.left + w:
            ww = rng.randint(6, 22)
            ww = min(ww, rect.left + w - x)
            pygame.draw.rect(surf, (172, 160, 140), (x, y, ww, 2))
            x += ww + 3
        y += 5


class NewspaperScene(Scene):
    def __init__(self, app, result):
        super().__init__(app)
        self.r = result
        self.t = 0.0
        self.rng = random.Random()
        self.cdef = BY_ID[result["char"]]
        self.backdrop = None
        if result.get("photo") is not None:
            bd = gfx.blur(result["photo"], 4)
            shade = pygame.Surface((W, H))
            shade.fill((70, 60, 80))
            bd.blit(shade, (0, 0), special_flags=pygame.BLEND_MULT)
            self.backdrop = bd
        self.paper = self.build_paper()
        self.landed = False
        self.asked = False
        self.highlight = None
        self.options = ["Retry", "Character Select", "Title"]
        if result["mode"] == "story" and result.get("stage_index", 0) > 0:
            self.options.insert(0, "Continue")
        self.sel = 0

    # ------------------------------------------------------------------
    def build_paper(self):
        r = self.r
        pw, ph = 452, 318
        p = pygame.Surface((pw, ph))
        p.fill(PAPER)
        rng = self.rng
        for _ in range(500):
            c = rng.randint(212, 228)
            p.set_at((rng.randrange(pw), rng.randrange(ph)), (c, c - 8, c - 26))
        m = 12
        assets.blit_text(p, "文々。新聞", (m, 6), 24, INK, outline=None)
        assets.blit_text(p, "BUNBUNMARU", (pw - m, 8), 12, INK, "topright", outline=None)
        assets.blit_text(p, "Gensokyo's #1 (and only) newspaper", (pw - m, 21), 12, INK_SOFT, "topright", outline=None)
        pygame.draw.line(p, INK, (m, 36), (pw - m, 36), 2)
        pygame.draw.line(p, INK, (m, 39), (pw - m, 39), 1)
        issue = rng.randint(100, 999)
        diff = DIFFICULTY[r["difficulty"]]
        assets.blit_text(p, f"Issue No.{issue}  ·  {diff} edition  ·  Price: 1 donation", (m, 42), 12, INK_SOFT, outline=None)
        # Headline
        y = 58
        tag = assets.text(" EXTRA! ", 12, PAPER, None)
        pygame.draw.rect(p, RED_INK, (m, y + 4, tag.get_width(), tag.get_height()))
        p.blit(tag, (m, y + 4))
        hl = headline(r)
        lines = assets.wrap(hl, 24, pw - 2 * m - tag.get_width() - 8)
        for i, line in enumerate(lines[:2]):
            assets.blit_text(p, line, (m + tag.get_width() + 6, y + i * 24), 24, INK, outline=None)
        y += 24 * min(2, len(lines)) + 6
        pygame.draw.line(p, INK_SOFT, (m, y), (pw - m, y))
        y += 6
        # Photo
        ph_w, ph_h = 206, 116
        if r.get("photo") is not None:
            photo = gfx.newspaper_photo(r["photo"], (ph_w, ph_h), INK, PAPER)
        else:
            photo = pygame.Surface((ph_w, ph_h))
            photo.fill(INK_SOFT)
        p.blit(photo, (m, y))
        pygame.draw.rect(p, INK, (m - 1, y - 1, ph_w + 2, ph_h + 2), 1)
        cap_y = y + ph_h + 3
        first = first_name(self.cdef)
        caption = f"Pictured: {first}, moments before defeat by {r['killer']}."
        cap_lines = assets.wrap(caption, 12, ph_w)[:2]
        for i, line in enumerate(cap_lines):
            assets.blit_text(p, line, (m, cap_y + i * 13), 12, INK_SOFT, outline=None)
        cap_bottom = cap_y + 13 * len(cap_lines)
        # Facts column
        cx = m + ph_w + 14
        assets.blit_text(p, "THE FACTS", (cx, y), 12, RED_INK, outline=None)
        st = r["stats"]
        mins, secs = divmod(int(r["time"]), 60)
        facts = [
            ("Score", fmt_score(r["score"])),
            ("Reached", f"{r['stage']}"),
            ("Survived", f"{mins}m {secs:02d}s"),
            ("Grazes", str(st.get("graze", 0))),
            ("Parries", f"{st.get('parries', 0)} ({st.get('reflects', 0)} bullets)"),
            ("Fairies beaten", str(st.get("kills", 0))),
            ("Cards captured", f"{st.get('captures', 0)} / {st.get('cards', 0)}"),
            ("Best chain", str(st.get("max_chain", 0))),
        ]
        fy = y + 16
        for label, val in facts:
            assets.blit_text(p, label, (cx, fy), 12, INK_SOFT, outline=None)
            assets.blit_text(p, val, (cx + 96, fy), 12, INK, outline=None)
            fy += 13
        self.stamp_y = fy - 4
        qy = max(cap_bottom, fy) + 8
        fake_text(p, pygame.Rect(cx, fy + 4, pw - m - cx, qy - fy - 12), rng)
        # Quotes
        pygame.draw.line(p, INK_SOFT, (m, qy - 4), (pw - m, qy - 4))
        quote = rng.choice(self.cdef.death_quotes) if self.cdef.death_quotes else ""
        assets.blit_text(p, f"{quote} - {self.cdef.name}", (m, qy), 12, INK, outline=None)
        aya = aya_comment(r)
        for i, line in enumerate(assets.wrap(f"\"{aya}\" - A. Shameimaru, reporter", 12, pw - 2 * m)):
            assets.blit_text(p, line, (m, qy + 15 + i * 13), 12, INK_SOFT, outline=None)
        fake_text(p, pygame.Rect(m, qy + 46, pw - 2 * m, ph - qy - 52), rng)
        pygame.draw.rect(p, (190, 178, 150), (0, 0, pw, ph), 2)
        self.photo_rect = pygame.Rect(m, 0, ph_w, 0)
        return p

    def stamp(self, rank):
        """Slam a red 'NEW RECORD' stamp onto the paper."""
        txt = assets.text(f"NEW RECORD! #{rank + 1}", 12, RED_INK, None)
        box = pygame.Surface((txt.get_width() + 14, txt.get_height() + 8), pygame.SRCALPHA)
        pygame.draw.rect(box, (*RED_INK, 255), box.get_rect(), 2)
        box.blit(txt, (7, 4))
        box = pygame.transform.rotate(box, 12)
        box.set_alpha(215)
        self.paper.blit(box, (self.paper.get_width() - box.get_width() - 18, self.stamp_y))

    # ------------------------------------------------------------------
    def enter(self):
        self.sfx("whoosh")

    def resume(self):
        pass

    def update(self, dt):
        self.t += dt
        inp = self.app.input
        if not self.landed and self.t > 1.15:
            self.landed = True
            self.sfx("camera")
            self.app.audio.play_music(None, fade_ms=2500)
        if self.landed and not self.asked and self.t > 1.6:
            self.asked = True
            save = self.app.save
            if save.qualifies(self.r["mode"], self.r["score"]):
                self.app.push(NameEntryScene(self.app, self.r, self.on_name))
                return
        if not self.landed:
            if inp.was_pressed("confirm"):
                self.t = 1.15
            return
        if inp.menu("left"):
            self.sel = (self.sel - 1) % len(self.options)
            self.sfx("move")
        elif inp.menu("right"):
            self.sel = (self.sel + 1) % len(self.options)
            self.sfx("move")
        elif inp.was_pressed("confirm") and self.t > 1.8:
            self.sfx("select")
            self.choose(self.options[self.sel])

    def on_name(self, name):
        r = self.r
        entry = {"name": name, "score": r["score"], "char": r["char"], "difficulty": r["difficulty"],
                 "stage": r["stage"], "cleared": r["cleared"]}
        self.highlight = self.app.save.add_score(r["mode"], entry)
        if self.highlight is not None and self.highlight >= 0:
            self.stamp(self.highlight)
            self.sfx("camera")

    def choose(self, opt):
        from ..game import GameScene
        from .charselect import CharSelectScene
        from .title import TitleScene

        r = self.r
        if opt == "Continue":
            self.app.replace(GameScene(self.app, r["mode"], r["char"], r["difficulty"], start_stage=r["stage_index"],
                                       continues=r.get("continues", 0) + 1, charm_ids=r.get("charms", ())))
        elif opt == "Retry":
            self.app.replace(GameScene(self.app, r["mode"], r["char"], r["difficulty"]))
        elif opt == "Character Select":
            self.app.replace(CharSelectScene(self.app, r["mode"]))
        else:
            self.app.replace(TitleScene(self.app))

    def draw(self, surf):
        if self.backdrop is not None:
            surf.blit(self.backdrop, (0, 0))
        else:
            surf.fill((14, 10, 20))
        surf.blit(gfx.vignette((W, H), 200), (0, 0))
        t = min(1.0, self.t / 1.15)
        k = ease_out_cubic(t)
        scale = 0.05 + 0.95 * k
        angle = (1 - k) * 720 - 1.5
        img = pygame.transform.rotozoom(self.paper, angle, scale)
        cy = H / 2 - 12
        shadow = pygame.Surface((img.get_width(), img.get_height()), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 90))
        if t >= 1:
            surf.blit(shadow, (W / 2 - img.get_width() / 2 + 5, cy - img.get_height() / 2 + 6))
        surf.blit(img, (W / 2 - img.get_width() / 2, cy - img.get_height() / 2))
        if self.landed:
            a = clamp((self.t - 1.2) / 0.4, 0, 1)
            gap = 150 if len(self.options) == 3 else 130
            x = W / 2 - gap * (len(self.options) - 1) / 2
            for i, o in enumerate(self.options):
                sel = i == self.sel
                lbl = f"▶ {o}" if sel else o
                if o == "Continue":
                    lbl += f" ({self.r['stage']})"
                assets.blit_text(surf, lbl, (x + i * gap, H - 18), 12, GOLD if sel else TEXT, "midtop", alpha=255 * a)


class NameEntryScene(Scene):
    transparent = True
    MAX = 12

    def __init__(self, app, result, on_done):
        super().__init__(app)
        self.result = result
        self.on_done = on_done
        self.name = app.save.settings.get("player_name", "") or ""
        self.t = 0.0

    def enter(self):
        pygame.key.start_text_input()
        self.sfx("capture")

    def exit(self):
        pygame.key.stop_text_input()

    def handle_event(self, e):
        if e.type == pygame.TEXTINPUT:
            for ch in e.text:
                if ch.isprintable() and len(self.name) < self.MAX:
                    self.name += ch
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.finish()
            elif e.key == pygame.K_ESCAPE:
                self.finish()
        elif e.type == pygame.JOYBUTTONDOWN and e.button in (0, 7):
            self.finish()

    def finish(self):
        name = self.name.strip() or "Anonymous"
        self.app.save.settings["player_name"] = name
        self.app.pop()
        self.on_done(name)

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        dim(surf, 170)
        box = pygame.Rect(0, 0, 340, 130)
        box.center = (W // 2, H // 2)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((10, 6, 20, 230))
        surf.blit(panel, box)
        pygame.draw.rect(surf, GOLD, box, 1)
        k = ease_out_back(min(1.0, self.t / 0.4))
        title = assets.text("NEW HIGH SCORE!", 24, GOLD)
        if k < 1:
            title = pygame.transform.scale(title, (max(1, int(title.get_width() * k)), title.get_height()))
        surf.blit(title, (W / 2 - title.get_width() / 2, box.top + 10))
        assets.blit_text(surf, fmt_score(self.result["score"]), (W / 2, box.top + 40), 12, TEXT, "midtop")
        field = pygame.Rect(0, 0, 220, 22)
        field.center = (W // 2, box.top + 78)
        pygame.draw.rect(surf, (24, 16, 40), field)
        pygame.draw.rect(surf, TEXT_DIM, field, 1)
        cursor = "_" if int(self.t * 3) % 2 == 0 else " "
        assets.blit_text(surf, self.name + cursor, (field.left + 8, field.top + 4), 12, TEXT)
        assets.blit_text(surf, "Type your name · Enter to confirm", (W / 2, box.bottom - 18), 12, TEXT_DIM, "midtop")


CREDITS = [
    ("title", "避ける - DASH N DODGE!"),
    ("gap", ""),
    ("role", "Original game"),
    ("name", "1llumni (2025)"),
    ("role", "v0.1 remake"),
    ("name", "1llumni & Claude"),
    ("role", "Character sprites"),
    ("name", "Majstek - Touhou Mini 16x16 Pack"),
    ("role", "Music"),
    ("name", "\"Dance Dance Little Flowers !\" + original chiptune themes"),
    ("role", "Sound"),
    ("name", "Original game SFX + synthesized effects"),
    ("role", "Font"),
    ("name", "PixelMplus"),
    ("role", "Touhou Project"),
    ("name", "(c) ZUN / Team Shanghai Alice"),
    ("gap", ""),
    ("small", "This is a non-commercial fan game."),
    ("small", "No fairies were harmed. Several were mildly inconvenienced."),
    ("gap", ""),
    ("title", "Thank you for playing!"),
]


class VictoryScene(Scene):
    def __init__(self, app, result):
        super().__init__(app)
        self.r = result
        self.cdef = BY_ID[result["char"]]
        self.t = 0.0
        self.phase = 0
        self.bg = backgrounds.get("moon" if result["mode"] != "extra" else "basement")
        self.particles = Particles(300)
        self.unlocked = []
        save = app.save
        if result["mode"] == "story":
            save.stats["clears"] = save.stats.get("clears", 0) + 1
            if not save.unlocks.get("remilia"):
                save.unlocks["remilia"] = True
                self.unlocked.append("Remilia Scarlet is now playable!")
            if not save.unlocks.get("extra"):
                save.unlocks["extra"] = True
                self.unlocked.append("The Extra Stage is open... if you dare.")
        save.write()
        self.lines = self.cdef.ending if result["mode"] == "story" else [
            "Flandre is defeated. She's thrilled.",
            "\"That was the most fun I've had in 495 years!\"",
            "She wants a rematch tomorrow. And the day after.",
        ]
        self.credit_y = H + 10
        self.asked = False
        self.phase_t = 0.0

    def enter(self):
        self.app.audio.play_music(["ending", "title"])

    def update(self, dt):
        self.t += dt
        self.phase_t += dt
        inp = self.app.input
        if random.random() < 0.4:
            self.particles.emit(random.uniform(0, W), -4, random.uniform(-10, 10), random.uniform(20, 50), 8.0, 2,
                                random.choice(((255, 190, 215), (255, 220, 235))), "petal")
        self.particles.update(dt)
        if self.phase == 0:
            if self.phase_t > 9 or (inp.was_pressed("confirm") and self.phase_t > 1.0):
                self.phase, self.phase_t = 1, 0.0
        elif self.phase == 1:
            self.credit_y -= dt * 34 * (4 if inp.held("confirm") else 1)
            if self.credit_y < -len(CREDITS) * 22 - 20:
                self.phase, self.phase_t = 2, 0.0
        elif self.phase == 2:
            if not self.asked and self.phase_t > 0.6:
                self.asked = True
                if self.app.save.qualifies(self.r["mode"], self.r["score"]):
                    self.app.push(NameEntryScene(self.app, self.r, self.on_name))
                    return
            if self.phase_t > 1.0 and inp.was_pressed("confirm"):
                from .title import TitleScene

                self.app.replace(TitleScene(self.app))

    def on_name(self, name):
        r = self.r
        self.app.save.add_score(r["mode"], {"name": name, "score": r["score"], "char": r["char"],
                                            "difficulty": r["difficulty"], "stage": "All Clear!", "cleared": True})

    def draw(self, surf):
        self.bg.draw(surf, self.t)
        dim(surf, 110)
        self.particles.draw(surf, surf)
        if self.phase == 0:
            a = min(1.0, self.t / 0.6)
            assets.blit_text(surf, "ALL CLEAR!", (W / 2, 30), 24, GOLD, "midtop", alpha=255 * a)
            assets.blit_text(surf, "The scarlet mist lifts over Gensokyo." if self.r["mode"] == "story" else "The basement is quiet again. For now.",
                             (W / 2, 60), 12, TEXT, "midtop", alpha=255 * a)
            art = gfx.CharArt.get(self.cdef.sprite, 6)
            img = art.frame(self.t, 0, False)
            surf.blit(img, (W / 2 - img.get_width() / 2, 100 + math.sin(self.t * 2) * 3))
            for i, line in enumerate(self.lines):
                k = clamp((self.phase_t - 1.0 - i * 1.8) / 0.6, 0, 1)
                if k > 0:
                    assets.blit_text(surf, line, (W / 2, 220 + i * 18), 12, TEXT, "midtop", alpha=255 * k)
        elif self.phase == 1:
            y = self.credit_y
            for kind, text in CREDITS:
                if kind == "title":
                    assets.blit_text(surf, text, (W / 2, y), 24, GOLD, "midtop")
                    y += 30
                elif kind == "role":
                    assets.blit_text(surf, text, (W / 2, y), 12, TEXT_DIM, "midtop")
                    y += 14
                elif kind == "name":
                    assets.blit_text(surf, text, (W / 2, y), 12, TEXT, "midtop")
                    y += 22
                elif kind == "small":
                    assets.blit_text(surf, text, (W / 2, y), 12, TEXT_DIM, "midtop")
                    y += 16
                else:
                    y += 18
        else:
            assets.blit_text(surf, "Final Score", (W / 2, 90), 12, TEXT_DIM, "midtop")
            assets.blit_text(surf, fmt_score(self.r["score"]), (W / 2, 106), 24, GOLD, "midtop")
            d = self.r["difficulty"]
            assets.blit_text(surf, f"{self.cdef.name} · {DIFFICULTY[d]}", (W / 2, 138), 12, DIFF_COLORS[d], "midtop")
            if self.r.get("continues"):
                assets.blit_text(surf, f"Continues used: {self.r['continues']}", (W / 2, 154), 12, TEXT_DIM, "midtop")
            for i, msg in enumerate(self.unlocked):
                assets.blit_text(surf, "★ " + msg, (W / 2, 180 + i * 18), 12, (255, 150, 180), "midtop")
            if int(self.t * 2) % 2 == 0:
                assets.blit_text(surf, "Press Enter", (W / 2, H - 40), 12, TEXT, "midtop")
