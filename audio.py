"""Sound: a real-time synthesised engine per vehicle, effects and music.

The engine is generated on the fly in short chunks and queued on its own
mixer channel, so pitch follows RPM smoothly instead of crossfading loops.
If there is no sound device the game runs silently.
"""
import random
from pathlib import Path
import threading
from collections import deque

import numpy as np
import pygame

import music
from config import WEB
from drivers import DRIVERS

SR = 44100
# Engine audio is streamed one chunk ahead; a chunk must outlast the slowest frame or the sound
# runs dry and crackles (the browser often runs at 20-30 frames per second).
CHUNK = 4410 if WEB else 2205          # 100 ms / 50 ms

# Firing-frequency range (Hz), spectral tilt, sub-harmonic (uneven firing)
# amount, two exhaust resonances (centre Hz, width Hz, gain), combustion noise.
PROFILES = {
    "jeep": dict(idle=24, top=120, tilt=1.05, sub=0.55, f1=(190, 130, 2.0), f2=(620, 320, 0.9), noise=0.22, gain=0.55),
    "dirtbike": dict(idle=50, top=255, tilt=0.72, sub=0.12, f1=(900, 500, 1.6), f2=(2200, 800, 0.8), noise=0.35, gain=0.42),
    "chopper": dict(idle=13, top=64, tilt=1.15, sub=1.1, f1=(140, 90, 2.2), f2=(480, 240, 1.0), noise=0.32, gain=0.62),
    "monster": dict(idle=17, top=94, tilt=1.2, sub=0.8, f1=(120, 80, 2.4), f2=(380, 200, 1.1), noise=0.3, gain=0.62),
    "supercar": dict(idle=34, top=275, tilt=0.85, sub=0.2, f1=(420, 250, 1.6), f2=(1500, 600, 1.0), noise=0.18, gain=0.46),
    "jet": dict(jet=True, gain=0.36),
    "tesla": dict(electric=True, gain=0.3),
    "mini": dict(idle=38, top=190, tilt=0.9, sub=0.3, f1=(520, 300, 1.6), f2=(1500, 600, 0.8), noise=0.25, gain=0.46),
    "excavator": dict(idle=11, top=46, tilt=1.4, sub=0.8, f1=(80, 50, 2.6), f2=(260, 140, 1.3), noise=0.5, gain=0.66),
    "lkw": dict(idle=10, top=52, tilt=1.35, sub=0.9, f1=(70, 45, 2.8), f2=(240, 120, 1.2), noise=0.42, gain=0.68),
    "rusty": dict(idle=24, top=150, tilt=0.95, sub=0.7, f1=(380, 260, 1.6), f2=(1300, 700, 1.1), noise=0.5, gain=0.5),
    "golf": dict(idle=32, top=210, tilt=0.88, sub=0.25, f1=(470, 280, 1.7), f2=(1700, 650, 0.9), noise=0.24, gain=0.48),
    "shark": dict(electric=True, gain=0.22),
    "tank": dict(idle=12, top=58, tilt=1.35, sub=0.7, f1=(90, 60, 2.6), f2=(300, 160, 1.2), noise=0.45, gain=0.66),
    "police": dict(idle=20, top=118, tilt=1.1, sub=0.75, f1=(150, 90, 2.2), f2=(450, 220, 1.0), noise=0.26, gain=0.58),
    "hover": dict(electric=True, gain=0.4),
}


def _to_sound(mono, volume=1.0):
    mono = np.clip(mono * volume, -1.0, 1.0)
    data = (mono * 32000).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([data, data])))


def _env(n, attack=0.005, decay=8.0):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t * decay)


def _tone(freq, dur, decay=8.0, shape="sine"):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2 * np.pi * freq * t
    if shape == "square":
        w = np.sign(np.sin(ph)) * 0.5
    elif shape == "tri":
        w = 2 / np.pi * np.arcsin(np.sin(ph))
    else:
        w = np.sin(ph)
    return w * _env(n, decay=decay)


def _noise(dur, decay, smooth=8, seed=0):
    n = int(SR * dur)
    x = np.random.default_rng(seed).uniform(-1, 1, n)
    k = np.ones(smooth) / smooth
    x = np.convolve(np.convolve(x, k, mode="same"), k, mode="same")
    return x / (np.abs(x).max() + 1e-9) * _env(n, decay=decay)


def _mix(*parts):
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[:len(p)] += p
    return out


