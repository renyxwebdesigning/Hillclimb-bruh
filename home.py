"""Home menu: the title screen, with a live demo drive running behind the menu."""
import copy
import math
import random

import pygame

import gfx
import lang
import lighting
import sprites
from config import DAY_LENGTH, STAGES, TITLE, VERSION, VEHICLE_BY_KEY, WEB
from drivers import DRIVER_BY_KEY, face
from game import Run
from gfx import s, si
from render import CarView
from ui import GOLD, INK, MUTED, NAVY, PANEL, PANEL_EDGE, WHITE, Button, glass, toggles_hit, top_bar, upgrade_icon

TILES = [("GARAGE", "garage"), ("TROPHIES", "trophies"), ("RANKING", "leaderboard"), ("SETTINGS", "settings")] + \
        ([] if WEB else [("QUIT", "quit")])


def _play_icon(h):
    def draw(surf, k):
        w, hh = surf.get_size()
        pygame.draw.polygon(surf, NAVY, [(w * 0.12, hh * 0.06), (w * 0.98, hh * 0.52), (w * 0.12, hh * 0.98)])
        pygame.draw.polygon(surf, WHITE, [(w * 0.16, hh * 0.14), (w * 0.86, hh * 0.5), (w * 0.16, hh * 0.86)])
    return gfx.supersample(h * 0.9, h, draw)


def _tile_icon(key, size):
    """Icons for the bottom dock, drawn in code like everything else."""
    if key == "garage":
        return upgrade_icon("engine", size)
    if key == "trophies":
        return sprites.trophy(int(size * 0.9))

    def draw(surf, k):
        w, h = surf.get_size()
        c = (w / 2, h / 2)
        if key == "leaderboard":
            for x, top, col in ((0.18, 0.42, (200, 206, 216)), (0.5, 0.18, (255, 204, 48)), (0.82, 0.56, (214, 140, 80))):
                r = pygame.Rect(0, 0, w * 0.28, h * (0.92 - top))
                r.midbottom = (w * x, h * 0.92)
                pygame.draw.rect(surf, NAVY, r.inflate(w * 0.06, h * 0.06), border_radius=int(w * 0.05))
                pygame.draw.rect(surf, col, r, border_radius=int(w * 0.04))
        elif key == "settings":
            R = w * 0.42
            for i in range(8):
                a = i * math.pi / 4
                tooth = [(c[0] + math.cos(a + d) * R * rr, c[1] + math.sin(a + d) * R * rr)
                         for d, rr in ((-0.22, 0.78), (-0.15, 1.0), (0.15, 1.0), (0.22, 0.78))]
                pygame.draw.polygon(surf, (220, 228, 240), tooth)
            pygame.draw.circle(surf, (220, 228, 240), c, R * 0.8)
            pygame.draw.circle(surf, (60, 110, 190), c, R * 0.34)
        elif key == "quit":
            R = w * 0.36
            pygame.draw.arc(surf, (255, 110, 90), pygame.Rect(c[0] - R, c[1] - R, 2 * R, 2 * R), -1.0, 4.14,
                            max(2, int(w * 0.1)))
            pygame.draw.line(surf, (255, 110, 90), (c[0], c[1] - R * 1.15), (c[0], c[1] - R * 0.15), max(2, int(w * 0.1)))
    return gfx.supersample(size, size, draw)


class Tile:
    """A square dock button: icon on top, label underneath."""

    def __init__(self, label, key, rect):
        self.label, self.key, self.rect = label, key, rect
        self.icon = _tile_icon(key, int(rect.w * 0.5))

    def draw(self, surf, hover, focus):
        r = self.rect.move(0, -s(4) if hover else 0)
        glass(surf, r, 18, selected=focus, hover=hover)
        surf.blit(self.icon, self.icon.get_rect(center=(r.centerx, r.y + r.h * 0.42)))
        lab = gfx.text("black_i", 18, self.label, WHITE, outline=NAVY, width=2)
        if lab.get_width() > r.w - s(10):
            lab = pygame.transform.smoothscale_by(lab, (r.w - s(10)) / lab.get_width())
        surf.blit(lab, lab.get_rect(center=(r.centerx, r.bottom - s(18))))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


class _Silent:
    """Stands in for audio and HUD during the demo drive."""

    def boost(self, *_):
        pass

    def engine_update(self, *_, **__):
        pass

    def play(self, *_, **__):
        pass

    def say(self, *_, **__):
        return "", 0

    def bonus(self, *_):
        pass

    def notice(self, *_):
        pass


