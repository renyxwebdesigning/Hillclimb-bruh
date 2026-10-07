"""Selectable drivers: names, voices and swear lines; the faces are painted by portraits.py.

Each driver has a head drawer, a voice for espeak and a few lines they
shout when the engine seizes ("Kolbenklemmer").
"""
import math

import pygame

import gfx

DRIVERS = [
    dict(key="default", name="Racer", voice=("de", 50, 165),
         lines=["Verdammt nochmal!", "So ein Mist!", "Nicht schon wieder!"]),
    dict(key="trump", name="Tromald Dump", voice=("en-us", 32, 150),
         lines=["Total disaster! Sad!", "This engine is fake news!", "Terrible, terrible engine!"]),
    dict(key="putin", name="Plad Vutin", voice=("de", 22, 135),
         lines=["Bljin!", "Tschort wasmi!", "Njet, njet, njet!"]),
    dict(key="bonnie", name="Bunny Blue", voice=("en-us+f3", 70, 165),
         lines=["Oh bloody hell!", "Are you kidding me?!", "Oh, for crying out loud!"]),
    dict(key="mozart", name="Zotmard", voice=("de", 62, 180),
         lines=["Sapperlot!", "Potz Blitz und Donnerwetter!", "Himmel, Arsch und Zwirn!"]),
    dict(key="einstein", name="Zweistein", voice=("de", 45, 130),
         lines=["Relativ kaputt!", "Gott würfelt doch!", "Donnerwetter!"]),
    dict(key="roesti", name="Rollbert Rösti", voice=("de", 46, 160),
         lines=["Gopferdammi!", "Huere Seich!", "Das isch jetzt nöd wahr!"]),
    dict(key="blocher", name="Bristoph Chocher", voice=("de", 34, 145),
         lines=["Gopfertami nomal!", "Huere Chaib!", "So en Seich!"]),
    dict(key="maurer", name="Ulimuli", voice=("de", 40, 150),
         lines=["Kä Luscht!", "Gopferdeckel!", "Huere Mischt!"]),
    dict(key="greta", name="Töra Brummberg", voice=("en-us+f2", 66, 160),
         lines=["How dare you, engine!", "You have stolen my horsepower!", "Blah, blah, blah!"]),
    dict(key="federer", name="Fodger Rederer", voice=("de", 52, 160),
         lines=["Come on!", "Oh nei, das isch jetzt blöd!", "Hopp Schwiiz!"]),
]
DRIVER_BY_KEY = {d["key"]: d for d in DRIVERS}

OUT = (44, 28, 24)
SIZE = 1.95          # sprite half-size in head radii (hair and collar stick out)


def face(key, radius_px):
    """A head sprite for the driver; the head centre is the sprite centre."""
    size = radius_px * 2 * SIZE

    import portraits

    def draw(surf, k):
        if key in portraits.PORTRAITS:
            portraits.PORTRAITS[key](portraits.Art(surf, radius_px * k))
        else:
            DRAW.get(key, _default)(Painter(surf, radius_px * k))
    return gfx.supersample(size, size, draw)


def spline(pts, closed=True, steps=8):
    """Catmull-Rom curve through the points (smooth organic shapes)."""
    n = len(pts)
    out = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[-1]
        for j in range(steps):
            t = j / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[d] + (-p0[d] + p2[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t2
                                    + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t3) for d in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


class Painter:
    """Draws in head units: (0, 0) is the head centre, 1 is the head radius, y points up."""

    def __init__(self, surf, R):
        self.s, self.R = surf, R
        self.c = surf.get_width() / 2

    def P(self, x, y):
        return (self.c + x * self.R, self.c - y * self.R)

    def shape(self, col, pts, smooth=True, outline=OUT, ow=0.045):
        q = [self.P(*p) for p in (spline(pts) if smooth else pts)]
        if outline:
            pygame.draw.polygon(self.s, outline, q)
            pygame.draw.polygon(self.s, outline, q, max(1, int(ow * self.R * 2)))
        pygame.draw.polygon(self.s, col, q)
        if outline:
            pygame.draw.polygon(self.s, outline, q, max(1, int(ow * self.R)))

    def fill(self, col, pts, smooth=True):
        self.shape(col, pts, smooth, outline=None)

    def ell(self, col, x, y, w, h, outline=None, ow=0.04):
        r = pygame.Rect(0, 0, w * self.R, h * self.R)
        r.center = self.P(x, y)
        if outline:
            pygame.draw.ellipse(self.s, outline, r.inflate(ow * self.R * 2, ow * self.R * 2))
        pygame.draw.ellipse(self.s, col, r)

    def line(self, col, pts, w, smooth=True):
        q = [self.P(*p) for p in (spline(pts, closed=False) if smooth and len(pts) > 2 else pts)]
        width = max(1, int(w * self.R))
        pygame.draw.lines(self.s, col, False, q, width)
        for pt in (q[0], q[-1]):
            pygame.draw.circle(self.s, col, pt, width / 2)

    def masked(self, mask_pts, draw):
        """Draw with `draw(painter)` but only inside the given smooth outline."""
        tmp = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        draw(Painter(tmp, self.R))
        mask = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), [self.P(*p) for p in spline(mask_pts)])
        tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.s.blit(tmp, (0, 0))


