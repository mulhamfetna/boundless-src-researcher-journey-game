import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
// The <main id="app"> block holds every screen + element the app touches.
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

// Load app.js into the current jsdom document and return its drivable functions.
// app.js is a classic script with top-level `function` declarations and a `let state`;
// we evaluate it with window/document/fetch injected and return the functions we drive.
function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {} } };

  const questions = Array.from({ length: 10 }, (_, i) => ({
    id: i, type: "mcq", prompt_ar: "س" + i, concept: "c",
    options_ar: ["أ", "ب"], correct_index: 0, option_explanations_ar: ["", ""], hint_ar: "",
  }));
  const fetchStub = vi.fn((url) =>
    Promise.resolve({
      ok: true,
      json: async () =>
        url.includes("/questions")
          ? { quiz: { slug: "x", title_ar: "X" }, questions, fun_facts_ar: ["f1", "f2", "f3"] }
          : [],
    })
  );

  // Drop the auto-run bootstrap line so we control the flow from the test.
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const factory = new Function(
    "window", "document", "fetch",
    src + "\n; return { startQuiz, nextStep, show };"
  );
  return factory(window, document, fetchStub, fetchStub);
}

const isHidden = (id) => document.getElementById(id).classList.contains("hidden");

describe("quiz runner screen transitions", () => {
  it("starts on the runner screen", async () => {
    const app = loadApp();
    await app.startQuiz("x");
    expect(isHidden("screen-runner")).toBe(false);
  });

  it("shows a fun-fact at question 5", async () => {
    const app = loadApp();
    await app.startQuiz("x");
    for (let i = 0; i < 5; i++) app.nextStep(); // advance idx 0 -> 5
    expect(isHidden("screen-funfact")).toBe(false);
    expect(isHidden("screen-runner")).toBe(true);
  });

  it("returns to the runner after pressing متابعة on a fun-fact (regression: no freeze)", async () => {
    const app = loadApp();
    await app.startQuiz("x");
    for (let i = 0; i < 5; i++) app.nextStep();
    // press the fun-fact continue button
    document.getElementById("funfact-continue").onclick();
    // The bug left the fun-fact screen visible (frozen); the fix shows the runner.
    expect(isHidden("screen-runner")).toBe(false);
    expect(isHidden("screen-funfact")).toBe(true);
  });
});
