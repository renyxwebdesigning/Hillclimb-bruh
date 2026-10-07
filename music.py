"""Original background music, synthesised with numpy and cached as WAV.

Two loops: a relaxed electric-piano groove for the menus and an upbeat
country-rock tune for driving. Both loop seamlessly.
"""
from pathlib import Path

import numpy as np

SR = 44100
CACHE = Path.home() / ".hill_rider" / "cache"
VERSION = 3


def _midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _lp(x, k):
    if k <= 1:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def pluck(f, dur, bright=1.0):
    t = _t(dur)
    out = np.zeros_like(t)
    for h in range(1, 9):
        out += (1 / h ** 1.15) * np.exp(-t * (2.5 + h * 2.4 / bright)) * np.sin(2 * np.pi * f * h * t * (1 + 0.0007 * h))
    return out * (1 - np.exp(-t * 500)) * 0.5


def bass(f, dur):
    t = _t(dur)
    out = 0.8 * np.sin(2 * np.pi * f * t)
    for h in range(2, 6):
        out += (0.5 / h) * np.sin(2 * np.pi * f * h * t)
    env = (1 - np.exp(-t * 300)) * np.exp(-t * 2.2) * np.clip((dur - t) * 30, 0, 1)
    return out * env * 0.55


def lead(f, dur):
    t = _t(dur + 0.12)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) * 4, 0, 1)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    out = np.sin(ph) + 0.28 * np.sin(3 * ph) + 0.12 * np.sin(5 * ph) + 0.18 * np.sin(2 * ph)
    env = np.minimum(1, t / 0.012) * (0.75 + 0.25 * np.exp(-t * 8))
    env *= np.clip((dur + 0.1 - t) / 0.1, 0, 1)
    return out * env * 0.22


def epiano(f, dur):
    t = _t(dur + 0.6)
    out = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6) + 0.08 * np.sin(6 * np.pi * f * t)
    env = (1 - np.exp(-t * 200)) * np.exp(-t * 1.6) * (1 + 0.12 * np.sin(2 * np.pi * 4.2 * t))
    return out * env * 0.3


def kick():
    t = _t(0.35)
    f = 48 + 100 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 9) + 0.3 * np.exp(-t * 300)) * 0.9


def snare(rng):
    t = _t(0.22)
    n = rng.uniform(-1, 1, len(t))
    n = _lp(n - _lp(n, 6), 2)
    return (n * np.exp(-t * 20) * 0.7 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.45) * 0.8


def hat(rng, open_=False):
    t = _t(0.25 if open_ else 0.06)
    n = rng.uniform(-1, 1, len(t))
    n = n - _lp(n, 3)
    return n * np.exp(-t * (14 if open_ else 70)) * 0.28


class Track:
    def __init__(self, bpm, bars):
        self.beat = 60.0 / bpm
        self.length = int(round(bars * 4 * self.beat * SR))
        self.buf = np.zeros((self.length + SR * 3, 2))

    def add(self, beat, sig, pan=0.5, vol=1.0):
        i = int(round(beat * self.beat * SR))
        sig = sig * vol
        n = min(len(sig), len(self.buf) - i)
        self.buf[i:i + n, 0] += sig[:n] * np.sqrt(1 - pan)
        self.buf[i:i + n, 1] += sig[:n] * np.sqrt(pan)

    def render(self):
        out = self.buf[:self.length].copy()
        tail = self.buf[self.length:]
        out[:len(tail)] += tail[:self.length]          # wrap tails for a seamless loop
        out = np.tanh(out * 1.2)
        return out / (np.abs(out).max() + 1e-9) * 0.9


