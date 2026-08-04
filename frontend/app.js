// رحلة الباحث — The Researcher's Journey
// Copyright (C) 2026 Boundless Academic Services, the Scientific Research Camp
// initiative, and Mulham Fetna.
// Licensed under AGPL-3.0-or-later. See LICENSE and NOTICE.
const tg = window.Telegram ? window.Telegram.WebApp : { initData: "", ready() {}, expand() {} };
tg.ready(); tg.expand();

const screens = ["home", "runner", "report", "board", "badges", "funfact", "progress", "onboarding", "report-issue", "duel", "about"];
function show(name) {
  screens.forEach(s => document.getElementById("screen-" + s).classList.toggle("hidden", s !== name));
  if (document.body) document.body.dataset.screen = name;
}

const BADGES = {
  perfect_capstone: { ico: "perfect_capstone", name_ar: "رحلة مثالية" },
  senior_researcher: { ico: "senior_researcher", name_ar: "كبير باحثي بيلتوفر" },
  all_stations: { ico: "all_stations", name_ar: "جوّاب المحطات" },
  flawless: { ico: "flawless", name_ar: "أداء لا يُخطئ" },
  streak_10: { ico: "streak_10", name_ar: "سلسلة العشرة" },
  perfect_quiz: { ico: "perfect_quiz", name_ar: "الإتقان" },
  streak_master: { ico: "streak_master", name_ar: "السلسلة" },
  dedicated: { ico: "dedicated", name_ar: "المثابر" },
  self_reliant: { ico: "self_reliant", name_ar: "بلا تلميحات" },
  first_finish: { ico: "first_finish", name_ar: "البداية" },
};
const BADGE_ORDER = ["perfect_capstone", "senior_researcher", "all_stations", "flawless", "streak_10", "perfect_quiz", "streak_master", "dedicated", "self_reliant", "first_finish"];

// Copyright attribution (issue #18). AGPL-3.0 expects the notice to reach the
// people RUNNING the program, not only those reading the repository — hence the
// home footer, the onboarding screen, the About screen and the shared cards.
// Single source of truth: change a name here and it changes everywhere.
const CREDITS = {
  year: "2026",
  author: "Mulham Fetna",
  orgs_ar: ["باوندلس للخدمات الأكاديمية", "معسكر البحث العلمي"],
  orgs_en: ["Boundless Academic Services", "Scientific Research Camp initiative"],
  licence: "AGPL-3.0-or-later",
  repo: "https://github.com/mulhamfetna/boundless-src-researcher-journey-game",
};
CREDITS.line_ar = "© " + CREDITS.year + " " + CREDITS.orgs_ar.join(" و");
CREDITS.line_full_ar = CREDITS.line_ar + " — جميع الحقوق محفوظة";

function renderCredits() {
  [document.getElementById("credits"), document.getElementById("ob-credits")]
    .filter(Boolean)
    .forEach((el) => { el.textContent = CREDITS.line_ar; });
}

function showAbout() {
  const body = document.getElementById("about-body");
  if (body) {
    body.innerHTML =
      '<p class="about-lead">رحلة الباحث — لعبة تعليمية لمنهجية البحث العلمي.</p>' +
      '<h3>حقوق النشر</h3>' +
      '<p>' + CREDITS.line_full_ar + '</p>' +
      '<ul class="about-list">' +
        CREDITS.orgs_ar.map((o, i) => '<li>' + o + ' <span class="en">' + CREDITS.orgs_en[i] + '</span></li>').join("") +
        '<li>' + CREDITS.author + '</li>' +
      '</ul>' +
      '<h3>الرخصة</h3>' +
      '<p>هذا البرنامج حر ومفتوح المصدر بموجب رخصة <span dir="ltr">' + CREDITS.licence + '</span>. ' +
      'يحق لك دراسته وتعديله وإعادة توزيعه، وإذا شغّلت نسخة معدّلة كخدمة عبر الشبكة فيجب إتاحة مصدرها لمستخدميها.</p>' +
      '<p class="about-link">' + CREDITS.repo + '</p>';
  }
  const back = document.getElementById("about-back");
  if (back) back.onclick = loadHome;
  show("about");
}

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts);
  if (!res.ok) throw new Error("api " + res.status);
  return res.json();
}

let state = { slug: null, questions: [], funFacts: [], idx: 0, answers: [], curRetries: 0, curHint: false };
let currentXp = 0;

const AVATARS = (typeof AVATAR_SPRITES !== "undefined") ? AVATAR_SPRITES : ["tinkerer", "brawler", "sniper"];
function spr(name) { return (typeof sprite === "function") ? sprite(name) : ""; }
function avatarSprite(id) {
  const eff = (typeof AVATAR_SPRITES !== "undefined" && AVATAR_SPRITES.includes(id)) ? id : "tinkerer";
  const art = (typeof champArt === "function") ? champArt(eff) : null;
  return art || spr(eff);
}
function stageSprite(slug) { return spr((typeof STAGE_SPRITES !== "undefined" && STAGE_SPRITES[slug]) || "book"); }

async function loadHome() {
  // Deep-link: opening the app via a duel challenge link (?startapp=duel_<token>).
  const sp = (window.Telegram && Telegram.WebApp && Telegram.WebApp.initDataUnsafe && Telegram.WebApp.initDataUnsafe.start_param) || "";
  if (sp.indexOf("duel_") === 0 && !window.__duelStarted) { window.__duelStarted = true; return startDuelAnswer(sp.slice(5)); }
  const profile = await loadProfile();
  if (!profile.onboarded) return showOnboarding();
  return renderMap(profile);
}

