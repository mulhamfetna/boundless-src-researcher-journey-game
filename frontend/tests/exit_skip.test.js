/**
 * Leaving a station (#28) and skipping a question (#29).
 *
 * Neither should require closing the whole Mini App, and neither should be free:
 * exiting abandons the attempt, skipping costs the question's points and the
 * streak. The cost is applied SERVER-side; the client only reports the skip.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

const Q = (id) => ({
  id, type: "mcq", prompt_ar: "س" + id, concept: "c",
  options_ar: ["أ", "ب"], correct_index: 0,
  option_explanations_ar: ["", ""], explanation_ar: "الشرح الصحيح",
});

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {}, showAlert() {} } };
  const fetchStub = vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }));
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const app = new Function("window", "document", "fetch",
    src + "\n; return { renderQuestion, skipQuestion, exitStation, state, show };"
  )(window, document, fetchStub);
  app.state.questions = [Q(1), Q(2)];
  app.state.idx = 0;
  app.state.answers = [];
  app.state.curRetries = 0;
  app.state.curHint = false;
  return app;
}

describe("#29 skipping a question", () => {
  it("records the question as skipped so the server can zero it", () => {
    const app = loadApp();
    app.renderQuestion();
    app.skipQuestion();

    expect(app.state.answers).toHaveLength(1);
    expect(app.state.answers[0]).toMatchObject({ question_id: 1, skipped: true });
  });

  it("moves on to the next question instead of leaving the learner stuck", () => {
    const app = loadApp();
    app.renderQuestion();
    app.skipQuestion();
    expect(app.state.idx).toBe(1);
  });

  it("shows the explanation, so a skip still teaches the point", () => {
    const app = loadApp();
    app.renderQuestion();
    app.skipQuestion();
    expect(document.getElementById("q-feedback").textContent).toContain("الشرح الصحيح");
  });

  it("offers a skip control on the runner", () => {
    const app = loadApp();
    app.renderQuestion();
    const btn = document.getElementById("q-skip-btn");
    expect(btn).not.toBeNull();
    expect(btn.textContent).toMatch(/تخطّ|تخطي/);
  });
});

describe("#28 leaving a station", () => {
  it("returns to the map rather than closing the app", () => {
    const app = loadApp();
    app.renderQuestion();
    app.exitStation({ confirm: false });
    expect(document.getElementById("screen-runner").classList.contains("hidden")).toBe(true);
  });

  it("discards the in-progress attempt", () => {
    const app = loadApp();
    app.renderQuestion();
    app.state.answers.push({ question_id: 1, retries: 0, hint_used: false });
    app.exitStation({ confirm: false });
    expect(app.state.answers).toHaveLength(0);
    expect(app.state.idx).toBe(0);
  });

  it("offers an exit control on the runner", () => {
    const app = loadApp();
    app.renderQuestion();
    expect(document.getElementById("q-exit-btn")).not.toBeNull();
  });
});
