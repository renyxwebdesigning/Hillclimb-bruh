"""Vehicle bodies, rider heads and wheels, drawn procedurally in local metres.

Every body sprite is a square centred on the chassis origin so it can be
rotated freely. `head_behind` vehicles have see-through glass: the head is
drawn first and shows through the canopy.
"""
import math

import pygame

import gfx
from sprites import OUTLINE, STEEL, STEEL_HI, TYRE, _mapper, _poly, _tube, car_body, ring_arc

EXTENT = {"jeep": 2.3, "dirtbike": 1.8, "chopper": 2.0, "monster": 2.7, "supercar": 2.35, "rocket": 2.55}

CHROME, CHROME_DK = (214, 220, 228), (118, 124, 134)
BLACK = (34, 34, 38)


def _limb(surf, P, sc, a, b, width, color):
    w = max(1, int(width * sc))
    pygame.draw.line(surf, color, P(*a), P(*b), w)
    pygame.draw.circle(surf, color, P(*a), w / 2)
    pygame.draw.circle(surf, color, P(*b), w / 2)


def _cut(surf, P, sc, centre, r):
    pygame.draw.circle(surf, (0, 0, 0, 0), P(*centre), r * sc)


# ===================================================================== bodies
def _dirtbike(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    orange, orange_dk = (255, 122, 24), (190, 76, 6)
    jersey, jersey_dk = (38, 92, 222), (24, 58, 150)
    pants = (236, 238, 244)
    # exhaust
    _tube(surf, P, sc, [(0.02, -0.12), (-0.3, -0.06), (-0.62, 0.16), (-0.86, 0.22)], 0.07, CHROME_DK)
    pygame.draw.polygon(surf, CHROME, [P(-1.0, 0.3), P(-0.62, 0.3), P(-0.6, 0.14), P(-0.98, 0.14)])
    pygame.draw.circle(surf, BLACK, P(-0.99, 0.22), 0.05 * sc)
    # frame
    _tube(surf, P, sc, [(0.5, 0.5), (0.08, -0.18)], 0.07, (60, 62, 70))
    _tube(surf, P, sc, [(0.5, 0.56), (-0.18, 0.4), (-0.36, -0.02)], 0.06, (60, 62, 70))
    _tube(surf, P, sc, [(-0.18, 0.4), (-0.78, 0.44)], 0.05, (60, 62, 70))
    # engine
    eng = pygame.Rect(P(-0.26, 0.12), (0.52 * sc, 0.42 * sc))
    pygame.draw.rect(surf, (70, 72, 80), eng, border_radius=int(0.06 * sc))
    for i in range(4):
        y = 0.08 - i * 0.08
        pygame.draw.line(surf, (110, 114, 122), P(-0.22, y), P(0.0, y), max(1, int(0.02 * sc)))
    pygame.draw.circle(surf, CHROME, P(0.08, -0.16), 0.12 * sc)
    pygame.draw.circle(surf, CHROME_DK, P(0.08, -0.16), 0.12 * sc, max(1, int(0.02 * sc)))
    # rear fender + number panel
    _poly(surf, P, sc, [(-0.2, 0.44), (-1.12, 0.64), (-1.08, 0.53), (-0.3, 0.3)], orange, orange_dk, 0.02)
    _poly(surf, P, sc, [(-0.5, 0.42), (-0.86, 0.5), (-0.82, 0.3), (-0.48, 0.24)], (250, 250, 250), (150, 150, 160), 0.015)
    t = gfx.font_px("heavy", 0.2 * sc).render("17", True, BLACK)
    surf.blit(t, t.get_rect(center=P(-0.66, 0.37)))
    # seat and tank
    _poly(surf, P, sc, [(-0.78, 0.52), (0.08, 0.55), (0.14, 0.45), (-0.74, 0.43)], BLACK, None)
    _poly(surf, P, sc, [(0.02, 0.52), (0.46, 0.58), (0.52, 0.36), (0.16, 0.18), (-0.06, 0.3)], orange, orange_dk, 0.02)
    pygame.draw.line(surf, (255, 255, 255), P(0.1, 0.42), P(0.44, 0.48), max(1, int(0.04 * sc)))
    # front fender and number plate
    _poly(surf, P, sc, [(0.5, 0.3), (1.12, 0.26), (1.16, 0.2), (0.56, 0.22)], orange, orange_dk, 0.018)
    pygame.draw.ellipse(surf, (250, 250, 250), pygame.Rect(P(0.5, 0.68), (0.2 * sc, 0.26 * sc)))
    # rider
    _limb(surf, P, sc, (-0.28, 0.6), (0.22, 0.42), 0.18, pants)
    _limb(surf, P, sc, (0.22, 0.42), (0.02, 0.04), 0.15, pants)
    pygame.draw.line(surf, jersey, P(-0.2, 0.55), P(0.2, 0.44), max(1, int(0.035 * sc)))
    _poly(surf, P, sc, [(-0.06, 0.08), (0.08, 0.0), (0.12, -0.08), (-0.1, -0.08)], BLACK, None)
    _limb(surf, P, sc, (-0.26, 0.64), (0.08, 1.08), 0.3, jersey)
    pygame.draw.line(surf, (255, 255, 255), P(-0.2, 0.72), P(0.06, 1.02), max(1, int(0.04 * sc)))
    pygame.draw.line(surf, (40, 40, 44), P(0.48, 0.6), P(0.4, 0.82), max(1, int(0.05 * sc)))
    _limb(surf, P, sc, (0.08, 1.04), (0.3, 0.86), 0.11, jersey_dk)
    _limb(surf, P, sc, (0.3, 0.86), (0.42, 0.82), 0.1, jersey_dk)
    pygame.draw.circle(surf, BLACK, P(0.43, 0.82), 0.055 * sc)


def _chopper(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    purple, purple_dk = (128, 50, 200), (78, 24, 136)
    leather, jeans = (44, 42, 46), (52, 82, 140)
    # exhaust pipes
    for dy in (0.0, 0.1):
        _tube(surf, P, sc, [(0.05, -0.1 + dy), (-0.4, -0.08 + dy), (-1.44, -0.04 + dy)], 0.07, CHROME)
        pygame.draw.polygon(surf, CHROME_DK, [P(-1.44, 0.0 + dy), P(-1.58, 0.04 + dy), P(-1.58, -0.12 + dy), P(-1.44, -0.08 + dy)])
    # frame
    _tube(surf, P, sc, [(0.84, 0.7), (0.24, -0.2), (-0.3, -0.06)], 0.07, BLACK)
    _tube(surf, P, sc, [(0.84, 0.72), (-0.35, 0.32), (-1.0, 0.26)], 0.065, BLACK)
    # rear fender (wheel rests near (-1.05, -0.43))
    ring_arc(surf, purple_dk, P(-1.05, -0.43), 0.6 * sc, 0.5 * sc, math.radians(25), math.radians(160))
    ring_arc(surf, purple, P(-1.05, -0.43), 0.585 * sc, 0.515 * sc, math.radians(28), math.radians(157))
    # V-twin engine
    for a, b in (((0.0, -0.04), (-0.2, 0.34)), ((0.12, -0.04), (0.34, 0.34))):
        _limb(surf, P, sc, a, b, 0.18, CHROME)
        for i in range(1, 5):
            f = i / 5
            mx, my = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            pygame.draw.line(surf, CHROME_DK, P(mx - 0.08, my + 0.02), P(mx + 0.08, my - 0.02), max(1, int(0.018 * sc)))
    pygame.draw.ellipse(surf, CHROME, pygame.Rect(P(-0.16, 0.0), (0.42 * sc, 0.26 * sc)))
    pygame.draw.ellipse(surf, CHROME_DK, pygame.Rect(P(-0.16, 0.0), (0.42 * sc, 0.26 * sc)), max(1, int(0.02 * sc)))
    pygame.draw.circle(surf, CHROME, P(0.08, 0.14), 0.1 * sc)
    pygame.draw.circle(surf, CHROME_DK, P(0.08, 0.14), 0.1 * sc, max(1, int(0.02 * sc)))
    # tank with flame stripe
    _poly(surf, P, sc, [(0.04, 0.44), (0.34, 0.6), (0.74, 0.62), (0.8, 0.5), (0.4, 0.34)], purple, purple_dk, 0.02)
    pygame.draw.polygon(surf, (255, 190, 40), [P(0.7, 0.54), P(0.4, 0.5), P(0.5, 0.46), P(0.3, 0.44), P(0.62, 0.42)])
    # seat and sissy bar
    _tube(surf, P, sc, [(-0.86, 0.3), (-1.0, 0.96), (-0.88, 0.98)], 0.045, CHROME)
    _poly(surf, P, sc, [(-0.8, 0.42), (-0.1, 0.34), (-0.04, 0.44), (-0.55, 0.5)], BLACK, None)
    # bars and headlight
    _tube(surf, P, sc, [(0.84, 0.72), (0.74, 1.22), (0.5, 1.2)], 0.045, CHROME)
    pygame.draw.circle(surf, CHROME, P(0.98, 0.62), 0.11 * sc)
    pygame.draw.circle(surf, (255, 240, 170), P(1.0, 0.62), 0.07 * sc)
    # rider leaning back, feet forward
    _limb(surf, P, sc, (-0.45, 0.46), (0.25, 0.48), 0.18, jeans)
    _limb(surf, P, sc, (0.25, 0.48), (0.52, 0.16), 0.15, jeans)
    _poly(surf, P, sc, [(0.46, 0.2), (0.66, 0.16), (0.66, 0.08), (0.46, 0.08)], BLACK, None)
    _limb(surf, P, sc, (-0.44, 0.5), (-0.32, 1.1), 0.32, leather)
    _limb(surf, P, sc, (-0.3, 1.06), (0.08, 1.16), 0.11, leather)
    _limb(surf, P, sc, (0.08, 1.16), (0.5, 1.2), 0.1, leather)
    pygame.draw.circle(surf, (226, 176, 140), P(0.5, 1.2), 0.05 * sc)


def _monster(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    blue, blue_dk, blue_hi = (34, 104, 222), (18, 60, 150), (110, 170, 250)
    # exhaust stacks behind the cab
    for x in (-0.66, -0.5):
        _tube(surf, P, sc, [(x, 0.7), (x, 1.78)], 0.12, CHROME, (255, 255, 255))
        pygame.draw.rect(surf, BLACK, pygame.Rect(P(x - 0.07, 1.82), (0.14 * sc, 0.06 * sc)))
    # chassis rails
    pygame.draw.rect(surf, (36, 36, 40), pygame.Rect(P(-1.75, -0.04), (3.55 * sc, 0.28 * sc)), border_radius=int(0.04 * sc))
    body = [(-1.96, 0.0), (-1.96, 0.8), (-0.42, 0.8), (-0.42, 1.46), (0.44, 1.46), (0.86, 0.86),
            (1.9, 0.8), (2.02, 0.56), (2.02, 0.0)]
    pygame.draw.polygon(surf, blue, [P(*p) for p in body])
    pygame.draw.polygon(surf, blue_dk, [P(-1.96, 0.3), P(2.02, 0.3), P(2.02, 0.0), P(-1.96, 0.0)])
    pygame.draw.line(surf, blue_hi, P(-1.9, 0.74), P(-0.48, 0.74), max(1, int(0.04 * sc)))
    pygame.draw.line(surf, blue_hi, P(0.9, 0.76), P(1.86, 0.74), max(1, int(0.04 * sc)))
    # flames along the side
    for col, inset in (((255, 210, 40), 0.0), ((255, 130, 30), 0.06), ((226, 40, 30), 0.12)):
        pts = [(-0.2 + inset, 0.08 + inset * 0.5)]
        x = 0.0
        while x < 1.7 - inset:
            pts += [(x + 0.18, 0.5 - inset), (x + 0.32, 0.24 + inset * 0.3)]
            x += 0.36
        pts += [(1.92 - inset, 0.3), (1.92 - inset, 0.08 + inset * 0.5)]
        pygame.draw.polygon(surf, col, [P(*p) for p in pts])
    # see-through window (head sits behind it)
    win = [P(-0.3, 0.88), P(0.56, 0.88), P(0.4, 1.34), P(-0.3, 1.34)]
    pygame.draw.polygon(surf, (170, 220, 250, 110), win)
    pygame.draw.line(surf, (255, 255, 255, 180), P(0.1, 0.9), P(0.3, 1.3), max(1, int(0.05 * sc)))
    pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], max(1, int(0.03 * sc)))
    pygame.draw.polygon(surf, OUTLINE, win, max(1, int(0.03 * sc)))
    # roof lights, lamps, bumpers, mirror
    pygame.draw.rect(surf, BLACK, pygame.Rect(P(-0.3, 1.58), (0.74 * sc, 0.12 * sc)), border_radius=int(0.03 * sc))
    for i in range(4):
        pygame.draw.circle(surf, (255, 226, 80), P(-0.21 + i * 0.19, 1.52), 0.06 * sc)
    pygame.draw.circle(surf, (255, 240, 170), P(1.96, 0.62), 0.08 * sc)
    pygame.draw.rect(surf, (230, 40, 40), pygame.Rect(P(-2.0, 0.7), (0.08 * sc, 0.18 * sc)))
    for x0, x1 in ((1.92, 2.18), (-2.18, -1.92)):
        r = pygame.Rect(P(x0, 0.3), ((x1 - x0) * sc, 0.28 * sc))
        pygame.draw.rect(surf, CHROME, r, border_radius=int(0.05 * sc))
        pygame.draw.rect(surf, CHROME_DK, r, max(1, int(0.02 * sc)), border_radius=int(0.05 * sc))
    pygame.draw.rect(surf, BLACK, pygame.Rect(P(0.62, 1.12), (0.12 * sc, 0.16 * sc)))


def _supercar(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    yellow, yellow_dk, yellow_hi = (255, 198, 22), (206, 140, 0), (255, 232, 120)
    body = [(-2.05, -0.12), (-2.02, 0.26), (-1.6, 0.4), (-0.95, 0.5), (-0.45, 0.72), (0.25, 0.74),
            (0.95, 0.38), (1.75, 0.16), (2.08, 0.0), (2.02, -0.18), (1.6, -0.3), (-1.7, -0.3), (-2.05, -0.2)]
    # spoiler
    for x in (-1.75, -1.55):
        pygame.draw.line(surf, BLACK, P(x, 0.38), P(x - 0.05, 0.62), max(1, int(0.04 * sc)))
    pygame.draw.polygon(surf, BLACK, [P(-2.12, 0.6), P(-1.42, 0.62), P(-1.48, 0.72), P(-2.12, 0.72)])
    pygame.draw.polygon(surf, yellow, [P(*p) for p in body])
    pygame.draw.polygon(surf, yellow_dk, [P(-2.05, -0.02), P(2.05, -0.02), P(2.02, -0.18), P(1.6, -0.3),
                                          P(-1.7, -0.3), P(-2.05, -0.2)])
    pygame.draw.line(surf, yellow_hi, P(1.0, 0.36), P(1.72, 0.17), max(1, int(0.04 * sc)))
    pygame.draw.line(surf, yellow_hi, P(-1.55, 0.38), P(-0.98, 0.47), max(1, int(0.035 * sc)))
    # side intake and skirt
    pygame.draw.polygon(surf, BLACK, [P(-0.95, 0.1), P(-0.5, 0.3), P(-0.38, 0.04), P(-0.9, -0.04)])
    pygame.draw.rect(surf, BLACK, pygame.Rect(P(-1.7, -0.22), (3.3 * sc, 0.09 * sc)))
    for x in (-1.25, 1.3):
        _cut(surf, P, sc, (x, -0.17), 0.43)
        ring_arc(surf, BLACK, P(x, -0.17), 0.46 * sc, 0.42 * sc, math.radians(5), math.radians(175))
    # see-through glass
    glass = [P(-0.85, 0.5), P(-0.42, 0.69), P(0.22, 0.71), P(0.86, 0.4)]
    pygame.draw.polygon(surf, (40, 52, 74, 150), glass)
    pygame.draw.line(surf, (200, 220, 255, 170), P(0.2, 0.66), P(0.6, 0.46), max(1, int(0.03 * sc)))
    pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], max(1, int(0.025 * sc)))
    # lights and tips
    pygame.draw.polygon(surf, (255, 255, 240), [P(1.68, 0.14), P(1.98, 0.05), P(1.96, 0.1), P(1.7, 0.2)])
    pygame.draw.rect(surf, (230, 30, 30), pygame.Rect(P(-2.06, 0.22), (0.08 * sc, 0.14 * sc)))
    for dy in (0.0, 0.08):
        pygame.draw.circle(surf, CHROME_DK, P(-2.06, -0.13 + dy), 0.04 * sc)
    pygame.draw.line(surf, BLACK, P(-0.3, 0.3), P(0.9, 0.3), max(1, int(0.015 * sc)))