# ------------------------------------------------------------------ parts
FACE_ROUND = [(0, 0.98), (0.62, 0.8), (0.88, 0.3), (0.84, -0.3), (0.62, -0.78), (0.0, -1.02), (-0.62, -0.78),
              (-0.84, -0.3), (-0.88, 0.3), (-0.62, 0.8)]


def face_pts(width=1.0, jaw=1.0, chin=1.0, length=1.0):
    pts = []
    for x, y in FACE_ROUND:
        w = width * (jaw if y < -0.2 else 1.0)
        yy = y * (chin if y < -0.9 else 1.0)
        pts.append((x * w, yy * length if y < 0 else yy))
    return pts


def suit(p, suit_col, tie_col, shirt=(250, 250, 248), pin=None):
    p.fill(gfx.shade(suit_col, 0.85), [(-1.85, -2.0), (-1.7, -1.42), (-1.0, -1.12), (1.0, -1.12), (1.7, -1.42),
                                      (1.85, -2.0)], smooth=False)
    p.fill(suit_col, [(-1.8, -2.0), (-1.62, -1.48), (-0.95, -1.2), (0.95, -1.2), (1.62, -1.48), (1.8, -2.0)])
    p.fill(shirt, [(-0.5, -1.06), (0.5, -1.06), (0.3, -2.0), (-0.3, -2.0)], smooth=False)
    for sd in (-1, 1):
        p.fill(gfx.shade(suit_col, 0.75), [(sd * 0.48, -1.12), (sd * 0.3, -2.0), (sd * 0.62, -1.95), (sd * 0.82, -1.25)],
               smooth=False)
        p.fill((228, 228, 226), [(sd * 0.05, -1.12), (sd * 0.52, -1.04), (sd * 0.36, -1.36)], smooth=False)
    if tie_col:
        p.fill(gfx.shade(tie_col, 0.85), [(-0.13, -1.13), (0.13, -1.13), (0.1, -1.33), (-0.1, -1.33)], smooth=False)
        p.fill(tie_col, [(-0.1, -1.33), (0.1, -1.33), (0.19, -1.9), (0.0, -2.0), (-0.19, -1.9)], smooth=False)
        p.line(gfx.shade(tie_col, 1.3), [(-0.05, -1.45), (0.08, -1.62)], 0.03, smooth=False)
    if pin == "us":
        r = pygame.Rect(0, 0, 0.24 * p.R, 0.15 * p.R)
        r.center = p.P(-0.85, -1.48)
        pygame.draw.rect(p.s, (220, 40, 50), r)
        pygame.draw.rect(p.s, (250, 250, 250), r.inflate(0, -r.h * 0.6))
        pygame.draw.rect(p.s, (40, 60, 150), (r.x, r.y, r.w * 0.45, r.h * 0.55))
    elif pin == "ch":
        r = pygame.Rect(0, 0, 0.22 * p.R, 0.22 * p.R)
        r.center = p.P(-0.88, -1.48)
        pygame.draw.rect(p.s, (220, 30, 40), r)
        cx, cy = r.center
        pygame.draw.rect(p.s, (255, 255, 255), (cx - 0.025 * p.R, cy - 0.07 * p.R, 0.05 * p.R, 0.14 * p.R))
        pygame.draw.rect(p.s, (255, 255, 255), (cx - 0.07 * p.R, cy - 0.025 * p.R, 0.14 * p.R, 0.05 * p.R))


def neck(p, skin, w=0.36):
    p.fill(gfx.shade(skin, 0.78), [(-w, -0.6), (w, -0.6), (w * 1.05, -1.25), (-w * 1.05, -1.25)], smooth=False)


def ears(p, skin, y=0.02, size=1.0, x=0.86):
    for sd in (-1, 1):
        p.ell(gfx.shade(skin, 0.92), sd * x, y, 0.3 * size, 0.46 * size, OUT, 0.04)
        p.ell(gfx.shade(skin, 0.78), sd * (x + 0.02), y - 0.02, 0.13 * size, 0.26 * size)


def head(p, skin, pts):
    p.shape(skin, pts)

    def shading(q):
        q.ell(gfx.shade(skin, 0.95), 0.55, -0.05, 1.3, 2.4)
        q.ell(gfx.shade(skin, 0.9), 0.85, -0.1, 0.8, 2.2)
        q.ell(gfx.shade(skin, 0.9), 0.0, -1.0, 1.4, 0.5)
        q.ell(gfx.shade(skin, 1.06), -0.28, 0.62, 0.95, 0.42)
        q.ell(gfx.mix(skin, (232, 110, 110), 0.28), -0.52, -0.3, 0.42, 0.24)
        q.ell(gfx.mix(skin, (232, 110, 110), 0.22), 0.55, -0.3, 0.38, 0.22)
    p.masked(pts, shading)


