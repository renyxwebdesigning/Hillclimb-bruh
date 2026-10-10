"""Story mode: climb the Blacklist, the ten most wanted street racers in the world.

You arrive in Zurich with a rusty old hatchback. In every city there are three events
(a street race, a time trial and a police pursuit) that pay cash; finish all three and
the city's Blacklist racer will race you. Beat them and their car is yours. Cash buys
upgrades (each car has its own), and every rival is quicker than the last, so you have
to keep upgrading to move up: #10 in Zurich to #1 in Abu Dhabi.

Like Need for Speed: Most Wanted, the loop is earn -> upgrade -> beat the next rival
-> win a better car -> do it all again in the next city.
"""
import math

from config import GRAVITY_SCALE, PHYS_DT, STAGE_BY_KEY, UPGRADES, VEHICLE_BY_KEY, upgrade_cost, vehicle_stats
from physics import Vehicle

# ------------------------------------------------------------------ the cars
# Outline points (local metres: x forward, y up, chassis centre at 0, 0) are used for the
# drawing and the collision hull alike. cls 0 is the starter, cls 10 the best car in the game.
CAR_SHAPES = {
    "rusty": dict(name="Rusty Corsa", cls=0, color=(168, 74, 62), wheels=(-1.2, 1.2), r=0.31, wheel_art="truck",
                  pts=[(-1.85, -0.3), (-1.88, 0.45), (-1.7, 0.86), (-0.4, 0.9), (0.2, 0.86), (0.75, 0.5), (1.65, 0.4),
                       (1.85, 0.2), (1.88, -0.15), (1.75, -0.32)],
                  glass=[(-1.6, 0.5), (-1.52, 0.82), (-0.42, 0.85), (0.18, 0.82), (0.62, 0.5)],
                  extras=("rust",), sound="rusty", rear=0.0, smooth=False),
    "audi_tt": dict(name="Audi TT", cls=1, color=(40, 72, 150), wheels=(-1.28, 1.3), r=0.33, wheel_art="aero",
                    pts=[(-2.0, -0.28), (-2.02, 0.3), (-1.75, 0.55), (-1.1, 0.86), (-0.3, 0.95), (0.35, 0.86), (0.95, 0.5),
                         (1.7, 0.36), (2.0, 0.15), (2.02, -0.15), (1.85, -0.32)],
                    glass=[(-1.3, 0.58), (-0.95, 0.82), (-0.3, 0.9), (0.3, 0.82), (0.8, 0.52)],
                    extras=("fuelcap",), sound="mini", rear=0.5),
    "mustang": dict(name="Ford Mustang GT", cls=2, color=(28, 48, 120), wheels=(-1.42, 1.45), r=0.35, wheel_art="sport",
                    pts=[(-2.25, -0.3), (-2.28, 0.35), (-2.15, 0.52), (-1.6, 0.6), (-0.9, 0.92), (-0.2, 0.95), (0.35, 0.62),
                         (2.0, 0.48), (2.28, 0.3), (2.3, -0.15), (2.1, -0.32)],
                    glass=[(-1.55, 0.62), (-0.9, 0.88), (-0.25, 0.9), (0.28, 0.62)],
                    extras=("stripes", "scoop"), sound="monster", rear=1.0),
    "skyline": dict(name="Nissan Skyline GT-R", cls=3, color=(36, 92, 200), wheels=(-1.4, 1.42), r=0.35,
                    wheel_art="sport",
                    pts=[(-2.25, -0.3), (-2.28, 0.42), (-2.0, 0.5), (-1.4, 0.55), (-0.9, 0.92), (0.1, 0.94), (0.6, 0.6),
                         (2.05, 0.46), (2.28, 0.3), (2.3, -0.15), (2.1, -0.32)],
                    glass=[(-1.3, 0.58), (-0.85, 0.88), (0.08, 0.9), (0.52, 0.6)],
                    extras=("wing", "roundtail"), sound="supercar", rear=0.5, smooth=False),
    "m3gtr": dict(name="BMW M3 GTR", cls=4, color=(200, 204, 212), wheels=(-1.38, 1.4), r=0.35, wheel_art="sport",
                  pts=[(-2.22, -0.32), (-2.25, 0.4), (-2.0, 0.5), (-1.35, 0.56), (-0.85, 0.9), (0.05, 0.93), (0.55, 0.58),
                       (1.9, 0.44), (2.22, 0.25), (2.25, -0.18), (2.05, -0.34)],
                  glass=[(-1.25, 0.58), (-0.82, 0.86), (0.03, 0.89), (0.48, 0.58)],
                  extras=("livery", "wing", "kidney"), sound="supercar", rear=1.0),
    "db9": dict(name="Aston Martin DB9", cls=5, color=(22, 76, 54), wheels=(-1.45, 1.5), r=0.36, wheel_art="sport",
                pts=[(-2.3, -0.3), (-2.32, 0.3), (-2.1, 0.5), (-1.5, 0.58), (-0.8, 0.86), (0.0, 0.88), (0.6, 0.56),
                     (2.0, 0.4), (2.32, 0.18), (2.34, -0.15), (2.15, -0.32)],
                glass=[(-1.4, 0.6), (-0.8, 0.83), (-0.02, 0.85), (0.52, 0.56)],
                extras=("vent",), sound="supercar", rear=1.0),
    "corvette": dict(name="Chevrolet Corvette", cls=6, color=(250, 196, 20), wheels=(-1.4, 1.45), r=0.36,
                     wheel_art="sport",
                     pts=[(-2.2, -0.28), (-2.22, 0.35), (-2.05, 0.5), (-1.3, 0.55), (-0.7, 0.8), (0.05, 0.82),
                          (0.55, 0.5), (2.05, 0.32), (2.25, 0.12), (2.26, -0.15), (2.05, -0.3)],
                     glass=[(-1.2, 0.57), (-0.7, 0.77), (0.03, 0.79), (0.48, 0.5)],
                     extras=("vent",), sound="monster", rear=1.0),
    "gt2": dict(name="Porsche 911 GT2", cls=7, color=(238, 238, 232), wheels=(-1.32, 1.3), r=0.35, wheel_art="sport",
                pts=[(-2.15, -0.3), (-2.2, 0.25), (-1.95, 0.55), (-1.1, 0.88), (-0.35, 0.95), (0.2, 0.86), (0.7, 0.5),
                     (1.7, 0.36), (2.05, 0.2), (2.1, -0.12), (1.9, -0.32)],
                glass=[(-1.0, 0.62), (-0.35, 0.9), (0.18, 0.82), (0.6, 0.5)],
                extras=("wing", "frogeye"), sound="supercar", rear=1.0),
    "slr": dict(name="Mercedes SLR McLaren", cls=8, color=(192, 198, 206), wheels=(-1.45, 1.55), r=0.36,
                wheel_art="aero",
                pts=[(-2.32, -0.3), (-2.34, 0.35), (-2.15, 0.52), (-1.55, 0.58), (-1.05, 0.85), (-0.35, 0.88),
                     (0.15, 0.55), (1.9, 0.45), (2.32, 0.22), (2.34, -0.12), (2.1, -0.32)],
                glass=[(-1.45, 0.6), (-1.02, 0.82), (-0.37, 0.85), (0.1, 0.55)],
                extras=("gills", "sidepipe"), sound="supercar", rear=1.0),
    "murcielago": dict(name="Lamborghini Murcielago", cls=9, color=(255, 124, 10), wheels=(-1.42, 1.45), r=0.36,
                       wheel_art="sport",
                       pts=[(-2.3, -0.3), (-2.32, 0.38), (-2.0, 0.5), (-0.8, 0.8), (-0.3, 0.82), (0.45, 0.62),
                            (2.2, 0.16), (2.32, 0.02), (2.3, -0.15), (2.1, -0.32)],
                       glass=[(-0.95, 0.62), (-0.75, 0.78), (-0.3, 0.8), (0.4, 0.6)],
                       extras=("scoopside", "wedge"), sound="supercar", rear=0.6, smooth=False),
    "enzo": dict(name="Ferrari Enzo", cls=10, color=(222, 22, 22), wheels=(-1.45, 1.5), r=0.36, wheel_art="sport",
                 pts=[(-2.35, -0.3), (-2.37, 0.42), (-2.1, 0.48), (-0.9, 0.7), (-0.35, 0.85), (0.25, 0.82), (0.7, 0.5),
                      (1.6, 0.34), (2.2, 0.12), (2.37, -0.02), (2.36, -0.18), (2.1, -0.32)],
                 glass=[(-0.85, 0.68), (-0.35, 0.82), (0.22, 0.8), (0.62, 0.5)],
                 extras=("intake", "fnose"), sound="supercar", rear=1.0),
}


