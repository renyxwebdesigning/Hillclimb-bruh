"""Online session: lobby, synchronised starts, car syncing and race results.

The host is player 0 and relays everything; every player simulates their own
vehicle and sends its pose 20 times a second. Other players' cars are drawn
as smoothed "ghosts" (no collisions between cars), on the same track.
"""
import math
import time

import net
from config import VEHICLE_BY_KEY

COLORS = [(255, 214, 60), (90, 200, 255), (255, 110, 150), (130, 230, 90), (255, 150, 60),
          (190, 140, 255), (240, 240, 240), (80, 240, 210)]
SEND_HZ = 20


class RemoteWheel:
    __slots__ = ("x", "y", "angle", "r")

    def __init__(self, r):
        self.x = self.y = self.angle = 0.0
        self.r = r


class RemoteCar:
    """Looks like a physics Vehicle to the renderer, but follows network updates."""

    def __init__(self, spec):
        self.spec = spec
        self.HEAD, self.NOZZLE = spec["head"], spec["nozzle"]
        self.x = self.y = self.angle = 0.0
        self.vx = self.vy = 0.0
        self.wheels = [RemoteWheel(w[2]) for w in spec["wheels"]]
        self.target = None
        self.boosting = self.thrusting = self.seized = self.lights = self.respawning = False
        self.dist = 0
        self.ready = False

    def to_world(self, lx, ly):
        c, s = math.cos(self.angle), math.sin(self.angle)
        return self.x + lx * c - ly * s, self.y + lx * s + ly * c

    def apply(self, s):
        self.target = s
        flags = int(s[9])
        self.boosting, self.thrusting = bool(flags & 1), bool(flags & 2)
        self.seized, self.lights, self.respawning = bool(flags & 4), bool(flags & 8), bool(flags & 16)
        self.dist = s[10]
        if not self.ready or abs(s[0] - self.x) > 25:
            self._snap()
            self.ready = True

    def _snap(self):
        s = self.target
        self.x, self.y, self.angle = s[0], s[1], s[2]
        for i, w in enumerate(self.wheels):
            w.x, w.y, w.angle = s[3 + 3 * i], s[4 + 3 * i], s[5 + 3 * i]

    def update(self, dt):
        if not self.target:
            return
        s = self.target
        k = 1 - math.exp(-dt * 16)

        def ang(cur, tgt):
            d = (tgt - cur + math.pi) % (2 * math.pi) - math.pi
            return cur + d * k
        ox, oy = self.x, self.y
        self.x += (s[0] - self.x) * k
        self.y += (s[1] - self.y) * k
        if dt > 0:
            self.vx += ((self.x - ox) / dt - self.vx) * 0.2
            self.vy += ((self.y - oy) / dt - self.vy) * 0.2
        self.angle = ang(self.angle, s[2])
        for i, w in enumerate(self.wheels):
            w.x += (s[3 + 3 * i] - w.x) * k
            w.y += (s[4 + 3 * i] - w.y) * k
            w.angle = ang(w.angle, s[5 + 3 * i])


def pack_state(run):
    car = run.car
    flags = (1 if car.boosting else 0) | (2 if car.thrusting else 0) | (4 if run.seized else 0) \
        | (8 if run.lights_on else 0) | (16 if run.respawn_t is not None else 0)
    s = [car.x, car.y, car.angle]
    for w in car.wheels[:2]:
        s += [w.x, w.y, w.angle]
    s += [flags, run.distance]
    return [round(v, 3) if isinstance(v, float) else v for v in s]


