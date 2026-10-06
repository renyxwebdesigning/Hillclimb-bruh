"""Scenery props that stand along the track (trees, cacti, snowmen, ...).

Each prop is drawn in metres; the returned sprite's bottom centre sits on
the ground.
"""
import math
import random

import pygame

import gfx

# kind: (width m, height m)
SIZES = {
    "tree": (3.2, 4.6), "bush": (1.8, 1.0), "flowers": (1.4, 0.6), "fence": (2.6, 1.1), "rock": (1.4, 0.9),
    "cactus": (1.6, 3.0), "cactus2": (1.4, 1.2), "skull": (1.0, 0.55), "deadbush": (1.4, 0.9),
    "pine": (2.4, 4.4), "snowman": (1.2, 1.9), "crystal": (1.2, 1.3),
    "moonrock": (1.6, 0.9), "dish": (1.8, 2.2), "flag": (1.3, 2.4),
}


def make(kind, ppm, variant=0):
    w, h = SIZES[kind]
    rnd = random.Random(hash((kind, variant)) & 0xFFFF)

    def draw(surf, k):
        W, H = surf.get_size()
        sc = ppm * k

        def P(x, y):           # x from centre, y up from the ground
            return (W / 2 + x * sc, H - y * sc)

        def circ(col, x, y, r):
            pygame.draw.circle(surf, col, P(x, y), r * sc)

        def poly(col, pts):
            pygame.draw.polygon(surf, col, [P(*p) for p in pts])

        def line(col, a, b, wd):
            pygame.draw.line(surf, col, P(*a), P(*b), max(1, int(wd * sc)))

        if kind == "tree":
            line((100, 66, 38), (0, 0), (0, 2.2), 0.32)
            line((100, 66, 38), (0, 1.5), (0.5, 2.3), 0.14)
            dark, mid, light = (56, 132, 40), (76, 160, 48), (118, 194, 66)
            blobs = ((-0.75, 2.5, 0.85), (0.7, 2.6, 0.9), (0, 3.4, 1.05), (-0.2, 2.3, 0.8), (0.5, 3.2, 0.7))
            for col, dx, dy, sh in ((dark, 0.1, -0.1, 1.0), (mid, 0.0, 0.0, 0.9), (light, -0.22, 0.25, 0.5)):
                for cx, cy, r in blobs:
                    circ(col, cx * sh + dx, 3.0 + (cy - 3.0) * sh + dy, r * sh)
        elif kind == "bush":
            for col, dy, sh in (((56, 132, 40), 0, 1.0), ((92, 174, 56), 0.08, 0.72)):
                for cx, cy, r in ((-0.5, 0.42, 0.42), (0.1, 0.55, 0.5), (0.55, 0.38, 0.38)):
                    circ(col, cx * sh, cy + dy, r * sh)
        elif kind == "flowers":
            for i in range(7):
                x = -0.6 + i * 0.2 + rnd.uniform(-0.05, 0.05)
                top = rnd.uniform(0.3, 0.55)
                line((70, 140, 40), (x, 0), (x, top), 0.03)
                col = rnd.choice(((255, 90, 90), (255, 220, 60), (250, 250, 250), (200, 120, 255)))
                for a in range(5):
                    ang = a * math.tau / 5
                    circ(col, x + math.cos(ang) * 0.06, top + math.sin(ang) * 0.06, 0.05)
                circ((255, 200, 40), x, top, 0.035)
        elif kind == "fence":
            wood, dark = (176, 122, 70), (120, 80, 44)
            for x in (-1.1, 0.0, 1.1):
                poly(dark, [(x - 0.09, 0), (x + 0.09, 0), (x + 0.09, 1.0), (x, 1.08), (x - 0.09, 1.0)])
                poly(wood, [(x - 0.06, 0), (x + 0.06, 0), (x + 0.06, 0.98), (x, 1.04), (x - 0.06, 0.98)])
            for y in (0.4, 0.78):
                poly(dark, [(-1.3, y - 0.09), (1.3, y - 0.07), (1.3, y + 0.07), (-1.3, y + 0.09)])
                poly(wood, [(-1.3, y - 0.06), (1.3, y - 0.04), (1.3, y + 0.04), (-1.3, y + 0.06)])
        elif kind in ("rock", "moonrock"):
            base = (128, 124, 120) if kind == "rock" else (170, 166, 184)
            pts = [(-0.68, 0), (-0.6, 0.42), (-0.25, 0.8), (0.2, 0.86), (0.58, 0.55), (0.68, 0)]
            poly(gfx.shade(base, 0.7), pts)
            poly(base, [(x * 0.9, y * 0.93) for x, y in pts])
            poly(gfx.shade(base, 1.25), [(-0.4, 0.45), (-0.2, 0.72), (0.15, 0.76), (-0.05, 0.5)])
            if kind == "moonrock":
                circ(gfx.shade(base, 0.8), 0.3, 0.3, 0.1)
        elif kind == "cactus":
            g, dg = (76, 156, 70), (52, 116, 50)
            for col, s_ in ((dg, 1.0), (g, 0.72)):
                line(col, (0, 0), (0, 2.7), 0.42 * s_)
                circ(col, 0, 2.7, 0.21 * s_)
                line(col, (-0.62, 1.2), (-0.62, 2.0), 0.28 * s_)
                line(col, (-0.62, 1.2), (0, 1.2), 0.28 * s_)
                circ(col, -0.62, 2.0, 0.14 * s_)
                line(col, (0.55, 1.6), (0.55, 2.3), 0.26 * s_)
                line(col, (0.55, 1.6), (0, 1.6), 0.26 * s_)
                circ(col, 0.55, 2.3, 0.13 * s_)
        elif kind == "cactus2":
            g, dg = (98, 170, 80), (62, 124, 54)
            for cx, cy, r in ((0, 0.45, 0.45), (-0.35, 0.85, 0.3), (0.32, 0.95, 0.28)):
                pygame.draw.ellipse(surf, dg, pygame.Rect(P(cx - r * 0.8, cy + r), (r * 1.6 * sc, r * 2 * sc)))
                pygame.draw.ellipse(surf, g, pygame.Rect(P(cx - r * 0.62, cy + r * 0.86), (r * 1.24 * sc, r * 1.7 * sc)))
            circ((255, 90, 140), 0.32, 1.24, 0.08)
        elif kind == "skull":
            bone, dark = (246, 236, 214), (120, 100, 80)
            poly(bone, [(-0.45, 0.35), (-0.2, 0.5), (0.2, 0.5), (0.45, 0.35), (0.2, 0.05), (-0.2, 0.05)])
            line(bone, (-0.4, 0.4), (-0.6, 0.55), 0.06)
            line(bone, (0.4, 0.4), (0.6, 0.55), 0.06)
            circ(dark, -0.15, 0.3, 0.07)
            circ(dark, 0.15, 0.3, 0.07)
        elif kind == "deadbush":
            col = (150, 110, 70)
            for i in range(9):
                a = math.radians(rnd.uniform(25, 155))
                L = rnd.uniform(0.4, 0.8)
                line(col, (0, 0), (math.cos(a) * L, math.sin(a) * L), 0.035)
                line(col, (math.cos(a) * L * 0.6, math.sin(a) * L * 0.6),
                     (math.cos(a + 0.5) * L * 0.9, math.sin(a + 0.5) * L * 0.9), 0.025)
        elif kind == "pine":
            line((96, 66, 40), (0, 0), (0, 0.8), 0.28)
            for i, (y, wd) in enumerate(((0.55, 1.15), (1.55, 0.95), (2.45, 0.72), (3.25, 0.48))):
                top = y + 1.25 - i * 0.08
                poly((30, 96, 70), [(-wd, y), (wd, y), (0, top)])
                poly((246, 250, 255), [(-wd * 0.6, y + 0.45), (0, top), (wd * 0.4, y + 0.55), (wd * 0.1, y + 0.4)])
        elif kind == "snowman":
            for cy, r in ((0.45, 0.45), (1.12, 0.33), (1.6, 0.24)):
                circ((205, 220, 238), cy * 0 + 0.03, cy - 0.03, r)
                circ((252, 253, 255), 0, cy, r * 0.96)
            poly((255, 140, 30), [(0.06, 1.62), (0.38, 1.58), (0.06, 1.54)])
            circ((30, 30, 34), -0.06, 1.68, 0.035)
            circ((30, 30, 34), 0.1, 1.68, 0.035)
            pygame.draw.rect(surf, (30, 30, 34), pygame.Rect(P(-0.2, 2.02), (0.4 * sc, 0.2 * sc)))
            pygame.draw.rect(surf, (30, 30, 34), pygame.Rect(P(-0.3, 1.84), (0.6 * sc, 0.05 * sc)))
            pygame.draw.rect(surf, (220, 40, 44), pygame.Rect(P(-0.26, 1.42), (0.52 * sc, 0.1 * sc)))
            line((110, 70, 40), (0.28, 1.15), (0.62, 1.4), 0.04)
            line((110, 70, 40), (-0.28, 1.15), (-0.6, 1.35), 0.04)
        elif kind == "crystal":
            for x, hh, a in ((-0.3, 0.9, -0.25), (0.05, 1.25, 0.05), (0.35, 0.8, 0.3)):
                ca, sa = math.cos(a), math.sin(a)

                def R(px, py, x=x, ca=ca, sa=sa):
                    return (x + px * ca - py * sa, px * sa + py * ca)
                poly((150, 210, 245), [R(-0.14, 0), R(0.14, 0), R(0.14, hh - 0.2), R(0, hh), R(-0.14, hh - 0.2)])
                poly((220, 244, 255), [R(-0.14, 0), R(0, 0), R(0, hh), R(-0.14, hh - 0.2)])
        elif kind == "dish":
            line((150, 150, 160), (0, 0), (0, 1.2), 0.12)
            poly((120, 120, 132), [(-0.4, 0), (0.4, 0), (0.2, 0.25), (-0.2, 0.25)])
            rect = pygame.Rect(0, 0, 1.5 * sc, 0.7 * sc)
            rect.center = P(-0.05, 1.55)
            surf.blit(pygame.transform.rotate(_ellipse(rect.size, (226, 228, 236)), 30), rect.move(-0.15 * sc, -0.35 * sc))
            line((90, 90, 100), (-0.05, 1.5), (0.35, 1.95), 0.05)
            circ((230, 60, 50), 0.38, 1.98, 0.06)
        elif kind == "flag":
            line((210, 210, 220), (0, 0), (0, 2.3), 0.06)
            stripes = ((220, 40, 44), (250, 250, 250))
            for i in range(5):
                pygame.draw.rect(surf, stripes[i % 2], pygame.Rect(P(0.03, 2.28 - i * 0.12), (1.1 * sc, 0.12 * sc)))
            pygame.draw.rect(surf, (40, 70, 160), pygame.Rect(P(0.03, 2.28), (0.42 * sc, 0.36 * sc)))
    return gfx.supersample(w * ppm, h * ppm, draw)


def _ellipse(size, color):
    s = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(s, color, s.get_rect())
    pygame.draw.ellipse(s, gfx.shade(color, 0.7), s.get_rect(), max(1, size[1] // 10))
    return s