def _spec(key, d):
    """Physics numbers from the car's class: every class is about four upgrade levels better."""
    c = d["cls"]
    pts = d["pts"]
    xs = [x for x, _ in pts]
    gx = sum(x for x, _ in d["glass"]) / len(d["glass"])
    roof = max(y for _, y in d["glass"])
    mass = 190 + 7 * c
    torque = 560 * 1.15 ** c
    spin = 34 * 1.05 ** c * 0.34 / d["r"]        # later cars gain mostly power and grip: too fast and they only fly
    rear = d["rear"]
    shares = (1.0, 0.0) if rear >= 1.0 else (0.0, 1.0) if rear <= 0.0 else (rear, 1.0 - rear)
    return dict(
        key=key, name=d["name"], tagline=f"Blacklist car · class {c}" if c else "Your first car. It rattles.",
        mass=mass, inertia=mass * 0.82, rest=0.27, ext=(0.11, 0.4),
        wheels=[(d["wheels"][0], -0.04, d["r"], 18, shares[0]), (d["wheels"][1], -0.04, d["r"], 18, shares[1])],
        torque=(torque, 0.06 * torque), spin=(spin, 0.025 * spin), spring=(16000 + 1500 * c, 1300),
        damping=(1600 + 120 * c, 120), grip=0.97 + 0.02 * c, air_torque=1100 + 40 * c, thrust=(0, 0),
        boost=(2300 * 1.1 ** c, 0.08 * 2300 * 1.1 ** c), fuel_rate=1.0,
        hull=list(pts), head=(gx - 0.1, roof - 0.37), head_r=0.27,
        exhaust=(min(xs) + 0.05, -0.2), nozzle=(min(xs) - 0.05, 0.05), engine=(max(xs) - 0.8, 0.2),
        lights=[(max(xs) - 0.06, 0.2)], tail=[(min(xs) + 0.04, 0.35)], wing=None,
        rig="strut", sound=d["sound"], head_art="helmet", wheel_art=(d["wheel_art"],) * 2, head_behind=True,
        story=True, cls=c, has_wing="wing" in d["extras"],
    )


