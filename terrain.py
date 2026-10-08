"""Procedural track: hills, bridges over gorges, tunnels, caves, jumps, walls, pickups and props.

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
# set pieces built around obstacles (terrain.things); feature_at reports their stretch by this name
BLOCK_KINDS = ("cars", "traffic", "crates", "wrecker", "boulder", "flames", "spinner", "spikes")


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
        difficulty = (0.6 * _smoothstep(8, 50, dist)
                      + 0.45 * _smoothstep(50, 900, dist)
                      + 0.4 * _smoothstep(900, 3000, dist)
                      + 0.3 * _smoothstep(3000, 7000, dist))
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
        self.zones, self.bumps = self._place_obstacles(xs, h, v, np.random.default_rng(stage["seed"] + 9))
        self._zone_a = [z[0] for z in self.zones]
        self.h = h.tolist()
        self.v = v.tolist()
        self.c = ceil.tolist()
        self._tunnel_a = [a for a, _ in self.tunnels]
        self.spike_x = [sp[0] for sp in self.spikes]
        self.things.sort(key=lambda th: th["x"])
        self.thing_x = [th["x"] for th in self.things]
        self.nitro, self.coins = self._place_pickups(np.random.default_rng(stage["seed"] + 1))
        self.props = self._place_props(np.random.default_rng(stage["seed"] + 3))
        self.landmarks = self._place_landmarks(np.random.default_rng(stage["seed"] + 5))
        self.trophies = place_trophies(self, __import__("random").Random(stage["seed"] * 31))

    # ----------------------------------------------------------- features
    def _build_features(self, xs, h, rng):
        """Cut gorges under bridges, dig tunnels and caves, add jumps, walls and steps (modifies h)."""
        v = h.copy()
        ceil = np.full(len(h), INF)
        self.bridges, self.tunnels, self.pits = [], [], []
        self.caves, self.spikes, self.walls, self.steps = [], [], [], []
        self.things, self.blocks = [], []          # obstacles with their own shapes; (a, b, kind) stretches they need
        water = self.stage["water"]
        lava = self.stage.get("lava", False)
        # gaps (and lava pits) everywhere except underwater, where nobody could jump them through the water
        wet = bool(self.stage.get("water_drag"))
        city = self.stage["key"] == "city"
        table = [("bridge", 2.0), ("tunnel", 1.4), ("cave", 3.4), ("wall", 2.0), ("steps", 1.4),
                 ("pit", 3.0 if lava else 0.0 if wet else 1.6),
                 ("cars", 0.0 if wet else 2.6 if city else 1.6), ("traffic", 0.0 if wet else 2.6 if city else 1.2),
                 ("crates", 2.2), ("wrecker", 1.3), ("boulder", 1.3), ("flames", 1.4), ("spinner", 1.2),
                 ("spikes", 0.0 if wet else 1.3)]
        kinds = [k for k, _ in table]
        odds = np.array([w for _, w in table])
        odds /= odds.sum()
        x = 150.0 + rng.uniform(0, 40)
        while x < LENGTH - 300:
            hard = float(_smoothstep(150, 3000, np.array(x)))     # 0 near the start, 1 from 3 km on
            kind = kinds[int(rng.choice(len(kinds), p=odds))]
            while x < 450 and kind in ("wrecker", "traffic", "boulder", "spinner", "flames", "spikes"):
                kind = kinds[int(rng.choice(len(kinds), p=odds))]         # warm up before anything moves
            for _ in range(14):
                span = {"bridge": lambda: rng.uniform(13, 22),
                        "tunnel": lambda: rng.uniform(26, 42),
                        "cave": lambda: rng.uniform(70, 110) + 90 * hard,
                        "pit": lambda: rng.uniform(4.0, 5.5) + 2.5 * hard,
                        "wall": lambda: 0.0,
                        "steps": lambda: 0.0,
                        "cars": lambda: 0.0,
                        "traffic": lambda: rng.uniform(26, 34),
                        "crates": lambda: 30.0,
                        "wrecker": lambda: 22.0,
                        "boulder": lambda: 34.0,
                        "flames": lambda: 0.0,
                        "spinner": lambda: 22.0,
                        "spikes": lambda: 0.0}[kind]()
                if kind == "flames":
                    jets = 2 + int(rng.random() < 0.4 + 0.5 * hard) + int(rng.random() < 0.4 * hard)
                    span = 12 + 4.0 * jets + 8
                elif kind == "spikes":
                    spiked = rng.uniform(3.5, 5.0) + 1.2 * hard
                    span = 11 + 1.0 + spiked + 12
                if kind == "cars":
                    count = 1 + int(rng.random() < 0.25 + 0.5 * hard) + int(rng.random() < 0.3 * hard)
                    span = 11 + 2.5 + 4.0 * count + 12
                if kind == "wall":
                    height = rng.uniform(4.0, 6.5) + 5.0 * hard
                    steep = rng.uniform(0.62, 0.72) + 0.3 * hard            # steepest slope of the climb
                    climb, top = 1.5 * height / steep, rng.uniform(3, 9)
                    fall = climb * rng.uniform(1.0, 1.8)
                    if rng.random() < 0.35:                                 # the other way round: a steep drop
                        climb, fall = fall, climb
                    span = climb + top + fall
                elif kind == "steps":
                    count = int(rng.integers(3, 6)) + int(round(2 * hard))
                    rises = rng.uniform(0.3, 0.45, count) + 0.2 * hard
                    treads = rng.uniform(2.6, 4.2, count)
                    span = float(treads.sum()) + 0.9 * count + 3.0
                ia, ib = int((x - START) / RES), int((x + span - START) / RES)
                if kind == "cave" or abs(h[ib] - h[ia]) <= (0.08 * span if kind == "pit" else 0.1 * span):
                    break
                x += 7.0
            else:
                x += 90.0
                continue
            gap = rng.uniform(170, 330) * (1.0 - 0.45 * hard)
            sl = slice(ia, ib + 1)
            t = (xs[sl] - xs[ia]) / (xs[ib] - xs[ia])
            if kind in BLOCK_KINDS:
                self._level(xs, h, v, ia, ib)
                g = lambda px: float(h[int((px - START) / RES)])          # noqa: E731
                a = float(xs[ia])
                if kind == "cars":
                    # A kicker, then a row of parked cars to jump. Land on a roof if you must, hit a side and you crash.
                    lip = a + 11
                    r0 = ia
                    seg = slice(r0, int((lip - START) / RES) + 1)
                    u = (xs[seg] - a) / 11
                    h[seg] += (1.7 + 0.6 * hard) * u ** 2.2
                    v[seg] = h[seg]
                    for k in range(count):
                        cx = lip + 2.5 + 1.85 + 4.0 * k
                        self.things.append(dict(kind="car", x=cx, y=g(cx), flip=bool(rng.random() < 0.5),
                                                variant=int(rng.integers(3))))
                elif kind == "traffic":
                    # A car driving back and forth; a kicker at the start to jump it when the timing is right.
                    seg = slice(ia, int((a + 9 - START) / RES) + 1)
                    u = (xs[seg] - a) / 9
                    h[seg] += 1.5 * u ** 2.2
                    v[seg] = h[seg]
                    self.things.append(dict(kind="traffic", a=a + 12, b=float(xs[ib]) - 3, x=a + 12,
                                            period=float(rng.uniform(5.5, 7.5) - 1.0 * hard),
                                            phase=float(rng.uniform(0, 10)), variant=int(rng.integers(3)), y=g(a + 12)))
                elif kind == "crates":
                    # A wall you can't jump: smash through it with enough speed (boost helps).
                    cx = a + 24
                    self.things.append(dict(kind="crates", x=cx, y=g(cx), w=1.0 + 0.8 * int(rng.random() < hard),
                                            hgt=2.6, need=5.5 + 4.0 * hard))
                elif kind == "boulder":
                    # Boulders keep rolling down at you out of a rock pile; jump them off the kicker.
                    seg = slice(ia, int((a + 9 - START) / RES) + 1)
                    u = (xs[seg] - a) / 9
                    h[seg] += 1.7 * u ** 2.2
                    v[seg] = h[seg]
                    # one boulder per wave, then a quiet spell: go right after one has rolled past
                    self.things.append(dict(kind="boulder", a=float(xs[ib]) - 2, b=a + 10.5, x=a + 25, r=0.9,
                                            period=float(rng.uniform(5.5, 6.5) - 0.6 * hard), roll=0.45,
                                            phase=float(rng.uniform(0, 10)), y=g(a + 25)))
                elif kind == "flames":
                    # Gas jets that flare up one after the other; the gap between flares runs forward at
                    # about driving speed, so ride it.
                    period = float(rng.uniform(2.6, 3.4) - 0.4 * hard)
                    phase0 = float(rng.uniform(0, 10))
                    for k in range(jets):
                        jx = a + 12 + 4.0 * k
                        self.things.append(dict(kind="flames", x=jx, y=g(jx), period=period,
                                                phase=phase0 - k * 4.0 / 10.0, duty=0.36 + 0.1 * hard))
                elif kind == "spinner":
                    # A two-armed bar turning over the road like a windmill.
                    cx = a + 12
                    self.things.append(dict(kind="spinner", x=cx, y=g(cx), arm=3.0, py=g(cx) + 3.1,
                                            period=float(rng.uniform(4.2, 5.4) - 0.8 * hard),
                                            phase=float(rng.uniform(0, 10))))
                elif kind == "spikes":
                    # A kicker, then a bed of spikes to fly over.
                    lip = a + 11
                    seg = slice(ia, int((lip - START) / RES) + 1)
                    u = (xs[seg] - a) / 11
                    h[seg] += (1.7 + 0.8 * hard) * u ** 2.2
                    v[seg] = h[seg]
                    x0 = lip + 1.0
                    self.things.append(dict(kind="spikes", x=x0 + spiked / 2, x0=x0, x1=x0 + spiked, y=g(x0 + spiked / 2)))
                else:
                    # A wrecking ball swinging across the road from a crane.
                    cx = a + 12
                    self.things.append(dict(kind="wrecker", x=cx, y=g(cx), py=g(cx) + 6.3, length=4.7, r=0.8,
                                            amp=1.25, period=float(rng.uniform(4.2, 5.4) - 0.6 * hard),
                                            phase=float(rng.uniform(0, 10))))
                self.blocks.append((a, float(xs[ib]), kind))
            elif kind == "pit":
                # A kicker ramp, then a lava pit (or a bottomless gap) you have to jump.
                r0 = int((x - 10 - START) / RES)
                seg = slice(r0, ia + 1)
                u = (xs[seg] - xs[r0]) / (xs[ia] - xs[r0])
                lift = (1.6 + 0.5 * hard) * u ** 2.4
                h[seg] += lift
                v[seg] += lift
                # a flat landing, so nobody respawning there rolls back in
                land = slice(ib, ib + int(8 / RES) + 1)
                h[land] = h[ib]
                v[land] = h[ib]
                ease = slice(ib + int(8 / RES), ib + int(18 / RES) + 1)
                u = np.linspace(0, 1, ease.stop - ease.start)
                h[ease] = h[ib] + (h[ease] - h[ib]) * (u * u * (3 - 2 * u))
                v[ease] = h[ease]
                level = min(h[ia], h[ib]) - 1.8
                floor = level - (3.0 if lava else 14.0)
                h[ia + 1:ib] = floor
                v[ia + 1:ib] = floor
                self.pits.append((float(xs[ia]), float(xs[ib]), float(level)))
            elif kind == "wall":
                # A steep hill wall: climb it with momentum or roll back down.
                x0 = xs[ia]
                shape = height * (_smoothstep(x0, x0 + climb, xs[sl])
                                  - _smoothstep(x0 + climb + top, x0 + span, xs[sl]))
                h[sl] += shape
                v[sl] += shape
                self.walls.append((float(x0), float(xs[ib])))
            elif kind == "steps":
                # Rock ledges up (or down) a slope; each riser is a sharp kick for the suspension.
                up = rng.random() < 0.7
                order = range(count) if up else range(count - 1, -1, -1)
                shape = np.zeros(ib - ia + 1)
                pos = xs[ia] + 1.5
                risers = []
                for k in order:
                    pos += treads[k]
                    shape += (1 if up else -1) * rises[k] * _smoothstep(pos, pos + 0.9, xs[sl])
                    risers.append((float(pos), float(pos + 0.9)))
                    pos += 0.9
                h[sl] += shape
                v[sl] += shape
                h[ib + 1:] += shape[-1]                  # the rest of the track carries on from the top (or bottom)
                v[ib + 1:] += shape[-1]
                self.steps.append((float(xs[ia]), float(xs[ib]), risers))
            elif kind == "bridge":
                ha, hb = h[ia], h[ib]
                deck = ha + (hb - ha) * t - (0.3 + 0.02 * span) * np.sin(np.pi * t)
                depth = rng.uniform(5.5, 9.0)
                gorge = deck - depth * np.sin(np.pi * t) ** 0.35
                v[sl] = np.minimum(v[sl], gorge)
                h[sl] = deck
                level = float(v[sl].min()) + depth * 0.32 if water else None
                self.bridges.append((float(xs[ia]), float(xs[ib]), level))
            else:
                if kind == "cave":
                    # a rough, bumpy floor that calms down near both portals
                    fade = _smoothstep(xs[ia], xs[ia] + 8, xs[sl]) * (1 - _smoothstep(xs[ib] - 8, xs[ib], xs[sl]))
                    # big hills inside launch you into the roof: iron them out, keep the rocky bumps
                    k = int(24 / RES)
                    calm = np.convolve(np.pad(h[sl], k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
                    h[sl] += (calm - h[sl]) * fade
                    rough = (0.3 + 0.35 * hard) * (0.6 if self.stage["gravity"] < 6 else 1.0)
                    h[sl] += rough * fade * _catmull_rom_noise((xs[sl] - xs[ia]) / 6.0, rng)
                # Smooth the approach and exit so nobody gets launched into the portal face.
                run_in = 36 if kind == "cave" else 22
                for lo, hi, entering in ((ia - int(run_in / RES), ia, True), (ib, ib + int(14 / RES), False)):
                    seg = slice(lo, hi + 1)
                    u = (xs[seg] - xs[lo]) / (xs[hi] - xs[lo])
                    line = h[lo] + (h[hi] - h[lo]) * u
                    wgt = (u * u * (3 - 2 * u)) if entering else 1 - (u * u * (3 - 2 * u))
                    h[seg] = h[seg] + (line - h[seg]) * wgt
                    v[seg] = h[seg]
                if kind == "cave":
                    roof = self._dig_cave(xs, h, v, ceil, ia, ib, hard, rng)
                    self.caves.append((float(xs[ia]), float(xs[ib])))
                else:
                    ha, hb = h[ia], h[ib]
                    road = ha + (hb - ha) * t
                    roof = road + 4.0 + 0.25 * np.sin(np.pi * t)          # room for the LKW and the horse rider
                    v[sl] = np.maximum(v[sl], roof + 1.0 + 3.4 * np.sin(np.pi * t) ** 0.7)
                    h[sl] = road
                    ceil[sl] = roof
                    if rng.random() < 0.25 + 0.5 * hard:
                        cx = float(xs[ia] + xs[ib]) / 2
                        i = int((cx - START) / RES)
                        self._crusher(cx, float(h[i]), float(roof[i - ia]), hard, rng)
                self.tunnels.append((float(xs[ia]), float(xs[ib])))
            x += span + gap
        return v, ceil

    def _dig_cave(self, xs, h, v, ceil, ia, ib, hard, rng):
        """A long cave: the floor keeps its hills, the roof rises and dips with it, stalactites hang down.

        The roof always stays at least 4.2 m above the highest floor within 2.5 m (more where gravity is low), so every vehicle
        fits through; jumping over a crest in here is what gets you.
        """
        sl = slice(ia, ib + 1)
        w = int(2.5 / RES)
        floor = np.pad(h[sl], w, mode="edge")
        peak = np.lib.stride_tricks.sliding_window_view(floor, 2 * w + 1).max(axis=1)
        x = xs[sl]
        ends = _smoothstep(xs[ia], xs[ia] + 10, x) * (1 - _smoothstep(xs[ib] - 10, xs[ib], x))
        floaty = 2.0 if self.stage["gravity"] < 6 else 0.0        # Moon, Mars, underwater: you bounce much higher
        room = 4.6 + floaty - 0.3 * hard + 1.2 * (1 - ends) + 2.8 * ends * (0.5 + 0.5 * _catmull_rom_noise((x - xs[ia]) / 13, rng))
        roof = peak + room
        roof = np.convolve(np.pad(roof, 2, mode="edge"), np.ones(5) / 5, mode="valid")
        c = roof.copy()
        crush = []
        if hard > 0.1:
            for _ in range(1 + int(rng.random() < hard)):
                p = float(rng.uniform(xs[ia] + 20, xs[ib] - 20))
                i = int((p - xs[ia]) / RES)
                if all(abs(p - q) > 18 for q in crush):
                    crush.append(p)
                    self._crusher(p, float(peak[i]), float(roof[i]), hard, rng)
        p = xs[ia] + rng.uniform(4, 8)
        while p < xs[ib] - 5:
            if any(abs(p - q) < 2.5 for q in crush):
                p += 3.0
                continue
            i = int((p - xs[ia]) / RES)
            spare = roof[i] - peak[i] - 4.2 - floaty
            if spare > 0.4:
                length = min(2.4, rng.uniform(0.45, 1.0) * spare)
                half = rng.uniform(0.35, 0.65) + 0.18 * length
                near = np.abs(x - p) < half
                c[near] = np.minimum(c[near], roof[near] - length * (1 - np.abs(x[near] - p) / half))
                self.spikes.append((float(p), float(roof[i]), float(roof[i] - length), float(half)))
            p += rng.uniform(2.5, 7.5) * (1.0 - 0.35 * hard)
        ceil[sl] = c
        t = (x - xs[ia]) / (xs[ib] - xs[ia])
        v[sl] = np.maximum(v[sl], roof + 1.4 + rng.uniform(2.0, 4.0) * np.sin(np.pi * t) ** 0.6)
        return roof

    def _level(self, xs, h, v, ia, ib):
        """Make [ia, ib] a straight road, easing in and out of it."""
        for lo, hi, entering in ((ia - int(14 / RES), ia, True), (ib, ib + int(10 / RES), False)):
            seg = slice(lo, hi + 1)
            u = (xs[seg] - xs[lo]) / (xs[hi] - xs[lo])
            line = h[lo] + (h[hi] - h[lo]) * u
            wgt = (u * u * (3 - 2 * u)) if entering else 1 - (u * u * (3 - 2 * u))
            h[seg] = h[seg] + (line - h[seg]) * wgt
            v[seg] = h[seg]
        sl = slice(ia, ib + 1)
        h[sl] = h[ia] + (h[ib] - h[ia]) * (xs[sl] - xs[ia]) / (xs[ib] - xs[ia])
        v[sl] = h[sl]

    def _crusher(self, x, floor, roof, hard, rng):
        """A stone block that slams down from the roof; under it at the wrong moment and you're flat."""
        self.things.append(dict(kind="crusher", x=x, y=floor, top=roof - 0.1, low=floor + 1.0, w=1.7,
                                period=float(rng.uniform(2.6, 3.6) - 0.5 * hard), phase=float(rng.uniform(0, 10))))

    def thing_range(self, x0, x1):
        """Indices of the things that may reach into [x0, x1]."""
        return range(bisect.bisect_left(self.thing_x, x0 - 16), bisect.bisect_right(self.thing_x, x1 + 16))

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
        for a, b in self.walls:
            if a - pad <= x <= b + pad:
                return "wall"
        for a, b, _ in self.steps:
            if a - pad <= x <= b + pad:
                return "steps"
        for a, b, kind in self.blocks:
            if a - pad <= x <= b + pad:
                return kind
        return None

    def cave_at(self, x, pad=0.0):
        for a, b in self.caves:
            if a - pad <= x <= b + pad:
                return a, b
        return None

    # ---------------------------------------------------------- obstacles
    # patches that change how the road drives: (grip multiplier, drag that slows the wheels and the body)
    ZONES = {"mud": (0.55, 2.6), "ice": (0.22, 0.0), "snow": (0.7, 1.7), "sand": (0.7, 1.3), "oil": (0.25, 0.0),
             "seaweed": (0.8, 2.2)}
    BUMPS = {"rocks": (0.75, 3.2), "log": (0.55, 1.6), "speedbump": (0.32, 2.4)}     # height, length (m)

    def _place_obstacles(self, xs, h, v, rng):
        """Mud, ice, snow drifts, sand, oil, rocks, logs and speed bumps, every 60-130 m after the start."""
        zones, bumps = [], []
        x = 75.0
        while x < LENGTH - 60:
            x += float(rng.uniform(45, 110))
            kinds = self._kinds(x, "obstacles")
            if not kinds:
                continue
            kind = kinds[int(rng.integers(len(kinds)))]
            if kind in self.BUMPS:
                height, length = self.BUMPS[kind]
                if self.feature_at(x, 10.0):
                    continue
                lo, hi = int((x - length / 2 - START) / RES), int((x + length / 2 - START) / RES)
                if hi + 1 >= len(h):
                    break
                u = np.linspace(0, 1, hi - lo + 1)
                shape = np.sin(np.pi * u) ** (0.6 if kind == "rocks" else 1.4) * height * rng.uniform(0.8, 1.15)
                h[lo:hi + 1] += shape
                v[lo:hi + 1] += shape
                bumps.append((x, kind, length))
            else:
                length = float(rng.uniform(9, 18))
                if self.feature_at(x, 8.0) or self.feature_at(x + length, 8.0):
                    continue
                if kind == "snow":                       # a drift: a soft hump of deep snow
                    lo, hi = int((x - START) / RES), int((x + length - START) / RES)
                    if hi + 1 >= len(h):
                        break
                    u = np.linspace(0, 1, hi - lo + 1)
                    shape = np.sin(np.pi * u) ** 1.5 * rng.uniform(0.9, 1.5)
                    h[lo:hi + 1] += shape
                    v[lo:hi + 1] += shape
                zones.append((x, x + length, kind))
        return zones, bumps

    def zone_at(self, x):
        i = bisect.bisect_right(self._zone_a, x) - 1
        if i >= 0 and self.zones[i][0] <= x <= self.zones[i][1]:
            return self.zones[i][2]
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
        # nitro cans: the only way to refill the boost, so it doesn't last forever
        nitro = []
        x = 120.0
        while x < LENGTH - 50:
            x += float(rng.uniform(160, 270))
            if self.feature_at(x, 6.0) in ("tunnel",) + BLOCK_KINDS or self.pit_at(x) \
                    or self.pit_at(x + 3):
                x += 40.0
            nitro.append([x, self.height(x) + 1.05, False])
        coins = []
        fuel_x = [n[0] for n in nitro]
        x = 28.0
        while x < LENGTH - 50:
            cols = int(rng.integers(3, 8))
            rows = int(rng.choice([1, 2, 3], p=[0.5, 0.35, 0.15]))
            span = (cols - 1) * 0.78
            if any(fx - 10 < x + span and x < fx + 10 for fx in fuel_x):
                x += 22.0
                continue
            if {self.feature_at(x, 2), self.feature_at(x + span, 2)} & set(BLOCK_KINDS):
                x += 30.0
                continue
            if self.feature_at(x, 2) == "tunnel" or self.feature_at(x + span, 2) == "tunnel":
                rows = 1
            value = coin_value_at(x)
            for c in range(cols):
                cx = x + c * 0.78
                pit = self.pit_at(cx)
                if pit:
                    f = (cx - pit[0]) / (pit[1] - pit[0])
                    ground = self.height(pit[0]) + 1.2 + 1.6 * math.sin(math.pi * f)
                else:
                    ground = max(self.height(cx - 0.4), self.height(cx), self.height(cx + 0.4))
                ceil = self.ceiling(cx)
                for r in range(rows):
                    if r and ceil is not None and ground + 0.95 + r * 0.78 > ceil - 0.5:
                        break
                    coins.append([cx, ground + 0.95 + r * 0.78, value, False])
            x += span + float(rng.uniform(45, 95))
        return nitro, coins

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


