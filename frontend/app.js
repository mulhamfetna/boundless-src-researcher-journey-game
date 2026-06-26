const tg = window.Telegram ? window.Telegram.WebApp : { initData: "", ready() {}, expand() {} };
tg.ready(); tg.expand();

const screens = ["home", "runner", "report", "board", "badges"];
function show(name) {
  screens.forEach(s => document.getElementById("screen-" + s).classList.toggle("hidden", s !== name));
}

const BADGES = {
  perfect_quiz: { ico: "🏅", name_ar: "الإتقان" },
  speed_demon: { ico: "⚡", name_ar: "البرق" },
  streak_master: { ico: "🔥", name_ar: "السلسلة" },
  first_finish: { ico: "🌟", name_ar: "البداية" },
};
const BADGE_ORDER = ["perfect_quiz", "speed_demon", "streak_master", "first_finish"];

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts);
  if (!res.ok) throw new Error("api " + res.status);
  return res.json();
}

let state = { slug: null, questions: [], idx: 0, answers: [], qStart: 0, timer: null };

async function loadHome() {
  const quizzes = await api("/quizzes");
  const list = document.getElementById("quiz-list");
  list.innerHTML = "";
  quizzes.forEach(q => {
    const b = document.createElement("button");
    b.className = "quiz-card";
    b.textContent = q.title_ar;
    b.onclick = () => startQuiz(q.slug);
    list.appendChild(b);
  });
  document.getElementById("btn-my-badges").onclick = loadBadges;
  show("home");
}

async function startQuiz(slug) {
  const data = await api(`/quizzes/${slug}/questions`);
  state = { slug, questions: data.questions, idx: 0, answers: [], qStart: 0, timer: null, startedAt: Date.now() };
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
    answerComplex({ pairs });
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
    answerComplex({ sequence });
  });
}

function makeRowReorderable(row, list) {
  row.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    row.setPointerCapture(e.pointerId);
    row.classList.add("dragging");
    const move = (ev) => {
      const over = elementUnder(ev.clientX, ev.clientY, ".order-row");
      if (over && over !== row) {
        const rect = over.getBoundingClientRect();
        const before = ev.clientY < rect.top + rect.height / 2;
        list.insertBefore(row, before ? over : over.nextSibling);
      }
    };
    const cancel = () => {
      row.classList.remove("dragging");
      row.removeEventListener("pointermove", move);
      row.removeEventListener("pointerup", up);
      row.removeEventListener("pointercancel", cancel);
    };
    const up = () => {
      row.releasePointerCapture(e.pointerId);
      row.classList.remove("dragging");
      row.removeEventListener("pointermove", move);
      row.removeEventListener("pointerup", up);
      row.removeEventListener("pointercancel", cancel);
    };
    row.addEventListener("pointermove", move);
    row.addEventListener("pointerup", up);
    row.addEventListener("pointercancel", cancel);
  });
}

function ensureSubmitButton(onSubmit) {
  const opts = document.getElementById("q-options");
  const btn = document.createElement("button");
  btn.className = "runner-submit";
  btn.textContent = "تأكيد";
  btn.onclick = () => { clearInterval(state.timer); onSubmit(); };
  opts.appendChild(btn);
}

function answerComplex(givenExtra) {
  const q = state.questions[state.idx];
  state.answers.push({ question_id: q.id, time_ms: Date.now() - state.qStart, ...givenExtra });
  state.idx += 1;
  if (state.idx < state.questions.length) renderQuestion();
  else submit();
}

function renderQuestion() {
  const q = state.questions[state.idx];
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
    q.options_ar.forEach((text, i) => {
      const btn = document.createElement("button");
      btn.className = "opt";
      btn.textContent = text;
      btn.onclick = () => answer(i);
      opts.appendChild(btn);
    });
  }

  state.qStart = Date.now();
  const timerEl = document.getElementById("timer");
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    timerEl.textContent = ((Date.now() - state.qStart) / 1000).toFixed(1) + "s";
  }, 100);
}

function answer(index) {
  clearInterval(state.timer);
  const q = state.questions[state.idx];
  state.answers.push({ question_id: q.id, index, time_ms: Date.now() - state.qStart });
  state.idx += 1;
  if (state.idx < state.questions.length) renderQuestion();
  else submit();
}

async function submit() {
  const report = await api(`/quizzes/${state.slug}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Init-Data": tg.initData },
    body: JSON.stringify({ answers: state.answers, duration_ms: Date.now() - state.startedAt }),
  });
  renderReport(report);
  show("report");
}

function renderReport(report) {
  const correct = report.items.filter((i) => i.is_correct).length;
  document.getElementById("report-summary").innerHTML =
    `<div class="summary-big">${report.total_score} نقطة</div>` +
    `<div style="text-align:center">صحيح ${correct}/${report.items.length} — الترتيب #${report.rank}</div>`;

  const badgesBox = document.getElementById("report-badges");
  badgesBox.innerHTML = "";
  (report.earned_now || []).forEach((code) => {
    const b = BADGES[code]; if (!b) return;
    const span = document.createElement("span");
    span.className = "report-badge";
    span.textContent = `${b.ico} ${b.name_ar}`;
    badgesBox.appendChild(span);
  });

  const box = document.getElementById("report-items");
  box.innerHTML = "";
  report.items.forEach((it) => {
    const div = document.createElement("div");
    div.className = "report-item " + (it.is_correct ? "good" : "bad");
    div.innerHTML =
      `<div>${it.prompt_ar}</div>` +
      `<div>إجابتك: ${it.your_ar} ${it.is_correct ? "✅" : "❌"}</div>` +
      (it.is_correct ? "" : `<div>الصحيح: ${it.correct_ar}</div>`) +
      (it.explanation_ar ? `<div>📖 ${it.explanation_ar}` + (it.source_page ? ` (ص ${it.source_page})` : "") + `</div>` : "") +
      (it.asset_file ? `<img src="/content/${it.asset_file}" alt="" />` : "");
    box.appendChild(div);
  });

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
    const badge = (r.top_badge && BADGES[r.top_badge]) ? `<span class="lb-badge">${BADGES[r.top_badge].ico}</span>` : "";
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
    div.innerHTML = `<div class="ico">${b.ico}</div><div>${b.name_ar}</div>`;
    grid.appendChild(div);
  });
  document.getElementById("btn-badges-home").onclick = loadHome;
  show("badges");
}

loadHome().catch(e => { document.getElementById("quiz-list").textContent = "تعذّر التحميل"; });
