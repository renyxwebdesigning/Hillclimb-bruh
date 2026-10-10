"""One run on a stage: physics, pickups, stunts, horn, races."""
import math
import random

from config import FLIP_BONUS, GRAVITY_SCALE, NECK_FLIP_BONUS, PHYS_DT, season_at, vehicle_stats
from physics import Vehicle
from render import Camera, Particles
from terrain import thing_shapes

START_X = 2.0


class Run:
    def __init__(self, stage, terrain, spec, levels, bank, best, audio, hud, driver="default",
                 horn="puppy", online=None, mode="solo", race_m=0, progress=None, story=None):
        self.stage, self.terrain, self.audio, self.hud = stage, terrain, audio, hud
        self.spec, self.driver, self.horn_kind = spec, driver, horn
        self.online, self.mode, self.race_m = online, mode, race_m
        self.progress = progress
        # story mode: (city, event) and the AI cars; a crash costs time there instead of ending the run
        self.story = story
        self.forgiving = online is not None or story is not None
        self.story_result = None
        self.busted = 0.0
        self._siren_t = 0.0
        self.flips = 0
        self.max_air = 0.0
        self.pits_cleared = 0
        self.broken = set()             # crate walls smashed this run
        self._pull_t = 0.0              # how long the turbo has been pulling hard
        self._slow_note = None
        self._skip_to = None            # online: where to respawn after an obstacle got you
        self.night_m = 0.0
        self.is_night = False
        self._next_pit = 0
        self._live_t = 0.0
        self._last_x = START_X
        for t in terrain.trophies:
            t[3] = bool(progress and progress.has_trophy(stage["key"], t[2]))
        self.stats = vehicle_stats(spec, levels)
        self.opponents = []
        if story is not None:
            import story as story_mode
            self.opponents = story_mode.make_opponents(terrain, stage, story[0], story[1], START_X)
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
        self.bubble = None              # (text, seconds left)
        self.lights_on = False
        self.lights_forced = None       # None = automatic
        self.outbox = []                # events for other online players
        self._acc = 0.0
        self._coin_lo = 0
        for n in terrain.nitro:
            n[2] = False
        self._air_t = 0.0
        self._air_rot = 0.0
        self._inverted_head = 9.0
        self._flip_t = 0.0
        self._land_vy = 0.0
        self._exhaust_t = 0.0
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
        if self.boosting:                  # no refill over time: grab the blue nitro cans
            self.boost = max(0.0, self.boost - dt / self.stats["boost_seconds"])
        self.audio.boost(self.boosting)

        grip = st["grip"]
        season = season_at(st, car.x)
        if season is not None:                      # Four Seasons: icy winter, grippy summer
            grip = st["seasons"][season[0]]["grip"]
            if season[0] != getattr(self, "_season", None):
                if getattr(self, "_season", None) is not None:
                    name = st["seasons"][season[0]]["name"]
                    self.hud.notice(name + "!", {"WINTER": (170, 220, 255), "SPRING": (255, 160, 200),
                                                 "SUMMER": (255, 220, 60), "FALL": (240, 140, 40)}[name])
                self._season = season[0]
        drag = 0.0
        zone = self.terrain.zone_at(car.x)
        if zone:
            mul, drag = self.terrain.ZONES[zone]
            grip *= mul
            if zone != getattr(self, "_zone", None) and self.state == "drive":
                self.hud.notice({"mud": "MUD!", "ice": "ICE!", "snow": "DEEP SNOW!", "sand": "SAND!",
                                 "oil": "OIL!", "seaweed": "SEAWEED!"}[zone], (230, 230, 240))
        self._zone = zone
        # turbo blow-off: lifting off the gas after pulling hard goes "pssh"
        if self.stats["levels"].get("turbo", 1) >= 2:
            if g:
                self._pull_t = self._pull_t + dt if car.rpm > 0.55 else 0.0
            else:
                if self._pull_t > 0.5:
                    self.audio.play("turbo", 0.7)
                self._pull_t = 0.0
        self._acc += dt
        shapes = self._shapes(car, dt) if alive else ()
        steps = 0
        while self._acc >= PHYS_DT and steps < 50:
            car.step(PHYS_DT, g, b, self.boosting, self.terrain, st["gravity"] * GRAVITY_SCALE, grip, drag,
                     st.get("water_drag", 0.0), shapes)
            self._acc -= PHYS_DT
            steps += 1
            if not car.grounded:
                self._land_vy = car.vy
        if steps == 50:
            self._acc = 0.0
        if not (math.isfinite(car.x) and math.isfinite(car.y) and abs(car.vx) + abs(car.vy) < 400):
            self._respawn()                 # physics went wild: put the vehicle back on the road
            car = self.car

        if self.state == "drive" and car.touched and self.respawn_t is None:
            self._hit_things(car)
        car.touched.clear()
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
                self._check_finish()
                if self.story is not None:
                    self._story_tick(dt)
                self._check_lava()
                self._check_flipped(dt)
        else:
            self.end_t += dt
            if self.end_t > 2.2:
                self.state = "done"

        if self.bubble:
            self.bubble = (self.bubble[0], self.bubble[1] - dt) if self.bubble[1] > dt else None
        self._horn_t = max(0.0, self._horn_t - dt)
        self.distance = max(self.distance, int(max(0.0, car.x - START_X)))
        if self.state == "drive":
            if self.is_night and car.x > self._last_x:
                self.night_m += car.x - self._last_x
            pits = self.terrain.pits
            while self._next_pit < len(pits) and car.x > pits[self._next_pit][1] + 1.0:
                if pits[self._next_pit][1] < car.x and self.respawn_t is None and st.get("lava"):
                    self.pits_cleared += 1
                self._next_pit += 1
            self._live_t -= dt
            if self.progress and self._live_t <= 0:
                self._live_t = 0.5
                self.progress.live(self)
                self.progress.daily_check(self)
        self._last_x = car.x
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
    def _swear(self):
        """The driver shouts a line (and other online players hear it too)."""
        text, line = self.audio.say(self.driver)
        self.bubble = (text, 2.6)
        return line

    def _crash(self):
        self.audio.play("crash")
        line = self._swear()
        x, y = self.car.to_world(*self.car.HEAD)
        for _ in range(18):
            self.particles.add("chunk", x, y, random.uniform(-3, 3), random.uniform(1, 5), 0.9,
                               random.uniform(0.06, 0.13), random.choice((self.stage["ground"], self.stage["top"])))
        if self.forgiving:
            # Online (and in story races) nobody drops out: shake it off and get back on the road.
            self.respawn_t = 1.6
            self.hud.notice("DRIVER DOWN!", (255, 90, 70))
            self.outbox.append({"kind": "crash", "line": line})
        else:
            self.finish("DRIVER DOWN!")

    def _check_lava(self):
        pit = self.terrain.pit_at(self.car.x)
        if pit and min(w.y - w.r for w in self.car.wheels) < pit[2] + 0.1:
            self.audio.play("crash")
            line = self._swear()
            lava = self.stage.get("lava")
            if lava:
                for _ in range(24):
                    self.particles.add("spark", self.car.x, pit[2], random.uniform(-3, 3), random.uniform(2, 7), 0.8,
                                       0.09, random.choice(((255, 200, 60), (255, 110, 20), (255, 60, 20))), grav=8)
            if self.forgiving:
                self.respawn_t = 1.2
                self.hud.notice("BURNED!" if lava else "FELL!", (255, 120, 40))
                self.outbox.append({"kind": "crash", "line": line})
            else:
                self.finish("BURNED IN LAVA!" if lava else "FELL INTO A GAP!")

    # ------------------------------------------------------------ obstacles
    def _shapes(self, car, dt):
        """Collision shapes of the obstacles around the car right now; smashes crate walls hit fast enough."""
        t = self.terrain
        out = []
        for i in t.thing_range(car.x - 6, car.x + 6):
            th = t.things[i]
            if th["kind"] == "crates":
                if i in self.broken:
                    continue
                speed = car.forward_speed
                need = th["need"] - (2.0 if self.boosting else 0.0)
                gap = th["x"] - th["w"] / 2 - (car.x + 2.7)
                if speed >= need and gap < speed * dt + 0.4 and car.x < th["x"]:
                    self._smash(i, th)
                    continue
            out.extend(thing_shapes(th, self.time, i, t))
        return out

    def _smash(self, i, th):
        self.broken.add(i)
        self.audio.play("crash")
        self.hud.notice("SMASH!", (255, 200, 60))
        car = self.car
        car.vx *= 0.8
        for w in car.wheels:
            w.vx *= 0.8
        col = {"city": (170, 74, 54), "arctic": (190, 230, 250)}.get(self.stage["key"], (176, 120, 64))
        for _ in range(26):
            self.particles.add("chunk", th["x"] + random.uniform(-0.4, 0.4), th["y"] + random.uniform(0.2, th["hgt"]),
                               car.vx * random.uniform(0.3, 0.9) + random.uniform(-1, 2), random.uniform(1, 6), 1.2,
                               random.uniform(0.1, 0.24), col, back=False)

    def _hit_things(self, car):
        t = self.terrain
        for i, (nx, ny) in car.touched.items():
            th = t.things[i]
            kind = th["kind"]
            if kind == "crates":
                if self._slow_note != i:
                    self._slow_note = i
                    self.hud.notice("TOO SLOW! BACK UP AND BOOST", (255, 220, 120))
                continue
            if kind == "car" and abs(nx) < 0.75:
                continue                                    # on the roof: fine
            reason, short = {"car": ("CRASHED INTO A CAR!", "CRASH!"), "traffic": ("HIT BY A CAR!", "CRASH!"),
                             "crusher": ("SQUASHED!", "SQUASHED!"), "wrecker": ("SMASHED!", "SMASHED!"),
                             "boulder": ("FLATTENED BY A BOULDER!", "FLATTENED!"), "flames": ("TOASTED!", "TOASTED!"),
                             "spinner": ("WHACKED!", "WHACKED!"), "spikes": ("SPIKED!", "SPIKED!")}[kind]
            end = next((b for a, b, _ in t.blocks if a - 2 <= th["x"] <= b + 2), th["x"] + 3)
            self._skip_to = end + 3.0
            self.audio.play("crash")
            line = self._swear()
            for _ in range(18):
                self.particles.add("chunk", car.x, car.y + 0.5, random.uniform(-3, 3), random.uniform(1, 5), 0.9,
                                   random.uniform(0.06, 0.13), (90, 90, 96))
            if self.forgiving:
                self.respawn_t = 1.4
                self.hud.notice(short, (255, 90, 70))
                self.outbox.append({"kind": "crash", "line": line})
            else:
                self.finish(reason)
            return

    def _check_flipped(self, dt):
        """On its roof and not moving (no fuel to run out): end the run instead of leaving the player stuck."""
        car = self.car
        resting = math.cos(car.angle) < -0.2 and math.hypot(car.vx, car.vy) < 1.0
        self._flip_t = self._flip_t + dt if resting else 0.0
        if self._flip_t < 2.5 or self.state != "drive":
            return
        self._flip_t = 0.0
        if self.forgiving:
            self.respawn_t = 0.4
            self.hud.notice("FLIPPED!", (255, 176, 40))
        else:
            self.audio.play("crash")
            self._swear()
            self.finish("FLIPPED OVER!")

    def _respawn(self):
        self.respawn_t = None
        if not math.isfinite(self.car.x):
            self.car.x = START_X + self.distance
        x = max(START_X, self.car.x - 2.0)
        pit = self.terrain.pit_at(self.car.x) or self.terrain.pit_at(self.car.x + 3)
        if self._skip_to is not None:
            x, self._skip_to = self._skip_to, None
        elif pit:
            x = pit[1] + 3.0
        elif self.terrain.feature_at(x, 2.0) == "tunnel":
            x = self.car.x
        self.car = Vehicle(x, self.terrain.height(x) + self._lift + 0.2, self.spec, self.stats)

    def finish(self, reason):
        if self.state != "drive":
            return
        self.state = "ending"
        self.reason = reason
        self.end_t = 0.0
        self.boosting = False
        self.audio.boost(False)

    # ---------------------------------------------------------------- story
    def _story_tick(self, dt):
        """AI cars drive, and the event is won or lost: first over the line, beat the clock, or escape the cops."""
        if self.countdown > 0:
            return
        car = self.car
        ev = self.story[1]
        for ai in self.opponents:
            ai.update(dt, car.x, self.time)
            if ai.role != "cop" and ai.finished_at is None and ai.x - START_X >= self.race_m:
                ai.finished_at = self.race_time
        kind = ev["kind"]
        if self.finished_at is not None:
            self._story_end("win", {"pursuit": "ESCAPED!", "trial": "MADE IT!"}.get(kind, "YOU WIN!"))
        elif kind in ("sprint", "rival") and any(ai.finished_at is not None for ai in self.opponents):
            self._story_end("lose", f"{self.opponents[0].name} WINS!")
        elif kind == "trial" and self.race_time > ev["limit"]:
            self._story_end("lose", "TIME'S UP!")
        elif kind == "pursuit":
            near = [ai for ai in self.opponents if abs(ai.x - car.x) < 4.5 and abs(ai.car.y - car.y) < 3.0
                    and ai.respawn_t is None]
            slow = math.hypot(car.vx, car.vy) < 9.0
            if near:                        # boxed in: fills fast when you are slow, slowly even at speed
                self.busted = min(2.0, self.busted + dt * (1.0 if slow else 0.35))
            else:
                self.busted = max(0.0, self.busted - dt * 0.6)
            closest = min((abs(ai.x - car.x) for ai in self.opponents), default=99)
            self._siren_t -= dt
            if closest < 40 and self._siren_t <= 0:
                self._siren_t = 2.6
                self.audio.play("horn_siren", 0.3 if closest > 15 else 0.55)
            if self.busted >= 2.0:
                self._story_end("lose", "BUSTED!")

    def _story_end(self, result, reason):
        self.story_result = result
        self.audio.play("finish" if result == "win" else "crash")
        self.finish(reason)

    def _check_finish(self):
        if self.mode != "race" or self.finished_at is not None:
            return
        if self.car.x - START_X >= self.race_m:
            self.finished_at = self.race_time
            self.audio.play("finish")
            self.hud.notice("FINISH!", (255, 220, 60))
            self.outbox.append({"kind": "finish", "time": round(self.race_time, 3)})

    # --------------------------------------------------------------- horn
    def honk(self):
        if self._horn_t > 0:
            return
        kind = "siren" if self.spec["key"] == "police" else self.horn_kind
        self._horn_t = {"puppy": 0.35, "ship": 1.0, "siren": 1.5}[kind]
        self.audio.play("horn_" + kind)
        self.outbox.append({"kind": "horn", "horn": kind})

    def toggle_lights(self):
        self.lights_forced = not self.lights_on

    # --------------------------------------------------------------- systems
    def _pickups(self):
        car = self.car
        hx, hy = car.to_world(*car.HEAD)
        probes = [(car.x, car.y + 0.2, 1.25), (hx, hy, 0.5)] + [(w.x, w.y, 0.62) for w in car.wheels]
        self._trophies(probes)
        for n in self.terrain.nitro:
            if n[2] or abs(n[0] - car.x) > 4:
                continue
            if any((n[0] - px) ** 2 + (n[1] - py) ** 2 < (pr + 0.5) ** 2 for px, py, pr in probes):
                n[2] = True
                self.boost = min(1.0, self.boost + 0.5)
                self.audio.play("fuel")
                self.hud.notice("NITRO!", (90, 200, 255))
                for _ in range(14):
                    self.particles.add("spark", n[0], n[1], random.uniform(-3, 3), random.uniform(-1, 4), 0.5, 0.08,
                                       (120, 220, 255), grav=3, back=False)
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

    def _trophies(self, probes):
        for t in self.terrain.trophies:
            if t[3] or abs(t[0] - self.car.x) > 4:
                continue
            if any((t[0] - px) ** 2 + (t[1] - py) ** 2 < (pr + 0.55) ** 2 for px, py, pr in probes):
                t[3] = True
                for _ in range(16):
                    self.particles.add("spark", t[0], t[1], random.uniform(-3, 3), random.uniform(-1, 4), 0.6, 0.09,
                                       (255, 230, 120), grav=4, back=False)
                if self.progress:
                    self.progress.trophy(self, t[2])

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
                    self.flips += flips
                    title = "FLIP" if flips == 1 else "DOUBLE FLIP" if flips == 2 else f"{flips}x FLIP"
                    self._award(title, FLIP_BONUS * flips)
                    if self._inverted_head < 0.5:
                        self._award("NECK FLIP", NECK_FLIP_BONUS)
                t = self._air_t
                self.max_air = max(self.max_air, t)
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

    def _effects(self, dt, gas):
        car, st = self.car, self.stage
        colors = {"mud": ((78, 52, 30), (98, 66, 38), (60, 40, 24)), "snow": ((250, 252, 255), (226, 236, 248)),
                  "sand": ((226, 196, 130), (204, 170, 104)), "ice": ((210, 236, 255), (250, 252, 255)),
                  "oil": ((30, 30, 34), (60, 60, 70))}.get(getattr(self, "_zone", None),
                                                           (st["ground"], st["top"], st["pebble"], st["top_lo"]))
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
        self._exhaust_t -= dt
        if gas and car.engine_on and st["decor"] != "space" and self._exhaust_t <= 0 and not car.thrusting:
            self._exhaust_t = 0.07
            x, y = car.to_world(*car.EXHAUST)
            c = math.cos(car.angle)
            self.particles.add("smoke", x, y, -1.4 * c + car.vx * 0.2, 0.5 + car.vy * 0.2, 0.8, 0.13,
                               (150, 150, 156), grav=-0.8)