class HomeMenu:
    def __init__(self, app):
        self.app = app
        cx = gfx.W - s(214)
        self.play_btn = Button("PLAY", (cx, gfx.H - s(176)), (360, 116), "green", icon=_play_icon(s(44)), key="setup")
        self.online_btn = Button("PLAY ONLINE", (cx, gfx.H - s(60)), (360, 70), "blue", key="online")
        size, gap = s(116), s(16)
        self.tiles = [Tile(label, key, pygame.Rect(s(32) + i * (size + gap), gfx.H - s(24) - size, size, size))
                      for i, (label, key) in enumerate(TILES)]
        self.items = [self.play_btn, self.online_btn] + self.tiles      # keyboard order
        self.focus = 0
        self.shade = self._shade()
        self.demo = None
        self.demo_stage = random.randrange(len(STAGES))
        self.still_t = 0.0
        self.face_img = None
        self.face_key = None
        self.daily_rect = None

    @staticmethod
    def _shade():
        """Soft darkening behind the logo (top left) and the dock (bottom), so text stays readable."""
        surf = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (8, 24, 64, 80), (-gfx.W * 0.2, -gfx.H * 0.25, gfx.W * 0.75, gfx.H * 0.8))
        surf = pygame.transform.smoothscale(pygame.transform.smoothscale(surf, (gfx.W // 16, gfx.H // 16)),
                                            (gfx.W, gfx.H))
        bottom = gfx.vgradient(gfx.W, int(gfx.H * 0.3), (8, 24, 64, 0), (8, 24, 64, 170)).convert_alpha()
        surf.blit(bottom, (0, gfx.H - bottom.get_height()))
        return surf

    # ---------------------------------------------------------------- demo
    def _new_demo(self):
        app = self.app
        self.demo_stage = (self.demo_stage + 1) % len(STAGES)
        stage = STAGES[self.demo_stage]
        terrain, self.world = app.world_for(stage)
        spec = app.vehicle
        quiet = _Silent()
        self.demo = Run(stage, terrain, spec, app.data["levels"][spec["key"]], 0, 0, quiet, quiet,
                        driver=app.data["driver"])
        self.demo.time = random.uniform(0, DAY_LENGTH)
        self.demo_start = self.demo.time
        self.demo_key = (spec["key"], app.data["driver"])
        self.still_t = 0.0

    def _drive(self, dt):
        run = self.demo
        car = run.car
        gas, brake = True, False
        if car.angle > 0.55:
            gas, brake = False, not car.grounded
        if car.angle < -0.45 and not car.grounded:
            gas = True
        boost = car.grounded and abs(car.angle) < 0.2 and run.boost > 0.6
        run.update(dt, gas, brake, boost)
        self.still_t = self.still_t + dt if math.hypot(car.vx, car.vy) < 0.5 else 0.0
        if run.state != "drive" or self.still_t > 2.5 or run.time - self.demo_start > 45:
            self._new_demo()

    # -------------------------------------------------------------- events
    def handle(self, ev):
        app = self.app
        n = len(self.items)
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                self.focus = (self.focus + 1) % n
                app.audio.play("click")
            elif ev.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                self.focus = (self.focus - 1) % n
                app.audio.play("click")
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate(self.items[self.focus].key)
            elif ev.key == pygame.K_ESCAPE and not WEB:
                app.quit()
        elif ev.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.items):
                if b.hit(ev.pos):
                    self.focus = i
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.daily_rect and self.daily_rect.collidepoint(ev.pos) and not app.progress.daily_done():
                app.start_daily()
                return
            for b in self.items:
                if b.hit(ev.pos):
                    self.activate(b.key)
                    return

    def activate(self, key):
        self.app.audio.play("click")
        if key == "quit":
            self.app.quit()
        else:
            self.app.goto(key)

    # ---------------------------------------------------------------- draw
    def draw(self, surf, mouse, now):
        app = self.app
        dt = 1 / 60
        if self.demo is None or self.demo_key != (app.data["vehicle"], app.data["driver"]):
            self._new_demo()
        self._drive(dt)
        run = self.demo
        darkness, sunset = lighting.phase_info(run.stage, run.time)
        cam = copy.copy(run.cam)
        cam.x -= gfx.W * 0.04 / cam.ppm             # car in the middle, between the logo and PLAY
        lights = darkness > 0.22 or run.terrain.feature_at(run.car.x) == "tunnel"
        view = CarView(run.car, run.driver, run.wobble, lights)
        self.world.clock, self.world.broken = run.time, run.broken
        self.world.draw(surf, cam, [view], run.particles, now, dt, 0, darkness, sunset)
        surf.blit(self.shade, (0, 0))
        top_bar(surf, app, "")
        logo = gfx.text("black_i", 96, TITLE.upper(), WHITE, outline=(176, 24, 30), width=6, shadow=6)
        surf.blit(logo, logo.get_rect(topleft=(s(36), s(86))))
        gfx.blit_text(surf, "black_i", 26, "Climb  ·  Flip  ·  Race your friends", GOLD,
                      (s(48), s(200)), "topleft", outline=NAVY, width=2.5)
        self._info_card(surf)
        self._daily_card(surf, mouse)
        pressed = pygame.mouse.get_pressed()[0]
        for i, b in enumerate([self.play_btn, self.online_btn]):
            focus = self.items[self.focus] is b
            if focus and not b.rect.collidepoint(mouse):
                pygame.draw.rect(surf, GOLD, b.rect.inflate(s(12), s(12)), si(4), border_radius=si(22))
            b.draw(surf, mouse, pressed and b.rect.collidepoint(mouse))
        for t in self.tiles:
            t.draw(surf, t.rect.collidepoint(mouse), self.items[self.focus] is t)
        gfx.blit_text(surf, "heavy", 14, f"v{VERSION}", (200, 214, 240), (gfx.W - s(12), gfx.H - s(6)), "bottomright",
                      outline=NAVY, width=1)

    def _daily_card(self, surf, mouse):
        app = self.app
        d = app.progress.daily()
        done = app.progress.daily_done()
        card = pygame.Rect(0, 0, s(380), s(168))
        card.topright = (gfx.W - s(28), s(84))
        glass(surf, card, 20, fill=(70, 46, 12))
        pygame.draw.rect(surf, GOLD, card, si(3), border_radius=si(20))
        gfx.blit_text(surf, "black_i", 22, "DAILY CHALLENGE", GOLD, (card.x + s(18), card.y + s(10)), outline=NAVY, width=2)
        gfx.blit_text(surf, "heavy", 17, f"+{d['reward']:,}", WHITE, (card.right - s(44), card.y + s(14)), "topright")
        surf.blit(app.coin_icon_small, app.coin_icon_small.get_rect(midright=(card.right - s(16), card.y + s(25))))
        words, lines, line = lang.tr(d["text"]).split(), [], ""   # translate first, then wrap
        for w in words:
            test = (line + " " + w).strip()
            if gfx.text("heavy", 18, test, WHITE).get_width() > card.w - s(36):
                lines.append(line)
                line = w
            else:
                line = test
        lines.append(line)
        for i, ln in enumerate(lines[:2]):
            gfx.blit_text(surf, "heavy", 18, ln, WHITE, (card.x + s(18), card.y + s(46) + i * s(24)))
        self.daily_rect = pygame.Rect(card.x + s(18), card.bottom - s(54), card.w - s(36), s(40))
        r = self.daily_rect
        if done:
            pygame.draw.rect(surf, (40, 70, 40), r, border_radius=si(12))
            gfx.blit_text(surf, "black_i", 18, "DONE - COME BACK TOMORROW", (170, 240, 120), r.center, "center")
        else:
            hover = r.collidepoint(mouse)
            pygame.draw.rect(surf, NAVY, r.move(0, s(4)), border_radius=si(12))
            pygame.draw.rect(surf, (120, 226, 70) if hover else (84, 190, 46), r, border_radius=si(12))
            gfx.blit_text(surf, "black_i", 20, "PLAY CHALLENGE", WHITE, r.center, "center", outline=NAVY, width=2)

    def _info_card(self, surf):
        """Who is driving what, plus progress at a glance."""
        app = self.app
        card = pygame.Rect(s(36), s(248), s(400), s(136))
        glass(surf, card, 20)
        key = (app.data["driver"], app.data["vehicle"])
        if self.face_key != key:
            d = app.data["driver"]
            self.face_img = face(d, s(26)) if d != "default" else None
            self.face_key = key
        x = card.x + s(18)
        if self.face_img:
            clip = surf.get_clip()
            surf.set_clip(card.inflate(-s(4), -s(4)))
            surf.blit(self.face_img, self.face_img.get_rect(center=(card.x + s(62), card.y + s(66))))
            surf.set_clip(clip)
            x = card.x + s(118)
        name = DRIVER_BY_KEY.get(app.data["driver"], {"name": "Racer"})["name"]
        gfx.blit_text(surf, "heavy", 15, "YOUR RIDE", MUTED, (x, card.y + s(14)))
        gfx.blit_text(surf, "black_i", 26, VEHICLE_BY_KEY[app.data["vehicle"]]["name"].upper(), WHITE, (x, card.y + s(34)),
                      outline=NAVY, width=2)
        gfx.blit_text(surf, "heavy", 17, f"driven by {name}", (150, 210, 255), (x, card.y + s(70)))
        from progress import ACHIEVEMENTS
        got = sum(a[0] in app.data.get("achievements", []) for a in ACHIEVEMENTS)
        trophies = sum(len(v) for v in app.data.get("trophies", {}).values())
        gfx.blit_text(surf, "heavy", 15, f"Achievements {got}/{len(ACHIEVEMENTS)}   ·   Trophies {trophies}/{5 * len(STAGES)}",
                      GOLD, (x, card.y + s(100)))
