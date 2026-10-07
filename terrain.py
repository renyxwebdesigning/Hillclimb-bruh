"""Procedural track: hills, bridges over gorges, tunnels, pickups and props.

Three height profiles are kept:
  h  the drivable surface (bridge decks and tunnel floors included),
  v  the visible ground (gorges under bridges, hills above tunnels),
  c  tunnel ceilings (+inf where there is none).
Each stage has a fixed seed, so a stage is the same track every run.
"""
import bisect
import math

import numpy as np

from config import coin_value_at, season_at
from progress import place_trophies

RES = 0.25          # metres between height samples
START = -60.0       # world x of the first sample
LENGTH = 30000.0    # metres of track
INF = float("inf")


def _catmull_rom_noise(u, rng):
    """Smooth 1-D noise in [-1, 1] at positions u (in units of control spacing)."""
    n = int(u[-1]) + 4
    v = rng.uniform(-1.0, 1.0, n)
    i = np.floor(u).astype(int)
    f = u - i
    p0, p1, p2, p3 = v[i], v[i + 1], v[i + 2], v[i + 3]
    return 0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Terrain:
    def __init__(self, stage):
        rng = np.random.default_rng(stage["seed"])
        n = int(LENGTH / RES)
        xs = START + np.arange(n) * RES
        dist = np.maximum(xs, 0.0)

        # Flat start pad, then hills that grow taller and steeper with distance.
        difficulty = (0.5 * _smoothstep(8, 60, dist)
                      + 0.5 * _smoothstep(60, 1300, dist)
                      + 0.3 * _smoothstep(1300, 4500, dist))
        h = np.zeros(n)
        for wavelength, amp in stage["octaves"]:
            h += amp * _catmull_rom_noise((xs - START) / wavelength, rng)
        h *= difficulty

        if stage["key"] in ("moon", "mars"):
            c = 70.0
            while c < LENGTH:
                w = rng.uniform(4.0, 9.0)
                depth = rng.uniform(0.8, 2.0) * (0.5 + float(_smoothstep(60, 1500, np.array(c))))
                # only the crater's own neighbourhood: further out both terms are exactly 0 anyway
                lo, hi = max(0, int((c - 5 * w - START) / RES)), min(n, int((c + 5 * w - START) / RES) + 1)
                x = xs[lo:hi]
                h[lo:hi] += -depth * np.exp(-((x - c) / (0.45 * w)) ** 2)
                h[lo:hi] += 0.4 * depth * np.exp(-((np.abs(x - c) - 0.75 * w) / (0.22 * w)) ** 2)
                c += rng.uniform(35, 90)

        self.n = n
        self.stage = stage
        v, ceil = self._build_features(xs, h, np.random.default_rng(stage["seed"] + 7))
        self.h = h.tolist()
        self.v = v.tolist()
        self.c = ceil.tolist()
        self._tunnel_a = [a for a, _ in self.tunnels]
        self.fuel, self.coins = self._place_pickups(np.random.default_rng(stage["seed"] + 1))
        self.props = self._place_props(np.random.default_rng(stage["seed"] + 3))
        self.landmarks = self._place_landmarks(np.random.default_rng(stage["seed"] + 5))
        self.trophies = place_trophies(self, __import__("random").Random(stage["seed"] * 31))

    # ----------------------------------------------------------- features
    def _build_features(self, xs, h, rng):
        """Cut gorges under bridges and raise hills over tunnels (modifies h)."""
        v = h.copy()
        ceil = np.full(len(h), INF)
        self.bridges, self.tunnels, self.pits = [], [], []
        water = self.stage["water"]
        lava = self.stage.get("lava", False)
        x = 330.0 + rng.uniform(0, 60)
        while x < LENGTH - 300:
            roll = rng.random()
            kind = ("bridge" if roll < 0.35 else "tunnel" if roll < 0.65 else "pit") if lava else \
                ("bridge" if roll < 0.55 else "tunnel")
            bridge = kind == "bridge"
            for _ in range(14):
                span = rng.uniform(13, 22) if bridge else rng.uniform(5, 7.5) if kind == "pit" else rng.uniform(26, 42)
                ia, ib = int((x - START) / RES), int((x + span - START) / RES)
                if abs(h[ib] - h[ia]) <= (0.08 * span if kind == "pit" else 0.1 * span):
                    break
                x += 7.0
            else:
                x += 90.0
                continue
            if kind == "pit":
                # A kicker ramp, then a lava pit you have to jump.
                r0 = int((x - 10 - START) / RES)
                seg = slice(r0, ia + 1)
                u = (xs[seg] - xs[r0]) / (xs[ia] - xs[r0])
                lift = 1.6 * u ** 2.4
                h[seg] += lift
                v[seg] += lift
                level = min(h[ia], h[ib]) - 1.8
                h[ia + 1:ib] = level - 3.0
                v[ia + 1:ib] = level - 3.0
                self.pits.append((float(xs[ia]), float(xs[ib]), float(level)))
                x += span + rng.uniform(230, 480)
                continue
            sl = slice(ia, ib + 1)
            t = (xs[sl] - xs[ia]) / (xs[ib] - xs[ia])
            ha, hb = h[ia], h[ib]
            if bridge:
                deck = ha + (hb - ha) * t - (0.3 + 0.02 * span) * np.sin(np.pi * t)
                depth = rng.uniform(5.5, 9.0)
                gorge = deck - depth * np.sin(np.pi * t) ** 0.35
                v[sl] = np.minimum(v[sl], gorge)
                h[sl] = deck
                level = float(v[sl].min()) + depth * 0.32 if water else None
                self.bridges.append((float(xs[ia]), float(xs[ib]), level))
            else:
                # Smooth the approach and exit so nobody gets launched into the portal face.
                for lo, hi, entering in ((ia - int(22 / RES), ia, True), (ib, ib + int(14 / RES), False)):
                    seg = slice(lo, hi + 1)
                    u = (xs[seg] - xs[lo]) / (xs[hi] - xs[lo])
                    line = h[lo] + (h[hi] - h[lo]) * u
                    wgt = (u * u * (3 - 2 * u)) if entering else 1 - (u * u * (3 - 2 * u))
                    h[seg] = h[seg] + (line - h[seg]) * wgt
                    v[seg] = h[seg]
                ha, hb = h[ia], h[ib]
                road = ha + (hb - ha) * t
                roof = road + 4.0 + 0.25 * np.sin(np.pi * t)          # room for the LKW and the horse rider
                v[sl] = np.maximum(v[sl], roof + 1.0 + 3.4 * np.sin(np.pi * t) ** 0.7)
                h[sl] = road
                ceil[sl] = roof
                self.tunnels.append((float(xs[ia]), float(xs[ib])))
            x += span + rng.uniform(230, 480)
        return v, ceil

    def feature_at(self, x, pad=0.0):
        for a, b, _ in self.bridges:
            if a - pad <= x <= b + pad:
                return "bridge"
        for a, b in self.tunnels:
            if a - pad <= x <= b + pad:
                return "tunnel"
        for a, b, _ in self.pits:
            if a - pad - 10 <= x <= b + pad:
                return "pit"
        return None

    def pit_at(self, x):
        for a, b, level in self.pits:
            if a <= x <= b:
                return a, b, level
        return None

    # ------------------------------------------------------------ queries
    def _interp(self, arr, x):
        f = (x - START) / RES
        i = int(f)
        if i < 0:
            return arr[0]
        if i >= self.n - 1:
            return arr[-1]
        a = arr[i]
        return a + (arr[i + 1] - a) * (f - i)

    def height(self, x):
        return self._interp(self.h, x)

    def visual_height(self, x):
        return self._interp(self.v, x)

    def ceiling(self, x):
        i = int((x - START) / RES)
        if i < 0 or i >= self.n - 1:
            return None
        a = self.c[i]
        if a == INF:
            return None
        b = self.c[i + 1]
        if b == INF:
            return a
        return a + (b - a) * ((x - START) / RES - i)

    def rock(self, x, y, r=0.0):
        """Push-out for a circle inside the rock around a tunnel: (nx, ny, depth) or None.

        The rock is the band between the tunnel roof and the hill top, with
        vertical faces at both portals.
        """
        i = bisect.bisect_right(self._tunnel_a, x + r) - 1
        if i < 0:
            return None
        a, b = self.tunnels[i]
        if x - r > b:
            return None
        xc = min(max(x, a), b)
        roof, top = self.ceiling(xc), self.visual_height(xc)
        if roof is None or not (roof - r < y < top + r):
            return None
        pen, nx, ny = min(((y + r - roof, 0.0, -1.0), (top + r - y, 0.0, 1.0),
                           (x + r - a, -1.0, 0.0), (b + r - x, 1.0, 0.0)))
        return (nx, ny, pen) if pen > 0 else None

    def normal(self, x):
        d = self.height(x + 0.15) - self.height(x - 0.15)
        inv = 1.0 / math.hypot(0.3, d)
        return -d * inv, 0.3 * inv

    def distance(self, cx, cy, reach):
        """Distance from (cx, cy) to the drivable surface, with the outward normal.

        Negative when the point is below the surface. Only segments within
        `reach` horizontally are considered, which is plenty for wheels.
        """
        i0 = max(0, int((cx - reach - START) / RES) - 1)
        i1 = min(self.n - 2, int((cx + reach - START) / RES) + 1)
        best = 1e9
        bx = by = 0.0
        h = self.h
        for i in range(i0, i1 + 1):
            ax, ay = START + i * RES, h[i]
            ex, ey = RES, h[i + 1] - ay
            t = ((cx - ax) * ex + (cy - ay) * ey) / (ex * ex + ey * ey)
            t = 0.0 if t < 0 else 1.0 if t > 1 else t
            px, py = ax + ex * t, ay + ey * t
            d2 = (cx - px) ** 2 + (cy - py) ** 2
            if d2 < best:
                best, bx, by = d2, px, py
        d = math.sqrt(best)
        below = cy < self.height(cx)
        if d < 1e-6:
            nx, ny = self.normal(cx)
            return 0.0, nx, ny
        nx, ny = (cx - bx) / d, (cy - by) / d
        if below:
            return -d, -nx, -ny
        return d, nx, ny

    # ------------------------------------------------------------ pickups
    def _place_pickups(self, rng):
        fuel = []           # fuel never runs out any more, so no cans

        coins = []
        fuel_x = [f[0] for f in fuel]
        x = 28.0
        while x < LENGTH - 50:
            cols = int(rng.integers(3, 8))
            rows = int(rng.choice([1, 2, 3], p=[0.5, 0.35, 0.15]))
            span = (cols - 1) * 0.78
            if any(fx - 10 < x + span and x < fx + 10 for fx in fuel_x):
                x += 22.0
                continue
            if self.feature_at(x, 2) == "tunnel" or self.feature_at(x + span, 2) == "tunnel":
                rows = 1
            value = coin_value_at(x)
            for c in range(cols):
                cx = x + c * 0.78
                ground = max(self.height(cx - 0.4), self.height(cx), self.height(cx + 0.4))
                for r in range(rows):
                    coins.append([cx, ground + 0.95 + r * 0.78, value, False])
            x += span + float(rng.uniform(45, 95))
        return fuel, coins

    def _kinds(self, x, what):
        """Prop or landmark kinds at x (the Four Seasons stage changes them with the season)."""
        s = season_at(self.stage, x)
        if s is None:
            return self.stage.get(what, ())
        return self.stage["seasons"][s[0]][what]

    def _place_props(self, rng):
        """Scenery along the track: (x, kind, scale, mirrored)."""
        props = []
        x = 12.0
        while x < LENGTH - 50:
            x += float(rng.uniform(3.5, 12.5))
            if self.feature_at(x, 4.0):
                continue
            slope = abs(self.visual_height(x + 0.6) - self.visual_height(x - 0.6)) / 1.2
            kinds = self._kinds(x, "props")
            kind = kinds[int(rng.integers(len(kinds)))]
            if slope > 0.55 and kind not in ("rock", "moonrock", "flowers", "skull", "cone", "lavarock", "marsrock",
                                              "fern", "mushroom"):
                continue
            props.append((x, kind, float(rng.uniform(0.8, 1.2)), bool(rng.random() < 0.5)))
        return props

    def _place_landmarks(self, rng):
        """A big set piece (windmill, pyramid, temple...) every few hundred metres, on fairly flat ground."""
        marks = []
        x = 90.0
        while x < LENGTH - 60:
            x += float(rng.uniform(250, 400))
            kinds = self._kinds(x, "landmarks")
            if not kinds:
                continue
            for _ in range(12):                               # shuffle along to a flat spot
                if not self.feature_at(x, 12.0) and abs(self.visual_height(x + 4) - self.visual_height(x - 4)) < 1.6:
                    marks.append((x, kinds[int(rng.integers(len(kinds)))], bool(rng.random() < 0.5)))
                    break
                x += 9.0
        return marks
