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

OUT = (44, 28, 24)
SIZE = 1.95          # sprite half-size in head radii (hair and collar stick out)


def face(key, radius_px):
    """A head sprite for the driver; the head centre is the sprite centre."""
    if key == "lutz":
        return _photo(radius_px)
    size = radius_px * 2 * SIZE

    def draw(surf, k):
        DRAW[key](Painter(surf, radius_px * k))
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


def draw_hair(p, col, outer, front, hi=None, strands=()):
    """Hair: filled between the outer contour and the hairline, outlined only on the outside."""
    pts = spline(outer, closed=False) + spline(front[::-1], closed=False)[1:]
    q = [p.P(*pt) for pt in pts]
    pygame.draw.polygon(p.s, col, q)
    p.line(OUT, outer, 0.045)
    for st in strands:
        p.line(hi or gfx.shade(col, 1.25), st, 0.03)


def tufts(p, col, pts, size=0.2, dark=None):
    """Little locks hanging over the hairline so it isn't a straight cap edge."""
    for x, y, ang in pts:
        dx, dy = math.sin(ang) * size, -math.cos(ang) * size
        lock = [(x - size * 0.45, y + 0.02), (x + size * 0.45, y + 0.02), (x + dx + size * 0.08, y + dy)]
        if dark:
            p.fill(dark, [(a + 0.015, b - 0.015) for a, b in lock], smooth=False)
        p.fill(col, lock, smooth=False)


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


def glasses(p, y, w, h, rim, gap=0.1, rimless=False):
    for sd in (-1, 1):
        cx = sd * (gap / 2 + w / 2)
        r = pygame.Rect(0, 0, w * p.R, h * p.R)
        r.center = p.P(cx, y)
        lens = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(lens, (210, 230, 245, 70), lens.get_rect(), border_radius=int(h * p.R * 0.35))
        p.s.blit(lens, r)
        pygame.draw.rect(p.s, rim, r, max(1, int((0.02 if rimless else 0.04) * p.R)), border_radius=int(h * p.R * 0.35))
        pygame.draw.line(p.s, (255, 255, 255), (r.x + r.w * 0.2, r.y + r.h * 0.3), (r.x + r.w * 0.4, r.y + r.h * 0.18),
                         max(1, int(0.025 * p.R)))
    p.line(rim, [(-gap / 2, y + h * 0.15), (gap / 2, y + h * 0.15)], 0.035, smooth=False)
    for sd in (-1, 1):
        p.line(rim, [(sd * (gap / 2 + w), y + h * 0.2), (sd * 0.86, y + h * 0.3)], 0.035, smooth=False)


def wrinkles(p, skin, forehead=0, laugh=0.0, crows=0.0):
    col = gfx.shade(skin, 0.8)
    for i in range(forehead):
        yy = 0.58 + i * 0.1
        p.line(col, [(-0.42, yy), (0.0, yy + 0.03), (0.42, yy)], 0.025)
    if laugh:
        for sd in (-1, 1):
            p.line(col, [(sd * 0.24, -0.18), (sd * 0.36, -0.42), (sd * 0.38, -0.62 - laugh * 0.1)], 0.03)
    if crows:
        for sd in (-1, 1):
            for a in (-0.25, 0.0, 0.25):
                p.line(col, [(sd * 0.56, 0.12 + a * 0.2), (sd * (0.56 + 0.12 * crows), 0.12 + a * 0.45)], 0.02, False)


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