async function renderMap(profile) {
  let quizzes = [];
  let dashboard = null;
  try { quizzes = await api("/quizzes"); } catch (_) {}
  try { dashboard = await api("/me/dashboard", { headers: { "X-Init-Data": tg.initData } }); } catch (_) {}

  currentXp = (dashboard && dashboard.stats && dashboard.stats.total_points) || 0;
  if (typeof levelFromXp === "function" && typeof worldFromLevel === "function") {
    const w = worldFromLevel(levelFromXp(currentXp).level);
    document.documentElement.style.setProperty("--world", String(w));
  }
  const hud = document.getElementById("map-hud");
  if (typeof renderHUD === "function" && typeof levelFromXp === "function") {
    const lv = levelFromXp(currentXp);
    renderHUD(hud, { avatar: avatarSprite(profile.avatar), name: profile.name, rank_ar: lv.rank_ar, level: lv.level, progress: lv.progress });
    const av = hud.querySelector(".hud-avatar");
    if (av) av.onclick = () => openAvatarPicker(profile);
  } else {
    hud.innerHTML = `<span class="hud-avatar">${avatarSprite(profile.avatar)}</span><span class="hud-name">${profile.name || "باحث"}</span>`;
  }

  const path = document.getElementById("map-path");
  path.innerHTML = "";
  mapState(quizzes, dashboard).forEach((s) => {
    const node = document.createElement("div");
    node.className = "map-node " + s.status;
    const mark = s.status === "done" ? spr("check") : (s.status === "next" ? spr("star") : "");
    node.innerHTML =
      `<span class="node-emoji">${stageSprite(s.slug)}</span>` +
      `<span class="node-title">${s.title_ar}</span>` +
      `<span class="node-mark">${mark}</span>` +
      `<span class="node-num">${s.index + 1}</span>` +
      (s.status === "next" ? `<span class="node-here">${avatarSprite(profile.avatar)}</span>` : "");
    node.onclick = () => enterStage(s.slug, profile);
    path.appendChild(node);
  });

  document.getElementById("btn-my-badges").onclick = loadBadges;
  document.getElementById("btn-my-progress").onclick = loadDashboard;
  document.getElementById("btn-report").onclick = showReport;
  const ab = document.getElementById("btn-about");
  if (ab) ab.onclick = showAbout;
  renderCredits();
  const rv = document.getElementById("btn-review");
  if (rv) rv.onclick = startReview;
  if (typeof embers === "function") {
    const w = (typeof levelFromXp === "function" && typeof worldFromLevel === "function")
      ? worldFromLevel(levelFromXp(currentXp).level) : 0.4;
    const n = (typeof emberCountForWorld === "function") ? emberCountForWorld(w) : 14;
    embers({ world: w, count: n });
  }
  show("home");
}

function showReport() {
  const status = document.getElementById("report-status");
  status.textContent = "";
  const ta = document.getElementById("report-text");
  ta.value = "";
  document.getElementById("report-send").onclick = async () => {
    const text = (ta.value || "").trim();
    if (!text) { status.textContent = "اكتب رسالتك أولاً."; return; }
    try {
      await api("/report", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData },
        body: JSON.stringify({ text, platform: tg.platform, version: tg.version }),
      });
      status.textContent = "✅ تم الإرسال، شكراً لك!";
      ta.value = "";
    } catch (e) {
      status.textContent = "تعذّر الإرسال، حاول لاحقاً.";
    }
  };
  document.getElementById("report-back").onclick = loadHome;
  show("report-issue");
}

function enterStage(slug, profile) {
  const line = mentorLineFor("stage:" + slug, { name: profile.name });
  if (typeof mentorSay === "function") mentorSay(line, { onDone: () => startQuiz(slug) });
  else startQuiz(slug);
}

function showOnboarding() {
  const mentor = document.getElementById("ob-mentor");
  mentor.innerHTML =
    `<div class="mentor-card"><div class="mentor-avatar">${avatarSprite("tinkerer")}</div>` +
    `<div class="mentor-text">${mentorLineFor("welcome_anon", {})}</div></div>`;

  let chosen = AVATARS[0];
  const grid = document.getElementById("ob-avatars");
  grid.innerHTML = "";
  AVATARS.forEach((a, i) => {
    const b = document.createElement("span");
    b.className = "ob-avatar" + (i === 0 ? " selected" : "");
    b.innerHTML = avatarSprite(a);
    b.onclick = () => {
      chosen = a;
      grid.querySelectorAll(".ob-avatar").forEach((x) => x.classList.remove("selected"));
      b.classList.add("selected");
    };
    grid.appendChild(b);
  });

  document.getElementById("ob-start").onclick = async () => {
    const name = (document.getElementById("ob-name").value || "").trim() || "باحث";
    await saveProfile({ name, avatar: chosen, onboarded: true });
    loadHome();
  };
  renderCredits();
  show("onboarding");
}

