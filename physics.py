"""Vehicle physics: a rigid body on two sprung wheels over a height field.

World units are metres, seconds and kilograms; +y is up and angles are
counter-clockwise. Contacts use stiff penalty springs; tyre grip uses a
velocity-level friction impulse, which stays stable at any stiffness.
Every vehicle (cars, bikes, the B2 bomber, the shark) is the same model with different
numbers, see config.VEHICLES.
"""
import math

GROUND_K, GROUND_C = 130000.0, 3200.0       # wheel/ground contact spring
HULL_K, HULL_C = 160000.0, 5000.0           # body/ground contact spring
HULL_FRICTION, HULL_MU = 9000.0, 0.7
LAT_K, LAT_C = 260000.0, 5200.0             # keeps each wheel on its strut axis
STOP_K, STOP_C = 140000.0, 3500.0           # suspension bump stops
DRAG = 0.55


class Wheel:
    __slots__ = ("ax", "ay", "r", "m", "inv_m", "inv_i", "share", "x", "y", "vx", "vy", "angle", "omega",
                 "fx", "fy", "tq", "contact", "nx", "ny", "load", "slip", "brake")

    def __init__(self, ax, ay, radius, mass, share):
        self.ax, self.ay = ax, ay
        self.r, self.m, self.share = radius, mass, share
        self.inv_m = 1.0 / mass
        self.inv_i = 1.0 / (0.6 * mass * radius * radius)
        self.x = self.y = self.vx = self.vy = 0.0
        self.angle = self.omega = 0.0
        self.fx = self.fy = self.tq = 0.0
        self.contact = False
        self.nx, self.ny = 0.0, 1.0
        self.load = self.slip = 0.0
        self.brake = False


