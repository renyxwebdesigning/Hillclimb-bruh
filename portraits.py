"""Painted driver portraits: soft shading, layered hair and detailed eyes.

Everything is drawn in head units like drivers.Painter: (0, 0) is the head centre, 1 is the head
radius and y points up. Soft shadows and highlights are painted on separate layers, blurred and
clipped to the skin, which is what makes the faces read as real heads instead of flat stickers.
"""
import math
import random

import pygame

import gfx
from drivers import spline

LIGHT = (-0.45, 0.6)                  # light comes from the upper left


def blur(surf, radius):
    """Cheap soft blur (works in pygame and pygame-ce): shrink, then scale back up, twice."""
    if radius < 1:
        return surf
    w, h = surf.get_size()
    f = max(1.0, radius / 1.6)
    sw, sh = max(1, int(w / f)), max(1, int(h / f))
    small = pygame.transform.smoothscale(surf, (sw, sh))
    small = pygame.transform.smoothscale(pygame.transform.smoothscale(small, (max(1, sw // 2), max(1, sh // 2))),
                                         (sw, sh))
    return pygame.transform.smoothscale(small, (w, h))


class Art:
    def __init__(self, surf, R):
        self.s, self.R = surf, R
        self.c = surf.get_width() / 2
        self.size = surf.get_size()

    # ------------------------------------------------------------ geometry
    def P(self, x, y):
        return (self.c + x * self.R, self.c - y * self.R)

    def poly(self, pts, smooth=True, closed=True):
        return [self.P(*p) for p in (spline(pts, closed=closed) if smooth else pts)]

    def layer(self):
        return pygame.Surface(self.size, pygame.SRCALPHA)

    def mask(self, pts):
        m = self.layer()
        pygame.draw.polygon(m, (255, 255, 255, 255), self.poly(pts))
        return m

    # ------------------------------------------------------------- drawing
    # pygame.draw replaces pixels instead of blending, so translucent strokes made straight onto
    # the portrait go through a temporary layer.
    def _blend(self, col, surf, paint):
        if surf is None and len(col) == 4 and col[3] < 255:
            lay = self.layer()
            paint(lay)
            self.s.blit(lay, (0, 0))
        else:
            paint(surf or self.s)

    def fill(self, col, pts, smooth=True, surf=None):
        q = self.poly(pts, smooth)
        self._blend(col, surf, lambda tgt: pygame.draw.polygon(tgt, col, q))

    def ell(self, col, x, y, w, h, surf=None, angle=0.0):
        r = pygame.Rect(0, 0, max(1, w * self.R), max(1, h * self.R))
        if angle:
            e = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.ellipse(e, col, e.get_rect())
            e = pygame.transform.rotate(e, angle)
            (surf or self.s).blit(e, e.get_rect(center=self.P(x, y)))   # blit blends by itself
            return
        r.center = self.P(x, y)
        self._blend(col, surf, lambda tgt: pygame.draw.ellipse(tgt, col, r))

    def line(self, col, pts, w, smooth=True, surf=None):
        q = [self.P(*p) for p in (spline(pts, closed=False) if smooth and len(pts) > 2 else pts)]
        width = max(1, int(w * self.R))

        def paint(tgt):
            pygame.draw.lines(tgt, col, False, q, width)
            for pt in (q[0], q[-1]):
                pygame.draw.circle(tgt, col, pt, width / 2)
        self._blend(col, surf, paint)

    def taper(self, col, pts, w0, w1, surf=None, steps=10):
        """A stroke that thins from w0 to w1 (hair strands, lashes, wrinkles)."""
        q = spline(pts, closed=False, steps=steps) if len(pts) > 2 else pts
        n = len(q)
        left, right = [], []
        for i, (x, y) in enumerate(q):
            a = q[max(0, i - 1)]
            b = q[min(n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy) or 1.0
            w = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
            left.append((x - dy / d * w, y + dx / d * w))
            right.append((x + dy / d * w, y - dx / d * w))
        poly = [self.P(*p) for p in left + right[::-1]]
        self._blend(col, surf, lambda tgt: pygame.draw.polygon(tgt, col, poly))

    def soft(self, draw, radius, clip=None, alpha=255, mode=0):
        """Paint `draw(layer)` on its own layer, blur it, optionally clip it, then blend it in."""
        lay = self.layer()
        draw(lay)
        lay = blur(lay, radius * self.R)
        if clip is not None:
            lay.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if alpha < 255:
            lay.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        self.s.blit(lay, (0, 0), special_flags=mode)


def rgba(col, a):
    return (col[0], col[1], col[2], a)


# ---------------------------------------------------------------- face shape
def face_outline(top=1.0, temple=0.8, cheek=0.84, jaw=0.66, chin=0.3, chin_y=-1.08, cheek_y=0.0, jaw_y=-0.7):
    right = [(0.0, top), (0.55 * temple, top - 0.1), (temple, 0.5), (cheek, cheek_y), (cheek * 0.96, -0.32),
             (jaw, jaw_y), (chin, chin_y + 0.1), (chin * 0.5, chin_y + 0.01)]
    left = [(-x, y) for x, y in right[1:][::-1]]
    return right + [(0.0, chin_y)] + left


class Face:
    """Builds one portrait from a few parameters, layer by layer."""

    def __init__(self, art, skin, outline, seed=1):
        self.a, self.skin, self.pts = art, skin, outline
        self.clip = art.mask(outline)
        self.rng = random.Random(seed)
        self.line_col = gfx.shade(skin, 0.42)

    # ------------------------------------------------------------ the head
    def base(self, flush=0.0, form=1.0):
        a, skin = self.a, self.skin
        # a thin dark rim keeps the head readable when it is tiny in the vehicle
        a.fill(gfx.shade(self.skin, 0.55), [(x * 1.022, y * 1.016 + (0.006 if y > 0 else -0.006)) for x, y in self.pts])
        a.fill(skin, self.pts)
        dark = gfx.mix(gfx.shade(skin, 0.74), (130, 58, 48), 0.3)          # shadows on skin are warm, not grey
        deep = gfx.mix(gfx.shade(skin, 0.6), (110, 46, 40), 0.3)
        light = gfx.mix(skin, (255, 246, 236), 0.45)
        red = gfx.mix(skin, (214, 84, 84), 0.55)

        def shadows(l):
            a.ell(rgba(dark, 110), 1.0, -0.15, 0.9, 2.6, l)               # shadow side (light is upper left)
            a.ell(rgba(dark, 60), -1.08, -0.1, 0.5, 2.2, l)               # rim of the lit side
            a.ell(rgba(deep, 80), 0.0, -1.14, 1.3, 0.5, l)                # under the jaw
            for sd in (-1, 1):
                a.ell(rgba(dark, 60 if sd > 0 else 38), sd * 0.62, -0.44, 0.34, 0.6, l, angle=sd * 20)   # under cheekbones
                a.ell(rgba(dark, 55), sd * 0.84, 0.42, 0.3, 0.5, l)       # temples
        a.soft(shadows, 0.22 * form, self.clip, alpha=int(255 * min(1.0, form)))

        def lights(l):
            a.ell(rgba(light, 130), -0.18, 0.64, 0.9, 0.5, l)             # forehead
            a.ell(rgba(light, 110), -0.46, -0.08, 0.32, 0.26, l)          # cheekbone
            a.ell(rgba(light, 60), 0.4, -0.06, 0.22, 0.2, l)
            a.ell(rgba(light, 110), -0.04, -0.86, 0.26, 0.14, l)          # chin
        a.soft(lights, 0.12, self.clip)
        if flush:
            def cheeks(l):
                for sd in (-1, 1):
                    a.ell(rgba(red, int(120 * flush)), sd * 0.5, -0.26, 0.42, 0.3, l)
                a.ell(rgba(red, int(70 * flush)), 0.0, -0.18, 0.2, 0.2, l)
            a.soft(cheeks, 0.12, self.clip)

    def ears(self, y=0.02, size=1.0, x=0.86, back=False):
        a, skin = self.a, self.skin
        for sd in (-1, 1):
            ex = sd * x
            shape = [(ex, y + 0.24 * size), (ex + sd * 0.16 * size, y + 0.2 * size), (ex + sd * 0.19 * size, y),
                     (ex + sd * 0.12 * size, y - 0.2 * size), (ex, y - 0.26 * size)]
            a.fill(self.line_col, [(px + sd * 0.025, py) for px, py in shape])
            a.fill(gfx.shade(skin, 0.94 if sd < 0 else 0.86), shape)
            a.line(gfx.shade(skin, 0.68), [(ex + sd * 0.05, y + 0.15 * size), (ex + sd * 0.12 * size, y + 0.08 * size),
                                           (ex + sd * 0.1 * size, y - 0.1 * size)], 0.035)

    def neck(self, w=0.4, shirt=None):
        a, skin = self.a, self.skin
        pts = [(-w, -0.5), (w, -0.5), (w * 1.08, -1.45), (-w * 1.08, -1.45)]
        a.fill(gfx.shade(skin, 0.86), pts, smooth=False)
        a.soft(lambda l: a.ell(rgba(gfx.mix(gfx.shade(skin, 0.55), (110, 46, 40), 0.3), 200), 0.05, -0.98, w * 2.4,
                               0.5, l), 0.1, a.mask(pts))

    # ------------------------------------------------------------- features
    def eye(self, x, y, iris, w=0.3, h=0.15, lid=0.2, look=0.0, bags=0.0, lashes=0.0, socket=1.0, squint=0.0,
            liner=1.0, white=(244, 240, 236), crease=1.0):
        a, skin = self.a, self.skin
        sd = 1 if x > 0 else -1
        # eye socket shadow and the crease of the upper lid
        sock = gfx.shade(skin, 0.68)
        a.soft(lambda l: a.ell(rgba(sock, int(50 * socket)), x + sd * 0.02, y + 0.05, w * 1.5, h * 2.4, l), 0.09, self.clip)
        if crease:
            a.line(rgba(gfx.shade(skin, 0.66), int(200 * crease)),
                   [(x - w * 0.46, y + h * 0.7), (x, y + h * 1.25), (x + w * 0.46, y + h * 0.75)], 0.022)
        if bags:
            a.soft(lambda l: a.ell(rgba(gfx.shade(skin, 0.74), int(70 * bags)), x, y - h * 1.0, w * 1.0, h * 0.8, l),
                   0.05, self.clip)
            a.line(rgba(gfx.shade(skin, 0.62), int(110 * bags)),
                   [(x - w * 0.42, y - h * 0.9), (x, y - h * (1.25 + 0.3 * bags)), (x + w * 0.44, y - h * 0.86)], 0.018)
        top = h / 2 * (1 - squint)
        almond = [(x - w / 2, y - h * 0.02), (x - w * 0.22, y + top), (x + w * 0.2, y + top * 1.02),
                  (x + w / 2, y + h * 0.08), (x + w * 0.22, y - h * 0.46), (x - w * 0.2, y - h * 0.46)]
        clip = a.mask(almond)
        lay = a.layer()
        a.fill(white, almond, surf=lay)
        r = h * 0.56
        ix, iy = x + look, y - h * 0.02
        a.ell(gfx.shade(iris, 0.55), ix, iy, r * 2.1, r * 2.1, lay)
        a.ell(iris, ix, iy, r * 1.86, r * 1.86, lay)
        a.ell(gfx.mix(iris, (255, 255, 255), 0.35), ix - r * 0.1, iy - r * 0.38, r * 1.1, r * 0.8, lay)
        a.ell((16, 14, 16), ix, iy, r * 0.82, r * 0.82, lay)
        # upper lid casts a shadow on the eyeball, and may hang over the iris
        a.ell(rgba((60, 40, 36), 90), x, y + h * 0.42, w * 1.1, h * 0.6, lay)
        if lid:
            a.fill(gfx.shade(skin, 0.9), [(x - w, y + h), (x + w, y + h), (x + w, y + top - h * lid),
                                          (x - w, y + top - h * lid)], smooth=False, surf=lay)
        a.ell((255, 255, 255), ix + r * 0.32, iy + r * 0.34, r * 0.42, r * 0.42, lay)
        lay.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        a.s.blit(lay, (0, 0))
        lid_y = top - h * lid
        upper = [(x - w / 2, y - h * 0.02), (x - w * 0.22, y + lid_y), (x + w * 0.2, y + lid_y * 1.02),
                 (x + w / 2, y + h * 0.08)]
        a.taper((28, 20, 20), upper, 0.03 * liner + lashes * 0.02, 0.05 * liner + lashes * 0.03)
        a.line(rgba(gfx.shade(skin, 0.6), 160), [(x - w * 0.42, y - h * 0.18), (x, y - h * 0.5),
                                                 (x + w * 0.46, y - h * 0.08)], 0.016)
        if lashes:
            for i in range(5):
                t = 0.35 + i * 0.15
                px = x - w / 2 + w * t
                py = y + lid_y * (1 - abs(t - 0.45) * 0.9)
                a.taper((24, 16, 16), [(px, py), (px + 0.03 + 0.03 * t, py + 0.06 * lashes)], 0.02, 0.004)

    def brow(self, x, y, w, col, angle=0.0, thick=0.07, arch=0.04, hairs=30, bushy=0.0):
        a = self.a
        sd = 1 if x > 0 else -1
        d = math.tan(angle) * w / 2
        inner, outer = (x - sd * w / 2, y - d * sd), (x + sd * w / 2, y + d * sd)
        mid = ((inner[0] + outer[0]) / 2, (inner[1] + outer[1]) / 2 + arch)
        a.soft(lambda l: a.taper(rgba(col, 120), [inner, mid, outer], thick * 1.4, thick * 0.6, surf=l), 0.02,
               self.clip)
        rng = self.rng
        for i in range(hairs):
            t = rng.random()
            px = inner[0] + (outer[0] - inner[0]) * t
            py = inner[1] + (outer[1] - inner[1]) * t + arch * (1 - (2 * t - 1) ** 2) + rng.uniform(-0.4, 0.4) * thick
            ln = thick * (0.9 + 0.6 * bushy) * rng.uniform(0.8, 1.3)
            ang = (0.25 + 0.9 * t) * sd + rng.uniform(-0.2, 0.2)
            c = gfx.shade(col, rng.uniform(0.75, 1.25))
            a.taper(c, [(px, py - ln * 0.4), (px + math.sin(ang) * ln, py + math.cos(ang) * ln * 0.5)],
                    0.016 + 0.01 * bushy, 0.004)

    def nose(self, y=-0.24, w=0.2, length=0.5, bridge=0.06, tip=1.0):
        a, skin = self.a, self.skin
        dark, light = gfx.shade(skin, 0.72), gfx.mix(skin, (255, 246, 236), 0.5)
        top = y + length

        def shade(l):
            a.taper(rgba(dark, 100), [(bridge * 0.6, top), (bridge * 1.1, (top + y) / 2), (w * 0.52, y + 0.05)], 0.07,
                    0.1, surf=l)                                          # shadow side of the bridge
            a.ell(rgba(dark, 130), 0.0, y - 0.1, w * 2.0, w * 0.45, l)      # under the nose
            a.ell(rgba(dark, 50), -w * 0.62, y - 0.01, w * 0.5, w * 0.5, l)
            a.ell(rgba(dark, 90), w * 0.66, y - 0.01, w * 0.5, w * 0.55, l)
        a.soft(shade, 0.05, self.clip)

        def hi(l):
            a.taper(rgba(light, 140), [(-bridge * 0.4, top - 0.05), (-bridge * 0.3, (top + y) / 2), (-0.02, y + 0.08)],
                    0.035, 0.06, surf=l)
            a.ell(rgba(light, int(170 * tip)), -0.02, y + 0.05, w * 0.6, w * 0.45, l)
        a.soft(hi, 0.035, self.clip)
        for sd in (-1, 1):
            a.ell(rgba((70, 34, 30), 200), sd * w * 0.36, y - 0.07, w * 0.36, w * 0.17, angle=-sd * 15)
            a.line(rgba(gfx.shade(skin, 0.58), 170), [(sd * w * 0.55, y + 0.06), (sd * w * 0.68, y - 0.02),
                                                     (sd * w * 0.5, y - 0.08)], 0.018)

    def mouth(self, y=-0.56, w=0.42, lip=(196, 110, 104), smile=0.0, open_=0.0, teeth=True, upper=0.06, lower=0.08,
              thin=1.0, frown=0.0):
        a, skin = self.a, self.skin
        cy = y - smile * 0.06 + frown * 0.05
        curve = smile * 0.1 - frown * 0.06
        corner_l, corner_r = (-w / 2, y + curve), (w / 2, y + curve)
        # philtrum and the shadow under the lower lip
        a.soft(lambda l: (a.ell(rgba(gfx.shade(skin, 0.75), 90), 0.0, y + upper + 0.08, 0.1, 0.14, l),
                          a.ell(rgba(gfx.shade(skin, 0.66), 150), 0.0, y - lower - 0.1, w * 0.7, 0.12, l)), 0.04,
               self.clip)
        if open_:
            hole = [corner_l, (-w * 0.22, cy + 0.01), (w * 0.22, cy + 0.01), corner_r, (w * 0.25, cy - open_),
                    (-w * 0.25, cy - open_)]
            a.fill((70, 20, 22), hole)
            if teeth:
                clip = a.mask(hole)
                lay = a.layer()
                a.ell((246, 242, 234), 0.0, cy - open_ * 0.05, w * 0.86, open_ * 1.1, lay)
                a.ell((206, 196, 186), 0.0, cy - open_ * 0.5, w * 0.7, open_ * 0.25, lay)
                lay.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                a.s.blit(lay, (0, 0))
            up = [corner_l, (-w * 0.25, cy + upper * thin + 0.02), (0.0, cy + upper * thin * 0.7 + 0.02),
                  (w * 0.25, cy + upper * thin + 0.02), corner_r, (w * 0.22, cy + 0.01), (-w * 0.22, cy + 0.01)]
            a.fill(gfx.shade(lip, 0.86), up)
            lo = [corner_l, (-w * 0.25, cy - open_), (w * 0.25, cy - open_), corner_r, (w * 0.3, cy - open_ - lower * thin),
                  (0.0, cy - open_ - lower * thin * 1.15), (-w * 0.3, cy - open_ - lower * thin)]
            a.fill(lip, lo)
        else:
            up = [corner_l, (-w * 0.28, cy + upper * thin), (0.0, cy + upper * thin * 0.75), (w * 0.28, cy + upper * thin),
                  corner_r, (0.0, cy - 0.005)]
            lo = [corner_l, (0.0, cy - 0.005), corner_r, (w * 0.3, cy - lower * thin), (0.0, cy - lower * thin * 1.2),
                  (-w * 0.3, cy - lower * thin)]
            a.fill(gfx.shade(lip, 0.82), up)
            a.fill(lip, lo)
            a.soft(lambda l: a.ell(rgba(gfx.mix(lip, (255, 255, 255), 0.5), 150), -0.03, cy - lower * thin * 0.55,
                                   w * 0.36, lower * thin * 0.5, l), 0.02, self.clip)
            a.taper((70, 30, 30), [corner_l, (-w * 0.2, cy - 0.005), (w * 0.2, cy - 0.005), corner_r], 0.02, 0.02)
        for c in (corner_l, corner_r):
            a.soft(lambda l, c=c: a.ell(rgba(gfx.shade(skin, 0.6), 150), c[0], c[1], 0.07, 0.07, l), 0.02, self.clip)

    def folds(self, depth=1.0, mouth_y=-0.56, w=0.42, marionette=0.0):
        """Nasolabial folds (nose to mouth corners) and optional lines down from the mouth."""
        a, skin = self.a, self.skin
        col = gfx.shade(skin, 0.62)
        for sd in (-1, 1):
            pts = [(sd * 0.2, -0.16), (sd * (w / 2 + 0.12), mouth_y + 0.14), (sd * (w / 2 + 0.1), mouth_y - 0.08)]
            a.soft(lambda l, pts=pts: a.taper(rgba(col, int(110 * depth)), pts, 0.07, 0.03, surf=l), 0.035, self.clip)
            a.taper(rgba(gfx.shade(skin, 0.58), int(110 * depth)), pts, 0.014, 0.008)
            if marionette:
                m = [(sd * (w / 2 + 0.02), mouth_y - 0.06), (sd * (w / 2 + 0.06), mouth_y - 0.3)]
                a.taper(rgba(gfx.shade(skin, 0.6), int(150 * marionette)), m, 0.018, 0.006)

    def lines(self, forehead=0, crows=0.0, frown=0.0, under=0.0):
        a, skin = self.a, self.skin
        col = rgba(gfx.shade(skin, 0.64), 110)
        for i in range(forehead):
            yy = 0.52 + i * 0.1
            a.taper(col, [(-0.4, yy - 0.01), (-0.1, yy + 0.02), (0.15, yy + 0.015), (0.42, yy - 0.02)], 0.012, 0.012)
        for sd in (-1, 1):
            for k in range(int(3 * crows)):
                ang = -0.4 + k * 0.4
                a.taper(col, [(sd * 0.56, 0.1 + k * 0.03), (sd * (0.7 + 0.03 * k), 0.1 + ang * 0.25)], 0.014, 0.004)
            if frown:
                a.taper(col, [(sd * 0.06, 0.32), (sd * 0.04, 0.22)], 0.016 * frown, 0.008)
            if under:
                a.taper(col, [(sd * 0.2, -0.02), (sd * 0.36, -0.1), (sd * 0.52, -0.06)], 0.012 * under, 0.006)

    def stubble(self, col=(60, 44, 36), amount=1.0, area=None):
        a = self.a
        region = area or [(-0.72, -0.3), (-0.4, -0.46), (0.0, -0.44), (0.4, -0.46), (0.72, -0.3), (0.62, -0.72),
                          (0.3, -0.98), (0.0, -1.03), (-0.3, -0.98), (-0.62, -0.72)]
        clip = a.mask(region)
        clip.blit(self.clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        a.soft(lambda l: a.fill(rgba(col, int(95 * amount)), region, surf=l), 0.08, clip)
        lay = a.layer()
        rng = self.rng
        for _ in range(int(260 * amount)):
            x, y = rng.uniform(-0.75, 0.75), rng.uniform(-1.05, -0.3)
            a.ell(rgba(col, rng.randint(40, 110)), x, y, 0.014, 0.014, lay)
        lay.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        a.s.blit(lay, (0, 0))

    # ---------------------------------------------------------------- hair
    def hair(self, outer, hairline, col, dark=None, light=None, strands=60, flow=None, length=(0.25, 0.6), width=0.03,
             shadow=1.0, seed=None, rim=True):
        """Hair mass between `outer` and `hairline`, then many thin locks following `flow(x, y) -> angle`."""
        a = self.a
        rng = random.Random(seed) if seed is not None else self.rng
        dark = dark or gfx.shade(col, 0.7)
        light = light or gfx.mix(col, (255, 255, 255), 0.35)
        pts = spline(outer, closed=False) + spline(hairline[::-1], closed=False)[1:]
        q = [a.P(*p) for p in pts]
        # shadow the hair casts on the forehead
        if shadow:
            sh = a.layer()
            pygame.draw.polygon(sh, rgba(gfx.shade(self.skin, 0.5), int(170 * shadow)),
                                [(x, y + 0.06 * a.R) for x, y in q])
            sh = blur(sh, 0.06 * a.R)
            sh.blit(self.clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            a.s.blit(sh, (0, 0))
        if rim:
            out = [a.P(*p) for p in spline(outer, closed=False)]
            pygame.draw.lines(a.s, gfx.shade(dark, 0.6), False, out, max(1, int(0.05 * a.R)))
        pygame.draw.polygon(a.s, dark, q)
        mass = a.layer()
        pygame.draw.polygon(mass, (255, 255, 255, 255), q)
        lay = a.layer()
        # broad soft sheen, then individual locks
        a.ell(rgba(col, 255), -0.1, 0.9, 1.9, 1.2, lay)
        a.ell(rgba(light, 140), LIGHT[0] * 0.6, 1.0, 0.8, 0.45, lay)
        lay = blur(lay, 0.12 * a.R)
        xs = [p[0] for p in outer + hairline]
        ys = [p[1] for p in outer + hairline]
        flow = flow or (lambda x, y: 0.0)
        for _ in range(strands):
            x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
            ln = rng.uniform(*length)
            ang = flow(x, y) + rng.uniform(-0.12, 0.12)
            bend = rng.uniform(-0.08, 0.08)
            pts2 = [(x, y), (x + math.sin(ang) * ln * 0.5 + bend, y - math.cos(ang) * ln * 0.5),
                    (x + math.sin(ang) * ln, y - math.cos(ang) * ln)]
            tone = rng.random()
            c = gfx.mix(dark, light, tone) if tone > 0.15 else gfx.shade(dark, 0.8)
            a.taper(rgba(c, rng.randint(150, 240)), pts2, width * rng.uniform(0.6, 1.4), 0.003, surf=lay)
        lay.blit(mass, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        a.s.blit(lay, (0, 0))

    def glasses(self, y, w, h, rim, gap=0.12, thick=0.035, rimless=False, round_=0.35, temple_y=0.05):
        a = self.a
        for sd in (-1, 1):
            cx = sd * (gap / 2 + w / 2)
            r = pygame.Rect(0, 0, w * a.R, h * a.R)
            r.center = a.P(cx, y)
            lens = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(lens, (225, 238, 248, 46), lens.get_rect(), border_radius=int(h * a.R * round_))
            pygame.draw.line(lens, (255, 255, 255, 120), (r.w * 0.15, r.h * 0.65), (r.w * 0.4, r.h * 0.15),
                             max(1, int(0.03 * a.R)))
            a.s.blit(lens, r)
            # the frame casts a faint shadow on the cheek
            a.soft(lambda l, r=r: pygame.draw.rect(l, rgba((40, 30, 30), 70), r.move(0.03 * a.R, 0.05 * a.R),
                                                   max(1, int(thick * a.R)), border_radius=int(h * a.R * round_)),
                   0.02, self.clip)
            pygame.draw.rect(a.s, rim, r, max(1, int((thick * 0.5 if rimless else thick) * a.R)),
                             border_radius=int(h * a.R * round_))
            if rimless:
                pygame.draw.line(a.s, rim, r.topleft, r.topright, max(1, int(thick * a.R)))
        a.line(rim, [(-gap / 2, y + h * 0.12), (0.0, y + h * 0.2), (gap / 2, y + h * 0.12)], thick * 0.9)
        for sd in (-1, 1):
            a.line(rim, [(sd * (gap / 2 + w), y + h * 0.3), (sd * 0.88, y + temple_y + 0.1)], thick * 0.9, smooth=False)


# ---------------------------------------------------------------- clothing
def suit(a, col, tie=None, shirt=(246, 246, 244), pin=None, collar_w=0.5):
    dark, light = gfx.shade(col, 0.7), gfx.mix(col, (255, 255, 255), 0.18)
    body = [(-1.9, -2.0), (-1.72, -1.6), (-1.0, -1.32), (1.0, -1.32), (1.72, -1.6), (1.9, -2.0)]
    a.fill(gfx.shade(col, 0.55), [(x * 1.03, y - 0.03) for x, y in body])
    a.fill(col, body)
    clip = a.mask(body)
    a.soft(lambda l: (a.ell(rgba(light, 120), -1.2, -1.45, 0.9, 0.5, l), a.ell(rgba(dark, 160), 1.3, -1.7, 1.0, 0.9, l)),
           0.15, clip)
    shirt_pts = [(-collar_w * 0.8, -1.22), (collar_w * 0.8, -1.22), (0.3, -2.0), (-0.3, -2.0)]
    a.fill(shirt, shirt_pts, smooth=False)
    a.soft(lambda l: a.ell(rgba((120, 120, 130), 120), 0.0, -1.3, 0.8, 0.2, l), 0.04, a.mask(shirt_pts))
    for sd in (-1, 1):
        lapel = [(sd * 0.44, -1.28), (sd * 0.28, -2.0), (sd * 0.62, -1.96), (sd * 0.8, -1.42)]
        a.fill(gfx.shade(col, 0.82 if sd < 0 else 0.68), lapel, smooth=False)
        a.line(gfx.shade(col, 0.5), [(sd * 0.28, -2.0), (sd * 0.44, -1.28)], 0.02, smooth=False)
        a.fill((236, 236, 234) if sd < 0 else (214, 214, 214),
               [(sd * 0.03, -1.27), (sd * collar_w * 0.82, -1.16), (sd * 0.32, -1.5)], smooth=False)
    if tie:
        knot = [(-0.11, -1.28), (0.11, -1.28), (0.08, -1.44), (-0.08, -1.44)]
        a.fill(gfx.shade(tie, 0.8), knot, smooth=False)
        blade = [(-0.08, -1.44), (0.08, -1.44), (0.17, -1.92), (0.0, -2.0), (-0.17, -1.92)]
        a.fill(tie, blade, smooth=False)
        a.soft(lambda l: a.ell(rgba(gfx.shade(tie, 0.6), 160), 0.12, -1.6, 0.16, 0.7, l), 0.04, a.mask(blade))
        a.line(gfx.mix(tie, (255, 255, 255), 0.25), [(-0.04, -1.54), (0.07, -1.7)], 0.025, smooth=False)
    if pin == "us":
        r = pygame.Rect(0, 0, 0.22 * a.R, 0.14 * a.R)
        r.center = a.P(-0.92, -1.66)
        pygame.draw.rect(a.s, (220, 40, 50), r)
        for i in range(1, 4, 2):
            pygame.draw.rect(a.s, (250, 250, 250), (r.x, r.y + r.h * i / 5, r.w, r.h / 5))
        pygame.draw.rect(a.s, (40, 60, 150), (r.x, r.y, r.w * 0.45, r.h * 0.55))
    elif pin == "ch":
        r = pygame.Rect(0, 0, 0.2 * a.R, 0.2 * a.R)
        r.center = a.P(-0.94, -1.66)
        pygame.draw.rect(a.s, (220, 30, 40), r, border_radius=int(0.02 * a.R))
        cx, cy = r.center
        pygame.draw.rect(a.s, (255, 255, 255), (cx - 0.022 * a.R, cy - 0.065 * a.R, 0.044 * a.R, 0.13 * a.R))
        pygame.draw.rect(a.s, (255, 255, 255), (cx - 0.065 * a.R, cy - 0.022 * a.R, 0.13 * a.R, 0.044 * a.R))


def top(a, col, neckline=0.5, deep=0.0):
    """A plain top (t-shirt, polo, sweater) with soft folds."""
    body = [(-1.75, -2.0), (-1.58, -1.58), (-0.86, -1.32), (0.86, -1.32), (1.58, -1.58), (1.75, -2.0)]
    a.fill(gfx.shade(col, 0.6), [(x * 1.03, y - 0.03) for x, y in body])
    a.fill(col, body)
    clip = a.mask(body)
    a.soft(lambda l: (a.ell(rgba(gfx.mix(col, (255, 255, 255), 0.3), 130), -1.1, -1.5, 0.9, 0.5, l),
                      a.ell(rgba(gfx.shade(col, 0.7), 150), 1.2, -1.75, 1.0, 0.9, l)), 0.15, clip)
    return clip


# ------------------------------------------------------------- the drivers
def trump(a):
    skin = (236, 160, 112)
    pale = (246, 210, 172)
    f = Face(a, skin, face_outline(top=1.05, temple=0.8, cheek=0.86, jaw=0.76, chin=0.38, chin_y=-1.14, jaw_y=-0.72), 7)
    f.neck(0.44)
    suit(a, (28, 40, 80), (40, 90, 182), pin="us", collar_w=0.54)
    f.ears(size=1.08, y=0.02)
    f.base(flush=0.55)
    # jowls and a soft double chin
    a.soft(lambda l: (a.ell(rgba(gfx.shade(skin, 0.72), 90), 0.0, -1.1, 0.8, 0.2, l),
                      a.ell(rgba(gfx.shade(skin, 0.76), 50), -0.6, -0.72, 0.3, 0.36, l),
                      a.ell(rgba(gfx.shade(skin, 0.74), 60), 0.62, -0.72, 0.3, 0.36, l)), 0.1, f.clip)
    # the pale skin around the eyes (tanning goggles)
    a.soft(lambda l: [a.ell(rgba(pale, 200), sd * 0.31, 0.12, 0.44, 0.28, l) for sd in (-1, 1)], 0.07, f.clip)
    f.lines(forehead=3, crows=0.6, frown=1.0, under=0.5)
    for sd in (-1, 1):
        f.eye(sd * 0.3, 0.12, (120, 162, 196), w=0.26, h=0.125, lid=0.24, look=-0.01, bags=0.7, socket=0.4, squint=0.1)
        f.brow(sd * 0.31, 0.3, 0.3, (220, 180, 128), angle=-0.1, thick=0.055, arch=0.03, hairs=24)
    f.nose(y=-0.24, w=0.23, length=0.48, bridge=0.07)
    f.folds(depth=0.9, mouth_y=-0.6, w=0.36, marionette=0.8)
    f.mouth(y=-0.6, w=0.36, lip=(206, 120, 104), upper=0.045, lower=0.07, frown=0.5)
    # the famous hair: pale blond, swept back over the sides, a high wave combed across the forehead
    hair, dark, light = (238, 222, 178), (204, 180, 128), (255, 250, 232)
    f.hair([(-0.86, 0.12), (-0.98, 0.62), (-0.86, 1.08), (-0.4, 1.38), (0.2, 1.46), (0.78, 1.34), (1.06, 1.0),
            (1.06, 0.56), (0.92, 0.12)],
           [(-0.86, 0.12), (-0.8, 0.5), (-0.56, 0.74), (-0.1, 0.82), (0.4, 0.8), (0.76, 0.66), (0.88, 0.42),
            (0.92, 0.12)],
           hair, dark, light, strands=260, length=(0.3, 0.75), width=0.022,
           flow=lambda x, y: 1.75 if y > 0.8 else (1.45 if x > -0.4 else 2.5), seed=3)
    wave = [(-0.62, 0.8), (-0.3, 0.98), (0.25, 1.02), (0.72, 0.9), (0.94, 0.66), (0.62, 0.74), (0.05, 0.82),
            (-0.4, 0.78)]
    a.soft(lambda l: a.fill(rgba(gfx.shade(skin, 0.55), 110), [(x, y - 0.06) for x, y in wave], surf=l), 0.05, f.clip)
    a.fill(dark, wave)
    lay = a.layer()
    a.soft(lambda l: a.fill(rgba(hair, 255), wave, surf=l), 0.03)
    for i in range(70):
        t = i / 70
        x0 = -0.62 + 1.4 * t
        tone = (i * 37 % 10) / 10
        a.taper(rgba(gfx.mix(hair, light if tone > 0.4 else dark, abs(tone - 0.4)), 220),
                [(x0 - 0.12, 0.96 - 0.12 * t), (x0 + 0.12, 0.86 - 0.06 * t), (x0 + 0.3, 0.76 - 0.06 * t)], 0.026,
                0.003, surf=lay)
    lay.blit(a.mask(wave), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    a.s.blit(lay, (0, 0))


def putin(a):
    skin = (236, 192, 168)
    f = Face(a, skin, face_outline(top=1.12, temple=0.8, cheek=0.84, jaw=0.66, chin=0.3, chin_y=-1.1, cheek_y=-0.05,
                                   jaw_y=-0.7), 11)
    f.neck(0.4)
    suit(a, (26, 26, 30), (122, 26, 40), collar_w=0.5)
    f.ears(size=1.1, y=0.04)
    f.base(flush=0.35)
    # thin, short light-brown hair: receding at the temples, thin on top
    a.soft(lambda l: a.fill(rgba((150, 128, 104), 150), [(-0.86, 0.3), (-0.8, 0.78), (-0.5, 1.02), (0.0, 1.1),
                                                          (0.5, 1.02), (0.8, 0.78), (0.86, 0.3), (0.72, 0.62),
                                                          (0.4, 0.84), (0.1, 0.7), (-0.2, 0.84), (-0.6, 0.66)], surf=l),
           0.05, f.clip)
    lay = a.layer()
    rng = random.Random(4)
    for _ in range(260):
        x = rng.uniform(-0.86, 0.86)
        y = rng.uniform(0.62, 1.1) if abs(x) < 0.7 else rng.uniform(0.2, 0.9)
        if abs(x) < 0.35 and y < 0.86:
            continue
        a.taper(rgba(gfx.mix((128, 104, 82), (196, 176, 150), rng.random()), rng.randint(110, 220)),
                [(x, y), (x + 0.04 * (1 if x > 0 else -1), y + 0.07)], 0.014, 0.003, surf=lay)
    lay.blit(f.clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    a.s.blit(lay, (0, 0))
    f.lines(forehead=2, crows=0.5, under=0.8)
    for sd in (-1, 1):
        f.eye(sd * 0.3, 0.1, (126, 150, 168), w=0.26, h=0.12, lid=0.34, look=0.0, bags=0.6, socket=1.0, squint=0.1)
        f.brow(sd * 0.31, 0.27, 0.3, (168, 140, 112), angle=-0.06, thick=0.045, arch=0.03, hairs=18)
    f.nose(y=-0.24, w=0.2, length=0.5, bridge=0.06)
    f.folds(depth=0.7, mouth_y=-0.6, w=0.34, marionette=0.3)
    f.mouth(y=-0.6, w=0.34, lip=(196, 128, 120), upper=0.035, lower=0.05, frown=0.25, thin=0.8)


def roesti(a):
    skin = (238, 190, 164)
    f = Face(a, skin, face_outline(top=1.02, temple=0.82, cheek=0.86, jaw=0.7, chin=0.32, chin_y=-1.1, jaw_y=-0.7), 21)
    f.neck(0.42)
    suit(a, (32, 34, 40), (120, 122, 128), collar_w=0.52)
    f.ears(size=1.0, y=0.04)
    f.base(flush=0.8)
    f.lines(forehead=1, crows=0.6)
    for sd in (-1, 1):
        f.eye(sd * 0.3, 0.12, (110, 92, 70), w=0.26, h=0.13, lid=0.18, look=0.0, bags=0.3, socket=0.6, squint=0.15)
        f.brow(sd * 0.31, 0.3, 0.32, (110, 80, 56), angle=0.02, thick=0.06, arch=0.04, hairs=26)
    f.nose(y=-0.22, w=0.21, length=0.46, bridge=0.06)
    f.folds(depth=0.6, mouth_y=-0.56, w=0.4)
    f.mouth(y=-0.56, w=0.4, lip=(200, 120, 112), smile=0.6, upper=0.035, lower=0.06)
    f.glasses(0.12, 0.33, 0.21, (150, 150, 154), gap=0.1, thick=0.02, rimless=True, round_=0.25)
    # brown hair swept over to the right, full and a bit untidy
    hair, dark, light = (122, 86, 54), (78, 52, 32), (178, 136, 92)
    f.hair([(-0.88, 0.2), (-0.98, 0.7), (-0.74, 1.12), (-0.2, 1.32), (0.4, 1.3), (0.88, 1.06), (1.0, 0.62),
            (0.92, 0.2)],
           [(-0.88, 0.2), (-0.8, 0.56), (-0.5, 0.74), (-0.1, 0.8), (0.3, 0.74), (0.62, 0.64), (0.84, 0.46),
            (0.92, 0.2)],
           hair, dark, light, strands=240, length=(0.25, 0.6), width=0.026,
           flow=lambda x, y: 1.6 + 0.4 * (y - 1.0), seed=5)
    tuft = [(-0.5, 0.74), (-0.3, 0.9), (0.1, 0.92), (0.5, 0.78), (0.3, 0.66), (0.0, 0.68), (-0.28, 0.66)]
    a.fill(hair, tuft)
    for i in range(18):
        x0 = -0.45 + i * 0.05
        a.taper(rgba(gfx.mix(dark, light, (i * 7 % 10) / 10), 230), [(x0, 0.88), (x0 + 0.12, 0.76), (x0 + 0.16, 0.64)],
                0.024, 0.004)


def blocher(a):
    skin = (234, 178, 156)
    f = Face(a, skin, face_outline(top=1.02, temple=0.82, cheek=0.9, jaw=0.8, chin=0.4, chin_y=-1.1, jaw_y=-0.66), 31)
    f.neck(0.46)
    suit(a, (98, 102, 110), (72, 92, 120), collar_w=0.54)
    f.ears(size=1.12, y=0.02)
    f.base(flush=0.8)
    a.soft(lambda l: (a.ell(rgba(gfx.shade(skin, 0.74), 70), 0.0, -1.06, 0.9, 0.24, l),
                      a.ell(rgba(gfx.shade(skin, 0.74), 60), -0.66, -0.7, 0.3, 0.4, l),
                      a.ell(rgba(gfx.shade(skin, 0.72), 70), 0.68, -0.7, 0.3, 0.4, l)), 0.1, f.clip)
    f.lines(forehead=3, crows=1.0, under=0.8)
    for sd in (-1, 1):
        f.eye(sd * 0.31, 0.12, (96, 104, 112), w=0.25, h=0.11, lid=0.2, bags=0.9, socket=0.6, squint=0.35)
        f.brow(sd * 0.32, 0.3, 0.32, (200, 196, 190), angle=0.05, thick=0.05, arch=0.04, hairs=24, bushy=0.4)
    f.nose(y=-0.22, w=0.25, length=0.46, bridge=0.07)
    f.folds(depth=1.0, mouth_y=-0.56, w=0.46, marionette=0.6)
    f.mouth(y=-0.56, w=0.44, lip=(196, 112, 106), smile=0.8, open_=0.07, upper=0.03, lower=0.05)
    f.glasses(0.12, 0.34, 0.2, (176, 176, 182), gap=0.1, thick=0.022, round_=0.4)
    # short white hair with a side parting, receding at the temples
    hair, dark, light = (226, 226, 222), (170, 170, 168), (252, 252, 250)
    f.hair([(-0.9, 0.2), (-0.98, 0.66), (-0.72, 1.1), (-0.15, 1.28), (0.45, 1.24), (0.9, 0.98), (0.98, 0.56),
            (0.9, 0.2)],
           [(-0.9, 0.2), (-0.8, 0.6), (-0.58, 0.86), (-0.3, 0.86), (0.0, 0.92), (0.4, 0.88), (0.7, 0.74),
            (0.9, 0.2)],
           hair, dark, light, strands=200, length=(0.2, 0.45), width=0.022,
           flow=lambda x, y: 1.4 if x > -0.35 else -1.4, seed=8)


def maurer(a):
    skin = (226, 172, 140)
    f = Face(a, skin, face_outline(top=1.22, temple=0.76, cheek=0.8, jaw=0.64, chin=0.3, chin_y=-1.18, cheek_y=-0.05,
                                   jaw_y=-0.76), 41)
    f.neck(0.38)
    suit(a, (30, 30, 34), (130, 28, 40), pin="ch", collar_w=0.5)
    f.ears(size=1.22, y=0.04, x=0.82)
    f.base(flush=0.4)
    # a shiny bald dome, short grey hair only around the sides and the back
    a.soft(lambda l: a.ell(rgba((255, 238, 220), 150), -0.2, 0.96, 0.6, 0.3, l), 0.06, f.clip)
    for sd in (-1, 1):
        side = [(sd * 0.8, -0.05), (sd * 0.88, 0.3), (sd * 0.86, 0.6), (sd * 0.74, 0.8), (sd * 0.7, 0.56),
                (sd * 0.74, 0.3), (sd * 0.72, 0.0)]
        a.fill(rgba((150, 146, 140), 200), side)
        lay = a.layer()
        rng = random.Random(9 + sd)
        for _ in range(60):
            y = rng.uniform(0.0, 0.76)
            x = sd * rng.uniform(0.72, 0.88)
            a.taper(rgba(gfx.mix((120, 116, 110), (230, 228, 224), rng.random()), 220), [(x, y), (x + sd * 0.03, y + 0.06)],
                    0.016, 0.003, surf=lay)
        lay.blit(a.mask(side), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        a.s.blit(lay, (0, 0))
    f.lines(forehead=3, crows=0.8, under=0.6)
    for sd in (-1, 1):
        f.eye(sd * 0.29, 0.1, (96, 72, 54), w=0.24, h=0.11, lid=0.3, bags=0.6, socket=0.9, squint=0.2)
        f.brow(sd * 0.3, 0.28, 0.3, (130, 118, 104), angle=-0.15, thick=0.06, arch=0.03, hairs=28, bushy=0.6)
    f.nose(y=-0.26, w=0.21, length=0.56, bridge=0.06)
    f.folds(depth=1.2, mouth_y=-0.64, w=0.4, marionette=0.8)
    f.mouth(y=-0.64, w=0.4, lip=(186, 116, 104), smile=0.5, upper=0.025, lower=0.04, thin=0.7)


def greta(a):
    skin = (246, 218, 202)
    f = Face(a, skin, face_outline(top=1.0, temple=0.78, cheek=0.8, jaw=0.6, chin=0.26, chin_y=-1.06, jaw_y=-0.7), 51)
    f.neck(0.32)
    top(a, (236, 160, 186), neckline=0.5)
    hair, dark, light = (104, 72, 50), (66, 44, 30), (158, 118, 84)
    # the hair behind the head, then the face
    a.fill(dark, [(-0.86, -0.2), (-0.96, 0.6), (-0.6, 1.14), (0.0, 1.26), (0.6, 1.14), (0.96, 0.6), (0.86, -0.2)])
    f.ears(size=0.9, y=0.04, x=0.78)
    f.base(flush=0.35, form=0.8)
    for sd in (-1, 1):
        f.eye(sd * 0.29, 0.1, (110, 136, 156), w=0.28, h=0.14, lid=0.1, look=-0.04, socket=0.5, lashes=0.4)
        f.brow(sd * 0.3, 0.3, 0.3, (126, 96, 70), angle=0.0, thick=0.05, arch=0.02, hairs=22)
    f.nose(y=-0.24, w=0.17, length=0.44, bridge=0.05)
    f.mouth(y=-0.56, w=0.32, lip=(214, 140, 140), upper=0.04, lower=0.06)
    # centre parting, pulled back tight
    f.hair([(-0.84, 0.3), (-0.92, 0.7), (-0.62, 1.1), (0.0, 1.22), (0.62, 1.1), (0.92, 0.7), (0.84, 0.3)],
           [(-0.84, 0.3), (-0.74, 0.62), (-0.4, 0.84), (0.0, 0.9), (0.4, 0.84), (0.74, 0.62), (0.84, 0.3)],
           hair, dark, light, strands=200, length=(0.3, 0.6), width=0.02,
           flow=lambda x, y: (2.2 if x < 0 else -2.2), seed=12)
    a.line(gfx.shade(dark, 0.8), [(0.0, 1.2), (0.0, 0.92)], 0.02, smooth=False)
    # the long braid over her shoulder
    for i in range(9):
        y = 0.1 - i * 0.24
        x = 0.82 + 0.04 * math.sin(i * 0.8)
        for sd in (-1, 1):
            lock = [(x - 0.12, y + 0.1), (x + sd * 0.02, y + 0.14), (x + 0.13, y + 0.02), (x + sd * 0.02, y - 0.12),
                    (x - 0.1, y - 0.06)]
            a.fill(gfx.shade(hair, 0.7), [(px + 0.01, py - 0.015) for px, py in lock])
            a.fill(gfx.mix(hair, light, 0.4 if sd > 0 else 0.1), lock)
    a.ell((236, 200, 70), 0.86, -2.0, 0.12, 0.1)


def mozart(a):
    skin = (246, 220, 204)
    f = Face(a, skin, face_outline(top=1.02, temple=0.78, cheek=0.82, jaw=0.64, chin=0.3, chin_y=-1.06), 61)
    f.neck(0.34)
    # red court coat with gold trim and a lace jabot
    coat = [(-1.85, -2.0), (-1.66, -1.56), (-0.9, -1.3), (0.9, -1.3), (1.66, -1.56), (1.85, -2.0)]
    clip = top(a, (172, 30, 42))
    for sd in (-1, 1):
        a.line((222, 182, 76), [(sd * 0.42, -1.3), (sd * 0.36, -2.0)], 0.06, smooth=False)
    for i in range(5):
        y = -1.28 - i * 0.15
        a.ell((250, 248, 244), 0.0, y, 0.5 - i * 0.04, 0.2, outline=None) if False else None
        a.ell(gfx.shade((250, 248, 244), 0.8), 0.0, y - 0.02, 0.52 - i * 0.04, 0.2)
        a.ell((250, 248, 244), 0.0, y, 0.48 - i * 0.04, 0.17)
    # the powdered wig behind the head
    wig, wig_dk, wig_hi = (236, 234, 230), (184, 182, 180), (255, 255, 255)
    a.fill(wig_dk, [(-0.86, -0.1), (-0.94, 0.6), (-0.64, 1.12), (0.0, 1.24), (0.64, 1.12), (0.94, 0.6), (0.86, -0.1)])
    f.ears(size=0.9, y=0.0, x=0.78)
    f.base(flush=0.7, form=0.8)
    for sd in (-1, 1):
        f.eye(sd * 0.29, 0.1, (118, 134, 150), w=0.29, h=0.15, lid=0.22, look=0.02, socket=0.5, bags=0.3)
        f.brow(sd * 0.3, 0.32, 0.3, (170, 150, 126), angle=0.05, thick=0.045, arch=0.05, hairs=20)
    f.nose(y=-0.26, w=0.21, length=0.54, bridge=0.07)
    f.mouth(y=-0.58, w=0.32, lip=(206, 120, 120), smile=0.3, upper=0.04, lower=0.06)
    f.hair([(-0.86, 0.3), (-0.92, 0.74), (-0.6, 1.12), (0.0, 1.26), (0.6, 1.12), (0.92, 0.74), (0.86, 0.3)],
           [(-0.86, 0.3), (-0.72, 0.66), (-0.38, 0.86), (0.0, 0.92), (0.38, 0.86), (0.72, 0.66), (0.86, 0.3)],
           wig, wig_dk, wig_hi, strands=200, length=(0.3, 0.6), width=0.024,
           flow=lambda x, y: (2.3 if x < 0 else -2.3), seed=14)
    # the rolled curls over the ears
    for sd in (-1, 1):
        for k, y in enumerate((0.24, 0.0)):
            cx = sd * 0.92
            a.soft(lambda l, cx=cx, y=y: a.ell(rgba((0, 0, 0), 90), cx + 0.02, y - 0.05, 0.42, 0.22, l), 0.03)
            a.ell(wig_dk, cx, y, 0.42, 0.22)
            a.ell(wig, cx, y + 0.01, 0.38, 0.18)
            a.ell(wig_hi, cx - 0.05, y + 0.04, 0.18, 0.07)
            a.ell(gfx.shade(wig_dk, 0.85), cx + sd * 0.14, y, 0.08, 0.1)


def einstein(a):
    skin = (232, 192, 170)
    f = Face(a, skin, face_outline(top=1.02, temple=0.8, cheek=0.86, jaw=0.7, chin=0.32, chin_y=-1.08), 71)
    f.neck(0.38)
    top(a, (110, 112, 118))
    a.fill((90, 92, 98), [(-0.5, -1.3), (0.5, -1.3), (0.0, -1.7)])
    hair, dark, light = (226, 226, 228), (164, 164, 170), (255, 255, 255)
    # the wild hair behind the head
    # a soft cloud first, then wavy tufts sticking out every which way
    cloud = [(-0.9, -0.3), (-1.28, 0.2), (-1.3, 0.8), (-0.9, 1.34), (0.0, 1.56), (0.9, 1.34), (1.3, 0.8), (1.28, 0.2),
             (0.9, -0.3)]
    a.soft(lambda l: a.fill(rgba(dark, 255), cloud, surf=l), 0.08)
    lay = a.layer()
    rng = random.Random(17)
    for _ in range(420):
        ang = rng.uniform(-2.4, 2.4)
        r0 = rng.uniform(0.55, 1.0)
        r1 = r0 + rng.uniform(0.18, 0.5)
        x0, y0 = math.sin(ang) * r0 * 1.15, 0.3 + math.cos(ang) * r0
        x1, y1 = math.sin(ang) * r1 * 1.18, 0.3 + math.cos(ang) * r1
        nx, ny = math.cos(ang) * 0.08, -math.sin(ang) * 0.08
        w1 = rng.uniform(-1, 1)
        a.taper(rgba(gfx.mix(dark, light, rng.random()), rng.randint(190, 250)),
                [(x0, y0), (x0 * 0.66 + x1 * 0.34 + nx * w1, y0 * 0.66 + y1 * 0.34 + ny * w1),
                 (x0 * 0.33 + x1 * 0.67 - nx * w1, y0 * 0.33 + y1 * 0.67 - ny * w1), (x1, y1)], 0.05, 0.006,
                surf=lay)
    a.s.blit(lay, (0, 0))
    f.ears(size=1.1, y=0.0)
    f.base(flush=0.5)
    f.lines(forehead=4, crows=1.0, frown=1.0, under=1.0)
    for sd in (-1, 1):
        f.eye(sd * 0.3, 0.1, (96, 70, 52), w=0.26, h=0.13, lid=0.3, look=0.0, bags=1.0, socket=0.9, squint=0.1)
        f.brow(sd * 0.31, 0.3, 0.32, (190, 186, 180), angle=-0.2, thick=0.07, arch=0.06, hairs=40, bushy=1.0)
    f.nose(y=-0.24, w=0.24, length=0.52, bridge=0.07)
    f.folds(depth=1.0, mouth_y=-0.66, w=0.4, marionette=0.6)
    # tongue out
    a.fill((90, 24, 28), [(-0.17, -0.62), (0.17, -0.62), (0.14, -0.72), (-0.14, -0.72)])
    tongue = [(-0.13, -0.66), (0.13, -0.66), (0.15, -0.86), (0.0, -0.98), (-0.15, -0.86)]
    a.fill((206, 86, 96), tongue)
    a.soft(lambda l: a.ell(rgba((255, 200, 200), 160), -0.04, -0.82, 0.1, 0.1, l), 0.02, a.mask(tongue))
    a.line((150, 50, 60), [(0.0, -0.7), (0.0, -0.86)], 0.015)
    # the bushy moustache
    mo = [(-0.38, -0.5), (-0.2, -0.34), (0.0, -0.36), (0.2, -0.34), (0.38, -0.5), (0.24, -0.6), (0.0, -0.58),
          (-0.24, -0.6)]
    a.fill(dark, mo)
    lay = a.layer()
    for i in range(70):
        x = -0.36 + 0.72 * (i / 70)
        a.taper(rgba(gfx.mix(dark, light, (i * 13 % 10) / 10), 230), [(x * 0.9, -0.38), (x * 1.02, -0.5),
                (x * 1.06, -0.6)], 0.024, 0.004, surf=lay)
    lay.blit(a.mask(mo), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    a.s.blit(lay, (0, 0))
    # front hair over the top of the head
    f.hair([(-0.86, 0.4), (-0.98, 0.84), (-0.6, 1.24), (0.0, 1.36), (0.6, 1.24), (0.98, 0.84), (0.86, 0.4)],
           [(-0.86, 0.4), (-0.7, 0.7), (-0.36, 0.84), (0.0, 0.88), (0.36, 0.84), (0.7, 0.7), (0.86, 0.4)],
           hair, dark, light, strands=200, length=(0.25, 0.55), width=0.026,
           flow=lambda x, y: math.atan2(x, 1.0) * 1.4 + 3.14, seed=18)


def federer(a):
    skin = (226, 174, 136)
    f = Face(a, skin, face_outline(top=1.04, temple=0.8, cheek=0.84, jaw=0.72, chin=0.34, chin_y=-1.12, jaw_y=-0.74), 81)
    f.neck(0.4)
    clip = top(a, (248, 248, 246))
    for sd in (-1, 1):
        a.fill((232, 232, 230), [(sd * 0.06, -1.3), (sd * 0.62, -1.2), (sd * 0.5, -1.56)], smooth=False)
        a.line((200, 200, 200), [(sd * 0.06, -1.3), (sd * 0.5, -1.56)], 0.02, smooth=False)
    hair, dark, light = (96, 66, 44), (58, 38, 26), (150, 110, 74)
    a.fill(dark, [(-0.84, -0.3), (-0.98, 0.5), (-0.7, 1.12), (0.0, 1.26), (0.7, 1.12), (0.98, 0.5), (0.84, -0.3)])
    f.ears(size=1.0, y=0.02, x=0.8)
    f.base(flush=0.4)
    f.lines(forehead=1, crows=0.8)
    for sd in (-1, 1):
        f.eye(sd * 0.3, 0.1, (98, 74, 52), w=0.27, h=0.13, lid=0.16, look=0.0, bags=0.3, socket=0.8, squint=0.3)
        f.brow(sd * 0.31, 0.29, 0.32, (84, 58, 40), angle=0.06, thick=0.06, arch=0.05, hairs=28)
    f.nose(y=-0.24, w=0.21, length=0.52, bridge=0.07)
    f.folds(depth=0.8, mouth_y=-0.6, w=0.46)
    f.stubble((70, 50, 38), 0.9)
    f.mouth(y=-0.6, w=0.46, lip=(186, 110, 98), smile=1.0, open_=0.1, upper=0.03, lower=0.05)
    f.hair([(-0.86, 0.2), (-0.98, 0.7), (-0.66, 1.14), (0.0, 1.28), (0.66, 1.14), (0.98, 0.7), (0.86, 0.2)],
           [(-0.86, 0.2), (-0.78, 0.6), (-0.4, 0.8), (0.0, 0.84), (0.4, 0.8), (0.78, 0.6), (0.86, 0.2)],
           hair, dark, light, strands=200, length=(0.3, 0.6), width=0.026,
           flow=lambda x, y: (2.6 if x < 0 else -2.6), seed=20)
    # wavy locks over the ears, then the white headband
    for sd in (-1, 1):
        for i in range(14):
            y0 = 0.5 - i * 0.05
            a.taper(gfx.mix(dark, light, (i * 3 % 7) / 7), [(sd * 0.82, y0 + 0.1), (sd * 0.94, y0 - 0.15),
                    (sd * (0.86 + 0.04 * (i % 3)), y0 - 0.4)], 0.04, 0.006)
    band = [(-0.92, 0.66), (-0.5, 0.86), (0.0, 0.92), (0.5, 0.86), (0.92, 0.66), (0.9, 0.5), (0.5, 0.7), (0.0, 0.76),
            (-0.5, 0.7), (-0.9, 0.5)]
    a.fill((200, 200, 204), [(x, y - 0.02) for x, y in band])
    a.fill((250, 250, 250), band)
    a.soft(lambda l: a.ell(rgba((170, 170, 180), 150), 0.5, 0.72, 0.8, 0.14, l), 0.03, a.mask(band))


def bonnie(a):
    skin = (232, 182, 148)
    f = Face(a, skin, face_outline(top=1.0, temple=0.78, cheek=0.82, jaw=0.62, chin=0.28, chin_y=-1.06, jaw_y=-0.7), 91)
    hair, dark, light = (238, 222, 176), (176, 146, 98), (255, 248, 226)
    # long straight platinum hair behind the shoulders
    back = [(-0.9, 0.6), (-1.06, -0.2), (-1.12, -1.4), (-0.7, -1.9), (0.7, -1.9), (1.12, -1.4), (1.06, -0.2), (0.9, 0.6)]
    a.fill(dark, back)
    f.neck(0.32)
    top(a, (236, 120, 170))
    lay = a.layer()
    rng = random.Random(23)
    for _ in range(220):
        sd = rng.choice((-1, 1))
        x = sd * rng.uniform(0.72, 1.08)
        a.taper(rgba(gfx.mix(dark, light, rng.random()), 220), [(x, 0.5), (x * 1.04, -0.6), (x * 0.98, -1.85)], 0.03,
                0.006, surf=lay)
    lay.blit(a.mask(back), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    a.s.blit(lay, (0, 0))
    f.base(flush=0.5, form=0.9)
    # make-up: contour, blush
    a.soft(lambda l: [a.ell(rgba((214, 120, 120), 70), sd * 0.52, -0.22, 0.36, 0.22, l) for sd in (-1, 1)], 0.08,
           f.clip)
    for sd in (-1, 1):
        f.eye(sd * 0.29, 0.1, (100, 76, 56), w=0.3, h=0.15, lid=0.08, look=0.0, socket=0.6, lashes=1.0, liner=1.6)
        f.brow(sd * 0.3, 0.3, 0.3, (110, 80, 56), angle=-0.12, thick=0.06, arch=0.06, hairs=26)
    f.nose(y=-0.24, w=0.17, length=0.44, bridge=0.05)
    f.mouth(y=-0.58, w=0.36, lip=(222, 110, 136), smile=0.4, upper=0.07, lower=0.09)
    f.hair([(-0.86, -0.1), (-0.96, 0.62), (-0.62, 1.12), (0.0, 1.24), (0.62, 1.12), (0.96, 0.62), (0.86, -0.1)],
           [(-0.86, -0.1), (-0.8, 0.4), (-0.5, 0.78), (-0.06, 0.92), (0.06, 0.92), (0.5, 0.78), (0.8, 0.4),
            (0.86, -0.1)],
           hair, dark, light, strands=260, length=(0.4, 0.9), width=0.024,
           flow=lambda x, y: (2.7 if x < 0 else -2.7), seed=24)
    for sd in (-1, 1):
        lock = [(sd * 0.7, 0.5), (sd * 0.92, 0.3), (sd * 0.98, -0.8), (sd * 0.86, -1.5), (sd * 0.74, -0.7),
                (sd * 0.72, 0.0)]
        a.fill(hair, lock)
        for i in range(10):
            x = sd * (0.74 + i * 0.022)
            a.taper(gfx.mix(dark, light, (i * 3 % 7) / 7), [(x, 0.4), (x * 1.04, -0.4), (x * 1.02, -1.3)], 0.03, 0.006)


PORTRAITS = {"trump": trump, "putin": putin, "roesti": roesti, "blocher": blocher, "maurer": maurer,
             "greta": greta, "mozart": mozart, "einstein": einstein, "federer": federer, "bonnie": bonnie}
