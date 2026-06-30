// Reusable visual juice. No dependencies. Functions are attached to window so
// app.js can call them via a typeof guard.
(function () {
  function layer() {
    return document.getElementById("fx-layer") || document.body;
  }

  function piece(x, y) {
    const el = document.createElement("span");
    el.className = "confetti-piece";
    const hue = Math.floor(Math.random() * 360);
    el.style.setProperty("--x", (Math.random() * 2 - 1).toFixed(2));
    el.style.setProperty("--r", Math.floor(Math.random() * 360) + "deg");
    el.style.setProperty("--d", (0.7 + Math.random() * 0.8).toFixed(2) + "s");
    el.style.left = x + "px";
    el.style.top = y + "px";
    el.style.background = `hsl(${hue} 90% 60%)`;
    return el;
  }

  function spawn(count, life, x, y) {
    const host = layer();
    for (let i = 0; i < count; i++) host.appendChild(piece(x, y));
    setTimeout(() => {
      host.querySelectorAll(".confetti-piece").forEach((p) => p.remove());
    }, life);
    return count;
  }

  function confetti(opts = {}) {
    const count = opts.count == null ? 24 : opts.count;
    const life = opts.life == null ? 1200 : opts.life;
    const w = window.innerWidth || 360;
    return spawn(count, life, w / 2, 40);
  }

  function burst(el, opts = {}) {
    if (!el) return 0;
    const count = opts.count == null ? 12 : opts.count;
    const life = opts.life == null ? 900 : opts.life;
    const r = el.getBoundingClientRect ? el.getBoundingClientRect() : { left: 0, top: 0, width: 0, height: 0 };
    return spawn(count, life, r.left + r.width / 2, r.top + r.height / 2);
  }

  function mentorSay(text, opts = {}) {
    const overlay = document.createElement("div");
    overlay.className = "mentor-overlay";
    overlay.innerHTML =
      '<div class="mentor-card"><div class="mentor-avatar">' + (typeof sprite === "function" ? sprite("owl") : "🦉") + '</div>' +
      '<div class="mentor-text"></div><button class="mentor-next">متابعة</button></div>';
    overlay.querySelector(".mentor-text").textContent = text;
    const close = () => {
      overlay.remove();
      if (typeof opts.onDone === "function") opts.onDone();
    };
    overlay.querySelector(".mentor-next").onclick = close;
    overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
    document.body.appendChild(overlay);
    return overlay;
  }

  function renderHUD(el, s) {
    s = s || {};
    el.innerHTML =
      `<span class="hud-avatar">${s.avatar || "🧑‍🎓"}</span>` +
      `<div class="hud-meta">` +
      `<div class="hud-line"><span class="hud-name">${s.name || "باحث"}</span>` +
      `<span class="hud-rank">${s.rank_ar || ""} · ★${s.level || 1}</span></div>` +
      `<div class="level-bar"><i style="width:${Math.round((s.progress || 0) * 100)}%"></i></div>` +
      `</div>`;
  }

  function levelUpOverlay(level, rank_ar) {
    const ov = document.createElement("div");
    ov.className = "levelup-overlay";
    ov.innerHTML =
      `<div class="levelup-card"><div class="levelup-emoji">${typeof sprite === "function" ? sprite("star") : "⭐"}</div>` +
      `<div class="levelup-title">المستوى ${level}!</div>` +
      `<div class="levelup-rank">${rank_ar || ""}</div>` +
      `<button class="levelup-next">رائع!</button></div>`;
    ov.querySelector(".levelup-next").onclick = () => ov.remove();
    document.body.appendChild(ov);
    if (typeof confetti === "function") confetti({ count: 40 });
    return ov;
  }

  function embers(opts = {}) {
    const host = document.getElementById("fx-layer") || document.body;
    host.querySelectorAll(".ember").forEach((e) => e.remove());
    const count = opts.count == null ? 14 : opts.count;
    const world = opts.world == null ? 0.5 : Math.max(0, Math.min(1, opts.world));
    const gold = Math.round(count * world); // how many Piltover motes
    for (let i = 0; i < count; i++) {
      const e = document.createElement("span");
      e.className = "ember " + (i < gold ? "ember-pilt" : "ember-zaun");
      e.style.left = Math.floor(Math.random() * 100) + "%";
      e.style.setProperty("--dur", (6 + Math.random() * 6).toFixed(1) + "s");
      e.style.setProperty("--delay", (-Math.random() * 8).toFixed(1) + "s");
      e.style.setProperty("--drift", (Math.random() * 2 - 1).toFixed(2));
      e.style.setProperty("--sz", (2 + Math.random() * 3).toFixed(1) + "px");
      host.appendChild(e);
    }
    return count;
  }

  window.confetti = confetti;
  window.burst = burst;
  window.mentorSay = mentorSay;
  window.renderHUD = renderHUD;
  window.levelUpOverlay = levelUpOverlay;
  window.embers = embers;
})();
