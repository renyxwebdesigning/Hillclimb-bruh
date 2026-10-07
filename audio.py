"""Sound: a real-time synthesised engine per vehicle, effects and music.

The engine is generated on the fly in short chunks and queued on its own
mixer channel, so pitch follows RPM smoothly instead of crossfading loops.
If there is no sound device the game runs silently.
"""
import random
import shutil
from pathlib import Path
import subprocess
import threading
from collections import deque

import numpy as np
import pygame

import music
from drivers import DRIVERS

SR = 44100
CHUNK = 1764            # 40 ms of engine audio per queued chunk

# Firing-frequency range (Hz), spectral tilt, sub-harmonic (uneven firing)
# amount, two exhaust resonances (centre Hz, width Hz, gain), combustion noise.
PROFILES = {
    "jeep": dict(idle=24, top=120, tilt=1.05, sub=0.55, f1=(190, 130, 2.0), f2=(620, 320, 0.9), noise=0.22, gain=0.55),
    "dirtbike": dict(idle=50, top=255, tilt=0.72, sub=0.12, f1=(900, 500, 1.6), f2=(2200, 800, 0.8), noise=0.35, gain=0.42),
    "chopper": dict(idle=13, top=64, tilt=1.15, sub=1.1, f1=(140, 90, 2.2), f2=(480, 240, 1.0), noise=0.32, gain=0.62),
    "monster": dict(idle=17, top=94, tilt=1.2, sub=0.8, f1=(120, 80, 2.4), f2=(380, 200, 1.1), noise=0.3, gain=0.62),
    "supercar": dict(idle=34, top=275, tilt=0.85, sub=0.2, f1=(420, 250, 1.6), f2=(1500, 600, 1.0), noise=0.18, gain=0.46),
    "rocket": dict(rocket=True, gain=0.36),
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

    def __init__(self, profile):
        self.p = PROFILES[profile]
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
        if p.get("rocket"):
            return self._rocket(n, load0, self.load)
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
        return np.tanh(y * 1.6) / np.tanh(1.6)

    def _rocket(self, n, l0, l1):
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


def _seize():
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    f = 260 * np.exp(-t * 2.2) + 40
    ph = 2 * np.pi * np.cumsum(f) / SR
    grind = np.sign(np.sin(ph)) * 0.4 * np.exp(-t * 2.5)
    bang = _noise(0.25, 14, 3, 6) * 1.0
    clank = sum(np.sin(2 * np.pi * fr * t) * np.exp(-t * 9) for fr in (523, 1187, 2011)) * 0.25
    return _mix(grind, bang, clank)


def _wrench():
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * fr * t) * np.exp(-t * d) for fr, a, d in
            ((2350, 0.5, 18), (3720, 0.35, 24), (5230, 0.25, 30), (870, 0.3, 14)))
    return _mix(y, _noise(0.03, 120, 2, 9) * 0.5)


def _restart():
    n = int(SR * 0.8)
    t = np.arange(n) / SR
    f = 22 + 70 * (t / 0.8) ** 0.6
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum((1 / k) * np.sin(k * ph) for k in range(1, 12)) * np.minimum(1, t / 0.05) * np.clip((0.8 - t) / 0.2, 0, 1)
    return y * 0.7


class Voices:
    """Driver swear lines, spoken by espeak and cached as WAV files."""

    def __init__(self):
        self.dir = music.CACHE / "voice"
        self.sounds = {}
        self.espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        threading.Thread(target=self._build, daemon=True).start()

    def _path(self, key, i):
        return self.dir / f"{key}_{i}_v1.wav"

    def _build(self):
        if not self.espeak:
            return
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        for d in DRIVERS:
            voice, pitch, speed = d["voice"]
            for i, line in enumerate(d["lines"]):
                path = self._path(d["key"], i)
                if not path.exists():
                    try:
                        subprocess.run([self.espeak, "-v", voice, "-p", str(pitch), "-s", str(speed), "-a", "180",
                                        "-w", str(path), line], timeout=10, capture_output=True)
                    except (OSError, subprocess.SubprocessError):
                        continue

    def say(self, key, index=None):
        """Pick a line for the driver; returns (text, Sound or None, index)."""
        d = next((d for d in DRIVERS if d["key"] == key), DRIVERS[0])
        i = random.randrange(len(d["lines"])) if index is None else index % len(d["lines"])
        snd = self.sounds.get((key, i))
        if snd is None:
            from gfx import resource
            path = Path(resource("assets", "voice", f"{key}_{i}.wav"))
            if not path.exists():
                path = self._path(key, i)
            if path.exists():
                try:
                    snd = self.sounds[(key, i)] = pygame.mixer.Sound(str(path))
                    snd.set_volume(1.0)
                except pygame.error:
                    snd = None
        return d["lines"][i], snd, i


