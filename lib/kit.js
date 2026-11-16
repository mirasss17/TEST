// Общий набор приёмов для роликов. Каждый приём ставит и анимацию, и звуковую метку,
// поэтому звук всегда совпадает с движением: sfx.py собирает дорожку из window.CUES.
(function () {
  const tl = gsap.timeline({ paused: true });
  const CUES = [];
  const cue = (type, t, o = {}) => CUES.push({ type, t: Math.max(0, +t.toFixed(3)), ...o });
  const count = (sel) => (typeof sel === "string" ? document.querySelectorAll(sel).length : sel.length ?? 1);
  const fmt = (n) => Math.round(n).toLocaleString("ru-RU").replace(/ /g, " ");

  const ICONS = {
    box: '<path d="M8 22 L32 10 L56 22 L56 46 L32 58 L8 46 Z M8 22 L32 34 L56 22 M32 34 L32 58"/>',
    mail: '<rect x="8" y="14" width="48" height="36" rx="6"/><path d="M10 18 L32 36 L54 18"/>',
    money: '<rect x="6" y="16" width="52" height="32" rx="6"/><circle cx="32" cy="32" r="8"/>',
    news: '<rect x="10" y="10" width="44" height="44" rx="6"/><path d="M20 22 H44 M20 32 H44 M20 42 H34"/>',
    home: '<path d="M8 30 L32 10 L56 30 M15 25 V54 H49 V25 M27 54 V40 H37 V54"/>',
    people: '<circle cx="24" cy="22" r="9"/><path d="M8 54 C8 40 40 40 40 54"/><circle cx="46" cy="26" r="7"/><path d="M46 40 C54 40 58 46 58 54"/>',
    pin: '<path d="M32 58 C18 40 14 34 14 26 A18 18 0 0 1 50 26 C50 34 46 40 32 58 Z"/><circle cx="32" cy="26" r="6"/>',
  };
  document.querySelectorAll("[data-icon]").forEach((el) => {
    el.innerHTML = `<svg viewBox="0 0 64 64">${ICONS[el.dataset.icon]}</svg>`;
  });

  const K = {
    tl, cue, fmt,
    /** Показать сцену в момент at. */
    scene(id, at) { tl.set(id, { autoAlpha: 1 }, at); },
    /** Текст выезжает снизу с отскоком. */
    up(sel, at, o = {}) {
      tl.from(sel, { y: o.y ?? 70, opacity: 0, duration: 0.55, ease: "back.out(1.5)", stagger: o.stagger ?? 0.14 }, at);
      for (let i = 0; i < count(sel); i++) cue("whoosh", at + i * (o.stagger ?? 0.14), { gain: 0.26, pan: -0.3 + 0.3 * i });
    },
    /** Плашка или кнопка «выпрыгивает». */
    pop(sel, at, o = {}) {
      tl.from(sel, { scale: 0.7, opacity: 0, duration: 0.5, ease: "back.out(2)", stagger: o.stagger ?? 0.1 }, at);
      for (let i = 0; i < count(sel); i++) cue("pop", at + i * (o.stagger ?? 0.1), { gain: 0.42, pitch: 1 + i * 0.14 });
    },
    /** Карточка поднимается снизу. */
    card(sel, at, o = {}) {
      tl.from(sel, { y: 110, opacity: 0, scale: 0.93, duration: 0.58, ease: "back.out(1.5)", stagger: o.stagger ?? 0.25 }, at);
      for (let i = 0; i < count(sel); i++) cue("pop", at + i * (o.stagger ?? 0.25), { gain: 0.5, pitch: 0.75 + i * 0.1 });
    },
    /** Счётчик: число набегает от from до to, в конце звоночек. */
    count(sel, to, at, dur, o = {}) {
      const el = document.querySelector(sel), v = { v: o.from ?? 0 };
      const show = o.show ?? ((n) => (o.prefix ?? "") + fmt(n) + (o.suffix ?? ""));
      el.textContent = show(v.v);
      tl.to(v, { v: to, duration: dur, ease: o.ease ?? "power2.out", onUpdate: () => { el.textContent = show(v.v); } }, at);
      cue("ticks", at, { dur: dur * 0.9, n: Math.round(dur * 14), gain: 0.11 });
      cue("ding", at + dur, { f: o.f ?? 1046.5, gain: 0.26 });
      tl.to(sel, { scale: 1.06, transformOrigin: o.origin ?? "left center", duration: 0.15, ease: "power2.out", yoyo: true, repeat: 1 }, at + dur);
    },
    /** Сцена уезжает вверх. */
    out(id, at) {
      tl.to(id, { y: -90, opacity: 0, duration: 0.3, ease: "power2.in" }, at);
      tl.set(id, { autoAlpha: 0 }, at + 0.31);
      cue("whoosh_out", at - 0.02, { gain: 0.36 });
    },
    /** Закончить сборку: длительность ролика в секундах. */
    done(duration) {
      tl.fromTo("#glow", { scale: 0.9, x: -60 }, { scale: 1.15, x: 80, duration, ease: "sine.inOut" }, 0);
      tl.to({}, { duration: 0.01 }, duration - 0.01);
      window.DURATION = duration;
      window.CUES = CUES;
      window.seek = (t) => { tl.time(t); };
      window.ready = document.fonts.ready.then(() => { tl.time(0); return true; });
      if (!navigator.webdriver) tl.play();
    },
  };
  window.FPS = 30;
  window.K = K;
})();