def _rocket(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    white, shade, red, red_dk = (242, 244, 248), (196, 202, 214), (222, 40, 44), (150, 20, 26)
    _poly(surf, P, sc, [(-1.1, 0.48), (-1.95, 0.95), (-2.02, 0.82), (-1.55, 0.4)], red, red_dk, 0.02)
    _poly(surf, P, sc, [(-1.1, -0.28), (-1.95, -0.65), (-2.02, -0.52), (-1.55, -0.22)], red, red_dk, 0.02)
    _poly(surf, P, sc, [(-1.55, 0.32), (-1.96, 0.44), (-1.96, -0.24), (-1.55, -0.12)], (66, 68, 76), (30, 30, 34), 0.02)
    pygame.draw.line(surf, CHROME, P(-1.96, 0.44), P(-1.96, -0.24), max(1, int(0.05 * sc)))
    tube = pygame.Rect(P(-1.62, 0.52), (3.08 * sc, 0.84 * sc))
    pygame.draw.rect(surf, white, tube, border_radius=int(0.1 * sc))
    pygame.draw.rect(surf, shade, pygame.Rect(P(-1.62, 0.02), (3.08 * sc, 0.34 * sc)),
                     border_bottom_left_radius=int(0.1 * sc), border_bottom_right_radius=int(0.1 * sc))
    pygame.draw.rect(surf, OUTLINE, tube, max(1, int(0.025 * sc)), border_radius=int(0.1 * sc))
    for x in (-1.3, 0.98):
        pygame.draw.rect(surf, red, pygame.Rect(P(x, 0.52), (0.13 * sc, 0.84 * sc)))
    _poly(surf, P, sc, [(1.42, 0.52), (1.92, 0.4), (2.28, 0.1), (1.92, -0.2), (1.42, -0.32)], red, red_dk, 0.025)
    pygame.draw.line(surf, (255, 140, 130), P(1.5, 0.44), P(1.9, 0.34), max(1, int(0.04 * sc)))
    _poly(surf, P, sc, [(-0.2, -0.3), (-0.55, -0.62), (-0.7, -0.58), (-0.55, -0.3)], red, red_dk, 0.02)
    for x in (-0.85, -0.45):
        pygame.draw.circle(surf, CHROME_DK, P(x, 0.16), 0.11 * sc)
        pygame.draw.circle(surf, (80, 150, 220), P(x, 0.16), 0.08 * sc)
        pygame.draw.circle(surf, (200, 230, 255), P(x - 0.02, 0.19), 0.025 * sc)
    t = gfx.font_px("heavy", 0.18 * sc).render("HR-1", True, red_dk)
    surf.blit(t, t.get_rect(center=P(0.0, -0.12)))
    canopy = pygame.Rect(P(0.18, 0.98), (0.8 * sc, 0.76 * sc))
    _cut(surf, P, sc, (0.58, 0.6), 0.36)
    pygame.draw.ellipse(surf, (150, 210, 250, 110), canopy)
    pygame.draw.ellipse(surf, CHROME_DK, canopy, max(1, int(0.03 * sc)))
    pygame.draw.arc(surf, (255, 255, 255, 200), canopy.inflate(-0.14 * sc, -0.14 * sc), 1.7, 2.6, max(1, int(0.04 * sc)))


BODIES = {"dirtbike": _dirtbike, "chopper": _chopper, "monster": _monster, "supercar": _supercar, "rocket": _rocket}


def body(key, ppm):
    if key == "jeep":
        return car_body(ppm)
    size = 2 * EXTENT[key] * ppm
    return gfx.supersample(size, size, lambda s, k: BODIES[key](s, k, ppm))


# ====================================================================== heads
def head(style, ppm):
    r = 0.27 if style not in ("mx", "biker", "astro") else 0.22
    size = 2 * (r + 0.16) * ppm

    def draw(surf, k):
        P, sc = _mapper(surf, ppm, k)
        if style == "mx":
            shell, accent = (255, 122, 24), (30, 30, 34)
            pygame.draw.circle(surf, OUTLINE, P(0, 0), (r + 0.02) * sc)
            pygame.draw.circle(surf, shell, P(0, 0), r * sc)
            _poly(surf, P, sc, [(-0.04, 0.2), (0.34, 0.16), (0.36, 0.1), (0.0, 0.1)], accent, None)   # peak
            _poly(surf, P, sc, [(0.1, -0.06), (0.32, -0.08), (0.3, -0.2), (0.08, -0.2)], accent, None)  # chin bar
            pygame.draw.rect(surf, (40, 40, 44), pygame.Rect(P(0.04, 0.07), (0.22 * sc, 0.11 * sc)), border_radius=int(0.03 * sc))
            pygame.draw.rect(surf, (90, 200, 255), pygame.Rect(P(0.07, 0.05), (0.16 * sc, 0.07 * sc)), border_radius=int(0.02 * sc))
            pygame.draw.line(surf, (255, 255, 255), P(-0.2, 0.0), P(0.04, -0.02), max(1, int(0.04 * sc)))
        elif style == "biker":
            skin, beard = (230, 180, 142), (140, 84, 40)
            pygame.draw.circle(surf, skin, P(0, -0.02), r * sc)
            _poly(surf, P, sc, [(-0.12, -0.02), (0.22, -0.02), (0.2, -0.22), (0.02, -0.32), (-0.14, -0.2)], beard, None)
            pygame.draw.circle(surf, BLACK, P(0, 0.02), (r + 0.02) * sc, draw_top_left=True, draw_top_right=True)
            pygame.draw.rect(surf, BLACK, pygame.Rect(P(-0.22, 0.04), (0.46 * sc, 0.06 * sc)))
            pygame.draw.rect(surf, (30, 30, 34), pygame.Rect(P(0.06, 0.0), (0.18 * sc, 0.08 * sc)), border_radius=int(0.02 * sc))
            pygame.draw.circle(surf, (226, 70, 40), P(0.2, -0.06), 0.03 * sc)
        elif style == "astro":
            pygame.draw.circle(surf, OUTLINE, P(0, 0), (r + 0.02) * sc)
            pygame.draw.circle(surf, (246, 246, 250), P(0, 0), r * sc)
            pygame.draw.ellipse(surf, (230, 170, 40), pygame.Rect(P(-0.02, 0.14), (0.26 * sc, 0.26 * sc)))
            pygame.draw.ellipse(surf, (255, 230, 150), pygame.Rect(P(0.04, 0.1), (0.08 * sc, 0.06 * sc)))
            pygame.draw.rect(surf, (200, 40, 40), pygame.Rect(P(-0.2, -0.12), (0.12 * sc, 0.06 * sc)))
        else:
            shell, stripe, visor = {
                "helmet": ((244, 244, 248), (220, 40, 44), (36, 46, 70)),
                "helmet_blue": ((255, 214, 40), (30, 30, 34), (36, 46, 70)),
                "racer": ((32, 32, 36), (255, 198, 22), (60, 90, 140)),
            }[style]
            pygame.draw.circle(surf, OUTLINE, P(0, 0), (r + 0.02) * sc)
            pygame.draw.circle(surf, shell, P(0, 0), r * sc)
            band = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(band, stripe, [P(-0.08, 0.3), P(0.06, 0.3), P(-0.06, -0.3), P(-0.2, -0.3)])
            mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), P(0, 0), r * sc)
            band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(band, (0, 0))
            pygame.draw.polygon(surf, visor, [P(0.02, 0.1), P(0.27, 0.08), P(0.25, -0.1), P(0.04, -0.07)])
            pygame.draw.line(surf, (130, 180, 230), P(0.07, 0.06), P(0.22, 0.05), max(1, int(0.03 * sc)))
            ring_arc(surf, gfx.shade(shell, 0.85), P(0, 0), r * sc, (r - 0.05) * sc, math.radians(200), math.radians(320))
            pygame.draw.circle(surf, (255, 255, 255), P(-0.1, 0.15), 0.05 * sc)
    return gfx.supersample(size, size, draw)


