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

  window.confetti = confetti;
  window.burst = burst;
})();
