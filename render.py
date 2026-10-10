"""World rendering: camera, sky and parallax, terrain features, props, vehicles, particles."""
import bisect
import math
import random

import pygame

import drivers
import gfx
import lighting
import props as prop_art
import sprites
import styling
import vehicle_art
from config import BASE_PPM, season_at, vehicle_stats
from physics import rest_wheel_offsets
from terrain import (RES, START, boulder_pos, boulder_sink, crusher_bottom, flame_height, spinner_points,
                     traffic_pos, wrecker_ball)


QUALITY = "high"     # "low" skips pebbles and roadside props


SEASON_KEYS = ("sky", "far", "ground", "pebble", "pebble_hi", "top", "top_hi", "top_lo")


def _mix_any(a, b, t):
    if isinstance(a[0], (tuple, list)):
        return tuple(_mix_any(x, y, t) for x, y in zip(a, b))
    return gfx.mix(a, b, t)


def season_stage(stage, x):
    """The stage as it looks at distance x: on the Four Seasons stage the colours blend between seasons."""
    s = season_at(stage, x)
    if s is None:
        return stage
    i, j, k = s
    k = round(k * 10) / 10                      # 10 steps, so sprites cached by colour stay few
    a, b = stage["seasons"][i], stage["seasons"][j]
    out = dict(stage)
    for key in SEASON_KEYS:
        out[key] = _mix_any(a[key], b[key], k) if k > 0 else a[key]
    out["season"] = (i, j, k)
    return out


