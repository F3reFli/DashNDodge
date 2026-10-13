import os
import sys

VERSION = "0.1.0"
TITLE = "Dash N Dodge"

# Logical resolution. Everything is drawn on a 640x360 canvas that SDL scales
# up to the window (x2 = 720p, x3 = 1080p, x4 = 1440p), so pixels stay crisp.
W, H = 640, 360
FPS = 60
DT = 1.0 / FPS

# Area the player can move in (the HUD bar sits above FIELD_TOP).
FIELD_LEFT = 8
FIELD_TOP = 24
FIELD_RIGHT = W - 8
FIELD_BOTTOM = H - 8

FONT_PATH = "fonts/pixelmplus-12.ttf"
SPRITES_DIR = "sprites"
MUSIC_DIR = "vfx/musics"
SFX_DIR = "vfx/soundEffects"
MENU_BG = "vfx/backgrounds/menu_bg.jpg"

# Bullet / effect palette: name -> (rim colour, core colour)
PALETTE = {
    "red": ((255, 56, 80), (255, 220, 220)),
    "orange": ((255, 140, 40), (255, 236, 200)),
    "yellow": ((255, 220, 60), (255, 255, 220)),
    "green": ((80, 228, 100), (225, 255, 225)),
    "cyan": ((70, 220, 255), (225, 252, 255)),
    "blue": ((70, 110, 255), (220, 230, 255)),
    "purple": ((170, 80, 255), (240, 225, 255)),
    "pink": ((255, 100, 200), (255, 230, 245)),
    "white": ((200, 200, 230), (255, 255, 255)),
    "gold": ((255, 196, 64), (255, 250, 220)),
    "black": ((40, 20, 60), (130, 100, 160)),
}
RAINBOW = ["red", "orange", "yellow", "green", "cyan", "blue", "purple"]

TEXT = (240, 236, 255)
TEXT_DIM = (150, 140, 175)
ACCENT = (255, 84, 120)
GOLD = (255, 214, 90)
OUTLINE = (16, 8, 28)
BG_DARK = (10, 6, 18)


def resource_path(rel):
    """Absolute path to a bundled resource, in dev and inside PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def user_data_dir():
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(root, "DashNDodge")
    elif sys.platform == "darwin":
        path = os.path.expanduser("~/Library/Application Support/DashNDodge")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        path = os.path.join(root, "dashndodge")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.abspath(".")
    return path