STORY_CARS = [_spec(k, d) for k, d in CAR_SHAPES.items()]
for _s in STORY_CARS:
    if _s["wing"] is None:
        del _s["wing"]
    VEHICLE_BY_KEY[_s["key"]] = _s           # drawable and drivable everywhere, but only picked in story mode
CAR_BY_KEY = {s["key"]: s for s in STORY_CARS}

# ------------------------------------------------------------------ cities
_BASE = STAGE_BY_KEY["city"]


def _city(key, name, seed, sky, far, octaves, landmark, props, night=False, ground=None, top=None):
    st = dict(_BASE)
    st.update(key=key, name=name, seed=seed, sky=sky, far=far, octaves=octaves, landmarks=(landmark,), props=props,
              obstacles=("oil", "speedbump", "speedbump"), cycle=False, base_dark=0.5 if night else 0.0,
              decor="citynight" if night else "city", street=True)
    if ground:
        st["ground"], st["pebble"], st["pebble_hi"] = ground, tuple(max(0, v - 18) for v in ground), \
            tuple(min(255, v + 26) for v in ground)
    if top:
        st["top"], st["top_hi"], st["top_lo"] = top, tuple(min(255, v + 36) for v in top), \
            tuple(max(0, v - 24) for v in top)
    STAGE_BY_KEY[key] = st
    return st


CITY_PROPS = ("lamp", "lamp", "car", "hydrant", "bin", "sign", "bench", "trafficlight")
PALM_PROPS = ("palm", "lamp", "palm", "car", "bench", "sign", "lamp")

