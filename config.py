"""Tuning constants, stages, vehicles and upgrade tables."""

import sys

TITLE = "Hill Rider"
WEB = sys.platform == "emscripten"     # running in a web browser (pygbag)
FPS = 60
PHYS_DT = 1 / 500          # fixed physics step (s)
BASE_PPM = 56              # pixels per metre at 720p, before speed zoom-out
FUEL_SECONDS = 30          # a full tank lasts this long (fuel_rate 1.0)
BOOST_RECHARGE = 9.0       # seconds to refill an empty boost tank

# ---------------------------------------------------------------- stages
# Colours are (r, g, b). "octaves" are (wavelength m, amplitude m) pairs for
# the terrain noise; amplitudes are scaled up with distance.
STAGES = [
    dict(
        key="countryside", name="Countryside", seed=11,
        gravity=9.8, grip=1.0,
        sky=((70, 164, 230), (200, 236, 252)),
        far=((170, 214, 200), (122, 186, 150)),
        ground=(146, 96, 50), pebble=(124, 80, 40), pebble_hi=(160, 110, 62),
        top=(132, 200, 46), top_hi=(182, 232, 90), top_lo=(92, 156, 34),
        top_depth=0.34, water=(64, 156, 224), cave=(58, 40, 26),
        octaves=[(72, 11.0), (29, 6.5), (11, 1.8), (4.5, 0.25)],
        decor="clouds", props=("tree", "tree", "bush", "flowers", "fence", "rock"), cycle=True,
    ),
    dict(
        key="desert", name="Desert", seed=23,
        gravity=9.8, grip=0.92,
        sky=((232, 160, 84), (253, 232, 182)),
        far=((236, 196, 140), (214, 160, 100)),
        ground=(214, 162, 88), pebble=(192, 140, 72), pebble_hi=(232, 186, 112),
        top=(240, 204, 128), top_hi=(252, 228, 166), top_lo=(206, 160, 86),
        top_depth=0.30, water=None, cave=(96, 62, 34),
        octaves=[(95, 15.0), (36, 6.5), (13, 1.2), (5, 0.15)],
        decor="sun", props=("cactus", "cactus", "cactus2", "rock", "skull", "deadbush"), cycle=True,
    ),
    dict(
        key="arctic", name="Arctic", seed=37,
        gravity=9.8, grip=0.62,
        sky=((100, 150, 210), (222, 238, 250)),
        far=((216, 232, 246), (176, 202, 230)),
        ground=(120, 166, 206), pebble=(100, 146, 190), pebble_hi=(160, 200, 232),
        top=(244, 249, 255), top_hi=(255, 255, 255), top_lo=(196, 218, 238),
        top_depth=0.40, water=(150, 210, 240), cave=(40, 70, 104),
        octaves=[(64, 11.0), (24, 5.5), (9, 1.6), (4, 0.2)],
        decor="snow", props=("pine", "pine", "pine", "snowman", "rock", "crystal"), cycle=True,
    ),
    dict(
        key="moon", name="Moon", seed=53,
        gravity=3.4, grip=0.9,
        sky=((6, 8, 26), (34, 38, 82)),
        far=((70, 68, 96), (96, 94, 120)),
        ground=(146, 142, 160), pebble=(118, 114, 134), pebble_hi=(176, 172, 190),
        top=(198, 194, 210), top_hi=(226, 222, 236), top_lo=(150, 146, 164),
        top_depth=0.22, water=None, cave=(44, 42, 58),
        octaves=[(84, 8.0), (31, 3.8), (10, 1.2), (4, 0.2)],
        decor="space", props=("moonrock", "moonrock", "dish", "flag", "moonrock"), cycle=False, base_dark=0.35,
    ),
]
STAGES += [
    dict(
        key="city", name="City", seed=61,
        gravity=9.8, grip=1.02,
        sky=((96, 150, 214), (214, 226, 238)),
        far=((150, 168, 196), (110, 126, 156)),
        ground=(120, 112, 108), pebble=(104, 96, 92), pebble_hi=(150, 142, 136),
        top=(70, 72, 78), top_hi=(110, 112, 120), top_lo=(46, 46, 52),
        top_depth=0.36, water=(70, 120, 170), cave=(40, 40, 46),
        octaves=[(80, 7.0), (32, 3.6), (12, 0.6), (5, 0.08)],
        decor="city", props=("lamp", "lamp", "car", "hydrant", "cone", "bin", "sign"), cycle=True,
    ),
    dict(
        key="volcano", name="Volcano", seed=71,
        gravity=9.8, grip=0.95,
        sky=((60, 18, 20), (196, 80, 40)),
        far=((70, 34, 34), (48, 26, 28)),
        ground=(62, 52, 54), pebble=(48, 40, 42), pebble_hi=(150, 60, 30),
        top=(92, 82, 82), top_hi=(130, 118, 116), top_lo=(52, 44, 46),
        top_depth=0.28, water=(255, 110, 20), lava=True, cave=(36, 22, 20),
        octaves=[(70, 10.0), (26, 5.5), (10, 1.6), (4, 0.25)],
        decor="volcano", props=("deadtree", "lavarock", "vent", "lavarock", "skull"), cycle=False, base_dark=0.12,
    ),
    dict(
        key="jungle", name="Jungle", seed=81,
        gravity=9.8, grip=0.9,
        sky=((80, 150, 140), (200, 230, 200)),
        far=((90, 150, 110), (52, 118, 74)),
        ground=(96, 64, 40), pebble=(76, 50, 30), pebble_hi=(120, 86, 56),
        top=(56, 150, 50), top_hi=(110, 196, 70), top_lo=(30, 104, 36),
        top_depth=0.42, water=(70, 150, 140), cave=(30, 42, 24),
        octaves=[(66, 10.0), (25, 5.5), (10, 1.8), (4, 0.3)],
        decor="jungle", props=("palm", "palm", "fern", "bigflower", "mushroom", "fern", "rock"), cycle=True,
    ),
    dict(
        key="mars", name="Mars", seed=91,
        gravity=3.7, grip=0.85,
        sky=((196, 120, 90), (240, 196, 160)),
        far=((176, 96, 64), (150, 76, 50)),
        ground=(176, 86, 50), pebble=(150, 70, 40), pebble_hi=(210, 120, 80),
        top=(214, 130, 84), top_hi=(236, 164, 116), top_lo=(168, 92, 58),
        top_depth=0.24, water=None, cave=(80, 36, 24),
        octaves=[(88, 9.0), (32, 4.2), (11, 1.3), (4, 0.2)],
        decor="mars", props=("marsrock", "marsrock", "rover", "dish", "marsrock"), cycle=False, base_dark=0.0,
    ),
]
STAGE_BY_KEY = {s["key"]: s for s in STAGES}

