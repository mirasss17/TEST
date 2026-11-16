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


def impact(dur=1.6):
    """Низкий удар с шумовым хвостом — для драматических моментов."""
    t = t_(dur)
    f = 70 * (32 / 70) ** (t / dur)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    tail = lowpass(rng.standard_normal(len(t)), np.linspace(2500, 200, len(t))) * np.exp(-t * 5) * 0.6
    return (boom + tail) * np.minimum(1, t / 0.003)


def kick():
    t = t_(0.16)
    f = 120 * (45 / 120) ** (t / 0.16)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 24)


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
    size = int(SR * (total + 6))
    music, fx, voice = np.zeros((size, 2)), np.zeros((size, 2)), np.zeros((size, 2))
    bus = {"cur": music}

    def put(sig, at, gain=1.0, pan=0.0):
        i = int(max(0, at) * SR)
        mix = bus["cur"]
        sig = sig[: size - i]
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        mix[i:i + len(sig), 0] += sig * gain * left
        mix[i:i + len(sig), 1] += sig * gain * right

    # Музыка. Настроение задают метки mood: calm (по умолчанию), dark (тревога), hero (подъём).
    moods = sorted((c["t"], c["mode"]) for c in data["cues"] if c["type"] == "mood")

    def mood_at(t):
        cur = "calm"
        for mt, mode in moods:
            if mt <= t + 0.01:
                cur = mode
        return cur

    beat = 60 / 104
    bar = beat * 4
    bright = [
        [174.61, 220.00, 261.63, 329.63],  # Fmaj7
        [220.00, 261.63, 329.63, 392.00],  # Am7
        [146.83, 220.00, 261.63, 349.23],  # Dm7
        [196.00, 246.94, 293.66, 392.00],  # G
    ]
    grim = [
        [146.83, 174.61, 220.00],  # Dm
        [116.54, 146.83, 174.61],  # Bb
        [98.00, 116.54, 146.83],   # Gm
        [110.00, 138.59, 164.81],  # A
    ]
    order = [0, 2, 1, 3, 2, 3, 1, 2]
    half = bar / 2
    for h in range(int(np.ceil(total / half))):   # шаг — полтакта, чтобы настроение менялось быстро
        at = h * half
        mode = mood_at(at)
        b = h // 2
        if mode == "dark":
            ch = grim[b % 4]
            put(pad(ch, half + 0.5), at, 0.10)
            put(pad([36.71 * 2, 36.71 * 3], half + 0.5), at, 0.16)      # низкий гул
            put(thud(0.2), at, 0.34)                                    # сердцебиение
            put(thud(0.2), at + 0.27, 0.22)
        else:
            ch = bright[b % 4]
            put(pad(ch, half + 0.5), at, 0.085 if mode == "calm" else 0.10)
            put(pad([ch[0] / 2], half + 0.3), at, 0.10)
            hero = mode == "hero"
            if hero or b >= 2:
                for k in range(4):
                    kk = k + (h % 2) * 4
                    put(pluck(ch[order[kk]] * 2), at + k * beat / 2, 0.05, pan=0.5 if kk % 2 else -0.5)
                    if hero:
                        put(pluck(ch[order[(kk + 3) % 8]] * 4), at + k * beat / 2, 0.035, pan=-0.5 if kk % 2 else 0.5)
            if hero:
                put(kick(), at, 0.30)
                put(kick(), at + beat, 0.24)
                put(tick(), at + beat / 2, 0.05)
                put(tick(), at + beat * 1.5, 0.05)

    # Метка cut: музыка резко замолкает и плавно возвращается.
    tt = np.arange(size) / SR
    for c in data["cues"]:
        if c["type"] == "cut":
            t0, d = c["t"], c.get("dur", 1.0)
            env = np.clip((t0 - tt) / 0.04, 0, 1) + np.clip((tt - t0 - d) / 0.6, 0, 1)
            music *= np.clip(env, 0, 1)[:, None]

    # Эффекты по меткам.
    bus["cur"] = fx
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
        elif kind == "impact":
            put(impact(), at, gain, pan)
        elif kind in ("mood", "cut"):
            pass
        elif kind == "thud":
            put(thud(), at, gain, pan)
        elif kind == "click":
            put(click(), at, gain, pan)
        elif kind == "riser":
            put(riser(c.get("dur", 1.5)), at, gain, pan)
        else:
            print("неизвестная метка:", kind)

    # Голос за кадром: если есть voice.json, кладём фразы и приглушаем музыку с эффектами.
    voice_path = os.path.join(project, "voice.json")
    has_voice = os.path.exists(voice_path)
    if has_voice:
        import soundfile as sf
        bus["cur"] = voice
        with open(voice_path, encoding="utf-8") as f:
            for item in json.load(f):
                x, rate = sf.read(os.path.join(project, item["file"]), dtype="float32")
                n = int(len(x) * SR / rate)
                put(np.interp(np.arange(n) * rate / SR, np.arange(len(x)), x), item["t"], 1.0)
        voice /= max(1e-6, np.max(np.abs(voice))) / 0.8
        mix = voice + music * 0.5 + fx * 0.5
    else:
        mix = music + fx

    out = mix[: int(SR * total)]
    t = np.arange(len(out)) / SR
    fade = np.minimum(1, t / 0.15) * np.minimum(1, (total - t) / 0.8)
    out = np.tanh(out * (1.25 if has_voice else 1.6)) * fade[:, None]
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