# rank, city, rival (name, nickname), rival's car, lines, race length, event lengths and the stage
CITIES = [
    dict(rank=10, key="zurich", name="Zurich", rival="Lukas Meier", nick="Clockwork", car="audi_tt",
         intro="Swiss precision, my friend. Your rust bucket won't even make it out of the old town.",
         lose="Not bad... for a pile of scrap. Take the TT, you earned it.",
         race=700, events=(450, 400, 450),
         stage=_city("story_zurich", "Zurich", 201, ((110, 170, 230), (220, 236, 250)), ((190, 210, 230), (150, 176, 206)),
                     [(80, 8.0), (30, 4.0), (12, 0.8), (5, 0.08)], "grossmuenster", CITY_PROPS + ("tree",))),
    dict(rank=9, key="sanfrancisco", name="San Francisco", rival="Jack Harlan", nick="Fog", car="mustang",
         intro="These hills eat little cars for breakfast. Try to keep up in the fog.",
         lose="You came out of nowhere. The Mustang's yours. Don't scratch it.",
         race=850, events=(550, 500, 550),
         stage=_city("story_sanfrancisco", "San Francisco", 202, ((150, 176, 200), (226, 232, 238)),
                     ((176, 186, 196), (140, 150, 166)), [(70, 13.0), (28, 6.0), (12, 1.0), (5, 0.1)], "goldengate",
                     CITY_PROPS)),
    dict(rank=8, key="tokyo", name="Tokyo", rival="Kenji Mori", nick="Drift King", car="skyline",
         intro="Under the neon, the GT-R rules. You are just a tourist here.",
         lose="Sugoi... The Skyline belongs to you now. Treat her with respect.",
         race=1000, events=(600, 550, 600),
         stage=_city("story_tokyo", "Tokyo", 203, ((20, 14, 52), (90, 40, 110)), ((60, 40, 100), (40, 26, 70)),
                     [(80, 9.0), (30, 4.4), (12, 0.8), (5, 0.08)], "tokyotower", CITY_PROPS, night=True)),
    dict(rank=7, key="paris", name="Paris", rival="Elodie Moreau", nick="Le Fantome", car="m3gtr",
         intro="You will never see me. Just my tail lights, and then nothing.",
         lose="Incroyable. The GTR is yours... au revoir.",
         race=1100, events=(650, 600, 650),
         stage=_city("story_paris", "Paris", 204, ((240, 160, 120), (252, 226, 196)), ((200, 160, 150), (160, 120, 120)),
                     [(80, 9.5), (30, 4.6), (12, 0.8), (5, 0.08)], "eiffel", CITY_PROPS + ("tree",))),
    dict(rank=6, key="london", name="London", rival="Oliver Hayes", nick="Bulldog", car="db9",
         intro="Rain, roundabouts and me. Nobody gets past the Bulldog in my town.",
         lose="Bloody hell. Fine, take the Aston. Keys are in the ignition.",
         race=1250, events=(700, 650, 700),
         stage=_city("story_london", "London", 205, ((130, 140, 156), (200, 206, 214)), ((150, 156, 166), (116, 122, 134)),
                     [(80, 10.0), (30, 4.8), (12, 0.9), (5, 0.08)], "bigben", CITY_PROPS + ("tree",))),
    dict(rank=5, key="lasvegas", name="Las Vegas", rival="Vinnie Russo", nick="Jackpot", car="corvette",
         intro="The house always wins, kid. And tonight I'm the house.",
         lose="Snake eyes. The Vette's yours... don't spend it all in one place.",
         race=1400, events=(750, 700, 750),
         stage=_city("story_lasvegas", "Las Vegas", 206, ((26, 10, 46), (120, 50, 90)), ((110, 70, 70), (80, 50, 56)),
                     [(90, 9.5), (34, 4.4), (12, 0.8), (5, 0.08)], "vegassign", PALM_PROPS, night=True,
                     ground=(170, 120, 80))),
    dict(rank=4, key="monaco", name="Monaco", rival="Marco Castellane", nick="Royale", car="gt2",
         intro="Tunnels, hairpins, the harbour. This is where legends are made. Not you.",
         lose="Magnifique. The GT2 is yours. The Principality salutes you.",
         race=1550, events=(800, 750, 800),
         stage=_city("story_monaco", "Monaco", 207, ((60, 150, 230), (200, 232, 252)), ((170, 200, 210), (120, 160, 180)),
                     [(80, 10.0), (30, 4.6), (12, 0.9), (5, 0.08)], "casino", PALM_PROPS)),
    dict(rank=3, key="hongkong", name="Hong Kong", rival="Wei Chen", nick="Dragon", car="slr",
         intro="The dragon never sleeps. Neither do the streets of Hong Kong.",
         lose="The dragon bows. The SLR is yours. Two left above you.",
         race=1700, events=(850, 800, 850),
         stage=_city("story_hongkong", "Hong Kong", 208, ((10, 20, 50), (40, 70, 120)), ((40, 60, 100), (26, 40, 70)),
                     [(85, 10.0), (32, 4.6), (12, 0.9), (5, 0.08)], "hktower", CITY_PROPS, night=True)),
    dict(rank=2, key="miami", name="Miami", rival="Carlos Mendez", nick="Vice", car="murcielago",
         intro="Ocean Drive is my runway. You're about to see what a Lambo really does.",
         lose="No way... OK, the Murcielago is yours. Only Mirage is left.",
         race=1850, events=(900, 850, 900),
         stage=_city("story_miami", "Miami", 209, ((250, 120, 150), (255, 210, 160)), ((240, 150, 170), (200, 110, 150)),
                     [(95, 9.0), (34, 4.2), (12, 0.8), (5, 0.08)], "artdeco", PALM_PROPS, ground=(200, 170, 130))),
    dict(rank=1, key="abudhabi", name="Abu Dhabi", rival="Khalid Al Sayed", nick="Mirage", car="enzo",
         intro="So you made it to the top. Everyone sees the Mirage. Nobody catches it.",
         lose="Impossible... The Enzo is yours. You are number one on the Blacklist.",
         race=2000, events=(950, 900, 950),
         stage=_city("story_abudhabi", "Abu Dhabi", 210, ((120, 176, 230), (250, 230, 190)), ((230, 200, 150), (200, 160, 110)),
                     [(100, 10.0), (36, 4.6), (13, 0.9), (5, 0.08)], "mosque", PALM_PROPS, ground=(214, 170, 110))),
]
CITY_BY_KEY = {c["key"]: c for c in CITIES}

