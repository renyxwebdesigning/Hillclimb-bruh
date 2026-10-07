"""Long-term progress: achievements, secret trophies, daily challenges and stats."""
import datetime
import random

from config import STAGES, VEHICLES

TROPHY_DISTANCES = [380, 900, 1600, 2500, 4000]
TROPHY_REWARD = 500

# key, title, description, reward, (stat, target)
ACHIEVEMENTS = [
    ("first_ride", "First Ride", "Finish your first run", 200, ("runs", 1)),
    ("flipper", "Flipper", "Do a flip", 500, ("flips_total", 1)),
    ("acrobat", "Acrobat", "10 flips in one run", 4000, ("best_flips", 10)),
    ("flyer", "Frequent Flyer", "5 seconds of air time in one jump", 2500, ("best_air", 5)),
    ("marathon", "Marathon", "Drive 1000 m in one run", 2000, ("best_distance", 1000)),
    ("explorer", "Explorer", "Drive 3000 m in one run", 8000, ("best_distance", 3000)),
    ("treasure", "Treasure Hunter", "Find 5 secret trophies", 3000, ("trophies", 5)),
    ("trophy_master", "Trophy Master", "Find all 40 secret trophies", 25000, ("trophies", 40)),
    ("mechanic", "Mechanic", "Fix 5 seized engines", 1500, ("fixes", 5)),
    ("moonwalker", "Moon Walker", "Drive 500 m on the Moon", 2000, ("moon_best", 500)),
    ("lava_jumper", "Lava Jumper", "Jump 5 lava pits in one run", 5000, ("best_pits", 5)),
    ("rich", "Rich", "Earn 50,000 coins in total", 5000, ("coins_earned", 50000)),
    ("collector", "Collector", "Drive every vehicle", 6000, ("vehicles_used", len(VEHICLES))),
    ("social", "Social Driver", "Play an online race", 1500, ("online_races", 1)),
    ("champion", "Champion", "Win an online race", 5000, ("online_wins", 1)),
    ("night_rider", "Night Rider", "Drive 500 m at night", 2000, ("night_best", 500)),
]
ACH_BY_KEY = {a[0]: a for a in ACHIEVEMENTS}


def defaults():
    return {"stats": {}, "achievements": [], "trophies": {}, "daily_done": ""}


def stat(data, key):
    v = data["stats"].get(key, 0)
    return len(v) if isinstance(v, list) else v


def place_trophies(terrain, rng):
    """Five hard-to-reach trophies per stage: high above hills, over lava pits, in tunnels."""
    out = []
    for i, d in enumerate(TROPHY_DISTANCES):
        x = d + rng.uniform(-40, 40)
        where = terrain.feature_at(x, 2.0)
        pit = next(((a, b, lv) for a, b, lv in terrain.pits if abs((a + b) / 2 - x) < 120), None)
        if pit:
            x = (pit[0] + pit[1]) / 2
            y = terrain.height(pit[0]) + 1.6
        elif where == "tunnel" and terrain.ceiling(x) is not None:
            y = terrain.ceiling(x) - 0.7
        else:
            y = terrain.height(x) + rng.uniform(2.6, 3.6)
        out.append([x, y, i, False])
    return out


class Progress:
    def __init__(self, app):
        self.app = app
        data = app.data
        for k, v in defaults().items():
            data.setdefault(k, v)

    # ------------------------------------------------------------ helpers
    @property
    def data(self):
        return self.app.data

    def _bump(self, key, amount=1):
        self.data["stats"][key] = self.data["stats"].get(key, 0) + amount

    def _max(self, key, value):
        if value > self.data["stats"].get(key, 0):
            self.data["stats"][key] = value

    def trophies_found(self, stage_key=None):
        t = self.data["trophies"]
        if stage_key:
            return len(t.get(stage_key, []))
        return sum(len(v) for v in t.values())

    def has_trophy(self, stage_key, i):
        return i in self.data["trophies"].get(stage_key, [])

    # -------------------------------------------------------------- events
    def trophy(self, run, i):
        found = self.data["trophies"].setdefault(run.stage["key"], [])
        if i in found:
            return
        found.append(i)
        self.data["stats"]["trophies"] = self.trophies_found()
        run.coins += TROPHY_REWARD
        run.hud.toast("SECRET TROPHY!", f"{len(found)}/5 on {run.stage['name']}  ·  +{TROPHY_REWARD}")
        run.audio.play("finish")
        self.check(run)
        self.app.persist()

    def fixed(self, run):
        self._bump("fixes")
        self.check(run)

    def live(self, run):
        """Called a few times a second during a run."""
        self._max("best_flips", run.flips)
        self._max("best_air", round(run.max_air, 1))
        self._max("best_distance", run.distance)
        self._max("best_pits", run.pits_cleared)
        self._max("night_best", int(run.night_m))
        if run.stage["key"] == "moon":
            self._max("moon_best", run.distance)
        self.check(run)

    def run_over(self, run):
        self._bump("runs")
        self._bump("flips_total", run.flips)
        self._bump("coins_earned", run.coins)
        used = self.data["stats"].setdefault("vehicles_used", [])
        if run.spec["key"] not in used:
            used.append(run.spec["key"])
        self.live(run)
        self.daily_check(run)

    def online_race(self, won):
        self._bump("online_races")
        if won:
            self._bump("online_wins")
        self.check(None)

    def check(self, run):
        for key, title, desc, reward, (st, target) in ACHIEVEMENTS:
            if key in self.data["achievements"] or stat(self.data, st) < target:
                continue
            self.data["achievements"].append(key)
            self.data["coins"] += reward
            hud = run.hud if run else self.app.hud
            hud.toast(f"ACHIEVEMENT: {title.upper()}", f"{desc}  ·  +{reward:,} coins")
            self.app.audio.play("bonus")

    # ------------------------------------------------------- daily challenge
    def daily(self):
        today = datetime.date.today()
        rng = random.Random(today.toordinal() * 7919)
        stage = rng.choice(STAGES)
        vehicle = rng.choice(VEHICLES)
        kind = rng.choice(["distance", "distance", "flips", "coins", "air"])
        if kind == "distance":
            target = rng.choice([400, 600, 800, 1000])
            text = f"Drive {target} m"
        elif kind == "flips":
            target = rng.choice([2, 3, 5])
            text = f"Do {target} flips"
        elif kind == "coins":
            target = rng.choice([300, 600, 1000])
            text = f"Collect {target} coins"
        else:
            target = rng.choice([2, 3, 4])
            text = f"{target} s of air time in one jump"
        reward = {"distance": 1500, "flips": 2500, "coins": 2000, "air": 2500}[kind]
        return dict(date=today.isoformat(), stage=stage, vehicle=vehicle, kind=kind, target=target,
                    text=f"{text} on {stage['name']} with the {vehicle['name']}", reward=reward)

    def daily_done(self):
        return self.data["daily_done"] == self.daily()["date"]

    def daily_progress(self, run):
        d = self.daily()
        if run.stage["key"] != d["stage"]["key"] or run.spec["key"] != d["vehicle"]["key"]:
            return None
        value = {"distance": run.distance, "flips": run.flips, "coins": run.coin_pickups,
                 "air": run.max_air}[d["kind"]]
        return d, value

    def daily_check(self, run):
        if self.daily_done():
            return
        got = self.daily_progress(run)
        if got and got[1] >= got[0]["target"]:
            d = got[0]
            self.data["daily_done"] = d["date"]
            self.data["coins"] += d["reward"]
            run.hud.toast("DAILY CHALLENGE DONE!", f"+{d['reward']:,} coins")
            self.app.audio.play("finish")
            self.app.persist()