def _trump(p):
    skin = (238, 158, 98)
    hair, hair_dk, hair_hi = (246, 226, 168), (214, 180, 112), (255, 246, 214)
    neck(p, skin, 0.42)
    suit(p, (30, 40, 78), (36, 80, 170), pin="us")
    ears(p, skin, size=1.05)
    pts = face_pts(width=1.04, jaw=1.08, chin=0.96)
    head(p, skin, pts)

    def jowls(q):
        for sd in (-1, 1):
            q.line(gfx.shade(skin, 0.78), [(sd * 0.3, -0.3), (sd * 0.5, -0.66), (sd * 0.42, -0.92)], 0.035)
        q.ell(gfx.shade(skin, 0.88), 0, -0.88, 0.7, 0.24)
    p.masked(pts, jowls)
    for x in (-0.33, 0.33):
        p.ell((250, 214, 178), x, 0.12, 0.5, 0.34)          # pale "goggle" skin around the eyes
        eye(p, x, 0.12, (70, 110, 170), w=0.3, h=0.13, lid=0.25, skin=(250, 214, 178), bags=0.6)
        brow(p, x, 0.3, 0.34, (196, 150, 92), angle=0.25 if x < 0 else -0.25, thick=0.11)
    p.line(gfx.shade(skin, 0.8), [(-0.06, 0.34), (-0.04, 0.24)], 0.03, False)
    p.line(gfx.shade(skin, 0.8), [(0.06, 0.34), (0.04, 0.24)], 0.03, False)
    nose(p, skin, w=0.24)
    lips = [(-0.2, -0.56), (0.0, -0.5), (0.2, -0.56), (0.12, -0.66), (0.0, -0.68), (-0.12, -0.66)]
    p.shape((196, 104, 90), lips, ow=0.03)
    p.line((140, 60, 60), [(-0.14, -0.6), (0.14, -0.6)], 0.03, False)
    # The famous hair: swept back on the sides, a big blond wave combed forward over the forehead.
    draw_hair(p, hair_dk, [(-0.94, 0.1), (-1.06, 0.62), (-0.88, 1.08), (-0.3, 1.36), (0.45, 1.38), (1.02, 1.1),
                      (1.16, 0.6), (1.0, 0.12)],
         [(-0.94, 0.1), (-0.84, 0.5), (-0.4, 0.62), (0.2, 0.6), (0.7, 0.58), (1.0, 0.12)])
    draw_hair(p, hair, [(-0.86, 0.5), (-0.92, 0.95), (-0.45, 1.26), (0.3, 1.32), (0.92, 1.12), (1.12, 0.74),
                   (1.02, 0.42)],
         [(-0.86, 0.5), (-0.5, 0.66), (0.0, 0.6), (0.5, 0.66), (0.86, 0.56), (1.02, 0.42)], hi=hair_hi,
         strands=[[(1.0, 0.75), (0.5, 0.98), (-0.3, 1.05), (-0.75, 0.86)],
                  [(1.02, 0.6), (0.4, 0.82), (-0.2, 0.86), (-0.7, 0.7)],
                  [(0.8, 1.05), (0.2, 1.2), (-0.4, 1.12)]])
    for sd in (-1, 1):
        p.fill(hair_dk, [(sd * 0.8, 0.2), (sd * 0.98, 0.25), (sd * 0.98, 0.62), (sd * 0.8, 0.5)])


def _putin(p):
    skin = (242, 210, 192)
    hair = (186, 168, 150)
    neck(p, skin, 0.34)
    suit(p, (32, 32, 36), (126, 28, 40))
    ears(p, skin, size=1.08, x=0.82)
    pts = face_pts(width=0.94, jaw=0.86, chin=0.98, length=1.04)
    head(p, skin, pts)

    def detail(q):
        q.ell(gfx.shade(skin, 1.06), -0.1, 0.72, 1.1, 0.5)              # high forehead
        for sd in (-1, 1):
            q.fill(hair, [(sd * 0.95, 0.05), (sd * 0.96, 0.6), (sd * 0.78, 0.88), (sd * 0.62, 0.7), (sd * 0.78, 0.35)])
            q.line(gfx.shade(skin, 0.82), [(sd * 0.22, -0.2), (sd * 0.32, -0.45), (sd * 0.3, -0.62)], 0.025)
        for i in range(4):
            q.line(gfx.mix(hair, skin, 0.55), [(-0.5 + i * 0.12, 0.98), (-0.2 + i * 0.16, 0.9), (0.2 + i * 0.1, 0.94)],
                   0.02)
    p.masked(pts, detail)
    for x in (-0.33, 0.33):
        eye(p, x, 0.12, (110, 140, 160), w=0.3, h=0.15, lid=0.3, skin=skin, bags=0.5, look=0.02)
        brow(p, x, 0.33, 0.3, (176, 150, 128), angle=0.08 if x < 0 else -0.08, thick=0.06)
    nose(p, skin, w=0.18, length=0.46)
    p.line((176, 110, 104), [(-0.2, -0.58), (0.0, -0.6), (0.2, -0.6)], 0.045)
    p.line(gfx.shade(skin, 0.86), [(-0.12, -0.7), (0.12, -0.7)], 0.025, False)


