import colorsys
import math

from .config import FPS

TAU = math.tau


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def approach(v, target, step):
    if v < target:
        return min(v + step, target)
    return max(v - step, target)


def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * t


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t, s=1.70158):
    t = clamp(t, 0.0, 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


def angle_to(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


def dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def sec(seconds):
    """Seconds -> whole logic frames (scripts wait in frames)."""
    return max(1, int(round(seconds * FPS)))


def hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def mix(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def scale_color(c, k):
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def fmt_score(n):
    return f"{int(n):,}".replace(",", " ")
