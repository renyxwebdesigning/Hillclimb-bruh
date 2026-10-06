"""Procedurally drawn game art. Everything is supersampled for clean edges.

Vehicle parts are drawn in local metres at a given pixels-per-metre so the
sprite lines up exactly with the physics body.
"""
import math

import pygame

import gfx
from gfx import supersample

OUTLINE = (40, 22, 22)
STEEL = (66, 70, 78)
STEEL_HI = (138, 144, 154)
RED = (218, 42, 44)
RED_DK = (156, 24, 30)
RED_HI = (246, 104, 96)
TYRE = (34, 34, 38)

CAR_EXTENT = 2.3   # half-size (m) of the square car sprite, enough for any rotation


def _mapper(surf, ppm, k):
    c = surf.get_width() / 2
    sc = ppm * k

    def P(x, y):
        return (c + x * sc, c - y * sc)
    return P, sc


def _tube(surf, P, sc, pts, width, color, hi=None):
    w = max(1, int(width * sc))
    for a, b in zip(pts, pts[1:]):
        pygame.draw.line(surf, color, P(*a), P(*b), w)
    for p in pts:
        pygame.draw.circle(surf, color, P(*p), w / 2)
    if hi:
        hw = max(1, int(width * sc * 0.35))
        for a, b in zip(pts, pts[1:]):
            pa, pb = P(*a), P(*b)
            pygame.draw.line(surf, hi, (pa[0] - hw * 0.6, pa[1] - hw * 0.6), (pb[0] - hw * 0.6, pb[1] - hw * 0.6), hw)


def ring_arc(surf, color, centre, r_out, r_in, a0, a1, steps=40):
    """Filled annular arc (pygame's thick arcs leave pinholes). Angles in radians, CCW, y up."""
    cx, cy = centre
    outer = [(cx + math.cos(a0 + (a1 - a0) * i / steps) * r_out, cy - math.sin(a0 + (a1 - a0) * i / steps) * r_out)
             for i in range(steps + 1)]
    inner = [(cx + math.cos(a1 - (a1 - a0) * i / steps) * r_in, cy - math.sin(a1 - (a1 - a0) * i / steps) * r_in)
             for i in range(steps + 1)]
    pygame.draw.polygon(surf, color, outer + inner)


def _poly(surf, P, sc, pts, fill, outline=OUTLINE, ow=0.028):
    q = [P(*p) for p in pts]
    pygame.draw.polygon(surf, fill, q)
    if outline:
        pygame.draw.polygon(surf, outline, q, max(1, int(ow * sc)))


