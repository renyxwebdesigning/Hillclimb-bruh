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
    "lamp": (1.4, 3.4), "car": (3.8, 1.6), "hydrant": (0.7, 0.9), "cone": (0.6, 0.7), "bin": (0.8, 1.0),
    "sign": (1.0, 2.4), "deadtree": (2.4, 3.2), "lavarock": (1.6, 1.0), "vent": (1.8, 1.2), "palm": (3.0, 5.0),
    "fern": (1.8, 1.1), "bigflower": (1.4, 1.6), "mushroom": (1.0, 1.0), "marsrock": (1.7, 1.0), "rover": (2.6, 1.8),
    # more roadside things
    "haybale": (1.6, 1.2), "sunflower": (0.9, 2.1), "mailbox": (0.7, 1.3), "tumbleweed": (1.1, 0.9),
    "barrel": (0.8, 1.1), "penguin": (0.8, 1.0), "icerock": (1.7, 1.2), "satellite": (1.8, 1.8), "bench": (1.7, 0.9),
    "trafficlight": (0.7, 3.4), "bones": (1.3, 0.5), "warnsign": (1.1, 1.9), "bamboo": (1.3, 4.2), "totem": (0.9, 2.5),
    "solarpanel": (1.9, 1.1), "antenna": (0.9, 3.0),
    # the four seasons
    "blossom": (3.3, 4.5), "tulips": (1.4, 0.6), "autumntree": (3.3, 4.6), "pumpkin": (1.0, 0.65),
    "scarecrow": (1.5, 2.5), "leafpile": (1.5, 0.5), "snowpine": (2.4, 4.4),
    # landmarks: big set pieces every few hundred metres
    "windmill": (4.4, 9.5), "barn": (6.4, 5.4), "pyramid": (11.0, 7.2), "pumpjack": (5.6, 4.2), "igloo": (3.6, 2.2),
    "lander": (3.8, 3.8), "billboard": (6.6, 5.4), "hut": (3.8, 3.2), "temple": (8.0, 6.4), "dome": (6.6, 4.4),
    "launchpad": (3.6, 8.6),
    # underwater
    "coral": (1.8, 1.7), "seaweed": (1.2, 3.2), "anemone": (1.2, 0.9), "shell": (0.7, 0.45), "starfish": (0.8, 0.3),
    "treasure": (1.3, 1.0), "shipwreck": (9.0, 6.0),
}
# landmarks with moving parts (render.WorldRenderer animates them) or lights
LANDMARKS = {"windmill", "barn", "pyramid", "pumpjack", "igloo", "lander", "billboard", "hut", "temple", "dome",
             "launchpad", "shipwreck"}