class Vehicle:
    def __init__(self, x, y, spec, stats):
        self.spec, self.stats = spec, stats
        self.MASS, self.INERTIA = float(spec["mass"]), float(spec["inertia"])
        self.REST = spec["rest"]
        self.EXT_MIN, self.EXT_MAX = spec["ext"]
        self.HULL = spec["hull"]
        self.HEAD, self.HEAD_R = spec["head"], spec["head_r"]
        self.EXHAUST, self.NOZZLE = spec["exhaust"], spec["nozzle"]
        self.air_torque = stats.get("air_torque", spec["air_torque"])
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.angle = self.omega = 0.0
        self.wheels = [Wheel(*w) for w in spec["wheels"]]
        for w in self.wheels:
            w.x, w.y = x + w.ax, y + w.ay - self.REST
        self.inv_m = 1.0 / self.MASS
        self.inv_i = 1.0 / self.INERTIA
        self.hull_contact = False
        self.head_hit = False
        self.touched = {}           # obstacle index -> contact normal, collected until the game reads it
        self.head_clearance = 9.0
        self.engine_on = True
        self.boosting = False
        self.thrusting = False
        self.rpm = 0.0

    # --------------------------------------------------------------- helpers
    def to_world(self, lx, ly):
        c, s = math.cos(self.angle), math.sin(self.angle)
        return self.x + lx * c - ly * s, self.y + lx * s + ly * c

    @property
    def grounded(self):
        return any(w.contact for w in self.wheels)

    @property
    def forward_speed(self):
        return self.vx * math.cos(self.angle) + self.vy * math.sin(self.angle)

    # ------------------------------------------------------------------ step
    def step(self, dt, gas, brake, boost, terrain, gravity, grip_scale, drag=0.0, water=0.0, shapes=()):
        """drag: mud, deep snow or sand on the road here (slows rolling wheels and the vehicle).
        water: extra resistance underwater (every move pushes through water, spinning slows down too).
        shapes: obstacles nearby (terrain.thing_shapes); solid ones push back, every touch is recorded."""
        st = self.stats
        c, s = math.cos(self.angle), math.sin(self.angle)
        dnx, dny = s, -c          # chassis "down"
        sdx, sdy = c, s           # chassis "forward"

        fx, fy, tq = 0.0, -self.MASS * gravity, 0.0
        speed = math.hypot(self.vx, self.vy)
        k = DRAG + water * 0.35
        fx -= k * self.vx * speed + water * self.MASS * 0.06 * self.vx
        fy -= k * self.vy * speed + water * self.MASS * 0.06 * self.vy

        for w in self.wheels:
            w.fx, w.fy, w.tq = 0.0, -w.m * gravity, 0.0
            w.brake = False

        # Suspension: soft along the strut, stiff across it.
        for w in self.wheels:
            rx, ry = w.ax * c - w.ay * s, w.ax * s + w.ay * c
            px, py = self.x + rx, self.y + ry
            avx, avy = self.vx - self.omega * ry, self.vy + self.omega * rx
            dx, dy = w.x - px, w.y - py
            ext = dx * dnx + dy * dny
            lat = dx * sdx + dy * sdy
            rvx, rvy = w.vx - avx, w.vy - avy
            vext = rvx * dnx + rvy * dny
            vlat = rvx * sdx + rvy * sdy
            f_ax = st["spring"] * (self.REST - ext) - st["damping"] * vext
            if ext < self.EXT_MIN:
                f_ax += STOP_K * (self.EXT_MIN - ext) - STOP_C * min(vext, 0.0)
            elif ext > self.EXT_MAX:
                f_ax -= STOP_K * (ext - self.EXT_MAX) + STOP_C * max(vext, 0.0)
            f_lat = -LAT_K * lat - LAT_C * vlat
            Fx = dnx * f_ax + sdx * f_lat
            Fy = dny * f_ax + sdy * f_lat
            w.fx += Fx
            w.fy += Fy
            fx -= Fx
            fy -= Fy
            tq -= rx * Fy - ry * Fx

        # Engine and brakes. Forward rolling is negative (clockwise) spin.
        driving = gas and self.engine_on
        self.thrusting = driving and st["thrust"] > 0
        if driving:
            for w in self.wheels:
                if w.share <= 0:
                    continue
                spin = -w.omega
                avail = max(0.0, 1.0 - spin / st["max_spin"])
                t = st["torque"] * w.share * avail
                w.tq -= t
                tq += t
            if st["thrust"] > 0:
                fx += sdx * st["thrust"]
                fy += sdy * st["thrust"]
        elif brake:
            if self.forward_speed > 0.6 or not self.engine_on:
                for w in self.wheels:
                    w.brake = True
            else:
                for w in self.wheels:
                    if w.share <= 0:
                        continue
                    spin = max(0.0, w.omega)
                    t = st["torque"] * 0.55 * w.share * max(0.0, 1.0 - spin / 14.0)
                    w.tq += t
                    tq -= t
        self.boosting = boost
        if boost:
            fx += sdx * st["boost_force"]
            fy += sdy * st["boost_force"]

        # Ground and ceiling contact for the wheels.
        for w in self.wheels:
            d, nx, ny = terrain.distance(w.x, w.y, w.r + 0.3)
            if d < w.r:
                pen = w.r - d
                vn = w.vx * nx + w.vy * ny
                fn = GROUND_K * pen - GROUND_C * vn
                if fn > 0:
                    w.fx += fn * nx
                    w.fy += fn * ny
                w.contact, w.nx, w.ny, w.load = True, nx, ny, max(fn, 0.0)
            else:
                w.contact, w.load = False, 0.0
            hit = terrain.rock(w.x, w.y, w.r)
            if hit:
                nx, ny, pen = hit
                fn = GROUND_K * pen - GROUND_C * (w.vx * nx + w.vy * ny)
                if fn > 0:
                    w.fx += fn * nx
                    w.fy += fn * ny

        # Body contact (roll bar, bumpers, roof) with the ground and tunnel roofs.
        hull_contact = False
        for lx, ly in self.HULL:
            rx, ry = lx * c - ly * s, lx * s + ly * c
            px, py = self.x + rx, self.y + ry
            pvx, pvy = self.vx - self.omega * ry, self.vy + self.omega * rx
            h = terrain.height(px)
            if py < h:
                nx, ny = terrain.normal(px)
                pen = (h - py) * ny
            else:
                hit = terrain.rock(px, py)
                if not hit:
                    continue
                nx, ny, pen = hit
            vn = pvx * nx + pvy * ny
            fn = HULL_K * pen - HULL_C * vn
            if fn <= 0:
                continue
            tx, ty = ny, -nx
            vt = pvx * tx + pvy * ty
            ft = -max(-HULL_MU * fn, min(HULL_MU * fn, HULL_FRICTION * vt))
            Fx, Fy = nx * fn + tx * ft, ny * fn + ty * ft
            fx += Fx
            fy += Fy
            tq += rx * Fy - ry * Fx
            hull_contact = True

        # Obstacles: parked cars and crate walls push back (you can drive on a car roof), all touches are recorded.
        for shape in shapes:
            solid = shape[-1]
            for w in self.wheels:
                hit = _push(shape, w.x, w.y, w.r)
                if not hit:
                    continue
                nx, ny, pen = hit
                self.touched.setdefault(shape[-2], (nx, ny))
                if not solid:
                    continue
                vn = w.vx * nx + w.vy * ny
                fn = GROUND_K * pen - GROUND_C * vn
                if fn > 0:
                    w.fx += fn * nx
                    w.fy += fn * ny
                    if not w.contact or fn > w.load:
                        w.contact, w.nx, w.ny, w.load = True, nx, ny, fn
            for lx, ly in self.HULL:
                rx, ry = lx * c - ly * s, lx * s + ly * c
                hit = _push(shape, self.x + rx, self.y + ry, 0.0)
                if not hit:
                    continue
                nx, ny, pen = hit
                self.touched.setdefault(shape[-2], (nx, ny))
                if not solid:
                    continue
                pvx, pvy = self.vx - self.omega * ry, self.vy + self.omega * rx
                vn = pvx * nx + pvy * ny
                fn = HULL_K * pen - HULL_C * vn
                if fn <= 0:
                    continue
                tx, ty = ny, -nx
                vt = pvx * tx + pvy * ty
                ft = -max(-HULL_MU * fn, min(HULL_MU * fn, HULL_FRICTION * vt))
                Fx, Fy = nx * fn + tx * ft, ny * fn + ty * ft
                fx += Fx
                fy += Fy
                tq += rx * Fy - ry * Fx
                hull_contact = True
        self.hull_contact = hull_contact

        # The driver's head: hitting the ground or a tunnel roof ends the run.
        hx, hy = self.HEAD[0] * c - self.HEAD[1] * s + self.x, self.HEAD[0] * s + self.HEAD[1] * c + self.y
        clearance = terrain.distance(hx, hy, self.HEAD_R + 0.6)[0] - self.HEAD_R
        hit = terrain.rock(hx, hy, self.HEAD_R)
        if hit:
            clearance = min(clearance, -hit[2])
        for shape in shapes:
            hit = _push(shape, hx, hy, self.HEAD_R)
            if hit:
                self.touched.setdefault(shape[-2], (hit[0], hit[1]))
                if shape[-1]:
                    clearance = min(clearance, -hit[2])
        self.head_clearance = clearance
        if clearance < 0:
            self.head_hit = True

        # In the air, gas tips the nose up and brake tips it down.
        if not any(w.contact for w in self.wheels) and not hull_contact:
            tq += (int(gas) - int(brake)) * self.air_torque

        # Integrate velocities.
        self.vx += fx * self.inv_m * dt
        self.vy += fy * self.inv_m * dt
        self.omega += tq * self.inv_i * dt
        self.omega *= 1.0 - (0.25 + water * 0.12) * dt
        for w in self.wheels:
            w.vx += w.fx * w.inv_m * dt
            w.vy += w.fy * w.inv_m * dt
            w.omega += w.tq * w.inv_i * dt
            w.omega *= 1.0 - (0.15 if w.contact else 0.6) * dt
            if drag and w.contact:
                w.omega *= 1.0 - drag * 0.55 * dt
                w.vx *= 1.0 - drag * 0.35 * dt
            if w.brake:
                dw = 2600.0 * st.get("gravity_scale", 1.0) * (w.m / 28.0) * w.inv_i * dt
                w.omega = 0.0 if abs(w.omega) <= dw else w.omega - math.copysign(dw, w.omega)

        # Tyre grip: an impulse that cancels contact-patch slip, capped by friction.
        mu = st["grip"] * grip_scale
        for w in self.wheels:
            if not w.contact:
                w.slip = 0.0
                continue
            tx, ty = w.ny, -w.nx
            rcx, rcy = -w.nx * w.r, -w.ny * w.r
            vcx = w.vx - w.omega * rcy
            vcy = w.vy + w.omega * rcx
            slip = vcx * tx + vcy * ty
            k_inv = w.inv_m + w.r * w.r * w.inv_i
            j = -slip / k_inv
            j_max = mu * w.load * dt
            j = max(-j_max, min(j_max, j))
            w.vx += j * tx * w.inv_m
            w.vy += j * ty * w.inv_m
            w.omega += w.r * j * w.inv_i
            w.slip = slip

        # Integrate positions.
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.omega * dt
        for w in self.wheels:
            w.x += w.vx * dt
            w.y += w.vy * dt
            w.angle += w.omega * dt

        drivers = [w for w in self.wheels if w.share > 0]
        spin = sum(-w.omega * w.share for w in drivers) / max(1e-6, sum(w.share for w in drivers))
        if st["thrust"] > 0:
            target = 0.25 + (0.75 if driving else 0.0) + (0.2 if boost else 0.0)
        else:
            target = min(1.0, abs(spin) / st["max_spin"]) * 0.85 + (0.15 if driving else 0.0)
        self.rpm += (min(1.0, target) - self.rpm) * min(1.0, dt * 8)