STREET_RACERS = ("Nina 'Spark' Vogel", "Tommy 'Two-Step' Reyes", "Ayumi 'Kitsune' Sato", "Hugo 'Turbo' Lambert",
                 "Priya 'Nitro' Shah", "Dex 'Redline' Cole", "Mila 'Ghost' Novak", "Sam 'Slick' Okoye",
                 "Jules 'Comet' Bernard", "Omar 'Falcon' Haddad")

INTRO = ("Mirage, number one on the Blacklist, beat you in a rigged race and took everything. "
         "All you have left is a rusty old Corsa. The Blacklist: the ten most wanted street racers "
         "in the world, one in every big city. Earn cash in street races, time trials and police chases, "
         "upgrade your car, beat each racer and take their car. Start at number 10 in Zurich. "
         "End at number 1 in Abu Dhabi.")

EVENT_KINDS = ("sprint", "trial", "pursuit")
EVENT_TITLES = {"sprint": "STREET RACE", "trial": "TIME TRIAL", "pursuit": "POLICE CHASE", "rival": "BLACKLIST RACE"}
EVENT_INFO = {"sprint": "Beat a street racer to the finish", "trial": "Reach the finish before the clock runs out",
              "pursuit": "Outrun the cops: don't let them box you in", "rival": "Win, and their car is yours"}

RIVAL_LEVEL = 2              # the rival's own upgrades on their car (every upgrade at this level)


# ------------------------------------------------------------------ economy
def pay(city_i, kind, first):
    """Cash for an event in city number city_i (0 = Zurich): grows with the cities, like the upgrade prices."""
    base = {"sprint": 1800, "trial": 1500, "pursuit": 2400, "rival": 6000}[kind]
    amount = base * 1.35 ** city_i
    if not first:
        amount *= 0.75                       # replays pay a bit less
    return int(round(amount / 50.0)) * 50