def car_body(ppm):
    size = 2 * CAR_EXTENT * ppm

    def draw(surf, k):
        P, sc = _mapper(surf, ppm, k)
        ow = max(1, int(0.028 * sc))

        # Antenna with pennant (behind everything).
        pygame.draw.line(surf, (40, 40, 44), P(-1.38, 0.34), P(-1.62, 1.58), max(1, int(0.022 * sc)))
        _poly(surf, P, sc, [(-1.62, 1.58), (-1.26, 1.5), (-1.59, 1.4)], (255, 160, 30), (150, 80, 10), 0.018)

        # Spare wheel on the tail.
        pygame.draw.circle(surf, TYRE, P(-1.6, 0.2), 0.25 * sc)
        pygame.draw.circle(surf, (90, 92, 98), P(-1.6, 0.2), 0.11 * sc)
        pygame.draw.circle(surf, (50, 52, 56), P(-1.6, 0.2), 0.05 * sc)

        # Roll bar and seat behind the driver.
        _tube(surf, P, sc, [(-1.14, 0.34), (-1.0, 1.04), (-0.54, 1.04), (-0.44, 0.34)], 0.075, STEEL, STEEL_HI)
        _poly(surf, P, sc, [(-0.7, 0.34), (-0.74, 0.84), (-0.58, 0.9), (-0.5, 0.34)], (96, 58, 40), (50, 30, 20))

        # Driver: jacket, arm, gloves.
        jacket, jacket_dk = (36, 112, 210), (22, 72, 150)
        _poly(surf, P, sc, [(-0.5, 0.34), (-0.46, 0.76), (-0.3, 0.88), (-0.04, 0.86), (0.06, 0.7), (0.1, 0.34)],
              jacket, (16, 46, 100))
        pygame.draw.circle(surf, (230, 180, 140), P(-0.16, 0.86), 0.07 * sc)          # neck
        pygame.draw.line(surf, (40, 40, 44), P(0.52, 0.36), P(0.38, 0.62), max(1, int(0.04 * sc)))  # column
        pygame.draw.line(surf, (30, 30, 34), P(0.3, 0.52), P(0.44, 0.76), max(1, int(0.055 * sc)))  # wheel rim
        arm = [P(-0.14, 0.76), P(0.1, 0.56), P(0.36, 0.64)]
        pygame.draw.lines(surf, jacket_dk, False, arm, max(1, int(0.11 * sc)))
        for p in arm:
            pygame.draw.circle(surf, jacket_dk, p, 0.055 * sc)
        pygame.draw.circle(surf, (30, 30, 34), P(0.37, 0.64), 0.065 * sc)              # glove

        # Body tub.
        body = [(-1.52, 0.36), (0.42, 0.36), (0.6, 0.44), (1.36, 0.34), (1.5, 0.24), (1.5, -0.06),
                (1.38, -0.2), (-1.4, -0.2), (-1.52, -0.08)]
        pygame.draw.polygon(surf, RED, [P(*p) for p in body])
        lower = [(-1.52, 0.02), (1.5, 0.02), (1.5, -0.06), (1.38, -0.2), (-1.4, -0.2), (-1.52, -0.08)]
        pygame.draw.polygon(surf, RED_DK, [P(*p) for p in lower])
        pygame.draw.line(surf, RED_HI, P(-1.46, 0.31), P(0.4, 0.31), max(1, int(0.045 * sc)))
        pygame.draw.line(surf, RED_HI, P(0.64, 0.39), P(1.32, 0.3), max(1, int(0.04 * sc)))
        pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], ow)

        # Wheel arches: cut out, then a dark lip.
        for wx in (-1.02, 1.08):
            centre = P(wx, -0.64)
            pygame.draw.circle(surf, (0, 0, 0, 0), centre, 0.6 * sc)
            ring_arc(surf, OUTLINE, centre, 0.63 * sc, 0.57 * sc, math.radians(14), math.radians(166))
            ring_arc(surf, RED_DK, centre, 0.615 * sc, 0.585 * sc, math.radians(20), math.radians(160))

        # Door line, handle and racing roundel.
        pygame.draw.line(surf, RED_DK, P(0.02, 0.3), P(0.02, -0.04), max(1, int(0.02 * sc)))
        pygame.draw.rect(surf, (60, 20, 22), pygame.Rect(*P(-0.2, 0.22), 0.14 * sc, 0.04 * sc), border_radius=int(0.02 * sc))
        pygame.draw.circle(surf, (250, 248, 240), P(-0.68, 0.14), 0.15 * sc)
        pygame.draw.circle(surf, RED_DK, P(-0.68, 0.14), 0.15 * sc, max(1, int(0.022 * sc)))
        num = gfx.font_px("heavy", 0.27 * sc).render("7", True, (40, 30, 30))
        surf.blit(num, num.get_rect(center=P(-0.68, 0.135)))

        # Bumpers, lamp, exhaust.
        for x0, x1, y0, y1 in ((1.44, 1.64, -0.16, 0.04), (-1.66, -1.46, -0.18, 0.0)):
            r = pygame.Rect(P(x0, y1), ((x1 - x0) * sc, (y1 - y0) * sc))
            pygame.draw.rect(surf, STEEL, r, border_radius=int(0.04 * sc))
            pygame.draw.rect(surf, (30, 32, 36), r, max(1, int(0.018 * sc)), border_radius=int(0.04 * sc))
        pygame.draw.circle(surf, STEEL, P(1.45, 0.15), 0.09 * sc)
        pygame.draw.circle(surf, (255, 244, 190), P(1.46, 0.15), 0.06 * sc)
        pygame.draw.rect(surf, STEEL, pygame.Rect(P(-1.68, -0.15), (0.26 * sc, 0.07 * sc)), border_radius=int(0.03 * sc))

        # Windscreen frame, seen edge-on.
        pygame.draw.line(surf, (150, 200, 230), P(0.5, 0.42), P(0.36, 0.98), max(1, int(0.07 * sc)))
        pygame.draw.line(surf, STEEL, P(0.55, 0.42), P(0.41, 0.98), max(1, int(0.035 * sc)))
        pygame.draw.circle(surf, STEEL, P(0.39, 0.98), 0.03 * sc)
    return supersample(size, size, draw)