class Session:
    def __init__(self, hosting, name, vehicle, driver, address=None):
        self.is_host = hosting
        self.name = name
        self.players = {}
        self.settings = {"stage": "countryside", "mode": "race", "distance": 1000}
        self.phase = "lobby"
        self.remote = {}
        self.events = []
        self.finish = {}
        self.results = None
        self.error = None
        self.started = None
        self.to_lobby = False
        self._send_t = 0.0
        self._first_finish = None
        if hosting:
            self.net = net.Host()
            self.my_id = 0
            self.players[0] = dict(name=name, vehicle=vehicle, driver=driver, color=COLORS[0])
        else:
            host, port = net.parse_address(address)
            self.net = net.Client(host, port)
            self.my_id = None
            self.net.send({"t": "hello", "v": net.VERSION, "name": name, "vehicle": vehicle, "driver": driver})

    # --------------------------------------------------------------- helpers
    def _lobby_msg(self):
        return {"t": "lobby", "players": {str(k): v for k, v in self.players.items()},
                "settings": self.settings, "phase": self.phase}

    def _set_players(self, players):
        self.players = {int(k): v for k, v in players.items()}
        for k, v in self.players.items():
            v["color"] = tuple(v["color"])
        for k in list(self.remote):
            if k not in self.players:
                del self.remote[k]

    def _remote(self, pid):
        p = self.players.get(pid)
        if p is None:
            return None
        car = self.remote.get(pid)
        if car is None or car.spec["key"] != p["vehicle"]:
            car = self.remote[pid] = RemoteCar(VEHICLE_BY_KEY[p["vehicle"]])
        return car

    @property
    def me(self):
        return self.players.get(self.my_id, {})

    # ---------------------------------------------------------------- update
    def update(self, dt):
        for pid, msg in self.net.poll():
            try:
                (self._host_msg if self.is_host else self._client_msg)(pid, msg)
            except (KeyError, TypeError, ValueError, IndexError):
                pass
        for car in self.remote.values():
            car.update(dt)
        if self.is_host and self.phase == "race" and self.results is None and self.finish:
            everyone = all(pid in self.finish for pid in self.players)
            if everyone or time.monotonic() - self._first_finish > 45:
                self._publish_results()

    def _host_msg(self, cid, msg):
        t = msg.get("t")
        if t == "hello":
            if msg.get("v") != net.VERSION:
                self.net.send(cid, {"t": "error", "text": "Different game version - update Hill Rider on both PCs."})
                self.net.drop(cid)
                return
            self.players[cid] = dict(name=str(msg.get("name", "Player"))[:16], vehicle=msg.get("vehicle", "jeep"),
                                     driver=msg.get("driver", "default"), color=COLORS[cid % len(COLORS)])
            self.net.send(cid, {"t": "welcome", "id": cid})
            self.net.broadcast(self._lobby_msg())
            if self.phase == "free":
                self.net.send(cid, {"t": "start", "settings": self.settings})
        elif t == "pick":
            if cid in self.players:
                self.players[cid]["vehicle"] = msg["vehicle"]
                self.players[cid]["driver"] = msg["driver"]
                self.net.broadcast(self._lobby_msg())
        elif t == "state":
            car = self._remote(cid)
            if car:
                car.apply(msg["s"])
            self.net.broadcast({"t": "state", "id": cid, "s": msg["s"]}, exclude=cid)
        elif t == "event":
            self.net.broadcast({"t": "event", "id": cid, "e": msg["e"]}, exclude=cid)
            self._event(cid, msg["e"])
        elif t == "_closed":
            self.players.pop(cid, None)
            self.remote.pop(cid, None)
            self.net.drop(cid)
            self.net.broadcast(self._lobby_msg())

    def _client_msg(self, _, msg):
        t = msg.get("t")
        if t == "welcome":
            self.my_id = msg["id"]
        elif t == "lobby":
            self._set_players(msg["players"])
            self.settings = msg["settings"]
        elif t == "start":
            self.settings = msg["settings"]
            self._begin()
        elif t == "state":
            car = self._remote(msg["id"])
            if car:
                car.apply(msg["s"])
        elif t == "event":
            self._event(msg["id"], msg["e"])
        elif t == "results":
            self.results = [(int(r[0]), r[1], r[2]) for r in msg["rows"]]
        elif t == "lobby_return":
            self.phase = "lobby"
            self.to_lobby = True
        elif t == "error":
            self.error = msg.get("text", "Error")
        elif t == "_closed":
            self.error = self.error or "Lost the connection to the host."

    def _event(self, pid, ev):
        if ev.get("kind") == "finish":
            self.finish[pid] = float(ev["time"])
            if self._first_finish is None:
                self._first_finish = time.monotonic()
        self.events.append((pid, ev))

    def _begin(self):
        self.phase = self.settings["mode"]
        self.finish = {}
        self.results = None
        self._first_finish = None
        self.started = dict(self.settings)
        self.remote.clear()

    def _publish_results(self):
        rows = []
        for pid in self.players:
            if pid in self.finish:
                rows.append((pid, self.finish[pid], self.settings["distance"]))
            else:
                dist = self.remote[pid].dist if pid in self.remote else 0
                rows.append((pid, None, dist))
        rows.sort(key=lambda r: (r[1] is None, r[1] if r[1] is not None else -r[2]))
        self.results = rows
        self.net.broadcast({"t": "results", "rows": rows})

    # --------------------------------------------------------------- actions
    def pick(self, vehicle, driver):
        if self.my_id in self.players:
            self.players[self.my_id]["vehicle"] = vehicle
            self.players[self.my_id]["driver"] = driver
        if self.is_host:
            self.net.broadcast(self._lobby_msg())
        else:
            self.net.send({"t": "pick", "vehicle": vehicle, "driver": driver})

    def configure(self, **settings):
        if self.is_host:
            self.settings.update(settings)
            self.net.broadcast(self._lobby_msg())

    def start(self):
        if self.is_host:
            self.net.broadcast({"t": "start", "settings": self.settings})
            self._begin()

    def back_to_lobby(self):
        if self.is_host:
            self.phase = "lobby"
            self.to_lobby = True
            self.net.broadcast({"t": "lobby_return"})
            self.net.broadcast(self._lobby_msg())

    def send_state(self, run, dt):
        self._send_t -= dt
        if self._send_t > 0:
            return
        self._send_t = 1.0 / SEND_HZ
        s = pack_state(run)
        if self.is_host:
            self.net.broadcast({"t": "state", "id": 0, "s": s})
        else:
            self.net.send({"t": "state", "s": s})

    def send_event(self, ev):
        if self.is_host:
            self.net.broadcast({"t": "event", "id": 0, "e": ev})
            if ev.get("kind") == "finish":
                self._event(0, dict(ev))
        else:
            self.net.send({"t": "event", "e": ev})
            if ev.get("kind") == "finish" and self.my_id is not None:
                self.finish[self.my_id] = float(ev["time"])

    def leave(self):
        try:
            self.net.close()
        except OSError:
            pass
