"""Story mode screens: the Blacklist, a city with its events and rival, the story garage, results, HUD."""
import math

import pygame

import gfx
import story
from config import UPGRADES
from gfx import s, si
from render import compose_vehicle
from ui import Button, Garage, scene, top_bar, vehicle_on_scene

BG_TOP, BG_BOTTOM = (26, 26, 32), (8, 8, 12)
PANEL = (34, 34, 42)
EDGE = (70, 70, 84)
YELLOW = (255, 200, 30)
RED = (230, 50, 40)
GREEN = (110, 230, 110)
WHITE = (255, 255, 255)
MUTED = (160, 162, 176)
INK = (10, 10, 14)


def background(w, h):
    """Dark asphalt with yellow hazard slashes along the bottom."""
    surf = gfx.opaque(gfx.vgradient(w, h, BG_TOP, BG_BOTTOM))
    for i in range(-2, int(w / s(60)) + 3):
        x = i * s(60)
        pygame.draw.polygon(surf, (40, 36, 16), [(x, h), (x + s(30), h), (x + s(60), h - s(14)), (x + s(30), h - s(14))])
    return surf


def card(surf, rect, edge=EDGE, fill=PANEL, width=2):
    pygame.draw.rect(surf, (0, 0, 0), rect.move(0, s(4)), border_radius=si(10))
    pygame.draw.rect(surf, fill, rect, border_radius=si(10))
    pygame.draw.rect(surf, edge, rect, max(1, si(width)), border_radius=si(10))


def wrap(text, size, width, font="heavy"):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if gfx.text(font, size, test, WHITE).get_width() > width:
            lines.append(line)
            line = w
        else:
            line = test
    lines.append(line)
    return lines


def rating_bar(surf, x, y, w, label, value, top, color):
    gfx.blit_text(surf, "heavy", 15, label, MUTED, (x, y))
    bar = pygame.Rect(x, y + s(20), w, s(12))
    pygame.draw.rect(surf, (20, 20, 26), bar, border_radius=si(6))
    fill = bar.copy()
    fill.w = max(s(6), int(w * min(1.0, value / top)))
    pygame.draw.rect(surf, color, fill, border_radius=si(6))


def money(v):
    return f"$ {gfx.fmt(v)}"