def price(spec, upgrade, level):
    """Upgrade prices grow with the car's class: a Ferrari costs more to tune than a Corsa."""
    return int(round(upgrade_cost(upgrade, level) * 0.5 * 1.35 ** spec["cls"] / 50.0)) * 50


def rating(spec, levels):
    """One number for how quick a car is (bars in the menus): power, top speed, grip and boost."""
    st = vehicle_stats(spec, levels)
    r = spec["wheels"][0][2]
    power = st["torque"] / (spec["mass"] * r * GRAVITY_SCALE)
    speed = st["max_spin"] * r
    return power * 0.35 + speed * 0.9 + st["grip"] * 6 + st["boost_force"] / spec["mass"] * 0.25


def rival_levels():
    return {u["key"]: (RIVAL_LEVEL if u["key"] != "turbo" else 1) for u in UPGRADES}


# ------------------------------------------------------------------ progress
def default_state():
    return dict(cash=0, car="rusty", cars={"rusty": {u["key"]: 1 for u in UPGRADES}}, beaten=0, events={},
                intro_seen=False)


def state(data):
    """The story part of the save, created on first use and repaired if it is incomplete."""
    st = data.get("story")
    if not isinstance(st, dict):
        st = data["story"] = default_state()
    for k, v in default_state().items():
        st.setdefault(k, v)
    for key, lv in list(st["cars"].items()):
        if key not in CAR_BY_KEY:
            del st["cars"][key]
            continue
        for u in UPGRADES:
            lv.setdefault(u["key"], 1)
    if st["car"] not in st["cars"]:
        st["car"] = next(iter(st["cars"]), "rusty")
        st["cars"].setdefault("rusty", {u["key"]: 1 for u in UPGRADES})
    st["beaten"] = max(0, min(len(CITIES), int(st["beaten"])))
    return st


def current_city(st):
    """The city you are working on (the last one once the Blacklist is beaten)."""
    return CITIES[min(st["beaten"], len(CITIES) - 1)]


def city_index(city):
    return CITIES.index(city)


def events_done(st, city):
    return st["events"].get(city["key"], [False, False, False])


def rival_unlocked(st, city):
    return all(events_done(st, city))


def event(city, kind):
    """Settings for one event in a city: length, opponents, time limit."""
    i = city_index(city)
    if kind == "rival":
        return dict(kind="rival", distance=city["race"])
    length = city["events"][EVENT_KINDS.index(kind)]
    ev = dict(kind=kind, distance=length)
    if kind == "trial":
        ev["limit"] = trial_limit(i, length)
    return ev


# Time limits for the trials, from simulated runs: the AI in your car, still stock, over each city's trial
# (seconds), plus 25 % and two seconds for being human.
TRIAL_STOCK = (28.7, 26.6, 41.4, 40.2, 41.7, 35.3, 44.4, 40.1, 49.3, 45.3)


def trial_limit(i, length):
    return round(TRIAL_STOCK[i] * 1.25 + 2.0)