class EngineSynth:
    """Additive engine model with phase-continuous pitch glides."""

    K = 28

    def __init__(self, profile, turbo=0.0):
        self.p = PROFILES[profile]
        self.turbo = turbo              # 0..1: how loud the turbo whistles (the TURBO upgrade)
        self.spool = 0.0
        self.whistle_phase = 0.0
        self.rng = np.random.default_rng(3)
        self.phase = 0.0
        self.f = self.p.get("idle", 30)
        self.load = 0.0
        self.noise_tail = np.zeros(64)
        self.phi = self.rng.uniform(0, 2 * np.pi, self.K)[:, None]
        self.k = np.arange(1, self.K + 1)[:, None]
        self.am = 1.0
        self.amp = None

    def _causal(self, noise, k):
        """Moving-average low-pass that continues seamlessly from the last chunk."""
        both = np.concatenate([self.noise_tail, noise])
        out = np.convolve(both, np.ones(k) / k)[len(self.noise_tail):len(both)]
        return out

    def render(self, rpm, load):
        p = self.p
        n = CHUNK
        load0, self.load = self.load, self.load + (load - self.load) * 0.5
        if p.get("jet"):
            return self._jet(n, load0, self.load)
        if p.get("electric"):
            return self._electric(n, rpm, load0, self.load)
        f_target = p["idle"] + (p["top"] - p["idle"]) * max(0.0, min(1.0, rpm)) ** 1.1
        f = np.linspace(self.f, f_target, n, endpoint=False)
        self.f = f_target
        ph = self.phase + np.cumsum(2 * np.pi * f / SR)
        self.phase = float(ph[-1] % (4 * np.pi))
        base = ph / 2

        kk = self.k[:, 0]
        fk = kk * (f.mean() / 2)
        tilt = p["tilt"] - 0.3 * self.load
        c1, w1, g1 = p["f1"]
        c2, w2, g2 = p["f2"]
        amp = kk ** -tilt * (1 + g1 * np.exp(-((fk - c1) / w1) ** 2) + g2 * np.exp(-((fk - c2) / w2) ** 2))
        amp[0::2] *= p["sub"]
        amp[fk > 7000] = 0
        amp /= np.sqrt((amp ** 2).sum()) * 1.6 + 1e-9
        prev = amp if self.amp is None else self.amp
        self.amp = amp
        ramp = np.linspace(0.0, 1.0, n, endpoint=False)[None, :]
        weights = prev[:, None] + (amp - prev)[:, None] * ramp
        wave = (weights * np.sin(self.k * base[None, :] + self.phi)).sum(axis=0)

        noise = self.rng.uniform(-1, 1, n)
        filt = self._causal(noise, 5 if p["idle"] > 40 else 9)
        self.noise_tail = noise[-64:]
        pulse = (0.5 + 0.5 * np.cos(ph)) ** 3
        rough = p["noise"] * (0.4 + 0.6 * self.load) * filt * pulse * 2.2

        target_am = 1 + self.rng.uniform(-0.07, 0.07)
        am = np.linspace(self.am, target_am, n)
        self.am = target_am
        level = np.linspace(0.55 + 0.45 * load0, 0.55 + 0.45 * self.load, n)
        y = (wave + rough) * am * level * p["gain"]
        if self.turbo > 0:              # the turbo spools up with throttle and whistles
            spool0, self.spool = self.spool, self.spool + (rpm * self.load - self.spool) * 0.25
            sp = np.linspace(spool0, self.spool, n, endpoint=False)
            wph = self.whistle_phase + np.cumsum(2 * np.pi * (1600 + 4400 * sp) / SR)
            self.whistle_phase = float(wph[-1] % (2 * np.pi))
            y = y + np.sin(wph) * sp ** 1.5 * 0.09 * self.turbo
        return np.tanh(y * 1.6) / np.tanh(1.6)

    def _electric(self, n, rpm, l0, l1):
        """A rising electric whine with a soft hover hum."""
        f_target = 180 + 900 * max(0.0, min(1.0, rpm))
        f = np.linspace(self.f, f_target, n, endpoint=False)
        self.f = f_target
        ph = self.phase + np.cumsum(2 * np.pi * f / SR)
        self.phase = float(ph[-1] % (2 * np.pi * 64))
        hum_ph = ph * 0.11
        level = np.linspace(0.35 + 0.65 * l0, 0.35 + 0.65 * l1, n)
        y = (np.sin(ph) * 0.35 + np.sin(2 * ph) * 0.12 + np.sin(hum_ph) * 0.5) * level * self.p["gain"]
        return np.tanh(y * 1.5) / np.tanh(1.5)

    def _jet(self, n, l0, l1):
        noise = self.rng.uniform(-1, 1, n)
        hiss = self._causal(noise, 4)
        roar = self._causal(noise, 40) * 5
        self.noise_tail = noise[-64:]
        t = (np.arange(n) + self.phase) / SR
        self.phase += n
        rumble = np.sin(2 * np.pi * 36 * t) * 0.35 + np.sin(2 * np.pi * 53 * t) * 0.15
        level = np.linspace(l0, l1, n)
        y = (roar * (0.35 + 0.9 * level) + hiss * (0.05 + 0.3 * level) + rumble * (0.2 + 0.6 * level)) * self.p["gain"]
        return np.tanh(y * 1.3) / np.tanh(1.3)