def drive_track():
    rng = np.random.default_rng(5)
    tr = Track(bpm=126, bars=16)
    chords = {"A": ((57, 61, 64), 45), "E": ((56, 59, 64), 40), "F#m": ((57, 61, 66), 42),
              "D": ((57, 62, 66), 38), "C#m": ((56, 61, 64), 37)}
    prog = ["A", "E", "F#m", "D", "A", "E", "F#m", "D", "D", "E", "C#m", "F#m", "D", "E", "A", "A"]
    for bar, name in enumerate(prog):
        notes, root = chords[name]
        b0 = bar * 4
        # drums
        for e in range(8):
            tr.add(b0 + e * 0.5, hat(rng, open_=(e == 7)), 0.68, 0.9 if e % 2 else 0.6)
        for beat in (0, 1.5, 2):
            tr.add(b0 + beat, kick(), 0.5, 1.0)
        tr.add(b0 + 1, snare(rng), 0.45)
        tr.add(b0 + 3, snare(rng), 0.45)
        if bar in (7, 15):
            for k in range(4):
                tr.add(b0 + 3 + k * 0.25, snare(rng), 0.45, 0.5 + k * 0.12)
        # bass: root-fifth walking eighths
        pattern = [0, 0, 7, 0, 12, 0, 7, 4 if name in ("A", "D", "E") else 3]
        for e, iv in enumerate(pattern):
            tr.add(b0 + e * 0.5, bass(_midi(root + iv), 0.45 * tr.beat), 0.5, 0.9)
        # rhythm guitar: full strum on 1, chops on the off-beats
        for i, m in enumerate(notes):
            tr.add(b0 + i * 0.02, pluck(_midi(m), 1.2, 1.2), 0.3, 0.55)
        for e in (1, 3, 5, 7):
            for i, m in enumerate(notes):
                tr.add(b0 + e * 0.5 + i * 0.012, pluck(_midi(m + 12), 0.22, 0.8), 0.3, 0.35)
    melody = [
        (0, 0, 1, 76), (0, 1, .5, 73), (0, 1.5, .5, 76), (0, 2, 1, 78), (0, 3, 1, 76),
        (1, 0, 1, 76), (1, 1, .5, 74), (1, 1.5, .5, 73), (1, 2, 1.5, 71), (1, 3.5, .5, 69),
        (2, 0, 1, 73), (2, 1, .5, 69), (2, 1.5, .5, 73), (2, 2, 1, 78), (2, 3, 1, 76),
        (3, 0, 1.5, 74), (3, 1.5, .5, 73), (3, 2, 2, 69),
        (4, 0, 1, 76), (4, 1, .5, 73), (4, 1.5, .5, 76), (4, 2, 1, 78), (4, 3, 1, 81),
        (5, 0, 1, 80), (5, 1, .5, 78), (5, 1.5, .5, 76), (5, 2, 2, 71),
        (6, 0, 1, 73), (6, 1, .5, 76), (6, 1.5, .5, 78), (6, 2, 1, 81), (6, 3, 1, 78),
        (7, 0, 1, 74), (7, 1, 1, 76), (7, 2, 2, 81),
        (8, 0, 1, 78), (8, 1, 1, 81), (8, 2, 2, 78),
        (9, 0, 1, 80), (9, 1, 1, 76), (9, 2, 2, 71),
        (10, 0, 1, 76), (10, 1, 1, 73), (10, 2, 1, 68), (10, 3, 1, 73),
        (11, 0, 2, 73), (11, 2, 1, 76), (11, 3, 1, 78),
        (12, 0, 1, 81), (12, 1, 1, 78), (12, 2, 2, 74),
        (13, 0, 1, 76), (13, 1, 1, 80), (13, 2, 2, 83),
        (14, 0, 3, 81),
        (15, 3, .5, 76), (15, 3.5, .5, 78),
    ]
    for bar, beat, dur, m in melody:
        tr.add(bar * 4 + beat, lead(_midi(m), dur * tr.beat * 0.95), 0.55, 1.0)
    return tr.render()


def menu_track():
    rng = np.random.default_rng(9)
    tr = Track(bpm=92, bars=8)
    chords = [((62, 66, 69, 73), 38), ((59, 62, 66, 69), 35), ((55, 59, 62, 66), 43), ((57, 61, 64, 66), 45)]
    for bar in range(8):
        notes, root = chords[bar // 2]
        b0 = bar * 4
        tr.add(b0, bass(_midi(root), 1.8 * tr.beat), 0.5, 0.8)
        tr.add(b0 + 2.5, bass(_midi(root + 7), 1.3 * tr.beat), 0.5, 0.6)
        arp = list(notes) + [notes[1] + 12, notes[2] + 12, notes[3], notes[1]]
        for e, m in enumerate(arp):
            tr.add(b0 + e * 0.5, epiano(_midi(m), 0.5 * tr.beat), 0.35 + 0.3 * (e % 2), 0.7)
        if bar % 2 == 0:
            for i, m in enumerate(notes):
                tr.add(b0 + i * 0.03, epiano(_midi(m - 12), 3.6 * tr.beat), 0.5, 0.35)
        for e in range(8):
            tr.add(b0 + e * 0.5, hat(rng), 0.7, 0.35 if e % 2 else 0.2)
        tr.add(b0, kick(), 0.5, 0.5)
        tr.add(b0 + 2.5, kick(), 0.5, 0.35)
    return tr.render()


# ---------------------------------------------------------------- more tracks
def saw(f, dur, harm=10, decay=3.0, attack=0.004):
    t = _t(dur)
    out = np.zeros_like(t)
    for h in range(1, harm + 1):
        out += np.sin(2 * np.pi * f * h * t) / h
    return out * np.minimum(1, t / attack) * np.exp(-t * decay)


def powerchord(f, dur, mute=False):
    t = _t(dur)
    x = sum(saw(f * r, dur, 8, 9.0 if mute else 1.6) for r in (1, 1.498, 2.0))
    x = np.tanh(x * 3.2) * 0.5
    return x * np.clip((dur - t) * 40, 0, 1)


def square(f, dur, duty=0.5, decay=1.5):
    t = _t(dur)
    ph = (f * t) % 1.0
    x = np.where(ph < duty, 1.0, -1.0) * 0.25
    return x * np.exp(-t * decay) * np.clip((dur - t) * 60, 0, 1)


def tri(f, dur):
    t = _t(dur)
    x = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t)) * 0.5
    return x * np.clip((dur - t) * 60, 0, 1) * np.minimum(1, t / 0.003)