def _hash(ix, iy, k=0):
    n = (ix * 374761393 + iy * 668265263 + k * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


class Camera:
    def __init__(self):
        self.x = self.y = 0.0
        self.ppm = BASE_PPM * gfx.U

    def follow(self, car, terrain, dt, snap=False):
        speed = math.hypot(car.vx, car.vy)
        look = max(-2.5, min(6.5, car.vx * 0.36))
        tx = car.x + 2.2 + look
        ty = 0.72 * car.y + 0.28 * terrain.height(car.x + 9) + 1.1
        target_ppm = BASE_PPM * gfx.U * (1 - 0.3 * min(1.0, speed / 30))
        if snap:
            self.x, self.y, self.ppm = tx, ty, target_ppm
            return
        self.x += (tx - self.x) * min(1.0, dt * 5.0)
        self.y += (ty - self.y) * min(1.0, dt * 3.2)
        self.ppm += (target_ppm - self.ppm) * min(1.0, dt * 1.2)

    def to_screen(self, x, y):
        return (gfx.W / 2 + (x - self.x) * self.ppm, gfx.H / 2 - (y - self.y) * self.ppm)

    def view(self, margin=1.0):
        half = gfx.W / 2 / self.ppm
        return self.x - half - margin, self.x + half + margin


class VehicleArt:
    def __init__(self, spec, ppm, driver="default"):
        self.spec, self.ppm = spec, ppm
        self.body = vehicle_art.body(spec["key"], ppm)
        if driver == "default":
            self.head = vehicle_art.head(spec["head_art"], ppm)
        else:
            r = 0.27 if spec["head_art"] in ("helmet", "helmet_blue", "racer", "hardhat") else 0.23
            self.head = drivers.face(driver, r * ppm)
        self.wheels = [vehicle_art.wheel(style, w[2], ppm) for style, w in zip(spec["wheel_art"], spec["wheels"])]
        self.flames = [vehicle_art.flame(ppm, 1.1 if spec["thrust"][0] > 0 else 0.8, seed=i) for i in range(4)]
        self._styled = {}

    def styled(self, levels):
        """The body with the paint and stickers (or, for the shark, the growth stage) its upgrades earned."""
        key = self.spec["key"]
        tier = (styling.shark_stage(levels),) if key == "shark" else styling.tiers(levels)[:2]
        img = self._styled.get(tier)
        if img is None:
            if key == "shark":
                img = vehicle_art.body("shark", self.ppm, tier[0])
            else:
                img = styling.styled_body(self.body, key, levels, self.ppm)
            self._styled[tier] = img
        return img


class Art:
    """Sprites at the camera's closest zoom; scaled down when it zooms out."""

    def __init__(self):
        self.ppm = BASE_PPM * gfx.U
        self.nitro = sprites.nitro_can(self.ppm)
        self._vehicles = {}
        self._cache = {}

    def vehicle(self, spec, driver="default"):
        key = (spec["key"], driver)
        if key not in self._vehicles:
            self._vehicles[key] = VehicleArt(spec, self.ppm, driver)
        return self._vehicles[key]

    def cached(self, key, make):
        surf = self._cache.get(key)
        if surf is None:
            if len(self._cache) > 2500:
                self._cache.clear()
            surf = self._cache[key] = make()
        return surf


def compose_vehicle(art, spec, scale, levels=None, angle=0.0, driver="default"):
    """A still picture of a vehicle at rest, for menus. Returns (surface, chassis centre)."""
    va = art.vehicle(spec, driver)
    stats = vehicle_stats(spec, levels or {})
    wheels = rest_wheel_offsets(spec, stats)
    k = art.ppm * scale
    ext = vehicle_art.EXTENT.get(spec["key"], 2.75)
    size = int(2 * ext * k)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    ca, sa = math.cos(angle), math.sin(angle)

    def P(x, y):
        return (c + (x * ca - y * sa) * k, c - (x * sa + y * ca) * k)
    _draw_vehicle_parts(surf, P, k, spec, va, scale, angle,
                        [(lx, ly, r, 0.0) for lx, ly, r in wheels], (0.0, 0.0, 0.0), True, levels=levels)
    return surf, (c, c)


# ------------------------------------------------------------ upgrade looks
# Every upgrade shows on the vehicle as it levels up:
#   boost       neon underglow (cyan, then magenta, then cycling rainbow)
#   tires       gold rims, then spinning gold spokes, then a glowing rim ring
#   engine      chrome tailpipes, a second pipe, then exhaust flames
#   suspension  gold springs, then neon springs
#   turbo       body sparkles, then a glowing aura (blue, purple, electric cyan)
#   all of them paint, stickers and spoilers by total level: see styling.py
_PUFFS = {}


def _puff(radius, color):
    key = (int(radius), color)
    img = _PUFFS.get(key)
    if img is None:
        if len(_PUFFS) > 300:
            _PUFFS.clear()
        img = _PUFFS[key] = sprites.soft_puff(max(2, int(radius)), color)
    return img


def _rainbow(t, offset=0.0):
    c = pygame.Color(0)
    c.hsva = (int((t * 90 + offset) % 360 / 30) * 30, 85, 100, 100)
    return (c.r, c.g, c.b)


def _lv(levels, key):
    return (levels or {}).get(key, 1)


def _neon_color(level, t):
    if level >= 9:
        return _rainbow(t)
    return (40, 220, 255) if level < 6 else (255, 60, 220)


def _underglow(surf, P, k, spec, levels, t, behind):
    b = _lv(levels, "boost")
    if b < 3:
        return
    axles = [w[0] for w in spec["wheels"]]
    x0, x1 = min(axles) - 0.2, max(axles) + 0.2
    y = min(ly for _, ly in spec["hull"]) - 0.06
    col = _neon_color(b, t)
    if behind:
        pulse = 0.85 + 0.15 * math.sin(t * 5)
        n = 6
        for i in range(n):
            x = x0 + (x1 - x0) * i / (n - 1)
            img = _puff(0.5 * k * (1 + 0.06 * (b - 3)) * pulse, col)
            p = P(x, y - 0.12)
            surf.blit(img, img.get_rect(center=p))
    else:
        pygame.draw.line(surf, col, P(x0 + 0.1, y), P(x1 - 0.1, y), max(2, int(0.06 * k)))
        pygame.draw.line(surf, (255, 255, 255), P(x0 + 0.2, y), P(x1 - 0.2, y), max(1, int(0.02 * k)))


def _aura(surf, va, levels, scale, angle, pos, t):
    tu = _lv(levels, "turbo")
    if tu < 3:
        return
    col = {3: (80, 180, 255), 4: (190, 90, 255)}.get(tu, (120, 255, 255))
    cache = va.__dict__.setdefault("auras", {})
    sil = cache.get(col)
    if sil is None:
        mask = pygame.mask.from_surface(va.body)
        sil = mask.to_surface(setcolor=(*col, 255), unsetcolor=(0, 0, 0, 0))
        w, h = sil.get_size()
        small = pygame.transform.smoothscale(sil, (max(1, w // 5), max(1, h // 5)))
        sil = cache[col] = pygame.transform.smoothscale(small, (w, h))
    img = pygame.transform.rotozoom(sil, math.degrees(angle), scale * 1.12)
    img.set_alpha(int(185 + 60 * math.sin(t * 4)))
    surf.blit(img, img.get_rect(center=pos))


def _sparkles(surf, P, k, spec, levels, t):
    tu = _lv(levels, "turbo")
    if tu < 2:
        return
    hull = spec["hull"]
    for i in range(tu):
        ph = t * 1.3 + i * 0.37
        lx, ly = hull[(int(ph) * 3 + i * 5) % len(hull)]
        life = ph % 1.0
        size = math.sin(life * math.pi) * 0.16 * k
        if size < 1:
            continue
        cx, cy = P(lx * 0.8, ly * 0.8 + 0.1)
        col = (255, 250, 210)
        pygame.draw.polygon(surf, col, [(cx, cy - size), (cx + size * 0.25, cy - size * 0.25), (cx + size, cy),
                                        (cx + size * 0.25, cy + size * 0.25), (cx, cy + size),
                                        (cx - size * 0.25, cy + size * 0.25), (cx - size, cy),
                                        (cx - size * 0.25, cy - size * 0.25)])


def _rims(surf, k, spec, levels, centres, wheels, t):
    tl = _lv(levels, "tires")
    if tl < 4 or spec["rig"] in ("hover", "shark"):
        return
    gold, gold_dk = (240, 186, 40), (170, 120, 20)
    for ctr, w, sw in zip(centres, wheels, spec["wheels"]):
        r = sw[2] * k
        pygame.draw.circle(surf, gold_dk, ctr, r * 0.56, max(2, int(0.07 * k)))
        pygame.draw.circle(surf, gold, ctr, r * 0.56, max(1, int(0.04 * k)))
        if tl >= 7:
            spin = -w[3]
            for j in range(5):
                a = spin + j * math.tau / 5
                pygame.draw.line(surf, gold, ctr, (ctr[0] + math.cos(a) * r * 0.52, ctr[1] + math.sin(a) * r * 0.52),
                                 max(1, int(0.045 * k)))
            pygame.draw.circle(surf, gold_dk, ctr, r * 0.14)
        if tl >= 9:
            col = _rainbow(t, 40) if tl >= 10 else (120, 255, 255)
            pygame.draw.circle(surf, col, ctr, r * 0.92, max(1, int(0.035 * k)))


def _pipes(surf, P, k, spec, levels, t, still, rpm):
    e = _lv(levels, "engine")
    if e < 3:
        return
    ex, ey = spec["exhaust"]
    up = ey > 0.6                                 # exhaust on the roof (monster truck, LKW): upright stacks
    chrome, dark = (214, 220, 230), (90, 94, 104)
    for off in ((0.0, -0.12) if e >= 6 else (0.0,)):
        if up:
            a, b = P(ex + off, ey - 0.3), P(ex + off, ey + 0.12)
            tip, fwd, side = (ex + off, ey + 0.12), (0.0, 1.0), (1.0, 0.0)
        else:
            a, b = P(ex + 0.3, ey + off), P(ex - 0.08, ey + off)
            tip, fwd, side = (ex - 0.08, ey + off), (-1.0, 0.0), (0.0, 1.0)
        pygame.draw.line(surf, dark, a, b, max(3, int(0.13 * k)))
        pygame.draw.line(surf, chrome, a, b, max(2, int(0.08 * k)))
        pygame.draw.circle(surf, (40, 40, 44), b, 0.05 * k)
        if e >= 8:
            power = 0.35 if still else rpm
            if power < 0.3:
                continue
            L = (0.2 + 0.45 * power) * (0.7 + 0.3 * math.sin(t * 40 + off * 50))
            outer, inner = ((60, 120, 255), (200, 240, 255)) if e >= 10 else ((255, 120, 30), (255, 230, 120))
            for col, w, f in ((outer, 0.09, 1.0), (inner, 0.045, 0.6)):
                pygame.draw.polygon(surf, col, [P(tip[0] + side[0] * w, tip[1] + side[1] * w),
                                                P(tip[0] + fwd[0] * L * f, tip[1] + fwd[1] * L * f),
                                                P(tip[0] - side[0] * w, tip[1] - side[1] * w)])


def _spring_color(levels, big):
    sl = _lv(levels, "suspension")
    if sl >= 8:
        return (60, 230, 255)
    if sl >= 4:
        return (240, 186, 40)
    return (230, 70, 50) if big else (176, 180, 188)


def _draw_vehicle_parts(surf, P, k, spec, va, scale, angle, wheels, wobble, still, flame=None, levels=None,
                        rpm=0.0):
    """Shared by gameplay and menus. wheels: (lx, ly, radius, spin) in local or world coords via P."""
    rig = spec["rig"]
    now_t = pygame.time.get_ticks() / 1000
    looks = None if spec["key"] in styling.NO_STYLE else levels          # the shark grows instead of glowing
    _underglow(surf, P, k, spec, looks, now_t, True)
    anchors = [(w[0], w[1]) for w in spec["wheels"]]
    wheel_imgs = [pygame.transform.rotozoom(img, math.degrees(w[3]), scale) for img, w in zip(va.wheels, wheels)]
    centres = [P(w[0], w[1]) for w in wheels] if still else [w[4] for w in wheels]

    def draw_wheels():
        for img, ctr in zip(wheel_imgs, centres):
            surf.blit(img, img.get_rect(center=ctr))
        if rig in ("bike", "tank"):
            _rims(surf, k, spec, looks, centres, wheels, now_t)

    if flame is not None:
        img, pos = flame
        surf.blit(img, img.get_rect(center=pos))

    if rig == "tank":
        (c0, c1), r = centres, spec["wheels"][0][2]
        R = (r + 0.08) * k
        dx, dy = c1[0] - c0[0], c1[1] - c0[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        belt = [(c0[0] + nx * R, c0[1] + ny * R), (c1[0] + nx * R, c1[1] + ny * R),
                (c1[0] - nx * R, c1[1] - ny * R), (c0[0] - nx * R, c0[1] - ny * R)]
        for c in (c0, c1):
            pygame.draw.circle(surf, (34, 34, 32), c, R)
        pygame.draw.polygon(surf, (34, 34, 32), belt)
        spacing = 0.26 * k
        phase = (-wheels[0][3] * r * k) % spacing
        for sgn in (-1, 1):
            ox, oy = nx * R * sgn, ny * R * sgn
            d = phase if sgn < 0 else spacing - phase
            while d < L:
                f = d / L
                px, py = c0[0] + dx * f + ox, c0[1] + dy * f + oy
                pygame.draw.circle(surf, (70, 70, 66), (px, py), 0.06 * k)
                d += spacing
        for f in (0.25, 0.5, 0.75):
            px, py = c0[0] + dx * f, c0[1] + dy * f
            pygame.draw.circle(surf, (78, 82, 72), (px, py), r * 0.62 * k)
            pygame.draw.circle(surf, (52, 56, 48), (px, py), r * 0.22 * k)
        draw_wheels()
    elif rig == "shark":                                   # the tail fin beats faster the faster it swims
        t = pygame.time.get_ticks() / 1000
        a = 0.12 if still else math.sin(t * 7.0) * 0.35
        size = styling.SHARK_SCALE[styling.shark_stage(levels)]
        root = (-1.7 * size, 0.1 + (0.08 - 0.1) * size)
        fin = [(0.0, 0.0), (-0.75, 0.75), (-0.55, 0.08), (-0.75, -0.6)]
        ca, sa = math.cos(a), math.sin(a)
        pts = [P(root[0] + (x * ca - y * sa * 0.3) * size, root[1] + (y + x * sa * 0.6) * size) for x, y in fin]
        pygame.draw.polygon(surf, (86, 106, 128), pts)
        pygame.draw.polygon(surf, (30, 40, 52), pts, max(1, int(0.02 * k)))
    elif rig == "hover":
        t = pygame.time.get_ticks() / 1000
        for i, c in enumerate(centres):
            pulse = 0.8 + 0.2 * math.sin(t * 18 + i)
            for j, (col, size) in enumerate((((60, 200, 255), 0.5), ((150, 240, 255), 0.32), ((240, 255, 255), 0.16))):
                rr = pygame.Rect(0, 0, size * k * 1.4 * pulse, size * k * 0.5 * pulse)
                rr.center = (c[0], c[1] - 0.2 * k)
                glow = pygame.Surface(rr.size, pygame.SRCALPHA)
                pygame.draw.ellipse(glow, (*col, 120 + j * 50), glow.get_rect())
                surf.blit(glow, rr)
    elif rig == "bike":
        draw_wheels()
        pivot = P(*spec["pivot"])
        pygame.draw.line(surf, (54, 56, 62), pivot, centres[0], max(2, int(0.11 * k)))
        pygame.draw.circle(surf, (54, 56, 62), centres[0], 0.07 * k)
        top = P(*spec["fork_top"])
        dx, dy = centres[1][0] - top[0], centres[1][1] - top[1]
        L = math.hypot(dx, dy) or 1
        px, py = -dy / L * 0.035 * k, dx / L * 0.035 * k
        for sgn in (-1, 1):
            pygame.draw.line(surf, (214, 220, 228), (top[0] + px * sgn, top[1] + py * sgn),
                             (centres[1][0] + px * sgn, centres[1][1] + py * sgn), max(2, int(0.05 * k)))
        mid = (top[0] + dx * 0.45, top[1] + dy * 0.45)
        pygame.draw.line(surf, (230, 170, 30), top, mid, max(2, int(0.1 * k)))
    else:
        for (ax, ay), ctr, w in zip(anchors, centres, spec["wheels"]):
            a = P(ax, ay)
            if rig == "gear":
                pygame.draw.line(surf, (40, 42, 48), a, ctr, max(2, int(0.07 * k)))
                continue
            thick = 0.1 if w[2] < 0.6 else 0.16
            pygame.draw.line(surf, (52, 54, 60), a, ctr, max(2, int(thick * k)))
            dx, dy = ctr[0] - a[0], ctr[1] - a[1]
            length = math.hypot(dx, dy) or 1
            ux, uy = -dy / length, dx / length
            amp = (0.075 if w[2] < 0.6 else 0.13) * k
            pts = [a]
            for i in range(1, 14):
                side = amp if i % 2 else -amp
                pts.append((a[0] + dx * i / 14 + ux * side, a[1] + dy * i / 14 + uy * side))
            pts.append(ctr)
            pygame.draw.lines(surf, _spring_color(looks, w[2] > 0.6), False, pts,
                              max(2, int((0.05 if w[2] > 0.6 else 0.035) * k)))

    body = pygame.transform.rotozoom(va.styled(levels), math.degrees(angle), scale)
    hx, hy = spec["head"][0] + wobble[0], spec["head"][1] + wobble[1]
    head = pygame.transform.rotozoom(va.head, math.degrees(angle + wobble[2]), scale)
    head_pos = P(hx, hy)
    body_pos = P(0.0, 0.0)
    _aura(surf, va, looks, scale, angle, body_pos, now_t)
    _pipes(surf, P, k, spec, looks, now_t, still, rpm)
    if spec.get("head_behind"):
        surf.blit(head, head.get_rect(center=head_pos))
        surf.blit(body, body.get_rect(center=body_pos))
    else:
        surf.blit(body, body.get_rect(center=body_pos))
        surf.blit(head, head.get_rect(center=head_pos))
    styling.draw_spoiler(surf, P, k, spec, looks)
    _underglow(surf, P, k, spec, looks, now_t, False)
    _sparkles(surf, P, k, spec, looks, now_t)
    if rig not in ("bike", "tank", "hover", "shark"):
        draw_wheels()
    if rig not in ("bike", "tank"):
        _rims(surf, k, spec, looks, centres, wheels, now_t)
    if spec.get("lightbar"):
        t = pygame.time.get_ticks() / 1000
        for i, (lx, ly) in enumerate(spec["lightbar"]):
            on = (int(t * 7) + i) % 2 == 0
            col = (255, 40, 40) if i % 2 == 0 else (40, 110, 255)
            p = P(lx, ly)
            pygame.draw.circle(surf, col if on else gfx.shade(col, 0.4), p, 0.11 * k)
            if on:
                glow = sprites.soft_puff(max(2, int(0.5 * k)), col)
                surf.blit(glow, glow.get_rect(center=p))


class Backdrop:
    """Sky gradient plus parallax silhouettes and weather for one stage."""

    SUNS = {"clouds": ((255, 252, 230), 0.84, 0.16, 40), "sun": ((255, 248, 222), 0.76, 0.3, 54),
            "snow": ((255, 255, 250), 0.18, 0.14, 34), "city": ((255, 246, 220), 0.8, 0.2, 38),
            "citynight": ((236, 236, 250), 0.22, 0.16, 26),
            "jungle": ((255, 250, 220), 0.78, 0.14, 36), "mars": ((255, 240, 220), 0.7, 0.22, 20),
            "seasons": ((255, 250, 228), 0.8, 0.18, 42)}
    SHAPES = {"clouds": 0, "sun": 1, "snow": 2, "space": 3, "city": 4, "citynight": 4, "volcano": 5, "jungle": 0, "mars": 1,
              "seasons": 0, "ocean": 0}
    WEATHER = {"snow": "snow", "jungle": "rain", "volcano": "embers", "mars": "dust", "ocean": "bubbles"}
    BIRDS = {"clouds": "flock", "jungle": "flock", "seasons": "flock", "sun": "vultures", "ocean": "fish"}

    def __init__(self, stage):
        self.stage = stage
        W, H = gfx.W, gfx.H
        rnd = random.Random(stage["seed"])
        if stage.get("seasons"):
            # one sky per season (with its own sun); draw() fades from one to the next
            self.season_skies = [self._sky(dict(stage, sky=sn["sky"], decor=sn["decor"]), random.Random(1))
                                 for sn in stage["seasons"]]
        self.sky = self._sky(stage, rnd)
        decor = stage["decor"]
        self.night = lighting.night_sky(stage, W, H) if stage.get("cycle") else None
        self.sunset = lighting.sunset_sky(W, H) if stage.get("cycle") else None
        self.clouds = []
        tint = {"sun": (255, 246, 230), "volcano": (74, 56, 56), "mars": (236, 196, 170),
                "citynight": (70, 64, 100)}.get(decor, (255, 255, 255))
        if decor not in ("space", "ocean"):
            n = 6 if decor != "mars" else 3
            for i in range(n):
                w = gfx.s(rnd.uniform(170, 290))
                self.clouds.append(((i + rnd.uniform(0.1, 0.6)) / n, rnd.uniform(0.06, 0.34),
                                    sprites.cloud(w, w * 0.42, tint), rnd.uniform(0.04, 0.09)))
        self.weather = self.WEATHER.get(decor)
        self.flakes = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.6, 1.4)]
                       for _ in range(220 if stage.get("seasons") else
                                      {"snow": 160, "rain": 220, "embers": 90, "dust": 120,
                                       "bubbles": 70}.get(self.weather, 0))]
        self.birds = self.BIRDS.get(decor)
        self.flocks = [[rnd.uniform(0, W * 1.5), rnd.uniform(0.08, 0.3) * H, rnd.uniform(0.5, 1.0), rnd.randint(3, 6),
                        rnd.uniform(0, 6)] for _ in range(2)] if self.birds else []

    def _sky(self, stage, rnd):
        W, H = gfx.W, gfx.H
        sky = gfx.opaque(gfx.vgradient(W, H, *stage["sky"]))
        decor = stage["decor"]
        if decor == "space":
            for _ in range(int(W * H / 2600)):
                x, y = rnd.uniform(0, W), rnd.uniform(0, H * 0.75)
                b = rnd.randint(140, 255)
                r = rnd.choice((1, 1, 1, 1.5, 2)) * gfx.U
                pygame.draw.circle(sky, (b, b, min(255, b + 20)), (x, y), r)
            self._earth(sky, W * 0.8, H * 0.18, gfx.s(46))
        elif decor == "volcano":
            glow = sprites.soft_puff(gfx.s(420), (255, 120, 40))
            sky.blit(glow, glow.get_rect(center=(W * 0.62, H * 0.62)))
        elif decor == "ocean":                      # sunlight falling through the water from the surface
            rays = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(9):
                x = W * (0.05 + i * 0.12 + rnd.uniform(-0.03, 0.03))
                wd = gfx.s(rnd.uniform(30, 70))
                pygame.draw.polygon(rays, (190, 236, 255, 26), [(x, 0), (x + wd, 0), (x + wd * 2.6 - gfx.s(120), H),
                                                                 (x + wd * 1.2 - gfx.s(160), H)])
            sky.blit(rays, (0, 0))
            shine = gfx.vgradient(W, int(H * 0.12), (200, 240, 255, 90), (200, 240, 255, 0)).convert_alpha()
            sky.blit(shine, (0, 0))
        else:
            sun = self.SUNS[decor]
            glow = sprites.soft_puff(gfx.s(sun[3] * 3.4), sun[0])
            sky.blit(glow, glow.get_rect(center=(W * sun[1], H * sun[2])))
            pygame.draw.circle(sky, sun[0], (W * sun[1], H * sun[2]), gfx.s(sun[3]))
            if decor == "mars":                       # Phobos and Deimos
                for x, y, r in ((0.22, 0.14, 9), (0.34, 0.24, 5)):
                    pygame.draw.circle(sky, (210, 180, 160), (W * x, H * y), gfx.s(r))
                    pygame.draw.circle(sky, (180, 150, 130), (W * x + gfx.s(r * 0.3), H * y + gfx.s(r * 0.2)), gfx.s(r * 0.35))
        return sky

    @staticmethod
    def _earth(surf, x, y, r):
        def draw(s, k):
            c = s.get_width() / 2
            R = r * k
            pygame.draw.circle(s, (54, 120, 220), (c, c), R)
            for ox, oy, rr in ((-0.3, -0.2, 0.35), (0.25, 0.1, 0.3), (-0.1, 0.45, 0.22), (0.45, -0.4, 0.15)):
                pygame.draw.circle(s, (80, 170, 90), (c + ox * R, c + oy * R), rr * R)
            pygame.draw.circle(s, (240, 248, 255, 140), (c + 0.1 * R, c - 0.55 * R), 0.22 * R)
            shadow = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(shadow, (0, 0, 20, 150), (c + R * 0.45, c + R * 0.3), R)
            mask = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), R)
            shadow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            s.blit(shadow, (0, 0))
        img = gfx.supersample(2 * r + 2, 2 * r + 2, draw)
        surf.blit(img, img.get_rect(center=(x, y)))

    def draw(self, surf, cam, dt, darkness=0.0, sunset=0.0, look=None):
        """look: the stage as it looks right now (seasons change colours, sky and weather)."""
        W, H = gfx.W, gfx.H
        season = (look or {}).get("season")
        if season:
            i, j, k = season
            surf.blit(self.season_skies[i], (0, 0))
            if k > 0:
                self.season_skies[j].set_alpha(int(255 * k))
                surf.blit(self.season_skies[j], (0, 0))
                self.season_skies[j].set_alpha(None)
            current = self.stage["seasons"][j if k > 0.5 else i]
            self.weather = current["weather"]
            self.birds = "flock" if current["name"] in ("SPRING", "SUMMER") else None
        else:
            surf.blit(self.sky, (0, 0))
        if self.sunset is not None and sunset > 0.01:
            self.sunset.set_alpha(int(170 * sunset))
            surf.blit(self.sunset, (0, 0))
        night = min(1.0, darkness / 0.78) if self.night is not None else 0.0
        if night > 0.01:
            self.night.set_alpha(int(255 * night))
            surf.blit(self.night, (0, 0))
        span = W + gfx.s(700)
        if night < 0.95:
            for fx, fy, img, par in self.clouds:
                x = (fx * span - cam.x * cam.ppm * par) % span - gfx.s(350)
                if night > 0.05:
                    img = img.copy()
                    img.set_alpha(int(255 * (1 - night)))
                surf.blit(img, (x, fy * H + cam.y * cam.ppm * 0.02))
        st = look or self.stage
        far, near = st["far"]
        if night > 0:
            far = gfx.mix(far, (24, 30, 60), night * 0.55)
            near = gfx.mix(near, (18, 24, 50), night * 0.55)
        shape = self.SHAPES[st["decor"]]
        if shape == 4:
            lit = 1.0 if st["decor"] == "citynight" else night       # neon cities: every window lit
            self._skyline(surf, cam, far, 0.05, 0.62, 1.0, lit, 3)
            self._skyline(surf, cam, near, 0.12, 0.74, 0.75, lit, 9)
        elif shape == 5:
            self._volcanoes(surf, cam, far, near)
        else:
            self._ridge(surf, cam, far, 0.05, 0.58, gfx.s(80), shape, 0.0, None)
            trees = {"clouds": "round", "snow": "pine", "jungle": "jungle", "seasons": "round",
                     "ocean": "kelp"}.get(st["decor"])
            if season and self.stage["seasons"][season[0]]["name"] == "WINTER":
                trees = "pine"
            self._ridge(surf, cam, near, 0.13, 0.7, gfx.s(55), shape, 2.0, trees)
        if night < 0.6:
            self._birds(surf, cam, dt)
        self._weather(surf, cam, dt)

    def _birds(self, surf, cam, dt):
        """Little flocks crossing the sky (vultures circle over the desert)."""
        if not self.birds:
            return
        W, H, U = gfx.W, gfx.H, gfx.U
        t = pygame.time.get_ticks() / 1000
        col = (40, 44, 56)
        for f in self.flocks:
            f[0] -= (24 + 30 * f[2]) * U * dt
            if f[0] < -gfx.s(200):
                f[0] = W + gfx.s(random.uniform(200, 900))
                f[1] = random.uniform(0.08, 0.3) * H
            for n in range(f[3]):
                if self.birds == "fish":                   # a little school of fish
                    x, y = f[0] + n * gfx.s(22), f[1] + math.sin(t * 2 + n) * gfx.s(6) + (n % 2) * gfx.s(10)
                    L = (7 + 3 * f[2]) * U
                    pygame.draw.ellipse(surf, (230, 170, 60) if n % 2 else (250, 210, 90), (x - L, y - L * 0.4, L * 2, L * 0.8))
                    tail = math.sin(t * 10 + n) * L * 0.25
                    pygame.draw.polygon(surf, (220, 140, 40), [(x + L * 0.8, y), (x + L * 1.5, y - L * 0.45 + tail),
                                                               (x + L * 1.5, y + L * 0.45 + tail)])
                    pygame.draw.circle(surf, (20, 20, 30), (x - L * 0.55, y - L * 0.08), max(1, L * 0.12))
                    continue
                if self.birds == "vultures":
                    a = t * 0.5 + n * math.tau / f[3]
                    x, y = f[0] + math.cos(a) * gfx.s(60), f[1] + math.sin(a) * gfx.s(18)
                    size = 9 * U
                else:
                    x, y = f[0] + n * gfx.s(16), f[1] + abs(n - f[3] // 2) * gfx.s(8)
                    size = 6 * U * f[2] + 3 * U
                flap = math.sin(t * 9 + n + f[4]) * 0.6
                pygame.draw.lines(surf, col, False, [(x - size, y - size * flap), (x, y), (x + size, y - size * flap)],
                                  max(1, int(1.6 * U)))

    def _weather(self, surf, cam, dt):
        kind = self.weather
        if not self.flakes or not kind:
            return
        W, H, U = gfx.W, gfx.H, gfx.U
        for f in self.flakes:
            if kind == "snow":
                f[1] += (40 + 50 * f[2]) * U * dt
                f[0] -= 18 * f[2] * U * dt
            elif kind == "rain":
                f[1] += (700 + 300 * f[2]) * U * dt
                f[0] -= 120 * U * dt
            elif kind == "embers":
                f[1] -= (30 + 40 * f[2]) * U * dt
                f[0] += math.sin(f[1] * 0.02 + f[2] * 9) * 20 * U * dt
            elif kind == "bubbles":
                f[1] -= (40 + 50 * f[2]) * U * dt
                f[0] += math.sin(f[1] * 0.03 + f[2] * 5) * 12 * U * dt
            elif kind in ("petals", "leaves"):
                f[1] += (30 + 30 * f[2]) * U * dt
                f[0] += (math.sin(f[1] * 0.015 + f[2] * 7) * 40 - 25) * U * dt
            else:
                f[0] -= (260 + 200 * f[2]) * U * dt
                f[1] += 15 * U * dt
            if f[1] > H:
                f[1] -= H + 10
            if f[1] < -10:
                f[1] += H + 10
            sx = (f[0] - cam.x * cam.ppm * 0.3 * f[2]) % W
            if kind == "snow":
                pygame.draw.circle(surf, (255, 255, 255), (sx, f[1]), 1.6 * f[2] * U)
            elif kind == "rain":
                pygame.draw.line(surf, (200, 220, 240), (sx, f[1]), (sx - 4 * U, f[1] + 16 * U * f[2]), max(1, int(U)))
            elif kind == "embers":
                pygame.draw.circle(surf, (255, 150 + int(60 * f[2]) % 100, 40), (sx, f[1]), 1.5 * f[2] * U)
            elif kind == "bubbles":
                pygame.draw.circle(surf, (200, 240, 255), (sx, f[1]), 3 * f[2] * U, max(1, int(U)))
            elif kind == "petals":
                r = pygame.Rect(0, 0, 5 * f[2] * U, 3 * f[2] * U)
                r.center = (sx, f[1])
                pygame.draw.ellipse(surf, (250, 190, 214) if f[2] > 1 else (255, 226, 238), r)
            elif kind == "leaves":
                a = f[1] * 0.03 + f[2] * 5
                L = 5 * f[2] * U
                col = ((206, 90, 30), (236, 150, 40), (180, 60, 30))[int(f[2] * 10) % 3]
                pygame.draw.polygon(surf, col, [(sx + math.cos(a) * L, f[1] + math.sin(a) * L * 0.5), (sx, f[1] - L * 0.4),
                                                (sx - math.cos(a) * L, f[1] - math.sin(a) * L * 0.5), (sx, f[1] + L * 0.4)])
            else:
                pygame.draw.line(surf, (236, 176, 130), (sx, f[1]), (sx + 22 * U * f[2], f[1]), max(1, int(U)))

    @staticmethod
    def _skyline(surf, cam, color, par, base_frac, scale, night, seed):
        W, H = gfx.W, gfx.H
        phase = cam.x * cam.ppm * par
        base = H * base_frac + cam.y * cam.ppm * par * 0.6
        bw = gfx.s(70 * scale)
        first = int((phase - bw) // bw)
        win = gfx.mix((255, 220, 120), color, 0.0)
        for i in range(first, first + int(W / bw) + 3):
            hgt = gfx.s((80 + 220 * _hash(i, seed)) * scale)
            w = bw * (0.7 + 0.28 * _hash(i, seed + 1))
            x = i * bw - phase
            r = pygame.Rect(x, base - hgt, w, H - base + hgt)
            pygame.draw.rect(surf, color, r)
            if _hash(i, seed + 2) > 0.6:
                pygame.draw.rect(surf, color, (x + w * 0.4, base - hgt - gfx.s(26 * scale), gfx.s(4), gfx.s(26 * scale)))
            if night > 0.2:
                for wy in range(int(r.y + gfx.s(10)), int(base), int(gfx.s(16 * scale)) or 1):
                    for wx in range(int(x + gfx.s(6)), int(x + w - gfx.s(8)), int(gfx.s(14 * scale)) or 1):
                        if _hash(wx // 7 + i * 31, wy // 7) < 0.4:
                            pygame.draw.rect(surf, gfx.mix(color, win, night), (wx, wy, gfx.s(6 * scale), gfx.s(8 * scale)))

    @staticmethod
    def _volcanoes(surf, cam, far, near):
        W, H = gfx.W, gfx.H
        for color, par, base_frac, size, seed in ((far, 0.04, 0.62, 1.0, 3), (near, 0.1, 0.74, 0.7, 8)):
            phase = cam.x * cam.ppm * par
            gap = gfx.s(520 * size)
            first = int((phase - gap) // gap)
            base = H * base_frac + cam.y * cam.ppm * par * 0.6
            for i in range(first, first + int(W / gap) + 3):
                cx = i * gap - phase + _hash(i, seed) * gap * 0.4
                hgt = gfx.s((170 + 120 * _hash(i, seed + 1)) * size)
                half = hgt * 1.5
                top = base - hgt
                pygame.draw.polygon(surf, color, [(cx - half, base + 2), (cx - hgt * 0.18, top), (cx + hgt * 0.18, top),
                                                  (cx + half, base + 2)])
                pygame.draw.ellipse(surf, (255, 140, 40), (cx - hgt * 0.16, top - gfx.s(5), hgt * 0.32, gfx.s(12)))
                for k in (-1, 1):
                    pygame.draw.polygon(surf, (230, 90, 30), [(cx + k * hgt * 0.06, top + 2), (cx + k * hgt * 0.13, top + 2),
                                                             (cx + k * hgt * 0.24, top + hgt * 0.32),
                                                             (cx + k * hgt * 0.2, top + hgt * 0.34)])
            pygame.draw.rect(surf, color, (0, base, W, H - base))

    @staticmethod
    def _ridge(surf, cam, color, par, base_frac, amp, shape, seed, trees):
        W, H = gfx.W, gfx.H
        phase = cam.x * cam.ppm * par
        base = H * base_frac + (cam.y * cam.ppm * par * 0.6)
        step = max(6, int(gfx.s(14)))

        def ridge_y(sx):
            u = (sx + phase) / gfx.U
            if shape == 2:      # sharp icy peaks
                v = 1 - abs(math.sin(u / 210 + seed)) * 1.6 + 0.3 * math.sin(u / 73 + seed * 3)
            elif shape == 1:    # flat-topped mesas
                v = max(-0.4, min(0.5, math.sin(u / 260 + seed) * 1.4)) + 0.12 * math.sin(u / 41)
            else:
                v = 0.6 * math.sin(u / 230 + seed) + 0.3 * math.sin(u / 97 + seed * 2) + 0.1 * math.sin(u / 37)
            return base - v * amp
        pts = [(sx, ridge_y(sx)) for sx in range(-step, W + 2 * step, step)]
        pts += [(W + step, H), (-step, H)]
        if trees:
            col = gfx.shade(color, 0.86)
            gap = gfx.s(14 if trees == "jungle" else 26)
            first = int((phase - gfx.s(60)) // gap)
            for i in range(first, first + int(W / gap) + 6):
                if trees != "jungle" and _hash(i, 7) < 0.45:
                    continue
                sx = i * gap - phase + _hash(i, 8) * gap * 0.6
                y = ridge_y(sx)
                size = gfx.s(10 + 12 * _hash(i, 9)) * (1.6 if trees == "jungle" else 1.0)
                if trees == "kelp":
                    for kk in range(int(size * 0.35)):
                        pygame.draw.line(surf, col, (sx + math.sin(kk * 0.5) * size * 0.15, y - kk * 2.6),
                                         (sx + math.sin(kk * 0.5 + 0.5) * size * 0.15, y - kk * 2.6 - 2.6), max(2, int(size * 0.18)))
                elif trees in ("round", "jungle"):
                    pygame.draw.circle(surf, col, (sx, y - size * 0.6), size)
                    pygame.draw.rect(surf, col, (sx - size * 0.15, y - size * 0.4, size * 0.3, size))
                else:
                    pygame.draw.polygon(surf, col, [(sx - size * 0.7, y + 2), (sx + size * 0.7, y + 2), (sx, y - size * 2.4)])
        pygame.draw.polygon(surf, color, pts)


class WorldRenderer:
    def __init__(self, stage, terrain, art):
        self.stage, self.terrain, self.art = stage, terrain, art
        self.base_stage = stage                   # self.stage is how it looks right now (seasons)
        self.backdrop = Backdrop(stage)
        self.mark_x = [m[0] for m in terrain.landmarks]
        self.coin_x = [c[0] for c in terrain.coins]
        self.nitro_x = [n[0] for n in terrain.nitro]
        self.prop_x = [p[0] for p in terrain.props]
        self.glow = sprites.soft_puff(gfx.s(60), (255, 214, 120))
        self.lighting = lighting.Lighting()
        self._lamps = []
        self.clock = None               # run time that moves the obstacles (None: the app clock)
        self.broken = set()             # crate walls already smashed

    # -------------------------------------------------------------- terrain
    def draw_terrain(self, surf, cam, now):
        st, t = self.stage, self.terrain
        x0, x1 = cam.view(1.0)
        i0 = max(0, int((x0 - START) / RES))
        i1 = min(t.n - 1, int((x1 - START) / RES) + 2)
        ppm = cam.ppm
        cx, cy = gfx.W / 2 - cam.x * ppm, gfx.H / 2 + cam.y * ppm
        v = t.v
        pts = [(cx + (START + i * RES) * ppm, cy - v[i] * ppm) for i in range(i0, i1 + 1)]
        bottom = gfx.H + 40
        pygame.draw.polygon(surf, st["ground"], pts + [(pts[-1][0], bottom), (pts[0][0], bottom)])

        self._draw_pebbles(surf, cam, x0, x1)

        depth = st["top_depth"] * ppm
        inner, soil = [], []
        n = len(pts)
        for i in range(n):
            ax, ay = pts[max(0, i - 1)]
            bx, by = pts[min(n - 1, i + 1)]
            tx, ty = bx - ax, by - ay
            inv = 1.0 / (math.hypot(tx, ty) or 1.0)
            nx, ny = -ty * inv, tx * inv
            inner.append((pts[i][0] + nx * depth, pts[i][1] + ny * depth))
            soil.append((pts[i][0] + nx * depth * 2.2, pts[i][1] + ny * depth * 2.2))
        pygame.draw.polygon(surf, gfx.mix(st["ground"], st["top_lo"], 0.35), inner + soil[::-1])
        pygame.draw.polygon(surf, st["top"], pts + inner[::-1])
        lw = max(2, int(gfx.s(2.5)))
        pygame.draw.lines(surf, st["top_lo"], False, inner, lw)
        hi = [(x, y + lw * 0.6) for x, y in pts]
        pygame.draw.lines(surf, st["top_hi"], False, hi, max(2, int(gfx.s(3.5))))
        self._draw_obstacles(surf, cam, x0, x1, now)

        for a, b, level in t.bridges:
            if b > x0 and a < x1:
                if level is not None:
                    self._draw_water(surf, cam, a, b, level, now)
                self._draw_bridge(surf, cam, a, b)
        for a, b, risers in t.steps:
            if b > x0 and a < x1:
                self._draw_steps(surf, cam, risers)
        for a, b in t.tunnels:
            if b > x0 - 2 and a < x1 + 2:
                if t.cave_at(a):
                    self._draw_cave(surf, cam, a, b, now)
                else:
                    self._draw_tunnel(surf, cam, a, b, now)
        for a, b, level in t.pits:
            if b > x0 and a < x1:
                if st.get("lava"):
                    self._draw_water(surf, cam, a - 0.3, b + 0.3, level, now)
                else:
                    self._draw_gap(surf, cam, a, b)
        if st["key"] == "city" or st.get("street"):
            dash = max(2, int(gfx.s(3)))
            for i in range(i0 - i0 % 12, i1 - 6, 12):
                if t.feature_at(START + i * RES) in ("bridge", "tunnel", "pit", "cars", "traffic"):
                    continue
                p0 = cam.to_screen(START + i * RES, t.v[i] - st["top_depth"] * 0.45)
                p1 = cam.to_screen(START + (i + 6) * RES, t.v[i + 6] - st["top_depth"] * 0.45)
                pygame.draw.line(surf, (236, 230, 200), p0, p1, dash)
        elif st["key"] == "volcano":
            for i in range(i0 - i0 % 9, i1 - 3, 9):
                if _hash(i, 77) < 0.55:
                    continue
                x = START + i * RES
                p0 = cam.to_screen(x, t.v[i] - 0.05)
                p1 = cam.to_screen(x + 0.4, t.v[i] - 0.45)
                p2 = cam.to_screen(x + 0.15, t.v[i] - 0.8)
                pygame.draw.lines(surf, (255, 120, 30), False, [p0, p1, p2], max(1, int(gfx.s(2.5))))

    # colour, depth below the surface, how far it sits on top of the surface (m)
    ZONE_LOOK = {"mud": ((66, 42, 24), 0.6, 0.14), "ice": ((150, 214, 248), 0.32, 0.07),
                 "snow": ((252, 253, 255), 0.62, 0.16), "sand": ((206, 160, 86), 0.5, 0.12),
                 "oil": ((14, 14, 20), 0.2, 0.04), "seaweed": ((40, 110, 60), 0.3, 0.1)}

    def _draw_obstacles(self, surf, cam, x0, x1, now):
        t = self.terrain
        ppm = cam.ppm
        lw = max(1, int(gfx.s(2)))
        for a, b, kind in t.zones:
            if b < x0 or a > x1:
                continue
            col, depth, raise_ = self.ZONE_LOOK[kind]
            i0, i1 = int((a - START) / RES), int((b - START) / RES)
            top, low = [], []
            for i in range(i0, i1 + 1):
                u = (i - i0) / max(1, i1 - i0)
                k = math.sin(math.pi * u) ** 0.35                # thin at both ends
                x = START + i * RES
                wobble = 0.04 * math.sin(i * 0.9) if kind in ("mud", "sand") else 0.0
                top.append(cam.to_screen(x, t.v[i] + (raise_ + wobble) * k))
                low.append(cam.to_screen(x, t.v[i] - depth * k))
            pygame.draw.polygon(surf, gfx.shade(col, 0.7), [(px, py + 2) for px, py in top] + low[::-1])
            pygame.draw.polygon(surf, col, top + low[::-1])
            if kind == "mud":                                   # wet shine and bubbles
                pygame.draw.lines(surf, (128, 96, 64), False, top[2:-2], max(2, lw * 2))
                for j in range(3, len(top) - 3, 7):
                    if _hash(j, int(a)) < 0.5:
                        r = (0.05 + 0.04 * math.sin(now * 3 + j)) * ppm
                        pygame.draw.circle(surf, (120, 90, 60), (top[j][0], top[j][1] + 0.12 * ppm), max(1, r))
            elif kind in ("ice", "oil"):                        # glossy streaks
                shine = (255, 255, 255) if kind == "ice" else (120, 60, 160)
                for j in range(4, len(top) - 6, 9):
                    pygame.draw.line(surf, shine, (top[j][0], top[j][1] + 2), (top[j + 3][0], top[j + 3][1] + 2), lw)
                if kind == "oil":
                    for j in range(6, len(top) - 6, 13):
                        pygame.draw.line(surf, (60, 160, 120), (top[j][0], top[j][1] + 3), (top[j + 2][0], top[j + 2][1] + 3),
                                         lw)
            elif kind == "snow":
                pygame.draw.lines(surf, (200, 220, 245), False, low[2:-2], lw)
            elif kind == "seaweed":                             # a thicket of swaying strands
                for j in range(2, len(top) - 2, 3):
                    sway = math.sin(now * 2 + j) * 0.25 * ppm
                    h = (0.7 + 0.6 * _hash(j, int(a))) * ppm
                    pygame.draw.line(surf, (50, 140, 70), top[j], (top[j][0] + sway, top[j][1] - h), max(2, int(0.08 * ppm)))
            elif kind == "sand":                                # wind ripples
                for j in range(3, len(top) - 4, 5):
                    p = (top[j][0], top[j][1] + 0.12 * ppm)
                    pygame.draw.line(surf, (196, 164, 100), p, (p[0] + 0.25 * ppm, p[1] - 0.02 * ppm), lw)
        for x, kind, length in t.bumps:
            if x + length < x0 or x - length > x1:
                continue
            a, b = x - length / 2, x + length / 2
            pts = self._span_points(cam, a, b, t.v, 0.04)
            base = [cam.to_screen(a, t.v[int((a - START) / RES)] - 0.15), cam.to_screen(b, t.v[int((b - START) / RES)] - 0.15)]
            if kind == "rocks":
                pygame.draw.polygon(surf, (104, 104, 110), pts + base[::-1])
                pygame.draw.lines(surf, (150, 150, 158), False, pts[1:-1], max(2, int(gfx.s(3))))
                m = len(pts) // 2
                for j in (m - len(pts) // 4, m + len(pts) // 5):
                    pygame.draw.line(surf, (70, 70, 76), pts[j], (pts[j][0] + 0.1 * ppm, pts[j][1] + 0.35 * ppm), lw)
            elif kind == "log":
                pygame.draw.polygon(surf, (120, 76, 40), pts + base[::-1])
                pygame.draw.lines(surf, (156, 106, 62), False, pts[1:-1], max(2, int(gfx.s(3))))
                end = pts[-2]
                r = 0.26 * ppm
                pygame.draw.circle(surf, (196, 150, 96), (end[0] - r * 0.6, end[1] + r), r)
                pygame.draw.circle(surf, (150, 100, 60), (end[0] - r * 0.6, end[1] + r), r * 0.55, lw)
            else:                                               # yellow-black speed bump
                pygame.draw.polygon(surf, (250, 200, 30), pts + base[::-1])
                for j in range(1, len(pts) - 1, 3):
                    pygame.draw.line(surf, (30, 30, 34), pts[j], (pts[j][0], pts[j][1] + 0.3 * ppm), max(2, int(0.12 * ppm)))

    def _span_points(self, cam, a, b, arr, offset=0.0):
        i0, i1 = int((a - START) / RES), int((b - START) / RES)
        return [cam.to_screen(START + i * RES, arr[i] + offset) for i in range(i0, i1 + 1)]

    def _draw_water(self, surf, cam, a, b, level, now):
        t = self.terrain
        i0, i1 = int((a - START) / RES), int((b - START) / RES)
        idx = [i for i in range(i0, i1 + 1) if t.v[i] < level]
        if len(idx) < 2:
            return
        top_l = cam.to_screen(START + idx[0] * RES, level)
        top_r = cam.to_screen(START + idx[-1] * RES, level)
        bed = [cam.to_screen(START + i * RES, t.v[i]) for i in idx]
        col = self.stage["water"]
        poly = [top_l] + bed + [top_r]
        x0 = min(p[0] for p in poly) - 4
        y0 = min(p[1] for p in poly) - 4
        w = max(p[0] for p in poly) - x0 + 8
        h = max(p[1] for p in poly) - y0 + 8
        if w <= 0 or h <= 0 or w > gfx.W * 3 or h > gfx.H * 3:
            return
        layer = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
        local = [(x - x0, y - y0) for x, y in poly]
        a_, b_ = local[0], local[-1]
        if self.stage.get("lava"):
            pygame.draw.polygon(layer, (*col, 255), local)
            deep = [(x, max(y, a_[1] + gfx.s(18))) for x, y in local]
            pygame.draw.polygon(layer, (200, 50, 10, 255), deep)
            pygame.draw.line(layer, (255, 230, 120, 255), a_, b_, max(3, int(gfx.s(5))))
            for k in range(7):
                fx = (k * 0.37 + now * 0.07) % 1
                life = (now * 1.3 + k * 0.29) % 1
                bx = a_[0] + (b_[0] - a_[0]) * fx
                pygame.draw.circle(layer, (255, 210, 90, 255), (bx, a_[1] + gfx.s(4) - life * gfx.s(6)),
                                   gfx.s(3 + 4 * (1 - life)), max(1, int(gfx.s(2))))
            surf.blit(layer, (x0, y0))
            for k in range(3):
                self._lamps.append(((top_l[0] + (top_r[0] - top_l[0]) * (k + 0.5) / 3), top_l[1]))
            return
        pygame.draw.polygon(layer, (*col, 215), local)
        pygame.draw.line(layer, (*gfx.shade(col, 1.45), 255), a_, b_, max(2, int(gfx.s(3))))
        for k in range(6):
            fx = (k / 6 + now * 0.05) % 1
            wx = a_[0] + (b_[0] - a_[0]) * fx
            pygame.draw.line(layer, (255, 255, 255, 120), (wx, a_[1] + gfx.s(8)), (wx + gfx.s(14), a_[1] + gfx.s(8)),
                             max(1, int(gfx.s(2))))
        surf.blit(layer, (x0, y0))

    def _draw_bridge(self, surf, cam, a, b):
        t, ppm = self.terrain, cam.ppm
        wood, dark, rope = (172, 116, 64), (104, 66, 34), (196, 170, 120)
        deck = self._span_points(cam, a, b, t.h)
        under = self._span_points(cam, a, b, t.h, -0.2)
        pygame.draw.polygon(surf, wood, deck + under[::-1])
        pygame.draw.lines(surf, dark, False, under, max(2, int(0.05 * ppm)))
        pygame.draw.lines(surf, gfx.shade(wood, 1.25), False, deck, max(2, int(0.04 * ppm)))
        i0, i1 = int((a - START) / RES), int((b - START) / RES)
        step = max(1, int(0.5 / RES))
        for i in range(i0, i1 + 1, step):
            x = START + i * RES
            p, q = cam.to_screen(x, t.h[i]), cam.to_screen(x, t.h[i] - 0.2)
            pygame.draw.line(surf, dark, p, q, max(1, int(0.03 * ppm)))
        # posts, ropes and hangers
        ha, hb = t.h[i0], t.h[i1]
        for x, hgt in ((a - 0.15, ha), (b + 0.15, hb)):
            base = cam.to_screen(x, hgt - 0.4)
            top = cam.to_screen(x, hgt + 1.35)
            pygame.draw.line(surf, dark, base, top, max(3, int(0.2 * ppm)))
            pygame.draw.line(surf, wood, base, top, max(2, int(0.12 * ppm)))
        rope_pts = []
        for i in range(i0, i1 + 1, 2):
            f = (i - i0) / max(1, i1 - i0)
            x = START + i * RES
            sag = 0.55 * math.sin(math.pi * f)
            ry = t.h[i] + 1.2 - sag + 0.3 * sag
            rope_pts.append(cam.to_screen(x, ry))
            if (i - i0) % 4 == 0:
                pygame.draw.line(surf, rope, cam.to_screen(x, ry), cam.to_screen(x, t.h[i]), max(1, int(0.025 * ppm)))
        if len(rope_pts) > 1:
            pygame.draw.lines(surf, rope, False, rope_pts, max(2, int(0.05 * ppm)))

    def _draw_tunnel(self, surf, cam, a, b, now):
        t, st, ppm = self.terrain, self.stage, cam.ppm
        floor = self._span_points(cam, a, b, t.h)
        roof = self._span_points(cam, a, b, t.c)
        cave = st["cave"]
        pygame.draw.polygon(surf, cave, floor + roof[::-1])
        band = self._span_points(cam, a, b, t.c, -0.6)
        pygame.draw.polygon(surf, gfx.shade(cave, 0.72), roof + band[::-1])
        i0, i1 = int((a - START) / RES), int((b - START) / RES)
        beam, beam_dk = (120, 84, 50), (78, 52, 28)
        step = int(3.0 / RES)
        for n, i in enumerate(range(i0 + step // 2, i1, step)):
            x = START + i * RES
            fl, rf = cam.to_screen(x, t.h[i]), cam.to_screen(x, t.c[i])
            pygame.draw.line(surf, beam_dk, fl, rf, max(3, int(0.22 * ppm)))
            pygame.draw.line(surf, beam, fl, rf, max(2, int(0.14 * ppm)))
            pygame.draw.line(surf, beam_dk, (rf[0] - 0.5 * ppm, rf[1] + 0.1 * ppm), (rf[0] + 0.5 * ppm, rf[1] + 0.1 * ppm),
                             max(3, int(0.2 * ppm)))
            if n % 2 == 0:
                lamp = cam.to_screen(x + 1.5, t.c[min(i1, i + step // 2)] - 0.55)
                anchor = (lamp[0], lamp[1] - 0.45 * ppm)
                pygame.draw.line(surf, (30, 30, 30), anchor, lamp, max(1, int(0.03 * ppm)))
                self._lamps.append(lamp)
                scale = round(cam.ppm / (BASE_PPM * gfx.U) * (0.92 + 0.08 * math.sin(now * 13 + x)), 2)
                gs = self.art.cached(("glow", scale), lambda: pygame.transform.smoothscale_by(self.glow, scale))
                surf.blit(gs, gs.get_rect(center=lamp))
                pygame.draw.circle(surf, (255, 236, 160), lamp, 0.09 * ppm)
        road_hi = [(x, y + gfx.s(1)) for x, y in floor]
        pygame.draw.lines(surf, st["top_lo"], False, floor, max(3, int(0.16 * ppm)))
        pygame.draw.lines(surf, gfx.shade(st["top_lo"], 1.2), False, road_hi, max(1, int(0.05 * ppm)))
        stone, mortar = (138, 134, 128), (96, 92, 88)
        for x, i in ((a, i0), (b, i1)):
            bottom = cam.to_screen(x, t.h[i] - 0.1)
            top = cam.to_screen(x, t.c[i] + 0.75)
            w = 0.55 * ppm
            r = pygame.Rect(bottom[0] - w / 2, top[1], w, bottom[1] - top[1])
            pygame.draw.rect(surf, mortar, r, border_radius=int(0.08 * ppm))
            rows = 6
            for j in range(rows):
                y0 = r.y + r.h * j / rows
                off = (w * 0.25) if j % 2 else 0
                pygame.draw.rect(surf, stone, (r.x + 2 + off * 0.2, y0 + 2, r.w - 4, r.h / rows - 3),
                                 border_radius=int(0.04 * ppm))
            key_r = pygame.Rect(0, 0, 0.9 * ppm, 0.4 * ppm)
            key_r.midbottom = (bottom[0], top[1] + 0.12 * ppm)
            pygame.draw.rect(surf, mortar, key_r, border_radius=int(0.06 * ppm))
            pygame.draw.rect(surf, gfx.shade(stone, 1.1), key_r.inflate(-4, -4), border_radius=int(0.05 * ppm))

    def _draw_steps(self, surf, cam, risers):
        """Bare rock on the face of every ledge."""
        t, ppm = self.terrain, cam.ppm
        stone = gfx.mix(self.stage["ground"], (128, 124, 120), 0.6)
        for p0, p1 in risers:
            top = self._span_points(cam, p0 - 0.15, p1 + 0.2, t.v, 0.02)
            low = self._span_points(cam, p0 - 0.15, p1 + 0.2, t.v, -0.55)
            pygame.draw.polygon(surf, gfx.shade(stone, 0.75), top + low[::-1])
            pygame.draw.lines(surf, gfx.shade(stone, 1.25), False, top, max(2, int(0.06 * ppm)))
            mid = top[len(top) // 2]
            pygame.draw.line(surf, gfx.shade(stone, 0.55), (mid[0] - 0.1 * ppm, mid[1] + 0.12 * ppm),
                             (mid[0] + 0.05 * ppm, mid[1] + 0.4 * ppm), max(1, int(0.04 * ppm)))

    def _draw_gap(self, surf, cam, a, b):
        """A bottomless gap: dark rock walls falling away into black."""
        t, ppm = self.terrain, cam.ppm
        ia, ib = int((a - START) / RES), int((b - START) / RES)
        lip_a, lip_b = t.h[ia], t.h[ib]
        floor = t.h[ia + 1]
        wall = gfx.shade(self.stage["ground"], 0.55)
        # the far wall of the gap, seen through it, topping out a bit below the lower lip
        top = min(lip_a, lip_b) - 0.5
        n = max(4, int((b - a) / 0.6))
        edge = [cam.to_screen(a + (b - a) * j / n, top - 0.35 * _hash(j, int(a))) for j in range(n + 1)]
        for k, col in ((0.0, wall), (0.3, gfx.shade(wall, 0.6)), (0.6, gfx.shade(wall, 0.3))):
            y = top + (floor - top) * k
            pts = edge if k == 0 else [cam.to_screen(a, y), cam.to_screen(b, y)]
            pygame.draw.polygon(surf, col, pts + [cam.to_screen(b, floor - 2), cam.to_screen(a, floor - 2)])
        pygame.draw.lines(surf, gfx.shade(wall, 1.3), False, edge, max(1, int(0.04 * ppm)))
        lw = max(2, int(0.07 * ppm))
        for x, y, side in ((a, lip_a, 1), (b, lip_b, -1)):       # jagged rock edges
            pts = [cam.to_screen(x + side * 0.12 * ((j % 2) + 0.3), y - j * 0.8) for j in range(10)]
            pygame.draw.lines(surf, gfx.shade(wall, 1.5), False, pts, lw)

    def _draw_cave(self, surf, cam, a, b, now):
        """A long dark cave: rough walls, stalactites, stalagmites and glowing crystals."""
        t, st, ppm = self.terrain, self.stage, cam.ppm
        x0, x1 = cam.view(1.5)
        a_, b_ = max(a, x0), min(b, x1)
        if b_ <= a_:
            return
        cave = gfx.shade(st["cave"], 0.8)
        rock = gfx.mix(st["cave"], (150, 140, 130), 0.35)
        floor = self._span_points(cam, a_, b_, t.h)
        roof = self._span_points(cam, a_, b_, t.c)
        if len(floor) < 2:
            return
        pygame.draw.polygon(surf, cave, floor + roof[::-1])
        i0, i1 = int((a_ - START) / RES), int((b_ - START) / RES)
        for i in range(i0 - i0 % 6, i1, 6):                      # blotchy back wall
            if _hash(i, 31) < 0.45:
                continue
            x = START + i * RES
            fl, rf = t.h[i], t.c[i]
            y = fl + (rf - fl) * (0.25 + 0.55 * _hash(i, 32))
            r = (0.35 + 0.7 * _hash(i, 33)) * ppm
            pygame.draw.ellipse(surf, gfx.shade(cave, 0.82), (*cam.to_screen(x, y), r * 1.8, r))
        tint = (255, 140, 40) if st.get("lava") else (120, 220, 255) if st["key"] in ("arctic", "ocean") else \
            (90, 255, 160) if st["key"] == "jungle" else (200, 120, 255)
        for i in range(i0 - i0 % 10, i1, 10):
            x = START + i * RES
            roll = _hash(i, 34)
            if roll < 0.4:                                       # stalagmite at the back
                hgt = (0.4 + 0.8 * _hash(i, 35)) * ppm
                base = cam.to_screen(x, t.h[i] + 0.05)
                w = hgt * 0.35
                pygame.draw.polygon(surf, gfx.shade(rock, 0.7), [(base[0] - w, base[1]), (base[0] + w, base[1]),
                                                                 (base[0] + w * 0.1, base[1] - hgt)])
            elif roll > 0.86:                                    # a glowing crystal cluster
                up = _hash(i, 36) < 0.5
                y = t.c[i] - 0.35 if up else t.h[i] + 0.25
                cx, cy = cam.to_screen(x, y)
                k = (0.8 + 0.2 * math.sin(now * 2.5 + i)) * ppm
                for dx, size in ((-0.3, 0.38), (0.0, 0.6), (0.26, 0.32)):
                    tip = -1 if not up else 1
                    pygame.draw.polygon(surf, tint, [(cx + (dx - 0.11) * k, cy), (cx + (dx + 0.11) * k, cy),
                                                     (cx + dx * k, cy + tip * size * k)])
                pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(1, 0.05 * ppm))
                self._lamps.append((cx, cy))
        spikes = t.spikes
        lw = max(1, int(0.04 * ppm))
        for k in range(bisect.bisect_left(t.spike_x, a_ - 2), bisect.bisect_right(t.spike_x, b_ + 2)):
            x, base, tip, half = spikes[k]
            pts = [cam.to_screen(x - half, base + 0.1), cam.to_screen(x + half, base + 0.1), cam.to_screen(x, tip)]
            pygame.draw.polygon(surf, rock, pts)
            pygame.draw.line(surf, gfx.shade(rock, 1.3), pts[0], pts[2], lw)
            pygame.draw.line(surf, gfx.shade(rock, 0.7), pts[1], pts[2], lw)
        pygame.draw.lines(surf, gfx.shade(cave, 0.6), False, roof, max(2, int(0.12 * ppm)))
        pygame.draw.lines(surf, gfx.shade(rock, 0.9), False, floor, max(3, int(0.16 * ppm)))
        pygame.draw.lines(surf, gfx.shade(rock, 1.25), False, [(x, y + gfx.s(1)) for x, y in floor],
                          max(1, int(0.05 * ppm)))
        for x, side in ((a, 1), (b, -1)):                        # a frame of rocks around each mouth
            if not x0 - 3 < x < x1 + 3:
                continue
            i = int((x - START) / RES)
            fl, rf = t.h[i], t.c[i]
            n = max(3, int((rf - fl + 0.9) / 0.75))
            stone = gfx.mix(st["ground"], (140, 136, 130), 0.55)
            for j in range(n + 1):
                y = fl + (rf + 0.9 - fl) * j / n
                r = (0.26 + 0.24 * _hash(i, j, 7)) * ppm
                c = cam.to_screen(x + side * (0.05 + 0.25 * _hash(i, j, 8)), y)
                pygame.draw.circle(surf, gfx.shade(stone, 0.55), (c[0], c[1] + r * 0.12), r)
                pygame.draw.circle(surf, gfx.shade(stone, 0.8 + 0.2 * _hash(i, j, 9)), c, r * 0.9)
                pygame.draw.circle(surf, gfx.shade(stone, 1.15), (c[0] - r * 0.3, c[1] - r * 0.3), r * 0.3)

    # ------------------------------------------------------------ obstacles
    MATERIAL = {"city": ((168, 72, 52), (210, 200, 186), "brick"), "arctic": ((176, 222, 246), (236, 248, 255), "ice"),
                "seasons": ((176, 120, 64), (110, 72, 38), "crate"), "moon": ((150, 146, 160), (96, 94, 108), "stone"),
                "mars": ((176, 100, 70), (110, 60, 40), "stone"), "volcano": ((96, 84, 84), (50, 42, 44), "stone")}

    def draw_things(self, surf, cam, t):
        terr, ppm = self.terrain, cam.ppm
        x0, x1 = cam.view(2.0)
        bucket = int(ppm / 2) * 2
        for i in terr.thing_range(x0, x1):
            th = terr.things[i]
            kind = th["kind"]
            if kind == "car":
                img = self._sprite("car", th["variant"], bucket, th["flip"])
                surf.blit(img, img.get_rect(midbottom=cam.to_screen(th["x"], th["y"] - 0.04)))
            elif kind == "traffic":
                x, right = traffic_pos(th, t)
                img = self._sprite("car", th["variant"], bucket, not right)
                bounce = 0.03 * math.sin(t * 17 + i)
                surf.blit(img, img.get_rect(midbottom=cam.to_screen(x, terr.height(x) - 0.04 + bounce)))
                hx = x + (1.8 if right else -1.8)
                self._lamps.append(cam.to_screen(hx, terr.height(x) + 0.6))
                if int(t * 3) % 2:                               # hazard flashers
                    pygame.draw.circle(surf, (255, 170, 30), cam.to_screen(x + (-1.8 if right else 1.8),
                                                                           terr.height(x) + 0.62), 0.09 * ppm)
            elif kind == "crates" and i not in self.broken:
                self._draw_crates(surf, cam, th)
            elif kind == "crusher":
                self._draw_crusher(surf, cam, th, t)
            elif kind == "wrecker":
                self._draw_wrecker(surf, cam, th, t)
            elif kind == "boulder":
                self._draw_boulder(surf, cam, th, t)
            elif kind == "flames":
                self._draw_flames(surf, cam, th, t, i)
            elif kind == "spinner":
                self._draw_spinner(surf, cam, th, t)
            elif kind == "spikes":
                self._draw_spikes(surf, cam, th)

    def _draw_crates(self, surf, cam, th):
        ppm = cam.ppm
        col, line, style = self.MATERIAL.get(self.stage["key"], ((176, 120, 64), (110, 72, 38), "crate"))
        cols = max(1, round(th["w"] / 0.9))
        rows = 3
        cw, rh = th["w"] / cols, th["hgt"] / rows
        lw = max(1, int(0.05 * ppm))
        for r in range(rows):
            for c in range(cols):
                x0 = th["x"] - th["w"] / 2 + c * cw
                y0 = th["y"] + r * rh
                tl = cam.to_screen(x0, y0 + rh)
                rect = pygame.Rect(tl[0], tl[1], cw * ppm + 1, rh * ppm + 1)
                shade = 0.9 + 0.2 * _hash(r, c, int(th["x"]))
                pygame.draw.rect(surf, gfx.shade(col, shade), rect)
                if style == "crate":
                    pygame.draw.rect(surf, line, rect, lw * 2)
                    pygame.draw.line(surf, line, rect.topleft, rect.bottomright, lw * 2)
                    pygame.draw.line(surf, gfx.shade(col, 1.2), (rect.x + lw * 2, rect.y + lw * 2),
                                     (rect.right - lw * 2, rect.y + lw * 2), lw)
                elif style == "brick":
                    for k in range(4):
                        y = rect.y + rect.h * k / 4
                        pygame.draw.line(surf, line, (rect.x, y), (rect.right, y), lw)
                        off = rect.w / 2 if k % 2 else 0
                        for bx in (rect.x + off, rect.x + off + rect.w / 2):
                            if rect.x < bx < rect.right:
                                pygame.draw.line(surf, line, (bx, y), (bx, y + rect.h / 4), lw)
                    pygame.draw.rect(surf, line, rect, lw)
                elif style == "ice":
                    pygame.draw.rect(surf, line, rect, lw)
                    pygame.draw.line(surf, (255, 255, 255), (rect.x + rect.w * 0.2, rect.y + rect.h * 0.2),
                                     (rect.x + rect.w * 0.45, rect.y + rect.h * 0.15), lw * 2)
                else:
                    pygame.draw.rect(surf, line, rect, lw * 2, border_radius=int(0.12 * ppm))
        # a warning sign in front: smash it
        sx, sy = cam.to_screen(th["x"] - th["w"] / 2 - 5.0, th["y"])
        pygame.draw.line(surf, (90, 90, 96), (sx, sy), (sx, sy - 1.3 * ppm), max(2, int(0.08 * ppm)))
        pts = [(sx, sy - 1.95 * ppm), (sx + 0.42 * ppm, sy - 1.3 * ppm), (sx - 0.42 * ppm, sy - 1.3 * ppm)]
        pygame.draw.polygon(surf, (250, 200, 30), pts)
        pygame.draw.polygon(surf, (30, 30, 34), pts, lw)
        gfx.blit_text(surf, "cond", max(8, int(0.34 * ppm / gfx.U)), "!", (30, 30, 34), (sx, sy - 1.5 * ppm), "center")

    def _draw_crusher(self, surf, cam, th, t):
        ppm = cam.ppm
        bottom = crusher_bottom(th, t)
        top_y = bottom + 1.4
        x, w = th["x"], th["w"]
        # the piston from the roof
        a, b = cam.to_screen(x, th["top"] + 0.4), cam.to_screen(x, top_y)
        pygame.draw.line(surf, (60, 62, 68), a, b, max(3, int(0.36 * ppm)))
        pygame.draw.line(surf, (150, 154, 162), (a[0] - 0.06 * ppm, a[1]), (b[0] - 0.06 * ppm, b[1]), max(1, int(0.08 * ppm)))
        tl = cam.to_screen(x - w / 2, top_y)
        rect = pygame.Rect(tl[0], tl[1], w * ppm, 1.4 * ppm)
        pygame.draw.rect(surf, (82, 86, 96), rect, border_radius=int(0.08 * ppm))
        pygame.draw.rect(surf, (120, 126, 138), rect.inflate(-0.16 * ppm, -0.16 * ppm), border_radius=int(0.06 * ppm))
        band = pygame.Rect(rect.x, rect.bottom - 0.32 * ppm, rect.w, 0.32 * ppm)
        pygame.draw.rect(surf, (250, 200, 30), band)
        k = 0
        while k * 0.3 * ppm < rect.w + band.h:                     # hazard stripes
            x0 = band.x + k * 0.3 * ppm
            pts = [(x0, band.bottom), (x0 + 0.15 * ppm, band.bottom), (x0 + 0.15 * ppm + band.h, band.y),
                   (x0 + band.h, band.y)]
            pts = [(min(max(px, band.x), band.right), py) for px, py in pts]
            pygame.draw.polygon(surf, (30, 30, 34), pts)
            k += 1
        for bx in (rect.x + 0.2 * ppm, rect.right - 0.2 * ppm):
            pygame.draw.circle(surf, (60, 62, 70), (bx, rect.y + 0.25 * ppm), 0.07 * ppm)
        self._lamps.append((rect.centerx, rect.bottom))

    def _draw_boulder(self, surf, cam, th, t):
        terr, ppm = self.terrain, cam.ppm
        # the rock pile they come out of
        pile = terr.height(th["a"] + 1.5)
        for dx, dy, r in ((0.6, 0.5, 1.1), (2.0, 0.6, 1.3), (1.3, 1.6, 0.9), (3.0, 0.4, 0.8)):
            c = cam.to_screen(th["a"] + dx, pile + dy)
            pygame.draw.circle(surf, (96, 90, 86), c, r * ppm)
            pygame.draw.circle(surf, (128, 122, 116), (c[0] - r * 0.3 * ppm, c[1] - r * 0.3 * ppm), r * 0.45 * ppm)
        x, rolled = boulder_pos(th, t)
        if x is None:
            return
        r = th["r"]
        y = terr.height(x) + r - boulder_sink(th, t)
        c = cam.to_screen(x, y)
        R = r * ppm
        pygame.draw.circle(surf, (84, 76, 70), c, R)
        pygame.draw.circle(surf, (120, 110, 100), (c[0] - R * 0.15, c[1] - R * 0.15), R * 0.8)
        ang = rolled / r                                         # rolls towards -x: counter-clockwise on screen
        for k in range(3):                                       # cracks that turn with it
            a = ang + k * 2.1
            p0 = (c[0] + math.cos(a) * R * 0.2, c[1] - math.sin(a) * R * 0.2)
            p1 = (c[0] + math.cos(a + 0.3) * R * 0.75, c[1] - math.sin(a + 0.3) * R * 0.75)
            pygame.draw.line(surf, (60, 54, 50), p0, p1, max(1, int(0.06 * ppm)))
        pygame.draw.circle(surf, (150, 140, 130), (c[0] - R * 0.4, c[1] - R * 0.42), R * 0.18)

    def _draw_flames(self, surf, cam, th, t, i):
        ppm = cam.ppm
        base = cam.to_screen(th["x"], th["y"])
        pygame.draw.rect(surf, (60, 62, 68), (base[0] - 0.4 * ppm, base[1] - 0.3 * ppm, 0.8 * ppm, 0.34 * ppm),
                         border_radius=int(0.06 * ppm))
        pygame.draw.rect(surf, (250, 200, 30), (base[0] - 0.4 * ppm, base[1] - 0.3 * ppm, 0.8 * ppm, 0.08 * ppm))
        f = flame_height(th, t)
        u = ((t + th["phase"]) / th["period"]) % 1.0
        if f <= 0:
            if u > 0.8:                                          # about to fire: it hisses and glows
                pygame.draw.circle(surf, (255, 150, 40), (base[0], base[1] - 0.32 * ppm), 0.14 * ppm)
            return
        for col, w, k in (((255, 90, 20), 0.55, 1.0), ((255, 170, 40), 0.38, 0.8), ((255, 240, 160), 0.2, 0.55)):
            hgt = f * k * (0.92 + 0.08 * math.sin(t * 30 + i))
            pts = [(base[0] - w * ppm, base[1] - 0.3 * ppm), (base[0] + w * ppm, base[1] - 0.3 * ppm)]
            for j in range(1, 6):
                fy = j / 6
                wob = math.sin(t * 25 + j * 1.7 + i) * 0.08
                pts.append((base[0] + (w * (1 - fy) + wob) * ppm, base[1] - (0.3 + hgt * fy) * ppm))
            pts.append((base[0], base[1] - (0.3 + hgt) * ppm))
            for j in range(5, 0, -1):
                fy = j / 6
                wob = math.sin(t * 23 + j * 1.3 + i) * 0.08
                pts.append((base[0] - (w * (1 - fy) - wob) * ppm, base[1] - (0.3 + hgt * fy) * ppm))
            pygame.draw.polygon(surf, col, pts)
        self._lamps.append((base[0], base[1] - (0.3 + f * 0.5) * ppm))

    def _draw_spinner(self, surf, cam, th, t):
        ppm = cam.ppm
        foot = cam.to_screen(th["x"], th["y"] - 0.1)
        hub = cam.to_screen(th["x"], th["py"])
        pygame.draw.polygon(surf, (70, 74, 82), [(foot[0] - 0.6 * ppm, foot[1]), (foot[0] + 0.6 * ppm, foot[1]),
                                                 (hub[0] + 0.15 * ppm, hub[1]), (hub[0] - 0.15 * ppm, hub[1])])
        pts = spinner_points(th, t)
        a, b = cam.to_screen(*pts[0]), cam.to_screen(*pts[-1])
        pygame.draw.line(surf, (40, 40, 46), a, b, max(4, int(0.5 * ppm)))
        pygame.draw.line(surf, (220, 50, 40), a, b, max(3, int(0.36 * ppm)))
        for k in range(8):                                       # white warning bands
            f = (k + 0.5) / 8
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            q = (a[0] + (b[0] - a[0]) * (f + 0.04), a[1] + (b[1] - a[1]) * (f + 0.04))
            pygame.draw.line(surf, (250, 250, 250), p, q, max(3, int(0.36 * ppm)))
        pygame.draw.circle(surf, (40, 40, 46), hub, 0.32 * ppm)
        pygame.draw.circle(surf, (170, 174, 182), hub, 0.16 * ppm)

    def _draw_spikes(self, surf, cam, th):
        ppm = cam.ppm
        n = max(3, int((th["x1"] - th["x0"]) / 0.35))
        y = th["y"]
        base_l, base_r = cam.to_screen(th["x0"], y), cam.to_screen(th["x1"], y)
        pygame.draw.rect(surf, (54, 56, 62), (base_l[0], base_l[1] - 0.08 * ppm, base_r[0] - base_l[0], 0.2 * ppm))
        for k in range(n):
            x = th["x0"] + (th["x1"] - th["x0"]) * (k + 0.5) / n
            p = cam.to_screen(x, y)
            w = 0.15 * ppm
            tip = (p[0], p[1] - 0.5 * ppm)
            pygame.draw.polygon(surf, (150, 156, 166), [(p[0] - w, p[1]), (p[0] + w, p[1]), tip])
            pygame.draw.line(surf, (226, 230, 236), (p[0] - w * 0.4, p[1] - 0.05 * ppm), tip, max(1, int(0.03 * ppm)))

    def _draw_wrecker(self, surf, cam, th, t):
        ppm = cam.ppm
        steel, dark = (230, 170, 40), (150, 104, 20)
        base = cam.to_screen(th["x"] - 3.0, th["y"] - 0.1)
        mast = cam.to_screen(th["x"] - 3.0, th["py"] + 0.7)
        tip = cam.to_screen(th["x"] + 0.6, th["py"] + 0.7)
        pygame.draw.line(surf, dark, base, mast, max(3, int(0.4 * ppm)))
        pygame.draw.line(surf, steel, base, mast, max(2, int(0.26 * ppm)))
        pygame.draw.line(surf, dark, mast, tip, max(3, int(0.34 * ppm)))
        pygame.draw.line(surf, steel, mast, tip, max(2, int(0.2 * ppm)))
        for k in range(1, 8):                                   # lattice
            p = (base[0], base[1] + (mast[1] - base[1]) * k / 8)
            q = (base[0] + 0.0, base[1] + (mast[1] - base[1]) * (k + 0.5) / 8)
            pygame.draw.line(surf, dark, (p[0] - 0.13 * ppm, p[1]), (q[0] + 0.13 * ppm, q[1]), max(1, int(0.05 * ppm)))
        pivot = cam.to_screen(th["x"], th["py"])
        pygame.draw.line(surf, dark, (pivot[0], tip[1]), pivot, max(2, int(0.1 * ppm)))
        bx, by = wrecker_ball(th, t)
        ball = cam.to_screen(bx, by)
        pygame.draw.line(surf, (60, 60, 66), pivot, ball, max(2, int(0.1 * ppm)))
        n = 12
        for k in range(n):                                       # chain links
            p = (pivot[0] + (ball[0] - pivot[0]) * k / n, pivot[1] + (ball[1] - pivot[1]) * k / n)
            pygame.draw.circle(surf, (110, 110, 118), p, max(2, 0.1 * ppm), max(1, int(0.04 * ppm)))
        r = th["r"] * ppm
        pygame.draw.circle(surf, (40, 40, 46), ball, r)
        pygame.draw.circle(surf, (70, 70, 78), (ball[0] - r * 0.12, ball[1] - r * 0.12), r * 0.82)
        pygame.draw.circle(surf, (120, 120, 130), (ball[0] - r * 0.35, ball[1] - r * 0.38), r * 0.22)

    def _draw_pebbles(self, surf, cam, x0, x1):
        if QUALITY == "low":
            return
        st, t = self.stage, self.terrain
        ppm = cam.ppm
        cw, ch = 1.3, 1.05
        y_bottom = cam.y - gfx.H / 2 / ppm - 0.5
        top_cut = st["top_depth"] * 2.2
        for ix in range(int(math.floor(x0 / cw)), int(math.floor(x1 / cw)) + 1):
            col_top = t.visual_height(ix * cw + cw / 2) + 0.4
            for iy in range(int(math.floor(y_bottom / ch)), int(math.floor(col_top / ch)) + 1):
                if _hash(ix, iy) > 0.58:
                    continue
                px = (ix + _hash(ix, iy, 1)) * cw
                py = (iy + _hash(ix, iy, 2)) * ch
                rad = 0.09 + 0.22 * _hash(ix, iy, 3) ** 1.5
                if py + rad > t.visual_height(px) - top_cut:
                    continue
                ceil = t.ceiling(px)
                if ceil is not None and t.height(px) - rad - 0.1 < py < ceil + rad + 0.8:
                    continue
                pr = max(2, int(rad * ppm))
                img = self.art.cached(("pebble", st["pebble"], pr),
                                      lambda: sprites.pebble(pr, st["pebble"], st["pebble_hi"]))
                sx, sy = cam.to_screen(px, py)
                surf.blit(img, (sx - pr, sy - pr))

    # ---------------------------------------------------------------- props
    def draw_props(self, surf, cam):
        if QUALITY == "low":
            return
        x0, x1 = cam.view(3.5)
        t = self.terrain
        bucket = int(cam.ppm / 2) * 2
        for i in range(bisect.bisect_left(self.prop_x, x0), bisect.bisect_right(self.prop_x, x1)):
            x, kind, scale, flip = t.props[i]
            variant = i % 3
            img = self._sprite(kind, variant, bucket * scale, flip)
            sx, sy = cam.to_screen(x, t.visual_height(x) - 0.06)
            surf.blit(img, img.get_rect(midbottom=(sx, sy)))
            light = prop_art.LIGHTS.get(kind)
            if light:
                lx = -light[0] if flip else light[0]
                self._lamps.append((sx + lx * cam.ppm * scale, sy - light[1] * cam.ppm * scale))

    def draw_landmarks(self, surf, cam, now, darkness):
        """Big set pieces behind the road, with their moving parts drawn live."""
        x0, x1 = cam.view(14.0)
        t = self.terrain
        bucket = int(cam.ppm / 2) * 2
        for i in range(bisect.bisect_left(self.mark_x, x0), bisect.bisect_right(self.mark_x, x1)):
            x, kind, flip = t.landmarks[i]
            flip = flip and kind not in prop_art.NO_FLIP
            img = self._sprite(kind, 0, bucket, flip)
            sx, sy = cam.to_screen(x, t.visual_height(x) - 0.12)
            surf.blit(img, img.get_rect(midbottom=(sx, sy)))
            self._animate(surf, kind, sx, sy, cam.ppm, -1 if flip else 1, now, darkness)
            light = prop_art.LIGHTS.get(kind)
            if light:
                self._lamps.append((sx + light[0] * cam.ppm, sy - light[1] * cam.ppm))

    @staticmethod
    def _animate(surf, kind, sx, sy, ppm, side, now, darkness):
        def P(x, y):
            return (sx + x * side * ppm, sy - y * ppm)
        if kind == "windmill":                                   # four sails turning slowly
            hub = P(0.0, 7.0)
            for n in range(4):
                a = now * 1.1 * side + n * math.pi / 2
                ca, sa = math.cos(a), math.sin(a)
                ux, uy = -sa, ca

                def Q(r, w):
                    return (hub[0] + (ca * r + ux * w) * ppm, hub[1] - (sa * r + uy * w) * ppm)
                pygame.draw.line(surf, (96, 70, 50), hub, Q(3.4, 0.0), max(2, int(0.12 * ppm)))
                pygame.draw.polygon(surf, (236, 230, 214), [Q(0.9, 0.06), Q(3.4, 0.06), Q(3.3, 0.62), Q(0.9, 0.5)])
                pygame.draw.polygon(surf, (120, 90, 64), [Q(0.9, 0.06), Q(3.4, 0.06), Q(3.3, 0.62), Q(0.9, 0.5)],
                                    max(1, int(0.04 * ppm)))
            pygame.draw.circle(surf, (70, 50, 40), hub, 0.3 * ppm)
        elif kind == "pumpjack":                                 # the nodding beam and horse head
            a = math.sin(now * 1.6) * 0.32 * side
            ca, sa = math.cos(a), math.sin(a)
            pivot = P(0.0, 3.2)

            def B(r, h):
                return (pivot[0] + (r * ca - h * sa) * side * ppm, pivot[1] - (r * sa + h * ca) * ppm)
            pygame.draw.polygon(surf, (60, 62, 70), [B(-2.2, -0.15), B(2.0, -0.15), B(2.0, 0.2), B(-2.2, 0.2)])
            pygame.draw.polygon(surf, (230, 180, 40), [B(1.9, -0.6), B(2.5, -0.4), B(2.5, 0.5), B(1.9, 0.3)])
            pygame.draw.line(surf, (40, 40, 46), B(2.4, -0.5), P(2.0, 1.4), max(1, int(0.05 * ppm)))
            pygame.draw.line(surf, (60, 62, 70), B(-2.0, 0.0), P(-1.55, 1.7), max(2, int(0.12 * ppm)))
            pygame.draw.circle(surf, (40, 40, 46), pivot, 0.18 * ppm)
        elif kind in ("dome", "lander", "launchpad"):            # blinking warning light
            tip = {"dome": (2.6, 4.25), "lander": (1.0, 3.8), "launchpad": (-1.1, 7.05)}[kind]
            if int(now * 1.6) % 2 == 0:
                p = P(*tip)
                pygame.draw.circle(surf, (255, 60, 50), p, 0.14 * ppm)
                glow = sprites.soft_puff(max(2, int(0.9 * ppm)), (255, 80, 60))
                surf.blit(glow, glow.get_rect(center=p))

    def _master(self, kind, variant):
        """Each prop is drawn once, in full quality, at the closest zoom; every other zoom just shrinks it.
        (Redrawing props for every zoom level caused the stutters while driving.)"""
        masters = self.art.__dict__.setdefault("masters", {})          # never cleared, unlike the sprite cache
        key = (kind, variant)
        if key not in masters:
            masters[key] = prop_art.make(kind, self.art.ppm * 1.25, variant)
        return masters[key]

    def _sprite(self, kind, variant, ppm, flip):
        ppm = max(4, int(ppm / 4) * 4)                    # a few zoom steps are plenty
        key = ("prop", kind, variant, ppm, flip)

        def make():
            master = self._master(kind, variant)
            k = ppm / (self.art.ppm * 1.25)
            size = (max(1, round(master.get_width() * k)), max(1, round(master.get_height() * k)))
            img = pygame.transform.smoothscale(master, size)
            return pygame.transform.flip(img, True, False) if flip else img
        return self.art.cached(key, make)

    def warm_up(self):
        """Draw every prop and landmark of this map before the run starts, not in the middle of it."""
        seen = set()
        for i, (_, kind, _, _) in enumerate(self.terrain.props):
            seen.add((kind, i % 3))
        for _, kind, _ in self.terrain.landmarks:
            seen.add((kind, 0))
        for th in self.terrain.things:
            if th["kind"] in ("car", "traffic"):
                seen.add(("car", th["variant"]))
        for kind, variant in seen:
            self._master(kind, variant)

    # -------------------------------------------------------------- pickups
    def draw_pickups(self, surf, cam, now):
        x0, x1 = cam.view(1.0)
        coins = self.terrain.coins
        for i in range(bisect.bisect_left(self.coin_x, x0), bisect.bisect_right(self.coin_x, x1)):
            x, y, value, taken = coins[i]
            if taken:
                continue
            pr = max(3, int(sprites.COIN_STYLE[value][3] * cam.ppm))
            img = self.art.cached(("coin", value, pr), lambda: sprites.coin(value, pr))
            sx, sy = cam.to_screen(x, y)
            surf.blit(img, (sx - img.get_width() / 2, sy - img.get_height() / 2))
        for tx, ty, ti, taken in self.terrain.trophies:
            if taken or not x0 - 1 < tx < x1 + 1:
                continue
            size = int(0.9 * cam.ppm)
            img = self.art.cached(("trophy", size), lambda: sprites.trophy(size))
            sx, sy = cam.to_screen(tx, ty + math.sin(now * 2.5 + ti) * 0.12)
            glow = self.art.cached(("tglow", size), lambda: sprites.soft_puff(size, (255, 230, 120)))
            surf.blit(glow, glow.get_rect(center=(sx, sy)))
            surf.blit(img, img.get_rect(center=(sx, sy)))
        nitro = self.terrain.nitro
        for i in range(bisect.bisect_left(self.nitro_x, x0), bisect.bisect_right(self.nitro_x, x1)):
            x, y, taken = nitro[i]
            if taken:
                continue
            sc = round(cam.ppm / self.art.ppm, 2)
            img = self.art.cached(("nitro", sc), lambda: pygame.transform.smoothscale_by(self.art.nitro, sc))
            glow = self.art.cached(("nglow", sc), lambda: sprites.soft_puff(int(1.6 * cam.ppm), (90, 190, 255)))
            surf.blit(glow, glow.get_rect(center=cam.to_screen(x, y)))
            bob = math.sin(now * 3.0 + x) * 0.06
            sx, sy = cam.to_screen(x, y + bob)
            surf.blit(img, img.get_rect(center=(sx, sy)))

    def draw_markers(self, surf, cam, best):
        x0, x1 = cam.view(3.0)
        start = int(max(0, x0) // 250 + 1) * 250
        for d in range(start, int(x1) + 1, 250):
            self._sign(surf, cam, d, f"{d}m")
        if best > 20 and x0 < best < x1:
            self._flag(surf, cam, best)

    def _sign(self, surf, cam, x, label):
        ppm = cam.ppm
        g = self.terrain.height(x)
        base = cam.to_screen(x, g)
        post_h, board_w, board_h = 1.25 * ppm, 1.15 * ppm, 0.5 * ppm
        pygame.draw.rect(surf, (96, 66, 40), (base[0] - 0.05 * ppm, base[1] - post_h, 0.1 * ppm, post_h + 4))

        def make():
            def draw(s, k):
                r = pygame.Rect(0, 0, s.get_width(), s.get_height())
                pygame.draw.rect(s, (110, 74, 42), r, border_radius=int(6 * k))
                pygame.draw.rect(s, (238, 214, 160), r.inflate(-5 * k, -5 * k), border_radius=int(5 * k))
                tx = gfx.font_px("cond", r.h * 0.62).render(label, True, (70, 46, 24))
                s.blit(tx, tx.get_rect(center=r.center))
            return gfx.supersample(board_w, board_h, draw)
        img = self.art.cached(("sign", label, int(ppm)), make)
        surf.blit(img, img.get_rect(midbottom=(base[0], base[1] - post_h + board_h * 0.5)))

    def _flag(self, surf, cam, x):
        ppm = cam.ppm
        g = self.terrain.height(x)
        bx, by = cam.to_screen(x, g)
        pole = 2.6 * ppm
        pygame.draw.line(surf, (60, 60, 66), (bx, by), (bx, by - pole), max(2, int(0.07 * ppm)))
        fw, fh = 1.0 * ppm, 0.6 * ppm

        def make():
            def draw(s, k):
                W, H = s.get_size()
                cw_, ch_ = W / 5, H / 3
                for i in range(5):
                    for j in range(3):
                        col = (30, 30, 34) if (i + j) % 2 else (250, 250, 250)
                        pygame.draw.rect(s, col, (i * cw_, j * ch_, cw_ + 1, ch_ + 1))
            return gfx.supersample(fw, fh, draw)
        surf.blit(self.art.cached(("flag", int(ppm)), make), (bx, by - pole))
        gfx.blit_text(surf, "cond", 15, "BEST", (255, 255, 255), (bx + fw / 2, by - pole - gfx.s(2)),
                      "midbottom", outline=(30, 30, 30))

    # -------------------------------------------------------------- vehicle
    def draw_vehicle(self, surf, cam, car, wobble, now, driver="default"):
        va = self.art.vehicle(car.spec, driver)
        sc = cam.ppm / self.art.ppm
        c, s = math.cos(car.angle), math.sin(car.angle)

        def P(lx, ly):
            return cam.to_screen(car.x + lx * c - ly * s, car.y + lx * s + ly * c)
        wheels = [(0, 0, w.r, w.angle, cam.to_screen(w.x, w.y)) for w in car.wheels]
        flame = None
        if car.thrusting or car.boosting:
            img = va.flames[int(now * 24) % len(va.flames)]
            big = 1.0 if car.thrusting else 0.75
            if car.thrusting and car.boosting:
                big = 1.35
            img = pygame.transform.rotozoom(img, math.degrees(car.angle), sc * big)
            flame = (img, P(*car.NOZZLE))
        levels = getattr(car, "stats", {}).get("levels")
        _draw_vehicle_parts(surf, P, cam.ppm, car.spec, va, sc, car.angle, wheels, wobble, False, flame, levels,
                            getattr(car, "rpm", 0.5))

    def draw(self, surf, cam, views, particles, now, dt, best, darkness=0.0, sunset=0.0, race_m=0):
        """views: list of CarView, the player's own car last (drawn on top)."""
        self._lamps = []
        self.stage = season_stage(self.base_stage, cam.x)
        self.backdrop.draw(surf, cam, dt, darkness, sunset, self.stage)
        self.draw_landmarks(surf, cam, now, darkness)
        self.draw_props(surf, cam)
        self.draw_terrain(surf, cam, now)
        self.draw_things(surf, cam, now if self.clock is None else self.clock)
        self.draw_markers(surf, cam, best)
        if race_m:
            self.draw_finish(surf, cam, race_m)
        self.draw_pickups(surf, cam, now)
        particles.draw(surf, cam, back=True)
        for v in views:
            if v.ghost:
                if not hasattr(self, "_ghost_layer"):
                    self._ghost_layer = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
                layer = self._ghost_layer
                layer.fill((0, 0, 0, 0))
                self.draw_vehicle(layer, cam, v.car, v.wobble, now, v.driver)
                layer.set_alpha(110)
                surf.blit(layer, (0, 0))
            else:
                self.draw_vehicle(surf, cam, v.car, v.wobble, now, v.driver)
        particles.draw(surf, cam, back=False)
        cave = self.terrain.cave_at(cam.x, 2.0)
        if cave:                                                  # caves are dark, day or night
            darkness = max(darkness, 0.8 * min(1.0, (cam.x - cave[0] + 2) / 12, (cave[1] + 2 - cam.x) / 12))
        if darkness > 0.01:
            cones, glows, tails = [], [], []
            for v in views:
                self._lights(cam, v, cones, glows, tails)
            for x, y in self._lamps:
                glows.append((x, y, 3.2 * cam.ppm, 0.9))
            self.lighting.apply(surf, darkness, cones, glows)
            self.lighting.lamp_dots(surf, cones, tails)
        for v in views:
            if v.label:
                self._name_tag(surf, cam, v)
            if v.bubble:
                self._bubble(surf, cam, v)

    def _lights(self, cam, v, cones, glows, tails):
        car = v.car
        if v.car.boosting or v.car.thrusting:
            x, y = cam.to_screen(*car.to_world(*car.NOZZLE))
            glows.append((x, y, 2.6 * cam.ppm, 0.9))
        if not v.lights:
            return
        for lx, ly in car.spec["lights"]:
            x, y = cam.to_screen(*car.to_world(lx, ly))
            cones.append((x, y, car.angle, 12.0 * cam.ppm))
            glows.append((x, y, 1.6 * cam.ppm, 0.8))
        for lx, ly in car.spec["tail"]:
            x, y = cam.to_screen(*car.to_world(lx, ly))
            tails.append((x, y))
            glows.append((x, y, 0.9 * cam.ppm, 0.5))

    def _name_tag(self, surf, cam, v):
        x, y = cam.to_screen(*v.car.to_world(v.car.HEAD[0], v.car.HEAD[1] + 0.9))
        img = gfx.text("cond", 18, v.label, v.color, outline=(20, 20, 24), width=2)
        surf.blit(img, img.get_rect(midbottom=(x, y)))

    def _bubble(self, surf, cam, v):
        text, left = v.bubble
        x, y = cam.to_screen(*v.car.to_world(v.car.HEAD[0], v.car.HEAD[1] + 0.5))
        t = gfx.text("cond_i", 22, text, (30, 30, 34))
        box = t.get_rect().inflate(gfx.s(26), gfx.s(16))
        box.midbottom = (x + gfx.s(40), y - gfx.s(26))
        box.clamp_ip(pygame.Rect(gfx.s(10), gfx.s(70), gfx.W - gfx.s(20), gfx.H))
        alpha = 255 if left > 0.4 else int(255 * left / 0.4)
        bub = pygame.Surface((box.w + 4, box.h + gfx.s(22)), pygame.SRCALPHA)
        r = pygame.Rect(2, 2, box.w, box.h)
        tail = [(r.x + gfx.s(18), r.bottom - 2), (r.x + gfx.s(40), r.bottom - 2), (r.x + gfx.s(10), r.bottom + gfx.s(18))]
        pygame.draw.polygon(bub, (30, 30, 34), [(p[0], p[1] + 2) for p in tail])
        pygame.draw.rect(bub, (30, 30, 34), r.inflate(4, 4), border_radius=gfx.si(14))
        pygame.draw.rect(bub, (255, 255, 255), r, border_radius=gfx.si(12))
        pygame.draw.polygon(bub, (255, 255, 255), tail)
        bub.blit(t, t.get_rect(center=r.center))
        bub.set_alpha(alpha)
        surf.blit(bub, (box.x - 2, box.y - 2))

    def draw_finish(self, surf, cam, race_m):
        from game import START_X
        x = START_X + race_m
        x0, x1 = cam.view(4.0)
        if not x0 < x < x1:
            return
        ppm = cam.ppm
        g = self.terrain.height(x)
        left, right = cam.to_screen(x - 0.25, g), cam.to_screen(x + 0.25, g)
        top = 4.2 * ppm
        for px in (left[0] - 0.3 * ppm, right[0] + 0.3 * ppm):
            pygame.draw.line(surf, (60, 60, 66), (px, left[1] + 6), (px, left[1] - top), max(3, int(0.14 * ppm)))
        n, rows = 8, 2
        cw = 0.5 * ppm / 2
        for i in range(n):
            for j in range(rows):
                col = (30, 30, 34) if (i + j) % 2 else (250, 250, 250)
                pygame.draw.rect(surf, col, (left[0] + (j * cw) - 2, left[1] - (i + 1) * 0.5 * ppm, cw + 1, 0.5 * ppm + 1))
        banner = pygame.Rect(0, 0, 3.4 * ppm, 0.8 * ppm)
        banner.midbottom = ((left[0] + right[0]) / 2, left[1] - top + 0.4 * ppm)
        pygame.draw.rect(surf, (30, 30, 34), banner.inflate(6, 6), border_radius=int(0.1 * ppm))
        pygame.draw.rect(surf, (230, 40, 44), banner, border_radius=int(0.1 * ppm))
        t = gfx.text("black_i", 30, "FINISH", (255, 255, 255), outline=(30, 30, 34), width=2)
        t = pygame.transform.smoothscale_by(t, min(1.0, banner.h * 0.9 / t.get_height()))
        surf.blit(t, t.get_rect(center=banner.center))


class Particles:
    def __init__(self):
        self.items = []
        self._puffs = {}

    def _puff(self, r, color):
        key = (int(r), color)
        img = self._puffs.get(key)
        if img is None:
            if len(self._puffs) > 300:
                self._puffs.clear()
            img = self._puffs[key] = sprites.soft_puff(max(2, int(r)), color)
        return img

    def add(self, kind, x, y, vx, vy, life, size, color, grav=9.8, back=True):
        if len(self.items) < 320:
            self.items.append([kind, x, y, vx, vy, 0.0, life, size, color, grav, back])

    def update(self, dt):
        alive = []
        for p in self.items:
            p[5] += dt
            if p[5] >= p[6]:
                continue
            if p[0] == "smoke":
                p[3] *= 1 - 1.2 * dt
            p[4] -= p[9] * dt
            p[1] += p[3] * dt
            p[2] += p[4] * dt
            alive.append(p)
        self.items = alive

    def draw(self, surf, cam, back):
        for kind, x, y, vx, vy, age, life, size, color, grav, b in self.items:
            if b != back:
                continue
            sx, sy = cam.to_screen(x, y)
            k = age / life
            if kind == "chunk":
                r = max(1.5, size * cam.ppm * (1 - k * 0.5))
                pygame.draw.rect(surf, color, (sx - r / 2, sy - r / 2, r, r))
            elif kind == "smoke":
                r = size * cam.ppm * (0.6 + k * 1.6)
                img = self._puff(r, color).copy()
                img.set_alpha(int(255 * (1 - k) ** 1.3))
                surf.blit(img, (sx - r, sy - r))
            elif kind == "spark":
                r = size * cam.ppm * (1 - k)
                pygame.draw.circle(surf, color, (sx, sy), max(1, r))


class CarView:
    """Everything needed to draw one vehicle (the player's or another player's)."""

    def __init__(self, car, driver="default", wobble=(0.0, 0.0, 0.0), lights=False, label=None,
                 color=(255, 255, 255), bubble=None, ghost=False):
        self.car, self.driver, self.wobble, self.lights = car, driver, wobble, lights
        self.label, self.color, self.bubble, self.ghost = label, color, bubble, ghost