def _puppy_horn():
    """Two squeaky little yips."""
    out = []
    for dur, f0, f1 in ((0.12, 820, 1650), (0.16, 720, 1500)):
        n = int(SR * dur)
        t = np.arange(n) / SR
        f = f0 + (f1 - f0) * np.sin(np.pi * t / dur) ** 0.8
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
        breath = np.random.default_rng(1).uniform(-1, 1, n) * np.exp(-t * 60) * 0.5
        out += [(tone + breath) * np.sin(np.pi * t / dur) ** 0.6, np.zeros(int(SR * 0.05))]
    y = np.concatenate(out)
    return y / np.abs(y).max() * 0.9


def _ship_horn():
    """A deep foghorn chord with a little echo."""
    dur = 1.9
    n = int(SR * dur)
    t = np.arange(n) / SR
    vib = 1 + 0.003 * np.sin(2 * np.pi * 4.5 * t)
    y = np.zeros(n)
    for f0, gain in ((62, 1.0), (93, 0.55)):
        ph = 2 * np.pi * f0 * np.cumsum(vib) / SR
        for k in range(1, 26):
            fk = f0 * k
            y += gain * (1 / k) * (1 + 1.8 * np.exp(-((fk - 320) / 160) ** 2)) * np.sin(k * ph)
    env = np.minimum(1, t / 0.14) * np.clip((dur - t) / 0.35, 0, 1)
    y *= env
    out = np.zeros(n + int(SR * 0.4))
    out[:n] += y
    for d, g in ((0.07, 0.35), (0.15, 0.25), (0.27, 0.15)):
        i = int(SR * d)
        out[i:i + n] += y * g
    return out / np.abs(out).max() * 0.95


def _crash():
    """Thump, metal crunch and a little glass."""
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    rng = np.random.default_rng(12)
    thump = np.sin(2 * np.pi * (55 + 40 * np.exp(-t * 20)) * t) * np.exp(-t * 7) * 1.0
    crunch = _noise(0.9, 5, 6, 13)[:n] * 0.8
    metal = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((420, 6), (911, 8), (1583, 10), (2390, 12))) * 0.22
    glass = np.zeros(n)
    for _ in range(14):
        i = int(rng.uniform(0.02, 0.5) * SR)
        f = rng.uniform(3000, 6500)
        m = min(n - i, int(SR * 0.08))
        tt = np.arange(m) / SR
        glass[i:i + m] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 60) * 0.25
    return thump + crunch + metal + glass


class Voices:
    """Driver swear lines: natural recordings made with Piper (tools/make_voices.py), bundled in assets/voice."""

    def __init__(self):
        self.sounds = {}

    def say(self, key, index=None):
        """Pick a line for the driver; returns (text, Sound or None, index)."""
        d = next((d for d in DRIVERS if d["key"] == key), DRIVERS[0])
        key = d["key"]
        i = random.randrange(len(d["lines"])) if index is None else index % len(d["lines"])
        snd = self.sounds.get((key, i))
        if snd is None:
            from gfx import resource
            path = Path(resource("assets", "voice", f"{key}_{i}.ogg"))
            if path.exists():
                try:
                    snd = self.sounds[(key, i)] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    snd = None
        return d["lines"][i], snd, i


