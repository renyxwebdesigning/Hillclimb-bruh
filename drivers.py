"""Selectable drivers: cartoon caricatures (and one photo face).

Each driver has a head drawer, a voice for espeak and a few lines they
shout when the engine seizes ("Kolbenklemmer").
"""
import math
import os

import pygame

import gfx

ASSETS = os.path.join(getattr(__import__("sys"), "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "assets")

DRIVERS = [
    dict(key="default", name="Racer", voice=("de", 50, 165),
         lines=["Verdammt nochmal!", "So ein Mist!", "Nicht schon wieder!"]),
    dict(key="trump", name="Donald Trump", voice=("en-us", 32, 150),
         lines=["Total disaster! Sad!", "This engine is fake news!", "Terrible, terrible engine!"]),
    dict(key="putin", name="Putin", voice=("de", 22, 135),
         lines=["Bljin!", "Tschort wasmi!", "Njet, njet, njet!"]),
    dict(key="bonnie", name="Bonnie Blue", voice=("en-us+f3", 70, 165),
         lines=["Oh bloody hell!", "Are you kidding me?!", "Oh, for crying out loud!"]),
    dict(key="mozart", name="Mozart", voice=("de", 62, 180),
         lines=["Sapperlot!", "Potz Blitz und Donnerwetter!", "Himmel, Arsch und Zwirn!"]),
    dict(key="einstein", name="Einstein", voice=("de", 45, 130),
         lines=["Relativ kaputt!", "Gott würfelt doch!", "Donnerwetter!"]),
    dict(key="roesti", name="Albert Rösti", voice=("de", 46, 160),
         lines=["Gopferdammi!", "Huere Seich!", "Das isch jetzt nöd wahr!"]),
    dict(key="blocher", name="Christoph Blocher", voice=("de", 34, 145),
         lines=["Gopfertami nomal!", "Huere Chaib!", "So en Seich!"]),
    dict(key="maurer", name="Ueli Maurer", voice=("de", 40, 150),
         lines=["Kä Luscht!", "Gopferdeckel!", "Huere Mischt!"]),
    dict(key="greta", name="Greta Thunberg", voice=("en-us+f2", 66, 160),
         lines=["How dare you, engine!", "You have stolen my horsepower!", "Blah, blah, blah!"]),
    dict(key="lutz", name="Lutz Wittenberg", voice=("de", 44, 155),
         lines=["Gopferdammi nomal!", "Ja Sapperlot!", "Das darf doch nöd wahr si!"]),
]
DRIVER_BY_KEY = {d["key"]: d for d in DRIVERS}

OUT = (40, 26, 22)


def face(key, radius_px):
    """A head sprite for the driver; the head centre is the sprite centre."""
    if key == "lutz":
        return _photo(radius_px)
    size = radius_px * 2 * 1.75

    def draw(surf, k):
        c = surf.get_width() / 2
        R = radius_px * k

        def P(x, y):
            return (c + x * R, c - y * R)

        def ell(col, x, y, w, h, width=0):
            r = pygame.Rect(0, 0, w * R, h * R)
            r.center = P(x, y)
            pygame.draw.ellipse(surf, col, r, width)

        def poly(col, pts):
            pygame.draw.polygon(surf, col, [P(*p) for p in pts])

        def line(col, a, b, w):
            pygame.draw.line(surf, col, P(*a), P(*b), max(1, int(w * R)))

        def arc(col, x, y, w, h, a0, a1, width):
            r = pygame.Rect(0, 0, w * R, h * R)
            r.center = P(x, y)
            pygame.draw.arc(surf, col, r, a0, a1, max(1, int(width * R)))

        DRAW[key](ell, poly, line, arc, P, R, surf)
    return gfx.supersample(size, size, draw)


def _base(ell, line, arc, skin, brow=(90, 60, 40), eye=(50, 40, 30), mouth="smile", face_w=1.84, face_h=2.0,
          blush=True, eyes_open=0.36):
    ell(gfx.shade(skin, 0.8), -0.93, 0.0, 0.34, 0.44)
    ell(gfx.shade(skin, 0.8), 0.93, 0.0, 0.34, 0.44)
    ell(OUT, 0, 0, face_w + 0.08, face_h + 0.08)
    ell(skin, 0, 0, face_w, face_h)
    ell(gfx.shade(skin, 1.08), -0.15, 0.25, face_w * 0.6, face_h * 0.5)
    for x in (-0.36, 0.36):
        ell((255, 255, 255), x, 0.14, 0.34, eyes_open)
        ell(eye, x + 0.06, 0.12, 0.15, min(0.17, eyes_open * 0.5))
        ell((255, 255, 255), x + 0.09, 0.16, 0.05, 0.05)
        line(brow, (x - 0.17, 0.42), (x + 0.17, 0.44), 0.08)
    ell(gfx.shade(skin, 0.86), 0.05, -0.16, 0.22, 0.26)
    if blush:
        ell(gfx.mix(skin, (240, 120, 120), 0.35), -0.55, -0.25, 0.32, 0.2)
        ell(gfx.mix(skin, (240, 120, 120), 0.35), 0.62, -0.25, 0.32, 0.2)
    if mouth == "smile":
        arc((120, 40, 40), 0.03, -0.42, 0.7, 0.42, math.pi * 1.1, math.pi * 1.9, 0.07)
    elif mouth == "grin":
        ell((120, 30, 30), 0.03, -0.5, 0.82, 0.26)
        ell((255, 255, 255), 0.03, -0.45, 0.68, 0.11)
    elif mouth == "flat":
        line((120, 50, 50), (-0.22, -0.52), (0.26, -0.5), 0.07)
    elif mouth == "o":
        ell((150, 60, 60), 0.05, -0.52, 0.26, 0.2)
        ell((90, 30, 30), 0.05, -0.52, 0.14, 0.1)


def _swiss_pin(ell, poly, P, R, surf):
    r = pygame.Rect(0, 0, 0.36 * R, 0.36 * R)
    r.center = P(0.62, -1.1)
    pygame.draw.rect(surf, (220, 30, 40), r, border_radius=int(0.05 * R))
    cx, cy = r.center
    pygame.draw.rect(surf, (255, 255, 255), (cx - 0.04 * R, cy - 0.12 * R, 0.08 * R, 0.24 * R))
    pygame.draw.rect(surf, (255, 255, 255), (cx - 0.12 * R, cy - 0.04 * R, 0.24 * R, 0.08 * R))


def _default(ell, poly, line, arc, P, R, surf):
    _base(ell, line, arc, (240, 196, 160))
    poly((70, 50, 36), [(-0.95, 0.35), (-0.8, 0.9), (0.0, 1.1), (0.8, 0.9), (0.95, 0.4), (0.4, 0.75), (-0.4, 0.75)])


def _trump(ell, poly, line, arc, P, R, surf):
    skin = (246, 168, 98)
    hair, hair_dk = (252, 214, 112), (214, 170, 70)
    ell(hair_dk, -0.2, 0.55, 2.2, 1.4)
    _base(ell, line, arc, skin, brow=(232, 190, 110), eye=(60, 90, 140), mouth="o", eyes_open=0.22)
    for x in (-0.36, 0.36):
        ell((252, 224, 190), x, 0.14, 0.5, 0.36, 0)
        ell((255, 255, 255), x, 0.14, 0.32, 0.18)
        ell((60, 90, 140), x + 0.06, 0.13, 0.13, 0.13)
    ell(hair, -0.05, 0.86, 2.08, 0.9)
    ell(hair, 0.62, 0.66, 1.16, 0.5)
    ell(hair, -0.82, 0.5, 0.5, 0.7)
    ell(gfx.shade(hair, 1.15), 0.1, 1.0, 1.2, 0.34)
    arc(hair_dk, 0.3, 0.7, 1.6, 0.5, 0.3, 2.6, 0.04)


def _putin(ell, poly, line, arc, P, R, surf):
    skin = (240, 210, 190)
    _base(ell, line, arc, skin, brow=(170, 140, 110), eye=(90, 120, 150), mouth="flat", face_w=1.76, blush=False,
          eyes_open=0.26)
    for side in (-1, 1):
        poly((176, 146, 116), [(side * 0.86, 0.1), (side * 0.92, 0.55), (side * 0.7, 0.85), (side * 0.6, 0.55)])
    line((190, 160, 130), (-0.25, 0.92), (0.2, 0.96), 0.05)
    ell((255, 236, 222), -0.2, 0.75, 0.5, 0.18)
    line(gfx.shade(skin, 0.8), (-0.6, -0.15), (-0.45, -0.4), 0.04)
    line(gfx.shade(skin, 0.8), (0.65, -0.15), (0.5, -0.4), 0.04)


def _bonnie(ell, poly, line, arc, P, R, surf):
    skin = (248, 212, 190)
    hair, hair_dk = (250, 226, 150), (222, 186, 100)
    poly(hair_dk, [(-1.2, 0.6), (-1.35, -0.6), (-1.15, -1.55), (-0.6, -1.4), (0.6, -1.4), (1.15, -1.55), (1.35, -0.6),
                   (1.2, 0.6), (0.6, 1.25), (-0.6, 1.25)])
    _base(ell, line, arc, skin, brow=(200, 160, 90), eye=(60, 130, 220), mouth="smile")
    ell((230, 90, 130), 0.03, -0.5, 0.42, 0.16)
    for x in (-0.36, 0.36):
        line((40, 30, 30), (x - 0.18, 0.3), (x + 0.2, 0.3), 0.05)
    poly(hair, [(-1.05, 0.4), (-0.9, 1.0), (-0.2, 1.22), (0.7, 1.1), (1.08, 0.6), (1.0, 0.2), (0.5, 0.8),
                (-0.3, 0.72), (-0.8, 0.3)])
    poly(gfx.shade(hair, 1.1), [(-0.4, 1.05), (0.4, 1.12), (0.9, 0.7), (0.3, 0.9)])


def _mozart(ell, poly, line, arc, P, R, surf):
    wig, wig_dk = (244, 244, 240), (196, 196, 200)
    ell(wig_dk, -0.05, 0.45, 2.15, 1.65)
    ell((200, 30, 40), -1.18, -0.5, 0.4, 0.26)
    ell((200, 30, 40), -1.18, -0.82, 0.26, 0.4)
    _base(ell, line, arc, (252, 228, 214), brow=(150, 120, 100), eye=(70, 90, 120), mouth="smile")
    ell(wig, 0.0, 0.78, 1.95, 0.85)
    for side in (-1, 1):
        for y in (0.1, -0.22):
            ell(wig_dk, side * 1.02, y, 0.52, 0.28)
            ell(wig, side * 1.0, y + 0.02, 0.46, 0.22)


def _einstein(ell, poly, line, arc, P, R, surf):
    hair = (236, 236, 238)
    for i in range(13):
        a = math.radians(-20 + i * 17.5)
        ell(gfx.shade(hair, 0.85 if i % 2 else 1.0), math.cos(a) * 1.05, math.sin(a) * 1.0 + 0.15, 0.62, 0.5)
    for a, L in ((15, 1.6), (50, 1.55), (90, 1.5), (130, 1.55), (165, 1.6), (-10, 1.5), (190, 1.5)):
        ar = math.radians(a)
        poly(hair, [(math.cos(ar - 0.25) * 0.9, math.sin(ar - 0.25) * 0.9 + 0.1),
                    (math.cos(ar) * L, math.sin(ar) * L + 0.1),
                    (math.cos(ar + 0.25) * 0.9, math.sin(ar + 0.25) * 0.9 + 0.1)])
    _base(ell, line, arc, (238, 200, 172), brow=(225, 225, 228), eye=(80, 60, 50), mouth=None)
    for x in (-0.36, 0.36):
        line((228, 228, 230), (x - 0.22, 0.42), (x + 0.22, 0.48), 0.13)
        arc(gfx.shade((238, 200, 172), 0.8), x, 0.0, 0.32, 0.18, math.pi, 2 * math.pi, 0.03)
    ell((200, 70, 90), 0.05, -0.68, 0.32, 0.38)
    line((150, 40, 60), (0.05, -0.55), (0.05, -0.8), 0.03)
    poly(hair, [(-0.5, -0.32), (-0.1, -0.22), (0.05, -0.28), (0.2, -0.22), (0.6, -0.32), (0.45, -0.5), (0.05, -0.44),
                (-0.35, -0.5)])


def _roesti(ell, poly, line, arc, P, R, surf):
    _base(ell, line, arc, (246, 204, 176), brow=(70, 50, 36), eye=(70, 50, 40), mouth="grin", face_w=1.92)
    poly((82, 58, 42), [(-0.98, 0.3), (-0.9, 0.85), (-0.3, 1.12), (0.5, 1.08), (0.98, 0.7), (0.95, 0.35),
                        (0.6, 0.75), (-0.15, 0.82), (-0.7, 0.62)])
    line((60, 40, 30), (-0.15, 0.82), (0.0, 1.08), 0.04)
    _swiss_pin(ell, poly, P, R, surf)


def _blocher(ell, poly, line, arc, P, R, surf):
    skin = (244, 198, 170)
    _base(ell, line, arc, skin, brow=(110, 110, 110), eye=(70, 60, 50), mouth="grin", face_w=1.96)
    for x in (-0.36, 0.36):
        line((100, 100, 100), (x - 0.2, 0.44), (x + 0.2, 0.47), 0.12)
    for side in (-1, 1):
        poly((222, 222, 222), [(side * 0.9, -0.05), (side * 1.0, 0.45), (side * 0.85, 0.7), (side * 0.72, 0.4)])
    ell((255, 236, 220), -0.25, 0.78, 0.5, 0.2)
    _swiss_pin(ell, poly, P, R, surf)


def _maurer(ell, poly, line, arc, P, R, surf):
    _base(ell, line, arc, (240, 202, 178), brow=(140, 140, 140), eye=(60, 60, 60), mouth="smile", face_w=1.7,
          face_h=2.06)
    poly((172, 172, 174), [(-0.88, 0.3), (-0.82, 0.86), (-0.2, 1.1), (0.55, 1.05), (0.88, 0.62), (0.85, 0.35),
                           (0.5, 0.72), (-0.35, 0.78), (-0.7, 0.55)])
    line((140, 140, 140), (-0.35, 0.78), (-0.25, 1.06), 0.04)
    _swiss_pin(ell, poly, P, R, surf)


def _greta(ell, poly, line, arc, P, R, surf):
    hair, tie = (126, 84, 52), (230, 200, 60)
    _base(ell, line, arc, (246, 214, 196), brow=(110, 74, 46), eye=(70, 90, 110), mouth="flat", blush=False)
    for x, d in ((-0.36, 1), (0.36, -1)):
        line((110, 74, 46), (x - 0.18, 0.4 + 0.08 * d), (x + 0.18, 0.4 - 0.08 * d), 0.08)
    for fx, fy in ((-0.5, -0.12), (-0.42, -0.2), (0.55, -0.1), (0.48, -0.18)):
        ell((200, 140, 110), fx, fy, 0.05, 0.05)
    poly(hair, [(-0.98, 0.25), (-0.85, 0.95), (0.0, 1.12), (0.85, 0.95), (0.98, 0.25), (0.6, 0.7), (0.0, 0.85),
                (-0.6, 0.7)])
    line(gfx.shade(hair, 0.8), (0.0, 0.85), (0.0, 1.1), 0.04)
    for side in (-1, 1):
        for i in range(6):
            ell(gfx.shade(hair, 0.85 if i % 2 else 1.0), side * (0.9 + 0.02 * i), -0.2 - i * 0.24, 0.34, 0.32)
        ell(tie, side * 1.02, -1.62, 0.2, 0.14)


DRAW = {"default": _default, "trump": _trump, "putin": _putin, "bonnie": _bonnie, "mozart": _mozart,
        "einstein": _einstein, "roesti": _roesti, "blocher": _blocher, "maurer": _maurer, "greta": _greta}


def _photo(radius_px):
    path = os.path.join(ASSETS, "lutz_photo.png")
    try:
        img = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return face("default", radius_px)
    crop = img.subsurface(pygame.Rect(10, 8, 164, 228)).copy()
    w, h = int(radius_px * 2 * 0.86), int(radius_px * 2 * 1.2)
    crop = pygame.transform.smoothscale(crop, (w, h))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
    crop.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    size = int(radius_px * 2 * 1.75)
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    ring = pygame.Rect(0, 0, w + 4, h + 4)
    ring.center = (size / 2, size / 2)
    pygame.draw.ellipse(out, (40, 26, 22), ring)
    out.blit(crop, crop.get_rect(center=(size / 2, size / 2)))
    return out