# ------------------------------------------------------------- moving things
CAR_BOXES = ((-1.85, 0.1, 1.85, 0.8), (-1.25, 0.8, 0.9, 1.38))       # body, cabin (facing right)


def crusher_bottom(th, t):
    """Height of a crusher's underside at time t: waits up, slams down, holds, winds back up."""
    u = ((t + th["phase"]) / th["period"]) % 1.0
    if u < 0.42:
        drop = 0.0
    elif u < 0.5:
        drop = ((u - 0.42) / 0.08) ** 2
    elif u < 0.64:
        drop = 1.0
    else:
        drop = 1.0 - (u - 0.64) / 0.36
    up = th["top"] - 1.5
    return up - drop * (up - th["low"])


def traffic_pos(th, t):
    """(x, facing right?) of a car driving back and forth."""
    w = 2 * math.pi * (t + th["phase"]) / th["period"]
    x = th["a"] + (th["b"] - th["a"]) * (0.5 - 0.5 * math.cos(w))
    return x, math.sin(w) > 0


def wrecker_ball(th, t):
    ang = th["amp"] * math.sin(2 * math.pi * (t + th["phase"]) / th["period"])
    return th["x"] + th["length"] * math.sin(ang), th["py"] - th["length"] * math.cos(ang)


def thing_shapes(th, t, idx, terrain):
    """Collision shapes: ("box", x0, y0, x1, y1, idx, solid) or ("ball", cx, cy, r, idx, solid).
    Solid shapes push the vehicle back; the others are deadly to touch."""
    kind = th["kind"]
    if kind in ("car", "traffic"):
        if kind == "car":
            x, right, y, solid = th["x"], not th["flip"], th["y"], True
        else:
            x, right = traffic_pos(th, t)
            y, solid = terrain.height(x), False
        out = []
        for x0, y0, x1, y1 in CAR_BOXES:
            if not right:
                x0, x1 = -x1, -x0
            out.append(("box", x + x0, y + y0, x + x1, y + y1, idx, solid))
        return out
    if kind == "crates":
        return [("box", th["x"] - th["w"] / 2, th["y"] - 0.3, th["x"] + th["w"] / 2, th["y"] + th["hgt"], idx, True)]
    if kind == "crusher":
        b = crusher_bottom(th, t)
        return [("box", th["x"] - th["w"] / 2, b, th["x"] + th["w"] / 2, th["top"], idx, False)]
    if kind == "boulder":
        x, _ = boulder_pos(th, t)
        if x is None:
            return []
        return [("ball", x, terrain.height(x) + th["r"] - boulder_sink(th, t), th["r"], idx, False)]
    if kind == "flames":
        f = flame_height(th, t)
        return [("box", th["x"] - 0.3, th["y"], th["x"] + 0.3, th["y"] + f, idx, False)] if f > 0.3 else []
    if kind == "spinner":
        out = []
        for cx, cy in spinner_points(th, t):
            out.append(("ball", cx, cy, 0.28, idx, False))
        return out
    if kind == "spikes":
        return [("box", th["x0"], th["y"] - 0.2, th["x1"], th["y"] + 0.45, idx, False)]
    cx, cy = wrecker_ball(th, t)
    return [("ball", cx, cy, th["r"], idx, False)]


