"""How upgrades change a vehicle's body: paint, stickers, the shark growing up.

Everything keys off the total upgrade level (0 when stock, 40 with every upgrade maxed).
Paint is found automatically: the body's own main colour (or its white/silver panels)
is recoloured with the shading kept, and stickers are clipped to those same panels,
so they never float over windows, tyres or the rider.
"""
import math

import numpy as np
import pygame

import gfx
from config import UPGRADES

NO_STYLE = ("shark",)              # the shark grows up instead (see shark_stage)

# (from total level, name, hue degrees, saturation, value multiplier)
PAINTS = [
    (6, "racing blue", 214, 0.85, 1.0),
    (14, "toxic green", 96, 0.8, 1.0),
    (22, "candy purple", 278, 0.78, 1.0),
    (30, "matte black", 220, 0.12, 0.32),
    (40, "gold", 44, 0.82, 1.08),
]
ALT_PAINTS = {"racing blue": (22, 0.9, 1.0)}     # if the stock body already is blue: blaze orange instead

STICKER_STEPS = (4, 10, 16, 24, 32)               # stripes, number, TURBO decal, flames, checker band
SPOILER_STEPS = (6, 18, 30)                       # lip, GT wing, big wing


def total_level(levels):
    if not levels:
        return 0
    return sum(max(0, levels.get(u["key"], 1) - 1) for u in UPGRADES)


def tiers(levels):
    """(paint index or -1, number of sticker steps, spoiler size 0..3) for these upgrade levels."""
    t = total_level(levels)
    paint = max((i for i, p in enumerate(PAINTS) if t >= p[0]), default=-1)
    return paint, sum(t >= s for s in STICKER_STEPS), sum(t >= s for s in SPOILER_STEPS)