function openAvatarPicker(profile) {
  const ov = document.createElement("div");
  ov.className = "mentor-overlay";
  ov.innerHTML = `<div class="mentor-card"><div class="mentor-text">اختر رمزك</div><div class="ob-avatars"></div></div>`;
  const grid = ov.querySelector(".ob-avatars");
  AVATARS.forEach((a) => {
    const b = document.createElement("span");
    b.className = "ob-avatar" + (a === profile.avatar ? " selected" : "");
    b.innerHTML = avatarSprite(a);
    b.onclick = async () => {
      profile.avatar = a;
      await saveProfile({ avatar: a });
      ov.remove();
      renderMap(profile);
    };
    grid.appendChild(b);
  });
  ov.addEventListener("click", (e) => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function startReview() {
  let deck;
  try { deck = await api("/me/review", { headers: { "X-Init-Data": tg.initData } }); }
  catch (e) { deck = { questions: [] }; }
  if (!deck.questions || !deck.questions.length) {
    if (window.Telegram && Telegram.WebApp && Telegram.WebApp.showAlert) Telegram.WebApp.showAlert("لا توجد مفاهيم للمراجعة الآن.");
    return;
  }
  state = { slug: "__review__", questions: deck.questions, bossId: null, funFacts: [],
            idx: 0, answers: [], curRetries: 0, curHint: false, practice: true, startedAt: Date.now() };
  renderQuestion();
}

function practiceDone() {
  document.getElementById("funfact-text").textContent =
    `أحسنت! راجعتَ ${state.questions.length} مفاهيم من نقاط ضعفك 🧠 عُد لاحقًا لمراجعة جديدة.`;
  document.getElementById("funfact-continue").onclick = loadHome;
  show("funfact");
}

// ---- Peer-Review Duel (timed one-shot challenge) ----
let _duelTimer = null, _duelStart = 0;

function pickDuelQuestion() {
  const single = (state.questions || []).filter((q) => ["mcq", "tf", "image"].includes(q.type));
  return single.length ? single[Math.floor(Math.random() * single.length)] : null;
}

function startDuelChallenge() {
  const q = pickDuelQuestion();
  if (q) playDuel(q, { mode: "create" });
}

async function startDuelAnswer(token) {
  let duel;
  try { duel = await api(`/duels/${token}`); } catch (e) { return loadHome(); }
  if (!duel || duel.status !== "open") {
    if (window.Telegram && Telegram.WebApp && Telegram.WebApp.showAlert) Telegram.WebApp.showAlert("انتهت هذه المبارزة.");
    window.__duelStarted = false;
    return loadHome();
  }
  playDuel(duel.question, { mode: "answer", token, creator: duel.creator });
}

function playDuel(q, ctx) {
  show("duel");
  document.getElementById("duel-result").innerHTML = "";
  document.getElementById("duel-home").classList.add("hidden");
  document.getElementById("duel-home").onclick = () => { window.__duelStarted = false; loadHome(); };
  document.getElementById("duel-prompt").textContent = q.prompt_ar;
  const img = document.getElementById("duel-image");
  if (q.asset_file) { img.src = "/content/" + q.asset_file; img.classList.remove("hidden"); }
  else { img.classList.add("hidden"); img.removeAttribute("src"); }
  const intro = (ctx.mode === "answer" && ctx.creator) ? `⚔️ ${ctx.creator.name} تحدّاك! أجب بسرعة ودقّة.` : "⚔️ أجب بسرعة ودقّة ثم تحدَّ زميلك.";
  const opts = document.getElementById("duel-options");
  opts.innerHTML = `<div class="duel-intro">${intro}</div>`;
  q.options_ar.forEach((text, i) => {
    const b = document.createElement("button");
    b.className = "opt"; b.textContent = text;
    b.onclick = () => finishDuel(q, i, ctx, opts);
    opts.appendChild(b);
  });
  _duelStart = Date.now();
  const t = document.getElementById("duel-timer");
  clearInterval(_duelTimer);
  _duelTimer = setInterval(() => { t.textContent = ((Date.now() - _duelStart) / 1000).toFixed(1) + "s"; }, 100);
}

async function finishDuel(q, index, ctx, opts) {
  clearInterval(_duelTimer);
  const time_ms = Date.now() - _duelStart;
  const correct = index === q.correct_index;
  [...opts.querySelectorAll(".opt")].forEach((b, i) => {
    b.disabled = true;
    if (i === q.correct_index) b.classList.add("correct"); else if (i === index) b.classList.add("wrong");
  });
  const res = document.getElementById("duel-result");
  const secs = (time_ms / 1000).toFixed(1);
  try {
    if (ctx.mode === "create") {
      const out = await api("/duels", { method: "POST", headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData }, body: JSON.stringify({ question_id: q.id, correct, time_ms }) });
      res.innerHTML = `<div>${correct ? "✅ صحيح" : "❌ خطأ"} في ${secs} ثانية</div><button id="duel-share" class="quiz-card">📤 تحدَّ زميلك</button>`;
      document.getElementById("duel-share").onclick = () => shareDuel(out.link);
    } else {
      const out = await api(`/duels/${ctx.token}/answer`, { method: "POST", headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData }, body: JSON.stringify({ correct, time_ms }) });
      const w = out.winner === "tie" ? "تعادل! 🤝" : `الفائز: ${out.winner === "creator" ? out.creator.name : out.opponent.name} 🏆`;
      res.innerHTML = `<div class="duel-winner">${w}</div>` +
        `<div>${out.creator.name}: ${out.creator.correct ? "✅" : "❌"} ${(out.creator.time_ms / 1000).toFixed(1)}s</div>` +
        `<div>${out.opponent.name}: ${out.opponent.correct ? "✅" : "❌"} ${(out.opponent.time_ms / 1000).toFixed(1)}s</div>`;
      if (typeof confetti === "function" && out.winner !== "tie") confetti();
    }
  } catch (e) { res.textContent = "تعذّرت العملية، حاول لاحقًا."; }
  document.getElementById("duel-home").classList.remove("hidden");
}

function shareDuel(link) {
  const text = "هل تتفوّق عليّ في هذه المبارزة العلمية؟ ⚔️";
  const shareUrl = "https://t.me/share/url?url=" + encodeURIComponent(link) + "&text=" + encodeURIComponent(text);
  if (window.Telegram && Telegram.WebApp && typeof Telegram.WebApp.openTelegramLink === "function") {
    Telegram.WebApp.openTelegramLink(shareUrl);
  } else if (navigator.share) {
    navigator.share({ title: "رحلة الباحث", text, url: link }).catch(() => {});
  } else {
    document.getElementById("duel-result").innerHTML += `<div class="duel-link" dir="ltr">${link}</div>`;
  }
}

