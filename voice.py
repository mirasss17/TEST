"""Озвучка: читает <папка>/vo.json (список фраз), синтезирует голос и раскладывает фразы по времени.
Пишет <папка>/vo/*.wav, <папка>/vo.js (тайминги для анимации) и <папка>/voice.json (для сведения в sfx.py).
Запуск: python3 voice.py <папка проекта>
Голос: Piper ru_RU-ruslan-medium, скачивается скриптом tools/get-voice.sh в .voices/.
"""
import hashlib
import json
import os
import subprocess
import sys
import numpy as np
import soundfile as sf
try:
    from piper import PiperVoice, SynthesisConfig
except ImportError:  # для ElevenLabs локальный движок не нужен
    PiperVoice = SynthesisConfig = None

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(ROOT, ".voices", "vits-piper-ru_RU-ruslan-medium")


def eleven(text, path, opt, prev_text, next_text):
    """Фраза через ElevenLabs. Ключ подставляет сетевой прокси среды, в коде его нет."""
    body = {
        "text": text,
        "model_id": opt.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": {"stability": opt.get("stability", 0.35), "similarity_boost": opt.get("similarity_boost", 0.8),
                           "style": opt.get("style", 0.45), "use_speaker_boost": True, "speed": opt.get("speed", 1.0)},
    }
    if prev_text:
        body["previous_text"] = prev_text   # соседние фразы — чтобы интонация была связной
    if next_text:
        body["next_text"] = next_text
    mp3 = path[:-4] + ".mp3"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{opt['voice_id']}?output_format=mp3_44100_128"
    code = subprocess.run(["curl", "-sS", "-m", "120", "-o", mp3, "-w", "%{http_code}", "-X", "POST", url,
                           "-H", "Content-Type: application/json", "-d", json.dumps(body)],
                          capture_output=True, text=True).stdout.strip()
    if code != "200":
        raise RuntimeError(f"ElevenLabs ответил {code}: " + open(mp3, encoding="utf-8", errors="replace").read()[:300])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "44100", path], check=True)
    os.remove(mp3)
    x, rate = sf.read(path, dtype="float32")
    return x, rate


def main(project):
    with open(os.path.join(project, "vo.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    engine = cfg.get("engine", "piper")
    if engine == "piper":
        voice = PiperVoice.load(os.path.join(MODEL, "ru_RU-ruslan-medium.onnx"))
        syn = SynthesisConfig(length_scale=1 / cfg.get("speed", 1.0))
    texts = [l["text"] for l in cfg["lines"]]
    os.makedirs(os.path.join(project, "vo"), exist_ok=True)
    t = cfg.get("start", 0.4)
    timings, files, prev_scene = {}, [], None
    for idx, line in enumerate(cfg["lines"]):
        scene = line["id"][0]
        if prev_scene is not None:
            t += cfg.get("scene_gap", 0.55) if scene != prev_scene else cfg.get("gap", 0.25)
        prev_scene = scene
        path = os.path.join(project, "vo", line["id"] + ".wav")
        if engine == "elevenlabs":
            opt = cfg["elevenlabs"]
            # Кэш: фразу не генерируем заново (и не тратим символы), пока не менялись текст и настройки.
            key = hashlib.sha1(json.dumps([line["text"], opt], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            stamp = path[:-4] + ".key"
            raw = path[:-4] + ".raw.wav"
            if os.path.exists(raw) and os.path.exists(stamp) and open(stamp).read() == key:
                x, rate = sf.read(raw, dtype="float32")
            else:
                x, rate = eleven(line["text"], raw, opt, " ".join(texts[max(0, idx - 2):idx]), " ".join(texts[idx + 1:idx + 2]))
                open(stamp, "w").write(key)
        else:
            chunks = list(voice.synthesize(line["text"], syn_config=syn))
            rate = chunks[0].sample_rate
            pause = np.zeros(int(rate * 0.12), dtype=np.float32)  # короткая пауза между предложениями
            parts = []
            for c in chunks:
                parts += [c.audio_float_array, pause]
            x = np.concatenate(parts[:-1]).astype(np.float32)
        loud = np.where(np.abs(x) > 0.01)[0]  # обрезаем тишину по краям
        x = x[max(0, loud[0] - int(rate * 0.02)): loud[-1] + int(rate * 0.06)]
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