def _bonnie(p):
    skin = (236, 190, 158)
    hair, hair_dk, hair_hi = (246, 232, 200), (214, 192, 150), (255, 250, 236)
    p.fill(hair_dk, [(-1.0, 0.7), (-1.22, -0.4), (-1.28, -1.6), (-0.7, -1.85), (0.7, -1.85), (1.28, -1.6),
                     (1.22, -0.4), (1.0, 0.7), (0.0, 1.15)])
    neck(p, skin, 0.32)
    p.fill((244, 132, 176), [(-1.2, -2.0), (-1.0, -1.35), (-0.4, -1.2), (0.4, -1.2), (1.0, -1.35), (1.2, -2.0)])
    pts = face_pts(width=0.92, jaw=0.88, chin=0.95)
    head(p, skin, pts)
    for x in (-0.33, 0.33):
        eye(p, x, 0.1, (120, 92, 60), w=0.34, h=0.2, lash=0.03, look=0.03)
        p.line((70, 50, 40), [(x - 0.17, 0.12), (x - 0.05, 0.22), (x + 0.12, 0.22), (x + 0.24, 0.16)], 0.06)
        brow(p, x, 0.36, 0.3, (150, 112, 70), angle=-0.15 if x < 0 else 0.15, thick=0.06)
    nose(p, skin, w=0.15, length=0.34)
    lips = [(-0.24, -0.56), (-0.08, -0.5), (0.0, -0.53), (0.08, -0.5), (0.24, -0.56), (0.12, -0.68), (-0.12, -0.68)]
    p.shape((222, 104, 136), lips, ow=0.025)
    p.line((176, 60, 96), [(-0.2, -0.57), (0.2, -0.57)], 0.025, False)
    p.ell((255, 200, 214), -0.06, -0.62, 0.12, 0.04)
    p.shape(hair, [(0.0, 1.08), (-0.6, 0.98), (-0.98, 0.5), (-1.02, -0.3), (-0.96, -1.1), (-0.8, -1.25),
                   (-0.76, -0.4), (-0.7, 0.4), (-0.3, 0.85), (0.0, 0.94), (0.3, 0.85), (0.7, 0.4), (0.76, -0.4),
                   (0.8, -1.25), (0.96, -1.1), (1.02, -0.3), (0.98, 0.5), (0.6, 0.98)], ow=0.03)
    for sd in (-1, 1):
        p.line(hair_hi, [(sd * 0.25, 0.98), (sd * 0.7, 0.72), (sd * 0.86, 0.1), (sd * 0.88, -0.8)], 0.04)
    p.line(hair_dk, [(0.0, 1.06), (0.0, 0.94)], 0.03, False)