# ------------------------------------------------------------------ AI drivers
class AIDriver:
    """A computer driver: keeps its wheels down, leans in the air, boosts up hills.

    It never touches the player (like online racers), respawns a little back after a crash,
    and has a soft rubber band so a race stays a race.
    """
    DT = PHYS_DT                     # the same step as the player: coarser steps blow up the powerful cars

    def __init__(self, terrain, stage, spec, levels, name, color, x, role="racer", band=(0.9, 1.1), power=1.0):
        """band: engine power when far ahead of / far behind the player; power: overall strength."""
        self.terrain, self.stage, self.spec = terrain, stage, spec
        self.name, self.color, self.role, self.band = name, color, role, band
        self.stats = vehicle_stats(spec, levels)
        self.base_torque = self.stats["torque"] * power
        self.lift = max(spec["rest"] + w[2] - w[1] for w in spec["wheels"]) + 0.05
        self.car = Vehicle(x, terrain.height(x) + self.lift, spec, self.stats)
        self.tank = 1.0
        self.cans = sorted(n[0] for n in terrain.nitro)
        self._can = 0
        self._acc = 0.0
        self.respawn_t = None
        self.finished_at = None
        self.flip_t = 0.0
        self.lights = stage.get("base_dark", 0) > 0.3

    @property
    def x(self):
        return self.car.x

    def update(self, dt, player_x, time):
        t, car = self.terrain, self.car
        if self.respawn_t is not None:
            self.respawn_t -= dt
            if self.respawn_t <= 0:
                self._respawn()
            return
        gap = player_x - car.x                      # > 0: the player is ahead
        lo, hi = self.band
        self.stats["torque"] = self.base_torque * (hi if gap > 30 else lo if gap < -60 else 1.0)
        slope = math.atan2(t.height(car.x + 1.5) - t.height(car.x - 1.5), 3.0)
        err = car.angle - slope
        if car.grounded:
            gas, brake = err < 0.75, False
        else:
            gas, brake = err < -0.15, err > 0.25
        while self._can < len(self.cans) and car.x > self.cans[self._can]:
            self.tank, self._can = 1.0, self._can + 1
        boost = car.grounded and self.tank > 0 and abs(err) < 0.4 and (slope > 0.2 or gap > 25)
        if boost:
            self.tank -= dt / self.stats["boost_seconds"]
        grip, drag = self.stage["grip"], 0.0
        zone = t.zone_at(car.x)
        if zone:
            mul, drag = t.ZONES[zone]
            grip *= mul
        self._acc += dt
        steps = 0
        g = self.stage["gravity"] * GRAVITY_SCALE
        while self._acc >= self.DT and steps < 40:
            car.step(self.DT, gas, brake, boost, t, g, grip, drag, self.stage.get("water_drag", 0.0))
            self._acc -= self.DT
            steps += 1
        car.boosting = boost
        resting = math.cos(car.angle) < -0.2 and math.hypot(car.vx, car.vy) < 1.0
        self.flip_t = self.flip_t + dt if resting else 0.0
        bad = not (math.isfinite(car.x) and math.isfinite(car.y) and abs(car.vx) + abs(car.vy) < 400)
        if car.head_hit or self.flip_t > 1.5 or bad:
            self.respawn_t = 1.2

    def _respawn(self):
        self.respawn_t = None
        self.flip_t = 0.0
        x = self.car.x - 2.0 if math.isfinite(self.car.x) else 2.0
        self.car = Vehicle(x, self.terrain.height(x) + self.lift + 0.2, self.spec, self.stats)


def make_opponents(terrain, stage, city, ev, player_x):
    """The AI cars for an event: a street racer, the Blacklist rival, or two police cars."""
    i = city_index(city)
    kind = ev["kind"]
    if kind == "rival":
        spec = CAR_BY_KEY[city["car"]]
        return [AIDriver(terrain, stage, spec, rival_levels(), f"#{city['rank']} {city['nick'].upper()}",
                         (255, 200, 40), player_x, "rival", band=(0.95, 1.05), power=0.96)]
    if kind == "sprint":
        # a street racer in the same kind of car you are driving now: beatable with the stock car,
        # and it eases off when it gets far ahead
        prev = CAR_BY_KEY[CITIES[i - 1]["car"]] if i > 0 else CAR_BY_KEY["rusty"]
        name = STREET_RACERS[i % len(STREET_RACERS)]
        return [AIDriver(terrain, stage, prev, {u["key"]: 1 for u in UPGRADES},
                         name.split("'")[1].upper() if "'" in name else name, (120, 220, 255), player_x, "racer",
                         band=(0.8, 1.0), power=0.88)]
    if kind == "pursuit":
        cop = VEHICLE_BY_KEY["police"]
        lv = min(10, 3 + i)
        levels = {u["key"]: (lv if u["key"] != "turbo" else 1 + i // 3) for u in UPGRADES}
        return [AIDriver(terrain, stage, cop, levels, "POLICE", (80, 140, 255), player_x - 22, "cop", band=(1.0, 1.4),
                         power=1.1),
                AIDriver(terrain, stage, cop, levels, "POLICE", (80, 140, 255), player_x - 34, "cop", band=(1.0, 1.45),
                         power=1.1)]
    return []