def shark_stage(levels):
    """0 = baby shark with big cute eyes ... 4 = huge and scary."""
    return min(4, total_level(levels) // 8)


SHARK_SCALE = (0.7, 0.84, 1.0, 1.14, 1.3)


# ----------------------------------------------------------------- colour maths
def _rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    rm, gm = nz & (mx == r), nz & (mx == g) & (mx != r)
    bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6
    h[gm] = (b - r)[gm] / d[gm] + 2
    h[bm] = (r - g)[bm] / d[bm] + 4
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h * 60.0, s, mx


def _hsv_to_rgb(h, s, v):
    h = (h % 360) / 60.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,))
    for k, (a, b, c) in enumerate(((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        out[m, 0], out[m, 1], out[m, 2] = a[m], b[m], c[m]
    return out


def paint_mask(surf):
    """(mask of the body's paint, hue of the stock paint or None for white/silver bodies)."""
    rgb = pygame.surfarray.array3d(surf).astype(float) / 255.0
    alpha = pygame.surfarray.array_alpha(surf)
    h, s, v = _rgb_to_hsv(rgb)
    solid = alpha > 220
    vivid = solid & (s > 0.45) & (v > 0.3)
    if solid.sum() == 0:
        return np.zeros(alpha.shape, bool), None
    hist = np.bincount((h[vivid] // 20).astype(int) % 18, minlength=18)
    best = int(hist.argmax())
    if hist[best] > 0.12 * solid.sum():
        centre = float(np.median(h[vivid & ((h // 20).astype(int) % 18 == best)]))
        dist = np.abs((h - centre + 180) % 360 - 180)
        return solid & (dist < 24) & (s > 0.3) & (v > 0.2), centre
    return solid & (s < 0.16) & (v > 0.6), None


def repaint(surf, mask, stock_hue, paint):
    name, hue, sat, val = paint[1:]
    if stock_hue is not None and name in ALT_PAINTS and abs((stock_hue - hue + 180) % 360 - 180) < 35:
        hue, sat, val = ALT_PAINTS[name]
    out = surf.copy()
    px = pygame.surfarray.pixels3d(out)
    rgb = px.astype(float) / 255.0
    h, s, v = _rgb_to_hsv(rgb)
    if stock_hue is None:                       # white or silver: shading lives in the value only
        nv = np.clip(0.25 + 0.75 * v, 0, 1) * val
    else:
        nv = np.clip(v * val * (1.0 if val < 0.5 else 1.05), 0, 1)
    new = _hsv_to_rgb(np.full(h.shape, float(hue)), np.full(h.shape, sat) * np.clip(s / max(s[mask].mean(), 1e-3), 0.7, 1.1)
                      if stock_hue is not None else np.full(h.shape, sat), nv)
    px[mask] = (np.clip(new[mask], 0, 1) * 255).astype(np.uint8)
    del px
    return out


# --------------------------------------------------------------------- stickers
def _contrast(paint_rgb):
    return (20, 20, 24) if sum(paint_rgb) > 420 else (250, 250, 250)


def stickers(surf, mask, steps, ppm):
    """Racing stripes, a number, a TURBO decal, flames and a checker band, only on painted panels."""
    if steps <= 0 or mask.sum() < 50:
        return surf
    w, h = surf.get_size()
    xs, ys = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    # the band of rows holding most of the paint: that's the door/side panel
    rows = np.bincount(ys, minlength=h)
    busy = np.nonzero(rows > 0.5 * rows.max())[0]
    band0, band1 = (busy.min(), busy.max()) if len(busy) else (y0, y1)
    mid = (band0 + band1) / 2
    bh = max(4, band1 - band0)
    cx = (x0 + x1) / 2
    avg = pygame.surfarray.array3d(surf)[mask].mean(0)
    ink = _contrast(avg)
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    sc = ppm
    # 1: twin racing stripes along the whole side
    for dy in (-0.16, 0.16):
        pygame.draw.rect(layer, (*ink, 235), (x0, mid + dy * bh - 0.035 * sc, x1 - x0, 0.07 * sc))
    if steps >= 2:                               # 2: a number roundel on the door
        r = min(0.24 * sc, bh * 0.55)
        pygame.draw.circle(layer, (250, 250, 250, 255), (cx - 0.15 * sc, mid), r)
        pygame.draw.circle(layer, (20, 20, 24, 255), (cx - 0.15 * sc, mid), r, max(1, int(0.03 * sc)))
        t = gfx.font_px("heavy", r * 1.25).render("77", True, (20, 20, 24))
        layer.blit(t, t.get_rect(center=(cx - 0.15 * sc, mid)))
    if steps >= 3:                               # 3: a TURBO sponsor decal towards the back
        t = gfx.font_px("black_i", max(6, 0.17 * sc)).render("TURBO", True, (20, 20, 24))
        box = t.get_rect(center=(x0 + (x1 - x0) * 0.24, mid + bh * 0.28))
        pygame.draw.rect(layer, (255, 206, 40, 255), box.inflate(0.08 * sc, 0.03 * sc), border_radius=int(0.03 * sc))
        layer.blit(t, box)
    if steps >= 4:                               # 4: flames licking back from the front
        fx = x1 - 0.05 * sc
        for col, k in (((255, 90, 20), 1.0), ((255, 200, 40), 0.65)):
            pts = [(fx, mid - bh * 0.42 * k)]
            for i in range(5):
                tip_x = fx - (0.55 + 0.35 * (i % 2)) * sc * k
                pts += [(tip_x, mid - bh * (0.42 - 0.21 * i) * k + 0.03 * sc),
                        (fx - 0.12 * sc * k, mid - bh * (0.32 - 0.21 * i) * k)]
            pts.append((fx, mid + bh * 0.5 * k))
            pygame.draw.polygon(layer, (*col, 240), pts)
    if steps >= 5:                               # 5: a checkered band near the rear
        cell = max(2, int(0.07 * sc))
        bx = x0 + (x1 - x0) * 0.08
        for i in range(4):
            for j in range(int(bh / cell) + 1):
                if (i + j) % 2 == 0:
                    pygame.draw.rect(layer, (20, 20, 24, 240), (bx + i * cell, band0 + j * cell, cell, cell))
                else:
                    pygame.draw.rect(layer, (250, 250, 250, 240), (bx + i * cell, band0 + j * cell, cell, cell))
    # clip to the painted panels
    la = pygame.surfarray.pixels_alpha(layer)
    la[~mask] = 0
    del la
    out = surf.copy()
    out.blit(layer, (0, 0))
    return out


def styled_body(base, key, levels, ppm):
    """The body sprite with this upgrade level's paint and stickers."""
    if key in NO_STYLE:
        return base
    paint, steps, _ = tiers(levels)
    if paint < 0 and steps == 0:
        return base
    mask, hue = paint_mask(base)
    out = base
    if paint >= 0 and mask.any():
        out = repaint(base, mask, hue, PAINTS[paint])
    return stickers(out, mask, steps, ppm)


# ---------------------------------------------------------------------- spoiler
SPOILER_CARS = ("monster", "supercar", "police", "tesla", "mini", "golf", "lkw")     # not the open-top jeep


def spoiler_mount(spec):
    if "wing" in spec:
        return spec["wing"]
    return min(((x, y) for x, y in spec["hull"] if y > 0.15), key=lambda p: p[0])


def draw_spoiler(surf, P, k, spec, levels):
    """Lip, GT wing or a big wing with endplates on the rear deck, drawn in the vehicle's frame."""
    if spec["key"] not in SPOILER_CARS and not (spec.get("story") and not spec.get("has_wing")):
        return
    size = tiers(levels)[2]
    if size == 0:
        return
    mx, my = spoiler_mount(spec)
    carbon, edge = (36, 38, 44), (90, 96, 108)
    accent = (230, 40, 40) if size < 3 else (255, 200, 40)
    lw = max(1, int(0.03 * k))
    if size == 1:                                 # a ducktail lip
        pts = [P(mx + 0.05, my - 0.02), P(mx + 0.55, my + 0.02), P(mx + 0.05, my + 0.16), P(mx - 0.12, my + 0.14)]
        pygame.draw.polygon(surf, carbon, pts)
        pygame.draw.polygon(surf, edge, pts, lw)
        return
    height = 0.32 if size == 2 else 0.5
    span = 0.75 if size == 2 else 1.0
    for sx in (mx + 0.18, mx + 0.48):             # struts
        pygame.draw.line(surf, carbon, P(sx, my - 0.02), P(sx - 0.08, my + height), max(2, int(0.06 * k)))
    wing = [P(mx - 0.32, my + height + 0.02), P(mx - 0.32 + span, my + height + 0.06),
            P(mx - 0.32 + span, my + height + 0.15), P(mx - 0.3, my + height + 0.18)]
    pygame.draw.polygon(surf, carbon, wing)
    pygame.draw.line(surf, accent, wing[3], wing[2], max(1, int(0.035 * k)))
    pygame.draw.polygon(surf, edge, wing, lw)
    if size == 3:                                 # endplate
        plate = [P(mx - 0.38, my + height - 0.08), P(mx - 0.22, my + height - 0.08), P(mx - 0.22, my + height + 0.28),
                 P(mx - 0.4, my + height + 0.24)]
        pygame.draw.polygon(surf, carbon, plate)
        pygame.draw.polygon(surf, accent, plate, lw)
