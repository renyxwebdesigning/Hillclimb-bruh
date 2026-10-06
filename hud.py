"""In-game heads-up display: distance, coins, pedals, gauges, pop-ups, repairs, races."""
import math

import pygame

import gfx
import sprites
from gfx import s, si

WHITE = (255, 255, 255)
INK = (28, 30, 34)


def _pedal(w, h, label, rows, cols):
    """Perforated steel pedal plate."""
    def draw(surf, k):
        W, H = surf.get_size()
        plate = pygame.Rect(0, 0, W, H)
        pygame.draw.rect(surf, (52, 54, 58), plate, border_radius=int(14 * k))
        inner = plate.inflate(-6 * k, -6 * k)
        grad = gfx.vgradient(inner.w, inner.h, (236, 238, 240), (150, 154, 160))
        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=int(11 * k))
        grad = grad.convert_alpha()
        grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(grad, inner.topleft)
        pygame.draw.rect(surf, (255, 255, 255), inner.inflate(-4 * k, -4 * k), max(1, int(1.5 * k)),
                         border_radius=int(10 * k))
        area = pygame.Rect(inner.x, inner.y + inner.h * 0.06, inner.w, inner.h * 0.66)
        r = min(area.w / cols, area.h / rows) * 0.36
        for i in range(rows):
            for j in range(cols):
                cx = area.x + area.w * (j + 0.5) / cols
                cy = area.y + area.h * (i + 0.5) / rows
                pygame.draw.circle(surf, (250, 250, 252), (cx, cy + r * 0.12), r * 1.12)
                pygame.draw.circle(surf, (44, 46, 50), (cx, cy), r)
                pygame.draw.circle(surf, (78, 80, 86), (cx, cy - r * 0.15), r * 0.72)
        t = gfx.font_px("cond", inner.h * 0.16).render(label, True, (52, 54, 60))
        surf.blit(t, t.get_rect(center=(inner.centerx, inner.y + inner.h * 0.85)))
    return gfx.supersample(w, h, draw)


def _gauge_face(r, label):
    def draw(surf, k):
        c = surf.get_width() / 2
        R = r * k
        pygame.draw.circle(surf, (30, 32, 36), (c, c), R)
        pygame.draw.circle(surf, (96, 100, 108), (c, c), R * 0.95)
        pygame.draw.circle(surf, (64, 68, 74), (c, c), R * 0.9)
        pygame.draw.circle(surf, (78, 82, 90), (c, c - R * 0.06), R * 0.82)
        for i in range(11):
            a = math.radians(225 - i * 27)
            red = i >= 8
            r0 = R * (0.62 if i % 2 == 0 else 0.7)
            p0 = (c + math.cos(a) * r0, c - math.sin(a) * r0)
            p1 = (c + math.cos(a) * R * 0.8, c - math.sin(a) * R * 0.8)
            pygame.draw.line(surf, (226, 40, 40) if red else (236, 238, 242), p0, p1,
                             max(1, int(R * (0.05 if i % 2 == 0 else 0.03))))
        t = gfx.font_px("cond_i", R * 0.3).render(label, True, (228, 40, 40))
        surf.blit(t, t.get_rect(center=(c, c + R * 0.52)))
    d = 2 * r + 2
    return gfx.supersample(d, d, draw)


def _boost_button(r, lit):
    def draw(surf, k):
        c = surf.get_width() / 2
        R = r * k
        pygame.draw.circle(surf, (24, 26, 30), (c, c + R * 0.06), R)
        pygame.draw.circle(surf, (255, 150, 30) if lit else (70, 74, 80), (c, c), R)
        pygame.draw.circle(surf, (255, 196, 70) if lit else (92, 96, 104), (c, c), R * 0.84)
        flame = [(0.0, -0.62), (0.3, -0.1), (0.18, 0.0), (0.34, 0.42), (0.0, 0.6), (-0.34, 0.42),
                 (-0.18, 0.0), (-0.3, -0.1)]
        pygame.draw.polygon(surf, (255, 255, 255) if lit else (220, 224, 230),
                            [(c + x * R * 0.75, c - y * R * 0.75 - R * 0.08) for x, y in flame])
        t = gfx.font_px("cond", R * 0.36).render("BOOST", True, (40, 30, 20) if lit else (40, 42, 48))
        surf.blit(t, t.get_rect(center=(c, c + R * 0.62)))
    return gfx.supersample(2 * r + 2, 2 * r + 2, draw)