def chip_noise(rng, dur, decay):
    t = _t(dur)
    return np.sign(rng.uniform(-1, 1, len(t))) * np.exp(-t * decay) * 0.18


def clap(rng):
    t = _t(0.25)
    n = rng.uniform(-1, 1, len(t))
    n = n - _lp(n, 4)
    env = np.exp(-t * 18) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < 0.03))
    return n * env * 0.6


def crash(rng):
    t = _t(1.6)
    n = rng.uniform(-1, 1, len(t))
    return (n - _lp(n, 2)) * np.exp(-t * 2.4) * 0.22


def rock_track():
    rng = np.random.default_rng(21)
    tr = Track(bpm=144, bars=16)
    prog = [(40, "Em"), (36, "C"), (43, "G"), (38, "D")] * 4
    melody = [76, 79, 81, 79, 76, 74, 71, 74, 76, 79, 83, 81, 79, 76, 74, 76]
    for bar, (root, _) in enumerate(prog):
        b0 = bar * 4
        if bar % 4 == 0:
            tr.add(b0, crash(rng), 0.6, 0.9)
        for beat in (0, 1.5, 2, 3.5 if bar % 2 else 2.5):
            tr.add(b0 + beat, kick(), 0.5, 1.0)
        tr.add(b0 + 1, snare(rng), 0.45, 1.1)
        tr.add(b0 + 3, snare(rng), 0.45, 1.1)
        for e in range(8):
            tr.add(b0 + e * 0.5, hat(rng), 0.65, 0.5 if e % 2 else 0.8)
            tr.add(b0 + e * 0.5, bass(_midi(root), 0.45 * tr.beat), 0.5, 0.9)
            tr.add(b0 + e * 0.5, powerchord(_midi(root + 12), (0.95 if e == 0 else 0.45) * tr.beat, mute=e != 0),
                   0.3 if e % 2 else 0.7, 0.55)
        if bar >= 8:
            for k in range(2):
                m = melody[(bar * 2 + k) % len(melody)]
                tr.add(b0 + k * 2, lead(_midi(m), 1.9 * tr.beat), 0.5, 0.9)
    return tr.render()