def _push(shape, px, py, r):
    """Push-out of a circle (radius r, 0 for a point) from a box or ball: (nx, ny, depth) or None."""
    if shape[0] == "ball":
        _, cx, cy, rad = shape[:4]
        dx, dy = px - cx, py - cy
        d = math.hypot(dx, dy)
        if d >= rad + r or d < 1e-9:
            return None
        return dx / d, dy / d, rad + r - d
    _, x0, y0, x1, y1 = shape[:5]
    if px < x0 - r or px > x1 + r or py < y0 - r or py > y1 + r:
        return None
    qx, qy = min(max(px, x0), x1), min(max(py, y0), y1)
    dx, dy = px - qx, py - qy
    d2 = dx * dx + dy * dy
    if d2 > 1e-12:
        if d2 >= r * r:
            return None
        d = math.sqrt(d2)
        return dx / d, dy / d, r - d
    pen, nx, ny = min(((px - x0 + r, -1.0, 0.0), (x1 - px + r, 1.0, 0.0), (py - y0 + r, 0.0, -1.0),
                       (y1 - py + r, 0.0, 1.0)))
    return nx, ny, pen


def rest_wheel_offsets(spec, stats):
    """Local wheel centres when the vehicle sits still on flat ground."""
    axs = [w[0] for w in spec["wheels"]]
    span = max(axs) - min(axs)
    out = []
    for ax, ay, r, m, share in spec["wheels"]:
        other = max(axs) if ax == min(axs) else min(axs)
        load = spec["mass"] * 9.8 * stats.get("gravity_scale", 1.0) * abs(other - 0.0) / span
        ext = spec["rest"] - load / stats["spring"]
        out.append((ax, ay - max(spec["ext"][0], ext), r))
    return out