# --------------------------------------------------------------- vehicles
# Geometry is in local metres (x forward, y up) relative to the chassis centre.
# wheels: (anchor x, anchor y, radius, mass, drive share)
VEHICLES = [
    dict(
        key="jeep", name="Jeep", tagline="Trusty all-rounder",
        mass=200, inertia=160, rest=0.42, ext=(0.17, 0.62),
        wheels=[(-1.02, -0.3, 0.46, 28, 0.8), (1.08, -0.3, 0.46, 28, 0.2)],
        torque=(760, 105), spin=(33, 3.4), spring=(15000, 1300), damping=(1500, 150),
        grip=0.95, air_torque=1500, thrust=(0, 0), boost=(2600, 200), fuel_rate=1.0,
        hull=[(-1.45, -0.14), (-1.2, -0.24), (1.2, -0.24), (1.48, -0.06),
              (1.4, 0.3), (-1.5, 0.36), (-0.95, 1.0), (-0.5, 1.0), (0.3, 0.92)],
        head=(-0.16, 1.1), head_r=0.27, exhaust=(-1.52, -0.16), nozzle=(-1.62, 0.12),
        engine=(1.0, 0.42), lights=[(1.47, 0.15)], tail=[(-1.6, 0.1)],
        rig="strut", sound="jeep", head_art="helmet", wheel_art=("knobby", "knobby"),
    ),
    dict(
        key="dirtbike", name="Dirt Bike", tagline="Light and flippy",
        mass=95, inertia=38, rest=0.4, ext=(0.15, 0.62),
        wheels=[(-0.68, -0.18, 0.38, 14, 1.0), (0.72, -0.18, 0.38, 12, 0.0)],
        torque=(330, 40), spin=(40, 3.5), spring=(7000, 600), damping=(650, 60),
        grip=1.0, air_torque=520, thrust=(0, 0), boost=(1300, 100), fuel_rate=0.8,
        hull=[(-0.95, -0.05), (0.95, 0.0), (0.45, 0.5), (-0.65, 0.4), (-0.3, 1.05), (0.3, 1.05)],
        head=(0.14, 1.32), head_r=0.2, exhaust=(-0.88, 0.1), nozzle=(-0.95, 0.3),
        engine=(0.0, 0.0), lights=[(0.62, 0.55)], tail=[(-1.08, 0.58)],
        rig="bike", fork_top=(0.5, 0.5), pivot=(-0.12, -0.06),
        sound="dirtbike", head_art="mx", wheel_art=("spoked", "spoked"),
    ),
    dict(
        key="chopper", name="Chopper", tagline="Long, low and loud",
        mass=170, inertia=120, rest=0.35, ext=(0.14, 0.55),
        wheels=[(-1.05, -0.15, 0.45, 18, 1.0), (1.25, -0.15, 0.38, 10, 0.0)],
        torque=(520, 62), spin=(32, 3.0), spring=(9000, 700), damping=(900, 80),
        grip=1.0, air_torque=700, thrust=(0, 0), boost=(1900, 140), fuel_rate=0.9,
        hull=[(-1.4, 0.05), (1.45, 0.1), (0.6, 0.6), (-0.2, 0.45), (-0.6, 1.15), (-0.95, 0.85)],
        head=(-0.32, 1.36), head_r=0.2, exhaust=(-1.48, -0.04), nozzle=(-1.4, 0.3),
        engine=(0.1, 0.15), lights=[(1.0, 0.62)], tail=[(-1.35, 0.25)],
        rig="bike", fork_top=(0.82, 0.68), pivot=(-0.3, -0.04),
        sound="chopper", head_art="biker", wheel_art=("whitewall", "spoked"),
    ),
    dict(
        key="monster", name="Monster Truck", tagline="Crushes every hill",
        mass=480, inertia=520, rest=0.62, ext=(0.25, 0.95),
        wheels=[(-1.35, -0.35, 0.82, 70, 0.5), (1.4, -0.35, 0.82, 70, 0.5)],
        torque=(2600, 330), spin=(20, 2.0), spring=(26000, 2000), damping=(3200, 250),
        grip=1.0, air_torque=3400, thrust=(0, 0), boost=(5400, 400), fuel_rate=1.25,
        hull=[(-2.0, 0.0), (2.0, 0.1), (2.0, 0.65), (0.75, 0.8), (0.5, 1.45), (-0.4, 1.45),
              (-2.0, 0.75), (-1.4, -0.2), (1.4, -0.2)],
        head=(0.08, 1.05), head_r=0.44, exhaust=(-0.5, 1.8), nozzle=(-2.1, 0.35),
        engine=(1.4, 0.9), lights=[(1.97, 0.62), (0.0, 1.52)], tail=[(-1.97, 0.78)],
        rig="strut", sound="monster", head_art="helmet_blue", wheel_art=("monster", "monster"),
        head_behind=True,
    ),
    dict(
        key="supercar", name="Supercar", tagline="Fast, but scrapes",
        mass=240, inertia=230, rest=0.26, ext=(0.12, 0.36),
        wheels=[(-1.25, 0.05, 0.36, 22, 1.0), (1.3, 0.05, 0.36, 22, 0.0)],
        torque=(820, 110), spin=(52, 5.0), spring=(30000, 2000), damping=(2600, 200),
        grip=1.05, air_torque=1300, thrust=(0, 0), boost=(3000, 230), fuel_rate=1.1,
        hull=[(-2.05, -0.1), (-1.9, -0.32), (1.9, -0.32), (2.08, -0.12), (1.0, 0.3),
              (0.1, 0.7), (-0.9, 0.62), (-2.0, 0.42)],
        head=(-0.18, 0.46), head_r=0.27, exhaust=(-2.08, -0.16), nozzle=(-2.1, 0.12),
        engine=(-1.3, 0.35), lights=[(1.86, 0.13)], tail=[(-2.03, 0.29)],
        rig="strut", sound="supercar", head_art="racer", wheel_art=("sport", "sport"),
        head_behind=True,
    ),
    dict(
        key="rocket", name="Rocket", tagline="Why drive? Fly!",
        mass=170, inertia=210, rest=0.3, ext=(0.12, 0.48),
        wheels=[(-0.95, -0.42, 0.3, 12, 1.0), (1.05, -0.42, 0.3, 12, 0.0)],
        torque=(260, 30), spin=(45, 4.0), spring=(12000, 900), damping=(1200, 100),
        grip=0.9, air_torque=1100, thrust=(1100, 120), boost=(3200, 240), fuel_rate=1.25,
        hull=[(2.25, 0.1), (1.6, 0.45), (1.6, -0.25), (-1.55, 0.5), (-1.55, -0.3),
              (-1.95, 0.9), (-1.95, -0.6), (0.6, 0.86)],
        head=(0.52, 0.6), head_r=0.24, exhaust=(-1.9, 0.1), nozzle=(-1.9, 0.1),
        engine=(-1.6, 0.1), lights=[(2.2, 0.1)], tail=[],
        rig="gear", sound="rocket", head_art="astro", wheel_art=("solid", "solid"),
        head_behind=True,
    ),
]
VEHICLES += [
    dict(
        key="tank", name="Tank", tagline="Slow. Heavy. Unstoppable.",
        mass=700, inertia=780, rest=0.3, ext=(0.12, 0.42),
        wheels=[(-1.35, -0.28, 0.42, 70, 0.5), (1.35, -0.28, 0.42, 70, 0.5)],
        torque=(3400, 380), spin=(19, 1.8), spring=(60000, 4000), damping=(7000, 500),
        grip=1.3, air_torque=4200, thrust=(0, 0), boost=(7200, 500), fuel_rate=1.4,
        hull=[(-2.0, -0.2), (2.05, -0.2), (2.0, 0.35), (-2.0, 0.35), (-1.0, 0.95), (0.9, 0.95), (2.9, 0.75),
              (-1.6, 0.6)],
        head=(-0.35, 1.35), head_r=0.27, exhaust=(-2.0, 0.3), nozzle=(-2.1, 0.2),
        engine=(-1.4, 0.45), lights=[(2.02, 0.18)], tail=[(-2.02, 0.2)],
        rig="tank", sound="tank", head_art="helmet_green", wheel_art=("sprocket", "sprocket"),
    ),
    dict(
        key="police", name="Police Car", tagline="Siren on the horn key",
        mass=250, inertia=240, rest=0.3, ext=(0.13, 0.42),
        wheels=[(-1.25, -0.12, 0.4, 24, 0.6), (1.3, -0.12, 0.4, 24, 0.4)],
        torque=(860, 110), spin=(44, 4.2), spring=(24000, 1800), damping=(2200, 180),
        grip=1.0, air_torque=1400, thrust=(0, 0), boost=(3000, 230), fuel_rate=1.1,
        hull=[(-2.05, -0.15), (-1.95, -0.35), (1.95, -0.35), (2.08, -0.12), (1.9, 0.35), (0.85, 0.42),
              (0.4, 0.95), (-0.9, 0.95), (-1.4, 0.45), (-2.05, 0.35)],
        head=(-0.15, 0.62), head_r=0.27, exhaust=(-2.08, -0.22), nozzle=(-2.1, 0.05),
        engine=(1.4, 0.3), lights=[(2.02, 0.15)], tail=[(-2.04, 0.18)], lightbar=[(-0.55, 1.04), (-0.1, 1.04)],
        rig="strut", sound="police", head_art="police", wheel_art=("sport", "sport"), head_behind=True,
    ),
    dict(
        key="hoverboard", name="Hoverboard", tagline="Glides, slides and flies",
        mass=70, inertia=30, rest=0.32, ext=(0.12, 0.5),
        wheels=[(-0.55, -0.1, 0.36, 14, 0.5), (0.55, -0.1, 0.36, 14, 0.5)],
        torque=(110, 14), spin=(46, 4.0), spring=(3600, 300), damping=(320, 30),
        grip=0.72, air_torque=360, thrust=(380, 40), boost=(1100, 90), fuel_rate=0.9,
        hull=[(-0.85, -0.05), (0.85, -0.05), (0.2, 1.0), (-0.2, 1.0), (0.0, 1.5)],
        head=(0.05, 1.78), head_r=0.2, exhaust=(-0.8, 0.0), nozzle=(-0.85, 0.02),
        engine=(0.0, 0.05), lights=[(0.85, 0.05)], tail=[(-0.85, 0.05)],
        rig="hover", sound="hover", head_art="helmet", wheel_art=("none", "none"),
    ),
]
VEHICLE_BY_KEY = {v["key"]: v for v in VEHICLES}