def head(ppm):
    """Driver's head: white full-face helmet with a red stripe and dark visor."""
    r = 0.27
    size = 2 * 0.36 * ppm

    def draw(surf, k):
        P, sc = _mapper(surf, ppm, k)
        shell = (244, 244, 248)
        pygame.draw.circle(surf, OUTLINE, P(0, 0), (r + 0.02) * sc)
        pygame.draw.circle(surf, shell, P(0, 0), r * sc)
        stripe = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(stripe, (220, 40, 44), [P(-0.08, 0.3), P(0.06, 0.3), P(-0.06, -0.3), P(-0.2, -0.3)])
        mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), P(0, 0), r * sc)
        stripe.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(stripe, (0, 0))
        visor = [P(0.02, 0.1), P(0.27, 0.08), P(0.25, -0.1), P(0.04, -0.07)]
        pygame.draw.polygon(surf, (36, 46, 70), visor)
        pygame.draw.line(surf, (130, 180, 230), P(0.07, 0.06), P(0.22, 0.05), max(1, int(0.03 * sc)))
        ring_arc(surf, (214, 214, 222), P(0, 0), r * sc, (r - 0.05) * sc, math.radians(200), math.radians(320))
        pygame.draw.circle(surf, (255, 255, 255), P(-0.1, 0.15), 0.05 * sc)     # gloss
    return supersample(size, size, draw)


def wheel(ppm, radius=0.46):
    size = 2 * (radius + 0.05) * ppm

    def draw(surf, k):
        P, sc = _mapper(surf, ppm, k)
        pygame.draw.circle(surf, TYRE, P(0, 0), radius * sc)
        n = 18
        for i in range(n):
            a = i * math.tau / n
            a0, a1 = a - 0.07, a + 0.07
            pts = [P(math.cos(a0) * (radius - 0.04), math.sin(a0) * (radius - 0.04)),
                   P(math.cos(a0) * (radius + 0.025), math.sin(a0) * (radius + 0.025)),
                   P(math.cos(a1) * (radius + 0.025), math.sin(a1) * (radius + 0.025)),
                   P(math.cos(a1) * (radius - 0.04), math.sin(a1) * (radius - 0.04))]
            pygame.draw.polygon(surf, TYRE, pts)
        pygame.draw.circle(surf, (56, 56, 62), P(0, 0), (radius - 0.07) * sc)
        pygame.draw.circle(surf, (42, 42, 46), P(0, 0), (radius - 0.1) * sc)
        pygame.draw.circle(surf, (120, 124, 132), P(0, 0), 0.26 * sc)
        pygame.draw.circle(surf, (196, 200, 208), P(0, 0), 0.235 * sc)
        for i in range(5):
            a = i * math.tau / 5
            pygame.draw.circle(surf, (70, 72, 80), P(math.cos(a) * 0.145, math.sin(a) * 0.145), 0.055 * sc)
        pygame.draw.circle(surf, (150, 154, 162), P(0, 0), 0.07 * sc)
        pygame.draw.circle(surf, (226, 228, 234), P(-0.02, 0.02), 0.03 * sc)
    return supersample(size, size, draw)


COIN_STYLE = {
    5: ((255, 214, 72), (214, 152, 26), (150, 96, 10), 0.3),
    25: ((255, 214, 72), (214, 152, 26), (150, 96, 10), 0.34),
    100: ((255, 220, 80), (210, 140, 20), (140, 84, 6), 0.38),
    500: ((255, 136, 108), (196, 46, 40), (120, 20, 20), 0.42),
}


def coin(value, px_radius):
    face, ring, ink, _ = COIN_STYLE[value]
    d = px_radius * 2 + 2

    def draw(surf, k):
        c = surf.get_width() / 2
        R = px_radius * k
        pygame.draw.circle(surf, gfx.shade(ring, 0.75), (c, c + R * 0.06), R)
        pygame.draw.circle(surf, ring, (c, c), R)
        pygame.draw.circle(surf, face, (c, c), R * 0.82)
        pygame.draw.circle(surf, gfx.shade(face, 1.35), (c - R * 0.05, c - R * 0.05), R * 0.7)
        pygame.draw.circle(surf, face, (c, c), R * 0.66)
        t = gfx.font_px("cond", R * 1.0).render(str(value), True, ink)
        if t.get_width() > R * 1.2:
            t = pygame.transform.smoothscale_by(t, R * 1.2 / t.get_width())
        surf.blit(t, t.get_rect(center=(c, c + R * 0.02)))
        pygame.draw.arc(surf, (255, 250, 220), pygame.Rect(c - R * 0.74, c - R * 0.74, R * 1.48, R * 1.48),
                        math.radians(100), math.radians(170), max(1, int(R * 0.1)))
    return supersample(d, d, draw)