# ------------------------------------------------------------------ Blacklist
class StoryHub:
    """The Blacklist: ten racers, the one you are after, and the way to their city."""

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        self.back_btn = Button("BACK", (s(150), gfx.H - s(50)), (220, 60), "gray")
        self.garage_btn = Button("GARAGE", (gfx.W / 2, gfx.H - s(50)), (240, 60), "dark")
        self.go_btn = None
        self.rows = []
        self.cache = {}
        self.intro_ok = Button("LET'S GO", (gfx.W / 2, gfx.H * 0.44 + s(112)), (280, 66), "yellow")

    @property
    def st(self):
        return story.state(self.app.data)

    def handle(self, ev):
        app, st = self.app, self.st
        if not st["intro_seen"]:
            if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.intro_ok.hit(ev.pos)) or \
                    (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE)):
                st["intro_seen"] = True
                app.persist()
                app.audio.play("click")
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("home")
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                app.open_city(story.current_city(st))
            elif ev.key == pygame.K_g:
                app.goto("story_garage")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("home")
            elif self.garage_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("story_garage")
            elif self.go_btn is not None and self.go_btn.hit(ev.pos):
                app.open_city(story.current_city(st))
            else:
                for city, r in self.rows:
                    if r.collidepoint(ev.pos) and story.city_index(city) <= st["beaten"]:
                        app.open_city(city)

    def _target_art(self, city, w, h):
        key = ("target", city["key"])
        if key not in self.cache:
            img, _ = scene(city["stage"], w, h)
            spec = story.CAR_BY_KEY[city["car"]]
            k = h * 0.32 / 2.0
            car, (cx, cy) = compose_vehicle(self.app.art, spec, k / self.app.art.ppm, story.rival_levels())
            img.blit(car, (w / 2 - cx, h * 0.8 - cy))
            self.cache[key] = img
        return self.cache[key]

    def draw(self, surf, mouse, now):
        app, st = self.app, self.st
        surf.blit(self.bg, (0, 0))
        top_bar(surf, app, "BLACKLIST", cash=st["cash"])
        # the list: #1 at the top
        top, bottom = s(84), gfx.H - s(96)
        rh = (bottom - top) / len(story.CITIES)
        lw = s(560)
        self.rows = []
        beaten = st["beaten"]
        for n, city in enumerate(reversed(story.CITIES)):
            i = story.city_index(city)
            r = pygame.Rect(s(24), top + n * rh + s(2), lw, rh - s(4))
            self.rows.append((city, r))
            done, target = i < beaten, i == beaten
            edge = YELLOW if target else (60, 140, 60) if done else EDGE
            fill = (48, 44, 22) if target else PANEL
            if r.collidepoint(mouse) and i <= beaten:
                fill = gfx.shade(fill, 1.25)
            card(surf, r, edge, fill, 3 if target else 2)
            gfx.blit_text(surf, "black_i", 34, f"#{city['rank']}", YELLOW if target else WHITE if done else MUTED,
                          (r.x + s(14), r.centery), "midleft", outline=INK, width=2)
            name = f"{city['nick'].upper()}  ·  {city['rival']}"
            gfx.blit_text(surf, "black_i", 20, name, WHITE if i <= beaten else MUTED, (r.x + s(96), r.y + s(5)))
            gfx.blit_text(surf, "heavy", 15, f"{city['name']}  ·  {story.CAR_BY_KEY[city['car']]['name']}", MUTED,
                          (r.x + s(96), r.y + s(30)))
            tag, col = ("BEATEN", GREEN) if done else ("TARGET", YELLOW) if target else ("LOCKED", (110, 110, 120))
            if target and int(now * 2) % 2:
                col = gfx.shade(YELLOW, 0.8)
            gfx.blit_text(surf, "black_i", 18, tag, col, (r.right - s(14), r.centery), "midright", outline=INK, width=2)
        # the target
        panel = pygame.Rect(lw + s(48), top + s(2), gfx.W - lw - s(72), bottom - top - s(4))
        card(surf, panel, YELLOW, (30, 30, 36), 3)
        if beaten >= len(story.CITIES):
            gfx.blit_text(surf, "black_i", 52, "YOU ARE #1", YELLOW, (panel.centerx, panel.y + s(70)), "center",
                          outline=INK, width=3)
            for j, line in enumerate(wrap("Every racer on the Blacklist is beaten and every car is yours. "
                                          "Replay any city to earn cash and max out your collection.", 20,
                                          panel.w - s(60))):
                gfx.blit_text(surf, "heavy", 20, line, WHITE, (panel.centerx, panel.y + s(130) + j * s(28)), "center")
            self.go_btn = None
        else:
            city = story.current_city(st)
            art = self._target_art(city, panel.w - s(28), s(190))
            surf.blit(art, (panel.x + s(14), panel.y + s(14)))
            y = panel.y + s(214)
            gfx.blit_text(surf, "black_i", 34, f"#{city['rank']} {city['nick'].upper()}", YELLOW, (panel.x + s(20), y),
                          outline=INK, width=2)
            gfx.blit_text(surf, "heavy", 18, f"{city['rival']} in {city['name']}  ·  drives the "
                          f"{story.CAR_BY_KEY[city['car']]['name']}", WHITE, (panel.x + s(20), y + s(44)))
            for j, line in enumerate(wrap(f"\"{city['intro']}\"", 17, panel.w - s(40), "cond_i")[:3]):
                gfx.blit_text(surf, "cond_i", 17, line, MUTED, (panel.x + s(20), y + s(76) + j * s(22)))
            mine = story.CAR_BY_KEY[st["car"]]
            rival = story.CAR_BY_KEY[city["car"]]
            r_me = story.rating(mine, st["cars"][st["car"]])
            r_riv = story.rating(rival, story.rival_levels())
            top_r = max(r_me, r_riv) * 1.1
            bx = panel.x + s(20)
            rating_bar(surf, bx, y + s(146), panel.w - s(40), f"YOUR {mine['name'].upper()}", r_me, top_r,
                       GREEN if r_me >= r_riv else (240, 160, 40))
            rating_bar(surf, bx, y + s(186), panel.w - s(40), f"{city['nick'].upper()}'S {rival['name'].upper()}",
                       r_riv, top_r, RED)
            self.go_btn = Button(f"GO TO {city['name'].upper()}", (panel.centerx, panel.bottom - s(44)),
                                 (360, 62), "yellow")
            self.go_btn.draw(surf, mouse, pygame.mouse.get_pressed()[0])
        pressed = pygame.mouse.get_pressed()[0]
        self.back_btn.draw(surf, mouse, pressed)
        self.garage_btn.draw(surf, mouse, pressed)
        if not st["intro_seen"]:
            self._intro(surf, mouse)

    def _intro(self, surf, mouse):
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 200))
        surf.blit(dim, (0, 0))
        box = pygame.Rect(0, 0, s(760), s(330))
        box.center = (gfx.W / 2, gfx.H * 0.44)
        card(surf, box, YELLOW, (24, 24, 30), 3)
        gfx.blit_text(surf, "black_i", 44, "STORY MODE", YELLOW, (box.centerx, box.y + s(44)), "center",
                      outline=INK, width=3)
        for j, line in enumerate(wrap(story.INTRO, 19, box.w - s(70))):
            gfx.blit_text(surf, "heavy", 19, line, WHITE, (box.centerx, box.y + s(96) + j * s(27)), "center")
        self.intro_ok.draw(surf, mouse, pygame.mouse.get_pressed()[0])


