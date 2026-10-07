"""Home menu: the title screen, with a live demo drive running behind the menu."""
import copy
import math
import random

import pygame

import gfx
import lighting
from config import DAY_LENGTH, STAGES, TITLE, VEHICLE_BY_KEY
from drivers import DRIVER_BY_KEY, face
from game import Run
from gfx import s, si
from render import CarView
from ui import GOLD, INK, MUTED, WHITE, Button, toggles_hit

ITEMS = [("PLAY", "setup"), ("PLAY ONLINE", "online"), ("GARAGE", "garage"), ("TROPHIES", "trophies"),
         ("LEADERBOARD", "leaderboard"), ("SETTINGS", "settings"), ("QUIT", "quit")]


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
        x = s(250)
        self.buttons = [Button(label, (x, s(262) + i * s(60)), (330, 50), "green" if i == 0 else "gray", key=key)
                        for i, (label, key) in enumerate(ITEMS)]
        self.focus = 0
        self.panel = self._panel()
        self.demo = None
        self.demo_stage = random.randrange(len(STAGES))
        self.still_t = 0.0
        self.face_img = None
        self.face_key = None
        self.daily_rect = None

    @staticmethod
    def _panel():
        w = int(gfx.W * 0.42)
        surf = pygame.Surface((w, gfx.H), pygame.SRCALPHA)
        for x in range(w):
            a = int(210 * (1 - x / w) ** 1.4)
            pygame.draw.line(surf, (12, 14, 20, a), (x, 0), (x, gfx.H))
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
        self.demo._safe_until = 1e9                 # no seized engines in the demo
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
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.focus = (self.focus + 1) % len(ITEMS)
                app.audio.play("click")
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.focus = (self.focus - 1) % len(ITEMS)
                app.audio.play("click")
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate(ITEMS[self.focus][1])
            elif ev.key == pygame.K_ESCAPE:
                app.quit()
        elif ev.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.hit(ev.pos):
                    self.focus = i
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if toggles_hit(app, ev.pos):
                return
            if self.daily_rect and self.daily_rect.collidepoint(ev.pos) and not app.progress.daily_done():
                app.start_daily()
                return
            for b in self.buttons:
                if b.hit(ev.pos):
                    self.activate(b.key)

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
        cam.x -= gfx.W * 0.17 / cam.ppm             # keep the car right of the menu
        lights = darkness > 0.22 or run.terrain.feature_at(run.car.x) == "tunnel"
        view = CarView(run.car, run.driver, run.wobble, lights)
        self.world.draw(surf, cam, [view], run.particles, now, dt, 0, darkness, sunset)
        surf.blit(self.panel, (0, 0))

        logo = gfx.text("black_i", 92, TITLE.upper(), WHITE, outline=(170, 28, 30), width=5, shadow=5)
        surf.blit(logo, logo.get_rect(midleft=(s(48), s(120))))
        gfx.blit_text(surf, "cond_i", 24, "Climb  ·  Flip  ·  Race your friends", (255, 214, 120),
                      (s(58), s(186)), "midleft", outline=INK, width=2)
        pressed = pygame.mouse.get_pressed()[0]
        for i, b in enumerate(self.buttons):
            b.draw(surf, mouse if i != self.focus else b.rect.center, pressed and b.rect.collidepoint(mouse))
            if i == self.focus:
                pygame.draw.polygon(surf, GOLD, [(b.rect.x - s(26), b.rect.centery - s(10)),
                                                 (b.rect.x - s(10), b.rect.centery),
                                                 (b.rect.x - s(26), b.rect.centery + s(10))])
        self._info_card(surf)
        self._daily_card(surf, mouse)
        self._toggles(surf)
        hint = "Tap a button" if app.hud.touch_mode else "Arrow keys + Enter, or click"
        gfx.blit_text(surf, "cond", 15, hint, (190, 194, 202),
                      (s(58), gfx.H - s(22)), "midleft", outline=INK, width=1)

    def _daily_card(self, surf, mouse):
        app = self.app
        d = app.progress.daily()
        done = app.progress.daily_done()
        card = pygame.Rect(0, 0, s(360), s(150))
        card.bottomright = (gfx.W - s(24), gfx.H - s(258))
        box = pygame.Surface(card.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (14, 16, 22, 200), box.get_rect(), border_radius=si(16))
        surf.blit(box, card)
        pygame.draw.rect(surf, GOLD, card, si(2), border_radius=si(16))
        gfx.blit_text(surf, "cond", 18, "DAILY CHALLENGE", GOLD, (card.x + s(16), card.y + s(12)))
        gfx.blit_text(surf, "cond", 16, f"+{d['reward']:,} coins", WHITE, (card.right - s(16), card.y + s(13)), "topright")
        words, lines, line = d["text"].split(), [], ""
        for w in words:
            test = (line + " " + w).strip()
            if gfx.text("cond", 18, test, WHITE).get_width() > card.w - s(32):
                lines.append(line)
                line = w
            else:
                line = test
        lines.append(line)
        for i, ln in enumerate(lines[:2]):
            gfx.blit_text(surf, "cond", 18, ln, WHITE, (card.x + s(16), card.y + s(40) + i * s(24)))
        self.daily_rect = pygame.Rect(card.x + s(16), card.bottom - s(44), card.w - s(32), s(32))
        if done:
            pygame.draw.rect(surf, (60, 64, 70), self.daily_rect, border_radius=si(8))
            gfx.blit_text(surf, "cond", 18, "DONE - COME BACK TOMORROW", (170, 230, 120), self.daily_rect.center, "center")
        else:
            hover = self.daily_rect.collidepoint(mouse)
            pygame.draw.rect(surf, (100, 210, 70) if hover else (76, 170, 46), self.daily_rect, border_radius=si(8))
            gfx.blit_text(surf, "cond", 18, "PLAY CHALLENGE", WHITE, self.daily_rect.center, "center")

    def _toggles(self, surf):
        app = self.app
        sound = app.speaker[app.data["sound"]]
        app.sound_rect = sound.get_rect(topright=(gfx.W - s(22), s(20)))
        note = app.note[app.data["music"]]
        app.music_rect = note.get_rect(topright=(app.sound_rect.left - s(22), s(20)))
        icons = [(sound, app.sound_rect), (note, app.music_rect)]
        if app.fs_available():
            fs = app.fs_icon[app.is_fullscreen()]
            app.fs_rect = fs.get_rect(topright=(app.music_rect.left - s(22), s(20)))
            icons.append((fs, app.fs_rect))
        for img, r in icons:
            bg = r.inflate(s(16), s(14))
            pygame.draw.rect(surf, (12, 14, 20), bg, border_radius=si(10))
            surf.blit(img, r)

    def _info_card(self, surf):
        app = self.app
        card = pygame.Rect(0, 0, s(360), s(220))
        card.bottomright = (gfx.W - s(24), gfx.H - s(24))
        box = pygame.Surface(card.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (14, 16, 22, 200), box.get_rect(), border_radius=si(16))
        surf.blit(box, card)
        x, y = card.x + s(18), card.y + s(16)
        relay = app.relay
        pygame.draw.circle(surf, (90, 220, 70) if relay.online else (230, 160, 40), (x + s(6), y + s(12)), s(6))
        r = gfx.blit_text(surf, "cond", 22, f"#{app.data['player_id']}", GOLD, (x + s(20), y + s(12)), "midleft")
        from config import WEB
        status = "browser" if WEB else "online" if relay.online else "connecting..."
        gfx.blit_text(surf, "cond", 16, status, MUTED,
                      (r.right + s(8), y + s(13)), "midleft")
        surf.blit(app.coin_icon, app.coin_icon.get_rect(midright=(card.right - s(70), y + s(12))))
        gfx.blit_text(surf, "cond", 22, gfx.fmt(app.data["coins"]), WHITE, (card.right - s(18), y + s(12)), "midright")
        key = (app.data["driver"], app.data["vehicle"])
        if self.face_key != key:
            d = app.data["driver"]
            self.face_img = face(d, s(19)) if d != "default" else None
            self.face_key = key
        y += s(44)
        if self.face_img:
            clip = surf.get_clip()
            surf.set_clip(card)
            surf.blit(self.face_img, self.face_img.get_rect(center=(x + s(26), y + s(18))))
            surf.set_clip(clip)
        name = DRIVER_BY_KEY.get(app.data["driver"], {"name": "Racer"})["name"]
        tx = x + (s(64) if self.face_img else 0)
        gfx.blit_text(surf, "cond", 20, VEHICLE_BY_KEY[app.data["vehicle"]]["name"].upper(), WHITE, (tx, y), "topleft")
        gfx.blit_text(surf, "cond", 16, f"driven by {name}", MUTED, (tx, y + s(24)), "topleft")
        y += s(62)
        from progress import ACHIEVEMENTS
        bests = [(b, k) for k, b in app.data["best"].items() if b]
        top = max(bests) if bests else None
        st_name = next((st["name"] for st in STAGES if top and st["key"] == top[1]), "")
        rows = [("Best run", f"{top[0]} m  ({st_name})" if top else "-"),
                ("Achievements", f"{len(app.data.get('achievements', []))} / {len(ACHIEVEMENTS)}"),
                ("Secret trophies", f"{sum(len(v) for v in app.data.get('trophies', {}).values())} / {5 * len(STAGES)}")]
        for i, (label, value) in enumerate(rows):
            gfx.blit_text(surf, "cond", 16, label, MUTED, (x, y + i * s(25)), "topleft")
            gfx.blit_text(surf, "cond", 17, value, WHITE, (card.right - s(18), y + i * s(25)), "topright")
