// Рендер HTML-анимации в MP4: кадр за кадром через Chromium, склейка в ffmpeg.
// Запуск: node render.js demo-01 [звук.wav]
// Страница должна объявить window.DURATION, window.FPS, window.seek(t) и window.ready.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

(async () => {
  const name = process.argv[2];
  if (!name) throw new Error("Укажите папку проекта: node render.js demo-01");
  const dir = path.resolve(__dirname, name);
  const audio = process.argv[3] ? path.resolve(process.argv[3]) : path.join(dir, "sound.wav");
  const outDir = path.join(__dirname, "out");
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, `${name}.mp4`);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.join(dir, "index.html"));
  await page.evaluate(() => window.ready);
  const { duration, fps } = await page.evaluate(() => ({ duration: window.DURATION, fps: window.FPS }));
  const frames = Math.round(duration * fps);

  const args = ["-y", "-f", "image2pipe", "-framerate", String(fps), "-i", "-"];
  const hasAudio = fs.existsSync(audio);
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
    if (i % 60 === 0) console.log(`кадр ${i}/${frames}`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log(`готово: ${out} (${frames} кадров, звук: ${hasAudio ? "да" : "нет"})`);
})().catch((e) => { console.error(e); process.exit(1); });