def _mozart(p):
    skin = (252, 226, 212)
    wig, wig_dk = (242, 242, 238), (200, 200, 206)
    p.ell((26, 26, 30), -0.98, -0.62, 0.36, 0.24)          # black ribbon of the queue
    p.ell((26, 26, 30), -1.1, -0.82, 0.22, 0.34)
    neck(p, skin, 0.32)
    p.fill((172, 32, 44), [(-1.8, -2.0), (-1.6, -1.42), (-0.9, -1.15), (0.9, -1.15), (1.6, -1.42), (1.8, -2.0)])
    for i in range(5):                                      # lace jabot
        p.ell((252, 252, 248), 0.0, -1.2 - i * 0.16, 0.6 - i * 0.04, 0.24, OUT, 0.02)
    pts = face_pts(width=0.92, jaw=0.94)
    head(p, skin, pts)
    for x in (-0.33, 0.33):
        eye(p, x, 0.1, (110, 130, 150), w=0.32, h=0.19, look=0.03)
        brow(p, x, 0.36, 0.3, (170, 140, 112), angle=-0.1 if x < 0 else 0.1, thick=0.05)
    nose(p, skin, w=0.2, length=0.5)
    smile(p, w=0.4, lip=(200, 100, 100))
    p.shape(wig, [(-0.95, 0.15), (-0.98, 0.75), (-0.55, 1.14), (0.1, 1.24), (0.7, 1.08), (0.98, 0.7),
                  (0.95, 0.15), (0.7, 0.62), (0.0, 0.74), (-0.7, 0.62)])
    p.line(wig_dk, [(-0.6, 0.98), (0.0, 1.08), (0.6, 0.98)], 0.03)
    for sd in (-1, 1):
        for yy in (0.18, -0.12):
            p.ell(wig_dk, sd * 1.0, yy, 0.56, 0.3, OUT, 0.03)
            p.ell(wig, sd * 0.98, yy + 0.02, 0.48, 0.22)
            p.ell(wig_dk, sd * 0.88, yy, 0.12, 0.12)


def _einstein(p):
    skin = (236, 198, 170)
    hair, hair_dk = (240, 240, 240), (196, 196, 202)
    puffs = []
    for i in range(17):
        a = math.pi * (-0.2 + 1.4 * i / 16)
        r = 1.05 + 0.22 * abs(math.sin(i * 1.9)) + (0.12 if i % 3 == 0 else 0)
        size = 0.5 + 0.18 * abs(math.cos(i * 2.3))
        puffs.append((math.cos(a) * r * 1.12, math.sin(a) * r * 0.95 + 0.15, size))
    for x, y, sz in puffs:
        p.ell(OUT, x, y, sz + 0.07, sz * 0.86 + 0.07)
    for x, y, sz in puffs:
        p.ell(hair_dk, x, y, sz, sz * 0.86)
    for x, y, sz in puffs:
        p.ell(hair, x - 0.04, y + 0.04, sz * 0.82, sz * 0.7)
    for x, y, sz in puffs[::2]:
        p.line((255, 255, 255), [(x - sz * 0.2, y + sz * 0.1), (x + sz * 0.15, y + sz * 0.22)], 0.03)
    neck(p, skin, 0.36)
    p.fill((112, 112, 124), [(-1.8, -2.0), (-1.6, -1.4), (-0.9, -1.12), (0.9, -1.12), (1.6, -1.4), (1.8, -2.0)])
    p.fill((92, 92, 104), [(-0.5, -1.1), (0.5, -1.1), (0.4, -1.32), (-0.4, -1.32)])
    ears(p, skin)
    pts = face_pts(width=0.95)
    head(p, skin, pts)
    p.masked(pts, lambda q: wrinkles(q, skin, forehead=3, laugh=0.6))
    crown = [(-0.7, 0.92, 0.42), (-0.32, 1.06, 0.44), (0.08, 1.1, 0.46), (0.46, 1.04, 0.44), (0.78, 0.86, 0.4)]
    for x, y, sz in crown:
        p.ell(OUT, x, y, sz + 0.07, sz * 0.8 + 0.07)
    for x, y, sz in crown:
        p.ell(hair_dk, x, y, sz, sz * 0.8)
        p.ell(hair, x - 0.03, y + 0.04, sz * 0.8, sz * 0.62)
    for x in (-0.33, 0.33):
        eye(p, x, 0.08, (90, 70, 56), w=0.3, h=0.17, lid=0.25, skin=skin, bags=1.0, look=0.02)
        brow(p, x, 0.34, 0.36, (220, 220, 222), angle=-0.3 if x < 0 else 0.3, thick=0.13)
    nose(p, skin, w=0.24, length=0.46)
    p.ell((110, 30, 40), 0.02, -0.66, 0.36, 0.3)
    p.ell((224, 96, 120), 0.02, -0.76, 0.28, 0.32, OUT, 0.025)
    p.line((170, 60, 80), [(0.02, -0.66), (0.02, -0.84)], 0.025, False)
    p.shape(hair, [(-0.52, -0.42), (-0.25, -0.34), (0.0, -0.38), (0.25, -0.34), (0.54, -0.42), (0.44, -0.6),
                   (0.02, -0.56), (-0.42, -0.6)], ow=0.03)
    for i in range(5):
        x0 = -0.36 + i * 0.18
        p.line(hair_dk, [(x0, -0.4), (x0 + 0.03, -0.54)], 0.02, False)