class Audio:
    def __init__(self):
        self.ok = False
        self.enabled = True
        self.music_on = True
        self.track = None
        self.vol = {"master": 1.0, "music": 0.8, "sfx": 1.0, "voice": 1.0}
        self._duck_until = 0.0
        self.synth = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SR, -16, 2, 2048 if WEB else 1024)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(4)
        except pygame.error:
            return
        self.ok = True
        self.engine_ch = pygame.mixer.Channel(0)
        self.boost_ch = pygame.mixer.Channel(1)
        self.music_chs = [pygame.mixer.Channel(2), pygame.mixer.Channel(3)]   # two, to crossfade tracks
        self.music_ch = self.music_chs[0]
        self._recent = deque(maxlen=6)
        self.fx = {
            "coin": _to_sound(self._arpeggio([1568, 2093], 0.045), 0.3),
            "fuel": _to_sound(self._sweep(320, 900, 0.32), 0.5),
            "bonus": _to_sound(self._arpeggio([784, 988, 1175, 1568], 0.07), 0.4),
            "crash": _to_sound(_crash() / 1.6, 0.9),
            "land": _to_sound(_mix(_noise(0.18, 22, 30, 2) * 0.8, _tone(90, 0.15, 25)), 0.5),
            "click": _to_sound(_tone(1200, 0.035, 80, "tri"), 0.35),
            "buy": _to_sound(self._arpeggio([1046, 1568], 0.06), 0.45),
            "deny": _to_sound(_tone(150, 0.22, 10, "square"), 0.3),
            "beep": _to_sound(_tone(880, 0.12, 18, "square"), 0.18),
            "boost_on": _to_sound(_mix(_noise(0.35, 7, 3, 4) * 0.7, self._sweep(120, 420, 0.3) * 0.5), 0.45),
            "horn_puppy": _to_sound(np.tanh(_puppy_horn() * 2.2) / np.tanh(2.2), 1.0),
            "horn_ship": _to_sound(np.tanh(_ship_horn() * 2.0) / np.tanh(2.0), 1.0),
            "horn_siren": _to_sound(self._siren(), 0.95),
            "count": _to_sound(_tone(660, 0.18, 10, "square"), 0.3),
            "go": _to_sound(_tone(1320, 0.45, 5, "square"), 0.32),
            "finish": _to_sound(self._arpeggio([523, 659, 784, 1046, 1318], 0.09), 0.5),
            "turbo": _to_sound(self._blow_off(), 0.5),
        }
        self.voices = Voices()
        self.boost_loop = _to_sound(self._whoosh(), 0.5)
        self.tracks = {}
        try:
            self.tracks["menu"] = pygame.mixer.Sound(str(music.load("menu")))
        except (pygame.error, OSError):
            pass
        if WEB:
            self._load_tracks()
        else:
            threading.Thread(target=self._load_tracks, daemon=True).start()

    def _load_tracks(self):
        for name in music.TRACKS:
            if name in self.tracks:
                continue
            try:
                self.tracks[name] = pygame.mixer.Sound(str(music.load(name)))
            except (pygame.error, OSError):
                continue
            if self.track == name:                 # it was asked for before it was ready
                self.track = None
                self._want = name

    @staticmethod
    def _siren():
        """Police siren: a few wailing cycles."""
        dur = 1.6
        n = int(SR * dur)
        t = np.arange(n) / SR
        f = 750 + 350 * np.sin(2 * np.pi * 1.25 * t - np.pi / 2)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sign(np.sin(ph))
        return x * np.minimum(1, t / 0.05) * np.clip((dur - t) / 0.1, 0, 1) * 0.5

    def set_volumes(self, vol):
        self.vol.update(vol)
        self._apply_music_volume()

    def _apply_music_volume(self):
        if not self.ok:
            return
        base = 0.55 if self.track == "menu" else 0.5
        duck = 0.3 if pygame.time.get_ticks() / 1000 < self._duck_until else 1.0
        self.music_ch.set_volume(base * self.vol["music"] * self.vol["master"] * duck)

    def tick(self):
        """Once per frame: start a track that finished loading, restore ducked music."""
        want = getattr(self, "_want", None)
        if want and want in self.tracks:
            self._want = None
            self.music(want)
        if self.ok and self._duck_until:
            self._apply_music_volume()
            if pygame.time.get_ticks() / 1000 > self._duck_until:
                self._duck_until = 0.0
                self._apply_music_volume()

    @staticmethod
    def _sweep(f0, f1, dur):
        n = int(SR * dur)
        t = np.arange(n) / SR
        f = f0 + (f1 - f0) * (t / dur) ** 0.7
        ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sign(np.sin(ph)) * 0.35 * _env(n, decay=5)

    @staticmethod
    def _arpeggio(freqs, step):
        n = int(SR * (step * len(freqs) + 0.25))
        out = np.zeros(n)
        for i, f in enumerate(freqs):
            t = _tone(f, 0.25, 14, "tri")
            o = int(i * step * SR)
            out[o:o + len(t)] += t[:n - o]
        return out * 0.7

    @staticmethod
    def _blow_off():
        """Turbo blow-off valve: a sharp hiss with a 'stu-tu-tu' flutter as it dies away."""
        n = int(SR * 0.55)
        t = np.arange(n) / SR
        x = np.random.default_rng(11).uniform(-1, 1, n)
        hiss = x - np.convolve(x, np.ones(6) / 6, mode="same")           # high-passed: just the hiss
        flutter = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * (34 - 20 * t) * t))
        env = np.minimum(1.0, t / 0.006) * np.exp(-t * 6.5)
        return hiss * flutter * env * 1.6

    @staticmethod
    def _whoosh():
        """A seamless one-second jet loop (noise crossfaded onto itself)."""
        n, q = SR, SR // 4
        x = np.random.default_rng(8).uniform(-1, 1, n + q)
        x = np.convolve(x, np.ones(7) / 7, mode="same") * 0.8 + np.convolve(x, np.ones(30) / 30, mode="same") * 2.5
        fade = np.linspace(0, 1, q)
        loop = x[:n].copy()
        loop[:q] = loop[:q] * fade + x[n:] * (1 - fade)
        return loop / (np.abs(loop).max() + 1e-9) * 0.8

    # ------------------------------------------------------------- effects
    def play(self, name, volume=1.0):
        volume *= self.vol["sfx"] * self.vol["master"]
        if self.ok and self.enabled and volume > 0.02:
            ch = self.fx[name].play()
            if ch:
                ch.set_volume(min(1.0, volume))

    def say(self, driver_key, volume=1.0, index=None):
        """The driver shouts a line; returns (text for the speech bubble, line index)."""
        if not self.ok:
            d = next((d for d in DRIVERS if d["key"] == driver_key), DRIVERS[0])
            i = random.randrange(len(d["lines"])) if index is None else index % len(d["lines"])
            return d["lines"][i], i
        text, snd, i = self.voices.say(driver_key, index)
        volume *= self.vol["voice"] * self.vol["master"]
        if snd is not None and self.enabled and volume > 0.02:
            ch = snd.play()
            if ch:
                ch.set_volume(min(1.0, volume))
                self._duck_until = pygame.time.get_ticks() / 1000 + snd.get_length()
                self._apply_music_volume()
        return text, i

    def boost(self, on):
        if not self.ok:
            return
        busy = self.boost_ch.get_busy()
        if on and not busy and self.enabled:
            self.play("boost_on")
            self.boost_ch.play(self.boost_loop, loops=-1, fade_ms=80)
            self.boost_ch.set_volume(self.vol["sfx"] * self.vol["master"])
        elif not on and busy:
            self.boost_ch.fadeout(160)

    # -------------------------------------------------------------- engine
    def engine_start(self, profile, turbo=0.0):
        if not self.ok:
            return
        self.synth = EngineSynth(profile, turbo)
        self.engine_ch.stop()
        self._feed(0.0, 0.0)

    def engine_stop(self):
        if self.ok:
            self.engine_ch.stop()
            self.boost_ch.stop()
        self.synth = None

    def engine_update(self, rpm, load, on=True):
        if self.ok and self.synth is not None:
            self._feed(rpm, load, on)

    def _feed(self, rpm, load, on=True):
        ch = self.engine_ch
        ch.set_volume(0.9 * self.vol["sfx"] * self.vol["master"] if self.enabled and on else 0.0)
        if not ch.get_busy():
            snd = _to_sound(self.synth.render(rpm, load))
            self._recent.append(snd)
            ch.play(snd)
        if ch.get_queue() is None:
            snd = _to_sound(self.synth.render(rpm, load))
            self._recent.append(snd)
            ch.queue(snd)

    # --------------------------------------------------------------- music
    def music(self, name):
        if not self.ok or name == self.track:
            return
        self.track = name
        # fade the old track out on its own channel while the new one fades in on the other
        self.music_ch.fadeout(700)
        if name and self.music_on:
            if name in self.tracks:
                self.music_ch = self.music_chs[1] if self.music_ch is self.music_chs[0] else self.music_chs[0]
                self.music_ch.stop()
                self.music_ch.play(self.tracks[name], loops=-1, fade_ms=900)
                self._apply_music_volume()
            else:
                self._want, self.track = name, None

    def set_music(self, on):
        self.music_on = on
        if not self.ok:
            return
        if on:
            current, self.track = self.track, None
            self.music(current)
        else:
            for ch in self.music_chs:
                ch.fadeout(300)
