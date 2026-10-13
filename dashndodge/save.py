"""Persistent settings, high scores, unlocks and stats (one JSON file)."""

import json
import os

from .config import user_data_dir

DEFAULT_SETTINGS = {
    "music_volume": 0.6,
    "sfx_volume": 0.7,
    "fullscreen": False,
    "screen_shake": 1.0,
    "show_fps": False,
    "effects": True,
    "scanlines": True,
    "bg_brightness": 0.8,
    "player_name": "",
    "last_character": "reimu",
    "last_difficulty": 1,
}

MODES = ("story", "extra", "endless")
MAX_SCORES = 10


class SaveData:
    def __init__(self, path=None):
        self.path = path or os.path.join(user_data_dir(), "save.json")
        self.settings = dict(DEFAULT_SETTINGS)
        self.scores = {m: [] for m in MODES}
        self.unlocks = {"remilia": False, "extra": False}
        self.stats = {"runs": 0, "clears": 0, "deaths": 0, "tutorial_seen": 0, "best_endless_time": 0.0}
        self.captured = {}  # spell card name -> [captures, attempts]
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return
        self.settings.update({k: v for k, v in data.get("settings", {}).items() if k in DEFAULT_SETTINGS})
        for m in MODES:
            self.scores[m] = list(data.get("scores", {}).get(m, []))[:MAX_SCORES]
        self.unlocks.update(data.get("unlocks", {}))
        self.stats.update(data.get("stats", {}))
        self.captured.update(data.get("captured", {}))

    def write(self):
        data = {
            "settings": self.settings,
            "scores": self.scores,
            "unlocks": self.unlocks,
            "stats": self.stats,
            "captured": self.captured,
        }
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=1, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as exc:
            print(f"[save] could not write {self.path}: {exc}")

    def qualifies(self, mode, score):
        table = self.scores[mode]
        return score > 0 and (len(table) < MAX_SCORES or score > table[-1]["score"])

    def add_score(self, mode, entry):
        table = self.scores[mode]
        table.append(entry)
        table.sort(key=lambda e: e["score"], reverse=True)
        del table[MAX_SCORES:]
        self.write()
        return table.index(entry) if entry in table else -1

    def best(self, mode):
        table = self.scores.get(mode) or []
        return table[0]["score"] if table else 0

    def record_card(self, name, captured):
        rec = self.captured.setdefault(name, [0, 0])
        rec[1] += 1
        if captured:
            rec[0] += 1
