// Рендер HTML-анимации в MP4: кадр за кадром через Chromium, склейка в ffmpeg.
// Запуск: node render.js <папка проекта>
// Страница объявляет window.DURATION, window.FPS, window.seek(t), window.ready.
// Если есть window.CUES (ролики на lib/kit.js), звук собирается автоматически через sfx.py;
// иначе берётся готовый <папка>/sound.wav, если он есть.
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const path = require("path");
const fs = require("fs");

(async () => {
  const name = process.argv[2];
  if (!name) throw new Error("Укажите папку проекта: node render.js kazpost-01");
  const dir = path.resolve(__dirname, name);
  const audio = path.join(dir, "sound.wav");
  const outDir = path.join(__dirname, "out");
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, `${path.basename(dir)}.mp4`);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => console.error("ошибка на странице:", e.message));
  await page.goto("file://" + path.join(dir, "index.html"));
  await page.evaluate(() => window.ready);
  const { duration, fps, cues } = await page.evaluate(() => ({ duration: window.DURATION, fps: window.FPS, cues: window.CUES || null }));
  const frames = Math.round(duration * fps);

  if (cues) {
    fs.writeFileSync(path.join(dir, "cues.json"), JSON.stringify({ duration, cues }));
    execFileSync("python3", [path.join(__dirname, "sfx.py"), dir], { stdio: "inherit" });
  }

  const hasAudio = fs.existsSync(audio);
  const args = ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-i", "-"];
  if (hasAudio) args.push("-i", audio);
  args.push("-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium", "-r", String(fps));
  if (hasAudio) args.push("-c:a", "aac", "-b:a", "192k", "-shortest");
  args.push("-movflags", "+faststart", out);
  const ff = spawn("ffmpeg", args, { stdio: ["pipe", "ignore", "inherit"] });
  const done = new Promise((res, rej) => ff.on("close", (code) => (code === 0 ? res() : rej(new Error("ffmpeg: код " + code)))));

  for (let i = 0; i < frames; i++) {
    await page.evaluate((t) => window.seek(t), i / fps);
    const buf = await page.screenshot({ type: "png" });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (i % 150 === 0) console.log(`кадр ${i}/${frames}`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log(`готово: ${out} (${frames} кадров, звук: ${hasAudio ? "да" : "нет"})`);
})().catch((e) => { console.error(e); process.exit(1); });