async function startQuiz(slug) {
  const data = await api(`/quizzes/${slug}/questions`);
  const picked = (typeof pickBoss === "function") ? pickBoss(data.questions) : { bossId: null, ordered: data.questions };
  state = { slug, questions: picked.ordered, bossId: picked.bossId, funFacts: data.fun_facts_ar || [], idx: 0, answers: [], startedAt: Date.now() };
  renderQuestion();
  show("runner");
}

// --- generic pointer drag: returns the element under the pointer matching selector ---
function elementUnder(x, y, selector) {
  const el = document.elementFromPoint(x, y);
  return el ? el.closest(selector) : null;
}

// Shrink text until it fits its box, instead of letting the page grow past the
// screen. Game UIs scale text to the frame; documents grow and scroll. Question
// content is never changed — only how large it is drawn.
// `measure` is injectable because jsdom has no layout engine.
function fitToBox(el, opts) {
  const measure = (opts && opts.measure) ||
    ((e) => ({ content: e.scrollHeight, box: e.clientHeight }));
  const sizes = [16, 15, 14, 13, 12];
  for (const size of sizes) {
    el.style.fontSize = size + "px";
    const m = measure(el);
    if (m.content <= m.box) return size;
  }
  return sizes[sizes.length - 1];
}

// Scale the interaction to the play area after it renders, so a long question
// shrinks its text rather than pushing the page taller. Runs twice: once after
// layout settles, once on resize (the Telegram viewport changes when the
// keyboard or the header collapses).
function fitPlayArea() {
  const opts = document.getElementById("q-options");
  if (!opts) return;
  const run = () => fitToBox(opts);
  run();
  if (typeof window.requestAnimationFrame === "function") window.requestAnimationFrame(run);
  if (!window.__fitBound) {
    window.__fitBound = true;
    window.addEventListener("resize", () => {
      const el = document.getElementById("q-options");
      if (el && el.querySelector(".match-wrap, .order-list")) fitToBox(el);
    });
  }
}

// A one-line rule so the interaction is discoverable without a tutorial.
function playHint(text) {
  const el = document.createElement("div");
  el.className = "play-hint";
  el.textContent = text;
  return el;
}

// Tap is the primary interaction (issue #15): a learner selects a chip, then
// taps its slot. Distance stops mattering, so a slot below the fold is fine.
// Dragging is kept for mouse users, where it is reliable.
function renderMatch(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "match-wrap";
  const list = document.createElement("div");
  list.className = "match-list";
  const tray = document.createElement("div");
  tray.className = "chip-tray";
  wrap.append(playHint("اختر إجابة ثم اضغط مكانها"), list, tray);
  opts.appendChild(wrap);

  let selected = null;
  const select = (chip) => {
    if (selected) selected.classList.remove("selected");
    selected = chip;
    if (chip) chip.classList.add("selected");
  };
  const syncRow = (slot) => {
    const row = slot.closest(".match-row");
    if (row) row.classList.toggle("linked", !!slot.querySelector(".chip"));
  };

  q.left_ar.forEach((text, li) => {
    const row = document.createElement("div");
    row.className = "match-row";
    const label = document.createElement("div");
    label.className = "match-label";
    label.textContent = text;
    const slot = document.createElement("div");
    slot.className = "slot";
    slot.dataset.left = li;
    slot.addEventListener("click", () => {
      const existing = slot.querySelector(".chip");
      if (existing) {
        // Tapping a filled slot picks the chip back up, so a mistake is one tap to undo.
        tray.appendChild(existing);
        select(existing);
      } else if (selected) {
        const from = selected.parentElement;
        slot.appendChild(selected);
        select(null);
        if (from && from.classList.contains("slot")) syncRow(from);
      }
      syncRow(slot);
    });
    row.append(label, slot);
    list.appendChild(row);
  });

  const order = q.right_ar.map((_, i) => i).sort(() => Math.random() - 0.5);
  order.forEach((ri) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = q.right_ar[ri];
    chip.dataset.right = ri;
    tray.appendChild(chip);
    chip.addEventListener("click", () => {
      if (chip._dragged) { chip._dragged = false; return; }  // the tail of a mouse drag
      select(selected === chip ? null : chip);
    });
    makeChipDraggable(chip, tray);
  });

  ensureSubmitButton(() => {
    const pairs = [];
    document.querySelectorAll(".slot").forEach((slot) => {
      const chip = slot.querySelector(".chip");
      if (chip) pairs.push([Number(slot.dataset.left), Number(chip.dataset.right)]);
    });
    checkComplex({ pairs });
  });
}

function makeChipDraggable(chip, home) {
  chip.addEventListener("pointerdown", (e) => {
    // Touch belongs to tapping and scrolling — a finger cannot own both a drag
    // and a scroll. Mouse keeps the drag, which is where it works well.
    if (e.pointerType && e.pointerType !== "mouse") return;
    e.preventDefault();
    chip._dragged = false;
    chip.setPointerCapture(e.pointerId);
    chip.classList.add("dragging");
    const move = (ev) => {
      chip._dragged = true;
      chip.style.position = "fixed";
      chip.style.left = ev.clientX - 30 + "px";
      chip.style.top = ev.clientY - 20 + "px";
      chip.style.zIndex = 1000;
    };
    const cancel = () => {
      chip.classList.remove("dragging");
      chip.style.position = "";
      chip.style.left = chip.style.top = chip.style.zIndex = "";
      home.appendChild(chip);
      chip.removeEventListener("pointermove", move);
      chip.removeEventListener("pointerup", up);
      chip.removeEventListener("pointercancel", cancel);
    };
    const up = (ev) => {
      chip.releasePointerCapture(e.pointerId);
      chip.classList.remove("dragging");
      chip.style.position = "";
      chip.style.left = chip.style.top = chip.style.zIndex = "";
      const slot = elementUnder(ev.clientX, ev.clientY, ".slot");
      if (slot) {
        const existing = slot.querySelector(".chip");
        if (existing) home.appendChild(existing);
        slot.appendChild(chip);
      } else {
        home.appendChild(chip);
      }
      chip.removeEventListener("pointermove", move);
      chip.removeEventListener("pointerup", up);
      chip.removeEventListener("pointercancel", cancel);
    };
    chip.addEventListener("pointermove", move);
    chip.addEventListener("pointerup", up);
    chip.addEventListener("pointercancel", cancel);
  });
}

