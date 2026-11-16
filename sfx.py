"""Собирает звуковую дорожку ролика из меток cues.json (их пишет render.js из window.CUES).
Все звуки синтезируются здесь, без сторонних файлов.
Запуск: python3 sfx.py <папка проекта>  ->  <папка>/sound.wav
"""
import json
import os
import sys
import wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def t_(dur):
    return np.arange(int(SR * dur)) / SR


def lowpass(x, cutoff):
    a = 1 - np.exp(-2 * np.pi * np.asarray(cutoff) / SR)
    y = np.zeros_like(x)
    s = 0.0
    for n in range(len(x)):
        s += a[n] * (x[n] - s)
        y[n] = s
    return y


def make_whoosh(dur, up):
    t = t_(dur)
    sweep = np.linspace(500, 5200, len(t)) if up else np.linspace(5200, 500, len(t))
    noise = rng.standard_normal(len(t))
    return (lowpass(noise, sweep) - lowpass(noise, sweep * 0.35)) * np.sin(np.pi * t / dur) ** 2 * 0.9


WHOOSH_UP = [make_whoosh(0.3, True) for _ in range(4)]
WHOOSH_DOWN = [make_whoosh(0.34, False) for _ in range(3)]


def pop(pitch=1.0, dur=0.11):
    t = t_(dur)
    f0, f1 = 540 * pitch, 185 * pitch
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32)


def tick():
    t = t_(0.018)
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + rng.standard_normal(len(t)) * 0.4) * np.exp(-t * 320)


def ding(f, dur=0.8):
    t = t_(dur)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3.01 * f * t)
    return s * np.exp(-t * 7) * np.minimum(1, t / 0.004)


def thud(dur=0.25):
    t = t_(dur)
    f = 300 * (90 / 300) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)


def click():
    t = t_(0.06)
    k = tick()
    return np.sin(2 * np.pi * 150 * t) * np.exp(-t * 70) + np.pad(k, (0, len(t) - len(k))) * 0.8


def riser(dur):
    t = t_(dur)
    f = 180 * (4.0 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    noise = lowpass(rng.standard_normal(len(t)), np.linspace(400, 6000, len(t))) * 0.5
    return (tone + noise) * (t / dur) ** 1.6 * np.minimum(1, (dur - t) / 0.03)


def pad(freqs, dur):
    t = t_(dur)
    s = sum(np.sin(2 * np.pi * f * t + i) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for i, f in enumerate(freqs))
    return s / len(freqs) * np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.5)


def pluck(f, dur=0.32):
    t = t_(dur)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 11) * np.minimum(1, t / 0.003)


def build(project):
    with open(os.path.join(project, "cues.json"), encoding="utf-8") as f:
        data = json.load(f)
    total = float(data["duration"])
    mix = np.zeros((int(SR * (total + 6)), 2))

    def put(sig, at, gain=1.0, pan=0.0):
        i = int(max(0, at) * SR)
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        mix[i:i + len(sig), 0] += sig * gain * left
        mix[i:i + len(sig), 1] += sig * gain * right

    # Музыка: мягкий пэд, бас и арпеджио, 104 удара в минуту.
    beat = 60 / 104
    bar = beat * 4
    chords = [
        [174.61, 220.00, 261.63, 329.63],  # Fmaj7
        [220.00, 261.63, 329.63, 392.00],  # Am7
        [146.83, 220.00, 261.63, 349.23],  # Dm7
        [196.00, 246.94, 293.66, 392.00],  # G
    ]
    order = [0, 2, 1, 3, 2, 3, 1, 2]
    for b in range(int(np.ceil(total / bar))):
        ch = chords[b % 4]
        put(pad(ch, bar + 0.6), b * bar, 0.085)
        put(pad([ch[0] / 2], bar + 0.3), b * bar, 0.10)
        if b >= 2:  # арпеджио вступает с третьего такта
            octave = 4 if (b // 4) % 2 else 2
            for k in range(8):
                put(pluck(ch[order[k]] * octave), b * bar + k * beat / 2, 0.05, pan=0.5 if k % 2 else -0.5)

    # Эффекты по меткам.
    for i, c in enumerate(data["cues"]):
        kind, at, gain, pan = c["type"], c["t"], c.get("gain", 0.4), c.get("pan", 0.0)
        if kind == "whoosh":
            put(WHOOSH_UP[i % len(WHOOSH_UP)], at, gain, pan)
        elif kind == "whoosh_out":
            put(WHOOSH_DOWN[i % len(WHOOSH_DOWN)], at, gain, pan)
        elif kind == "pop":
            put(pop(c.get("pitch", 1.0)), at, gain, pan)
        elif kind == "tick":
            put(tick(), at, gain, pan)
        elif kind == "ticks":
            n = max(1, int(c.get("n", 10)))
            for j in range(n):
                put(tick(), at + c.get("dur", 1.0) * j / n, gain * (0.8 + 0.4 * rng.random()), pan)
        elif kind == "ding":
            put(ding(c.get("f", 1046.5)), at, gain, pan)
        elif kind == "thud":
            put(thud(), at, gain, pan)
        elif kind == "click":
            put(click(), at, gain, pan)
        elif kind == "riser":
            put(riser(c.get("dur", 1.5)), at, gain, pan)
        else:
            print("неизвестная метка:", kind)

    out = mix[: int(SR * total)]
    t = np.arange(len(out)) / SR
    fade = np.minimum(1, t / 0.15) * np.minimum(1, (total - t) / 0.8)
    out = np.tanh(out * 1.6) * fade[:, None]
    out = out / np.max(np.abs(out)) * 0.89
    path = os.path.join(project, "sound.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    print(f"звук готов: {path} ({len(data['cues'])} меток)")


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1]))
