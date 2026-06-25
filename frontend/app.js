const tg = window.Telegram ? window.Telegram.WebApp : { initData: "", ready() {}, expand() {} };
tg.ready(); tg.expand();

const screens = ["home", "runner", "report", "board"];
function show(name) {
  screens.forEach(s => document.getElementById("screen-" + s).classList.toggle("hidden", s !== name));
}

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
  show("home");
}

async function startQuiz(slug) {
  const data = await api(`/quizzes/${slug}/questions`);
  state = { slug, questions: data.questions, idx: 0, answers: [], qStart: 0, timer: null, startedAt: Date.now() };
  renderQuestion();
  show("runner");
}

function renderQuestion() {
  const q = state.questions[state.idx];
  document.getElementById("progress").textContent = `${state.idx + 1}/${state.questions.length}`;
  document.getElementById("q-prompt").textContent = q.prompt_ar;
  const img = document.getElementById("q-image");
  if (q.asset_file) { img.src = "/content/" + q.asset_file; img.classList.remove("hidden"); }
  else { img.classList.add("hidden"); img.removeAttribute("src"); }

  const opts = document.getElementById("q-options");
  opts.innerHTML = "";
  q.options_ar.forEach((text, i) => {
    const btn = document.createElement("button");
    btn.className = "opt";
    btn.textContent = text;
    btn.onclick = () => answer(i);
    opts.appendChild(btn);
  });

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
  const correct = report.items.filter(i => i.is_correct).length;
  document.getElementById("report-summary").innerHTML =
    `<div class="summary-big">${report.total_score} نقطة</div>` +
    `<div style="text-align:center">صحيح ${correct}/${report.items.length} — الترتيب #${report.rank}</div>`;
  const box = document.getElementById("report-items");
  box.innerHTML = "";
  report.items.forEach(it => {
    const div = document.createElement("div");
    div.className = "report-item " + (it.is_correct ? "good" : "bad");
    const yours = it.options_ar[it.given_index] ?? "—";
    const right = it.options_ar[it.correct_index];
    div.innerHTML =
      `<div>${it.prompt_ar}</div>` +
      `<div>إجابتك: ${yours} ${it.is_correct ? "✅" : "❌"}</div>` +
      (it.is_correct ? "" : `<div>الصحيح: ${right}</div>`) +
      (it.explanation_ar ? `<div>📖 ${it.explanation_ar}` + (it.source_page ? ` (ص ${it.source_page})` : "") + `</div>` : "") +
      (it.asset_file ? `<img src="/content/${it.asset_file}" alt="" />` : "");
    box.appendChild(div);
  });
  document.getElementById("btn-board").onclick = () => loadBoard();
}

async function loadBoard() {
  const board = await api(`/leaderboard?slug=${state.slug}`);
  const ol = document.getElementById("board-list");
  ol.innerHTML = "";
  board.forEach(r => {
    const li = document.createElement("li");
    li.textContent = `${r.first_name} — ${r.best_score}`;
    ol.appendChild(li);
  });
  document.getElementById("btn-home").onclick = loadHome;
  show("board");
}

loadHome().catch(e => { document.getElementById("quiz-list").textContent = "تعذّر التحميل"; });
