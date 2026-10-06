#!/usr/bin/env python3
"""Hill Rider: a 2D hill-climb driving game.

Right / D / Up = gas, Left / A / Down = brake (in the air they tilt the car).
Space = boost, H = horn, L = lights, Enter = whack a seized engine.
Esc or P pauses, M toggles music. Online play: "PLAY ONLINE" on the start screen.
"""
import math
import os
import sys
import warnings

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import threading  # noqa: E402

import pygame  # noqa: E402

import gfx  # noqa: E402
import lighting  # noqa: E402
import save  # noqa: E402
import sprites  # noqa: E402
import ui  # noqa: E402
from audio import Audio  # noqa: E402
from config import FPS, STAGE_BY_KEY, TITLE, VEHICLE_BY_KEY  # noqa: E402
from drivers import DRIVER_BY_KEY  # noqa: E402
from game import Run, black_smoke  # noqa: E402
from hud import Hud  # noqa: E402
from online import Session  # noqa: E402
from render import Art, CarView, WorldRenderer  # noqa: E402
from terrain import Terrain  # noqa: E402

GAS_KEYS = (pygame.K_RIGHT, pygame.K_d, pygame.K_UP, pygame.K_w)
BRAKE_KEYS = (pygame.K_LEFT, pygame.K_a, pygame.K_DOWN, pygame.K_s)
BOOST_KEYS = (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT)


def window_size():
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError):
        dw, dh = 1600, 900
    h = min(1080, int(dh * 0.86), int(dw * 0.86 * 9 / 16))
    h = max(540, h - h % 2)
    return int(round(h * 16 / 9)), h


