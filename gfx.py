"""Shared drawing helpers: resolution scale, fonts, outlined text, gradients.

The UI is designed at 1280x720 and scaled by U to whatever window size the
desktop allows, so every layout number in the code is in 720p units.
"""
import math
import subprocess

import pygame

W, H, U = 1280, 720, 1.0
CANVAS = None       # the opaque off-screen surface everything is drawn on

FONTS = {
    "cond": ("DejaVu Sans:style=Condensed Bold", "dejavusanscondensed,dejavusans", True, False),
    "cond_i": ("DejaVu Sans:style=Condensed Bold Oblique", "dejavusanscondensed,dejavusans", True, True),
    "black_i": ("Lato:style=Black Italic", "lato,dejavusans", True, True),
    "heavy": ("Lato:style=Heavy", "lato,dejavusans", True, False),
    "bold": ("Lato:style=Bold", "lato,dejavusans", True, False),
}
_paths = {}
_fonts = {}
_text_cache = {}


def init(width, height):
    global W, H, U, CANVAS
    W, H, U = width, height, height / 720
    # Draw into a surface without an alpha channel. Wayland windows have one,
    # and translucent pixels there show up as black holes on screen.
    CANVAS = pygame.Surface((width, height), 0, 32, (0xFF0000, 0xFF00, 0xFF, 0))
    return CANVAS


def opaque(surf):
    """Convert an opaque picture to the canvas format (fast blits, alpha-free)."""
    return surf.convert(CANVAS) if CANVAS is not None else surf


def s(v):
    """Scale a 720p length to the current window."""
    return v * U


def si(v):
    return int(round(v * U))


def _path(kind):
    if kind not in _paths:
        pattern, fallback, bold, italic = FONTS[kind]
        try:
            p = subprocess.run(["fc-match", "-f", "%{file}", pattern],
                               capture_output=True, text=True, timeout=2).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            p = ""
        _paths[kind] = p or pygame.font.match_font(fallback, bold=bold, italic=italic)
    return _paths[kind]


def font(kind, size):
    key = (kind, si(size))
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(_path(kind), max(6, key[1]))
    return _fonts[key]


def font_px(kind, px):
    """Font at an exact pixel size (for sprite art, not scaled UI)."""
    key = (kind, "px", int(px))
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(_path(kind), max(6, int(px)))
    return _fonts[key]


def text(kind, size, string, color, outline=None, width=2.0, shadow=0.0):
    """Render text, optionally with a dark outline and drop shadow (cached)."""
    key = (kind, size, string, color, outline, width, shadow)
    surf = _text_cache.get(key)
    if surf is not None:
        return surf
    if len(_text_cache) > 800:
        _text_cache.clear()
    f = font(kind, size)
    base = f.render(string, True, color)
    if not outline and not shadow:
        _text_cache[key] = base
        return base
    o = max(1, int(round(s(width)))) if outline else 0
    sh = int(round(s(shadow)))
    out = pygame.Surface((base.get_width() + 2 * o + sh, base.get_height() + 2 * o + sh), pygame.SRCALPHA)
    if outline:
        ring = f.render(string, True, outline)
        steps = 8 if o <= 2 else 16
        offsets = [(round(math.cos(a) * o), round(math.sin(a) * o))
                   for a in (i * math.tau / steps for i in range(steps))]
        if sh:
            for dx, dy in offsets:
                out.blit(ring, (o + dx + sh, o + dy + sh))
        for dx, dy in offsets:
            out.blit(ring, (o + dx, o + dy))
    elif sh:
        out.blit(f.render(string, True, (0, 0, 0)), (sh, sh))
    out.blit(base, (o, o))
    _text_cache[key] = out
    return out


def blit_text(surf, kind, size, string, color, pos, anchor="topleft", **kw):
    t = text(kind, size, string, color, **kw)
    r = t.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surf.blit(t, r)
    return r


def vgradient(w, h, top, bottom):
    """Vertical gradient surface. Colours may include alpha."""
    small = pygame.Surface((1, 2), pygame.SRCALPHA)
    small.set_at((0, 0), tuple(top) if len(top) == 4 else (*top, 255))
    small.set_at((0, 1), tuple(bottom) if len(bottom) == 4 else (*bottom, 255))
    big = pygame.transform.smoothscale(small, (1, max(2, int(h) * 2)))
    # smoothscale from 2px interpolates between the pixel centres; crop the
    # middle so the ends are the exact colours.
    q = big.get_height() // 4
    mid = big.subsurface((0, q, 1, big.get_height() - 2 * q))
    return pygame.transform.smoothscale(mid, (max(1, int(w)), max(1, int(h))))


def supersample(w, h, draw, ss=3):
    """Draw at ss× size with `draw(surface, ss)`, then downsample for smooth edges."""
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
    draw(big, ss)
    return pygame.transform.smoothscale(big, (w, h))


def rounded(w, h, radius, fill, border=None, border_w=0, top=None):
    """Anti-aliased rounded rectangle; `top` makes a vertical gradient fill."""
    def draw(surf, k):
        r = pygame.Rect(0, 0, surf.get_width(), surf.get_height())
        rad = int(radius * k)
        if border:
            pygame.draw.rect(surf, border, r, border_radius=rad)
            r = r.inflate(-2 * border_w * k, -2 * border_w * k)
            rad = max(0, rad - int(border_w * k))
        if top:
            g = vgradient(r.w, r.h, top, fill)
            mask = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=rad)
            g = g.convert_alpha()
            g.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(g, r.topleft)
        else:
            pygame.draw.rect(surf, fill, r, border_radius=rad)
    return supersample(w, h, draw)


def shade(c, f):
    """Darken (f<1) or lighten (f>1) a colour."""
    if f <= 1:
        return tuple(int(v * f) for v in c[:3])
    return tuple(int(v + (255 - v) * (f - 1)) for v in c[:3])


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def fmt(n):
    return f"{int(n):,}"
