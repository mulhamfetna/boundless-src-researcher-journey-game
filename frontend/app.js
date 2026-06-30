const tg = window.Telegram ? window.Telegram.WebApp : { initData: "", ready() {}, expand() {} };
tg.ready(); tg.expand();

const screens = ["home", "runner", "report", "board", "badges", "funfact", "progress", "onboarding", "report-issue"];
function show(name) {
  screens.forEach(s => document.getElementById("screen-" + s).classList.toggle("hidden", s !== name));
}

const BADGES = {
  perfect_quiz: { ico: "perfect_quiz", name_ar: "الإتقان" },
  self_reliant: { ico: "self_reliant", name_ar: "بلا تلميحات" },
  streak_master: { ico: "streak_master", name_ar: "السلسلة" },
  first_finish: { ico: "first_finish", name_ar: "البداية" },
};
const BADGE_ORDER = ["perfect_quiz", "self_reliant", "streak_master", "first_finish"];

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts);
  if (!res.ok) throw new Error("api " + res.status);
  return res.json();
}

let state = { slug: null, questions: [], funFacts: [], idx: 0, answers: [], curRetries: 0, curHint: false };
let currentXp = 0;

const AVATARS = (typeof AVATAR_SPRITES !== "undefined") ? AVATAR_SPRITES : ["scholar", "owl", "fox"];
function spr(name) { return (typeof sprite === "function") ? sprite(name) : ""; }
function avatarSprite(id) { return spr((typeof AVATAR_SPRITES !== "undefined" && AVATAR_SPRITES.includes(id)) ? id : "scholar"); }
function stageSprite(slug) { return spr((typeof STAGE_SPRITES !== "undefined" && STAGE_SPRITES[slug]) || "book"); }

async function loadHome() {
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
  if (typeof embers === "function") embers();
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
    `<div class="mentor-card"><div class="mentor-avatar">${spr("owl")}</div>` +
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

function renderMatch(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "match-wrap";
  const leftCol = document.createElement("div");
  leftCol.className = "match-col";
  const rightCol = document.createElement("div");
  rightCol.className = "match-col";
  wrap.append(leftCol, rightCol);
  opts.appendChild(wrap);

  // left fixed rows, each with a drop slot
  q.left_ar.forEach((text, li) => {
    const row = document.createElement("div");
    row.innerHTML = `<div style="margin-bottom:4px">${text}</div>`;
    const slot = document.createElement("div");
    slot.className = "slot";
    slot.dataset.left = li;
    row.appendChild(slot);
    leftCol.appendChild(row);
  });

  // right draggable chips, shuffled, carrying original index
  const order = q.right_ar.map((_, i) => i).sort(() => Math.random() - 0.5);
  order.forEach((ri) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = q.right_ar[ri];
    chip.dataset.right = ri;
    rightCol.appendChild(chip);
    makeChipDraggable(chip, rightCol);
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
    e.preventDefault();
    chip.setPointerCapture(e.pointerId);
    chip.classList.add("dragging");
    const move = (ev) => {
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

function renderOrder(q) {
  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  const list = document.createElement("div");
  list.className = "order-list";
  opts.appendChild(list);
  const order = q.items_ar.map((_, i) => i).sort(() => Math.random() - 0.5);
  order.forEach((oi) => {
    const row = document.createElement("div");
    row.className = "order-row";
    row.dataset.orig = oi;
    row.innerHTML = `<span class="handle">≡</span><span>${q.items_ar[oi]}</span>`;
    list.appendChild(row);
    makeRowReorderable(row, list);
  });
  ensureSubmitButton(() => {
    const sequence = [...list.querySelectorAll(".order-row")].map((r) => Number(r.dataset.orig));
    checkComplex({ sequence });
  });
}

function makeRowReorderable(row, list) {
  row.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    // Capture on the STABLE list, not the row: reordering moves `row` in the DOM
    // every step, and a captured element that moves fires lostpointercapture in
    // Chrome — which silently kills the drag after one step. The list never moves.
    list.setPointerCapture(e.pointerId);
    row.classList.add("dragging");
    const move = (ev) => {
      const over = elementUnder(ev.clientX, ev.clientY, ".order-row");
      if (over && over !== row) {
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
      const rows = [...document.querySelectorAll(".order-row")];
      rows.forEach((r, i) => {
        const isCorrect = Number(r.dataset.orig) === q.correct_sequence[i];
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
    if (isBoss) bossBanner.innerHTML = `${spr("crown")} تحدّي الزعيم`;
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
}

async function loadBoard(scope = "quiz") {
  const path = scope === "overall" ? "/leaderboard?scope=overall" : `/leaderboard?scope=quiz&slug=${state.slug}`;
  const board = await api(path);
  const ol = document.getElementById("board-list");
  ol.innerHTML = "";
  board.forEach((r) => {
    const li = document.createElement("li");
    const score = scope === "overall" ? r.total_score : r.best_score;
    const badge = (r.top_badge && BADGES[r.top_badge]) ? `<span class="lb-badge">${spr(BADGES[r.top_badge].ico)}</span>` : "";
    li.innerHTML = `${r.first_name} — ${score}${badge}`;
    ol.appendChild(li);
  });
  document.getElementById("board-quiz").onclick = () => loadBoard("quiz");
  document.getElementById("board-overall").onclick = () => loadBoard("overall");
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

  document.getElementById("btn-progress-home").onclick = loadHome;
  show("progress");
}

loadHome().catch(() => { const m = document.getElementById("map-path"); if (m) m.textContent = "تعذّر التحميل"; });
