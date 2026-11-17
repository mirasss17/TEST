"""Готовая запись голоса -> тайминги для ролика.
Берёт <папка>/voice-full.mp3 (один дубль всего текста) и фразы из <папка>/vo.json,
через ElevenLabs forced alignment находит, где звучит каждая фраза, режет запись по паузам
и раскладывает фразы по времени (между сценами пауза не короче scene_gap).
Пишет <папка>/vo/*.wav, vo.js и voice.json — как voice.py.
Запуск: python3 voice_from_take.py <папка проекта>
"""
import json
import os
import subprocess
import sys
import numpy as np
import soundfile as sf


def main(project):
    cfg = json.load(open(os.path.join(project, "vo.json"), encoding="utf-8"))
    lines = cfg["lines"]
    text = " ".join(l["text"] for l in lines)
    take = os.path.join(project, "voice-full.mp3")
    wav = os.path.join(project, "voice-full.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", take, "-ac", "1", "-ar", "44100", wav], check=True)
    x, rate = sf.read(wav, dtype="float32")

    align_path = os.path.join(project, "align.json")
    if not os.path.exists(align_path):
        txt = os.path.join(project, "text.txt")
        open(txt, "w", encoding="utf-8").write(text)
        code = subprocess.run(["curl", "-sS", "-m", "180", "-o", align_path, "-w", "%{http_code}", "-X", "POST",
                               "https://api.elevenlabs.io/v1/forced-alignment", "-F", f"file=@{take}", "-F", f"text=<{txt}"],
                              capture_output=True, text=True).stdout.strip()
        if code != "200":
            raise RuntimeError("forced alignment: " + code)
    chars = json.load(open(align_path, encoding="utf-8"))["characters"]
    joined = "".join(c["text"] for c in chars)
    if joined != text:
        raise RuntimeError("текст в vo.json не совпадает с тем, по которому делалась разметка: удалите align.json")

    # Границы фраз по символам.
    spans, pos = [], 0
    for l in lines:
        n = len(l["text"])
        seg = [c for c in chars[pos:pos + n] if c["text"].strip() and c["end"] > c["start"]]
        spans.append((seg[0]["start"], seg[-1]["end"]))
        pos += n + 1
    # Режем посередине пауз между фразами.
    cuts = [max(0.0, spans[0][0] - 0.15)] + [(spans[i][1] + spans[i + 1][0]) / 2 for i in range(len(spans) - 1)] + [min(len(x) / rate, spans[-1][1] + 0.4)]

    os.makedirs(os.path.join(project, "vo"), exist_ok=True)
    t = cfg.get("start", 0.4)
    timings, files, prev_scene = {}, [], None
    fade = int(rate * 0.008)
    for i, l in enumerate(lines):
        scene = l["id"][0]
        clip = x[int(cuts[i] * rate): int(cuts[i + 1] * rate)].copy()
        clip[:fade] *= np.linspace(0, 1, fade)
        clip[-fade:] *= np.linspace(1, 0, fade)
        lead = spans[i][0] - cuts[i]            # тишина в начале клипа
        tail = cuts[i + 1] - spans[i][1]        # тишина в конце клипа
        if prev_scene is not None and scene != prev_scene:
            t += max(0.0, cfg.get("scene_gap", 0.7) - prev_tail - lead)   # добавляем паузу между сценами
        prev_scene, prev_tail = scene, tail
        sf.write(os.path.join(project, "vo", l["id"] + ".wav"), clip, rate)
        d = spans[i][1] - spans[i][0]
        timings[l["id"]] = {"t": round(t + lead, 3), "d": round(d, 3), "text": l["text"]}
        files.append({"file": "vo/" + l["id"] + ".wav", "t": round(t, 3)})
        t += len(clip) / rate
    end = round(t + cfg.get("tail", 1.4), 2)
    with open(os.path.join(project, "vo.js"), "w", encoding="utf-8") as f:
        f.write("// Создано voice_from_take.py — не править руками.\nwindow.VO = " + json.dumps(timings, ensure_ascii=False) + ";\nwindow.VO_END = " + str(end) + ";\n")
    json.dump(files, open(os.path.join(project, "voice.json"), "w", encoding="utf-8"))
    for k, v in timings.items():
        print(k, v["t"], v["d"])
    print("длительность ролика:", end)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