# ===================================================================== wheels
def wheel(style, radius, ppm):
    size = 2 * (radius + 0.06) * ppm

    def draw(surf, k):
        P, sc = _mapper(surf, ppm, k)
        R = radius
        if style == "knobby":
            _knobby(surf, P, sc, R, 18, 0.04, 0.025)
            pygame.draw.circle(surf, (56, 56, 62), P(0, 0), (R - 0.07) * sc)
            pygame.draw.circle(surf, (42, 42, 46), P(0, 0), (R - 0.1) * sc)
            _rim(surf, P, sc, 0.26, 5, (196, 200, 208))
        elif style == "monster":
            _knobby(surf, P, sc, R, 14, 0.07, 0.05)
            pygame.draw.circle(surf, (50, 50, 56), P(0, 0), (R - 0.12) * sc)
            for i in range(14):
                a = (i + 0.5) * math.tau / 14
                pygame.draw.line(surf, (30, 30, 34), P(math.cos(a) * (R - 0.12), math.sin(a) * (R - 0.12)),
                                 P(math.cos(a) * (R - 0.25), math.sin(a) * (R - 0.25)), max(1, int(0.04 * sc)))
            pygame.draw.circle(surf, (40, 40, 44), P(0, 0), (R - 0.26) * sc)
            _rim(surf, P, sc, 0.42, 6, CHROME)
        elif style == "spoked":
            _knobby(surf, P, sc, R, 22, 0.02, 0.018)
            pygame.draw.circle(surf, (0, 0, 0, 0), P(0, 0), (R - 0.07) * sc)
            pygame.draw.circle(surf, CHROME, P(0, 0), (R - 0.07) * sc, max(1, int(0.03 * sc)))
            for i in range(16):
                a = i * math.tau / 16
                pygame.draw.line(surf, (170, 176, 186), P(math.cos(a) * 0.05, math.sin(a) * 0.05),
                                 P(math.cos(a + 0.4) * (R - 0.08), math.sin(a + 0.4) * (R - 0.08)), max(1, int(0.012 * sc)))
            pygame.draw.circle(surf, (90, 94, 102), P(0, 0), 0.07 * sc)
            pygame.draw.circle(surf, CHROME, P(0, 0), 0.04 * sc)
        elif style == "whitewall":
            pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
            pygame.draw.circle(surf, (246, 246, 240), P(0, 0), (R - 0.07) * sc)
            pygame.draw.circle(surf, TYRE, P(0, 0), (R - 0.13) * sc)
            pygame.draw.circle(surf, CHROME, P(0, 0), (R - 0.16) * sc)
            for i in range(12):
                a = i * math.tau / 12
                pygame.draw.line(surf, CHROME_DK, P(0, 0), P(math.cos(a) * (R - 0.17), math.sin(a) * (R - 0.17)),
                                 max(1, int(0.02 * sc)))
            pygame.draw.circle(surf, CHROME_DK, P(0, 0), 0.08 * sc)
            pygame.draw.circle(surf, CHROME, P(0, 0), 0.05 * sc)
        elif style == "sport":
            pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
            pygame.draw.circle(surf, (70, 72, 80), P(0, 0), (R - 0.07) * sc)
            pygame.draw.circle(surf, (40, 40, 46), P(0, 0), (R - 0.09) * sc)
            for i in range(5):
                a = i * math.tau / 5
                for d in (-0.13, 0.13):
                    pygame.draw.line(surf, (200, 204, 212), P(math.cos(a) * 0.05, math.sin(a) * 0.05),
                                     P(math.cos(a + d) * (R - 0.1), math.sin(a + d) * (R - 0.1)), max(1, int(0.035 * sc)))
            pygame.draw.circle(surf, (230, 40, 40), P(0, 0), 0.06 * sc)
            pygame.draw.circle(surf, CHROME, P(0, 0), 0.035 * sc)
        else:  # solid
            pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
            pygame.draw.circle(surf, (255, 196, 30), P(0, 0), R * 0.55 * sc)
            pygame.draw.circle(surf, (200, 140, 0), P(0, 0), R * 0.55 * sc, max(1, int(0.02 * sc)))
            for i in range(3):
                a = i * math.tau / 3
                pygame.draw.circle(surf, (200, 140, 0), P(math.cos(a) * R * 0.3, math.sin(a) * R * 0.3), 0.025 * sc)
    return gfx.supersample(size, size, draw)