def _roesti(p):
    skin = (240, 202, 178)
    hair, hair_dk, hair_hi = (120, 86, 58), (84, 58, 40), (160, 122, 86)
    neck(p, skin, 0.34)
    suit(p, (40, 42, 50), (120, 120, 128))
    ears(p, skin, x=0.82)
    pts = face_pts(width=0.92, jaw=0.88, length=1.08)
    head(p, skin, pts)
    p.masked(pts, lambda q: wrinkles(q, skin, laugh=0.4))
    for x in (-0.31, 0.31):
        eye(p, x, 0.12, (96, 74, 52), w=0.28, h=0.14, lid=0.15, skin=skin, look=0.02)
        brow(p, x, 0.36, 0.3, hair_dk, angle=-0.08 if x < 0 else 0.08, thick=0.07)
    glasses(p, 0.12, 0.42, 0.26, (150, 152, 160), gap=0.12, rimless=True)
    nose(p, skin, w=0.2, length=0.48)
    smile(p, y=-0.62, w=0.46)
    draw_hair(p, hair, [(-0.86, 0.22), (-0.98, 0.72), (-0.72, 1.14), (-0.1, 1.36), (0.55, 1.3), (0.98, 0.98),
                   (0.98, 0.5), (0.88, 0.2)],
         [(-0.86, 0.22), (-0.76, 0.6), (-0.3, 0.8), (0.2, 0.7), (0.62, 0.66), (0.88, 0.2)], hi=hair_hi,
         strands=[[(-0.7, 0.9), (-0.2, 1.18), (0.4, 1.16)], [(-0.5, 0.82), (0.1, 1.0), (0.7, 0.92)],
                  [(0.2, 1.24), (0.7, 1.1), (0.9, 0.8)]])
    tufts(p, hair, [(-0.45, 0.8, 0.55), (-0.15, 0.78, 0.45), (0.15, 0.72, 0.5), (0.45, 0.7, 0.35)],
          size=0.2, dark=hair_dk)


def _blocher(p):
    skin = (238, 188, 166)
    hair, hair_dk = (232, 232, 234), (190, 190, 196)
    neck(p, skin, 0.42)
    suit(p, (104, 106, 114), (84, 104, 136))
    ears(p, skin, size=1.15, x=0.92)
    pts = face_pts(width=1.06, jaw=1.06, chin=0.96)
    head(p, skin, pts)
    p.masked(pts, lambda q: wrinkles(q, skin, forehead=2, laugh=1.0, crows=1.0))
    for x in (-0.34, 0.34):
        eye(p, x, 0.12, (90, 100, 110), w=0.28, h=0.11, lid=0.2, skin=skin, bags=0.8, look=0.02)
        brow(p, x, 0.35, 0.34, (130, 128, 128), angle=-0.15 if x < 0 else 0.15, thick=0.09)
    glasses(p, 0.12, 0.44, 0.28, (176, 178, 186), gap=0.12)
    nose(p, skin, w=0.26, length=0.46)
    smile(p, y=-0.56, w=0.64, open_=0.14)
    draw_hair(p, hair, [(-0.98, 0.2), (-1.02, 0.66), (-0.78, 1.02), (-0.25, 1.18), (0.3, 1.18), (0.8, 1.02),
                   (1.02, 0.66), (0.98, 0.2)],
         [(-0.98, 0.2), (-0.86, 0.6), (-0.55, 0.9), (0.0, 0.98), (0.55, 0.9), (0.86, 0.6), (0.98, 0.2)],
         hi=hair_dk, strands=[[(-0.6, 0.98), (-0.2, 1.1), (0.25, 1.1)], [(-0.3, 0.98), (0.2, 1.04), (0.6, 0.98)],
                              [(-0.9, 0.45), (-0.82, 0.8)], [(0.9, 0.45), (0.82, 0.8)]])


