"""Vehicle bodies, rider heads and wheels, drawn procedurally in local metres.

Every body sprite is a square centred on the chassis origin so it can be
rotated freely. `head_behind` vehicles have see-through glass: the head is
drawn first and shows through the canopy.
"""
import math

import pygame

import gfx
from sprites import OUTLINE, STEEL, STEEL_HI, TYRE, _mapper, _poly, _tube, car_body, ring_arc

EXTENT = {"jeep": 2.3, "dirtbike": 1.8, "chopper": 2.0, "monster": 2.7, "supercar": 2.35,
          "tank": 3.15, "police": 2.4, "hoverboard": 2.0, "tesla": 2.35, "mini": 1.8, "b2": 2.5,
          "excavator": 3.1, "lkw": 2.95, "golf": 2.3, "shark": 3.0}

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


def _glass(surf, P, sc, pts, tint=(40, 56, 80, 140)):
    """See-through window (the driver's head is drawn behind the body) with a soft reflection."""
    pygame.draw.polygon(surf, tint, [P(*p) for p in pts])
    (x0, y0), (x1, y1) = pts[0], pts[len(pts) // 2]
    pygame.draw.line(surf, (220, 235, 255, 120), P(x0 + (x1 - x0) * 0.55, y0 + (y1 - y0) * 0.75),
                     P(x0 + (x1 - x0) * 0.75, y0 + (y1 - y0) * 0.3), max(1, int(0.03 * sc)))


def _arches(surf, P, sc, xs, y, r, rim=(20, 20, 24)):
    for x in xs:
        _cut(surf, P, sc, (x, y), r)
        ring_arc(surf, rim, P(x, y), (r + 0.03) * sc, (r - 0.01) * sc, math.radians(5), math.radians(175))


def _tesla(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    white, shade, hi = (244, 245, 247), (196, 200, 208), (255, 255, 255)
    body = [(-2.05, -0.22), (-2.06, 0.26), (-1.78, 0.44), (-1.5, 0.54), (-0.9, 0.82), (-0.2, 0.9), (0.45, 0.82),
            (0.95, 0.56), (1.3, 0.44), (1.85, 0.3), (2.08, 0.12), (2.1, -0.1), (1.95, -0.26), (1.6, -0.34),
            (-1.7, -0.34)]
    pygame.draw.polygon(surf, white, [P(*p) for p in body])
    pygame.draw.polygon(surf, shade, [P(-2.05, -0.06), P(2.1, -0.06), P(2.1, -0.1), P(1.95, -0.26), P(1.6, -0.34),
                                      P(-1.7, -0.34), P(-2.05, -0.22)])
    pygame.draw.line(surf, hi, P(-1.6, 0.42), P(1.6, 0.36), max(1, int(0.03 * sc)))           # shoulder line
    _arches(surf, P, sc, (-1.32, 1.38), -0.25, 0.44)
    # the glass roof: one sweep from the windscreen to the boot
    _glass(surf, P, sc, [(-1.62, 0.5), (-0.95, 0.78), (-0.2, 0.86), (0.42, 0.78), (0.9, 0.52)], (34, 44, 60, 170))
    pygame.draw.line(surf, white, P(-0.32, 0.5), P(-0.28, 0.86), max(1, int(0.05 * sc)))     # B pillar
    for x in (-0.95, 0.3):                                                                   # flush handles
        pygame.draw.rect(surf, shade, pygame.Rect(P(x, 0.32), (0.22 * sc, 0.04 * sc)), border_radius=int(0.02 * sc))
    pygame.draw.line(surf, shade, P(-0.32, 0.46), P(-0.36, -0.2), max(1, int(0.015 * sc)))   # door seam
    pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], max(1, int(0.022 * sc)))
    pygame.draw.polygon(surf, (250, 252, 255), [P(1.7, 0.26), P(2.04, 0.15), P(2.02, 0.11), P(1.72, 0.2)])
    pygame.draw.line(surf, (220, 30, 36), P(-2.05, 0.3), P(-1.82, 0.4), max(1, int(0.06 * sc)))
    t = gfx.font_px("heavy", 0.2 * sc).render("T", True, (200, 30, 36))
    surf.blit(t, t.get_rect(center=P(1.96, 0.02)))


