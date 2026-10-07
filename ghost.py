"""Ghost replays: record a run, save the best one per stage, play it back as a see-through car."""
import bisect
import json
import math
from pathlib import Path

from config import VEHICLE_BY_KEY
from online import RemoteCar

DIR = Path.home() / ".hill_rider" / "ghosts"
RATE = 15.0


class Recorder:
    def __init__(self, run):
        self.vehicle, self.driver = run.spec["key"], run.driver
        self.frames = []
        self._t = 0.0

    def record(self, run, dt):
        self._t -= dt
        if self._t > 0 or run.state != "drive" or len(self.frames) > RATE * 60 * 20:
            return
        self._t = 1.0 / RATE
        car = run.car
        f = [round(run.time, 3), car.x, car.y, car.angle]
        for w in car.wheels[:2]:
            f += [w.x, w.y, w.angle]
        self.frames.append([round(v, 3) for v in f])

    def save(self, stage_key, distance):
        if len(self.frames) < 10:
            return
        try:
            DIR.mkdir(parents=True, exist_ok=True)
            data = {"vehicle": self.vehicle, "driver": self.driver, "distance": distance, "frames": self.frames}
            (DIR / f"{stage_key}.json").write_text(json.dumps(data, separators=(",", ":")))
        except OSError:
            pass


class Player:
    def __init__(self, data):
        self.frames = data["frames"]
        self.times = [f[0] for f in self.frames]
        self.distance = data.get("distance", 0)
        self.driver = data.get("driver", "default")
        self.car = RemoteCar(VEHICLE_BY_KEY.get(data["vehicle"], VEHICLE_BY_KEY["jeep"]))
        self.done = False

    def update(self, t):
        i = bisect.bisect_right(self.times, t) - 1
        if i >= len(self.frames) - 1:
            self.done = True
            i = len(self.frames) - 2
        i = max(0, i)
        a, b = self.frames[i], self.frames[i + 1]
        span = b[0] - a[0] or 1
        k = max(0.0, min(1.0, (t - a[0]) / span))

        def lerp(j, angle=False):
            if angle:
                d = (b[j] - a[j] + math.pi) % (2 * math.pi) - math.pi
                return a[j] + d * k
            return a[j] + (b[j] - a[j]) * k
        car = self.car
        car.x, car.y, car.angle = lerp(1), lerp(2), lerp(3, True)
        for n, w in enumerate(car.wheels[:2]):
            w.x, w.y, w.angle = lerp(4 + 3 * n), lerp(5 + 3 * n), lerp(6 + 3 * n, True)


def load(stage_key):
    try:
        return Player(json.loads((DIR / f"{stage_key}.json").read_text()))
    except (OSError, ValueError, KeyError, IndexError):
        return None