// Renumber the picked rows 1..n after any pick or un-pick.
function renumberPicks(list) {
  const picked = [...list.querySelectorAll(".order-row.picked")]
    .sort((a, b) => Number(a.dataset.pickedAt) - Number(b.dataset.pickedAt));
  picked.forEach((row, i) => {
    row.dataset.seq = String(i + 1);
    const badge = row.querySelector(".seq-badge");
    if (badge) badge.textContent = String(i + 1);
  });
}

// The answer is whatever the learner tapped, in tap order. With no taps at all
// we fall back to on-screen order, so mouse dragging still works unchanged.
function readOrderSequence() {
  const list = document.querySelector(".order-list");
  if (!list) return [];
  const picked = [...list.querySelectorAll(".order-row.picked")]
    .sort((a, b) => Number(a.dataset.seq) - Number(b.dataset.seq));
  const rows = picked.length ? picked : [...list.querySelectorAll(".order-row")];
  return rows.map((r) => Number(r.dataset.orig));
}

// Tap the items in the order you believe is right; each one takes the next
// number. No reordering, so nothing has to travel across a scrolling page.
function renderOrder(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  opts.appendChild(playHint("اضغط العناصر بالترتيب الصحيح"));
  const list = document.createElement("div");
  list.className = "order-list";
  opts.appendChild(list);
  let pickCounter = 0;
  const order = q.items_ar.map((_, i) => i).sort(() => Math.random() - 0.5);
  order.forEach((oi) => {
    const row = document.createElement("div");
    row.className = "order-row";
    row.dataset.orig = oi;
    row.innerHTML =
      `<span class="seq-badge"></span><span class="order-text">${q.items_ar[oi]}</span>` +
      `<span class="handle">≡</span>`;
    row.addEventListener("click", () => {
      if (row._dragged) { row._dragged = false; return; }  // the tail of a mouse drag
      if (row.classList.contains("picked")) {
        row.classList.remove("picked");
        delete row.dataset.seq;
        delete row.dataset.pickedAt;
        row.querySelector(".seq-badge").textContent = "";
      } else {
        row.classList.add("picked");
        row.dataset.pickedAt = String(++pickCounter);
      }
      renumberPicks(list);
    });
    list.appendChild(row);
    makeRowReorderable(row, list);
  });
  ensureSubmitButton(() => checkComplex({ sequence: readOrderSequence() }));
}

function makeRowReorderable(row, list) {
  row.addEventListener("pointerdown", (e) => {
    if (e.pointerType && e.pointerType !== "mouse") return;
    e.preventDefault();
    row._dragged = false;
    // Capture on the STABLE list, not the row: reordering moves `row` in the DOM
    // every step, and a captured element that moves fires lostpointercapture in
    // Chrome — which silently kills the drag after one step. The list never moves.
    list.setPointerCapture(e.pointerId);
    row.classList.add("dragging");
    const move = (ev) => {
      const over = elementUnder(ev.clientX, ev.clientY, ".order-row");
      if (over && over !== row) {
        row._dragged = true;
        const rect = over.getBoundingClientRect();
        const before = ev.clientY < rect.top + rect.height / 2;
        list.insertBefore(row, before ? over : over.nextSibling);
      }
    };
    const end = () => {
      row.classList.remove("dragging");
      list.removeEventListener("pointermove", move);
      list.removeEventListener("pointerup", end);
      list.removeEventListener("pointercancel", end);
      try { list.releasePointerCapture(e.pointerId); } catch (_) {}
    };
    list.addEventListener("pointermove", move);
    list.addEventListener("pointerup", end);
    list.addEventListener("pointercancel", end);
  });
}

function ensureSubmitButton(onSubmit) {
  const opts = document.getElementById("q-options");
  const btn = document.createElement("button");
  btn.className = "runner-submit";
  btn.textContent = "تأكيد";
  btn.onclick = () => onSubmit();
  opts.appendChild(btn);
}

function checkComplex(givenExtra) {
  const q = state.questions[state.idx];
  let correct;
  if (q.type === "order") {
    const seq = givenExtra.sequence;
    correct = q.correct_sequence.every((v, i) => seq[i] === v);
    if (!correct) {
      state.curRetries += 1;
      // Mark by the position the learner CHOSE (its tap number), not by where
      // the row happens to sit in the DOM. Since tap-in-sequence the two are
      // unrelated, and marking DOM order produced meaningless colours (#25).
      // Untapped rows stay unmarked — the learner never placed them.
      [...document.querySelectorAll(".order-row")].forEach((r) => {
        const seq = Number(r.dataset.seq);          // 1-based, NaN when untapped
        if (!seq) { r.classList.remove("wrong", "correct"); return; }
        const isCorrect = Number(r.dataset.orig) === q.correct_sequence[seq - 1];
        r.classList.toggle("wrong", !isCorrect);
        r.classList.toggle("correct", isCorrect);
      });
      return;
    }
  } else { // match
    const want = new Set(q.correct_pairs.map(p => p.join(",")));
    const have = givenExtra.pairs;
    correct = have.length === want.size && have.every(p => want.has(p.join(",")));
    if (!correct) {
      state.curRetries += 1;
      document.querySelectorAll(".slot").forEach(slot => {
        const chip = slot.querySelector(".chip");
        const ok = chip && want.has([slot.dataset.left, chip.dataset.right].join(","));
        slot.classList.toggle("wrong", !ok);
        slot.classList.toggle("correct", ok);
      });
      return;
    }
  }
  state.answers.push({ question_id: q.id, retries: state.curRetries, hint_used: state.curHint });
  nextStep();
}