def _mini(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    red, red_dk, white = (206, 26, 34), (140, 12, 20), (246, 246, 244)
    body = [(-1.45, -0.28), (-1.47, 0.42), (-1.15, 0.47), (0.55, 0.47), (0.78, 0.44), (1.38, 0.36), (1.5, 0.18),
            (1.5, -0.14), (1.4, -0.3)]
    pygame.draw.polygon(surf, red, [P(*p) for p in body])
    pygame.draw.polygon(surf, red_dk, [P(-1.46, -0.06), P(1.5, -0.06), P(1.5, -0.14), P(1.4, -0.3), P(-1.45, -0.28)])
    _arches(surf, P, sc, (-0.98, 1.0), -0.27, 0.36)
    # white roof on thin pillars, dark windows
    _glass(surf, P, sc, [(-1.22, 0.47), (-1.2, 0.88), (0.36, 0.88), (0.72, 0.47)], (34, 44, 60, 170))
    for a, b in (((-1.22, 0.47), (-1.2, 0.9)), ((-0.32, 0.47), (-0.32, 0.9)), ((0.36, 0.9), (0.72, 0.47))):
        pygame.draw.line(surf, red, P(*a), P(*b), max(1, int(0.07 * sc)))
    _poly(surf, P, sc, [(-1.28, 0.88), (0.42, 0.88), (0.4, 0.98), (-1.25, 0.98)], white, OUTLINE, 0.02)
    for dy in (0.4, 0.31):                                                           # bonnet stripes
        pygame.draw.line(surf, white, P(0.8, dy + 0.02), P(1.38, dy - 0.05), max(1, int(0.035 * sc)))
    pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], max(1, int(0.022 * sc)))
    pygame.draw.circle(surf, CHROME_DK, P(1.42, 0.2), 0.1 * sc)
    pygame.draw.circle(surf, (255, 252, 230), P(1.43, 0.2), 0.075 * sc)
    pygame.draw.rect(surf, CHROME, pygame.Rect(P(1.36, -0.12), (0.18 * sc, 0.08 * sc)), border_radius=int(0.02 * sc))
    pygame.draw.rect(surf, (230, 40, 40), pygame.Rect(P(-1.5, 0.3), (0.07 * sc, 0.12 * sc)))
    pygame.draw.rect(surf, CHROME, pygame.Rect(P(-1.0, 0.26), (0.16 * sc, 0.035 * sc)))