def _pause_icon(r):
    def draw(surf, k):
        c = surf.get_width() / 2
        R = r * k
        pygame.draw.circle(surf, (24, 26, 30), (c, c + R * 0.06), R)
        pygame.draw.circle(surf, (66, 70, 76), (c, c), R)
        pygame.draw.circle(surf, (50, 54, 60), (c, c + R * 0.05), R * 0.86)
        for dx in (-0.22, 0.22):
            pygame.draw.rect(surf, (250, 250, 250),
                             pygame.Rect(c + dx * R - R * 0.11, c - R * 0.38, R * 0.22, R * 0.76),
                             border_radius=int(R * 0.06))
    return gfx.supersample(2 * r + 2, 2 * r + 2, draw)


def _fuel_icon(h):
    def draw(surf, k):
        W, H = surf.get_size()
        red, dk = (226, 40, 38), (120, 16, 18)
        pygame.draw.rect(surf, dk, (W * 0.05, H * 0.12, W * 0.62, H * 0.86), border_radius=int(W * 0.1))
        pygame.draw.rect(surf, red, (W * 0.12, H * 0.18, W * 0.48, H * 0.74), border_radius=int(W * 0.08))
        pygame.draw.rect(surf, (250, 250, 250), (W * 0.2, H * 0.26, W * 0.32, H * 0.22), border_radius=int(W * 0.04))
        pygame.draw.lines(surf, dk, False, [(W * 0.66, H * 0.4), (W * 0.88, H * 0.48), (W * 0.88, H * 0.8),
                                             (W * 0.78, H * 0.86)], max(1, int(W * 0.09)))
    return gfx.supersample(h * 0.8, h, draw)


def _ruler_icon(h):
    def draw(surf, k):
        W, H = surf.get_size()
        pygame.draw.polygon(surf, (250, 250, 250), [(W * 0.08, H * 0.8), (W * 0.72, H * 0.08),
                                                    (W * 0.94, H * 0.3), (W * 0.3, H * 0.98)])
        pygame.draw.polygon(surf, INK, [(W * 0.08, H * 0.8), (W * 0.72, H * 0.08),
                                        (W * 0.94, H * 0.3), (W * 0.3, H * 0.98)], max(1, int(W * 0.06)))
        for i in range(1, 6):
            f = i / 6
            x, y = W * (0.08 + 0.64 * f), H * (0.8 - 0.72 * f)
            pygame.draw.line(surf, INK, (x, y), (x + W * 0.1, y + H * 0.1), max(1, int(W * 0.05)))
    return gfx.supersample(h, h, draw)


def _horn_button(r, kind):
    def draw(surf, k):
        c = surf.get_width() / 2
        R = r * k
        pygame.draw.circle(surf, (24, 26, 30), (c, c + R * 0.06), R)
        pygame.draw.circle(surf, (70, 74, 80), (c, c), R)
        pygame.draw.circle(surf, (92, 96, 104), (c, c), R * 0.84)
        ink = (236, 238, 242)
        if kind == "puppy":       # paw print
            pygame.draw.ellipse(surf, ink, (c - R * 0.32, c - R * 0.02, R * 0.64, R * 0.5))
            for dx, dy in ((-0.38, -0.22), (-0.13, -0.42), (0.13, -0.42), (0.38, -0.22)):
                pygame.draw.circle(surf, ink, (c + dx * R, c + dy * R), R * 0.13)
        else:                     # anchor
            w = max(1, int(R * 0.11))
            pygame.draw.line(surf, ink, (c, c - R * 0.5), (c, c + R * 0.42), w)
            pygame.draw.circle(surf, ink, (c, c - R * 0.52), R * 0.12, w)
            pygame.draw.line(surf, ink, (c - R * 0.26, c - R * 0.22), (c + R * 0.26, c - R * 0.22), w)
            pygame.draw.arc(surf, ink, (c - R * 0.46, c - R * 0.1, R * 0.92, R * 0.6), math.pi * 1.05, math.pi * 1.95, w)
        t = gfx.font_px("cond", R * 0.3).render("HORN", True, (40, 42, 48))
        surf.blit(t, t.get_rect(center=(c, c + R * 0.66)))
    return gfx.supersample(2 * r + 2, 2 * r + 2, draw)


