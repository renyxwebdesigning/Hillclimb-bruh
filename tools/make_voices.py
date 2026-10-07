"""Record the drivers' swear lines with Piper (natural neural text-to-speech) into assets/voice.

Needs the Piper binary and the voice models named in drivers.DRIVERS:
    https://github.com/rhasspy/piper/releases  (piper_linux_x86_64.tar.gz)
    https://huggingface.co/rhasspy/piper-voices  (<model>.onnx + <model>.onnx.json)

    python tools/make_voices.py PATH/TO/piper PATH/TO/voice-models
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from drivers import DRIVERS  # noqa: E402

OUT = os.path.join(ROOT, "assets", "voice")


def polish(samples, rate):
    """Trim silence, normalise to -1 dBFS, short fades so nothing clicks."""
    x = samples.astype(np.float32) / 32768
    loud = np.flatnonzero(np.abs(x) > 0.02)
    if len(loud):
        a = max(0, loud[0] - int(0.02 * rate))
        b = min(len(x), loud[-1] + int(0.12 * rate))
        x = x[a:b]
    x *= 0.89 / max(1e-6, np.abs(x).max())
    fade = int(0.01 * rate)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return (x * 32767).astype(np.int16)


def main(piper, models):
    os.makedirs(OUT, exist_ok=True)
    for d in DRIVERS:
        model, speaker, speed = d["tts"]
        onnx = os.path.join(models, model + ".onnx")
        cfg = json.load(open(onnx + ".json"))
        for i, text in enumerate(d.get("say", d["lines"])):
            raw = os.path.join(OUT, f"{d['key']}_{i}.raw.wav")
            cmd = [piper, "--model", onnx, "--output_file", raw, "--length_scale", str(speed),
                   "--sentence_silence", "0"]
            if speaker is not None:
                cmd += ["--speaker", str(cfg["speaker_id_map"][speaker])]
            subprocess.run(cmd, input=text.encode(), check=True, capture_output=True)
            with wave.open(raw) as w:
                rate = w.getframerate()
                data = np.frombuffer(w.readframes(w.getnframes()), np.int16)
            os.remove(raw)
            with wave.open(os.path.join(OUT, f"{d['key']}_{i}.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(polish(data, rate).tobytes())
            print(d["key"], i, text)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