function renderQuestion() {
  show("runner");  // ensure the runner is visible (e.g. when returning from a fun-fact)
  const isBoss = state.bossId != null && state.questions[state.idx] && state.questions[state.idx].id === state.bossId;
  const bossBanner = document.getElementById("boss-banner");
  if (bossBanner) {
    bossBanner.classList.toggle("hidden", !isBoss);
    if (isBoss) bossBanner.innerHTML = `${spr("boss")} موجة الشيمر — أقوى سؤال`;
  }
  document.getElementById("screen-runner").classList.toggle("boss", isBoss);
  const q = state.questions[state.idx];
  const passEl = document.getElementById("q-passage");
  if (passEl) {
    if (q.passage) {
      const src = q.source_url ? ` <a href="${q.source_url}" target="_blank" rel="noopener">المصدر</a>` : "";
      passEl.innerHTML = `<div class="passage-text" dir="ltr">${q.passage}</div><div class="passage-src">${src}</div>`;
      passEl.classList.remove("hidden");
    } else {
      passEl.classList.add("hidden");
      passEl.innerHTML = "";
    }
  }
  state.curRetries = 0;
  state.curHint = false;
  document.getElementById("q-feedback").textContent = "";
  const hintBtn = document.getElementById("q-hint-btn");
  const hintBox = document.getElementById("q-hint");
  hintBox.classList.add("hidden");
  if (q.hint_ar) {
    hintBtn.classList.remove("hidden");
    hintBtn.onclick = () => { hintBox.textContent = q.hint_ar; hintBox.classList.remove("hidden"); state.curHint = true; };
  } else {
    hintBtn.classList.add("hidden");
  }

  document.getElementById("progress").textContent = `${state.idx + 1}/${state.questions.length}`;
  document.getElementById("q-prompt").textContent = q.prompt_ar;
  const img = document.getElementById("q-image");
  if (q.asset_file) { img.src = "/content/" + q.asset_file; img.classList.remove("hidden"); }
  else { img.classList.add("hidden"); img.removeAttribute("src"); }

  const q2type = q.type;
  if (q2type === "match") { renderMatch(q); }
  else if (q2type === "order") { renderOrder(q); }
  else if (q2type === "spot") { renderSpot(q); }
  else {
    const opts = document.getElementById("q-options");
    opts.innerHTML = "";
    document.getElementById("q-feedback").textContent = "";
    q.options_ar.forEach((text, i) => {
      const btn = document.createElement("button");
      btn.className = "opt";
      btn.textContent = text;
      btn.onclick = () => pickOption(btn, i);
      opts.appendChild(btn);
    });
  }
  // Fit EVERY question type, not just match/order. An image question with long
  // options overflowed because it was never measured (#24).
  fitPlayArea();
}

function spotIsCorrect(sel, correct) {
  const a = new Set(sel), b = new Set(correct);
  return a.size === b.size && [...a].every((x) => b.has(x));
}

function renderSpot(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  document.getElementById("q-feedback").textContent = "";
  const wrap = document.createElement("div");
  wrap.className = "spot-chips";
  q.options_ar.forEach((text, i) => {
    const chip = document.createElement("button");
    chip.className = "spot-chip";
    chip.textContent = text;
    chip.dataset.idx = i;
    chip.onclick = () => { chip.classList.toggle("selected"); chip.classList.remove("wrong"); };
    wrap.appendChild(chip);
  });
  opts.appendChild(wrap);
  const btn = document.createElement("button");
  btn.className = "runner-submit";
  btn.textContent = "تحقّق";
  btn.onclick = () => checkSpot(btn);
  opts.appendChild(btn);
}

function checkSpot(btn) {
  const q = state.questions[state.idx];
  const chips = [...document.querySelectorAll(".spot-chip")];
  const correct = new Set(q.correct_indices);
  const selected = chips.filter((c) => c.classList.contains("selected")).map((c) => Number(c.dataset.idx));
  if (spotIsCorrect(selected, q.correct_indices)) {
    chips.forEach((c) => { c.disabled = true; if (correct.has(Number(c.dataset.idx))) c.classList.add("correct"); });
    document.getElementById("q-feedback").textContent = "✅ " + (q.explanation_ar || "أحسنت");
    state.answers.push({ question_id: q.id, retries: state.curRetries, hint_used: state.curHint });
    btn.textContent = "التالي ➜";
    btn.onclick = () => nextStep();
    if (typeof burst === "function") burst(btn, { count: 12 });
  } else {
    state.curRetries += 1;
    chips.forEach((c) => {
      const idx = Number(c.dataset.idx);
      if (c.classList.contains("selected") && !correct.has(idx)) c.classList.add("wrong");
    });
    const extra = selected.filter((i) => !correct.has(i)).length;
    const missing = q.correct_indices.filter((i) => !selected.includes(i)).length;
    document.getElementById("q-feedback").textContent =
      "❌ " + (extra ? "أزِل اختيارًا غير صحيح. " : "") + (missing ? "لا تزال علامات لم تُحدَّد." : "");
  }
}

