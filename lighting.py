"""Day/night cycle and lights (headlights, tail lights, lamps).

Darkness is a full-screen overlay; lights punch holes into it. Headlight
cones are drawn as nested polygons with decreasing darkness, round lights
are subtracted from the overlay's alpha.
"""
import math
import random

import pygame

import gfx
from config import DAY_LENGTH

NIGHT = (8, 12, 36)


def phase_info(stage, t):
    """(darkness 0..1, sunset glow 0..1) for a stage at run time t (seconds)."""
    if not stage.get("cycle"):
        return stage.get("base_dark", 0.0), 0.0
    p = (t / DAY_LENGTH + 0.12) % 1.0
    # 0.00-0.42 day, 0.42-0.52 sunset, 0.52-0.88 night, 0.88-1.00 sunrise
    if p < 0.42:
        return 0.0, 0.0
    if p < 0.52:
        k = (p - 0.42) / 0.10
        return k * 0.78, math.sin(k * math.pi)
    if p < 0.88:
        return 0.78, 0.0
    k = (p - 0.88) / 0.12
    return (1 - k) * 0.78, math.sin(k * math.pi) * 0.8


def night_sky(stage, w, h):
    sky = gfx.vgradient(w, h, (6, 10, 30), (34, 44, 86)).convert_alpha()
    rnd = random.Random(stage["seed"] + 99)
    for _ in range(int(w * h / 2400)):
        b = rnd.randint(150, 255)
        pygame.draw.circle(sky, (b, b, min(255, b + 15)), (rnd.uniform(0, w), rnd.uniform(0, h * 0.7)),
                           rnd.choice((1, 1, 1.5, 2)) * gfx.U)
    mx, my, r = w * 0.22, h * 0.17, gfx.s(34)
    glow = pygame.Surface((int(r * 6), int(r * 6)), pygame.SRCALPHA)
    for i in range(14, 0, -1):
        pygame.draw.circle(glow, (220, 230, 255, int(60 * (1 - i / 14) ** 1.5)), (r * 3, r * 3), r * 3 * i / 14)
    sky.blit(glow, (mx - r * 3, my - r * 3))
    pygame.draw.circle(sky, (244, 244, 230), (mx, my), r)
    for ox, oy, rr in ((-0.3, -0.2, 0.22), (0.25, 0.25, 0.16), (0.1, -0.35, 0.1)):
        pygame.draw.circle(sky, (214, 214, 200), (mx + ox * r, my + oy * r), rr * r)
    return sky


def sunset_sky(w, h):
    return gfx.vgradient(w, h, (92, 70, 150), (255, 150, 90)).convert_alpha()


class Lighting:
    def __init__(self):
        self.overlay = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        self._round = {}

    def _round_light(self, radius, strength):
        radius = max(4, int(radius))
        key = (radius, round(strength, 1))
        img = self._round.get(key)
        if img is None:
            if len(self._round) > 80:
                self._round.clear()
            img = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for i in range(16, 0, -1):
                f = i / 16
                pygame.draw.circle(img, (0, 0, 0, int(255 * key[1] * (1 - f) ** 0.9)), (radius, radius), radius * f)
            self._round[key] = img
        return img

    def apply(self, surf, darkness, cones, glows):
        """cones: (x, y, angle, length_px); glows: (x, y, radius_px, strength 0..1)."""
        if darkness <= 0.01:
            return
        a = int(255 * darkness)
        ov = self.overlay
        ov.fill((*NIGHT, a))
        for x, y, ang, L in cones:
            ca, sa = math.cos(ang), -math.sin(ang)
            px, py = -sa, ca
            for i in range(12, 0, -1):
                frac = i / 12
                keep = 0.12 + 0.8 * frac ** 1.3
                length = L * frac
                spread = 0.04 * L + length * 0.22
                tip_w = 0.02 * L
                pts = [(x + px * tip_w, y + py * tip_w), (x - px * tip_w, y - py * tip_w),
                       (x + ca * length - px * spread, y + sa * length - py * spread),
                       (x + ca * length + px * spread, y + sa * length + py * spread)]
                pygame.draw.polygon(ov, (*NIGHT, int(a * keep)), pts)
        for x, y, r, strength in glows:
            img = self._round_light(r, strength)
            ov.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2), special_flags=pygame.BLEND_RGBA_SUB)
        surf.blit(ov, (0, 0))

    @staticmethod
    def lamp_dots(surf, cones, tails):
        """Bright lenses on top of the darkened scene."""
        for x, y, ang, L in cones:
            pygame.draw.circle(surf, (255, 246, 200), (x, y), max(2, L * 0.012))
            pygame.draw.circle(surf, (255, 255, 255), (x, y), max(1, L * 0.006))
        for x, y in tails:
            pygame.draw.circle(surf, (255, 40, 40), (x, y), gfx.s(3.5))
