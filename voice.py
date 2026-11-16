"""Озвучка: читает <папка>/vo.json (список фраз), синтезирует голос и раскладывает фразы по времени.
Пишет <папка>/vo/*.wav, <папка>/vo.js (тайминги для анимации) и <папка>/voice.json (для сведения в sfx.py).
Запуск: python3 voice.py <папка проекта>
Голос: Piper ru_RU-ruslan-medium, скачивается скриптом tools/get-voice.sh в .voices/.
"""
import json
import os
import sys
import numpy as np
import soundfile as sf
from piper import PiperVoice, SynthesisConfig

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(ROOT, ".voices", "vits-piper-ru_RU-ruslan-medium")


def main(project):
    with open(os.path.join(project, "vo.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    voice = PiperVoice.load(os.path.join(MODEL, "ru_RU-ruslan-medium.onnx"))
    syn = SynthesisConfig(length_scale=1 / cfg.get("speed", 1.0))
    os.makedirs(os.path.join(project, "vo"), exist_ok=True)
    t = cfg.get("start", 0.4)
    timings, files, prev_scene = {}, [], None
    for line in cfg["lines"]:
        scene = line["id"][0]
        if prev_scene is not None:
            t += cfg.get("scene_gap", 0.55) if scene != prev_scene else cfg.get("gap", 0.25)
        prev_scene = scene
        chunks = list(voice.synthesize(line["text"], syn_config=syn))
        rate = chunks[0].sample_rate
        pause = np.zeros(int(rate * 0.12), dtype=np.float32)  # короткая пауза между предложениями
        parts = []
        for c in chunks:
            parts += [c.audio_float_array, pause]
        x = np.concatenate(parts[:-1]).astype(np.float32)
        loud = np.where(np.abs(x) > 0.01)[0]  # обрезаем тишину по краям
        x = x[max(0, loud[0] - 400): loud[-1] + 1200]
        path = os.path.join(project, "vo", line["id"] + ".wav")
        sf.write(path, x, rate)
        d = len(x) / rate
        timings[line["id"]] = {"t": round(t, 3), "d": round(d, 3), "text": line["text"]}
        files.append({"file": "vo/" + line["id"] + ".wav", "t": round(t, 3)})
        t += d
    end = round(t + cfg.get("tail", 1.6), 2)
    with open(os.path.join(project, "vo.js"), "w", encoding="utf-8") as f:
        f.write("// Создано voice.py — не править руками.\nwindow.VO = " + json.dumps(timings, ensure_ascii=False) + ";\nwindow.VO_END = " + str(end) + ";\n")
    with open(os.path.join(project, "voice.json"), "w", encoding="utf-8") as f:
        json.dump(files, f)
    print("длительность ролика:", end)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