function pickOption(btn, index) {
  const q = state.questions[state.idx];
  if (index === q.correct_index) {
    btn.classList.add("correct");
    btn.disabled = true;
    const fb = document.getElementById("q-feedback");
    fb.textContent = "✅ " + (q.option_explanations_ar[index] || "إجابة صحيحة");
    recordAndAdvance(q);
    if (typeof burst === "function") burst(btn, { count: 10 });
  } else {
    btn.classList.add("wrong");
    btn.disabled = true;
    state.curRetries += 1;
    const ex = document.createElement("div");
    ex.className = "opt-explain";
    ex.textContent = "❌ " + (q.option_explanations_ar[index] || "إجابة غير صحيحة، حاول مرة أخرى");
    btn.insertAdjacentElement("afterend", ex);
  }
}

function recordAndAdvance(q) {
  state.answers.push({ question_id: q.id, retries: state.curRetries, hint_used: state.curHint });
  setTimeout(() => nextStep(), 700);
}

function nextStep() {
  state.idx += 1;
  if (state.idx > 0 && state.idx % 5 === 0 && state.idx < state.questions.length && state.funFacts.length) {
    showFunFact();
  } else if (state.idx < state.questions.length) {
    renderQuestion();
  } else if (state.practice) {
    practiceDone();
  } else {
    submit();
  }
}

function showFunFact() {
  const fact = state.funFacts[(Math.floor(state.idx / 5) - 1) % state.funFacts.length];
  document.getElementById("funfact-text").textContent = fact;
  document.getElementById("funfact-continue").onclick = () => {
    if (state.idx < state.questions.length) renderQuestion(); else submit();
  };
  show("funfact");
}