class App:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        w, h = window_size()
        try:
            pygame.display.set_icon(sprites.wheel(30))
        except pygame.error:
            pass
        self.window = pygame.display.set_mode((w, h))
        pygame.display.set_caption(TITLE)
        self.screen = gfx.init(w, h)            # opaque canvas; copied to the window each frame
        try:
            pygame.scrap.init()
        except (pygame.error, AttributeError):
            pass
        pygame.key.stop_text_input()
        self.clock = pygame.time.Clock()
        self.data = save.load()
        self.audio = Audio()
        self.audio.enabled = self.data["sound"]
        self.audio.music_on = self.data["music"]
        self.art = Art()
        self.hud = Hud()
        self.coin_icon = sprites.coin(5, gfx.si(15))
        self.coin_icon_small = sprites.coin(5, gfx.si(11))
        self.speaker = ui.speaker_icons(gfx.s(28))
        self.note = ui.note_icons(gfx.s(28))
        self.sound_rect = self.music_rect = None
        self.now = 0.0
        self._terrains = {}
        self._worlds = {}
        self.screens = {"stages": ui.StageSelect(self), "vehicles": ui.VehicleSelect(self),
                        "drivers": ui.DriverSelect(self), "garage": ui.Garage(self),
                        "online": ui.OnlineMenu(self), "lobby": ui.Lobby(self)}
        self.state = "stages"
        self.run = None
        self.results = None
        self.pause = None
        self.mouse_pedal = None
        self.session = None
        self._connecting = None
        self._waiting_connect = False
        self.race_board = ui.RaceResults(self)
        self.remote_bubbles = {}
        self._remote_smoke = 0.0
        self.running = True
        self.audio.music("menu")

    # ------------------------------------------------------------- helpers
    @property
    def stage(self):
        return STAGE_BY_KEY[self.data["stage"]]

    @property
    def vehicle(self):
        return VEHICLE_BY_KEY[self.data["vehicle"]]

    def persist(self):
        save.save(self.data)

    def toggle_sound(self):
        self.data["sound"] = not self.data["sound"]
        self.audio.enabled = self.data["sound"]
        self.persist()
        self.audio.play("click")

    def toggle_music(self):
        self.data["music"] = not self.data["music"]
        self.audio.set_music(self.data["music"])
        self.persist()
        self.audio.play("click")

    def quit(self):
        self.running = False

    def goto(self, state, message=""):
        self.audio.engine_stop()
        self.audio.music("menu")
        self.pause = None
        self.state = state
        if state == "online":
            self.screens["online"].enter(message)
        else:
            pygame.key.stop_text_input()
        if state == "lobby":
            self.screens["lobby"].enter()

    def world_for(self, stage):
        key = stage["key"]
        if key not in self._terrains:
            self._terrains[key] = Terrain(stage)
            self._worlds[key] = WorldRenderer(stage, self._terrains[key], self.art)
        t = self._terrains[key]
        for c in t.coins:
            c[3] = False
        return t, self._worlds[key]

    # ---------------------------------------------------------------- runs
    def _begin_run(self, stage, mode="solo", race_m=0):
        self.audio.play("click")
        spec = self.vehicle
        terrain, self.world = self.world_for(stage)
        self.hud.clear()
        self.remote_bubbles.clear()
        self.run = Run(stage, terrain, spec, self.data["levels"][spec["key"]], self.data["coins"],
                       self.data["best"].get(stage["key"], 0), self.audio, self.hud, driver=self.data["driver"],
                       horn=self.data["horn"], online=self.session, mode=mode, race_m=race_m)
        self.run_stage = stage
        self.pause = None
        self.mouse_pedal = None
        self.state = "play"
        pygame.key.stop_text_input()
        self.audio.engine_stop()
        self.audio.engine_start(spec["sound"])
        self.audio.music("drive")

    def start_run(self):
        self._begin_run(self.stage)

    def _bank_run_coins(self):
        if self.run is not None and self.run.coins:
            self.data["coins"] += self.run.coins
            self.run.coins = 0
            self.persist()

    def end_run(self):
        run = self.run
        key = self.run_stage["key"]
        best = self.data["best"].get(key, 0)
        record = run.distance > best
        if record:
            self.data["best"][key] = run.distance
        coins = run.coins
        self._bank_run_coins()
        run.coins = coins            # keep the total for the results screen
        self.audio.engine_stop()
        self.results = ui.Results(self, run, record)
        self.state = "results"

    # -------------------------------------------------------------- online
    def open_session(self, hosting, address=None):
        name = self.data.get("name") or "Player"
        if hosting:
            try:
                self.session = Session(True, name, self.data["vehicle"], self.data["driver"])
            except OSError as e:
                self.goto("online", f"Could not host: {e.strerror or e}")
                return
            self.goto("lobby")
            return

        def connect():
            try:
                self._connecting = Session(False, name, self.data["vehicle"], self.data["driver"], address)
            except OSError as e:
                self._connecting = f"Could not connect: {e.strerror or e}"
        self._connecting = None
        threading.Thread(target=connect, daemon=True).start()
        self._waiting_connect = True

    def leave_session(self, message=""):
        if self.run is not None and self.run.online:
            self._bank_run_coins()
        if self.session:
            self.session.leave()
        self.session = None
        self.goto("online", message)

    def _poll_session(self, dt):
        if getattr(self, "_waiting_connect", False) and self._connecting is not None:
            self._waiting_connect = False
            if isinstance(self._connecting, str):
                self.goto("online", self._connecting)
            else:
                self.session = self._connecting
                self.goto("lobby")
            self._connecting = None
        ses = self.session
        if ses is None:
            return
        ses.update(dt)
        if ses.error:
            self.leave_session(ses.error)
            return
        if ses.started is not None:
            settings, ses.started = ses.started, None
            self._begin_run(STAGE_BY_KEY[settings["stage"]], "race" if settings["mode"] == "race" else "free",
                            settings["distance"] if settings["mode"] == "race" else 0)
        if ses.to_lobby:
            ses.to_lobby = False
            self._bank_run_coins()
            self.goto("lobby")

    # ---------------------------------------------------------------- loop
    def loop(self):
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000)
            self.now += dt
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                    try:
                        pygame.display.toggle_fullscreen()
                    except pygame.error:
                        pass
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_m and self.state != "online":
                    self.toggle_music()
                else:
                    self.handle(ev)
            if not self.running:
                break
            self._poll_session(dt)
            if self.state in self.screens:
                if self.state == "lobby" and self.session is None:
                    self.goto("online")
                self.screens[self.state].draw(self.screen, mouse, self.now)
            elif self.state == "play":
                self.play_frame(dt, mouse)
            elif self.state == "results":
                self.results.draw(self.screen, mouse, self.now, dt)
            self.window.blit(self.screen, (0, 0))
            pygame.display.flip()
        if self.session:
            self.session.leave()
        self.persist()
        pygame.quit()

    def handle(self, ev):
        if self.state in self.screens:
            self.screens[self.state].handle(ev)
        elif self.state == "results":
            self.results.handle(ev)
        elif self.state == "play":
            self.handle_play(ev)

    def handle_play(self, ev):
        run, ses = self.run, self.session
        if ses and ses.results is not None:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.race_board.click(ev.pos)
                if act == "leave":
                    self.leave_session()
                elif act == "lobby":
                    ses.back_to_lobby()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and ses.is_host:
                ses.back_to_lobby()
            return
        if self.pause:
            act = None
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_p):
                act = "resume"
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.pause.click(ev.pos)
            if act == "resume":
                self.pause = None
                if not run.online:
                    self.audio.engine_start(run.spec["sound"])
            elif act == "restart":
                self.start_run()
            elif act == "garage":
                self.goto("garage")
            elif act == "lobby" and ses:
                ses.back_to_lobby()
            elif act == "leave":
                self.leave_session()
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self.open_pause()
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                run.repair()
            elif ev.key == pygame.K_h:
                run.honk()
            elif ev.key == pygame.K_l:
                run.toggle_lights()
            elif ev.key == pygame.K_r and not run.online:
                self.start_run()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.hud.hit(ev.pos, run.seized)
            if hit == "pause":
                self.open_pause()
            elif hit == "repair":
                run.repair()
            elif hit == "horn":
                run.honk()
            else:
                self.mouse_pedal = hit
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.mouse_pedal = None

    def open_pause(self):
        if self.run.state == "drive":
            self.pause = ui.PauseMenu(self, self.session)
            if not self.run.online:
                self.audio.engine_stop()

    # ----------------------------------------------------------- gameplay
    def play_frame(self, dt, mouse):
        run, ses = self.run, self.session
        keys = pygame.key.get_pressed()
        gas = any(keys[k] for k in GAS_KEYS) or self.mouse_pedal == "gas"
        brake = any(keys[k] for k in BRAKE_KEYS) or self.mouse_pedal == "brake"
        boost = any(keys[k] for k in BOOST_KEYS) or self.mouse_pedal == "boost"
        frozen = self.pause is not None and not run.online
        racing_over = ses is not None and ses.results is not None
        if self.pause or racing_over:
            gas = brake = boost = False
        if not frozen:
            run.update(dt, gas, brake, boost)
            self.hud.update(dt)
        darkness, sunset = lighting.phase_info(run.stage, run.time)
        in_tunnel = run.terrain.feature_at(run.car.x) == "tunnel"
        run.lights_on = run.lights_forced if run.lights_forced is not None else (darkness > 0.22 or in_tunnel)

        views, race = [], None
        if ses:
            self._online_tick(dt, run, ses, views)
            if run.mode == "race":
                race = self._race_info(run, ses)
        views.append(CarView(run.car, run.driver, run.wobble, run.lights_on, bubble=run.bubble))
        self.world.draw(self.screen, run.cam, views, run.particles, self.now, 0 if frozen else dt, run.best,
                        darkness, sunset, run.race_m)
        self.hud.draw(self.screen, run, gas and run.state == "drive", brake and run.state == "drive", self.now, race)
        if run.state == "ending":
            color = (255, 76, 60) if run.reason.startswith("DRIVER") else (255, 176, 40)
            self.hud.draw_banner(self.screen, run.reason, color, run.end_t)
        if ses and run.mode == "race" and run.finished_at is not None and ses.results is None:
            gfx.blit_text(self.screen, "cond", 26, "Finished! Waiting for the others...", (255, 255, 255),
                          (gfx.W / 2, gfx.H * 0.55), "center", outline=(20, 20, 24), width=2)
        if racing_over:
            self.race_board.draw(self.screen, mouse, ses.results)
        if self.pause:
            self.pause.draw(self.screen, mouse)
        if run.state == "done":
            self.end_run()

    def _online_tick(self, dt, run, ses, views):
        ses.send_state(run, dt)
        for ev in run.outbox:
            ses.send_event(ev)
        run.outbox.clear()
        for pid, ev in ses.events:
            if pid == ses.my_id:
                continue
            p = ses.players.get(pid)
            car = ses.remote.get(pid)
            if p is None:
                continue
            vol = 1.0
            if car is not None:
                vol = max(0.0, 1.0 - abs(car.x - run.car.x) / 60.0)
            kind = ev.get("kind")
            if kind == "horn":
                self.audio.play("horn_" + ev.get("horn", "puppy"), vol)
            elif kind == "seize":
                text, _ = self.audio.say(p["driver"], vol, ev.get("line"))
                self.remote_bubbles[pid] = [text, 3.0]
                self.audio.play("seize", vol * 0.7)
            elif kind == "crash":
                self.audio.play("crash", vol * 0.6)
            elif kind == "finish":
                self.hud.notice(f"{p['name']} FINISHED!", p["color"])
        ses.events.clear()
        self._remote_smoke -= dt
        smoke_now = self._remote_smoke <= 0
        if smoke_now:
            self._remote_smoke = 0.08
        for pid, car in ses.remote.items():
            p = ses.players.get(pid)
            if p is None or not car.ready:
                continue
            if car.seized and smoke_now:
                black_smoke(run.particles, car, car.spec)
            bubble = self.remote_bubbles.get(pid)
            if bubble:
                bubble[1] -= dt
                if bubble[1] <= 0:
                    del self.remote_bubbles[pid]
                    bubble = None
            views.append(CarView(car, p["driver"], lights=car.lights, label=p["name"], color=p["color"],
                                 bubble=tuple(bubble) if bubble else None))

    def _race_info(self, run, ses):
        players = []
        for pid, p in ses.players.items():
            if pid == ses.my_id:
                dist, done = run.distance, run.finished_at
            else:
                car = ses.remote.get(pid)
                dist, done = (car.dist if car else 0), ses.finish.get(pid)
            if done is not None:
                dist = run.race_m
            players.append(dict(pid=pid, color=p["color"], dist=dist, done=done, me=pid == ses.my_id))
        order = sorted(players, key=lambda q: (q["done"] is None, q["done"] or 0, -q["dist"]))
        pos = next((i + 1 for i, q in enumerate(order) if q["me"]), 1)
        return dict(players=players, distance=run.race_m, pos=pos)


def main():
    App().loop()


if __name__ == "__main__":
    main()