def boulder_pos(th, t):
    """(x, rolled distance) of this wave's boulder on its way from a down to b; None between waves."""
    u = ((t + th["phase"]) / th["period"]) % 1.0 / th["roll"]
    if u >= 1.0:
        return None, 0.0
    d = (th["a"] - th["b"]) * u
    return th["a"] - d, d


def boulder_sink(th, t):
    """How far the boulder has crumbled into the ground at the end of its run."""
    u = ((t + th["phase"]) / th["period"]) % 1.0 / th["roll"]
    return max(0.0, (u - 0.88) / 0.12) * 2 * th["r"]


def flame_height(th, t):
    """Height of a gas jet's flame (0 while it is off)."""
    u = ((t + th["phase"]) / th["period"]) % 1.0
    if u > th["duty"]:
        return 0.0
    k = min(1.0, u / 0.06, (th["duty"] - u) / 0.06)
    return 3.4 * k


def spinner_points(th, t):
    """Points along both arms of the spinner, for collisions and drawing."""
    ang = 2 * math.pi * (t + th["phase"]) / th["period"]          # the low arm sweeps forward
    ca, sa = math.cos(ang), math.sin(ang)
    return [(th["x"] + ca * d, th["py"] + sa * d) for d in (-3.0, -2.4, -1.8, -1.2, 1.2, 1.8, 2.4, 3.0)]