async function submit() {
  const report = await api(`/quizzes/${state.slug}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData },
    body: JSON.stringify({ answers: state.answers, duration_ms: Date.now() - state.startedAt }),
  });
  renderReport(report);
  if (typeof levelFromXp === "function" && typeof levelUpOverlay === "function") {
    const before = levelFromXp(currentXp).level;
    const afterLv = levelFromXp(currentXp + (report.total_score || 0));
    currentXp += report.total_score || 0;
    if (afterLv.level > before) levelUpOverlay(afterLv.level, afterLv.rank_ar);
  }
  show("report");
}

function renderReport(report) {
  const correct = report.items.filter((i) => i.first_try).length;
  const accuracy = report.items.length ? correct / report.items.length : 0;
  document.documentElement.style.setProperty("--world", String(Math.max(0, Math.min(1, accuracy))));
  document.getElementById("report-summary").innerHTML =
    `<div class="summary-big">${report.total_score} نقطة</div>` +
    `<div style="text-align:center">صحيح ${correct}/${report.items.length} — الترتيب #${report.rank}</div>`;

  const badgesBox = document.getElementById("report-badges");
  badgesBox.innerHTML = "";
  (report.earned_now || []).forEach((code) => {
    const b = BADGES[code]; if (!b) return;
    const span = document.createElement("span");
    span.className = "report-badge";
    span.innerHTML = `${spr(b.ico)} ${b.name_ar}`;
    badgesBox.appendChild(span);
  });

  const box = document.getElementById("report-items");
  box.innerHTML = "";
  report.items.forEach((it) => {
    const div = document.createElement("div");
    const tries = it.first_try ? "من أول محاولة ✅" : `محاولات: ${it.retries + 1}${it.hint_used ? " · استُخدم تلميح" : ""}`;
    div.className = "report-item " + (it.first_try ? "good" : "bad");
    div.innerHTML =
      (it.passage ? `<div class="passage-text" dir="ltr">${it.passage}</div>` : "") +
      `<div>${it.prompt_ar}</div>` +
      `<div>${tries}</div>` +
      `<div>الصحيح: ${it.correct_ar}</div>` +
      (it.explanation_ar ? `<div>📖 ${it.explanation_ar}` + (it.source_page ? ` (ص ${it.source_page})` : "") + `</div>` : "") +
      (it.asset_file ? `<img src="/content/${it.asset_file}" alt="" />` : "");
    box.appendChild(div);
  });

  if (typeof confetti === "function" && correct >= Math.ceil(report.items.length / 2)) confetti();
  document.getElementById("btn-board").onclick = () => loadBoard("quiz");

  // Capstone completion → offer a shareable certificate.
  const oldCert = document.getElementById("btn-cert");
  if (oldCert) oldCert.remove();
  if (state.slug === "capstone" && typeof certificateCard === "function") {
    const cb = document.createElement("button");
    cb.id = "btn-cert"; cb.className = "quiz-card";
    cb.textContent = "🎓 احصل على شهادتك";
    cb.onclick = async () => { const p = (typeof loadProfile === "function") ? await loadProfile() : {}; certificateCard(p, report); };
    document.getElementById("btn-board").insertAdjacentElement("beforebegin", cb);
  }

  // Challenge a colleague to a timed duel on one of these questions.
  const oldDuel = document.getElementById("btn-duel");
  if (oldDuel) oldDuel.remove();
  if (state.slug !== "__review__" && typeof startDuelChallenge === "function" && pickDuelQuestion()) {
    const db = document.createElement("button");
    db.id = "btn-duel"; db.className = "quiz-card"; db.textContent = "⚔️ تحدَّ زميلاً";
    db.onclick = startDuelChallenge;
    document.getElementById("btn-board").insertAdjacentElement("beforebegin", db);
  }
}

async function loadBoard(scope = "quiz") {
  const path = scope === "overall" ? "/leaderboard?scope=overall"
    : scope === "season" ? "/leaderboard?scope=season"
    : `/leaderboard?scope=quiz&slug=${state.slug}`;
  const board = await api(path);
  const ol = document.getElementById("board-list");
  ol.innerHTML = "";
  board.forEach((r) => {
    const li = document.createElement("li");
    const score = (scope === "overall" || scope === "season") ? r.total_score : r.best_score;
    const badge = (r.top_badge && BADGES[r.top_badge]) ? `<span class="lb-badge">${spr(BADGES[r.top_badge].ico)}</span>` : "";
    const tier = (scope === "season" && r.tier_ar) ? `<span class="lb-tier">${r.tier_ar}</span>` : "";
    li.innerHTML = `${r.first_name} — ${score}${badge}${tier}`;
    ol.appendChild(li);
  });
  document.getElementById("board-quiz").onclick = () => loadBoard("quiz");
  document.getElementById("board-overall").onclick = () => loadBoard("overall");
  const seasonBtn = document.getElementById("board-season");
  if (seasonBtn) seasonBtn.onclick = () => loadBoard("season");
  document.getElementById("btn-home").onclick = loadHome;
  show("board");
}

async function loadBadges() {
  let earned = [];
  try { earned = (await api("/me/badges", { headers: { "X-Init-Data": tg.initData } })).badges || []; }
  catch (e) { earned = []; }
  const grid = document.getElementById("badges-grid");
  grid.className = "badges-grid";
  grid.innerHTML = "";
  BADGE_ORDER.forEach((code) => {
    const b = BADGES[code];
    const div = document.createElement("div");
    div.className = "badge" + (earned.includes(code) ? "" : " locked");
    div.innerHTML = `<div class="ico">${spr(b.ico)}</div><div>${b.name_ar}</div>`;
    grid.appendChild(div);
  });
  document.getElementById("btn-badges-home").onclick = loadHome;
  show("badges");
}

const LEVELS = {
  not_started: { ar: "لم يبدأ", cls: "lv-none" },
  familiar: { ar: "مبتدئ", cls: "lv-familiar" },
  proficient: { ar: "جيد", cls: "lv-proficient" },
  mastered: { ar: "متقن", cls: "lv-mastered" },
};

async function loadDashboard() {
  let dash;
  try {
    dash = await api("/me/dashboard", { headers: { "X-Init-Data": tg.initData } });
  } catch (e) {
    document.getElementById("dash-stats").textContent = "تعذّر تحميل التقدّم";
    document.getElementById("dash-next").innerHTML = "";
    document.getElementById("dash-mastery").innerHTML = "";
    document.getElementById("dash-history").innerHTML = "";
    document.getElementById("btn-progress-home").onclick = loadHome;
    show("progress");
    return;
  }

  const s = dash.stats;
  document.getElementById("dash-stats").innerHTML =
    `<div class="stat"><b>${s.total_points}</b><span>نقطة</span></div>` +
    `<div class="stat"><b>${s.attempts_count}</b><span>محاولة</span></div>` +
    `<div class="stat"><b>${Math.round(s.first_try_accuracy * 100)}%</b><span>دقة أول محاولة</span></div>` +
    `<div class="stat"><b>${s.best_streak}</b><span>أطول سلسلة</span></div>`;

  const nextBox = document.getElementById("dash-next");
  nextBox.innerHTML = "";
  if (dash.next && dash.next.length) {
    const head = document.createElement("div");
    head.className = "next-head";
    head.textContent = "ما التالي؟";
    nextBox.appendChild(head);
    dash.next.forEach((n) => {
      const b = document.createElement("button");
      b.className = "next-card";
      b.innerHTML = `راجع <b>${n.label_ar}</b> في «${n.quiz_title_ar}»`;
      b.onclick = () => startQuiz(n.quiz_slug);
      nextBox.appendChild(b);
    });
  }

  const mBox = document.getElementById("dash-mastery");
  mBox.innerHTML = "";
  const byQuiz = {};
  dash.mastery.forEach((m) => { (byQuiz[m.quiz_title_ar] = byQuiz[m.quiz_title_ar] || []).push(m); });
  Object.keys(byQuiz).forEach((title) => {
    const group = document.createElement("div");
    group.className = "mastery-group";
    group.innerHTML = `<div class="mastery-title">${title}</div>`;
    const chips = document.createElement("div");
    chips.className = "mastery-chips";
    byQuiz[title].forEach((m) => {
      const lv = LEVELS[m.level] || LEVELS.not_started;
      const chip = document.createElement("span");
      chip.className = "mchip " + lv.cls;
      chip.innerHTML = `${m.label_ar}<small>${lv.ar}</small>`;
      chips.appendChild(chip);
    });
    group.appendChild(chips);
    mBox.appendChild(group);
  });

  const hist = document.getElementById("dash-history");
  hist.innerHTML = "";
  dash.history.forEach((h) => {
    const li = document.createElement("li");
    const when = (h.finished_at || "").slice(0, 10);
    li.innerHTML = `${h.quiz_title_ar} — ${h.total_score} نقطة · ${Math.round(h.accuracy * 100)}% <small>${when}</small>`;
    hist.appendChild(li);
  });

  const nb = document.getElementById("btn-lab-notebook");
  if (nb && typeof notebookCard === "function") {
    nb.onclick = async () => { const p = (typeof loadProfile === "function") ? await loadProfile() : {}; notebookCard(p, dash); };
  }
  document.getElementById("btn-progress-home").onclick = loadHome;
  show("progress");
}

loadHome().catch(() => { const m = document.getElementById("map-path"); if (m) m.textContent = "تعذّر التحميل"; });
