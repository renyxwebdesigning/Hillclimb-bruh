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
import vehicle_art
from config import BASE_PPM, vehicle_stats
from physics import rest_wheel_offsets
from terrain import RES, START


QUALITY = "high"     # "low" skips pebbles and roadside props


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
            r = 0.27 if spec["head_art"] in ("helmet", "helmet_blue", "racer") else 0.23
            self.head = drivers.face(driver, r * ppm)
        self.wheels = [vehicle_art.wheel(style, w[2], ppm) for style, w in zip(spec["wheel_art"], spec["wheels"])]
        self.flames = [vehicle_art.flame(ppm, 1.1 if spec["key"] == "rocket" else 0.8, seed=i) for i in range(4)]


class Art:
    """Sprites at the camera's closest zoom; scaled down when it zooms out."""

    def __init__(self):
        self.ppm = BASE_PPM * gfx.U
        self.fuel = sprites.fuel_can(self.ppm)
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
            if len(self._cache) > 500:
                self._cache.clear()
            surf = self._cache[key] = make()
        return surf


def compose_vehicle(art, spec, scale, levels=None, angle=0.0, driver="default"):
    """A still picture of a vehicle at rest, for menus. Returns (surface, chassis centre)."""
    va = art.vehicle(spec, driver)
    stats = vehicle_stats(spec, levels or {})
    wheels = rest_wheel_offsets(spec, stats)
    k = art.ppm * scale
    ext = vehicle_art.EXTENT[spec["key"]]
    size = int(2 * ext * k)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    ca, sa = math.cos(angle), math.sin(angle)

    def P(x, y):
        return (c + (x * ca - y * sa) * k, c - (x * sa + y * ca) * k)
    _draw_vehicle_parts(surf, P, k, spec, va, scale, angle,
                        [(lx, ly, r, 0.0) for lx, ly, r in wheels], (0.0, 0.0, 0.0), True)
    return surf, (c, c)


def _draw_vehicle_parts(surf, P, k, spec, va, scale, angle, wheels, wobble, still, flame=None):
    """Shared by gameplay and menus. wheels: (lx, ly, radius, spin) in local or world coords via P."""
    rig = spec["rig"]
    anchors = [(w[0], w[1]) for w in spec["wheels"]]
    wheel_imgs = [pygame.transform.rotozoom(img, math.degrees(w[3]), scale) for img, w in zip(va.wheels, wheels)]
    centres = [P(w[0], w[1]) for w in wheels] if still else [w[4] for w in wheels]

    def draw_wheels():
        for img, ctr in zip(wheel_imgs, centres):
            surf.blit(img, img.get_rect(center=ctr))

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
            pygame.draw.lines(surf, (230, 70, 50) if w[2] > 0.6 else (176, 180, 188), False, pts,
                              max(2, int((0.05 if w[2] > 0.6 else 0.035) * k)))

    body = pygame.transform.rotozoom(va.body, math.degrees(angle), scale)
    hx, hy = spec["head"][0] + wobble[0], spec["head"][1] + wobble[1]
    head = pygame.transform.rotozoom(va.head, math.degrees(angle + wobble[2]), scale)
    head_pos = P(hx, hy)
    body_pos = P(0.0, 0.0)
    if spec.get("head_behind"):
        surf.blit(head, head.get_rect(center=head_pos))
        surf.blit(body, body.get_rect(center=body_pos))
    else:
        surf.blit(body, body.get_rect(center=body_pos))
        surf.blit(head, head.get_rect(center=head_pos))
    if rig not in ("bike", "tank", "hover"):
        draw_wheels()
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
            "jungle": ((255, 250, 220), 0.78, 0.14, 36), "mars": ((255, 240, 220), 0.7, 0.22, 20)}
    SHAPES = {"clouds": 0, "sun": 1, "snow": 2, "space": 3, "city": 4, "volcano": 5, "jungle": 0, "mars": 1}
    WEATHER = {"snow": "snow", "jungle": "rain", "volcano": "embers", "mars": "dust"}

    def __init__(self, stage):
        self.stage = stage
        W, H = gfx.W, gfx.H
        sky = gfx.opaque(gfx.vgradient(W, H, *stage["sky"]))
        rnd = random.Random(stage["seed"])
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
        else:
            sun = self.SUNS[decor]
            glow = sprites.soft_puff(gfx.s(sun[3] * 3.4), sun[0])
            sky.blit(glow, glow.get_rect(center=(W * sun[1], H * sun[2])))
            pygame.draw.circle(sky, sun[0], (W * sun[1], H * sun[2]), gfx.s(sun[3]))
            if decor == "mars":                       # Phobos and Deimos
                for x, y, r in ((0.22, 0.14, 9), (0.34, 0.24, 5)):
                    pygame.draw.circle(sky, (210, 180, 160), (W * x, H * y), gfx.s(r))
                    pygame.draw.circle(sky, (180, 150, 130), (W * x + gfx.s(r * 0.3), H * y + gfx.s(r * 0.2)), gfx.s(r * 0.35))
        self.sky = sky
        self.night = lighting.night_sky(stage, W, H) if stage.get("cycle") else None
        self.sunset = lighting.sunset_sky(W, H) if stage.get("cycle") else None
        self.clouds = []
        tint = {"sun": (255, 246, 230), "volcano": (74, 56, 56), "mars": (236, 196, 170)}.get(decor, (255, 255, 255))
        if decor not in ("space",):
            n = 6 if decor != "mars" else 3
            for i in range(n):
                w = gfx.s(rnd.uniform(170, 290))
                self.clouds.append(((i + rnd.uniform(0.1, 0.6)) / n, rnd.uniform(0.06, 0.34),
                                    sprites.cloud(w, w * 0.42, tint), rnd.uniform(0.04, 0.09)))
        self.weather = self.WEATHER.get(decor)
        count = {"snow": 160, "rain": 220, "embers": 90, "dust": 120}.get(self.weather, 0)
        self.flakes = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.6, 1.4)] for _ in range(count)]

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

    def draw(self, surf, cam, dt, darkness=0.0, sunset=0.0):
        W, H = gfx.W, gfx.H
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
        st = self.stage
        far, near = st["far"]
        if night > 0:
            far = gfx.mix(far, (24, 30, 60), night * 0.55)
            near = gfx.mix(near, (18, 24, 50), night * 0.55)
        shape = self.SHAPES[st["decor"]]
        if shape == 4:
            self._skyline(surf, cam, far, 0.05, 0.62, 1.0, night, 3)
            self._skyline(surf, cam, near, 0.12, 0.74, 0.75, night, 9)
        elif shape == 5:
            self._volcanoes(surf, cam, far, near)
        else:
            self._ridge(surf, cam, far, 0.05, 0.58, gfx.s(80), shape, 0.0, None)
            trees = {"clouds": "round", "snow": "pine", "jungle": "jungle"}.get(st["decor"])
            self._ridge(surf, cam, near, 0.13, 0.7, gfx.s(55), shape, 2.0, trees)
        self._weather(surf, cam, dt)

    def _weather(self, surf, cam, dt):
        if not self.flakes:
            return
        W, H, U = gfx.W, gfx.H, gfx.U
        kind = self.weather
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
                if trees in ("round", "jungle"):
                    pygame.draw.circle(surf, col, (sx, y - size * 0.6), size)
                    pygame.draw.rect(surf, col, (sx - size * 0.15, y - size * 0.4, size * 0.3, size))
                else:
                    pygame.draw.polygon(surf, col, [(sx - size * 0.7, y + 2), (sx + size * 0.7, y + 2), (sx, y - size * 2.4)])
        pygame.draw.polygon(surf, color, pts)