def eye(p, x, y, iris, w=0.34, h=0.2, lid=0.0, look=0.04, lash=0.0, skin=None, bags=0.0):
    almond = [(x - w / 2, y), (x - w * 0.22, y + h / 2), (x + w * 0.22, y + h / 2), (x + w / 2, y + h * 0.05),
              (x + w * 0.2, y - h / 2), (x - w * 0.22, y - h / 2)]
    if bags and skin:
        p.line(gfx.shade(skin, 0.8), [(x - w * 0.42, y - h * 0.62), (x, y - h * 0.9), (x + w * 0.42, y - h * 0.62)],
               0.025)
    p.fill((252, 252, 250), almond)

    def inner(q):
        r = h * 0.48
        q.ell(gfx.shade(iris, 0.75), x + look, y - h * 0.02, r * 2.1, r * 2.1)
        q.ell(iris, x + look, y - h * 0.02, r * 1.8, r * 1.8)
        q.ell((22, 20, 22), x + look, y - h * 0.02, r * 0.9, r * 0.9)
        q.ell((255, 255, 255), x + look + r * 0.35, y + r * 0.35, r * 0.45, r * 0.45)
        if lid > 0 and skin:
            q.fill(gfx.shade(skin, 0.94), [(x - w, y + h), (x + w, y + h), (x + w, y + h / 2 - h * lid),
                                           (x - w, y + h / 2 - h * lid)], smooth=False)
    p.masked(almond, inner)
    top = [(x - w / 2, y), (x - w * 0.22, y + h / 2 - h * lid), (x + w * 0.22, y + h / 2 - h * lid), (x + w / 2, y + h * 0.05)]
    p.line(OUT, top, 0.045 + lash)
    if lash:
        for i in range(3):
            fx = x + w * (0.18 + i * 0.12)
            p.line(OUT, [(fx, y + h * 0.45), (fx + 0.05, y + h * 0.75)], 0.03, smooth=False)


def brow(p, x, y, w, col, angle=0.0, thick=0.09):
    d = math.tan(angle) * w / 2
    p.fill(col, [(x - w / 2, y - d - thick * 0.2), (x - w / 2 + 0.04, y - d + thick * 0.6), (x, y + thick * 0.75),
                 (x + w / 2, y + d + thick * 0.35), (x + w / 2, y + d - thick * 0.25), (x, y + thick * 0.05)])


def nose(p, skin, w=0.2, y=-0.28, length=0.42):
    dark = gfx.shade(skin, 0.74)
    p.line(gfx.shade(skin, 0.84), [(w * 0.3, y + length), (w * 0.55, y + length * 0.4), (w * 0.62, y + 0.05)], 0.04)
    p.ell(gfx.shade(skin, 0.9), 0.0, y + 0.02, w * 1.9, w * 1.0)
    p.ell(gfx.shade(skin, 1.06), -0.02, y + 0.08, w * 0.8, w * 0.45)
    p.ell(dark, -w * 0.38, y - 0.04, w * 0.42, w * 0.22)
    p.ell(dark, w * 0.42, y - 0.04, w * 0.42, w * 0.22)


def smile(p, y=-0.58, w=0.5, open_=0.0, lip=(170, 80, 80)):
    if open_:
        mouth = [(-w / 2, y + 0.02), (0, y - 0.03), (w / 2, y + 0.02), (w * 0.3, y - open_), (0, y - open_ * 1.15),
                 (-w * 0.3, y - open_)]
        p.shape((110, 30, 30), mouth, ow=0.03)

        def teeth(q):
            q.fill((252, 250, 244), [(-w, y + 0.1), (w, y + 0.1), (w, y - open_ * 0.45), (-w, y - open_ * 0.45)], False)
        p.masked(mouth, teeth)
    else:
        p.line(gfx.shade(lip, 0.8), [(-w / 2, y + 0.04), (-w * 0.2, y - 0.04), (w * 0.2, y - 0.04), (w / 2, y + 0.04)], 0.05)


# ------------------------------------------------------------- characters
def _default(p):
    skin = (240, 196, 160)
    neck(p, skin)
    suit(p, (36, 112, 210), None, shirt=(36, 112, 210))
    ears(p, skin)
    pts = face_pts()
    head(p, skin, pts)
    for x in (-0.34, 0.34):
        eye(p, x, 0.12, (90, 70, 50))
        brow(p, x, 0.38, 0.32, (80, 56, 40))
    nose(p, skin)
    smile(p, open_=0.12)
    p.shape((84, 60, 42), [(-0.92, 0.25), (-0.88, 0.85), (-0.3, 1.12), (0.4, 1.1), (0.9, 0.8), (0.93, 0.3),
                           (0.6, 0.66), (0.0, 0.78), (-0.6, 0.62)])


DRAW = {"default": _default}     # everyone else is painted by portraits.py

