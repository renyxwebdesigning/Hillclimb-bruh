#!/usr/bin/env python3
# /// script
# dependencies = [
#  "pygame-ce",
#  "numpy",
# ]
# ///
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

import asyncio  # noqa: E402
import threading  # noqa: E402

import pygame  # noqa: E402

import ghost  # noqa: E402
import gfx  # noqa: E402
import home  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402
import lighting  # noqa: E402
import save  # noqa: E402
import sprites  # noqa: E402
import ui  # noqa: E402
from audio import Audio  # noqa: E402
from config import FPS, STAGE_BY_KEY, TITLE, VEHICLE_BY_KEY, WEB  # noqa: E402
from drivers import DRIVER_BY_KEY  # noqa: E402
from game import Run, black_smoke  # noqa: E402
from hud import Hud  # noqa: E402
from online import Session  # noqa: E402
from progress import Progress  # noqa: E402
from relay import OfflineRelay, Relay  # noqa: E402
from render import Art, CarView, WorldRenderer  # noqa: E402
from terrain import Terrain  # noqa: E402

GAS_KEYS = (pygame.K_RIGHT, pygame.K_d, pygame.K_UP, pygame.K_w)
BRAKE_KEYS = (pygame.K_LEFT, pygame.K_a, pygame.K_DOWN, pygame.K_s)
BOOST_KEYS = (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT)