# ------------------------------------------------------------------ a city
class CityScreen:
    """Three events that pay cash, and the Blacklist racer once they are all done."""

    def __init__(self, app):
        self.app = app
        self.bg = background(gfx.W, gfx.H)
        self.city = story.CITIES[0]
        self.cards = []
        self.back_btn = Button("BLACKLIST", (s(150), gfx.H - s(50)), (240, 60), "gray")
        self.garage_btn = Button("GARAGE", (gfx.W / 2, gfx.H - s(50)), (240, 60), "dark")
        self.scene_img = None
        self.scene_key = None
        self.confirm = None                       # the rival's trash talk before the race
        self.race_btn = Button("RACE!", (gfx.W / 2 + s(130), gfx.H * 0.72), (230, 64), "yellow")
        self.notyet_btn = Button("NOT YET", (gfx.W / 2 - s(130), gfx.H * 0.72), (230, 64), "gray")

    def enter(self, city):
        self.city = city
        self.confirm = None

    @property
    def st(self):
        return story.state(self.app.data)

    def handle(self, ev):
        app = self.app
        if self.confirm:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.race_btn.hit(ev.pos):
                    app.start_story(self.city, "rival")
                elif self.notyet_btn.hit(ev.pos):
                    self.confirm = None
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    app.start_story(self.city, "rival")
                elif ev.key == pygame.K_ESCAPE:
                    self.confirm = None
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("story")
            elif ev.key == pygame.K_g:
                app.goto("story_garage")
            elif pygame.K_1 <= ev.key <= pygame.K_3:
                app.start_story(self.city, story.EVENT_KINDS[ev.key - pygame.K_1])
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("story")
            elif self.garage_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("story_garage")
            for kind, r, ok in self.cards:
                if r.collidepoint(ev.pos):
                    if kind == "rival":
                        if ok:
                            app.audio.play("click")
                            self.confirm = True
                        else:
                            app.audio.play("deny")
                    else:
                        app.start_story(self.city, kind)

    def draw(self, surf, mouse, now):
        app, st, city = self.app, self.st, self.city
        i = story.city_index(city)
        surf.blit(self.bg, (0, 0))
        levels = st["cars"][st["car"]]
        key = (city["key"], st["car"], tuple(sorted(levels.items())))
        if self.scene_key != key:
            self.scene_img = vehicle_on_scene(app, city["stage"], story.CAR_BY_KEY[st["car"]], gfx.W, s(220), 0.7, levels)
            self.scene_key = key
        surf.blit(self.scene_img, (0, s(64)))
        top_bar(surf, app, f"{city['name'].upper()}  ·  BLACKLIST #{city['rank']}", cash=st["cash"])
        done = story.events_done(st, city)
        beaten = i < st["beaten"]
        n = 4
        gap = s(16)
        cw = (gfx.W - s(48) - gap * (n - 1)) / n
        y, ch = s(300), s(250)
        self.cards = []
        for j, kind in enumerate(story.EVENT_KINDS + ("rival",)):
            r = pygame.Rect(s(24) + j * (cw + gap), y, cw, ch)
            rival = kind == "rival"
            ok = (not rival) or (story.rival_unlocked(st, city) and not beaten)
            self.cards.append((kind, r, ok))
            hover = r.collidepoint(mouse) and ok
            edge = YELLOW if rival and ok else GREEN if (not rival and done[j]) or (rival and beaten) else EDGE
            card(surf, r.move(0, -s(3) if hover else 0), edge, gfx.shade(PANEL, 1.2) if hover else PANEL, 3 if rival else 2)
            r = r.move(0, -s(3) if hover else 0)
            gfx.blit_text(surf, "black_i", 22, story.EVENT_TITLES[kind], YELLOW if rival else WHITE,
                          (r.centerx, r.y + s(24)), "center", outline=INK, width=2)
            ev = story.event(city, kind)
            lines = wrap(story.EVENT_INFO[kind], 15, r.w - s(24))
            for k, line in enumerate(lines[:2]):
                gfx.blit_text(surf, "heavy", 15, line, MUTED, (r.centerx, r.y + s(52) + k * s(20)), "center")
            info = f"{ev['distance']} m"
            if kind == "trial":
                info += f"  ·  {ev['limit']} s"
            gfx.blit_text(surf, "black_i", 26, info, WHITE, (r.centerx, r.y + s(112)), "center")
            if rival:
                gfx.blit_text(surf, "heavy", 15, f"{city['nick'].upper()}  ·  {story.CAR_BY_KEY[city['car']]['name']}",
                              WHITE, (r.centerx, r.y + s(146)), "center")
                prize = f"WIN: THE {story.CAR_BY_KEY[city['car']]['name'].upper()}"
                gfx.blit_text(surf, "heavy", 14, prize, GREEN, (r.centerx, r.y + s(170)), "center")
                status = "BEATEN" if beaten else "CHALLENGE" if ok else "FINISH ALL 3 EVENTS"
            else:
                first = not done[j]
                gfx.blit_text(surf, "black_i", 24, money(story.pay(i, kind, first)), GREEN, (r.centerx, r.y + s(150)),
                              "center", outline=INK, width=2)
                status = "NEW" if first else "DONE  ·  REPLAY"
            bar = pygame.Rect(r.x + s(12), r.bottom - s(48), r.w - s(24), s(36))
            col = (60, 140, 60) if status.startswith(("DONE", "BEATEN")) else YELLOW if ok else (70, 70, 80)
            pygame.draw.rect(surf, col, bar, border_radius=si(8))
            gfx.blit_text(surf, "black_i", 18, status, INK if col == YELLOW else WHITE, bar.center, "center")
        hint = "Click an event (or 1-3) to race  ·  win cash, upgrade your car in the GARAGE, then take on the rival"
        gfx.blit_text(surf, "cond", 16, hint, MUTED, (gfx.W / 2, s(574)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.back_btn.draw(surf, mouse, pressed)
        self.garage_btn.draw(surf, mouse, pressed)
        if self.confirm:
            self._trash_talk(surf, mouse)

    def _trash_talk(self, surf, mouse):
        city, st = self.city, self.st
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 190))
        surf.blit(dim, (0, 0))
        box = pygame.Rect(0, 0, s(720), s(340))
        box.center = (gfx.W / 2, gfx.H * 0.48)
        card(surf, box, YELLOW, (24, 24, 30), 3)
        gfx.blit_text(surf, "black_i", 40, f"#{city['rank']} {city['nick'].upper()}", YELLOW,
                      (box.centerx, box.y + s(40)), "center", outline=INK, width=3)
        for j, line in enumerate(wrap(f"\"{city['intro']}\"", 21, box.w - s(70), "cond_i")):
            gfx.blit_text(surf, "cond_i", 21, line, WHITE, (box.centerx, box.y + s(92) + j * s(30)), "center")
        r_me = story.rating(story.CAR_BY_KEY[st["car"]], st["cars"][st["car"]])
        r_riv = story.rating(story.CAR_BY_KEY[city["car"]], story.rival_levels())
        if r_me < r_riv * 0.97:
            gfx.blit_text(surf, "heavy", 17, "Your car looks slower than theirs. Upgrades might help...", (240, 160, 40),
                          (box.centerx, box.y + s(196)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.race_btn.draw(surf, mouse, pressed)
        self.notyet_btn.draw(surf, mouse, pressed)


# ------------------------------------------------------------------ garage
class StoryGarage(Garage):
    """The upgrade shop, paid in story cash, for the car you picked from the ones you've won."""

    def __init__(self, app):
        super().__init__(app)
        self.money_prefix = "$ "
        self.hint = "Click an upgrade (or 1-5) to buy  ·  every car keeps its own upgrades  ·  Enter: to the city"
        self.start_btn = Button("TO THE CITY", (gfx.W - s(176), gfx.H - s(56)), (250, 64), "yellow")
        self.back_btn = Button("BLACKLIST", (s(170), gfx.H - s(56)), (230, 64), "gray")
        self.prev_btn = Button("<", (gfx.W / 2 - s(250), gfx.H - s(56)), (70, 64), "dark")
        self.next_btn = Button(">", (gfx.W / 2 + s(250), gfx.H - s(56)), (70, 64), "dark")

    @property
    def st(self):
        return story.state(self.app.data)

    def scene_stage(self):
        return story.current_city(self.st)["stage"]

    def _spec(self):
        return story.CAR_BY_KEY[self.st["car"]]

    def _levels(self):
        return self.st["cars"][self.st["car"]]

    def _cost(self, u, lv):
        return story.price(self._spec(), u, lv)

    def _cash(self):
        return self.st["cash"]

    def _spend(self, amount):
        self.st["cash"] -= amount

    def _title(self):
        spec = self._spec()
        return f"{spec['name'].upper()}  ·  CLASS {spec['cls']}"

    def _top_bar(self, surf, title):
        top_bar(surf, self.app, title, cash=self.st["cash"])

    def _cycle(self, step):
        owned = [c["key"] for c in story.STORY_CARS if c["key"] in self.st["cars"]]
        if len(owned) < 2:
            self.app.audio.play("deny")
            return
        i = owned.index(self.st["car"])
        self.st["car"] = owned[(i + step) % len(owned)]
        self.app.persist()
        self.app.audio.play("click")

    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                app.goto("story")
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                app.open_city(story.current_city(self.st))
            elif ev.key in (pygame.K_LEFT, pygame.K_a):
                self._cycle(-1)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self._cycle(1)
            elif pygame.K_1 <= ev.key < pygame.K_1 + len(UPGRADES):
                self.buy(UPGRADES[ev.key - pygame.K_1])
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.start_btn.hit(ev.pos):
                app.open_city(story.current_city(self.st))
            elif self.back_btn.hit(ev.pos):
                app.audio.play("click")
                app.goto("story")
            elif self.prev_btn.hit(ev.pos):
                self._cycle(-1)
            elif self.next_btn.hit(ev.pos):
                self._cycle(1)
            for u, r in self.tiles:
                if r.collidepoint(ev.pos):
                    self.buy(u)

    def draw(self, surf, mouse, now):
        super().draw(surf, mouse, now)
        # the horn button of the normal garage sits where the car switcher goes: cover it
        cover = pygame.Rect(0, gfx.H - s(100), gfx.W, s(100))
        cover.x, cover.w = gfx.W / 2 - s(300), s(600)
        surf.fill((14, 40, 96), cover)
        spec = self._spec()
        owned = sum(1 for c in story.STORY_CARS if c["key"] in self.st["cars"])
        gfx.blit_text(surf, "black_i", 22, spec["name"].upper(), WHITE, (gfx.W / 2, gfx.H - s(66)), "center",
                      outline=INK, width=2)
        gfx.blit_text(surf, "heavy", 15, f"{owned} car{'s' if owned != 1 else ''} in your garage  ·  < > to switch",
                      (200, 220, 252), (gfx.W / 2, gfx.H - s(38)), "center")
        pressed = pygame.mouse.get_pressed()[0]
        self.prev_btn.draw(surf, mouse, pressed)
        self.next_btn.draw(surf, mouse, pressed)
        # how you stack up against the next rival
        city = story.current_city(self.st)
        r_me = story.rating(spec, self._levels())
        r_riv = story.rating(story.CAR_BY_KEY[city["car"]], story.rival_levels())
        top_r = max(r_me, r_riv) * 1.1
        x, w = s(40), s(300)
        rating_bar(surf, x, s(78), w, "YOUR CAR", r_me, top_r, GREEN if r_me >= r_riv else (240, 160, 40))
        rating_bar(surf, x, s(116), w, f"NEXT RIVAL: {city['nick'].upper()}", r_riv, top_r, RED)


# ------------------------------------------------------------------ results
class StoryResults:
    def __init__(self, app, run, outcome):
        """outcome: dict(win, reason, kind, city, cash, coins, car=None, finished_story=False)."""
        self.app, self.run, self.o = app, run, outcome
        self.t = 0.0
        self.frozen = app.screen.copy()
        dim = pygame.Surface((gfx.W, gfx.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 175))
        self.frozen.blit(dim, (0, 0))
        cy = gfx.H - s(70)
        self.cont = Button("CONTINUE", (gfx.W / 2 + s(150), cy), (260, 66), "yellow")
        self.retry = Button("RETRY", (gfx.W / 2 - s(150), cy), (260, 66), "gray")
        self.car_img = None
        if outcome.get("car"):
            spec = story.CAR_BY_KEY[outcome["car"]]
            self.car_img, _ = compose_vehicle(app.art, spec, 0.9, {})

    def handle(self, ev):
        app = self.app
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._continue()
            elif ev.key == pygame.K_r:
                app.start_story(self.o["city"], self.o["kind"])
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.cont.hit(ev.pos):
                self._continue()
            elif self.retry.hit(ev.pos):
                app.start_story(self.o["city"], self.o["kind"])

    def _continue(self):
        app = self.app
        app.audio.play("click")
        if self.o.get("car"):
            app.goto("story")
        else:
            app.open_city(self.o["city"])

    def draw(self, surf, mouse, now, dt):
        self.t += dt
        o = self.o
        surf.blit(self.frozen, (0, 0))
        k = min(1.0, self.t / 0.35)
        title = ("YOU WIN!" if o["kind"] != "pursuit" else "ESCAPED!") if o["win"] else o["reason"]
        img = gfx.text("black_i", 76, title, YELLOW if o["win"] else RED, outline=INK, width=4, shadow=4)
        img = pygame.transform.smoothscale_by(img, 0.6 + 0.4 * k)
        surf.blit(img, img.get_rect(center=(gfx.W / 2, s(110))))
        y = s(190)
        lines = []
        if o["cash"]:
            lines.append((f"{story.EVENT_TITLES[o['kind']]}  +{money(o['cash'])}", GREEN))
        if o["coins"]:
            lines.append((f"Coins picked up  +{money(o['coins'])}", GREEN))
        if not o["win"]:
            hint = {"rival": "Earn more cash in the city's events and upgrade your car.",
                    "pursuit": "Keep your speed up: the cops can only box you in when you're slow.",
                    "trial": "Use your boost on the climbs, and upgrade the engine.",
                    "sprint": "Boost early, and keep your wheels on the road."}[o["kind"]]
            lines.append((hint, (230, 200, 160)))
        for text, col in lines:
            gfx.blit_text(surf, "black_i", 26, text, col, (gfx.W / 2, y), "center", outline=INK, width=2)
            y += s(40)
        if self.car_img is not None:
            spec = story.CAR_BY_KEY[o["car"]]
            glow = pygame.Surface((s(620), s(230)), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 200, 30, 40 + int(25 * math.sin(self.t * 4))), glow.get_rect())
            surf.blit(glow, glow.get_rect(center=(gfx.W / 2, y + s(110))))
            surf.blit(self.car_img, self.car_img.get_rect(center=(gfx.W / 2, y + s(100))))
            gfx.blit_text(surf, "black_i", 30, f"NEW CAR: {spec['name'].upper()}", YELLOW, (gfx.W / 2, y + s(220)),
                          "center", outline=INK, width=3)
            gfx.blit_text(surf, "cond_i", 19, f"\"{o['city']['lose']}\"", WHITE, (gfx.W / 2, y + s(256)), "center")
            if o.get("finished_story"):
                gfx.blit_text(surf, "black_i", 34, "YOU ARE #1 ON THE BLACKLIST!", GREEN, (gfx.W / 2, y + s(296)),
                              "center", outline=INK, width=3)
        pressed = pygame.mouse.get_pressed()[0]
        self.cont.draw(surf, mouse, pressed)
        if not o["win"] or o["kind"] != "rival":
            self.retry.draw(surf, mouse, pressed)


# ------------------------------------------------------------------ HUD
def race_info(run):
    """Race bar data for the HUD: you and the AI cars (cops have no finishing position)."""
    players = [dict(color=(255, 255, 255), dist=run.distance, done=run.finished_at, me=True)]
    for ai in run.opponents:
        players.append(dict(color=ai.color, dist=max(0, int(ai.x - 2.0)), done=ai.finished_at, me=False))
    order = sorted(players, key=lambda q: (q["done"] is None, q["done"] or 0, -q["dist"]))
    pos = next(i + 1 for i, q in enumerate(order) if q["me"])
    return dict(players=players, distance=run.race_m, pos=pos, no_pos=run.story[1]["kind"] in ("pursuit", "trial"))


def draw_hud(surf, run):
    """Extra story HUD: the clock in a time trial, the busted meter in a chase."""
    kind = run.story[1]["kind"]
    if kind == "trial":
        left = max(0.0, run.story[1]["limit"] - run.race_time)
        col = RED if left < 8 else WHITE
        gfx.blit_text(surf, "black_i", 34, f"TIME LEFT  {left:4.1f}", col, (gfx.W / 2, s(64)), "center",
                      outline=INK, width=3)
    elif kind == "pursuit":
        behind = min((run.car.x - ai.x for ai in run.opponents), default=99)
        gfx.blit_text(surf, "black_i", 24, f"COPS {max(0, int(behind))} m BEHIND" if behind > 0 else "COPS ON YOU!",
                      (130, 180, 255) if behind > 8 else RED, (gfx.W / 2, s(56)), "center", outline=INK, width=2)
        if run.busted > 0.05:
            bar = pygame.Rect(0, 0, s(300), s(18))
            bar.midtop = (gfx.W / 2, s(76))
            pygame.draw.rect(surf, INK, bar.inflate(s(6), s(6)), border_radius=si(8))
            fill = bar.copy()
            fill.w = int(bar.w * run.busted / 2.0)
            pygame.draw.rect(surf, RED, fill, border_radius=si(6))
            gfx.blit_text(surf, "black_i", 16, "BUSTED", WHITE, bar.center, "center", outline=INK, width=2)
    elif kind == "rival":
        gfx.blit_text(surf, "black_i", 20, run.opponents[0].name, YELLOW, (gfx.W / 2, s(56)), "center",
                      outline=INK, width=2)