class WorldRenderer:
    def __init__(self, stage, terrain, art):
        self.stage, self.terrain, self.art = stage, terrain, art
        self.backdrop = Backdrop(stage)
        self.coin_x = [c[0] for c in terrain.coins]
        self.fuel_x = [f[0] for f in terrain.fuel]
        self.prop_x = [p[0] for p in terrain.props]
        self.glow = sprites.soft_puff(gfx.s(60), (255, 214, 120))
        self.lighting = lighting.Lighting()
        self._lamps = []

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

        for a, b, level in t.bridges:
            if b > x0 and a < x1:
                if level is not None:
                    self._draw_water(surf, cam, a, b, level, now)
                self._draw_bridge(surf, cam, a, b)
        for a, b in t.tunnels:
            if b > x0 - 2 and a < x1 + 2:
                self._draw_tunnel(surf, cam, a, b, now)
        for a, b, level in t.pits:
            if b > x0 and a < x1:
                self._draw_water(surf, cam, a - 0.3, b + 0.3, level, now)
        if st["key"] == "city":
            dash = max(2, int(gfx.s(3)))
            for i in range(i0 - i0 % 12, i1 - 6, 12):
                if t.feature_at(START + i * RES) == "bridge":
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
                img = self.art.cached(("pebble", st["key"], pr),
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
            img = self.art.cached(("prop", kind, variant, bucket, round(scale, 1), flip),
                                  lambda: self._prop_img(kind, variant, bucket * scale, flip))
            sx, sy = cam.to_screen(x, t.visual_height(x) - 0.06)
            surf.blit(img, img.get_rect(midbottom=(sx, sy)))
            light = prop_art.LIGHTS.get(kind)
            if light:
                lx = -light[0] if flip else light[0]
                self._lamps.append((sx + lx * cam.ppm * scale, sy - light[1] * cam.ppm * scale))

    @staticmethod
    def _prop_img(kind, variant, ppm, flip):
        img = prop_art.make(kind, ppm, variant)
        return pygame.transform.flip(img, True, False) if flip else img

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
        fuel = self.terrain.fuel
        for i in range(bisect.bisect_left(self.fuel_x, x0), bisect.bisect_right(self.fuel_x, x1)):
            x, y, taken = fuel[i]
            if taken:
                continue
            sc = cam.ppm / self.art.ppm
            img = self.art.cached(("fuel", round(sc, 2)), lambda: pygame.transform.smoothscale_by(self.art.fuel, sc))
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
        _draw_vehicle_parts(surf, P, cam.ppm, car.spec, va, sc, car.angle, wheels, wobble, False, flame)

    def draw(self, surf, cam, views, particles, now, dt, best, darkness=0.0, sunset=0.0, race_m=0):
        """views: list of CarView, the player's own car last (drawn on top)."""
        self._lamps = []
        self.backdrop.draw(surf, cam, dt, darkness, sunset)
        self.draw_props(surf, cam)
        self.draw_terrain(surf, cam, now)
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
