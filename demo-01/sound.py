"""Звуковая дорожка для demo-01: все звуки синтезируются здесь, без сторонних файлов.
Запуск: python3 demo-01/sound.py  ->  demo-01/sound.wav
Времена событий повторяют таймлайн из index.html.
"""
import os
import wave
import numpy as np

SR = 44100
DUR = 13.0
rng = np.random.default_rng(7)
mix = np.zeros((int(SR * (DUR + 5)), 2))


def put(sig, at, gain=1.0, pan=0.0):
    """Положить моно-сигнал на дорожку. pan: -1 слева, 1 справа."""
    i = int(at * SR)
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:i + len(sig), 0] += sig * gain * left
    mix[i:i + len(sig), 1] += sig * gain * right


def t_(dur):
    return np.arange(int(SR * dur)) / SR


def lowpass(x, cutoff):
    """Однополюсный фильтр с меняющейся частотой среза (cutoff — массив в Гц)."""
    a = 1 - np.exp(-2 * np.pi * np.asarray(cutoff) / SR)
    y = np.zeros_like(x)
    s = 0.0
    for n in range(len(x)):
        s += a[n] * (x[n] - s)
        y[n] = s
    return y


def whoosh(dur=0.38, up=True):
    t = t_(dur)
    sweep = np.linspace(500, 5200, len(t)) if up else np.linspace(5200, 500, len(t))
    noise = rng.standard_normal(len(t))
    band = lowpass(noise, sweep) - lowpass(noise, sweep * 0.35)
    return band * np.sin(np.pi * t / dur) ** 2 * 0.9


def pop(f0=560, f1=190, dur=0.11):
    t = t_(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32)


def tick():
    t = t_(0.018)
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + rng.standard_normal(len(t)) * 0.4) * np.exp(-t * 320)


def ding(f, dur=0.7):
    t = t_(dur)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3.01 * f * t)
    return s * np.exp(-t * 7) * np.minimum(1, t / 0.004)


def click():
    t = t_(0.06)
    return np.sin(2 * np.pi * 150 * t) * np.exp(-t * 70) + np.pad(tick(), (0, len(t) - len(tick()))) * 0.8


def riser(dur=1.7):
    t = t_(dur)
    f = 180 * (4.0 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    noise = lowpass(rng.standard_normal(len(t)), np.linspace(400, 6000, len(t))) * 0.5
    return (tone + noise) * (t / dur) ** 1.6 * np.minimum(1, (dur - t) / 0.03)


def pad(freqs, dur):
    t = t_(dur)
    s = sum(np.sin(2 * np.pi * f * t + i) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for i, f in enumerate(freqs))
    env = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.5)
    return s / len(freqs) * env


def pluck(f, dur=0.32):
    t = t_(dur)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 11) * np.minimum(1, t / 0.003)


# --- Музыка: мягкий пэд и арпеджио, 104 удара в минуту ---
beat = 60 / 104
chords = [
    [174.61, 220.00, 261.63, 329.63],  # Fmaj7
    [220.00, 261.63, 329.63, 392.00],  # Am7
    [146.83, 220.00, 261.63, 349.23],  # Dm7
    [196.00, 246.94, 293.66, 392.00],  # G
]
bar = beat * 4
n_bars = int(np.ceil(DUR / bar))
for b in range(n_bars):
    ch = chords[b % len(chords)]
    put(pad(ch, bar + 0.6), b * bar, 0.085)
    put(pad([ch[0] / 2], bar + 0.3), b * bar, 0.10)
    for k in range(8):
        note = ch[[0, 2, 1, 3, 2, 3, 1, 2][k]] * 2
        put(pluck(note), b * bar + k * beat / 2, 0.055, pan=0.5 if k % 2 else -0.5)

# --- Эффекты по таймлайну ---
put(pop(), 0.15, 0.5)                                   # плашка
for i, at in enumerate([0.35, 0.51, 0.67]):             # строки заголовка
    put(whoosh(0.3), at, 0.32, pan=-0.3 + 0.3 * i)
put(pop(420, 150, 0.14), 1.2, 0.55)                     # карточка с кодом
for i in range(26):                                     # печать первой строки
    put(tick(), 1.6 + i * 0.9 / 26, 0.16 + 0.05 * rng.random())
for i in range(14):                                     # печать второй строки
    put(tick(), 2.55 + i * 0.4 / 14, 0.16 + 0.05 * rng.random())
put(whoosh(0.34, up=False), 2.98, 0.4)                  # уход сцены 1

put(whoosh(0.3), 3.3, 0.3)                              # «Три шага»
for i, at in enumerate([3.7, 3.95, 4.2]):               # карточки шагов
    put(pop(480 + 60 * i, 170, 0.12), at, 0.5, pan=-0.2 + 0.2 * i)
for i, at in enumerate([4.9, 5.5, 6.1]):                # галочки — восходящие ноты
    put(ding([659.25, 783.99, 1046.50][i]), at, 0.3)
    put(pop(700, 300, 0.06), at, 0.25)
put(whoosh(0.34, up=False), 6.83, 0.4)                  # уход сцены 2

put(whoosh(0.3), 7.15, 0.3)                             # «Рендер»
put(pop(), 7.3, 0.4)
put(pop(420, 150, 0.14), 7.4, 0.5)
put(pop(380, 140, 0.14), 7.6, 0.5)
put(riser(1.7), 7.9, 0.3)                               # счётчик и полоса
for i in range(30):                                     # тиканье счётчика, ускоряется к середине
    p = i / 29
    eased = 0.5 - 0.5 * np.cos(np.pi * p)
    put(tick(), 7.9 + 1.7 * (0.5 * p + 0.5 * eased), 0.12)
put(ding(1046.50, 0.9), 9.6, 0.34)                      # 100 %
put(ding(1318.51, 0.9), 9.6, 0.2)
put(whoosh(0.34, up=False), 10.08, 0.4)                 # уход сцены 3

put(pop(300, 90, 0.22), 10.4, 0.75)                     # «Готово.» — низкий удар
put(ding(523.25, 1.0), 10.42, 0.22)
put(whoosh(0.3), 10.7, 0.25)
put(pop(), 11.05, 0.5)                                  # кнопка
put(whoosh(0.5), 11.42, 0.2, pan=0.4)                   # курсор
put(click(), 12.05, 0.8)                                # клик
put(ding(783.99, 0.8), 12.1, 0.25)
for i in range(3):                                      # три плашки
    put(pop(600 + 90 * i, 260, 0.08), 12.2 + 0.1 * i, 0.4, pan=-0.4 + 0.4 * i)

# --- Сведение: общий фейд и мягкое ограничение ---
out = mix[: int(SR * DUR)]
t = np.arange(len(out)) / SR
fade = np.minimum(1, t / 0.15) * np.minimum(1, (DUR - t) / 0.6)
out = np.tanh(out * 1.6) * fade[:, None]
out = out / np.max(np.abs(out)) * 0.89

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sound.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print("готово:", path)
