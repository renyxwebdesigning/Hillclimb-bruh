"""Menu screens: stage select, vehicle select, garage, results and pause."""
import math

import pygame

import gfx
from config import RACE_DISTANCES, STAGES, TITLE, UPGRADES, VEHICLES, rating, upgrade_cost, vehicle_stats
from drivers import DRIVERS
from gfx import s, si
from physics import rest_wheel_offsets
from render import compose_vehicle

WHITE = (255, 255, 255)
INK = (24, 26, 30)
GOLD = (255, 204, 48)
MUTED = (176, 196, 228)
HINT = (200, 220, 252)
NAVY = (12, 28, 64)                       # outlines and dark ink
PANEL, PANEL_EDGE = (20, 46, 98), (86, 148, 232)
BG_TOP, BG_BOTTOM = (46, 140, 232), (18, 62, 150)

# top colour, bottom colour, the darker "lip" under the button, text colour
BUTTON_STYLES = {
    "green": ((150, 236, 80), (58, 170, 36), (28, 104, 20), WHITE),
    "gray": ((255, 255, 255), (206, 220, 240), (120, 140, 176), NAVY),
    "red": ((255, 132, 104), (220, 52, 40), (130, 24, 18), WHITE),
    "blue": ((120, 200, 255), (38, 118, 230), (18, 64, 156), WHITE),
    "yellow": ((255, 230, 96), (255, 170, 20), (180, 96, 8), WHITE),
}


# ------------------------------------------------------------------ widgets
class Button:
    def __init__(self, label, center, size, style="gray", icon=None, slant=16, key=None):
        self.label, self.style, self.icon, self.key = label, style, icon, key
        self.rect = pygame.Rect(0, 0, s(size[0]), s(size[1]))
        self.rect.center = center
        self.slant = s(slant)
        self._img = {}

    def _render(self, hover, down):
        """Chunky rounded button with a dark lip underneath (pressed = lip squashed)."""
        top, bottom, lip, ink = BUTTON_STYLES[self.style]
        if hover:
            top, bottom = gfx.shade(top, 1.06), gfx.shade(bottom, 1.08)
        w, h = self.rect.w, self.rect.h
        lip_h = h * (0.06 if down else 0.13)

        def draw(surf, k):
            W, H = w * k, h * k
            rad = int(min(H * 0.32, 18 * gfx.U * k))
            body = pygame.Rect(0, H * 0.13 - lip_h * k, W, H - H * 0.13)
            pygame.draw.rect(surf, NAVY, pygame.Rect(0, body.y, W, H - body.y), border_radius=rad)
            inner = pygame.Rect(3 * gfx.U * k, body.y + 3 * gfx.U * k, W - 6 * gfx.U * k, H - body.y - 6 * gfx.U * k)
            pygame.draw.rect(surf, lip, inner, border_radius=rad)
            face = pygame.Rect(inner.x, inner.y, inner.w, inner.h - lip_h * k)
            grad = gfx.vgradient(face.w, face.h, top, bottom).convert_alpha()
            mask = pygame.Surface(face.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=rad)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(grad, face.topleft)
            gloss = pygame.Surface((face.w, face.h * 0.42), pygame.SRCALPHA)
            pygame.draw.rect(gloss, (255, 255, 255, 70), gloss.get_rect().inflate(-8 * gfx.U * k, 0).move(0, 3 * gfx.U * k),
                             border_radius=rad)
            surf.blit(gloss, face.topleft)
        img = gfx.supersample(w, h, draw, ss=2)
        size = 28 if h > s(56) else 24
        lab = gfx.text("black_i", size, self.label, ink, outline=NAVY if ink == WHITE else None, width=2.5)
        if lab.get_width() > w - s(28):
            lab = pygame.transform.smoothscale_by(lab, (w - s(28)) / lab.get_width())
        cy = h * 0.13 - lip_h + (h - h * 0.13 - lip_h) / 2
        x = w / 2 - lab.get_width() / 2
        if self.icon:
            ic = self.icon
            x = w / 2 - (lab.get_width() + ic.get_width() + s(12)) / 2
            img.blit(ic, (x, cy - ic.get_height() / 2))
            x += ic.get_width() + s(12)
        img.blit(lab, (x, cy - lab.get_height() / 2))
        return img

    def draw(self, surf, mouse, pressed=False):
        hover = self.rect.collidepoint(mouse)
        key = (hover, pressed and hover)
        if key not in self._img:
            self._img[key] = self._render(*key)
        surf.blit(self._img[key], self.rect)

    def hit(self, pos):
        return self.rect.collidepoint(pos)


def background(w, h):
    """Bright blue backdrop with soft light rays from the top, like a modern mobile game menu."""
    bg = gfx.opaque(gfx.vgradient(w, h, BG_TOP, BG_BOTTOM))
    rays = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, -h * 0.25
    n = 18
    reach = math.hypot(w, h) * 1.4
    for i in range(n):
        a0 = math.pi * (i / n)
        a1 = a0 + math.pi / n * 0.5
        pygame.draw.polygon(rays, (255, 255, 255, 13), [(cx, cy), (cx + math.cos(a0) * reach, cy + math.sin(a0) * reach),
                                                        (cx + math.cos(a1) * reach, cy + math.sin(a1) * reach)])
    bg.blit(rays, (0, 0))
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (160, 220, 255, 40), (w * 0.15, -h * 0.35, w * 0.7, h * 0.7))
    bg.blit(glow, (0, 0))
    bottom = gfx.vgradient(w, int(h * 0.35), (8, 20, 60, 0), (8, 20, 60, 110)).convert_alpha()
    bg.blit(bottom, (0, h - bottom.get_height()))
    return bg