def _b2(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    top, under, edge = (92, 98, 110), (58, 62, 72), (34, 36, 42)
    # the far wing, seen a little from above: a pale sliver behind the fuselage
    _poly(surf, P, sc, [(1.9, 0.08), (0.2, 0.3), (-2.4, 0.38), (-2.0, 0.2), (-2.3, 0.14), (-1.6, 0.06)],
          (120, 126, 138), edge, 0.015)
    body = [(2.3, 0.05), (1.6, 0.3), (1.05, 0.44), (0.6, 0.62), (0.05, 0.56), (-0.6, 0.42), (-1.6, 0.22),
            (-2.2, 0.06), (-1.92, -0.04), (-2.12, -0.12), (-1.5, -0.18), (1.0, -0.18), (1.9, -0.1)]
    pygame.draw.polygon(surf, top, [P(*p) for p in body])
    pygame.draw.polygon(surf, under, [P(2.25, 0.0), P(1.9, -0.1), P(1.0, -0.18), P(-1.5, -0.18), P(-2.12, -0.12),
                                      P(-1.92, -0.04), P(-2.0, 0.0)])
    pygame.draw.line(surf, (140, 148, 162), P(1.6, 0.27), P(-1.5, 0.2), max(1, int(0.025 * sc)))
    for x in (-0.55, 0.05):                                                          # engine intakes
        _poly(surf, P, sc, [(x - 0.25, 0.45), (x, 0.56), (x + 0.22, 0.5), (x + 0.1, 0.44)], (40, 42, 50), edge, 0.012)
    _glass(surf, P, sc, [(0.7, 0.42), (0.76, 0.58), (1.05, 0.5), (1.2, 0.4)], (20, 24, 32, 150))
    pygame.draw.polygon(surf, edge, [P(*p) for p in body], max(1, int(0.022 * sc)))
    pygame.draw.rect(surf, (30, 32, 36), pygame.Rect(P(-2.18, 0.16), (0.12 * sc, 0.12 * sc)))


def _excavator(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    yel, yel_dk, yel_hi, steel = (250, 190, 22), (190, 132, 0), (255, 222, 110), (70, 72, 78)
    # undercarriage: track frame and car body between the tracks and the turning upper part
    _poly(surf, P, sc, [(-1.45, -0.02), (1.45, -0.02), (1.25, 0.2), (-1.25, 0.2)], (64, 66, 72), (30, 30, 34), 0.02)
    _poly(surf, P, sc, [(-0.7, 0.18), (0.7, 0.18), (0.6, 0.44), (-0.6, 0.44)], (52, 54, 60), (30, 30, 34), 0.02)
    pygame.draw.rect(surf, (40, 40, 44), pygame.Rect(P(-1.55, 0.5), (2.9 * sc, 0.08 * sc)))       # slewing ring
    _tube(surf, P, sc, [(-1.15, 0.95), (-1.15, 1.92)], 0.08, (52, 54, 60))                      # exhaust stack
    house = [(-1.75, 0.45), (-1.8, 0.95), (-0.95, 1.0), (0.65, 1.0), (0.75, 0.45)]
    _poly(surf, P, sc, house, yel, (90, 62, 0), 0.025)
    _poly(surf, P, sc, [(-1.85, 0.45), (-1.9, 0.92), (-1.55, 0.95), (-1.5, 0.45)], (60, 62, 68), (30, 30, 34), 0.02)
    pygame.draw.line(surf, yel_hi, P(-1.4, 0.94), P(0.55, 0.95), max(1, int(0.035 * sc)))
    for x in (-1.25, -1.05, -0.85):                                                             # engine grille
        pygame.draw.line(surf, yel_dk, P(x, 0.6), P(x, 0.85), max(1, int(0.03 * sc)))
    # cab with see-through glass
    cab = [(-0.95, 1.0), (-0.95, 1.78), (0.1, 1.78), (0.3, 1.0)]
    _poly(surf, P, sc, cab, yel, (90, 62, 0), 0.025)
    _glass(surf, P, sc, [(-0.85, 1.05), (-0.85, 1.68), (0.04, 1.68), (0.2, 1.05)], (60, 90, 120, 120))
    pygame.draw.line(surf, yel, P(-0.4, 1.05), P(-0.4, 1.68), max(1, int(0.05 * sc)))
    # boom, arm, cylinders and bucket
    boom = [(0.3, 0.78), (0.55, 1.0), (1.55, 1.98), (1.82, 1.86), (0.75, 0.75)]
    _poly(surf, P, sc, boom, yel, (90, 62, 0), 0.025)
    pygame.draw.line(surf, yel_hi, P(0.5, 0.95), P(1.55, 1.92), max(1, int(0.03 * sc)))
    arm = [(1.6, 1.98), (1.86, 1.84), (2.72, 1.08), (2.58, 0.98)]
    _poly(surf, P, sc, arm, yel, (90, 62, 0), 0.025)
    for a, b in (((0.6, 0.62), (1.25, 1.55)), ((1.75, 2.02), (2.5, 1.32))):
        _tube(surf, P, sc, [a, b], 0.06, (160, 166, 176), hi=(230, 234, 240))
    bucket = [(2.52, 1.06), (2.92, 0.98), (2.98, 0.55), (2.7, 0.42), (2.42, 0.5), (2.6, 0.62), (2.72, 0.88)]
    _poly(surf, P, sc, bucket, steel, (30, 30, 34), 0.022)
    for i in range(3):
        pygame.draw.polygon(surf, (200, 204, 210), [P(2.47 + i * 0.09, 0.47), P(2.52 + i * 0.09, 0.45),
                                                    P(2.46 + i * 0.09, 0.36)])
    for c in ((0.62, 0.86), (1.7, 1.9), (2.62, 1.03)):
        pygame.draw.circle(surf, (50, 52, 58), P(*c), 0.07 * sc)
    pygame.draw.circle(surf, (255, 150, 30), P(0.0, 1.84), 0.07 * sc)                        # beacon


def _lkw(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    white, grey, blue, red = (246, 246, 248), (206, 210, 218), (30, 90, 200), (226, 40, 44)
    pygame.draw.rect(surf, (36, 36, 40), pygame.Rect(P(-2.5, 0.12), (5.0 * sc, 0.2 * sc)))         # chassis
    box = pygame.Rect(P(-2.58, 2.02), (3.52 * sc, 1.92 * sc))
    pygame.draw.rect(surf, grey, box, border_radius=int(0.06 * sc))
    pygame.draw.rect(surf, white, box.inflate(-0.12 * sc, -0.12 * sc), border_radius=int(0.05 * sc))
    for i in range(1, 7):
        x = -2.58 + i * 0.5
        pygame.draw.line(surf, grey, P(x, 1.92), P(x, 0.2), max(1, int(0.015 * sc)))
    pygame.draw.rect(surf, OUTLINE, box, max(1, int(0.022 * sc)), border_radius=int(0.06 * sc))
    t = gfx.font_px("black_i", 0.46 * sc).render("BRUH", True, red)
    surf.blit(t, t.get_rect(center=P(-0.9, 1.25)))
    t = gfx.font_px("heavy", 0.22 * sc).render("GAMES  LOGISTIK", True, blue)
    surf.blit(t, t.get_rect(center=P(-0.9, 0.82)))
    # the cab
    cab = [(1.0, 0.0), (1.02, 1.6), (2.35, 1.62), (2.5, 1.4), (2.6, 0.9), (2.62, 0.0), (2.5, -0.2), (1.1, -0.2)]
    _poly(surf, P, sc, cab, white, OUTLINE, 0.022)
    pygame.draw.polygon(surf, blue, [P(1.02, 0.42), P(2.62, 0.42), P(2.62, 0.3), P(1.02, 0.3)])
    _glass(surf, P, sc, [(1.2, 0.95), (1.2, 1.48), (2.28, 1.5), (2.42, 0.95)], (40, 60, 90, 150))
    pygame.draw.line(surf, white, P(1.85, 0.95), P(1.85, 1.49), max(1, int(0.05 * sc)))
    pygame.draw.line(surf, grey, P(1.85, 0.9), P(1.85, -0.1), max(1, int(0.015 * sc)))       # door seam
    pygame.draw.rect(surf, (40, 40, 46), pygame.Rect(P(2.52, 0.75), (0.12 * sc, 0.45 * sc)))  # grille
    pygame.draw.rect(surf, (255, 250, 220), pygame.Rect(P(2.5, 0.12), (0.12 * sc, 0.12 * sc)))
    _tube(surf, P, sc, [(2.5, 1.35), (2.7, 1.35), (2.7, 1.0)], 0.035, (40, 40, 46))            # mirror arm
    pygame.draw.rect(surf, (40, 40, 46), pygame.Rect(P(2.64, 1.12), (0.1 * sc, 0.24 * sc)))
    _tube(surf, P, sc, [(0.95, 1.6), (0.95, 2.18)], 0.07, (150, 154, 162))                    # exhaust stack
    _arches(surf, P, sc, (-1.6, 1.75), -0.66, 0.62)
    pygame.draw.rect(surf, (230, 30, 30), pygame.Rect(P(-2.62, 0.4), (0.08 * sc, 0.2 * sc)))


def _golf(surf, k, ppm):
    """VW Golf 4 GTI, three-door: round roof, the thick C-pillar, twin round lamps under a clear lens."""
    P, sc = _mapper(surf, ppm, k)
    silver, silver_dk, silver_hi = (178, 184, 192), (120, 126, 136), (224, 228, 234)
    body = [(-2.0, -0.24), (-2.04, 0.12), (-1.98, 0.5), (-1.86, 0.78), (-1.62, 0.94), (-1.0, 0.99), (-0.2, 0.96),
            (0.28, 0.86), (0.86, 0.5), (1.5, 0.38), (1.92, 0.3), (2.06, 0.14), (2.08, -0.08), (1.96, -0.28),
            (1.6, -0.34), (-1.72, -0.34)]
    from drivers import spline
    body = spline(body, steps=4)
    pygame.draw.polygon(surf, silver, [P(*p) for p in body])
    pygame.draw.polygon(surf, silver_dk, [P(-2.02, -0.04), P(2.08, -0.04), P(2.08, -0.08), P(1.96, -0.28),
                                          P(1.6, -0.34), P(-1.72, -0.34), P(-2.0, -0.24)])
    pygame.draw.line(surf, silver_hi, P(-1.8, 0.47), P(1.55, 0.4), max(1, int(0.035 * sc)))      # shoulder line
    pygame.draw.rect(surf, (44, 46, 52), pygame.Rect(P(-1.75, 0.08), (3.6 * sc, 0.07 * sc)))     # rubbing strip
    _arches(surf, P, sc, (-1.28, 1.32), -0.22, 0.42)
    # windows: long door glass, a small rear quarter, then the fat C-pillar
    _glass(surf, P, sc, [(-0.62, 0.52), (-0.6, 0.9), (-0.2, 0.9), (0.24, 0.82), (0.74, 0.52)], (34, 44, 60, 170))
    _glass(surf, P, sc, [(-1.22, 0.55), (-1.12, 0.88), (-0.72, 0.9), (-0.72, 0.55)], (34, 44, 60, 170))
    pygame.draw.line(surf, (40, 42, 48), P(-0.66, 0.52), P(-0.66, 0.92), max(1, int(0.04 * sc)))  # B pillar
    pygame.draw.line(surf, silver_dk, P(0.72, 0.48), P(0.7, -0.22), max(1, int(0.015 * sc)))       # door seams
    pygame.draw.line(surf, silver_dk, P(-0.72, 0.5), P(-0.7, -0.22), max(1, int(0.015 * sc)))
    pygame.draw.rect(surf, silver_dk, pygame.Rect(P(-0.5, 0.36), (0.22 * sc, 0.045 * sc)), border_radius=int(0.02 * sc))
    _poly(surf, P, sc, [(0.42, 0.56), (0.62, 0.62), (0.62, 0.5), (0.44, 0.48)], (40, 42, 48), None)    # mirror
    # stock roof spoiler on the hatch
    _poly(surf, P, sc, [(-1.62, 0.94), (-1.98, 0.86), (-1.94, 0.8), (-1.6, 0.88)], silver_dk, OUTLINE, 0.012)
    pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], max(1, int(0.022 * sc)))
    # twin round headlamps under one clear lens, honeycomb grille, red GTI badge
    pygame.draw.polygon(surf, (225, 232, 240), [P(1.66, 0.36), P(2.0, 0.27), P(2.04, 0.13), P(1.7, 0.18)])
    for x in (1.78, 1.92):
        pygame.draw.circle(surf, (250, 250, 236), P(x, 0.24), 0.055 * sc)
    pygame.draw.rect(surf, (36, 36, 40), pygame.Rect(P(1.98, 0.12), (0.1 * sc, 0.12 * sc)))
    pygame.draw.polygon(surf, (200, 30, 36), [P(-2.03, 0.5), P(-1.94, 0.5), P(-1.98, 0.2), P(-2.04, 0.2)])  # tail lamp
    t = gfx.font_px("black_i", 0.17 * sc).render("GTI", True, (210, 24, 30))
    surf.blit(t, t.get_rect(center=P(1.1, 0.24)))
    pygame.draw.circle(surf, CHROME, P(-1.98, -0.2), 0.045 * sc)                                      # tailpipe


def _tank(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    olive, olive_dk, olive_hi = (98, 114, 62), (66, 78, 42), (130, 146, 86)
    _tube(surf, P, sc, [(-1.7, 0.4), (-1.95, 1.5)], 0.025, (40, 40, 44))          # antenna
    pygame.draw.rect(surf, (60, 60, 64), pygame.Rect(P(-2.2, 0.35), (0.3 * sc, 0.12 * sc)), border_radius=int(0.03 * sc))
    _poly(surf, P, sc, [(-2.0, -0.05), (-1.8, 0.4), (1.85, 0.4), (2.12, 0.02), (1.92, -0.16), (-1.9, -0.16)],
          olive, (34, 40, 22), 0.03)
    pygame.draw.rect(surf, olive_dk, pygame.Rect(P(-2.08, 0.06), (4.22 * sc, 0.12 * sc)))
    pygame.draw.line(surf, olive_hi, P(-1.75, 0.36), P(1.8, 0.36), max(1, int(0.04 * sc)))
    # gun barrel, turret, hatch
    pygame.draw.rect(surf, olive_dk, pygame.Rect(P(0.9, 0.82), (2.0 * sc, 0.13 * sc)))
    pygame.draw.rect(surf, (52, 60, 34), pygame.Rect(P(2.72, 0.86), (0.2 * sc, 0.21 * sc)), border_radius=int(0.03 * sc))
    _poly(surf, P, sc, [(-1.15, 0.4), (-1.0, 0.92), (0.7, 0.98), (1.08, 0.46)], olive, (34, 40, 22), 0.03)
    pygame.draw.line(surf, olive_hi, P(-0.9, 0.88), P(0.6, 0.93), max(1, int(0.04 * sc)))
    star = [(0.15 + 0.16 * math.cos(math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else 0.42),
             0.66 + 0.16 * math.sin(math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else 0.42)) for i in range(10)]
    pygame.draw.polygon(surf, (245, 245, 235), [P(*p) for p in star])
    pygame.draw.rect(surf, (40, 44, 26), pygame.Rect(P(-0.65, 1.02), (0.6 * sc, 0.09 * sc)), border_radius=int(0.03 * sc))
    _limb(surf, P, sc, (-0.35, 0.98), (-0.35, 1.12), 0.36, (86, 98, 56))       # commander's shoulders


def _police(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    white, black = (246, 246, 248), (30, 32, 38)
    body = [(-2.05, -0.25), (-2.05, 0.32), (-1.45, 0.42), (-0.95, 0.95), (0.38, 0.98), (0.95, 0.45), (1.95, 0.36),
            (2.08, 0.1), (2.02, -0.28), (1.6, -0.35), (-1.7, -0.35)]
    pygame.draw.polygon(surf, black, [P(*p) for p in body])
    pygame.draw.polygon(surf, white, [P(-1.2, 0.42), (P(1.0, 0.42)), P(1.0, -0.12), P(-1.2, -0.12)])
    pygame.draw.polygon(surf, (40, 90, 200), [P(-1.2, -0.02), P(1.0, -0.02), P(1.0, -0.1), P(-1.2, -0.1)])
    t = gfx.font_px("heavy", 0.24 * sc).render("POLICE", True, (30, 60, 150))
    surf.blit(t, t.get_rect(center=P(-0.1, 0.18)))
    for x in (-1.25, 1.3):
        _cut(surf, P, sc, (x, -0.38), 0.46)
        ring_arc(surf, (20, 20, 24), P(x, -0.38), 0.49 * sc, 0.45 * sc, math.radians(5), math.radians(175))
    glass = [P(-1.38, 0.44), P(-0.9, 0.9), P(0.33, 0.92), P(0.86, 0.46)]
    pygame.draw.polygon(surf, (60, 80, 110, 140), glass)
    pygame.draw.line(surf, black, P(-0.25, 0.44), P(-0.25, 0.92), max(1, int(0.06 * sc)))
    pygame.draw.polygon(surf, OUTLINE, [P(*p) for p in body], max(1, int(0.025 * sc)))
    pygame.draw.rect(surf, (40, 40, 46), pygame.Rect(P(-0.75, 1.1), (0.85 * sc, 0.12 * sc)), border_radius=int(0.04 * sc))
    pygame.draw.polygon(surf, (255, 255, 240), [P(1.86, 0.2), P(2.04, 0.14), P(2.02, 0.06), P(1.86, 0.1)])
    pygame.draw.rect(surf, (230, 30, 30), pygame.Rect(P(-2.07, 0.26), (0.08 * sc, 0.16 * sc)))


def _hoverboard(surf, k, ppm):
    P, sc = _mapper(surf, ppm, k)
    jacket, jeans = (226, 64, 52), (50, 82, 150)
    board = [(-0.95, 0.0), (-0.8, 0.1), (0.8, 0.1), (0.95, 0.0), (0.8, -0.1), (-0.8, -0.1)]
    _poly(surf, P, sc, board, (250, 96, 170), (90, 20, 60), 0.025)
    pygame.draw.line(surf, (180, 240, 80), P(-0.7, 0.02), P(0.7, 0.02), max(1, int(0.04 * sc)))
    for x in (-0.55, 0.55):
        pygame.draw.ellipse(surf, (50, 50, 60), pygame.Rect(P(x - 0.2, -0.06), (0.4 * sc, 0.12 * sc)))
        pygame.draw.ellipse(surf, (120, 240, 255), pygame.Rect(P(x - 0.14, -0.1), (0.28 * sc, 0.05 * sc)))
    _limb(surf, P, sc, (-0.22, 0.1), (-0.12, 0.5), 0.13, jeans)
    _limb(surf, P, sc, (-0.12, 0.5), (0.0, 0.88), 0.15, jeans)
    _limb(surf, P, sc, (0.28, 0.1), (0.2, 0.5), 0.13, jeans)
    _limb(surf, P, sc, (0.2, 0.5), (0.05, 0.88), 0.15, jeans)
    for x in (-0.24, 0.3):
        pygame.draw.ellipse(surf, (240, 240, 240), pygame.Rect(P(x - 0.1, 0.16), (0.24 * sc, 0.1 * sc)))
    _limb(surf, P, sc, (0.0, 0.86), (0.05, 1.5), 0.32, jacket)
    _limb(surf, P, sc, (0.0, 1.42), (-0.4, 1.2), 0.1, jacket)
    _limb(surf, P, sc, (-0.4, 1.2), (-0.62, 1.06), 0.09, jacket)
    _limb(surf, P, sc, (0.1, 1.42), (0.45, 1.3), 0.1, jacket)
    _limb(surf, P, sc, (0.45, 1.3), (0.68, 1.36), 0.09, jacket)
    for hx, hy in ((-0.64, 1.04), (0.7, 1.37)):
        pygame.draw.circle(surf, (236, 190, 150), P(hx, hy), 0.055 * sc)


def _shark(surf, k, ppm, stage=2):
    """The shark (without its tail fin, which beats in render) and its rider (without the head).

    stage 0 is a chubby baby shark with big cute eyes; every stage it grows and gets meaner,
    up to stage 4: huge, scarred, jaws open full of teeth. Same colours all the way.
    """
    P0, sc = _mapper(surf, ppm, k)
    size = (0.7, 0.84, 1.0, 1.14, 1.3)[stage]
    chub = (1.18, 1.08, 1.0, 1.0, 1.04)[stage]

    def P(x, y):                                  # the shark grows around a point under the rider's seat
        return P0(x * size, 0.1 + (y - 0.1) * size * chub)
    top, belly, dark, line = (96, 118, 140), (236, 240, 244), (60, 76, 94), (30, 40, 52)
    fin = [(-0.2, 0.45), (0.25, 1.15), (0.6, 0.45)]
    if stage == 4:                                # a bite taken out of the fin
        fin = [(-0.2, 0.45), (0.12, 0.9), (0.2, 0.85), (0.28, 1.18), (0.6, 0.45)]
    pygame.draw.polygon(surf, dark, [P(*p) for p in fin])
    pygame.draw.polygon(surf, line, [P(*p) for p in fin], max(1, int(0.02 * sc)))
    body = [(-1.75, 0.08), (-1.2, 0.38), (-0.2, 0.55), (0.9, 0.48), (1.6, 0.28), (2.0, 0.02), (1.7, -0.18),
            (0.8, -0.32), (-0.4, -0.3), (-1.4, -0.12)]
    from drivers import spline
    body = spline(body, steps=6)
    pygame.draw.polygon(surf, top, [P(*p) for p in body])
    pygame.draw.polygon(surf, line, [P(*p) for p in body], max(1, int(0.022 * sc)))
    under = [(-1.6, 0.0), (-0.4, -0.08), (0.8, -0.08), (1.75, 0.0), (1.7, -0.18), (0.8, -0.32), (-0.4, -0.3),
             (-1.4, -0.12)]
    pygame.draw.polygon(surf, belly, [P(*p) for p in spline(under, steps=6)])
    pec = [(0.4, -0.15), (0.0, -0.62), (0.75, -0.2)]
    pygame.draw.polygon(surf, dark, [P(*p) for p in pec])
    pygame.draw.polygon(surf, line, [P(*p) for p in pec], max(1, int(0.02 * sc)))
    for x in (1.0, 1.1, 1.2)[:2 + (stage >= 2)]:                                                # gills
        pygame.draw.line(surf, dark, P(x, 0.25), P(x - 0.06, -0.02), max(1, int(0.03 * sc)))
    lw = max(1, int(0.03 * sc))
    if stage >= 3:                                                                              # scars
        for (ax, ay), (bx, by) in (((-0.6, 0.42), (-0.25, 0.18)), ((-0.45, 0.45), (-0.12, 0.24)))[:stage - 2]:
            pygame.draw.line(surf, belly, P(ax, ay), P(bx, by), max(1, int(0.035 * sc)))
            for f in (0.3, 0.6):
                mx, my = ax + (bx - ax) * f, ay + (by - ay) * f
                pygame.draw.line(surf, belly, P(mx - 0.05, my - 0.06), P(mx + 0.05, my + 0.06), lw)
    # eyes: huge and shiny when little, small and mean when grown
    ex, ey = P(1.48, 0.17)
    if stage <= 1:
        r = (0.2, 0.14)[stage] * sc
        pygame.draw.circle(surf, (255, 255, 255), (ex, ey), r)
        pygame.draw.circle(surf, line, (ex, ey), r, lw)
        pygame.draw.circle(surf, (20, 20, 24), (ex + r * 0.15, ey + r * 0.05), r * 0.68)
        pygame.draw.circle(surf, (255, 255, 255), (ex + r * 0.32, ey - r * 0.25), r * 0.26)
        pygame.draw.circle(surf, (255, 255, 255), (ex - r * 0.1, ey + r * 0.3), r * 0.12)
        for i in range(3):                                                                      # lashes
            a = math.radians(70 + i * 25)
            pygame.draw.line(surf, (20, 20, 24), (ex + math.cos(a) * r, ey - math.sin(a) * r),
                             (ex + math.cos(a) * r * 1.35, ey - math.sin(a) * r * 1.35), lw)
    else:
        r = (0.0, 0.0, 0.06, 0.055, 0.05)[stage] * sc
        pygame.draw.circle(surf, (20, 20, 24), (ex, ey), r)
        pygame.draw.circle(surf, (255, 255, 255), (ex + r * 0.3, ey - r * 0.3), r * 0.35)
        if stage >= 3:                                                                          # angry brow
            pygame.draw.line(surf, line, P(1.36, 0.3), P(1.6, 0.22), max(2, int(0.05 * sc)))
    # mouth
    if stage == 0:                                                                              # a little smile
        pygame.draw.arc(surf, (30, 30, 36), pygame.Rect(P(1.58, 0.02), (0.24 * sc * size, 0.14 * sc * size)),
                        math.pi * 1.1, math.pi * 1.9, lw)
    elif stage < 4:
        mouth = [(1.35, -0.06), (1.65, -0.1), (1.92, -0.02)]
        pygame.draw.lines(surf, (30, 30, 36), False, [P(*p) for p in mouth], lw)
        n, tooth = (3, 5, 7)[stage - 1], (0.06, 0.08, 0.1)[stage - 1]
        for i in range(n):
            x = 1.4 + i * 0.5 / n
            pygame.draw.polygon(surf, (255, 255, 255), [P(x, -0.07), P(x + 0.05, -0.07), P(x + 0.025, -0.07 - tooth)])
    else:                                                                                       # jaws wide open
        jaw = [(1.25, -0.02), (1.98, 0.06), (1.85, -0.3), (1.35, -0.16)]
        pygame.draw.polygon(surf, (40, 26, 30), [P(*p) for p in jaw])
        for i in range(8):
            x = 1.32 + i * 0.08
            y_top = -0.02 + (x - 1.25) * 0.11
            pygame.draw.polygon(surf, (255, 255, 255), [P(x, y_top), P(x + 0.06, y_top + 0.01), P(x + 0.03, y_top - 0.13)])
            y_bot = -0.16 - (x - 1.35) * 0.28
            pygame.draw.polygon(surf, (255, 255, 255), [P(x, y_bot), P(x + 0.06, y_bot), P(x + 0.03, y_bot + 0.12)])
    # rider astride (always the same size), hand on the fin wherever its tip ends up
    Q = P0
    pants, jacket, boot = (40, 50, 70), (230, 110, 40), (30, 22, 18)
    hand = (0.25 * size + 0.05, 0.1 + 0.62 * size * chub)
    _limb(surf, Q, sc, (-0.35, 0.72), (-0.1, 0.42), 0.15, pants)
    _limb(surf, Q, sc, (-0.1, 0.42), (-0.25, 0.12), 0.12, boot)
    _limb(surf, Q, sc, (-0.35, 0.72), (-0.28, 1.0), 0.3, jacket)
    _limb(surf, Q, sc, (-0.2, 0.95), ((hand[0] - 0.2) / 2, (0.95 + hand[1]) / 2 + 0.05), 0.1, jacket)
    _limb(surf, Q, sc, ((hand[0] - 0.2) / 2, (0.95 + hand[1]) / 2 + 0.05), hand, 0.09, jacket)
    pygame.draw.circle(surf, (236, 190, 150), Q(*hand), 0.05 * sc)


BODIES = {"dirtbike": _dirtbike, "chopper": _chopper, "monster": _monster, "supercar": _supercar,
          "tank": _tank, "police": _police, "hoverboard": _hoverboard, "tesla": _tesla, "mini": _mini, "b2": _b2,
          "excavator": _excavator, "lkw": _lkw, "golf": _golf, "shark": _shark}


def body(key, ppm, stage=2):
    """stage: only the shark has stages (it grows with its upgrades)."""
    if key == "jeep":
        return car_body(ppm)
    size = 2 * EXTENT[key] * ppm
    if key == "shark":
        return gfx.supersample(size, size, lambda s, k: _shark(s, k, ppm, stage))
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
                "helmet_green": ((96, 112, 60), (60, 70, 36), (36, 46, 40)),
                "police": ((32, 44, 90), (240, 200, 60), (36, 46, 70)),
                "racer": ((32, 32, 36), (255, 198, 22), (60, 90, 140)),
                "hardhat": ((255, 196, 20), (232, 150, 0), (36, 46, 70)),
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
        elif style == "sprocket":
            pygame.draw.circle(surf, (58, 62, 52), P(0, 0), R * sc)
            for i in range(10):
                a = i * math.tau / 10
                pygame.draw.circle(surf, (40, 42, 36), P(math.cos(a) * R * 0.92, math.sin(a) * R * 0.92), 0.06 * sc)
            pygame.draw.circle(surf, (96, 100, 86), P(0, 0), R * 0.62 * sc)
            pygame.draw.circle(surf, (64, 68, 58), P(0, 0), R * 0.25 * sc)
            for i in range(4):
                a = i * math.tau / 4
                pygame.draw.circle(surf, (64, 68, 58), P(math.cos(a) * R * 0.42, math.sin(a) * R * 0.42), 0.04 * sc)
        elif style == "aero":                       # Tesla-style aero cover
            pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
            pygame.draw.circle(surf, (58, 60, 66), P(0, 0), (R - 0.06) * sc)
            for i in range(5):
                a = i * math.tau / 5
                pygame.draw.arc(surf, (150, 154, 162), pygame.Rect(P(-(R - 0.1), R - 0.1), (2 * (R - 0.1) * sc,) * 2),
                                a, a + 0.7, max(1, int(0.04 * sc)))
            pygame.draw.circle(surf, (110, 114, 122), P(0, 0), (R - 0.2) * sc)
            pygame.draw.circle(surf, (210, 212, 218), P(0, 0), 0.06 * sc)
        elif style == "mini":                       # small silver spokes
            pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
            pygame.draw.circle(surf, (190, 194, 202), P(0, 0), (R - 0.08) * sc)
            for i in range(8):
                a = i * math.tau / 8
                pygame.draw.line(surf, (110, 114, 122), P(0, 0), P(math.cos(a) * (R - 0.09), math.sin(a) * (R - 0.09)),
                                 max(1, int(0.03 * sc)))
            pygame.draw.circle(surf, CHROME, P(0, 0), 0.06 * sc)
        elif style == "truck":                      # steel rim with lug nuts
            pygame.draw.circle(surf, TYRE, P(0, 0), R * sc)
            pygame.draw.circle(surf, (40, 40, 44), P(0, 0), (R - 0.05) * sc, max(1, int(0.02 * sc)))
            pygame.draw.circle(surf, (170, 174, 182), P(0, 0), (R - 0.17) * sc)
            pygame.draw.circle(surf, (120, 124, 132), P(0, 0), (R - 0.27) * sc)
            for i in range(10):
                a = i * math.tau / 10
                pygame.draw.circle(surf, (230, 232, 236), P(math.cos(a) * (R - 0.22), math.sin(a) * (R - 0.22)),
                                   0.025 * sc)
            pygame.draw.circle(surf, (80, 84, 92), P(0, 0), 0.07 * sc)
        elif style == "none":
            pass
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