LIGHTS = {"lamp": (0.42, 3.15), "billboard": (0.0, 5.0), "trafficlight": (0.0, 2.9)}  # glow at night: (x, y) of the light


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
        elif kind == "lamp":
            line((70, 74, 80), (0, 0), (0, 3.1), 0.12)
            line((70, 74, 80), (0, 3.1), (0.45, 3.2), 0.08)
            poly((50, 52, 58), [(0.25, 3.25), (0.62, 3.25), (0.55, 3.08), (0.3, 3.08)])
            circ((255, 240, 180), 0.42, 3.08, 0.08)
            poly((50, 52, 58), [(-0.18, 0), (0.18, 0), (0.1, 0.3), (-0.1, 0.3)])
        elif kind == "car":
            body = rnd.choice(((200, 50, 50), (60, 110, 200), (240, 200, 60), (80, 160, 90), (230, 230, 230)))
            poly(gfx.shade(body, 0.7), [(-1.85, 0.3), (1.85, 0.3), (1.85, 0.75), (1.0, 0.85), (0.55, 1.4), (-0.9, 1.4),
                                         (-1.4, 0.85), (-1.85, 0.8)])
            poly(body, [(-1.8, 0.35), (1.8, 0.35), (1.8, 0.72), (0.98, 0.8), (0.52, 1.34), (-0.86, 1.34), (-1.36, 0.8),
                        (-1.8, 0.76)])
            poly((150, 200, 230), [(-0.75, 0.86), (-0.1, 0.86), (-0.1, 1.26), (-0.62, 1.26)])
            poly((150, 200, 230), [(0.02, 0.86), (0.82, 0.86), (0.46, 1.26), (0.02, 1.26)])
            for x in (-1.15, 1.15):
                circ((30, 30, 34), x, 0.32, 0.32)
                circ((170, 174, 182), x, 0.32, 0.14)
            circ((255, 240, 180), 1.75, 0.6, 0.07)
        elif kind == "hydrant":
            poly((200, 40, 40), [(-0.2, 0), (0.2, 0), (0.18, 0.7), (-0.18, 0.7)])
            circ((200, 40, 40), 0, 0.72, 0.2)
            poly((160, 30, 30), [(-0.32, 0.38), (0.32, 0.38), (0.32, 0.5), (-0.32, 0.5)])
        elif kind == "cone":
            poly((255, 120, 30), [(-0.22, 0.05), (0.22, 0.05), (0.04, 0.65), (-0.04, 0.65)])
            poly((250, 250, 250), [(-0.15, 0.28), (0.15, 0.28), (0.11, 0.4), (-0.11, 0.4)])
            poly((60, 60, 64), [(-0.28, 0), (0.28, 0), (0.28, 0.06), (-0.28, 0.06)])
        elif kind == "bin":
            poly((70, 110, 80), [(-0.32, 0), (0.32, 0), (0.36, 0.85), (-0.36, 0.85)])
            poly((50, 80, 60), [(-0.4, 0.85), (0.4, 0.85), (0.36, 0.95), (-0.36, 0.95)])
        elif kind == "sign":
            line((150, 154, 162), (0, 0), (0, 2.2), 0.08)
            poly((40, 110, 200), [(-0.45, 1.6), (0.45, 1.6), (0.45, 2.25), (-0.45, 2.25)])
            poly((250, 250, 250), [(-0.32, 1.8), (0.2, 1.8), (0.2, 1.72), (0.36, 1.92), (0.2, 2.12), (0.2, 2.04),
                                   (-0.32, 2.04)])
        elif kind == "deadtree":
            col = (52, 40, 36)
            line(col, (0, 0), (0.1, 2.0), 0.24)
            for a, L, y0 in ((-0.9, 1.0, 1.2), (0.8, 0.9, 1.6), (-0.4, 0.8, 2.0), (0.5, 0.7, 2.4)):
                line(col, (0.05, y0), (0.05 + a, y0 + L), 0.09)
        elif kind == "lavarock":
            pts = [(-0.75, 0), (-0.6, 0.5), (-0.2, 0.9), (0.3, 0.85), (0.7, 0.4), (0.78, 0)]
            poly((40, 34, 36), pts)
            for a, b in (((-0.4, 0.2), (-0.1, 0.6)), ((0.1, 0.1), (0.35, 0.55)), ((-0.1, 0.6), (0.2, 0.75))):
                line((255, 120, 30), a, b, 0.05)
        elif kind == "vent":
            poly((70, 60, 62), [(-0.85, 0), (-0.3, 0.9), (0.3, 0.9), (0.85, 0)])
            poly((255, 140, 40), [(-0.25, 0.86), (0.25, 0.86), (0.18, 0.95), (-0.18, 0.95)])
            for i in range(4):
                circ((120, 110, 110, 160), -0.1 + i * 0.12, 1.0 + i * 0.05, 0.12 + i * 0.02)
        elif kind == "palm":
            trunk = (130, 96, 60)
            pts = [(0, 0), (0.25, 1.5), (0.5, 3.2), (0.55, 4.1)]
            for a, b in zip(pts, pts[1:]):
                line(trunk, a, b, 0.24)
            for i in range(9):
                line(gfx.shade(trunk, 0.8), (0.04 * i, 0.45 * i), (0.04 * i + 0.22, 0.45 * i), 0.04)
            for ang, L in ((-2.6, 1.6), (-1.9, 1.7), (-0.6, 1.7), (0.1, 1.5), (-1.3, 1.3), (2.8, 1.2)):
                tip = (0.55 + math.cos(ang) * L, 4.1 + math.sin(ang) * L * 0.55)
                mid = (0.55 + math.cos(ang) * L * 0.5, 4.1 + math.sin(ang) * L * 0.35 + 0.3)
                poly((46, 130, 50), [(0.55, 4.15), mid, tip, (mid[0], mid[1] - 0.25)])
            circ((110, 76, 40), 0.5, 3.95, 0.14)
        elif kind == "fern":
            for ang in (-2.4, -1.9, -1.2, -0.7):
                a = (0, 0)
                b = (math.cos(ang) * -0.9, -math.sin(ang) * 1.0)
                line((40, 120, 50), a, b, 0.07)
                for k in range(1, 6):
                    f = k / 6
                    px, py = b[0] * f, b[1] * f
                    line((70, 160, 70), (px, py), (px + 0.18, py + 0.12), 0.05)
                    line((70, 160, 70), (px, py), (px - 0.18, py + 0.12), 0.05)
        elif kind == "bigflower":
            line((50, 130, 60), (0, 0), (0.1, 1.1), 0.09)
            for a in range(6):
                ang = a * math.tau / 6
                circ((240, 70, 120), 0.1 + math.cos(ang) * 0.32, 1.15 + math.sin(ang) * 0.32, 0.24)
            circ((255, 210, 60), 0.1, 1.15, 0.16)
        elif kind == "mushroom":
            poly((240, 230, 210), [(-0.12, 0), (0.12, 0), (0.1, 0.5), (-0.1, 0.5)])
            pygame.draw.ellipse(surf, (220, 50, 50), pygame.Rect(P(-0.45, 0.85), (0.9 * sc, 0.5 * sc)))
            for x, y in ((-0.2, 0.7), (0.15, 0.75), (0.0, 0.62)):
                circ((255, 255, 255), x, y, 0.06)
        elif kind == "marsrock":
            base = (150, 72, 44)
            pts = [(-0.8, 0), (-0.62, 0.48), (-0.2, 0.86), (0.25, 0.9), (0.66, 0.5), (0.8, 0)]
            poly(gfx.shade(base, 0.75), pts)
            poly(base, [(x * 0.9, y * 0.93) for x, y in pts])
            poly(gfx.shade(base, 1.3), [(-0.4, 0.45), (-0.2, 0.72), (0.15, 0.76), (-0.05, 0.5)])
        elif kind == "rover":
            for x in (-0.9, 0.0, 0.9):
                circ((60, 60, 66), x, 0.25, 0.25)
                circ((140, 140, 150), x, 0.25, 0.1)
            poly((220, 220, 226), [(-1.1, 0.45), (1.1, 0.45), (1.1, 0.85), (-1.1, 0.85)])
            poly((60, 70, 120), [(-1.25, 0.88), (0.2, 0.88), (0.2, 0.95), (-1.25, 0.95)])
            line((150, 150, 160), (0.6, 0.85), (0.7, 1.55), 0.06)
            poly((230, 230, 236), [(0.5, 1.5), (0.95, 1.5), (0.95, 1.72), (0.5, 1.72)])
            circ((40, 40, 50), 0.82, 1.61, 0.07)
        elif kind == "haybale":
            poly((196, 160, 70), [(-0.78, 0), (0.78, 0), (0.78, 1.1), (-0.78, 1.1)])
            for y in (0.25, 0.55, 0.85):
                line((226, 196, 104), (-0.72, y), (0.72, y + 0.03), 0.04)
            line((120, 90, 40), (-0.3, 0), (-0.3, 1.1), 0.05)
            line((120, 90, 40), (0.3, 0), (0.3, 1.1), 0.05)
        elif kind == "sunflower":
            line((60, 130, 50), (0, 0), (0.05, 1.7), 0.08)
            poly((60, 140, 50), [(0.03, 0.8), (0.4, 1.0), (0.05, 0.95)])
            for a in range(12):
                ang = a * math.tau / 12
                circ((255, 200, 30), 0.05 + math.cos(ang) * 0.27, 1.75 + math.sin(ang) * 0.27, 0.12)
            circ((110, 70, 30), 0.05, 1.75, 0.2)
        elif kind == "mailbox":
            line((110, 80, 50), (0, 0), (0, 0.9), 0.1)
            pygame.draw.rect(surf, (40, 90, 170), pygame.Rect(P(-0.3, 1.25), (0.6 * sc, 0.38 * sc)),
                             border_top_left_radius=int(0.18 * sc), border_top_right_radius=int(0.18 * sc))
            line((220, 40, 40), (0.25, 1.05), (0.25, 1.35), 0.05)
        elif kind == "tumbleweed":
            for i in range(14):
                a = rnd.uniform(0, math.tau)
                r0 = rnd.uniform(0.15, 0.45)
                line((150, 110, 60), (math.cos(a) * r0, 0.45 + math.sin(a) * r0),
                     (math.cos(a + 1.6) * 0.45, 0.45 + math.sin(a + 1.6) * 0.42), 0.035)
        elif kind == "barrel":
            poly((150, 50, 40), [(-0.35, 0), (0.35, 0), (0.38, 1.0), (-0.38, 1.0)])
            for y in (0.2, 0.8):
                line((90, 30, 24), (-0.37, y), (0.37, y), 0.06)
            poly((255, 210, 40), [(-0.12, 0.42), (0.12, 0.42), (0.0, 0.62)])
        elif kind == "penguin":
            pygame.draw.ellipse(surf, (30, 32, 40), pygame.Rect(P(-0.3, 0.95), (0.6 * sc, 0.95 * sc)))
            pygame.draw.ellipse(surf, (250, 250, 250), pygame.Rect(P(-0.16, 0.78), (0.36 * sc, 0.7 * sc)))
            circ((30, 32, 40), 0.02, 0.92, 0.17)
            circ((255, 255, 255), 0.08, 0.95, 0.05)
            poly((255, 150, 30), [(0.16, 0.9), (0.34, 0.86), (0.16, 0.82)])
            poly((255, 150, 30), [(-0.2, 0.0), (0.0, 0.0), (-0.1, 0.06)])
            poly((255, 150, 30), [(0.04, 0.0), (0.24, 0.0), (0.14, 0.06)])
        elif kind == "icerock":
            pts = [(-0.85, 0), (-0.6, 0.8), (-0.1, 1.15), (0.5, 0.9), (0.85, 0)]
            poly((150, 200, 236), pts)
            poly((220, 240, 255), [(-0.6, 0.8), (-0.1, 1.15), (0.0, 0.5), (-0.4, 0.3)])
        elif kind == "satellite":
            line((150, 150, 160), (0, 0), (0, 0.9), 0.1)
            pygame.draw.rect(surf, (200, 200, 210), pygame.Rect(P(-0.25, 1.25), (0.5 * sc, 0.4 * sc)))
            for side in (-1, 1):
                pygame.draw.rect(surf, (40, 70, 150), pygame.Rect(P(side * 0.3 - (0.6 if side < 0 else 0), 1.2),
                                                                  (0.6 * sc, 0.3 * sc)))
            line((150, 150, 160), (0, 1.25), (0.0, 1.7), 0.04)
            circ((230, 60, 50), 0.0, 1.72, 0.05)
        elif kind == "bench":
            for x in (-0.65, 0.65):
                line((60, 60, 66), (x, 0), (x, 0.5), 0.07)
            poly((150, 96, 52), [(-0.82, 0.45), (0.82, 0.45), (0.82, 0.55), (-0.82, 0.55)])
            for y in (0.68, 0.82):
                poly((150, 96, 52), [(-0.82, y), (0.82, y), (0.82, y + 0.08), (-0.82, y + 0.08)])
        elif kind == "trafficlight":
            line((60, 62, 68), (0, 0), (0, 2.3), 0.12)
            pygame.draw.rect(surf, (40, 42, 46), pygame.Rect(P(-0.24, 3.3), (0.48 * sc, 1.1 * sc)),
                             border_radius=int(0.08 * sc))
            for i, col in enumerate(((90, 30, 30), (90, 80, 20), (40, 200, 70))):
                circ(col, 0, 3.1 - i * 0.34, 0.12)
        elif kind == "bones":
            for a, b in (((-0.5, 0.1), (0.4, 0.2)), ((-0.2, 0.05), (0.1, 0.35))):
                line((236, 230, 214), a, b, 0.07)
                circ((236, 230, 214), *a, 0.07)
                circ((236, 230, 214), *b, 0.07)
            circ((236, 230, 214), 0.5, 0.18, 0.15)
        elif kind == "warnsign":
            line((150, 154, 162), (0, 0), (0, 1.2), 0.07)
            poly((30, 30, 34), [(-0.5, 1.05), (0.5, 1.05), (0.0, 1.9)])
            poly((255, 200, 30), [(-0.42, 1.09), (0.42, 1.09), (0.0, 1.82)])
            line((30, 30, 34), (0.0, 1.32), (0.0, 1.58), 0.06)
            circ((30, 30, 34), 0.0, 1.22, 0.035)
        elif kind == "bamboo":
            for x, top in ((-0.35, 3.6), (0.0, 4.1), (0.35, 3.3)):
                line((120, 170, 60), (x, 0), (x + 0.05, top), 0.13)
                for y in range(1, int(top / 0.6)):
                    line((80, 130, 40), (x - 0.07, y * 0.6), (x + 0.12, y * 0.6), 0.04)
                poly((70, 150, 60), [(x, top), (x + 0.5, top - 0.2), (x + 0.1, top - 0.3)])
        elif kind == "totem":
            cols = ((180, 60, 40), (40, 120, 160), (230, 180, 40))
            for i, col in enumerate(cols):
                poly(col, [(-0.35, i * 0.75), (0.35, i * 0.75), (0.35, i * 0.75 + 0.72), (-0.35, i * 0.75 + 0.72)])
                circ((250, 250, 240), -0.12, i * 0.75 + 0.45, 0.07)
                circ((250, 250, 240), 0.12, i * 0.75 + 0.45, 0.07)
                line((30, 20, 20), (-0.15, i * 0.75 + 0.2), (0.15, i * 0.75 + 0.2), 0.05)
            poly((230, 180, 40), [(-0.45, 2.25), (0.45, 2.25), (0.0, 2.5)])
        elif kind == "solarpanel":
            line((150, 150, 160), (0, 0), (0, 0.5), 0.08)
            poly((30, 50, 110), [(-0.9, 0.5), (0.9, 0.8), (0.9, 1.05), (-0.9, 0.75)])
            for i in range(1, 4):
                f = i / 4
                line((90, 120, 200), (-0.9 + 1.8 * f, 0.5 + 0.3 * f), (-0.9 + 1.8 * f, 0.75 + 0.3 * f), 0.02)
        elif kind == "antenna":
            line((180, 180, 190), (0, 0), (0, 2.8), 0.07)
            for y in (0.8, 1.6, 2.3):
                line((180, 180, 190), (-0.3, y), (0.3, y), 0.04)
            circ((230, 60, 50), 0.0, 2.85, 0.07)
        # ------------------------------------------------------------ seasons
        elif kind in ("blossom", "autumntree"):
            line((100, 66, 42), (0, 0), (0, 2.2), 0.32)
            line((100, 66, 42), (0, 1.5), (0.55, 2.3), 0.14)
            line((100, 66, 42), (0, 1.8), (-0.5, 2.5), 0.12)
            if kind == "blossom":
                palette = ((236, 130, 170), (250, 176, 206), (255, 220, 236))
            else:
                palette = ((196, 80, 30), (232, 130, 40), (250, 190, 70))
            blobs = ((-0.8, 2.6, 0.85), (0.75, 2.7, 0.9), (0, 3.5, 1.05), (-0.25, 2.3, 0.8), (0.5, 3.3, 0.7))
            for col, dx, dy, sh in ((palette[0], 0.1, -0.1, 1.0), (palette[1], 0.0, 0.0, 0.9), (palette[2], -0.22, 0.25, 0.5)):
                for cx, cy, r in blobs:
                    circ(col, cx * sh + dx, 3.0 + (cy - 3.0) * sh + dy, r * sh)
            for _ in range(10):
                circ(palette[2], rnd.uniform(-1.3, 1.3), rnd.uniform(2.0, 4.2), 0.08)
        elif kind == "tulips":
            for i in range(6):
                x = -0.55 + i * 0.22
                line((60, 140, 50), (x, 0), (x, 0.42), 0.04)
                col = ((230, 40, 60), (250, 200, 40), (240, 120, 180))[i % 3]
                poly(col, [(x - 0.08, 0.4), (x + 0.08, 0.4), (x + 0.09, 0.56), (x, 0.5), (x - 0.09, 0.56)])
        elif kind == "pumpkin":
            for dx, w2 in ((-0.22, 0.32), (0.22, 0.32), (0.0, 0.36)):
                pygame.draw.ellipse(surf, (236, 120, 20), pygame.Rect(P(dx - w2, 0.55), (2 * w2 * sc, 0.55 * sc)))
            line((90, 120, 40), (0.0, 0.5), (0.08, 0.66), 0.06)
        elif kind == "scarecrow":
            line((120, 86, 50), (0, 0), (0, 2.1), 0.1)
            line((120, 86, 50), (-0.7, 1.5), (0.7, 1.5), 0.08)
            poly((60, 100, 170), [(-0.35, 0.9), (0.35, 0.9), (0.42, 1.65), (-0.42, 1.65)])
            for x in (-0.7, 0.7):
                line((230, 200, 110), (x, 1.5), (x + (0.15 if x > 0 else -0.15), 1.35), 0.04)
            circ((236, 214, 160), 0, 1.92, 0.22)
            poly((120, 80, 40), [(-0.4, 2.05), (0.4, 2.05), (0.15, 2.4), (-0.15, 2.4)])
            circ((30, 30, 34), -0.07, 1.95, 0.03)
            circ((30, 30, 34), 0.07, 1.95, 0.03)
        elif kind == "leafpile":
            for _ in range(26):
                circ(rnd.choice(((196, 80, 30), (232, 130, 40), (250, 190, 70), (160, 60, 30))),
                     rnd.uniform(-0.65, 0.65), rnd.uniform(0.05, 0.35), rnd.uniform(0.07, 0.13))
        elif kind == "snowpine":
            line((96, 66, 40), (0, 0), (0, 0.8), 0.28)
            for i, (y, wd) in enumerate(((0.55, 1.15), (1.55, 0.95), (2.45, 0.72), (3.25, 0.48))):
                top = y + 1.25 - i * 0.08
                poly((40, 90, 80), [(-wd, y), (wd, y), (0, top)])
                poly((250, 252, 255), [(-wd * 0.95, y + 0.05), (0, top), (wd * 0.85, y + 0.12), (wd * 0.2, y + 0.3)])
        # ---------------------------------------------------------- landmarks
        elif kind == "windmill":                    # tower only: the blades turn (render)
            poly((236, 232, 222), [(-1.3, 0), (1.3, 0), (0.75, 6.8), (-0.75, 6.8)])
            poly((206, 200, 190), [(0.35, 0), (1.3, 0), (0.75, 6.8), (0.2, 6.8)])
            poly((150, 60, 50), [(-1.0, 6.7), (1.0, 6.7), (0.0, 7.9)])
            pygame.draw.rect(surf, (110, 70, 40), pygame.Rect(P(-0.35, 1.3), (0.7 * sc, 1.3 * sc)),
                             border_top_left_radius=int(0.35 * sc), border_top_right_radius=int(0.35 * sc))
            for y in (3.2, 5.0):
                pygame.draw.rect(surf, (90, 140, 190), pygame.Rect(P(-0.25, y + 0.5), (0.5 * sc, 0.5 * sc)))
            circ((80, 60, 50), 0.0, 7.0, 0.22)
        elif kind == "barn":
            poly((176, 40, 36), [(-3.0, 0), (3.0, 0), (3.0, 3.2), (0.0, 5.2), (-3.0, 3.2)])
            poly((140, 28, 26), [(1.6, 0), (3.0, 0), (3.0, 3.2), (1.6, 4.1)])
            line((240, 240, 236), (-3.0, 3.2), (0.0, 5.2), 0.14)
            line((240, 240, 236), (0.0, 5.2), (3.0, 3.2), 0.14)
            pygame.draw.rect(surf, (240, 240, 236), pygame.Rect(P(-1.1, 2.6), (2.2 * sc, 2.6 * sc)), max(1, int(0.12 * sc)))
            line((240, 240, 236), (-1.1, 2.6), (1.1, 0.0), 0.1)
            line((240, 240, 236), (-1.1, 0.0), (1.1, 2.6), 0.1)
            pygame.draw.rect(surf, (60, 40, 30), pygame.Rect(P(-0.45, 4.2), (0.9 * sc, 0.7 * sc)))
        elif kind == "pyramid":
            poly((214, 176, 110), [(-5.4, 0), (5.4, 0), (0.0, 7.0)])
            poly((180, 140, 80), [(0.0, 7.0), (5.4, 0), (1.6, 0)])
            for i in range(1, 9):
                y = i * 0.78
                half = 5.4 * (1 - y / 7.0)
                line((190, 150, 90), (-half, y), (half * 0.3, y), 0.04)
            poly((60, 46, 30), [(-0.45, 0), (0.45, 0), (0.45, 1.0), (0.0, 1.3), (-0.45, 1.0)])
        elif kind == "pumpjack":                   # frame only: the beam nods (render)
            poly((60, 62, 70), [(-2.4, 0), (2.4, 0), (2.4, 0.3), (-2.4, 0.3)])
            line((200, 60, 40), (-0.4, 0.3), (0.0, 3.2), 0.16)
            line((200, 60, 40), (0.4, 0.3), (0.0, 3.2), 0.16)
            pygame.draw.rect(surf, (70, 72, 80), pygame.Rect(P(-2.0, 1.2), (0.9 * sc, 0.9 * sc)))
            line((140, 140, 150), (2.0, 0.3), (2.0, 1.4), 0.08)
        elif kind == "igloo":
            pygame.draw.ellipse(surf, (230, 240, 252), pygame.Rect(P(-1.75, 2.1), (3.5 * sc, 4.2 * sc)))
            pygame.draw.rect(surf, (0, 0, 0, 0), pygame.Rect(P(-1.8, 0.0), (3.6 * sc, 2.2 * sc)))
            for y in (0.5, 1.05, 1.55):
                half = 1.75 * math.sqrt(max(0.0, 1 - (y / 2.1) ** 2))
                line((180, 204, 232), (-half, y), (half, y), 0.04)
            pygame.draw.ellipse(surf, (40, 60, 90), pygame.Rect(P(0.7, 0.9), (0.8 * sc, 1.8 * sc)))
            pygame.draw.rect(surf, (0, 0, 0, 0), pygame.Rect(P(0.6, 0.0), (1.0 * sc, 0.0 * sc + 1)))
        elif kind == "lander":
            for a, b in (((-1.6, 0), (-0.8, 1.4)), ((1.6, 0), (0.8, 1.4)), ((-0.6, 0), (-0.4, 1.3))):
                line((200, 200, 210), a, b, 0.08)
            for x in (-1.6, 1.6):
                pygame.draw.ellipse(surf, (200, 200, 210), pygame.Rect(P(x - 0.3, 0.12), (0.6 * sc, 0.14 * sc)))
            poly((226, 180, 60), [(-1.1, 1.3), (1.1, 1.3), (1.0, 2.2), (-1.0, 2.2)])
            poly((214, 214, 222), [(-0.8, 2.2), (0.8, 2.2), (0.9, 3.0), (0.4, 3.5), (-0.5, 3.5), (-0.9, 3.0)])
            poly((40, 50, 70), [(-0.3, 2.8), (0.3, 2.8), (0.25, 3.2), (-0.25, 3.2)])
            line((180, 180, 190), (0.6, 3.4), (1.0, 3.75), 0.04)
        elif kind == "billboard":
            for x in (-2.2, 2.2):
                line((80, 84, 92), (x, 0), (x, 2.4), 0.16)
            pygame.draw.rect(surf, (30, 36, 60), pygame.Rect(P(-3.2, 5.2), (6.4 * sc, 2.9 * sc)), border_radius=int(0.1 * sc))
            pygame.draw.rect(surf, (255, 204, 48), pygame.Rect(P(-3.2, 5.2), (6.4 * sc, 2.9 * sc)), max(1, int(0.1 * sc)),
                             border_radius=int(0.1 * sc))
            t1 = gfx.font_px("black_i", 1.25 * sc).render("BRUH", True, (255, 255, 255))
            surf.blit(t1, t1.get_rect(center=P(0.0, 4.25)))
            t2 = gfx.font_px("heavy", 0.55 * sc).render("G A M E S", True, (255, 204, 48))
            surf.blit(t2, t2.get_rect(center=P(0.0, 3.0)))
        elif kind == "hut":
            poly((60, 50, 46), [(-1.7, 0), (1.7, 0), (1.6, 2.0), (-1.6, 2.0)])
            poly((40, 34, 32), [(-1.9, 1.9), (1.9, 1.9), (0.6, 3.1), (-0.4, 2.8)])
            pygame.draw.rect(surf, (255, 140, 40), pygame.Rect(P(-0.4, 1.3), (0.6 * sc, 0.6 * sc)))
            line((30, 26, 24), (-0.1, 1.3), (-0.1, 0.7), 0.05)
        elif kind == "temple":
            stone, stone_dk, moss = (150, 146, 120), (110, 106, 86), (80, 130, 60)
            for i in range(5):
                half = 3.8 - i * 0.62
                poly(stone_dk if i % 2 else stone, [(-half, i * 1.0), (half, i * 1.0), (half, i * 1.0 + 1.0), (-half, i * 1.0 + 1.0)])
                line(moss, (-half, i * 1.0 + 1.0), (-half + 0.8, i * 1.0 + 1.0), 0.12)
            poly(stone, [(-0.7, 5.0), (0.7, 5.0), (0.7, 6.2), (-0.7, 6.2)])
            poly((40, 34, 30), [(-0.35, 5.0), (0.35, 5.0), (0.35, 5.8), (-0.35, 5.8)])
            poly((60, 54, 46), [(-0.5, 0.0), (0.5, 0.0), (0.5, 4.95), (-0.5, 4.95)])
            for i in range(10):
                line(stone_dk, (-0.5, i * 0.5), (0.5, i * 0.5), 0.04)
        elif kind == "dome":
            pygame.draw.ellipse(surf, (200, 230, 250), pygame.Rect(P(-2.8, 3.6), (5.6 * sc, 6.2 * sc)))
            pygame.draw.rect(surf, (0, 0, 0, 0), pygame.Rect(P(-3.3, 0.5), (6.6 * sc, 1.0 * sc)))   # keep the top half
            poly((170, 170, 180), [(-3.2, 0), (3.2, 0), (3.2, 0.5), (-3.2, 0.5)])
            for i in range(-2, 3):
                line((150, 190, 220), (i * 1.0, 0.5), (i * 0.55, 3.55), 0.04)
            for x in (-1.4, 1.2):
                circ((80, 150, 70), x, 0.9, 0.35)
            line((180, 180, 190), (2.2, 0.5), (2.6, 4.2), 0.06)
        elif kind == "launchpad":
            poly((90, 92, 100), [(-1.8, 0), (1.8, 0), (1.6, 0.5), (-1.6, 0.5)])
            for x in (-1.3, -0.9):
                line((200, 60, 40), (x, 0.5), (x, 7.0), 0.1)
            for y in range(1, 7):
                line((200, 60, 40), (-1.3, y), (-0.9, y + 0.5), 0.05)
            poly((240, 240, 246), [(-0.4, 0.5), (0.6, 0.5), (0.6, 6.2), (0.1, 8.0), (-0.4, 6.2)])
            poly((220, 40, 40), [(-0.4, 6.2), (0.6, 6.2), (0.1, 8.0)])
            poly((220, 40, 40), [(-0.8, 0.5), (-0.4, 0.5), (-0.4, 1.8)])
            poly((220, 40, 40), [(1.0, 0.5), (0.6, 0.5), (0.6, 1.8)])
        # ---------------------------------------------------------- underwater
        elif kind == "coral":
            col = rnd.choice(((250, 110, 120), (255, 150, 70), (230, 90, 170)))

            def branch(x, y, ang, L, wd, depth):
                x2, y2 = x + math.cos(ang) * L, y + math.sin(ang) * L
                line(col, (x, y), (x2, y2), wd)
                circ(gfx.mix(col, (255, 255, 255), 0.3), x2, y2, wd * 0.6)
                if depth:
                    branch(x2, y2, ang + 0.5, L * 0.7, wd * 0.75, depth - 1)
                    branch(x2, y2, ang - 0.45, L * 0.7, wd * 0.75, depth - 1)
            branch(0.0, 0.0, math.pi / 2, 0.6, 0.18, 3)
        elif kind == "seaweed":
            for x0, top, ph in ((-0.3, 2.8, 0.0), (0.05, 3.1, 1.3), (0.35, 2.4, 2.4)):
                pts = [(x0 + 0.18 * math.sin(y * 2.2 + ph), y) for y in [i * 0.2 for i in range(int(top / 0.2) + 1)]]
                for a, b in zip(pts, pts[1:]):
                    line((50, 140, 70), a, b, 0.14)
                for a in pts[2::3]:
                    poly((80, 176, 90), [a, (a[0] + 0.3, a[1] + 0.12), (a[0] + 0.04, a[1] + 0.2)])
        elif kind == "anemone":
            for i in range(9):
                ang = math.pi * (0.15 + 0.7 * i / 8)
                tip = (math.cos(ang) * 0.55, 0.25 + math.sin(ang) * 0.6)
                line((200, 90, 200), (0, 0.25), tip, 0.08)
                circ((250, 160, 250), *tip, 0.06)
            pygame.draw.ellipse(surf, (150, 60, 160), pygame.Rect(P(-0.4, 0.35), (0.8 * sc, 0.35 * sc)))
        elif kind == "shell":
            for i in range(7):
                ang = math.pi * (i / 6)
                line((250, 220, 210), (0, 0.02), (math.cos(ang) * 0.3, 0.02 + math.sin(ang) * 0.36), 0.06)
            pygame.draw.ellipse(surf, (240, 200, 190), pygame.Rect(P(-0.3, 0.38), (0.6 * sc, 0.36 * sc)), max(1, int(0.03 * sc)))
        elif kind == "starfish":
            pts = []
            for i in range(10):
                r = 0.38 if i % 2 == 0 else 0.15
                ang = math.pi / 2 + i * math.pi / 5
                pts.append((math.cos(ang) * r, 0.15 + math.sin(ang) * r * 0.4))
            poly((250, 130, 60), pts)
        elif kind == "treasure":
            poly((110, 70, 36), [(-0.6, 0), (0.6, 0), (0.6, 0.55), (-0.6, 0.55)])
            pygame.draw.ellipse(surf, (130, 84, 44), pygame.Rect(P(-0.6, 0.85), (1.2 * sc, 0.6 * sc)))
            for x in (-0.45, 0.45):
                line((220, 180, 60), (x, 0), (x, 0.8), 0.07)
            circ((255, 220, 70), 0.0, 0.5, 0.08)
            for x in (-0.25, 0.0, 0.2):
                circ((255, 210, 50), x, 0.62, 0.09)
        elif kind == "shipwreck":
            hull = [(-4.2, 0.0), (3.8, 0.0), (4.4, 2.2), (2.0, 1.6), (0.6, 2.1), (-1.0, 1.4), (-2.6, 2.0), (-4.0, 1.5)]
            poly((90, 66, 46), hull)
            for i in range(1, 6):
                line((70, 50, 34), (-4.1, i * 0.32), (4.0, i * 0.36), 0.05)
            for x, y in ((-1.8, 0.8), (0.4, 0.9), (2.4, 1.0)):
                circ((30, 40, 50), x, y, 0.22)
            line((80, 60, 42), (-0.4, 1.8), (-1.2, 5.8), 0.2)
            poly((200, 196, 170), [(-1.1, 5.4), (-0.6, 3.4), (0.6, 3.8)])
            line((40, 120, 70), (2.8, 0.2), (3.2, 2.6), 0.1)
            line((40, 120, 70), (-3.6, 0.2), (-3.2, 2.0), 0.1)
    return gfx.supersample(w * ppm, h * ppm, draw)


def _ellipse(size, color):
    s = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(s, color, s.get_rect())
    pygame.draw.ellipse(s, gfx.shade(color, 0.7), s.get_rect(), max(1, size[1] // 10))
    return s