def glass(surf, rect, radius=18, selected=False, hover=False, fill=PANEL):
    """Rounded dark-blue glass panel with a soft shadow; gold rim when selected."""
    r = pygame.Rect(rect)
    sh = pygame.Surface((r.w + s(16), r.h + s(16)), pygame.SRCALPHA)
    pygame.draw.rect(sh, (6, 16, 44, 90), sh.get_rect().inflate(-s(8), -s(8)).move(0, s(5)),
                     border_radius=si(radius + 4))
    surf.blit(sh, (r.x - s(8), r.y - s(8)))
    if selected:
        glow = pygame.Surface((r.w + s(14), r.h + s(14)), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 220, 80, 150), glow.get_rect(), si(5), border_radius=si(radius + 6))
        surf.blit(glow, (r.x - s(7), r.y - s(7)))
    body = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(body, (*fill, 232), body.get_rect(), border_radius=si(radius))
    hi = gfx.vgradient(r.w, max(1, r.h // 3), (255, 255, 255, 26), (255, 255, 255, 0)).convert_alpha()
    mask = pygame.Surface(hi.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, r.w, r.h), border_radius=si(radius))
    hi.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    body.blit(hi, (0, 0))
    surf.blit(body, r)
    edge = GOLD if selected else (gfx.shade(PANEL_EDGE, 1.2) if hover else PANEL_EDGE)
    pygame.draw.rect(surf, edge, r, si(4) if selected else si(2), border_radius=si(radius))
    if selected:
        c = (r.right - s(6), r.y + s(6))
        pygame.draw.circle(surf, NAVY, c, s(15))
        pygame.draw.circle(surf, GOLD, c, s(12))
        pygame.draw.lines(surf, NAVY, False, [(c[0] - s(6), c[1]), (c[0] - s(1), c[1] + s(5)), (c[0] + s(7), c[1] - s(5))],
                          max(2, si(3)))


def pill(surf, rect, fill=(10, 30, 72, 200)):
    p = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(p, fill, p.get_rect(), border_radius=rect.h // 2)
    surf.blit(p, rect)
    pygame.draw.rect(surf, (80, 140, 220), rect, max(1, si(2)), border_radius=rect.h // 2)


def round_button(surf, img, center):
    r = pygame.Rect(0, 0, s(48), s(48))
    r.center = center
    pygame.draw.circle(surf, NAVY, (r.centerx, r.centery + s(3)), s(24))
    pygame.draw.circle(surf, (38, 96, 190), r.center, s(23))
    pygame.draw.circle(surf, (70, 140, 230), (r.centerx, r.centery - s(2)), s(20))
    surf.blit(img, img.get_rect(center=r.center))
    return r


def top_bar(surf, app, title):
    """Coin counter pill on the left, big title in the middle, round icon buttons on the right."""
    bar = pygame.Rect(0, 0, gfx.W, s(70))
    shade = gfx.vgradient(gfx.W, bar.h, (8, 24, 70, 150), (8, 24, 70, 0)).convert_alpha()
    surf.blit(shade, (0, 0))
    coins = gfx.text("heavy", 28, gfx.fmt(app.data["coins"]), WHITE, outline=NAVY, width=2)
    cp = pygame.Rect(s(18), 0, coins.get_width() + app.coin_icon.get_width() + s(44), s(44))
    cp.centery = bar.centery
    pill(surf, cp)
    surf.blit(app.coin_icon, app.coin_icon.get_rect(midleft=(cp.x + s(8), cp.centery)))
    surf.blit(coins, coins.get_rect(midleft=(cp.x + app.coin_icon.get_width() + s(18), cp.centery)))
    head = gfx.text("black_i", 36, title, WHITE, outline=NAVY, width=3, shadow=3)
    room = gfx.W - 2 * s(430)                  # between the coin pill and the icons on the right
    if head.get_width() > room:
        head = pygame.transform.smoothscale_by(head, room / head.get_width())
    surf.blit(head, head.get_rect(center=(gfx.W / 2, bar.centery)))
    x = gfx.W - s(42)
    app.sound_rect = round_button(surf, app.speaker[app.data["sound"]], (x, bar.centery))
    x -= s(60)
    app.music_rect = round_button(surf, app.note[app.data["music"]], (x, bar.centery))
    left = app.music_rect.left
    if app.fs_available():
        x -= s(60)
        app.fs_rect = round_button(surf, app.fs_icon[app.is_fullscreen()], (x, bar.centery))
        left = app.fs_rect.left
    relay = getattr(app, "relay", None)
    if relay is not None:
        tag = gfx.text("heavy", 20, f"#{app.data['player_id']}", GOLD)
        tp = pygame.Rect(0, 0, tag.get_width() + s(44), s(36))
        tp.midright = (left - s(14), bar.centery)
        pill(surf, tp)
        pygame.draw.circle(surf, (90, 220, 70) if relay.online else (230, 160, 40), (tp.x + s(16), tp.centery), s(6))
        surf.blit(tag, tag.get_rect(midleft=(tp.x + s(28), tp.centery)))


def toggles_hit(app, pos):
    if app.sound_rect and app.sound_rect.inflate(s(10), s(10)).collidepoint(pos):
        app.toggle_sound()
        return True
    if app.music_rect and app.music_rect.inflate(s(10), s(10)).collidepoint(pos):
        app.toggle_music()
        return True
    if app.fs_rect and app.fs_rect.inflate(s(10), s(10)).collidepoint(pos):
        app.toggle_fullscreen()
        return True
    return False


def speaker_icons(h):
    out = {}
    for on in (True, False):
        def draw(surf, k, on=on):
            W, H = surf.get_size()
            col = (236, 238, 242)
            pygame.draw.polygon(surf, col, [(W * 0.08, H * 0.36), (W * 0.26, H * 0.36), (W * 0.5, H * 0.12),
                                            (W * 0.5, H * 0.88), (W * 0.26, H * 0.64), (W * 0.08, H * 0.64)])
            if on:
                for r in (0.22, 0.38):
                    rect = pygame.Rect(W * 0.5 - W * r, H * 0.5 - H * r, W * r * 2, H * r * 2)
                    pygame.draw.arc(surf, col, rect, -0.9, 0.9, max(1, int(W * 0.07)))
            else:
                _cross(surf, W, H)
        out[on] = gfx.supersample(h * 1.1, h, draw)
    return out


def note_icons(h):
    out = {}
    for on in (True, False):
        def draw(surf, k, on=on):
            W, H = surf.get_size()
            col = (236, 238, 242)
            pygame.draw.ellipse(surf, col, (W * 0.06, H * 0.66, W * 0.3, H * 0.24))
            pygame.draw.ellipse(surf, col, (W * 0.4, H * 0.56, W * 0.3, H * 0.24))
            pygame.draw.line(surf, col, (W * 0.33, H * 0.78), (W * 0.33, H * 0.14), max(1, int(W * 0.07)))
            pygame.draw.line(surf, col, (W * 0.67, H * 0.68), (W * 0.67, H * 0.06), max(1, int(W * 0.07)))
            pygame.draw.polygon(surf, col, [(W * 0.3, H * 0.12), (W * 0.7, H * 0.02), (W * 0.7, H * 0.2), (W * 0.3, H * 0.3)])
            if not on:
                _cross(surf, W, H, 0.7)
        out[on] = gfx.supersample(h * 1.1, h, draw)
    return out


def fullscreen_icons(h):
    """Four corner brackets: pointing out (go fullscreen) or in (leave fullscreen)."""
    out = {}
    for on in (False, True):
        def draw(surf, k, on=on):
            W, H = surf.get_size()
            col, lw = (236, 238, 242), max(2, int(W * 0.11))
            a, b = (0.1, 0.4) if not on else (0.36, 0.06)    # corner point, arm end
            for sx in (0, 1):
                for sy in (0, 1):
                    fx = (lambda v: v) if sx == 0 else (lambda v: 1 - v)
                    fy = (lambda v: v) if sy == 0 else (lambda v: 1 - v)
                    c = (fx(a) * W, fy(a) * H)
                    pygame.draw.lines(surf, col, False, [(fx(b) * W, c[1]), c, (c[0], fy(b) * H)], lw)
        out[on] = gfx.supersample(h, h, draw)
    return out


def _cross(surf, W, H, x0=0.62):
    for a, b in (((x0, 0.3), (0.96, 0.7)), ((0.96, 0.3), (x0, 0.7))):
        pygame.draw.line(surf, (236, 70, 60), (W * a[0], H * a[1]), (W * b[0], H * b[1]), max(1, int(W * 0.1)))


def checker_icon(h):
    def draw(surf, k):
        W, H = surf.get_size()
        pygame.draw.line(surf, (40, 40, 44), (W * 0.1, H * 0.05), (W * 0.1, H), max(1, int(W * 0.08)))
        fw, fh = W * 0.85 / 4, H * 0.62 / 3
        for i in range(4):
            for j in range(3):
                col = (30, 30, 34) if (i + j) % 2 else (255, 255, 255)
                pygame.draw.rect(surf, col, (W * 0.14 + i * fw, H * 0.05 + j * fh, fw + 1, fh + 1))
    return gfx.supersample(h, h, draw)


def upgrade_icon(key, size):
    dark, mid = (58, 62, 70), (120, 126, 136)

    def piston(surf, cx, cy, ang, scale):
        c, sn = math.cos(ang), math.sin(ang)

        def P(x, y):
            return (cx + (x * c - y * sn) * scale, cy - (x * sn + y * c) * scale)
        pygame.draw.polygon(surf, dark, [P(-0.2, 0.5), P(0.2, 0.5), P(0.2, 0.18), P(-0.2, 0.18)])
        for y in (0.42, 0.34):
            pygame.draw.line(surf, mid, P(-0.2, y), P(0.2, y), max(1, int(0.03 * scale)))
        pygame.draw.line(surf, dark, P(0, 0.2), P(0, -0.32), max(1, int(0.12 * scale)))
        pygame.draw.circle(surf, dark, P(0, -0.36), 0.12 * scale)
        pygame.draw.circle(surf, (250, 250, 250), P(0, -0.36), 0.05 * scale)

    def draw(surf, k):
        W, H = surf.get_size()
        cx, cy, sc = W / 2, H / 2, min(W, H) * 0.9
        if key == "engine":
            piston(surf, cx, cy, math.radians(38), sc)
            piston(surf, cx, cy, math.radians(-38), sc)
        elif key == "suspension":
            ang = math.radians(-35)
            dx, dy = math.cos(ang), -math.sin(ang)
            a = (cx - dx * sc * 0.42, cy - dy * sc * 0.42)
            b = (cx + dx * sc * 0.42, cy + dy * sc * 0.42)
            pygame.draw.line(surf, dark, a, b, max(1, int(sc * 0.1)))
            px, py = -dy, dx
            pts = []
            for i in range(15):
                f = 0.12 + 0.76 * i / 14
                side = sc * 0.14 * (1 if i % 2 else -1)
                pts.append((a[0] + (b[0] - a[0]) * f + px * side, a[1] + (b[1] - a[1]) * f + py * side))
            pygame.draw.lines(surf, mid, False, pts, max(1, int(sc * 0.06)))
            for p in (a, b):
                pygame.draw.circle(surf, dark, p, sc * 0.09)
                pygame.draw.circle(surf, (250, 250, 250), p, sc * 0.04)
        elif key == "tires":
            pygame.draw.circle(surf, dark, (cx, cy), sc * 0.44)
            for i in range(16):
                a = i * math.tau / 16
                pygame.draw.circle(surf, dark, (cx + math.cos(a) * sc * 0.44, cy + math.sin(a) * sc * 0.44), sc * 0.05)
            pygame.draw.circle(surf, (40, 42, 48), (cx, cy), sc * 0.34)
            pygame.draw.circle(surf, (200, 204, 210), (cx, cy), sc * 0.2)
            for i in range(5):
                a = i * math.tau / 5
                pygame.draw.circle(surf, dark, (cx + math.cos(a) * sc * 0.12, cy + math.sin(a) * sc * 0.12), sc * 0.035)
        else:  # boost: a nozzle with a flame
            pygame.draw.polygon(surf, (255, 140, 30), [(cx - sc * 0.05, cy - sc * 0.16), (cx - sc * 0.5, cy),
                                                       (cx - sc * 0.05, cy + sc * 0.16)])
            pygame.draw.polygon(surf, (255, 210, 60), [(cx - sc * 0.05, cy - sc * 0.09), (cx - sc * 0.34, cy),
                                                       (cx - sc * 0.05, cy + sc * 0.09)])
            pygame.draw.polygon(surf, dark, [(cx, cy - sc * 0.2), (cx + sc * 0.42, cy - sc * 0.13),
                                             (cx + sc * 0.42, cy + sc * 0.13), (cx, cy + sc * 0.2)])
            pygame.draw.rect(surf, mid, (cx + sc * 0.12, cy - sc * 0.15, sc * 0.06, sc * 0.3))
    return gfx.supersample(size, size, draw)


def scene(stage, w, h, radius=12):
    """Little stage landscape used behind vehicle pictures."""
    surf = gfx.vgradient(w, h, *stage["sky"]).convert_alpha()
    far, near = stage["far"]
    seed = stage["seed"]
    pygame.draw.polygon(surf, far, [(x, h * 0.55 - math.sin(x / w * 5 + seed) * h * 0.08) for x in range(0, int(w) + 8, 8)]
                        + [(w, h), (0, h)])
    gy = h * 0.8
    pygame.draw.rect(surf, stage["ground"], (0, gy, w, h - gy))
    for i in range(int(w / s(30))):
        pygame.draw.ellipse(surf, stage["pebble"], ((i * 0.37 % 1) * w, gy + s(10) + (i * 0.61 % 1) * (h - gy - s(16)),
                                                   s(12), s(8)))
    pygame.draw.rect(surf, stage["top"], (0, gy, w, s(9)))
    pygame.draw.line(surf, stage["top_hi"], (0, gy + s(1)), (w, gy + s(1)), si(3))
    if stage["decor"] == "space":
        for i in range(30):
            pygame.draw.circle(surf, (240, 240, 255), ((i * 0.71 % 1) * w, (i * 0.37 % 1) * h * 0.45), 1.2 * gfx.U)
    if radius:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_top_left_radius=si(radius),
                         border_top_right_radius=si(radius))
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return surf, gy


def vehicle_on_scene(app, stage, spec, w, h, fit=0.62, levels=None):
    surf, gy = scene(stage, w, h)
    lowest = min(ly - r for _, ly, r in rest_wheel_offsets(spec, vehicle_stats(spec, levels or {})))
    top = max([y for _, y in spec["hull"]] + [spec["head"][1] + spec["head_r"],
                                             spec["exhaust"][1] if spec["key"] == "monster" else -9])
    xs = [x for x, _ in spec["hull"]] + [w_[0] - w_[2] for w_ in spec["wheels"]] + [w_[0] + w_[2] for w_ in spec["wheels"]]
    height_m, width_m = top - lowest + 0.25, max(abs(x) for x in xs) * 2 + 0.3
    k_target = min(gy * 0.9 / height_m, h * fit / 2.3, w * 0.86 / width_m)   # pixels per metre that fit
    scale = k_target / app.art.ppm
    img, (cx, cy) = compose_vehicle(app.art, spec, scale, levels, driver=app.data["driver"])
    surf.blit(img, (w / 2 - cx, gy + lowest * k_target - cy))
    return surf


# ------------------------------------------------------------------ screens
class Setup:
    """One screen for the next round: map, vehicle and driver side by side, then START."""
    ROWS = ("stage", "vehicle", "driver")
    TITLES = {"stage": "MAP", "vehicle": "VEHICLE", "driver": "DRIVER"}
    STAGE_INFO = {"countryside": "Rolling hills · day & night", "desert": "Huge dunes · day & night",
                  "arctic": "Slippery ice · day & night", "moon": "Low gravity", "city": "Skyscrapers · night lights",
                  "volcano": "Jump the lava pits!", "jungle": "Rain, rivers & palms", "mars": "Red dust · very low gravity"}

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        margin = s(40)
        self.hero_rect = pygame.Rect(margin, s(78), gfx.W - 2 * margin, s(236))
        gap = s(20)
        pw = min(s(400), (gfx.W - 2 * margin - 2 * gap) / 3)
        x0 = gfx.W / 2 - (3 * pw + 2 * gap) / 2
        self.panels = {}
        for i, row in enumerate(self.ROWS):
            r = pygame.Rect(x0 + i * (pw + gap), s(330), pw, s(246))
            thumb = pygame.Rect(0, 0, r.w - s(150), s(126))
            thumb.midtop = (r.centerx, r.y + s(42))
            left = pygame.Rect(r.x + s(10), thumb.centery - s(30), s(60), s(60))
            right = pygame.Rect(r.right - s(70), thumb.centery - s(30), s(60), s(60))
            self.panels[row] = dict(rect=r, thumb=thumb, left=left, right=right)
        self.focus = 0
        self.home_btn = Button("HOME", (s(150), gfx.H - s(56)), (210, 64), "gray")
        self.garage_btn = Button("UPGRADES", (gfx.W / 2, gfx.H - s(56)), (270, 64), "blue")
        self.start_btn = Button("START", (gfx.W - s(176), gfx.H - s(54)), (290, 78), "green", icon=checker_icon(s(34)))
        self.cache = {}

    # ----------------------------------------------------------- choices
    def options(self, row):
        return {"stage": STAGES, "vehicle": VEHICLES, "driver": DRIVERS}[row]

    def current(self, row):
        key = self.app.data[row]
        opts = self.options(row)
        return next((i for i, o in enumerate(opts) if o["key"] == key), 0)

    def step(self, row, d):
        app = self.app
        opts = self.options(row)
        o = opts[(self.current(row) + d) % len(opts)]
        app.data[row] = o["key"]
        app.persist()
        app.audio.play("click")
        if row == "driver":
            app.audio.say(o["key"])

    # ------------------------------------------------------------ images
    def _cached(self, key, make):
        if key not in self.cache:
            if len(self.cache) > 60:
                self.cache.clear()
            self.cache[key] = make()
        return self.cache[key]

    def hero(self):
        app, r = self.app, self.hero_rect
        return self._cached(("hero", app.data["stage"], app.data["vehicle"], app.data["driver"]),
                            lambda: vehicle_on_scene(app, app.stage, app.vehicle, r.w, r.h, 0.82,
                                                     app.data["levels"][app.data["vehicle"]]))

    def thumb(self, row):
        app, t = self.app, self.panels[row]["thumb"]
        if row == "stage":
            return self._cached(("st", app.data["stage"]), lambda: scene(app.stage, t.w, t.h)[0])
        if row == "vehicle":
            return self._cached(("veh", app.data["vehicle"], app.data["stage"], app.data["driver"]),
                                lambda: vehicle_on_scene(app, app.stage, app.vehicle, t.w, t.h, 0.8))
        key = app.data["driver"]

        def face_card():
            card = pygame.Surface(t.size, pygame.SRCALPHA)
            pygame.draw.rect(card, (70, 140, 210), card.get_rect(), border_top_left_radius=si(12),
                             border_top_right_radius=si(12))
            pygame.draw.rect(card, (110, 176, 236), (0, 0, t.w, t.h // 2), border_top_left_radius=si(12),
                             border_top_right_radius=si(12))
            img = vehicle_head_preview(app, s(44)) if key == "default" else face_img(key, s(44))
            card.blit(img, img.get_rect(center=(t.w / 2, t.h / 2 + s(14))))
            return card
        return self._cached(("drv", key, app.data["vehicle"]), face_card)

    # ------------------------------------------------------------ events
    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN:
            row = self.ROWS[self.focus]
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.focus = (self.focus - 1) % 3
            elif ev.key in (pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
                self.focus = (self.focus + 1) % 3
            elif ev.key in (pygame.K_LEFT, pygame.K_a):
                self.step(row, -1)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.step(row, 1)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                app.start_run()
            elif ev.key == pygame.K_g:
                app.goto("garage")
            elif ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("home")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.start_btn.hit(ev.pos):
                app.start_run()
                return
            if self.home_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("home")
                return
            if self.garage_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("garage")
                return
            for i, row in enumerate(self.ROWS):
                pn = self.panels[row]
                if pn["left"].inflate(s(10), s(10)).collidepoint(ev.pos):
                    self.focus = i
                    self.step(row, -1)
                elif pn["right"].inflate(s(10), s(10)).collidepoint(ev.pos):
                    self.focus = i
                    self.step(row, 1)
                elif pn["rect"].collidepoint(ev.pos):
                    self.focus = i
                    app.audio.play("click")
                    app.goto({"stage": "stages", "vehicle": "vehicles", "driver": "drivers"}[row])

    # -------------------------------------------------------------- draw
    def _arrow(self, surf, r, d, hover):
        """Round yellow arrow button with a dark lip, like the rest of the buttons."""
        rad = min(r.w, r.h) / 2
        cx, cy = r.centerx, r.centery
        pygame.draw.circle(surf, NAVY, (cx, cy + s(4)), rad + s(2))
        pygame.draw.circle(surf, (180, 96, 8), (cx, cy + s(3)), rad - s(1))
        pygame.draw.circle(surf, (255, 196, 40) if not hover else (255, 214, 80), (cx, cy - s(1)), rad - s(2))
        pygame.draw.circle(surf, (255, 236, 140), (cx - rad * 0.2, cy - rad * 0.35), rad * 0.4)
        pygame.draw.circle(surf, (255, 196, 40) if not hover else (255, 214, 80), (cx, cy - s(1)), rad * 0.72)
        k = rad * 0.42
        pts = [(cx - d * k * 0.55, cy - k), (cx + d * k * 0.75, cy), (cx - d * k * 0.55, cy + k)]
        pygame.draw.polygon(surf, NAVY, [(x + s(1), y + s(2)) for x, y in pts])
        pygame.draw.polygon(surf, WHITE, pts)

    def draw(self, surf, mouse, now):
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "READY TO RACE")
        hr = self.hero_rect
        pygame.draw.rect(surf, NAVY, hr.inflate(s(10), s(10)), border_radius=si(20))
        hero = self.hero().copy()
        mask = pygame.Surface(hr.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=si(16))
        hero.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(hero, hr.topleft)
        pygame.draw.rect(surf, (255, 255, 255), hr.inflate(s(2), s(2)), si(3), border_radius=si(17))
        best = app.data["best"].get(app.data["stage"], 0)
        label = f"{app.stage['name'].upper()}  ·  {app.vehicle['name'].upper()}"
        tag = gfx.text("black_i", 30, label, WHITE, outline=INK, width=3)
        surf.blit(tag, tag.get_rect(topleft=(hr.x + s(20), hr.y + s(14))))
        if best:
            gfx.blit_text(surf, "cond", 20, f"BEST {best} m", GOLD, (hr.x + s(22), hr.y + s(56)), outline=INK, width=2)
        for i, row in enumerate(self.ROWS):
            pn = self.panels[row]
            r = pn["rect"]
            focused = i == self.focus
            glass(surf, r, 18, focused)
            opts = self.options(row)
            idx = self.current(row)
            gfx.blit_text(surf, "black_i", 22, self.TITLES[row], GOLD if focused else WHITE, (r.x + s(18), r.y + s(8)),
                          outline=NAVY, width=2)
            gfx.blit_text(surf, "heavy", 16, f"{idx + 1} / {len(opts)}", MUTED, (r.right - s(28), r.y + s(13)),
                          "topright")
            t = pn["thumb"]
            hover = r.collidepoint(mouse) and not (pn["left"].collidepoint(mouse) or pn["right"].collidepoint(mouse))
            pygame.draw.rect(surf, (255, 255, 255) if hover else NAVY, t.inflate(s(8), s(8)), border_radius=si(14))
            img = self.thumb(row)
            mask = pygame.Surface(t.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=si(12))
            img = img.copy()
            img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(img, t.topleft)
            self._arrow(surf, pn["left"], -1, pn["left"].collidepoint(mouse))
            self._arrow(surf, pn["right"], 1, pn["right"].collidepoint(mouse))
            o = opts[idx]
            name = gfx.text("black_i", 28, o["name"].upper(), WHITE, outline=NAVY, width=2.5)
            if name.get_width() > r.w - s(24):
                name = pygame.transform.smoothscale_by(name, (r.w - s(24)) / name.get_width())
            surf.blit(name, name.get_rect(center=(r.centerx, t.bottom + s(26))))
            if row == "stage":
                sub = self.STAGE_INFO.get(o["key"], "")
            elif row == "vehicle":
                sub = o["tagline"]
            else:
                sub = "Tap the picture to see everyone" if app.hud.touch_mode else "Click the picture to see everyone"
            sub_img = gfx.text("cond_i", 16, sub, (130, 200, 255))
            if sub_img.get_width() > r.w - s(24):
                sub_img = pygame.transform.smoothscale_by(sub_img, (r.w - s(24)) / sub_img.get_width())
            surf.blit(sub_img, sub_img.get_rect(center=(r.centerx, t.bottom + s(56))))
        pressed = pygame.mouse.get_pressed()[0]
        self.home_btn.draw(surf, mouse, pressed)
        self.garage_btn.draw(surf, mouse, pressed)
        self.start_btn.draw(surf, mouse, pressed)


class StageSelect:
    CARD_W, CARD_H, PREVIEW_H = 270, 222, 142

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        cols, gap = 4, 22
        x0 = gfx.W / 2 - s(cols * self.CARD_W + (cols - 1) * gap) / 2
        self.rects = [pygame.Rect(x0 + s((i % cols) * (self.CARD_W + gap)), s(92 + (i // cols) * (self.CARD_H + 20)),
                                  s(self.CARD_W), s(self.CARD_H)) for i in range(len(STAGES))]
        self.previews = {}
        self.next_btn = Button("DONE", (gfx.W - s(170), gfx.H - s(62)), (250, 66), "green")
        self.quit_btn = Button("BACK", (s(170), gfx.H - s(62)), (220, 66), "gray")
        self.online_btn = Button("PLAY ONLINE", (gfx.W / 2, gfx.H - s(62)), (300, 66), "blue")

    def preview(self, st, r):
        key = (st["key"], self.app.data["vehicle"], self.app.data["driver"])
        if key not in self.previews:
            self.previews[key] = vehicle_on_scene(self.app, st, self.app.vehicle, r.w, s(self.PREVIEW_H), 0.55)
        return self.previews[key]

    def handle(self, ev):
        app = self.app
        keys = [st["key"] for st in STAGES]
        if ev.type == pygame.KEYDOWN:
            i = keys.index(app.data["stage"])
            moves = {pygame.K_RIGHT: 1, pygame.K_d: 1, pygame.K_LEFT: -1, pygame.K_a: -1,
                     pygame.K_DOWN: 4, pygame.K_s: 4, pygame.K_UP: -4, pygame.K_w: -4}
            if ev.key in moves:
                self.select(STAGES[max(0, min(len(STAGES) - 1, i + moves[ev.key]))])
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                app.goto("setup")
            elif ev.key == pygame.K_o:
                app.goto("online")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.next_btn.hit(ev.pos) or self.quit_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("setup")
            elif self.online_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("online")
            for st, r in zip(STAGES, self.rects):
                if r.collidepoint(ev.pos):
                    if app.data["stage"] == st["key"]:
                        app.audio.play("click")
                        app.goto("setup")
                    else:
                        self.select(st)

    def select(self, st):
        if self.app.data["stage"] != st["key"]:
            self.app.audio.play("click")
            self.app.data["stage"] = st["key"]
            self.app.persist()

    def draw(self, surf, mouse, now):
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "SELECT STAGE")
        for st, rect in zip(STAGES, self.rects):
            selected = app.data["stage"] == st["key"]
            hover = rect.collidepoint(mouse)
            r = rect.move(0, -s(4) if hover and not selected else 0)
            glass(surf, r, 14, selected, hover)
            surf.blit(self.preview(st, r), r.topleft)
            ph = s(self.PREVIEW_H)
            gfx.blit_text(surf, "cond", 24, st["name"].upper(), WHITE, (r.x + s(14), r.y + ph + s(10)))
            best = app.data["best"].get(st["key"], 0)
            if best:
                badge = gfx.text("cond", 16, f"BEST {best} m", WHITE)
                br = badge.get_rect(topright=(r.right - s(10), r.y + s(10))).inflate(s(14), s(6))
                pygame.draw.rect(surf, (20, 22, 26), br, border_radius=br.h // 2)
                surf.blit(badge, badge.get_rect(center=br.center))
            extra = {"arctic": "Slippery ice · day & night", "moon": "Low gravity", "desert": "Huge dunes · day & night",
                     "city": "Skyscrapers · night lights", "volcano": "Jump the lava pits!",
                     "jungle": "Rain, rivers & palms", "mars": "Red dust · very low gravity"}.get(
                st["key"], "Rolling hills · day & night")
            gfx.blit_text(surf, "cond_i", 16, extra, (130, 200, 255), (r.x + s(14), r.y + ph + s(46)))
        gfx.blit_text(surf, "cond", 18, "Pick a map  ·  tap it again (or press Enter) when you're done",
                      HINT, (gfx.W / 2, s(580)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.next_btn.draw(surf, mouse, pressed)
        self.quit_btn.draw(surf, mouse, pressed)
        self.online_btn.draw(surf, mouse, pressed)


class VehicleSelect:
    CARD_W, CARD_H, PREVIEW_H = 380, 158, 92

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        gap = 20
        x0 = gfx.W / 2 - s(3 * self.CARD_W + 2 * gap) / 2
        self.rects = []
        for i in range(len(VEHICLES)):
            col, row = i % 3, i // 3
            self.rects.append(pygame.Rect(x0 + s(col * (self.CARD_W + gap)), s(84 + row * (self.CARD_H + 14)),
                                          s(self.CARD_W), s(self.CARD_H)))
        self.previews = {}
        self.back_btn = Button("BACK", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.next_btn = Button("DONE", (gfx.W - s(176), gfx.H - s(56)), (250, 64), "green")

    def preview(self, spec, r):
        key = (spec["key"], self.app.data["stage"], self.app.data["driver"])
        if key not in self.previews:
            self.previews[key] = vehicle_on_scene(self.app, self.app.stage, spec, r.w, s(self.PREVIEW_H), 0.78)
        return self.previews[key]

    def select(self, spec):
        if self.app.data["vehicle"] != spec["key"]:
            self.app.audio.play("click")
            self.app.data["vehicle"] = spec["key"]
            self.app.persist()

    def handle(self, ev):
        app = self.app
        keys = [v["key"] for v in VEHICLES]
        if ev.type == pygame.KEYDOWN:
            i = keys.index(app.data["vehicle"])
            moves = {pygame.K_RIGHT: 1, pygame.K_d: 1, pygame.K_LEFT: -1, pygame.K_a: -1,
                     pygame.K_DOWN: 3, pygame.K_s: 3, pygame.K_UP: -3, pygame.K_w: -3}
            if ev.key in moves:
                self.select(VEHICLES[max(0, min(len(VEHICLES) - 1, i + moves[ev.key]))])
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("setup")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.next_btn.hit(ev.pos) or self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("setup")
            for spec, r in zip(VEHICLES, self.rects):
                if r.collidepoint(ev.pos):
                    if app.data["vehicle"] == spec["key"]:
                        app.audio.play("click")
                        app.goto("setup")
                    else:
                        self.select(spec)

    def draw(self, surf, mouse, now):
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "CHOOSE YOUR RIDE")
        for spec, rect in zip(VEHICLES, self.rects):
            selected = app.data["vehicle"] == spec["key"]
            hover = rect.collidepoint(mouse)
            r = rect.move(0, -s(3) if hover and not selected else 0)
            glass(surf, r, 14, selected, hover)
            surf.blit(self.preview(spec, r), r.topleft)
            ph = s(self.PREVIEW_H)
            name = gfx.text("cond", 24, spec["name"].upper(), WHITE)
            tag = gfx.text("cond_i", 15, spec["tagline"], MUTED)
            room = s(168)
            for img, y in ((name, s(4)), (tag, s(34))):
                if img.get_width() > room:
                    img = pygame.transform.smoothscale_by(img, room / img.get_width())
                surf.blit(img, (r.x + s(16), r.y + ph + y))
            lv = sum(app.data["levels"][spec["key"]].values()) - len(UPGRADES)
            if lv:
                gfx.blit_text(surf, "cond", 14, f"{lv} upgrades", GOLD, (r.right - s(12), r.y + s(8)), "topright")
            stats = rating(spec)
            bx, by = r.x + s(206), r.y + ph + s(2)
            for i, (name, val) in enumerate(stats.items()):
                y = by + i * s(15)
                gfx.blit_text(surf, "cond", 13, name, MUTED, (bx, y + s(5)), "midleft")
                bar = pygame.Rect(bx + s(52), y, s(110), s(10))
                pygame.draw.rect(surf, (64, 66, 72), bar, border_radius=si(4))
                fill = bar.copy()
                fill.w = max(si(4), int(bar.w * val))
                pygame.draw.rect(surf, gfx.mix((90, 200, 60), (255, 190, 40), 1 - val), fill, border_radius=si(4))
        gfx.blit_text(surf, "cond", 18, "Every vehicle is free  ·  tap it again (or press Enter) when you're done",
                      HINT, (gfx.W / 2, s(608)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.back_btn.draw(surf, mouse, pressed)
        self.next_btn.draw(surf, mouse, pressed)


class DriverSelect:
    CARD_W, CARD_H = 162, 214

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        cols, gap = 7, 12
        x0 = gfx.W / 2 - s(cols * self.CARD_W + (cols - 1) * gap) / 2
        self.rects = []
        for i in range(len(DRIVERS)):
            col, row = i % cols, i // cols
            self.rects.append(pygame.Rect(x0 + s(col * (self.CARD_W + gap)), s(96 + row * (self.CARD_H + gap)),
                                          s(self.CARD_W), s(self.CARD_H)))
        self.faces = {}
        self.back_btn = Button("BACK", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.next_btn = Button("DONE", (gfx.W - s(176), gfx.H - s(56)), (250, 64), "green")

    def face(self, d):
        if d["key"] not in self.faces:
            if d["key"] == "default":
                img = vehicle_head_preview(self.app, s(50))
            else:
                img = face_img(d["key"], s(50))
            self.faces[d["key"]] = img
        return self.faces[d["key"]]

    def select(self, d):
        if self.app.data["driver"] != d["key"]:
            self.app.audio.play("click")
            self.app.data["driver"] = d["key"]
            self.app.persist()
            self.app.audio.say(d["key"])

    def handle(self, ev):
        app = self.app
        keys = [d["key"] for d in DRIVERS]
        if ev.type == pygame.KEYDOWN:
            i = keys.index(app.data["driver"]) if app.data["driver"] in keys else 0
            moves = {pygame.K_RIGHT: 1, pygame.K_d: 1, pygame.K_LEFT: -1, pygame.K_a: -1,
                     pygame.K_DOWN: 7, pygame.K_s: 7, pygame.K_UP: -7, pygame.K_w: -7}
            if ev.key in moves:
                self.select(DRIVERS[max(0, min(len(DRIVERS) - 1, i + moves[ev.key]))])
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("setup")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.next_btn.hit(ev.pos) or self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("setup")
            for d, r in zip(DRIVERS, self.rects):
                if r.collidepoint(ev.pos):
                    if app.data["driver"] == d["key"]:
                        app.audio.play("click")
                        app.goto("setup")
                    else:
                        self.select(d)

    def draw(self, surf, mouse, now):
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "CHOOSE YOUR DRIVER")
        for d, rect in zip(DRIVERS, self.rects):
            selected = app.data["driver"] == d["key"]
            hover = rect.collidepoint(mouse)
            r = rect.move(0, -s(3) if hover and not selected else 0)
            glass(surf, r, 14, selected, hover)
            top = pygame.Rect(r.x, r.y, r.w, s(160))
            pygame.draw.rect(surf, (70, 140, 210), top, border_top_left_radius=si(12), border_top_right_radius=si(12))
            pygame.draw.rect(surf, (110, 176, 236), (top.x, top.y, top.w, top.h // 2),
                             border_top_left_radius=si(12), border_top_right_radius=si(12))
            img = self.face(d)
            clip = surf.get_clip()
            surf.set_clip(top)
            surf.blit(img, img.get_rect(center=(top.centerx, top.centery + s(4))))
            surf.set_clip(clip)
            name = gfx.text("cond", 20, d["name"].upper(), WHITE)
            if name.get_width() > r.w - s(14):
                name = pygame.transform.smoothscale_by(name, (r.w - s(14)) / name.get_width())
            surf.blit(name, name.get_rect(center=(r.centerx, r.y + s(186))))
        gfx.blit_text(surf, "cond", 18, "Pick who drives  ·  They will swear when the engine seizes!",
                      HINT, (gfx.W / 2, s(584)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.back_btn.draw(surf, mouse, pressed)
        self.next_btn.draw(surf, mouse, pressed)


def face_img(key, radius):
    from drivers import face
    return face(key, radius)


def vehicle_head_preview(app, radius):
    from vehicle_art import head
    img = head(app.vehicle["head_art"], radius / 0.27)
    return img


class Garage:
    TW, TH, GAP = 230, 200, 22

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        self.icons = {u["key"]: upgrade_icon(u["key"], s(74)) for u in UPGRADES}
        x0 = gfx.W / 2 - s(4 * self.TW + 3 * self.GAP) / 2
        self.tiles = [(u, pygame.Rect(x0 + s(i * (self.TW + self.GAP)), s(318), s(self.TW), s(self.TH)))
                      for i, u in enumerate(UPGRADES)]
        self.tile_img = gfx.rounded(s(self.TW), s(self.TH), s(14), (226, 228, 232), top=(255, 255, 255))
        self.tile_hover = gfx.rounded(s(self.TW), s(self.TH), s(14), (240, 242, 246), top=(255, 255, 255))
        self.back_btn = Button("BACK", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.start_btn = Button("START", (gfx.W - s(176), gfx.H - s(56)), (250, 64), "green",
                                icon=checker_icon(s(34)))
        self.horn_btns = {k: Button(f"HORN: {k.upper()}", (gfx.W / 2, gfx.H - s(56)), (290, 64), "blue")
                          for k in ("puppy", "ship")}
        self.flash = {}
        self.showcase = None
        self.showcase_key = None

    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                app.start_run()
            elif ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("setup")
            elif pygame.K_1 <= ev.key <= pygame.K_4:
                self.buy(UPGRADES[ev.key - pygame.K_1])
            elif ev.key == pygame.K_h:
                self.toggle_horn()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.start_btn.hit(ev.pos):
                app.start_run()
            elif self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("setup")
            elif self.horn_btns["puppy"].hit(ev.pos):
                self.toggle_horn()
            for u, r in self.tiles:
                if r.collidepoint(ev.pos):
                    self.buy(u)

    def toggle_horn(self):
        app = self.app
        app.data["horn"] = "ship" if app.data["horn"] == "puppy" else "puppy"
        app.persist()
        app.audio.play("horn_" + app.data["horn"])

    def buy(self, u):
        app = self.app
        levels = app.data["levels"][app.data["vehicle"]]
        lv = levels[u["key"]]
        if lv >= u["max"]:
            app.audio.play("deny")
            return
        cost = upgrade_cost(u, lv)
        if app.data["coins"] < cost:
            app.audio.play("deny")
            self.flash[u["key"]] = (app.now, False)
            return
        app.data["coins"] -= cost
        levels[u["key"]] = lv + 1
        app.persist()
        app.audio.play("buy")
        self.flash[u["key"]] = (app.now, True)

    def draw(self, surf, mouse, now):
        app = self.app
        key = (app.stage["key"], app.data["vehicle"], app.data["driver"])
        if self.showcase_key != key:
            self.showcase = vehicle_on_scene(app, app.stage, app.vehicle, gfx.W, s(236), 0.8)
            self.showcase_key = key
        surf.blit(self.bg, (0, 0))
        surf.blit(self.showcase, (0, s(64)))
        shade = gfx.vgradient(gfx.W, s(26), (0, 0, 0, 0), (0, 0, 0, 90))
        surf.blit(shade, (0, s(64) + s(236) - s(26)))
        best = app.data["best"].get(app.stage["key"], 0)
        title = f"{app.vehicle['name'].upper()}  ·  {app.stage['name'].upper()}"
        if best:
            title += f"  ·  BEST {best}m"
        top_bar(surf, app, title)
        levels = app.data["levels"][app.data["vehicle"]]
        dark = (40, 42, 48)
        for u, r in self.tiles:
            lv = levels[u["key"]]
            maxed = lv >= u["max"]
            cost = upgrade_cost(u, lv)
            hover = r.collidepoint(mouse)
            rect = r.move(0, -s(3) if hover and not maxed else 0)
            pygame.draw.rect(surf, (12, 14, 16), rect.move(0, s(5)), border_radius=si(14))
            surf.blit(self.tile_hover if hover else self.tile_img, rect)
            gfx.blit_text(surf, "cond", 22, u["name"], dark, (rect.centerx, rect.y + s(22)), "center")
            ic = self.icons[u["key"]]
            surf.blit(ic, ic.get_rect(center=(rect.centerx, rect.y + s(78))))
            gfx.blit_text(surf, "cond", 18, f"LEVEL {lv} / {u['max']}", (90, 94, 102),
                          (rect.centerx, rect.y + s(128)), "center")
            pip_w = (rect.w - s(28)) / u["max"]
            for i in range(u["max"]):
                pr = pygame.Rect(rect.x + s(14) + i * pip_w + s(1), rect.y + s(142), pip_w - s(3), s(7))
                pygame.draw.rect(surf, (90, 200, 50) if i < lv else (196, 200, 206), pr, border_radius=si(2))
            bar = pygame.Rect(rect.x + s(10), rect.bottom - s(42), rect.w - s(20), s(32))
            if maxed:
                pygame.draw.rect(surf, (255, 204, 48), bar, border_radius=si(9))
                gfx.blit_text(surf, "cond", 20, "MAXED OUT", dark, bar.center, "center")
            else:
                can = app.data["coins"] >= cost
                pygame.draw.rect(surf, (76, 170, 46) if can else (196, 70, 60), bar, border_radius=si(9))
                label = gfx.text("cond", 20, f"BUY  {gfx.fmt(cost)}", WHITE)
                ic = app.coin_icon_small
                x = bar.centerx - (label.get_width() + ic.get_width() + s(6)) / 2
                surf.blit(ic, ic.get_rect(midleft=(x, bar.centery)))
                surf.blit(label, label.get_rect(midleft=(x + ic.get_width() + s(6), bar.centery)))
            f = self.flash.get(u["key"])
            if f and now - f[0] < 0.4:
                ov = pygame.Surface(rect.size, pygame.SRCALPHA)
                a = int(150 * (1 - (now - f[0]) / 0.4))
                pygame.draw.rect(ov, (120, 230, 80, a) if f[1] else (240, 60, 50, a), ov.get_rect(), border_radius=si(14))
                surf.blit(ov, rect)
        gfx.blit_text(surf, "cond", 18, "Click an upgrade (or 1-4) to buy  ·  H switches the horn  ·  Enter to start",
                      HINT, (gfx.W / 2, s(560)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.back_btn.draw(surf, mouse, pressed)
        self.start_btn.draw(surf, mouse, pressed)
        self.horn_btns[app.data["horn"]].draw(surf, mouse, pressed)


class Results:
    def __init__(self, app, run, record):
        self.app, self.run, self.record = app, run, record
        self.t = 0.0
        self.frozen = app.screen.copy()
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((8, 10, 14, 160))
        self.frozen.blit(dim, (0, 0))
        cy = gfx.H - s(84)
        self.retry = Button("RETRY", (gfx.W / 2 + s(150), cy), (250, 66), "green", key="retry")
        self.garage = Button("CHANGE RIDE", (gfx.W / 2 - s(150), cy), (250, 66), "gray", key="setup")
        self.panel = gfx.rounded(s(560), s(286), s(18), PANEL, border=PANEL_EDGE, border_w=2,
                                 top=gfx.shade(PANEL, 1.3))

    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                app.start_run()
            elif ev.key in (pygame.K_ESCAPE, pygame.K_g):
                app.goto("setup")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.retry.hit(ev.pos):
                app.start_run()
            elif self.garage.hit(ev.pos):
                app.audio.play("click")
                app.goto("setup")

    def draw(self, surf, mouse, now, dt):
        self.t += dt
        run = self.run
        surf.blit(self.frozen, (0, 0))
        color = (255, 76, 60) if run.reason.startswith("DRIVER") else (255, 176, 40)
        img = gfx.text("black_i", 70, run.reason, color, outline=INK, width=4, shadow=4)
        surf.blit(img, img.get_rect(center=(gfx.W / 2, s(92))))
        panel = self.panel.get_rect(center=(gfx.W / 2, s(330)))
        surf.blit(self.panel, panel)
        x0, x1 = panel.x + s(36), panel.right - s(36)
        rows = [("Distance", f"{run.distance} m"), ("Coins collected", f"+{gfx.fmt(run.coin_pickups)}"),
                ("Stunt bonuses", f"+{gfx.fmt(run.bonus_total)}")]
        y = panel.y + s(42)
        for label, value in rows:
            gfx.blit_text(surf, "cond", 26, label, MUTED, (x0, y), "midleft")
            gfx.blit_text(surf, "cond", 28, value, WHITE, (x1, y), "midright")
            y += s(50)
        if self.record:
            badge = gfx.text("cond_i", 20, "NEW RECORD!", INK)
            label_w = gfx.text("cond", 26, "Distance", MUTED).get_width()
            br = badge.get_rect(midleft=(x0 + label_w + s(22), panel.y + s(42))).inflate(s(18), s(8))
            pygame.draw.rect(surf, GOLD, br, border_radius=br.h // 2)
            surf.blit(badge, badge.get_rect(center=br.center))
        pygame.draw.line(surf, (80, 84, 92), (x0, y - s(14)), (x1, y - s(14)), si(2))
        shown = int(run.coins * min(1.0, self.t / 1.1))
        gfx.blit_text(surf, "cond", 30, "TOTAL", WHITE, (x0, y + s(22)), "midleft")
        tot = gfx.text("cond", 40, f"+{gfx.fmt(shown)}", GOLD, outline=INK, width=2)
        r = tot.get_rect(midright=(x1, y + s(22)))
        surf.blit(tot, r)
        ic = self.app.coin_icon
        surf.blit(ic, ic.get_rect(midright=(r.left - s(8), r.centery)))
        pressed = pygame.mouse.get_pressed()[0]
        self.garage.draw(surf, mouse, pressed)
        self.retry.draw(surf, mouse, pressed)
        if not self.app.hud.touch_mode:
            gfx.blit_text(surf, "cond", 18, "Enter / R to retry  ·  Esc to change map, vehicle or driver", (170, 174, 182),
                          (gfx.W / 2, gfx.H - s(30)), "center")


class PauseMenu:
    def __init__(self, app, online=None):
        self.app = app
        cx, cy = gfx.W / 2, gfx.H / 2
        if online is None:
            self.buttons = [Button("RESUME", (cx, cy - s(10)), (300, 66), "green", key="resume"),
                            Button("RESTART", (cx, cy + s(76)), (300, 66), "gray", key="restart"),
                            Button("CHANGE RIDE", (cx, cy + s(162)), (300, 66), "gray", key="setup")]
        else:
            self.buttons = [Button("RESUME", (cx, cy - s(10)), (300, 66), "green", key="resume")]
            if online.is_host:
                self.buttons.append(Button("BACK TO LOBBY", (cx, cy + s(76)), (300, 66), "blue", key="lobby"))
            self.buttons.append(Button("LEAVE GAME", (cx, cy + s(162)), (300, 66), "gray", key="leave"))

    def click(self, pos):
        for b in self.buttons:
            if b.hit(pos):
                return b.key
        return None

    def draw(self, surf, mouse):
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((8, 10, 14, 170))
        surf.blit(dim, (0, 0))
        gfx.blit_text(surf, "black_i", 72, "PAUSED", WHITE, (gfx.W / 2, gfx.H / 2 - s(120)), "center",
                      outline=INK, width=4, shadow=4)
        if not self.app.hud.touch_mode:
            gfx.blit_text(surf, "cond", 18, "M toggles music", (170, 174, 182), (gfx.W / 2, gfx.H / 2 + s(226)),
                          "center")
        for b in self.buttons:
            b.draw(surf, mouse, pygame.mouse.get_pressed()[0])


# ------------------------------------------------------------------ online
class TextField:
    def __init__(self, rect, text="", placeholder="", max_len=24):
        self.rect, self.text, self.placeholder, self.max_len = rect, text, placeholder, max_len
        self.active = False

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.active = self.rect.collidepoint(ev.pos)
            return self.active
        if not self.active:
            return False
        if ev.type == pygame.TEXTINPUT:
            self.text = (self.text + ev.text)[:self.max_len]
            return True
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            if ev.key == pygame.K_v and ev.mod & pygame.KMOD_CTRL:
                try:
                    pasted = pygame.scrap.get_text() if hasattr(pygame.scrap, "get_text") else ""
                except Exception:     # no clipboard (browser) or old pygame
                    pasted = ""
                self.text = (self.text + (pasted or "").strip())[:self.max_len]
                return True
        return False

    def draw(self, surf, now):
        r = self.rect
        pygame.draw.rect(surf, GOLD if self.active else (90, 94, 102), r.inflate(s(4), s(4)), border_radius=si(10))
        pygame.draw.rect(surf, (20, 22, 26), r, border_radius=si(9))
        shown = self.text or self.placeholder
        img = gfx.text("cond", 24, shown, WHITE if self.text else (110, 114, 122))
        clip = surf.get_clip()
        surf.set_clip(r.inflate(-s(12), 0))
        x = min(r.x + s(14), r.right - s(20) - img.get_width())
        surf.blit(img, img.get_rect(midleft=(x, r.centery)))
        surf.set_clip(clip)
        if self.active and int(now * 2) % 2 == 0:
            cx = x + (img.get_width() if self.text else 0) + s(3)
            pygame.draw.line(surf, WHITE, (cx, r.y + s(10)), (cx, r.bottom - s(10)), si(2))


class Selector:
    """'LABEL  < value >' with clickable arrows."""

    def __init__(self, label, center, width=360):
        self.label = label
        self.rect = pygame.Rect(0, 0, s(width), s(46))
        self.rect.center = center
        self.left = pygame.Rect(self.rect.x, self.rect.y, s(46), self.rect.h)
        self.right = pygame.Rect(self.rect.right - s(46), self.rect.y, s(46), self.rect.h)

    def hit(self, pos):
        if self.left.collidepoint(pos):
            return -1
        if self.right.collidepoint(pos):
            return 1
        return 0

    def draw(self, surf, value, enabled=True):
        gfx.blit_text(surf, "cond", 17, self.label, MUTED, (self.rect.x, self.rect.y - s(4)), "bottomleft")
        pygame.draw.rect(surf, (20, 22, 26), self.rect, border_radius=si(10))
        for r, pts in ((self.left, ((0.62, 0.25), (0.35, 0.5), (0.62, 0.75))),
                       (self.right, ((0.38, 0.25), (0.65, 0.5), (0.38, 0.75)))):
            col = (255, 204, 48) if enabled else (70, 72, 78)
            pygame.draw.polygon(surf, col, [(r.x + r.w * x, r.y + r.h * y) for x, y in pts])
        gfx.blit_text(surf, "cond", 22, value, WHITE, self.rect.center, "center")


def mode_label(settings):
    if settings["mode"] == "free":
        return "FREE RIDE"
    if settings["mode"] == "tournament":
        return "TOURNAMENT · 4 RACES"
    return f"RACE  {settings['distance']} m"


MODES = [("free", 0)] + [("race", d) for d in RACE_DISTANCES] + [("tournament", 0)]


class SmallButton:
    def __init__(self, label, rect, color=(76, 170, 46)):
        self.label, self.rect, self.color = label, rect, color

    def draw(self, surf, mouse):
        col = gfx.shade(self.color, 1.15) if self.rect.collidepoint(mouse) else self.color
        pygame.draw.rect(surf, col, self.rect, border_radius=si(8))
        gfx.blit_text(surf, "cond", 17, self.label, WHITE, self.rect.center, "center")

    def hit(self, pos):
        return self.rect.collidepoint(pos)


def friend_rows(app, panel, first_y, with_invite=False, room=None):
    """Draw the friends list; returns [(number, action, rect)] for clicks."""
    relay = app.relay
    hits = []
    friends = sorted(app.data["friends"].items(), key=lambda kv: (not relay.presence.get(kv[0], {}).get("on"), kv[1]))
    if not friends:
        gfx.blit_text(app.screen, "cond", 18, "No friends yet - add one by player number.", MUTED,
                      (panel.x + s(20), first_y + s(8)))
    for i, (num, name) in enumerate(friends[:7]):
        y = first_y + i * s(44)
        row = pygame.Rect(panel.x + s(14), y, panel.w - s(28), s(38))
        pygame.draw.rect(app.screen, (48, 51, 58), row, border_radius=si(8))
        pres = relay.presence.get(num, {})
        online = bool(pres.get("on"))
        pygame.draw.circle(app.screen, (90, 220, 70) if online else (110, 112, 118), (row.x + s(18), row.centery), s(7))
        shown = pres.get("name") or name
        gfx.blit_text(app.screen, "cond", 20, f"{shown}", WHITE, (row.x + s(34), row.centery), "midleft")
        gfx.blit_text(app.screen, "cond", 16, f"#{num}", MUTED, (row.x + s(200), row.centery), "midleft")
        x = row.right - s(8)
        rm = pygame.Rect(0, 0, s(30), s(28))
        rm.midright = (x, row.centery)
        pygame.draw.rect(app.screen, (90, 50, 50), rm, border_radius=si(6))
        gfx.blit_text(app.screen, "cond", 16, "X", WHITE, rm.center, "center")
        hits.append((num, "remove", rm))
        x = rm.left - s(8)
        if with_invite and online:
            b = pygame.Rect(0, 0, s(84), s(28))
            b.midright = (x, row.centery)
            pygame.draw.rect(app.screen, (36, 110, 210), b, border_radius=si(6))
            gfx.blit_text(app.screen, "cond", 16, "INVITE", WHITE, b.center, "center")
            hits.append((num, "invite", b))
        elif not with_invite and online and pres.get("host"):
            b = pygame.Rect(0, 0, s(84), s(28))
            b.midright = (x, row.centery)
            pygame.draw.rect(app.screen, (76, 170, 46), b, border_radius=si(6))
            gfx.blit_text(app.screen, "cond", 16, "JOIN", WHITE, b.center, "center")
            hits.append((num, "join", b))
        elif online:
            gfx.blit_text(app.screen, "cond", 15, "online" + (" · hosting" if pres.get("host") else ""),
                          (130, 230, 90), (x, row.centery), "midright")
    return hits


def number_status(app, surf, center):
    relay = app.relay
    num = app.data["player_id"]
    img = gfx.text("black_i", 40, f"#{num}", GOLD, outline=INK, width=3)
    r = img.get_rect(center=center)
    surf.blit(img, r)
    gfx.blit_text(surf, "cond", 18, "YOUR PLAYER NUMBER", MUTED, (r.centerx, r.y - s(4)), "midbottom")
    on = relay.online
    pygame.draw.circle(surf, (90, 220, 70) if on else (230, 160, 40), (r.centerx - s(70), r.bottom + s(14)), s(6))
    gfx.blit_text(surf, "cond", 16, "online" if on else "connecting to the internet...", MUTED,
                  (r.centerx - s(58), r.bottom + s(14)), "midleft")


class OnlineMenu:
    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        L = gfx.W / 2 - s(600)
        self.name = TextField(pygame.Rect(L + s(20), s(230), s(360), s(48)), app.data.get("name", ""), "Your name", 16)
        self.join_num = TextField(pygame.Rect(L + s(20), s(410), s(220), s(48)), "", "Number", 8)
        self.friend_num = TextField(pygame.Rect(gfx.W / 2 + s(20), s(500), s(220), s(48)), "", "Number", 8)
        self.fields = [self.name, self.join_num, self.friend_num]
        self.host_btn = Button("HOST GAME", (L + s(200), s(320)), (360, 62), "green")
        self.join_btn = SmallButton("JOIN", pygame.Rect(L + s(256), s(410), s(124), s(48)), (36, 110, 210))
        self.add_btn = SmallButton("ADD FRIEND", pygame.Rect(gfx.W / 2 + s(256), s(500), s(150), s(48)), (36, 110, 210))
        self.back_btn = Button("BACK", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.status = ""
        self.status_ok = True
        self.busy = False
        self.hits = []

    def enter(self, message=""):
        pygame.key.start_text_input()
        self.status, self.status_ok, self.busy = message, not message, False

    def _remember_name(self):
        name = self.name.text.strip() or "Player"
        if name != self.app.data.get("name"):
            self.app.data["name"] = name
            self.app.persist()
            self.app.relay.set_name(name)

    def handle(self, ev):
        app = self.app
        if self.busy:
            return
        for f in self.fields:
            if f.handle(ev):
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                    break
                if f is not self.name:
                    f.text = "".join(c for c in f.text if c.isdigit())
                return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._remember_name()
                app.goto("home")
            elif ev.key == pygame.K_RETURN:
                if self.join_num.active:
                    self.join(self.join_num.text)
                elif self.friend_num.active:
                    self.add_friend()
                else:
                    self._remember_name()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.host_btn.hit(ev.pos):
                from config import WEB
                if WEB:
                    self.status, self.status_ok = "Online play needs the download version of Hill Rider.", False
                    return
                self._remember_name()
                app.audio.play("click")
                app.host_game()
            elif self.join_btn.hit(ev.pos):
                self.join(self.join_num.text)
            elif self.add_btn.hit(ev.pos):
                self.add_friend()
            elif self.back_btn.hit(ev.pos):
                self._remember_name()
                app.audio.play("click")
                app.goto("home")
            for num, action, rect in self.hits:
                if rect.collidepoint(ev.pos):
                    if action == "remove":
                        app.remove_friend(num)
                    elif action == "join":
                        self.join(num)
                    break

    def add_friend(self):
        num = self.friend_num.text.strip()
        if len(num) != 6 or num == self.app.data["player_id"]:
            self.status, self.status_ok = "A player number has 6 digits (and can't be your own).", False
            return
        self.app.add_friend(num, "Player")
        self.friend_num.text = ""
        self.status, self.status_ok = f"Added #{num} to your friends.", True
        self.app.audio.play("buy")

    def join(self, num):
        from config import WEB
        if WEB:
            self.status, self.status_ok = "Online play needs the download version of Hill Rider.", False
            return
        num = str(num).strip()
        if len(num) != 6:
            self.status, self.status_ok = "Type the host's 6-digit player number.", False
            self.join_num.active = True
            return
        if not self.app.relay.online:
            self.status, self.status_ok = "Not connected to the internet yet - wait a moment.", False
            return
        self._remember_name()
        self.app.audio.play("click")
        self.status, self.status_ok = f"Joining #{num} ...", True
        self.app.join_game(num)

    def draw(self, surf, mouse, now):
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "PLAY WITH FRIENDS")
        L = gfx.W / 2 - s(600)
        number_status(app, surf, (L + s(200), s(140)))
        gfx.blit_text(surf, "cond", 18, "YOUR NAME", MUTED, (self.name.rect.x, self.name.rect.y - s(4)), "bottomleft")
        self.name.draw(surf, now)
        self.host_btn.draw(surf, mouse, pygame.mouse.get_pressed()[0])
        gfx.blit_text(surf, "cond", 18, "JOIN A GAME BY THE HOST'S NUMBER", MUTED,
                      (self.join_num.rect.x, self.join_num.rect.y - s(4)), "bottomleft")
        self.join_num.draw(surf, now)
        self.join_btn.draw(surf, mouse)
        panel = pygame.Rect(gfx.W / 2, s(84), s(600), s(390))
        glass(surf, panel)
        gfx.blit_text(surf, "cond", 24, f"FRIENDS ({len(app.data['friends'])})", WHITE, (panel.x + s(20), panel.y + s(14)))
        self.hits = friend_rows(app, panel, panel.y + s(60))
        gfx.blit_text(surf, "cond", 18, "ADD A FRIEND BY PLAYER NUMBER", MUTED,
                      (self.friend_num.rect.x, self.friend_num.rect.y - s(4)), "bottomleft")
        self.friend_num.draw(surf, now)
        self.add_btn.draw(surf, mouse)
        if self.status:
            gfx.blit_text(surf, "cond", 20, self.status, (130, 230, 90) if self.status_ok else (255, 110, 96),
                          (L + s(20), s(500)), "midleft")
        gfx.blit_text(surf, "cond", 16, "Tell friends your number. They add you, and you invite each other "
                      "from the lobby - no IP addresses needed.", HINT, (gfx.W / 2, s(588)), "center")
        self.back_btn.draw(surf, mouse, pygame.mouse.get_pressed()[0])


class Lobby:
    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        cx = gfx.W / 2 + s(250)
        self.stage_sel = Selector("MAP", (cx, s(130)))
        self.mode_sel = Selector("MODE", (cx, s(204)))
        self.vehicle_sel = Selector("YOUR VEHICLE", (cx, s(278)))
        self.driver_sel = Selector("YOUR DRIVER", (cx, s(352)))
        self.invite_num = TextField(pygame.Rect(s(54), s(512), s(200), s(44)), "", "Player number", 8)
        self.invite_btn = SmallButton("INVITE", pygame.Rect(s(266), s(512), s(110), s(44)), (36, 110, 210))
        self.leave_btn = Button("LEAVE", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.start_btn = Button("START", (gfx.W - s(176), gfx.H - s(56)), (250, 64), "green",
                                icon=checker_icon(s(34)))
        self.hits = []
        self.msg = ""

    def enter(self):
        pygame.key.start_text_input()
        self.msg = ""

    def invite(self, num):
        num = str(num).strip()
        if len(num) != 6 or num == self.app.data["player_id"]:
            self.msg = "Type a 6-digit player number."
            return
        self.app.relay.invite(num, self.app.data["player_id"])
        self.app.add_friend(num, self.app.relay.presence.get(num, {}).get("name", "Player"))
        self.msg = f"Invite sent to #{num}."
        self.app.audio.play("click")
        self.invite_num.text = ""

    def handle(self, ev):
        app, ses = self.app, self.app.session
        if ses is None:
            return
        if ses.is_host and self.invite_num.handle(ev):
            self.invite_num.text = "".join(c for c in self.invite_num.text if c.isdigit())
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                self.invite(self.invite_num.text)
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                app.leave_session()
            elif ev.key == pygame.K_RETURN and ses.is_host:
                ses.start()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.leave_btn.hit(ev.pos):
                app.leave_session()
                return
            if ses.is_host and self.start_btn.hit(ev.pos):
                app.audio.play("click")
                ses.start()
                return
            if ses.is_host and self.invite_btn.hit(ev.pos):
                self.invite(self.invite_num.text)
                return
            for num, action, rect in self.hits:
                if rect.collidepoint(ev.pos):
                    if action == "invite":
                        self.invite(num)
                    elif action == "remove":
                        app.remove_friend(num)
                    return
            if ses.is_host:
                d = self.stage_sel.hit(ev.pos)
                if d:
                    keys = [st["key"] for st in STAGES]
                    i = keys.index(ses.settings["stage"])
                    ses.configure(stage=keys[(i + d) % len(keys)])
                    app.audio.play("click")
                d = self.mode_sel.hit(ev.pos)
                if d:
                    cur = (ses.settings["mode"], ses.settings["distance"] if ses.settings["mode"] == "race" else 0)
                    cur = cur if cur in MODES else (cur[0], 0)
                    i = MODES.index(cur) if cur in MODES else 0
                    mode, dist = MODES[(i + d) % len(MODES)]
                    ses.configure(mode=mode, distance=dist or ses.settings["distance"])
                    app.audio.play("click")
            for sel, items, field in ((self.vehicle_sel, VEHICLES, "vehicle"), (self.driver_sel, DRIVERS, "driver")):
                d = sel.hit(ev.pos)
                if d:
                    keys = [x["key"] for x in items]
                    i = keys.index(app.data[field]) if app.data[field] in keys else 0
                    app.data[field] = keys[(i + d) % len(keys)]
                    app.persist()
                    ses.pick(app.data["vehicle"], app.data["driver"])
                    app.audio.play("click")

    def draw(self, surf, mouse, now):
        app, ses = self.app, self.app.session
        from config import VEHICLE_BY_KEY
        from drivers import DRIVER_BY_KEY
        surf.blit(self.bg, (0, 0))
        title = f"ROOM #{ses.room}" if ses.room else "ONLINE LOBBY"
        top_bar(surf, app, title + ("  ·  YOU ARE THE HOST" if ses.is_host else ""))
        if not ses.welcomed:
            gfx.blit_text(surf, "black_i", 36, f"Joining #{ses.room} ...", WHITE, (gfx.W / 2, gfx.H / 2), "center",
                          outline=INK, width=3)
            self.leave_btn.draw(surf, mouse, False)
            return
        panel = pygame.Rect(s(40), s(84), s(560), s(380))
        glass(surf, panel)
        gfx.blit_text(surf, "cond", 24, f"PLAYERS ({len(ses.players)})", WHITE, (panel.x + s(20), panel.y + s(12)))
        for i, (pid, p) in enumerate(sorted(ses.players.items(), key=lambda kv: kv[0] != ses.host_id)):
            y = panel.y + s(54) + i * s(40)
            row = pygame.Rect(panel.x + s(14), y, panel.w - s(28), s(36))
            pygame.draw.rect(surf, (48, 51, 58), row, border_radius=si(8))
            pygame.draw.circle(surf, p["color"], (row.x + s(20), row.centery), s(9))
            me = " (you)" if pid == ses.my_id else ""
            host = "  ★" if pid == ses.host_id else ""
            gfx.blit_text(surf, "cond", 20, p["name"] + me + host, WHITE, (row.x + s(38), row.centery), "midleft")
            info = f"{VEHICLE_BY_KEY[p['vehicle']]['name']} · {DRIVER_BY_KEY.get(p['driver'], DRIVERS[0])['name']}"
            gfx.blit_text(surf, "cond", 16, info, MUTED, (row.right - s(12), row.centery), "midright")
        st_name = next(st["name"] for st in STAGES if st["key"] == ses.settings["stage"])
        self.stage_sel.draw(surf, st_name.upper(), ses.is_host)
        self.mode_sel.draw(surf, mode_label(ses.settings), ses.is_host)
        self.vehicle_sel.draw(surf, VEHICLE_BY_KEY[app.data["vehicle"]]["name"].upper())
        self.driver_sel.draw(surf, DRIVER_BY_KEY.get(app.data["driver"], DRIVERS[0])["name"].upper())
        friends = pygame.Rect(gfx.W / 2 + s(30), s(392), s(600), s(232))
        glass(surf, friends)
        self.hits = []
        if ses.is_host:
            gfx.blit_text(surf, "cond", 20, "INVITE FRIENDS", WHITE, (friends.x + s(18), friends.y + s(10)))
            self.hits = friend_rows(app, friends, friends.y + s(44), with_invite=True)
            gfx.blit_text(surf, "cond", 18, "INVITE ANY PLAYER BY NUMBER", MUTED,
                          (self.invite_num.rect.x, self.invite_num.rect.y - s(4)), "bottomleft")
            self.invite_num.draw(surf, now)
            self.invite_btn.draw(surf, mouse)
            hint = self.msg or f"Friends can also join with your number #{app.data['player_id']}"
            gfx.blit_text(surf, "cond", 17, hint, (130, 230, 90) if self.msg else MUTED, (s(54), s(574)))
        else:
            dots = "." * (int(now * 2) % 4)
            gfx.blit_text(surf, "cond", 22, f"Waiting for the host to start{dots}", WHITE, friends.center, "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.leave_btn.draw(surf, mouse, pressed)
        if ses.is_host:
            self.start_btn.draw(surf, mouse, pressed)


class InvitePopup:
    def __init__(self, app):
        self.app = app
        self.panel = pygame.Rect(0, 0, s(520), s(190))
        self.panel.center = (gfx.W / 2, gfx.H / 2)
        self.join = SmallButton("JOIN", pygame.Rect(0, 0, s(180), s(50)), (76, 170, 46))
        self.no = SmallButton("NO THANKS", pygame.Rect(0, 0, s(180), s(50)), (110, 112, 118))
        self.join.rect.bottomright = (self.panel.centerx - s(10), self.panel.bottom - s(20))
        self.no.rect.bottomleft = (self.panel.centerx + s(10), self.panel.bottom - s(20))

    def draw(self, surf, mouse, inv):
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((8, 10, 14, 150))
        surf.blit(dim, (0, 0))
        glass(surf, self.panel)
        pygame.draw.rect(surf, GOLD, self.panel, si(3), border_radius=si(16))
        gfx.blit_text(surf, "black_i", 34, f"{inv.get('name', 'Someone')} invites you!", WHITE,
                      (self.panel.centerx, self.panel.y + s(42)), "center", outline=INK, width=2)
        gfx.blit_text(surf, "cond", 18, f"Player #{inv['from']} is hosting a game", MUTED,
                      (self.panel.centerx, self.panel.y + s(84)), "center")
        self.join.draw(surf, mouse)
        self.no.draw(surf, mouse)

    def click(self, pos):
        if self.join.hit(pos):
            return "join"
        if self.no.hit(pos):
            return "no"
        return None


class RaceResults:
    """Leaderboard shown over the track when an online race is over."""

    def __init__(self, app):
        self.app = app
        cy = gfx.H - s(80)
        self.lobby_btn = Button("BACK TO LOBBY", (gfx.W / 2 + s(170), cy), (320, 64), "green")
        self.next_btn = Button("NEXT RACE", (gfx.W / 2 + s(170), cy), (320, 64), "green")
        self.leave_btn = Button("LEAVE", (gfx.W / 2 - s(170), cy), (260, 64), "gray")

    def _more_rounds(self):
        tour = self.app.session.tour
        return bool(tour) and tour["round"] < tour["rounds"]

    def click(self, pos):
        if self.leave_btn.hit(pos):
            return "leave"
        if self.app.session.is_host and self.lobby_btn.hit(pos):
            return "next" if self._more_rounds() else "lobby"
        return None

    def draw(self, surf, mouse, rows):
        ses = self.app.session
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((8, 10, 14, 170))
        surf.blit(dim, (0, 0))
        tour = ses.tour
        title = f"RACE {tour['round']} OF {tour['rounds']}" if tour else "RACE RESULTS"
        gfx.blit_text(surf, "black_i", 64, title, (255, 220, 60), (gfx.W / 2, s(90)), "center",
                      outline=INK, width=4, shadow=4)
        panel = pygame.Rect(0, 0, s(640), s(80 + 56 * len(rows)))
        panel.midtop = (gfx.W / 2, s(150))
        glass(surf, panel)
        medals = [(255, 204, 48), (200, 206, 214), (210, 140, 80)]
        for i, (pid, t, dist) in enumerate(rows):
            p = ses.players.get(pid, {"name": "?", "color": (200, 200, 200)})
            y = panel.y + s(40) + i * s(56)
            col = medals[i] if i < 3 else (90, 94, 102)
            pygame.draw.circle(surf, col, (panel.x + s(44), y + s(14)), s(18))
            gfx.blit_text(surf, "black_i", 24, str(i + 1), INK, (panel.x + s(44), y + s(14)), "center")
            name = p["name"] + ("  (you)" if pid == ses.my_id else "")
            gfx.blit_text(surf, "cond", 26, name, p["color"], (panel.x + s(80), y + s(14)), "midleft")
            right = f"{t:.2f} s" if t is not None else f"DNF  ({int(dist)} m)"
            gfx.blit_text(surf, "cond", 26, right, WHITE, (panel.right - s(30) - (s(130) if tour else 0), y + s(14)),
                          "midright")
            if tour:
                pts = tour["points"].get(str(pid), 0)
                gfx.blit_text(surf, "cond", 26, f"{pts} pts", GOLD, (panel.right - s(30), y + s(14)), "midright")
        if tour:
            standings = sorted(tour["points"].items(), key=lambda kv: -kv[1])
            if tour["round"] >= tour["rounds"] and standings:
                champ = ses.players.get(int(standings[0][0]), {"name": "?"})["name"]
                gfx.blit_text(surf, "black_i", 40, f"CHAMPION: {champ}!", GOLD, (gfx.W / 2, panel.bottom + s(40)),
                              "center", outline=INK, width=3)
            else:
                gfx.blit_text(surf, "cond", 22, "Points: 10 · 7 · 5 · 3 · 2 · 1  -  next map coming up", MUTED,
                              (gfx.W / 2, panel.bottom + s(30)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.leave_btn.draw(surf, mouse, pressed)
        if ses.is_host:
            (self.next_btn if self._more_rounds() else self.lobby_btn).draw(surf, mouse, pressed)
        else:
            gfx.blit_text(surf, "cond", 20, "Waiting for the host...", MUTED,
                          (gfx.W / 2 + s(170), gfx.H - s(80)), "center")


# ---------------------------------------------------------------- settings
class Slider:
    def __init__(self, label, rect):
        self.label, self.rect = label, rect
        self.dragging = False

    def value_at(self, x):
        return max(0.0, min(1.0, (x - self.rect.x) / self.rect.w))

    def draw(self, surf, value):
        gfx.blit_text(surf, "cond", 18, self.label, MUTED, (self.rect.x, self.rect.y - s(10)), "bottomleft")
        gfx.blit_text(surf, "cond", 18, f"{int(round(value * 100))}%", WHITE, (self.rect.right, self.rect.y - s(10)),
                      "bottomright")
        track = self.rect.inflate(0, -self.rect.h + s(10))
        pygame.draw.rect(surf, (20, 22, 26), track, border_radius=si(5))
        fill = track.copy()
        fill.w = int(track.w * value)
        pygame.draw.rect(surf, (90, 200, 60), fill, border_radius=si(5))
        knob = (self.rect.x + self.rect.w * value, self.rect.centery)
        pygame.draw.circle(surf, INK, knob, s(14))
        pygame.draw.circle(surf, WHITE, knob, s(11))


class Settings:
    def __init__(self, app):
        import music
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        x0 = s(90)
        self.sliders = [(Slider(label, pygame.Rect(x0, s(150) + i * s(84), s(460), s(30))), key)
                        for i, (label, key) in enumerate((("MASTER VOLUME", "master"), ("MUSIC", "music"),
                                                         ("EFFECTS & HORN", "sfx"), ("DRIVER VOICES", "voice")))]
        cx = gfx.W / 2 + s(270)
        self.tracks = ["auto"] + music.DRIVE_TRACKS
        self.track_names = {"auto": "AUTO (PER MAP)"} | {k: music.TRACKS[k][0].upper() for k in music.DRIVE_TRACKS}
        self.music_sel = Selector("MUSIC WHILE DRIVING", (cx, s(170)), 400)
        self.gfx_sel = Selector("GRAPHICS", (cx, s(260)), 400)
        self.full_sel = Selector("FULLSCREEN", (cx, s(350)), 400)
        self.ghost_sel = Selector("GHOST OF YOUR BEST RUN", (cx, s(440)), 400)
        self.back_btn = Button("BACK", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.active = None

    def enter(self):
        self.preview = None

    def _set_volume(self, key, value):
        self.app.data["volume"][key] = round(value, 2)
        self.app.audio.set_volumes(self.app.data["volume"])

    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            app.persist()
            app.goto("home")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.back_btn.hit(ev.pos):
                app.persist()
                app.audio.play("click")
                app.goto("home")
                return
            for sl, key in self.sliders:
                if sl.rect.inflate(s(20), s(24)).collidepoint(ev.pos):
                    self.active = (sl, key)
                    self._set_volume(key, sl.value_at(ev.pos[0]))
                    return
            d = self.music_sel.hit(ev.pos)
            if d:
                i = self.tracks.index(app.data["music_track"]) if app.data["music_track"] in self.tracks else 0
                app.data["music_track"] = self.tracks[(i + d) % len(self.tracks)]
                app.audio.music(app.data["music_track"] if app.data["music_track"] != "auto" else "menu")
                app.persist()
            d = self.gfx_sel.hit(ev.pos)
            if d:
                app.data["graphics"] = "low" if app.data["graphics"] == "high" else "high"
                app.apply_graphics()
                app.persist()
            d = self.full_sel.hit(ev.pos)
            if d and app.fs_available():
                app.toggle_fullscreen()
            d = self.ghost_sel.hit(ev.pos)
            if d:
                app.data["ghosts"] = not app.data.get("ghosts", True)
                app.persist()
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self.active:
                self.active = None
                app.persist()
                app.audio.play("click")
        elif ev.type == pygame.MOUSEMOTION and self.active:
            sl, key = self.active
            self._set_volume(key, sl.value_at(ev.pos[0]))

    def draw(self, surf, mouse, now):
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "SETTINGS")
        panel = pygame.Rect(s(50), s(96), s(540), s(380))
        glass(surf, panel)
        for sl, key in self.sliders:
            sl.draw(surf, app.data["volume"][key])
        self.music_sel.draw(surf, self.track_names.get(app.data["music_track"], "AUTO"))
        self.gfx_sel.draw(surf, "HIGH" if app.data["graphics"] == "high" else "LOW (FASTER)")
        if app.fs_available():
            self.full_sel.draw(surf, "ON" if app.is_fullscreen() else "OFF")
            app.fs_extra = self.full_sel.rect          # browser: the page switches on the tap itself
        else:
            self.full_sel.draw(surf, "NOT ON THIS DEVICE", enabled=False)
        self.ghost_sel.draw(surf, "SHOW" if app.data.get("ghosts", True) else "HIDE")
        keys = pygame.Rect(0, 0, s(460), s(150))
        keys.midtop = (gfx.W / 2 + s(270), s(484))
        glass(surf, keys)
        gfx.blit_text(surf, "cond", 20, "CONTROLS", WHITE, (keys.x + s(18), keys.y + s(12)))
        rows = [("Gas / Brake", "Right / Left  (or D / A)"), ("Boost  ·  Horn  ·  Lights", "Space  ·  H  ·  L"),
                ("Fix seized engine", "Enter"), ("Pause / Music / Fullscreen", "Esc  ·  M  ·  F11")]
        for i, (what, key) in enumerate(rows):
            y = keys.y + s(44) + i * s(26)
            gfx.blit_text(surf, "cond", 17, what, MUTED, (keys.x + s(18), y))
            gfx.blit_text(surf, "cond", 17, key, WHITE, (keys.right - s(18), y), "topright")
        gfx.blit_text(surf, "cond", 17, "Changing the music plays it so you can listen", HINT,
                      (gfx.W / 2 + s(270), s(660)), "center")
        self.back_btn.draw(surf, mouse, pygame.mouse.get_pressed()[0])


# ------------------------------------------------------------- trophy room
class TrophyRoom:
    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        self.back_btn = Button("BACK", (s(170), gfx.H - s(50)), (230, 60), "gray")
        self.cups = {}

    def cup(self, size, got):
        key = (size, got)
        if key not in self.cups:
            import sprites
            img = sprites.trophy(size)
            if not got:
                img = img.copy()
                img.fill((90, 92, 98, 255), special_flags=pygame.BLEND_RGBA_MIN)
            self.cups[key] = img
        return self.cups[key]

    def handle(self, ev):
        if (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)) or \
                (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.back_btn.hit(ev.pos)):
            self.app.audio.play("click")
            self.app.goto("home")

    def draw(self, surf, mouse, now):
        from progress import ACHIEVEMENTS, stat
        app = self.app
        data = app.data
        surf.blit(self.bg, (0, 0))
        got = len(data["achievements"])
        top_bar(surf, app, f"TROPHY ROOM  ·  {got}/{len(ACHIEVEMENTS)} ACHIEVEMENTS")
        cw, ch, gap = 228, 112, 12
        for i, (key, title, desc, reward, (st, target)) in enumerate(ACHIEVEMENTS):
            r = pygame.Rect(s(30) + (i % 4) * s(cw + gap), s(80) + (i // 4) * s(ch + gap), s(cw), s(ch))
            done = key in data["achievements"]
            glass(surf, r, 14, fill=(64, 58, 24) if done else PANEL)
            if done:
                pygame.draw.rect(surf, GOLD, r, si(2), border_radius=si(12))
            cup = self.cup(int(s(46)), done)
            surf.blit(cup, cup.get_rect(midleft=(r.x + s(10), r.y + s(40))))
            name = gfx.text("cond", 19, title.upper(), GOLD if done else WHITE)
            if name.get_width() > r.w - s(70):
                name = pygame.transform.smoothscale_by(name, (r.w - s(70)) / name.get_width())
            surf.blit(name, (r.x + s(64), r.y + s(12)))
            d = gfx.text("cond", 14, desc, MUTED)
            if d.get_width() > r.w - s(70):
                d = pygame.transform.smoothscale_by(d, (r.w - s(70)) / d.get_width())
            surf.blit(d, (r.x + s(64), r.y + s(40)))
            bar = pygame.Rect(r.x + s(12), r.bottom - s(24), r.w - s(24), s(10))
            pygame.draw.rect(surf, (20, 22, 26), bar, border_radius=si(5))
            f = min(1.0, stat(data, st) / target)
            fill = bar.copy()
            fill.w = max(si(4), int(bar.w * f))
            pygame.draw.rect(surf, GOLD if done else (90, 200, 60), fill, border_radius=si(5))
            label = "DONE" if done else f"+{reward:,}"
            gfx.blit_text(surf, "cond", 13, label, WHITE, (bar.right, bar.y - s(2)), "bottomright")
        panel = pygame.Rect(s(30) + 4 * s(cw + gap), s(80), gfx.W - (s(30) + 4 * s(cw + gap)) - s(30), s(4 * (ch + gap) - gap))
        glass(surf, panel)
        total = sum(len(v) for v in data["trophies"].values())
        gfx.blit_text(surf, "cond", 20, f"SECRET TROPHIES  {total}/{5 * len(STAGES)}", GOLD, (panel.x + s(14), panel.y + s(12)))
        for i, st in enumerate(STAGES):
            y = panel.y + s(52) + i * s(52)
            n = len(data["trophies"].get(st["key"], []))
            gfx.blit_text(surf, "cond", 18, st["name"], WHITE, (panel.x + s(14), y))
            for k in range(5):
                c = self.cup(int(s(22)), k < n)
                surf.blit(c, (panel.x + s(14) + k * s(26), y + s(22)))
        gfx.blit_text(surf, "cond", 16, "Secret trophies hide high in the air, over lava and in tunnels - jump for them!",
                      HINT, (gfx.W / 2 + s(120), gfx.H - s(50)), "center")
        self.back_btn.draw(surf, mouse, pygame.mouse.get_pressed()[0])


# ------------------------------------------------------------- leaderboard
class Leaderboard:
    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        self.sel = Selector("MAP", (gfx.W / 2, s(120)), 420)
        self.back_btn = Button("BACK", (s(170), gfx.H - s(50)), (230, 60), "gray")
        self.stage_i = 0

    def enter(self):
        keys = [st["key"] for st in STAGES]
        self.stage_i = keys.index(self.app.data["stage"]) if self.app.data["stage"] in keys else 0
        self.app.relay.watch_leaderboard()

    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("home")
            elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.stage_i = (self.stage_i + (1 if ev.key == pygame.K_RIGHT else -1)) % len(STAGES)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("home")
            d = self.sel.hit(ev.pos)
            if d:
                self.stage_i = (self.stage_i + d) % len(STAGES)
                app.audio.play("click")

    def draw(self, surf, mouse, now):
        from config import VEHICLE_BY_KEY
        app = self.app
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "WORLD LEADERBOARD")
        st = STAGES[self.stage_i]
        self.sel.draw(surf, st["name"].upper())
        rows = sorted(app.relay.leaderboard.get(st["key"], {}).items(), key=lambda kv: -kv[1]["best"])
        me = app.data["player_id"]
        panel = pygame.Rect(0, 0, s(760), s(430))
        panel.midtop = (gfx.W / 2, s(160))
        glass(surf, panel)
        if not app.relay.online:
            gfx.blit_text(surf, "cond", 22, "Connecting to the internet...", MUTED, panel.center, "center")
        elif not rows:
            gfx.blit_text(surf, "cond", 22, "No records yet - be the first!", MUTED, panel.center, "center")
        shown = rows[:12]
        my_rank = next((i for i, (num, _) in enumerate(rows) if num == me), None)
        if my_rank is not None and my_rank >= 12:
            shown = rows[:11] + [rows[my_rank]]
        medals = [(255, 204, 48), (200, 206, 214), (210, 140, 80)]
        for i, (num, e) in enumerate(shown):
            rank = rows.index((num, e)) + 1
            y = panel.y + s(18) + i * s(34)
            mine = num == me
            if mine:
                pygame.draw.rect(surf, (60, 56, 30), (panel.x + s(10), y - s(4), panel.w - s(20), s(32)),
                                 border_radius=si(8))
            col = medals[rank - 1] if rank <= 3 else (110, 114, 122)
            pygame.draw.circle(surf, col, (panel.x + s(36), y + s(12)), s(13))
            gfx.blit_text(surf, "cond", 17, str(rank), INK, (panel.x + s(36), y + s(12)), "center")
            name = str(e.get("name", "?"))[:18] + ("  (you)" if mine else "")
            gfx.blit_text(surf, "cond", 21, name, GOLD if mine else WHITE, (panel.x + s(64), y + s(12)), "midleft")
            veh = VEHICLE_BY_KEY.get(e.get("vehicle"), {"name": ""})["name"]
            gfx.blit_text(surf, "cond", 16, veh, MUTED, (panel.right - s(170), y + s(12)), "midright")
            gfx.blit_text(surf, "cond", 22, f"{e['best']} m", WHITE, (panel.right - s(20), y + s(12)), "midright")
        gfx.blit_text(surf, "cond", 16, "Best distance per map, from every Hill Rider player. Your records upload "
                      "automatically.", HINT, (gfx.W / 2 + s(100), gfx.H - s(50)), "center")
        self.back_btn.draw(surf, mouse, pygame.mouse.get_pressed()[0])