def fuel_can(ppm):
    w, h = 0.66 * ppm, 0.86 * ppm

    def draw(surf, k):
        W, H = surf.get_size()
        red, dark = (226, 38, 36), (130, 16, 18)
        body = pygame.Rect(W * 0.04, H * 0.2, W * 0.92, H * 0.78)
        pygame.draw.rect(surf, dark, body, border_radius=int(W * 0.12))
        pygame.draw.rect(surf, red, body.inflate(-W * 0.08, -W * 0.08), border_radius=int(W * 0.1))
        handle = pygame.Rect(W * 0.06, H * 0.02, W * 0.56, H * 0.24)
        pygame.draw.rect(surf, dark, handle, border_radius=int(W * 0.08))
        pygame.draw.rect(surf, red, handle.inflate(-W * 0.07, -W * 0.07), border_radius=int(W * 0.06))
        for i in range(3):
            hole = pygame.Rect(W * (0.13 + i * 0.15), H * 0.08, W * 0.11, H * 0.1)
            pygame.draw.rect(surf, (0, 0, 0, 0), hole, border_radius=int(W * 0.04))
        spout = pygame.Rect(W * 0.7, H * 0.04, W * 0.2, H * 0.2)
        pygame.draw.rect(surf, (60, 60, 66), spout, border_radius=int(W * 0.05))
        x0, y0, x1, y1 = W * 0.2, H * 0.32, W * 0.8, H * 0.74
        hi = (248, 110, 100)
        for a, b in (((x0, y0), (x1, y1)), ((x1, y0), (x0, y1))):
            pygame.draw.line(surf, hi, a, b, max(1, int(W * 0.06)))
        label = pygame.Rect(W * 0.12, H * 0.78, W * 0.76, H * 0.14)
        pygame.draw.rect(surf, (250, 246, 236), label, border_radius=int(W * 0.04))
        t = gfx.font_px("cond", label.h * 1.05).render("FUEL", True, dark)
        if t.get_width() > label.w * 0.9:
            t = pygame.transform.smoothscale_by(t, label.w * 0.9 / t.get_width())
        surf.blit(t, t.get_rect(center=label.center))
        pygame.draw.rect(surf, (255, 170, 160), pygame.Rect(W * 0.14, H * 0.26, W * 0.08, H * 0.42),
                         border_radius=int(W * 0.04))
    return supersample(w, h, draw)


def pebble(px_radius, color, hi):
    d = px_radius * 2 + 2

    def draw(surf, k):
        c = surf.get_width() / 2
        R = px_radius * k
        pygame.draw.ellipse(surf, color, pygame.Rect(c - R, c - R * 0.86, 2 * R, 1.72 * R))
        pygame.draw.ellipse(surf, (*hi, 110), pygame.Rect(c - R * 0.6, c - R * 0.7, R * 0.9, R * 0.55))
    return supersample(d, d, draw)


def cloud(w, h, tint=(255, 255, 255)):
    def draw(surf, k):
        W, H = surf.get_size()
        under = gfx.shade(tint, 0.9)
        for cx, cy, r in ((0.25, 0.62, 0.3), (0.45, 0.42, 0.38), (0.68, 0.52, 0.32), (0.84, 0.66, 0.2)):
            pygame.draw.circle(surf, (*under, 235), (cx * W, cy * H + H * 0.06), r * H)
        for cx, cy, r in ((0.25, 0.62, 0.3), (0.45, 0.42, 0.38), (0.68, 0.52, 0.32), (0.84, 0.66, 0.2)):
            pygame.draw.circle(surf, (*tint, 245), (cx * W, cy * H), r * H)
        pygame.draw.rect(surf, (*tint, 245), pygame.Rect(W * 0.2, H * 0.62, W * 0.66, H * 0.3),
                         border_radius=int(H * 0.15))
    return supersample(w, h, draw)


def soft_puff(px_radius, color=(255, 255, 255)):
    d = int(px_radius * 2) + 2
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    c = d / 2
    for i in range(12, 0, -1):
        f = i / 12
        pygame.draw.circle(surf, (*color, int(150 * (1 - f) ** 0.8 + 10)), (c, c), px_radius * f)
    return surf