def _wrench(h):
    def draw(surf, k):
        W, H = surf.get_size()
        col = (200, 206, 214)
        pygame.draw.line(surf, col, (W * 0.25, H * 0.75), (W * 0.62, H * 0.38), max(1, int(W * 0.14)))
        pygame.draw.circle(surf, col, (W * 0.68, H * 0.32), W * 0.2)
        pygame.draw.circle(surf, (0, 0, 0, 0), (W * 0.78, H * 0.22), W * 0.12)
        pygame.draw.circle(surf, col, (W * 0.25, H * 0.75), W * 0.08)
    return gfx.supersample(h, h, draw)


class Popup:
    def __init__(self, title, amount):
        self.title, self.amount, self.t = title, amount, 0.0


class Hud:
    def __init__(self):
        self.brake_img = _pedal(s(128), s(118), "BRAKE", 2, 3)
        self.gas_img = _pedal(s(104), s(126), "GAS", 3, 2)
        self.rpm_face = _gauge_face(s(60), "RPM")
        self.boost_face = _gauge_face(s(60), "boost")
        self.boost_btn = {lit: _boost_button(s(38), lit) for lit in (False, True)}
        self.horn_btn = {k: _horn_button(s(34), k) for k in ("puppy", "ship")}
        self.wrench = _wrench(s(70))
        self.pause_img = _pause_icon(s(27))
        self.ruler_img = _ruler_icon(s(24))
        self.coin_img = sprites.coin(5, si(13))
        self.popups = []
        self.notices = []
        W, H = gfx.W, gfx.H
        self.brake_rect = self.brake_img.get_rect(bottomleft=(s(26), H - s(34)))
        self.gas_rect = self.gas_img.get_rect(bottomright=(W - s(26), H - s(34)))
        self.pause_rect = self.pause_img.get_rect(topright=(W - s(18), s(14)))
        self.boost_rect = self.boost_btn[False].get_rect(center=(self.gas_rect.centerx - s(8), self.gas_rect.top - s(64)))
        self.horn_rect = self.horn_btn["puppy"].get_rect(center=(self.brake_rect.centerx, self.brake_rect.top - s(60)))
        self.fix_rect = pygame.Rect(0, 0, s(500), s(196))
        self.fix_rect.midtop = (W / 2, s(84))

    def bonus(self, title, amount):
        self.popups.append(Popup(title, amount))

    def notice(self, text, color):
        self.notices.append([text, color, 0.0])

    def clear(self):
        self.popups.clear()
        self.notices.clear()

    def update(self, dt):
        for p in self.popups:
            p.t += dt
        self.popups = [p for p in self.popups if p.t < 2.0]
        for n in self.notices:
            n[2] += dt
        self.notices = [n for n in self.notices if n[2] < 1.6]

    # --------------------------------------------------------------- drawing
    def draw(self, surf, run, gas, brake, now, race=None):
        self._draw_info(surf, run, race)
        surf.blit(self.boost_btn[run.boosting], self.boost_rect)
        surf.blit(self.horn_btn[run.horn_kind], self.horn_rect)
        if run.time < 7 and run.state == "drive" and run.countdown <= 0 and not run.seized:
            a = int(255 * min(1.0, (7 - run.time) / 1.0))
            img = gfx.text("cond_i", 22, "SPACE boost  ·  H horn  ·  L lights  ·  ENTER fixes a seized engine",
                           WHITE, outline=INK, width=2).copy()
            img.set_alpha(a)
            surf.blit(img, img.get_rect(center=(gfx.W / 2, s(150))))
        surf.blit(self.pause_img, self.pause_rect)
        self._draw_pedal(surf, self.brake_img, self.brake_rect, brake)
        self._draw_pedal(surf, self.gas_img, self.gas_rect, gas)
        cx = gfx.W / 2
        by = gfx.H - s(68)
        self._gauge(surf, self.rpm_face, (cx - s(76), by), run.car.rpm if run.car.engine_on else 0.0)
        if run.boosting:
            glow = 0.5 + 0.5 * math.sin(now * 20)
            pygame.draw.circle(surf, gfx.mix((255, 120, 20), (255, 220, 80), glow), (cx + s(76), by), s(64))
        self._gauge(surf, self.boost_face, (cx + s(76), by), run.boost)
        self._draw_popups(surf)
        if run.seized and run.state == "drive":
            self._draw_seized(surf, run, now)
        if run.countdown > 0:
            n = math.ceil(run.countdown - 0.4)
            label = str(n) if n > 0 else "GO!"
            k = (run.countdown - 0.4) % 1.0 if n > 0 else (run.countdown / 0.4)
            img = gfx.text("black_i", 120, label, (255, 220, 60) if n > 0 else (120, 240, 90),
                           outline=INK, width=5, shadow=5)
            img = pygame.transform.smoothscale_by(img, 0.8 + 0.4 * k)
            surf.blit(img, img.get_rect(center=(gfx.W / 2, gfx.H * 0.38)))
        for i, (text, color, t) in enumerate(self.notices[-2:]):
            k = min(1.0, t / 0.2)
            img = gfx.text("black_i", 64, text, color, outline=INK, width=4, shadow=4)
            img = pygame.transform.smoothscale_by(img, 1.4 - 0.4 * k).copy()
            img.set_alpha(int(255 * min(1.0, (1.6 - t) / 0.4)))
            surf.blit(img, img.get_rect(center=(gfx.W / 2, gfx.H * 0.3 + i * s(80))))

    def _draw_seized(self, surf, run, now):
        r = self.fix_rect.move(math.sin(now * 40) * s(3) if run.fix_shake > 0 else 0, 0)
        box = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (20, 18, 18, 215), box.get_rect(), border_radius=si(18))
        pygame.draw.rect(box, (230, 50, 40, 255), box.get_rect(), si(4), border_radius=si(18))
        surf.blit(box, r)
        pulse = 1 + 0.06 * math.sin(now * 10)
        title = pygame.transform.smoothscale_by(
            gfx.text("black_i", 50, "KOLBENKLEMMER!", (255, 70, 50), outline=INK, width=3), pulse)
        surf.blit(title, title.get_rect(center=(r.centerx, r.y + s(46))))
        gfx.blit_text(surf, "cond", 24, "Hammer ENTER to fix the engine!", WHITE, (r.centerx, r.y + s(100)), "center")
        ang = -30 + (40 if run.fix_shake > 0 else 0) + 6 * math.sin(now * 6)
        w = pygame.transform.rotozoom(self.wrench, ang, 1.0)
        surf.blit(w, w.get_rect(center=(r.x + s(70), r.y + s(150))))
        gfx.blit_text(surf, "cond", 30, f"Hits: {run.fix_count}", (255, 220, 80), (r.centerx, r.y + s(150)), "center",
                      outline=INK, width=2)
        gfx.blit_text(surf, "cond_i", 17, "(how many? nobody knows...)", (190, 190, 196),
                      (r.centerx, r.y + s(182)), "center")

    def _draw_info(self, surf, run, race):
        x, y = s(16), s(12)
        surf.blit(self.ruler_img, (x, y + s(2)))
        if race:
            line = f"{run.distance}m  of  {race['distance']}m"
        else:
            line = f"{run.distance}m  (best: {max(run.best, run.distance)}m)"
        gfx.blit_text(surf, "cond", 22, line, WHITE, (x + s(32), y - s(1)), outline=INK, width=2)
        y += s(34)
        surf.blit(self.coin_img, (x + s(1), y))
        gfx.blit_text(surf, "cond", 22, gfx.fmt(run.bank + run.coins), WHITE, (x + s(32), y - s(2)),
                      outline=INK, width=2)
        if race:
            self._draw_race(surf, run, race)

    def _draw_race(self, surf, run, race):
        bar = pygame.Rect(0, 0, s(520), s(12))
        bar.midtop = (gfx.W / 2, s(22))
        pygame.draw.rect(surf, INK, bar.inflate(s(6), s(6)), border_radius=si(8))
        pygame.draw.rect(surf, (90, 94, 100), bar, border_radius=si(6))
        flag = pygame.Rect(bar.right - s(4), bar.y - s(8), s(14), s(28))
        for i in range(4):
            for j in range(2):
                pygame.draw.rect(surf, (250, 250, 250) if (i + j) % 2 else (30, 30, 34),
                                 (flag.x + j * s(7), flag.y + i * s(7), s(7), s(7)))
        for p in sorted(race["players"], key=lambda p: p["me"]):
            f = max(0.0, min(1.0, p["dist"] / race["distance"]))
            cx = bar.x + bar.w * f
            pygame.draw.circle(surf, INK, (cx, bar.centery), s(11 if p["me"] else 9))
            pygame.draw.circle(surf, p["color"], (cx, bar.centery), s(8 if p["me"] else 6))
        gfx.blit_text(surf, "black_i", 30, f"POS {race['pos']}/{len(race['players'])}", WHITE,
                      (bar.right + s(60), bar.centery), "midleft", outline=INK, width=2)
        if run.mode == "race":
            t = run.finished_at if run.finished_at is not None else run.race_time
            gfx.blit_text(surf, "cond", 22, f"{t:5.1f}s", WHITE, (bar.x - s(16), bar.centery), "midright",
                          outline=INK, width=2)

    def _draw_pedal(self, surf, img, rect, pressed):
        post = pygame.Rect(0, 0, s(20), gfx.H - rect.bottom + s(10))
        post.midtop = (rect.centerx, rect.bottom - s(10))
        pygame.draw.rect(surf, (40, 42, 46), post)
        pygame.draw.rect(surf, (88, 92, 98), post.inflate(-s(8), 0))
        if pressed:
            sq = pygame.transform.smoothscale(img, (int(img.get_width() * 0.96), int(img.get_height() * 0.84)))
            r = sq.get_rect(midbottom=(rect.centerx, rect.bottom + s(6)))
            surf.blit(sq, r)
            shade = pygame.Surface(r.size, pygame.SRCALPHA)
            shade.fill((0, 0, 0, 70))
            shade.blit(sq, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(shade, r)
        else:
            surf.blit(img, rect)

    @staticmethod
    def _gauge(surf, face, centre, value):
        r = face.get_rect(center=centre)
        surf.blit(face, r)
        R = face.get_width() / 2
        a = math.radians(225 - max(0.0, min(1.0, value)) * 270)
        tip = (centre[0] + math.cos(a) * R * 0.78, centre[1] - math.sin(a) * R * 0.78)
        side = (math.cos(a + math.pi / 2) * R * 0.05, -math.sin(a + math.pi / 2) * R * 0.05)
        tail = (centre[0] - math.cos(a) * R * 0.16, centre[1] + math.sin(a) * R * 0.16)
        pygame.draw.polygon(surf, (196, 26, 26), [tip, (tail[0] + side[0], tail[1] + side[1]),
                                                  (tail[0] - side[0], tail[1] - side[1])])
        pygame.draw.circle(surf, (30, 32, 36), centre, R * 0.12)
        pygame.draw.circle(surf, (120, 124, 132), centre, R * 0.06)

    def _draw_popups(self, surf):
        base_y = gfx.H * 0.24
        for i, p in enumerate(self.popups[-3:]):
            t = p.t
            pop = 1 + 0.35 * max(0.0, 1 - t / 0.16)
            alpha = 255 if t < 1.4 else int(255 * max(0.0, 1 - (t - 1.4) / 0.6))
            rise = s(30) * max(0.0, t - 1.0)
            cx, cy = gfx.W * 0.6, base_y + i * s(104) - rise
            for txt, size, dy in ((p.title, 40, 0), (f"+{gfx.fmt(p.amount)}", 48, s(46))):
                img = gfx.text("cond_i", size, txt, WHITE, outline=INK, width=2.5, shadow=2)
                if pop != 1:
                    img = pygame.transform.smoothscale_by(img, pop)
                if alpha < 255:
                    img = img.copy()
                    img.set_alpha(alpha)
                surf.blit(img, img.get_rect(center=(cx, cy + dy)))

    def draw_banner(self, surf, text, color, t):
        """Big end-of-run banner that slams in."""
        k = min(1.0, t / 0.25)
        scale = 1.6 - 0.6 * (1 - (1 - k) ** 3)
        img = gfx.text("black_i", 76, text, color, outline=INK, width=4, shadow=4)
        img = pygame.transform.smoothscale_by(img, scale)
        img.set_alpha(int(255 * k))
        surf.blit(img, img.get_rect(center=(gfx.W / 2, gfx.H * 0.36)))

    def hit(self, pos, seized=False):
        if seized and self.fix_rect.collidepoint(pos):
            return "repair"
        if self.pause_rect.inflate(s(16), s(16)).collidepoint(pos):
            return "pause"
        if self.boost_rect.inflate(s(10), s(10)).collidepoint(pos):
            return "boost"
        if self.horn_rect.inflate(s(10), s(10)).collidepoint(pos):
            return "horn"
        if self.gas_rect.inflate(s(30), s(40)).collidepoint(pos) or pos[0] > gfx.W * 0.62 and pos[1] > gfx.H * 0.45:
            return "gas"
        if self.brake_rect.inflate(s(30), s(40)).collidepoint(pos) or pos[0] < gfx.W * 0.38 and pos[1] > gfx.H * 0.45:
            return "brake"
        return None
