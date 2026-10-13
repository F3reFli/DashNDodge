"""Loading and caching of images, character sprites, fonts and text."""

import os

import pygame

from .config import FONT_PATH, OUTLINE, SPRITES_DIR, TEXT, resource_path

_images = {}
_sprite_paths = None
_sprites = {}
_fonts = {}
_text_cache = {}
_TEXT_CACHE_MAX = 900


def image(rel, alpha=True):
    surf = _images.get(rel)
    if surf is None:
        surf = pygame.image.load(resource_path(rel))
        surf = surf.convert_alpha() if alpha else surf.convert()
        _images[rel] = surf
    return surf


def _index_sprites():
    global _sprite_paths
    _sprite_paths = {}
    root = resource_path(SPRITES_DIR)
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() == ".png":
                _sprite_paths[stem.lower()] = os.path.join(dirpath, f)


def sprite(name):
    """16x16 character sprite from the Majstek pack, looked up by name."""
    key = name.lower()
    surf = _sprites.get(key)
    if surf is None:
        if _sprite_paths is None:
            _index_sprites()
        path = _sprite_paths.get(key)
        if path is None:
            surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 0, 255), (8, 8), 7)
        else:
            surf = pygame.image.load(path).convert_alpha()
        _sprites[key] = surf
    return surf


def font(size=12):
    f = _fonts.get(size)
    if f is None:
        try:
            f = pygame.font.Font(resource_path(FONT_PATH), size)
        except (OSError, FileNotFoundError):
            f = pygame.font.Font(None, size + 4)
        _fonts[size] = f
    return f


def text(s, size=12, color=TEXT, outline=OUTLINE, shadow=None):
    """Render crisp pixel text with an optional 1px outline (cached)."""
    key = (s, size, color, outline, shadow)
    surf = _text_cache.get(key)
    if surf is not None:
        return surf
    if len(_text_cache) > _TEXT_CACHE_MAX:
        _text_cache.clear()
    f = font(size)
    base = f.render(s, False, color)
    pad = 1 if outline else 0
    sh = 1 if shadow else 0
    w, h = base.get_width() + pad * 2 + sh, base.get_height() + pad * 2 + sh
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    if shadow:
        sh_surf = f.render(s, False, shadow)
        for ox in range(-pad, pad + 1):
            for oy in range(-pad, pad + 1):
                surf.blit(sh_surf, (pad + ox + 1, pad + oy + 1))
    if outline:
        o = f.render(s, False, outline)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if ox or oy:
                    surf.blit(o, (pad + ox, pad + oy))
    surf.blit(base, (pad, pad))
    _text_cache[key] = surf
    return surf


def blit_text(dst, s, pos, size=12, color=TEXT, anchor="topleft", outline=OUTLINE, shadow=None, alpha=255):
    surf = text(s, size, color, outline, shadow)
    rect = surf.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(max(0, int(alpha)))
    dst.blit(surf, rect)
    return rect


def wrap(s, size, max_w):
    """Greedy word wrap for the pixel font (handles CJK without spaces)."""
    f = font(size)
    lines = []
    for paragraph in s.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            trial = word if not line else line + " " + word
            if f.size(trial)[0] <= max_w:
                line = trial
                continue
            if line:
                lines.append(line)
            # A single word that is too long gets split by characters.
            while f.size(word)[0] > max_w:
                cut = len(word)
                while cut > 1 and f.size(word[:cut])[0] > max_w:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            line = word
        lines.append(line)
    return lines