def chiptune_track():
    rng = np.random.default_rng(33)
    tr = Track(bpm=150, bars=16)
    chords = [(60, (0, 4, 7)), (57, (0, 3, 7)), (53, (0, 4, 7)), (55, (0, 4, 7))]
    melody = [72, 74, 76, 79, 76, 74, 72, 67, 69, 72, 74, 76, 74, 72, 69, 67,
              65, 69, 72, 74, 72, 69, 65, 64, 67, 71, 74, 79, 77, 74, 71, 67]
    for bar in range(16):
        root, iv = chords[bar % 4]
        b0 = bar * 4
        for e in range(16):
            m = root + iv[e % 3] + (12 if (e // 3) % 2 else 0)
            tr.add(b0 + e * 0.25, square(_midi(m), 0.22 * tr.beat, 0.25, 6), 0.3, 0.45)
        for e in range(4):
            tr.add(b0 + e, tri(_midi(root - 24 + (7 if e == 2 else 0)), 0.9 * tr.beat), 0.5, 0.9)
        for e in range(8):
            tr.add(b0 + e * 0.5, chip_noise(rng, 0.04, 80), 0.7, 0.6)
        tr.add(b0 + 1, chip_noise(rng, 0.15, 25), 0.5, 1.0)
        tr.add(b0 + 3, chip_noise(rng, 0.15, 25), 0.5, 1.0)
        tr.add(b0, kick(), 0.5, 0.7)
        tr.add(b0 + 2, kick(), 0.5, 0.7)
        for k in range(2):
            m = melody[(bar * 2 + k) % len(melody)]
            tr.add(b0 + k * 2, square(_midi(m), 1.8 * tr.beat, 0.5, 0.6), 0.6, 0.8)
    return tr.render()


def techno_track():
    rng = np.random.default_rng(44)
    tr = Track(bpm=128, bars=16)
    roots = [45, 45, 41, 43]
    for bar in range(16):
        root = roots[(bar // 2) % 4]
        b0 = bar * 4
        for beat in range(4):
            tr.add(b0 + beat, kick(), 0.5, 1.1)
            tr.add(b0 + beat + 0.5, hat(rng, open_=True), 0.65, 0.6)
        if bar >= 2:
            tr.add(b0 + 1, clap(rng), 0.45, 0.9)
            tr.add(b0 + 3, clap(rng), 0.45, 0.9)
        for e in range(16):
            if e % 4 != 0:
                tr.add(b0 + e * 0.25, saw(_midi(root - 12 + (12 if e % 8 == 6 else 0)), 0.2 * tr.beat, 6, 9), 0.5, 0.55)
        if bar >= 4:
            for e in (0.75, 2.75):
                for d in (0, 3, 7, 12):
                    for det in (0.995, 1.005):
                        tr.add(b0 + e, saw(_midi(root + 12 + d) * det, 0.4 * tr.beat, 8, 6), 0.3 if det < 1 else 0.7,
                               0.12)
        for e in range(16):
            tr.add(b0 + e * 0.25, hat(rng), 0.75, 0.18 if e % 2 else 0.1)
    return tr.render()


def lofi_track():
    rng = np.random.default_rng(55)
    tr = Track(bpm=80, bars=8)
    chords = [((62, 65, 69, 72, 76), 38), ((55, 59, 62, 65, 69), 43), ((60, 64, 67, 71, 74), 36),
              ((57, 61, 64, 67, 71), 45)]
    for bar in range(8):
        notes, root = chords[bar % 4]
        b0 = bar * 4
        for beat in (0, 2.5):
            for i, m in enumerate(notes):
                tr.add(b0 + beat + i * 0.04, epiano(_midi(m), (2.3 if beat == 0 else 1.3) * tr.beat), 0.4 + 0.05 * i,
                       0.5)
        tr.add(b0, bass(_midi(root), 1.6 * tr.beat), 0.5, 0.9)
        tr.add(b0 + 2.5, bass(_midi(root + 7), 1.2 * tr.beat), 0.5, 0.7)
        tr.add(b0, kick(), 0.5, 0.7)
        tr.add(b0 + 1.66, kick(), 0.5, 0.5)
        tr.add(b0 + 1, snare(rng), 0.45, 0.45)
        tr.add(b0 + 3, snare(rng), 0.45, 0.45)
        for e in range(8):
            swing = 0.08 if e % 2 else 0
            tr.add(b0 + e * 0.5 + swing, hat(rng), 0.7, 0.25 if e % 2 else 0.15)
    out = tr.render()
    crackle = np.zeros(len(out))
    idx = rng.integers(0, len(out), len(out) // 1800)
    crackle[idx] = rng.uniform(-0.25, 0.25, len(idx))
    out[:, 0] += crackle
    out[:, 1] += np.roll(crackle, 37)
    return out / (np.abs(out).max() + 1e-9) * 0.9


TRACKS = {"menu": ("Menu", menu_track), "drive": ("Country", drive_track), "rock": ("Rock", rock_track),
          "chiptune": ("8-Bit", chiptune_track), "techno": ("Techno", techno_track), "lofi": ("Lo-Fi", lofi_track)}
DRIVE_TRACKS = ["drive", "rock", "chiptune", "techno", "lofi"]
STAGE_MUSIC = {"countryside": "drive", "desert": "rock", "arctic": "lofi", "moon": "chiptune", "city": "techno",
               "volcano": "rock", "jungle": "lofi", "mars": "chiptune", "ocean": "lofi", "seasons": "drive"}


def load(name):
    """Path of the track: the bundled OGG if there is one, else a cached WAV rendered on demand."""
    from gfx import resource
    bundled = Path(resource("assets", "music", f"{name}.ogg"))
    if bundled.exists():
        return bundled
    path = CACHE / f"{name}_v{VERSION}.wav"
    if not path.exists():
        import wave                      # only needed when a track has to be rendered
        data = TRACKS[name][1]()
        CACHE.mkdir(parents=True, exist_ok=True)
        pcm = (data * 32000).astype(np.int16)
        tmp = path.with_suffix(".tmp")
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(pcm.tobytes())
        tmp.replace(path)
    return path