def _maurer(p):
    skin = (236, 190, 166)
    hair = (176, 176, 178)
    neck(p, skin, 0.32)
    suit(p, (30, 30, 34), (126, 28, 40), pin="ch")
    ears(p, skin, size=1.1, x=0.8)
    pts = face_pts(width=0.88, jaw=0.84, chin=0.96, length=1.12)
    head(p, skin, pts)

    def detail(q):
        for sd in (-1, 1):
            q.fill(hair, [(sd * 0.95, -0.05), (sd * 0.95, 0.5), (sd * 0.8, 0.68), (sd * 0.7, 0.45), (sd * 0.78, 0.05)])
        q.ell((255, 236, 222), -0.2, 0.8, 0.5, 0.18)                    # shine on the bald head
        wrinkles(q, skin, forehead=2, laugh=0.9)
    p.masked(pts, detail)
    for x in (-0.31, 0.31):
        eye(p, x, 0.12, (96, 110, 120), w=0.28, h=0.13, lid=0.3, skin=skin, bags=1.0, look=0.02)
        brow(p, x, 0.34, 0.3, (120, 116, 112), angle=0.0, thick=0.07)
    nose(p, skin, w=0.2, length=0.5)
    smile(p, y=-0.64, w=0.46)


def _greta(p):
    skin = (248, 222, 208)
    hair, hair_dk, tie = (126, 90, 62), (92, 64, 44), (230, 200, 60)
    neck(p, skin, 0.3)
    p.fill((240, 170, 190), [(-1.3, -2.0), (-1.1, -1.38), (-0.4, -1.18), (0.4, -1.18), (1.1, -1.38), (1.3, -2.0)])
    ears(p, skin, x=0.8)
    pts = face_pts(width=0.9, jaw=0.9, chin=0.94)
    head(p, skin, pts)
    for fx, fy in ((-0.48, -0.12), (-0.4, -0.2), (-0.55, -0.22), (0.5, -0.12), (0.44, -0.2), (0.56, -0.22)):
        p.ell((206, 150, 124), fx, fy, 0.04, 0.04)
    for x, ang in ((-0.33, 0.28), (0.33, -0.28)):
        eye(p, x, 0.1, (110, 136, 156), w=0.3, h=0.17, look=0.02)
        brow(p, x, 0.32, 0.3, hair_dk, angle=ang, thick=0.07)
    nose(p, skin, w=0.16, length=0.34)
    p.line((176, 110, 110), [(-0.16, -0.6), (0.0, -0.62), (0.16, -0.6)], 0.045)
    p.shape(hair, [(-0.9, 0.3), (-0.92, 0.8), (-0.5, 1.12), (0.0, 1.18), (0.5, 1.12), (0.92, 0.8), (0.9, 0.3),
                   (0.6, 0.72), (0.0, 0.86), (-0.6, 0.72)])
    p.line(hair_dk, [(0.0, 0.86), (0.0, 1.16)], 0.03, False)
    for i in range(8):                                     # one long braid over the shoulder
        y = 0.1 - i * 0.25
        x = 0.92 + 0.05 * math.sin(i)
        p.ell(hair_dk if i % 2 else hair, x, y, 0.36, 0.32, OUT, 0.025)
    p.ell(tie, 0.95, -1.9, 0.2, 0.14, OUT, 0.02)


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
