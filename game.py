"""One run on a stage: physics, pickups, stunts, Kolbenklemmer, horn, races."""
import math
import random

from config import (BOOST_RECHARGE, FLIP_BONUS, NECK_FLIP_BONUS, PHYS_DT, SEIZE_GRACE, SEIZE_RATE,
                    vehicle_stats)
from physics import Vehicle
from render import Camera, Particles

START_X = 2.0


class Run:
    def __init__(self, stage, terrain, spec, levels, bank, best, audio, hud, driver="default",
                 horn="puppy", online=None, mode="solo", race_m=0):
        self.stage, self.terrain, self.audio, self.hud = stage, terrain, audio, hud
        self.spec, self.driver, self.horn_kind = spec, driver, horn
        self.online, self.mode, self.race_m = online, mode, race_m
        self.stats = vehicle_stats(spec, levels)
        self._lift = max(spec["rest"] + w[2] - w[1] for w in spec["wheels"]) + 0.05
        self.car = Vehicle(START_X, terrain.height(START_X) + self._lift, spec, self.stats)
        self.boost = 1.0
        self.boosting = False
        self.cam = Camera()
        self.cam.follow(self.car, terrain, 0, snap=True)
        self.particles = Particles()
        self.bank, self.best = bank, best
        self.state = "drive"            # drive -> ending -> done
        self.reason = ""
        self.end_t = 0.0
        self.countdown = 3.4 if mode == "race" else 0.0
        self.finished_at = None
        self.coins = 0                  # everything earned this run
        self.coin_pickups = 0
        self.bonus_total = 0
        self.distance = 0
        self.time = 0.0
        self.race_time = 0.0
        self.respawn_t = None
        # Kolbenklemmer
        self.seized = False
        self.fix_needed = 0
        self.fix_count = 0
        self.fix_shake = 0.0
        self._safe_until = SEIZE_GRACE
        self.bubble = None              # (text, seconds left)
        self.lights_on = False
        self.lights_forced = None       # None = automatic
        self.outbox = []                # events for other online players
        self._acc = 0.0
        self._coin_lo = 0
        self._air_t = 0.0
        self._air_rot = 0.0
        self._inverted_head = 9.0
        self._land_vy = 0.0
        self._exhaust_t = 0.0
        self._smoke_t = 0.0
        self._horn_t = 0.0
        self._coin_sound_t = 0.0
        self._last_count = 4
        self._prev_v = (0.0, 0.0)
        self.wobble = [0.0, 0.0, 0.0]
        self._wobble_v = [0.0, 0.0]

    # ------------------------------------------------------------------ main
    def update(self, dt, gas, brake, boost=False):
        self.time += dt
        if self.countdown > 0:
            self._tick_countdown(dt)
            gas = brake = boost = False
        else:
            self.race_time += dt
        alive = self.state == "drive" and self.respawn_t is None
        car, st = self.car, self.stage
        g, b = gas and alive, brake and alive
        self.boosting = boost and alive and self.boost > 0
        if self.boosting:
            self.boost = max(0.0, self.boost - dt / self.stats["boost_seconds"])
        else:
            self.boost = min(1.0, self.boost + dt / BOOST_RECHARGE)
        self.audio.boost(self.boosting)
        car.engine_on = not self.seized

        self._acc += dt
        steps = 0
        while self._acc >= PHYS_DT and steps < 50:
            car.step(PHYS_DT, g, b, self.boosting, self.terrain, st["gravity"], st["grip"])
            self._acc -= PHYS_DT
            steps += 1
            if not car.grounded:
                self._land_vy = car.vy
        if steps == 50:
            self._acc = 0.0

        if self.state == "drive":
            if car.head_hit and self.respawn_t is None:
                self._crash()
            if self.respawn_t is not None:
                self.respawn_t -= dt
                if self.respawn_t <= 0:
                    self._respawn()
            else:
                self._pickups()
                self._stunts(dt)
                self._maybe_seize(dt, g)
                self._check_finish()
        else:
            self.end_t += dt
            if self.end_t > 2.2:
                self.state = "done"

        if self.bubble:
            self.bubble = (self.bubble[0], self.bubble[1] - dt) if self.bubble[1] > dt else None
        self.fix_shake = max(0.0, self.fix_shake - dt)
        self._horn_t = max(0.0, self._horn_t - dt)
        self.distance = max(self.distance, int(max(0.0, car.x - START_X)))
        self._head_wobble(dt)
        self._effects(dt, g)
        self.particles.update(dt)
        self.cam.follow(car, self.terrain, dt)
        load = (1.0 if g else 0.15) + (0.3 if self.boosting else 0.0)
        self.audio.engine_update(car.rpm, min(1.0, load), on=car.engine_on)

    def _tick_countdown(self, dt):
        self.countdown -= dt
        n = math.ceil(self.countdown - 0.4)
        if n < self._last_count:
            self._last_count = n
            self.audio.play("go" if n <= 0 else "count")

    # ------------------------------------------------------------- crashing
    def _crash(self):
        self.audio.play("crash")
        x, y = self.car.to_world(*self.car.HEAD)
        for _ in range(18):
            self.particles.add("chunk", x, y, random.uniform(-3, 3), random.uniform(1, 5), 0.9,
                               random.uniform(0.06, 0.13), random.choice((self.stage["ground"], self.stage["top"])))
        if self.online:
            # Online nobody drops out: shake it off and get back on the road.
            self.respawn_t = 1.6
            self.hud.notice("DRIVER DOWN!", (255, 90, 70))
            self.outbox.append({"kind": "crash"})
        else:
            self.finish("DRIVER DOWN!")

    def _respawn(self):
        self.respawn_t = None
        x = max(START_X, self.car.x - 2.0)
        if self.terrain.feature_at(x, 2.0) == "tunnel":
            x = self.car.x
        self.car = Vehicle(x, self.terrain.height(x) + self._lift + 0.2, self.spec, self.stats)
        self.car.engine_on = not self.seized

    def finish(self, reason):
        if self.state != "drive":
            return
        self.state = "ending"
        self.reason = reason
        self.end_t = 0.0
        self.boosting = False
        self.audio.boost(False)

    def _check_finish(self):
        if self.mode != "race" or self.finished_at is not None:
            return
        if self.car.x - START_X >= self.race_m:
            self.finished_at = self.race_time
            self.audio.play("finish")
            self.hud.notice("FINISH!", (255, 220, 60))
            self.outbox.append({"kind": "finish", "time": round(self.race_time, 3)})

    # ---------------------------------------------------------- Kolbenklemmer
    def _maybe_seize(self, dt, gas):
        if self.seized or self.time < self._safe_until or not gas or self.countdown > 0:
            return
        if random.random() < SEIZE_RATE * dt:
            self.seize()

    def seize(self):
        self.seized = True
        self.fix_needed = random.randint(5, 30)
        self.fix_count = 0
        self.car.engine_on = False
        self.audio.play("seize")
        text, line = self.audio.say(self.driver)
        self.bubble = (text, 3.0)
        self.outbox.append({"kind": "seize", "line": line})

    def repair(self):
        """One whack with the spanner (Enter)."""
        if not self.seized or self.state != "drive":
            return
        self.fix_count += 1
        self.fix_shake = 0.18
        self.audio.play("wrench")
        x, y = self.car.to_world(*self.spec["engine"])
        for _ in range(6):
            self.particles.add("spark", x, y, random.uniform(-3, 3), random.uniform(1, 4), 0.35, 0.06,
                               (255, 230, 140), grav=6, back=False)
        if self.fix_count >= self.fix_needed:
            self.seized = False
            self.car.engine_on = True
            self._safe_until = self.time + SEIZE_GRACE * 2
            self.audio.play("restart")
            self.hud.notice("FIXED!", (120, 230, 90))
            self.outbox.append({"kind": "fixed"})

    # --------------------------------------------------------------- horn
    def honk(self):
        if self._horn_t > 0:
            return
        self._horn_t = 0.35 if self.horn_kind == "puppy" else 1.0
        self.audio.play("horn_" + self.horn_kind)
        self.outbox.append({"kind": "horn", "horn": self.horn_kind})

    def toggle_lights(self):
        self.lights_forced = not self.lights_on

    # --------------------------------------------------------------- systems
    def _pickups(self):
        car = self.car
        hx, hy = car.to_world(*car.HEAD)
        probes = [(car.x, car.y + 0.2, 1.25), (hx, hy, 0.5)] + [(w.x, w.y, 0.62) for w in car.wheels]
        coins = self.terrain.coins
        while self._coin_lo < len(coins) and coins[self._coin_lo][0] < car.x - 4:
            self._coin_lo += 1
        i = self._coin_lo
        while i < len(coins) and coins[i][0] < car.x + 4:
            c = coins[i]
            if not c[3]:
                for px, py, pr in probes:
                    if (c[0] - px) ** 2 + (c[1] - py) ** 2 < (pr + 0.35) ** 2:
                        c[3] = True
                        self.coins += c[2]
                        self.coin_pickups += c[2]
                        if self.time - self._coin_sound_t > 0.035:
                            self.audio.play("coin")
                            self._coin_sound_t = self.time
                        for _ in range(4):
                            self.particles.add("spark", c[0], c[1], random.uniform(-2, 2), random.uniform(0, 3),
                                               0.4, 0.07, (255, 236, 120), grav=4, back=False)
                        break
            i += 1

    def _stunts(self, dt):
        car = self.car
        airborne = not car.grounded and not car.hull_contact
        if airborne:
            self._air_t += dt
            self._air_rot += car.omega * dt
            if math.cos(car.angle) < -0.5:
                self._inverted_head = min(self._inverted_head, car.head_clearance)
            return
        if self._air_t > 0:
            if car.grounded and not car.head_hit:
                flips = int((abs(self._air_rot) + 0.6) / math.tau)
                if flips:
                    title = "FLIP" if flips == 1 else "DOUBLE FLIP" if flips == 2 else f"{flips}x FLIP"
                    self._award(title, FLIP_BONUS * flips)
                    if self._inverted_head < 0.5:
                        self._award("NECK FLIP", NECK_FLIP_BONUS)
                t = self._air_t
                if t >= 1.0:
                    title = "AIR TIME" if t < 2.5 else "BIG AIR TIME" if t < 4 else "INSANE AIR TIME"
                    self._award(title, max(50, int(t * t * 60 / 25) * 25))
            if -self._land_vy > 4.5:
                self.audio.play("land")
                for w in car.wheels:
                    for _ in range(4):
                        self.particles.add("smoke", w.x, w.y - w.r * 0.8, random.uniform(-1.6, 1.6),
                                           random.uniform(0.2, 1.0), 0.7, 0.16, self.stage["top_lo"], grav=0)
        self._air_t = 0.0
        self._air_rot = 0.0
        self._inverted_head = 9.0
        self._land_vy = 0.0

    def _award(self, title, amount):
        self.coins += amount
        self.bonus_total += amount
        self.hud.bonus(title, amount)
        self.audio.play("bonus")

    def _head_wobble(self, dt):
        car = self.car
        if dt <= 0:
            return
        ax = (car.vx - self._prev_v[0]) / dt
        ay = (car.vy - self._prev_v[1]) / dt
        self._prev_v = (car.vx, car.vy)
        c, s = math.cos(car.angle), math.sin(car.angle)
        lx = max(-60.0, min(60.0, ax * c + ay * s))
        ly = max(-60.0, min(60.0, -ax * s + ay * c))
        for i, a in enumerate((lx, ly)):
            target = max(-0.09, min(0.09, -a * 0.0035))
            self._wobble_v[i] += ((target - self.wobble[i]) * 160 - self._wobble_v[i] * 12) * dt
            self.wobble[i] += self._wobble_v[i] * dt
        self.wobble[2] = -self.wobble[0] * 1.8
        if self.fix_shake > 0:
            self.wobble[1] += math.sin(self.time * 70) * 0.03

    def _effects(self, dt, gas):
        car, st = self.car, self.stage
        colors = (st["ground"], st["top"], st["pebble"], st["top_lo"])
        for w in car.wheels:
            if w.contact and abs(w.slip) > 1.6 and random.random() < min(1.0, abs(w.slip) * 0.12):
                tx, ty = w.ny, -w.nx
                d = 1 if w.slip > 0 else -1     # fling dirt the way the tyre surface moves
                speed = random.uniform(2, 5)
                self.particles.add("chunk", w.x - w.nx * w.r, w.y - w.ny * w.r,
                                   tx * speed * d + w.nx * random.uniform(1.5, 4),
                                   ty * speed * d + w.ny * random.uniform(1.5, 4),
                                   random.uniform(0.5, 0.9), random.uniform(0.05, 0.11), random.choice(colors))
        if car.boosting or car.thrusting:
            x, y = car.to_world(*car.NOZZLE)
            c, s = math.cos(car.angle), math.sin(car.angle)
            for _ in range(2):
                sp = random.uniform(4, 8)
                self.particles.add("spark", x, y, -c * sp + car.vx * 0.5 + random.uniform(-1, 1),
                                   -s * sp + car.vy * 0.5 + random.uniform(-1, 1), 0.3, 0.06,
                                   random.choice(((255, 200, 60), (255, 120, 30), (255, 240, 180))), grav=2)
            if st["decor"] != "space" and random.random() < 0.5:
                self.particles.add("smoke", x - c * 0.9, y - s * 0.9, -c * 2 + car.vx * 0.3, -s * 2 + 0.4, 0.9, 0.16,
                                   (190, 190, 196), grav=-0.6)
        if self.seized:
            self._smoke_t -= dt
            if self._smoke_t <= 0:
                self._smoke_t = 0.05
                black_smoke(self.particles, car, self.spec)
        self._exhaust_t -= dt
        if gas and car.engine_on and st["decor"] != "space" and self._exhaust_t <= 0 and not car.thrusting:
            self._exhaust_t = 0.07
            x, y = car.to_world(*car.EXHAUST)
            c = math.cos(car.angle)
            self.particles.add("smoke", x, y, -1.4 * c + car.vx * 0.2, 0.5 + car.vy * 0.2, 0.8, 0.13,
                               (150, 150, 156), grav=-0.8)


def black_smoke(particles, car, spec):
    """Thick black smoke pouring out of a seized engine."""
    x, y = car.to_world(*spec["engine"])
    particles.add("smoke", x + random.uniform(-0.15, 0.15), y, random.uniform(-0.6, 0.6) + car.vx * 0.3,
                  random.uniform(1.0, 2.0), random.uniform(1.2, 1.8), random.uniform(0.18, 0.28),
                  random.choice(((28, 28, 30), (45, 44, 46), (60, 58, 60))), grav=-1.5, back=False)