def window_size():
    if WEB:
        # 576 px tall keeps phones smooth (the page scales it up); the width follows the
        # browser's shape so the game fills the whole screen. Narrower than 16:9 gets bars.
        try:
            import platform as browser
            ratio = browser.window.innerWidth / browser.window.innerHeight
        except Exception:
            ratio = 16 / 9
        ratio = min(max(ratio, 16 / 9), 2.4)
        return int(576 * ratio) // 2 * 2, 576
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
        if WEB:
            # pygbag shows the canvas at half the page width until main.py returns, which a
            # game never does: switch to full size now, on a black page.
            try:
                import platform as browser
                browser.window.config.gui_divider = 1
                browser.document.body.style.background = "#000"
                browser.window.window_resize()
            except Exception:
                pass
        self.screen = gfx.init(w, h)            # opaque canvas; copied to the window each frame
        try:
            if not WEB and not hasattr(pygame.scrap, "get_text"):      # old pygame needs scrap.init()
                pygame.scrap.init()
        except Exception:     # no clipboard support (browser)
            pass
        pygame.key.stop_text_input()
        self.clock = pygame.time.Clock()
        self.data = save.load()
        self.audio = Audio()
        self.audio.enabled = self.data["sound"]
        self.audio.music_on = self.data["music"]
        self.audio.set_volumes(self.data["volume"])
        render.QUALITY = self.data["graphics"]
        if self.data["fullscreen"]:
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error:
                self.data["fullscreen"] = False
        self.progress = Progress(self)
        self.data.setdefault("best_vehicle", {})
        self.relay = (OfflineRelay if WEB else Relay)(self.data["player_id"], self.data.get("name") or "Player")
        self.fingers = {}
        for st_key, best in self.data["best"].items():
            if best > 0:
                self.relay.post_best(st_key, best, self.data["best_vehicle"].get(st_key, "jeep"))
        for num in self.data["friends"]:
            self.relay.watch(num)
        self.invite = None
        self.art = Art()
        self.hud = Hud()
        self.coin_icon = sprites.coin(5, gfx.si(15))
        self.coin_icon_small = sprites.coin(5, gfx.si(11))
        self.speaker = ui.speaker_icons(gfx.s(28))
        self.note = ui.note_icons(gfx.s(28))
        self.sound_rect = self.music_rect = self.fs_rect = self.fs_extra = None
        self.fs_icon = ui.fullscreen_icons(gfx.s(26))
        self._fs_ok = None
        self._fs_web = False
        self._fs_sent = None
        self._web_check = 0.0
        self.now = 0.0
        self._terrains = {}
        self._worlds = {}
        self.screens = {"home": None, "stages": ui.StageSelect(self), "vehicles": ui.VehicleSelect(self),
                        "drivers": ui.DriverSelect(self), "garage": ui.Garage(self),
                        "online": ui.OnlineMenu(self), "lobby": ui.Lobby(self)}
        self.screens["home"] = home.HomeMenu(self)
        self.screens["setup"] = ui.Setup(self)
        self.screens["settings"] = ui.Settings(self)
        self.screens["trophies"] = ui.TrophyRoom(self)
        self.screens["leaderboard"] = ui.Leaderboard(self)
        self.recorder = None
        self.ghost = None
        self.state = "home"
        self.run = None
        self.results = None
        self.pause = None
        self.mouse_pedal = None
        self.session = None
        self._connecting = None
        self._waiting_connect = False
        self.race_board = ui.RaceResults(self)
        self.invite_popup = ui.InvitePopup(self)
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

    def apply_graphics(self):
        render.QUALITY = self.data["graphics"]

    def fs_available(self):
        if not WEB:
            return True
        if self._fs_ok is None:
            try:
                import platform as browser
                self._fs_ok = bool(browser.window.hr_fs_ok())
            except Exception:
                self._fs_ok = False          # e.g. iPhone Safari has no fullscreen for pages
        return self._fs_ok

    def is_fullscreen(self):
        return self._fs_web if WEB else self.data["fullscreen"]

    def toggle_fullscreen(self):
        if WEB:
            return                  # the page script does it: browsers only allow it inside the tap itself
        try:
            pygame.display.toggle_fullscreen()
            self.data["fullscreen"] = not self.data["fullscreen"]
            self.persist()
        except pygame.error:
            pass

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
        if state == "settings":
            self.screens["settings"].enter()
        if state == "leaderboard":
            self.screens["leaderboard"].enter()

    def world_for(self, stage):
        key = stage["key"]
        if key not in self._terrains:
            self._terrains[key] = Terrain(stage)
        if key not in self._worlds:
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
                       horn=self.data["horn"], online=self.session, mode=mode, race_m=race_m, progress=self.progress)
        self.run.counted = False
        self.recorder = ghost.Recorder(self.run) if mode == "solo" else None
        self.ghost = ghost.load(stage["key"]) if mode == "solo" and self.data.get("ghosts", True) else None
        self.run_stage = stage
        self.pause = None
        self.mouse_pedal = None
        self.fingers.clear()
        self.state = "play"
        pygame.key.stop_text_input()
        self.audio.engine_stop()
        self.audio.engine_start(spec["sound"])
        track = self.data["music_track"]
        self.audio.music(music.STAGE_MUSIC.get(stage["key"], "drive") if track == "auto" else track)

    def start_run(self):
        self._begin_run(self.stage)

    def start_daily(self):
        d = self.progress.daily()
        self.data["stage"], self.data["vehicle"] = d["stage"]["key"], d["vehicle"]["key"]
        self.persist()
        self.start_run()

    def _count_run(self):
        run = self.run
        if run is not None and not getattr(run, "counted", True):
            run.counted = True
            self.progress.run_over(run)

    def _bank_run_coins(self):
        self._count_run()
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
            self.data["best_vehicle"][key] = run.spec["key"]
            self.relay.post_best(key, run.distance, run.spec["key"])
            if self.recorder:
                self.recorder.save(key, run.distance)
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

    # ------------------------------------------------- player numbers / friends
    def add_friend(self, num, name):
        num = str(num)
        if num == self.data["player_id"]:
            return
        if num not in self.data["friends"]:
            self.relay.watch(num)
        self.data["friends"][num] = name if name and name != "Player" else self.data["friends"].get(num, name)
        self.persist()

    def remove_friend(self, num):
        if self.data["friends"].pop(str(num), None) is not None:
            self.relay.unwatch(str(num))
            self.persist()

    def host_game(self):
        if self.session:
            self.session.leave()
        self.session = Session(True, self.data.get("name") or "Player", self.data["vehicle"], self.data["driver"],
                               relay=self.relay)
        self.relay.set_hosting(True)
        self.goto("lobby")

    def join_game(self, number):
        if self.session:
            self.session.leave()
        self.relay.set_hosting(False)
        self.session = Session(False, self.data.get("name") or "Player", self.data["vehicle"], self.data["driver"],
                               relay=self.relay, room=str(number))
        self.goto("lobby")

    def leave_session(self, message=""):
        if self.run is not None and self.run.online:
            self._bank_run_coins()
        if self.session:
            self.session.leave()
        self.session = None
        self.relay.set_hosting(False)
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
        self.relay.update()
        if self.relay.invites and self.invite is None:
            self.invite = self.relay.invites.pop(0)
        ses = self.session
        if ses is None:
            return
        ses.update(dt)
        for pid, p in ses.players.items():
            if pid != ses.my_id and len(str(pid)) == 6 and self.data["friends"].get(str(pid)) != p["name"]:
                self.add_friend(str(pid), p["name"])
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
    def frame(self):
        dt = min(0.05, self.clock.tick(FPS) / 1000)
        self.now += dt
        mouse = pygame.mouse.get_pos()
        self.fs_rect = self.fs_extra = None
        if WEB:
            self._web_tick(dt)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_m and self.state != "online":
                self.toggle_music()
            elif ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                self.touch(ev)
            else:
                self.handle(ev)
        if not self.running:
            return
        self._poll_session(dt)
        self.audio.tick()
        if self.state in self.screens:
            if self.state == "lobby" and self.session is None:
                self.goto("online")
            self.screens[self.state].draw(self.screen, mouse, self.now)
        elif self.state == "play":
            self.play_frame(dt, mouse)
        elif self.state == "results":
            self.results.draw(self.screen, mouse, self.now, dt)
        # on the results screen the top holds the big banner: show cards between score panel and buttons
        self.hud.draw_toasts(self.screen, dt, gfx.s(496) if self.state == "results" else None)
        if self.invite is not None:
            self.invite_popup.draw(self.screen, mouse, self.invite)
        if WEB:
            self._publish_fs_rect()
        self.window.blit(self.screen, (0, 0))
        pygame.display.flip()

    # ------------------------------------------------------------ browser
    SAFE_TO_RELAYOUT = ("home", "setup", "stages", "vehicles", "drivers", "garage", "settings", "trophies",
                        "leaderboard")

    def _web_tick(self, dt):
        """Twice a second: follow fullscreen changes and re-fit the layout to the browser's shape."""
        self._web_check -= dt
        if self._web_check > 0:
            return
        self._web_check = 0.5
        try:
            import platform as browser
            self._fs_web = bool(browser.window.hr_fs_on())
        except Exception:
            pass
        w, h = window_size()
        if abs(w - gfx.W) >= 8 and self.state in self.SAFE_TO_RELAYOUT and self.invite is None:
            self.relayout(w, h)

    def _publish_fs_rect(self):
        """Tell the page where the fullscreen button is; the page itself reacts to the tap."""
        rects = [r for r in (self.fs_rect, self.fs_extra) if r is not None] if self.fs_available() else []
        if self.state == "play" and self.pause is not None or self.invite is not None:
            rects = []
        key = tuple((r.x, r.y, r.w, r.h) for r in rects)
        if key == self._fs_sent:
            return
        self._fs_sent = key
        try:
            import platform as browser
            browser.window.hr_fs_set(-1, -1, 0, 0)
            for r in rects:
                g = r.inflate(gfx.s(12), gfx.s(12))
                browser.window.hr_fs_add(g.x / gfx.W, g.y / gfx.H, g.w / gfx.W, g.h / gfx.H)
        except Exception:
            pass

    def relayout(self, w, h):
        """Rebuild everything that depends on the screen size (menus only, never mid-run)."""
        self.window = pygame.display.set_mode((w, h))
        self.screen = gfx.init(w, h)
        touch_mode = self.hud.touch_mode
        self.hud = Hud()
        self.hud.touch_mode = touch_mode
        self._worlds.clear()
        state = self.state
        self.screens = {"home": None, "stages": ui.StageSelect(self), "vehicles": ui.VehicleSelect(self),
                        "drivers": ui.DriverSelect(self), "garage": ui.Garage(self),
                        "online": ui.OnlineMenu(self), "lobby": ui.Lobby(self)}
        self.screens["home"] = home.HomeMenu(self)
        self.screens["setup"] = ui.Setup(self)
        self.screens["settings"] = ui.Settings(self)
        self.screens["trophies"] = ui.TrophyRoom(self)
        self.screens["leaderboard"] = ui.Leaderboard(self)
        self.race_board = ui.RaceResults(self)
        self.invite_popup = ui.InvitePopup(self)
        self._fs_sent = None
        if state == "settings":
            self.screens["settings"].enter()
        try:
            import platform as browser
            browser.window.window_resize()
        except Exception:
            pass

    def touch(self, ev):
        """Multi-touch for phones: every finger can hold its own pedal (gas + boost together)."""
        if ev.type == pygame.FINGERUP:
            self.fingers.pop(ev.finger_id, None)      # even after the run ended, or a pedal stays held
            return
        self.hud.touch_mode = True
        if self.state != "play" or self.run is None:
            return
        if self.pause is not None or (self.session and self.session.results is not None):
            return                                    # menus on top get the taps as mouse clicks
        pos = (ev.x * gfx.W, ev.y * gfx.H)
        hit = self.hud.hit(pos, self.run.seized, self.fs_available())
        if ev.type == pygame.FINGERDOWN:
            if hit == "fullscreen":
                self.toggle_fullscreen()
            elif hit == "repair":
                self.run.repair()
            elif hit == "horn":
                self.run.honk()
            elif hit == "pause":
                self.open_pause()
        self.fingers[ev.finger_id] = hit

    def loop(self):
        while self.running:
            self.frame()
        self.shutdown()

    async def loop_async(self):
        """The same loop for the browser, which needs to get control back every frame."""
        first = True
        while self.running:
            self.frame()
            await asyncio.sleep(0)
            if first:                   # the first frame is on screen: fade out the loading page
                first = False
                try:
                    import platform as browser
                    browser.window.hr_stage("done")
                except Exception:
                    pass
        self.shutdown()

    def shutdown(self):
        if self.session:
            self.session.leave()
        self.relay.close()
        self.persist()
        pygame.quit()

    def handle(self, ev):
        if self.invite is not None:
            act = None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.invite_popup.click(ev.pos)
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_j):
                act = "join"
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_n):
                act = "no"
            if act == "join":
                inv, self.invite = self.invite, None
                self.add_friend(str(inv["from"]), inv.get("name", "Player"))
                self._bank_run_coins()
                self.join_game(str(inv["from"]))
            elif act == "no":
                self.invite = None
            return
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
                elif act == "next":
                    self._bank_run_coins()
                    ses.next_round()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and ses.is_host:
                if ses.tour and ses.tour["round"] < ses.tour["rounds"]:
                    self._bank_run_coins()
                    ses.next_round()
                else:
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
            elif act == "setup":
                self.goto("setup")
            elif act == "lobby" and ses:
                ses.back_to_lobby()
            elif act == "leave":
                self.leave_session()
            return
        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and getattr(ev, "touch", False):
            return                  # a finger: already handled by touch(), don't count the tap twice
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
            hit = self.hud.hit(ev.pos, run.seized, self.fs_available())
            if hit == "fullscreen":
                self.toggle_fullscreen()
            elif hit == "pause":
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
        touch = set(self.fingers.values())
        gas = any(keys[k] for k in GAS_KEYS) or self.mouse_pedal == "gas" or "gas" in touch
        brake = any(keys[k] for k in BRAKE_KEYS) or self.mouse_pedal == "brake" or "brake" in touch
        boost = any(keys[k] for k in BOOST_KEYS) or self.mouse_pedal == "boost" or "boost" in touch
        frozen = self.pause is not None and not run.online
        racing_over = ses is not None and ses.results is not None
        if self.pause or racing_over:
            gas = brake = boost = False
        if not frozen:
            run.update(dt, gas, brake, boost)
            self.hud.update(dt)
        darkness, sunset = lighting.phase_info(run.stage, run.time)
        run.is_night = darkness > 0.5
        if self.recorder and not frozen:
            self.recorder.record(run, dt)
        daily = self.progress.daily_progress(run) if not self.progress.daily_done() else None
        if daily:
            d, value = daily
            unit = {"distance": " m", "flips": " flips", "coins": " coins", "air": " s air"}[d["kind"]]
            run.daily_text = f"DAILY: {min(value, d['target']):.0f} / {d['target']}{unit}"
        else:
            run.daily_text = None
        in_tunnel = run.terrain.feature_at(run.car.x) == "tunnel"
        run.lights_on = run.lights_forced if run.lights_forced is not None else (darkness > 0.22 or in_tunnel)

        views, race = [], None
        if ses:
            self._online_tick(dt, run, ses, views)
            if run.mode == "race":
                race = self._race_info(run, ses)
        if self.ghost and run.mode == "solo":
            self.ghost.update(run.time)
            views.insert(0, CarView(self.ghost.car, self.ghost.driver, label=f"BEST {self.ghost.distance} m",
                                    color=(200, 220, 255), ghost=True))
        views.append(CarView(run.car, run.driver, run.wobble, run.lights_on, bubble=run.bubble))
        self.world.draw(self.screen, run.cam, views, run.particles, self.now, 0 if frozen else dt, run.best,
                        darkness, sunset, run.race_m)
        fs_icon = self.fs_icon[self.is_fullscreen()] if self.fs_available() else None
        self.hud.draw(self.screen, run, gas and run.state == "drive", brake and run.state == "drive", self.now, race,
                      fs_icon)
        if fs_icon is not None:
            self.fs_rect = self.hud.fs_rect
        if run.state == "ending":
            color = (255, 76, 60) if run.reason.startswith("DRIVER") else (255, 176, 40)
            self.hud.draw_banner(self.screen, run.reason, color, run.end_t)
        if ses and run.mode == "race" and run.finished_at is not None and ses.results is None:
            gfx.blit_text(self.screen, "cond", 26, "Finished! Waiting for the others...", (255, 255, 255),
                          (gfx.W / 2, gfx.H * 0.55), "center", outline=(20, 20, 24), width=2)
        if racing_over:
            if not getattr(ses, "_counted_results", False):
                ses._counted_results = True
                self.progress.online_race(bool(ses.results) and ses.results[0][0] == ses.my_id)
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


async def main_async():
    await App().loop_async()


def main():
    if WEB:
        asyncio.run(main_async())
    else:
        App().loop()


if __name__ == "__main__":
    main()