# --------------------------------------------------------------- upgrades
UPGRADES = [
    dict(key="engine", name="ENGINE", max=10, base=500, growth=1.62),
    dict(key="suspension", name="SUSPENSION", max=10, base=350, growth=1.58),
    dict(key="tires", name="TIRES", max=10, base=420, growth=1.6),
    dict(key="boost", name="BOOST", max=10, base=450, growth=1.6),
]


def upgrade_cost(upgrade, level):
    """Price of going from `level` to `level + 1`."""
    raw = upgrade["base"] * upgrade["growth"] ** (level - 1)
    return int(round(raw / 50.0)) * 50


def vehicle_stats(spec, levels):
    e, s, t, b = (levels.get(k, 1) - 1 for k in ("engine", "suspension", "tires", "boost"))

    def up(pair, lv):
        return pair[0] + pair[1] * lv
    return dict(
        torque=up(spec["torque"], e),
        max_spin=up(spec["spin"], e),
        thrust=up(spec["thrust"], e),
        spring=up(spec["spring"], s),
        damping=up(spec["damping"], s),
        grip=spec["grip"] + 0.075 * t,
        boost_force=up(spec["boost"], b),
        boost_seconds=2.0 + 0.35 * b,
    )


def rating(spec):
    """0..1 bars for the vehicle picker."""
    r = spec["wheels"][0][2]
    speed = spec["spin"][0] * r + spec["thrust"][0] / spec["mass"] * 0.9
    power = (spec["torque"][0] / r + spec["thrust"][0]) / (spec["mass"] * 9.8)
    return dict(
        SPEED=min(1.0, speed / 26),
        POWER=min(1.0, power / 1.1),
        GRIP=min(1.0, spec["grip"] / 1.1 * (0.7 + 0.3 * min(1, r / 0.6))),
        AIR=min(1.0, spec["air_torque"] / spec["inertia"] / 14),
    )


# ---------------------------------------------------------------- scoring
def coin_value_at(x):
    if x < 500:
        return 5
    if x < 1200:
        return 25
    if x < 2500:
        return 100
    return 500


# ---------------------------------------------------------- events/online
SEIZE_RATE = 1 / 55        # chance per second of full throttle that the engine seizes
SEIZE_GRACE = 12.0         # no seizure in the first seconds, nor right after a repair
RACE_DISTANCES = [500, 1000, 2000]
DAY_LENGTH = 210.0         # seconds for a full day/night cycle

FLIP_BONUS = 1000
NECK_FLIP_BONUS = 2500