class Audio:
    def __init__(self):
        self.ok = False
        self.enabled = True
        self.music_on = True
        self.track = None
        self.synth = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SR, -16, 2, 512)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(3)
        except pygame.error:
            return
        self.ok = True
        self.engine_ch = pygame.mixer.Channel(0)
        self.boost_ch = pygame.mixer.Channel(1)
        self.music_ch = pygame.mixer.Channel(2)
        self._recent = deque(maxlen=6)
        self.fx = {
            "coin": _to_sound(self._arpeggio([1568, 2093], 0.045), 0.3),
            "fuel": _to_sound(self._sweep(320, 900, 0.32), 0.5),
            "bonus": _to_sound(self._arpeggio([784, 988, 1175, 1568], 0.07), 0.4),
            "crash": _to_sound(_mix(_noise(0.6, 6, 14, 1) * 0.9, _tone(70, 0.5, 7) * 0.8), 0.7),
            "land": _to_sound(_mix(_noise(0.18, 22, 30, 2) * 0.8, _tone(90, 0.15, 25)), 0.5),
            "click": _to_sound(_tone(1200, 0.035, 80, "tri"), 0.35),
            "buy": _to_sound(self._arpeggio([1046, 1568], 0.06), 0.45),
            "deny": _to_sound(_tone(150, 0.22, 10, "square"), 0.3),
            "beep": _to_sound(_tone(880, 0.12, 18, "square"), 0.18),
            "boost_on": _to_sound(_mix(_noise(0.35, 7, 3, 4) * 0.7, self._sweep(120, 420, 0.3) * 0.5), 0.45),
            "horn_puppy": _to_sound(_puppy_horn(), 0.7),
            "horn_ship": _to_sound(_ship_horn(), 0.8),
            "seize": _to_sound(_seize(), 0.75),
            "wrench": _to_sound(_wrench(), 0.55),
            "restart": _to_sound(_restart(), 0.6),
            "count": _to_sound(_tone(660, 0.18, 10, "square"), 0.3),
            "go": _to_sound(_tone(1320, 0.45, 5, "square"), 0.32),
            "finish": _to_sound(self._arpeggio([523, 659, 784, 1046, 1318], 0.09), 0.5),
        }
        self.voices = Voices()
        self.boost_loop = _to_sound(self._whoosh(), 0.5)
        self.tracks = {}
        for name in ("menu", "drive"):
            try:
                self.tracks[name] = pygame.mixer.Sound(str(music.load(name)))
            except (pygame.error, OSError):
                pass

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
        if snd is not None and self.enabled and volume > 0.02:
            ch = snd.play()
            if ch:
                ch.set_volume(min(1.0, volume))
        return text, i

    def boost(self, on):
        if not self.ok:
            return
        busy = self.boost_ch.get_busy()
        if on and not busy and self.enabled:
            self.play("boost_on")
            self.boost_ch.play(self.boost_loop, loops=-1, fade_ms=80)
        elif not on and busy:
            self.boost_ch.fadeout(160)

    # -------------------------------------------------------------- engine
    def engine_start(self, profile):
        if not self.ok:
            return
        self.synth = EngineSynth(profile)
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
        ch.set_volume(0.9 if self.enabled and on else 0.0)
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
        self.music_ch.fadeout(400)
        if name and self.music_on and name in self.tracks:
            self.music_ch.play(self.tracks[name], loops=-1, fade_ms=900)
            self.music_ch.set_volume(0.42 if name == "drive" else 0.5)

    def set_music(self, on):
        self.music_on = on
        if not self.ok:
            return
        if on:
            current, self.track = self.track, None
            self.music(current)
        else:
            self.music_ch.fadeout(300)