def _knobby(surf, P, sc, R, n, depth, out):
    pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
    for i in range(n):
        a = i * math.tau / n
        w = math.pi / n * 0.55
        pts = [P(math.cos(a - w) * (R - depth), math.sin(a - w) * (R - depth)),
               P(math.cos(a - w) * (R + out), math.sin(a - w) * (R + out)),
               P(math.cos(a + w) * (R + out), math.sin(a + w) * (R + out)),
               P(math.cos(a + w) * (R - depth), math.sin(a + w) * (R - depth))]
        pygame.draw.polygon(surf, TYRE, pts)


def _rim(surf, P, sc, r, holes, color):
    pygame.draw.circle(surf, gfx.shade(color, 0.62), P(0, 0), r * sc)
    pygame.draw.circle(surf, color, P(0, 0), (r - 0.025) * sc)
    for i in range(holes):
        a = i * math.tau / holes
        pygame.draw.circle(surf, (70, 72, 80), P(math.cos(a) * r * 0.56, math.sin(a) * r * 0.56), r * 0.21 * sc)
    pygame.draw.circle(surf, gfx.shade(color, 0.78), P(0, 0), r * 0.27 * sc)
    pygame.draw.circle(surf, (236, 238, 242), P(-0.02, 0.02), r * 0.11 * sc)


# ===================================================================== flames
def flame(ppm, length=1.0, seed=0):
    """Rocket/boost flame pointing towards -x from its origin (sprite centre)."""
    size = 2 * (length + 0.1) * ppm
    rnd = __import__("random").Random(seed)

    def draw(surf, k):
        P, sc = _mapper(surf, ppm, k)
        for col, L, w in (((255, 90, 20, 170), length, 0.26), ((255, 170, 40, 220), length * 0.72, 0.19),
                          ((255, 236, 140, 255), length * 0.42, 0.12), ((255, 255, 255, 255), length * 0.18, 0.07)):
            L *= rnd.uniform(0.85, 1.1)
            pts = [(0, w)]
            for i in range(1, 7):
                f = i / 7
                pts.append((-L * f, w * (1 - f) ** 0.8 + rnd.uniform(-0.02, 0.02)))
            pts.append((-L, 0))
            for i in range(6, 0, -1):
                f = i / 7
                pts.append((-L * f, -w * (1 - f) ** 0.8 + rnd.uniform(-0.02, 0.02)))
            pts.append((0, -w))
            pygame.draw.polygon(surf, col, [P(*p) for p in pts])
    return gfx.supersample(size, size, draw)
