import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "x", ready() {}, expand() {}, showAlert() {} } };
  const qs = [0, 1, 2].map((i) => ({
    id: i, type: "mcq", prompt_ar: "س" + i, concept: "c",
    options_ar: ["أ", "ب"], correct_index: 0, option_explanations_ar: ["", ""], hint_ar: "",
  }));
  const fetchStub = vi.fn((url) =>
    Promise.resolve({ ok: true, json: async () => (url.includes("/me/review") ? { questions: qs } : []) }));
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const factory = new Function("window", "document", "fetch", src + "\n; return { startReview, nextStep, show };");
  return factory(window, document, fetchStub);
}

describe("Hex-Recall review (practice mode)", () => {
  it("plays the review deck and ends on a practice-done message (no submit)", async () => {
    const app = loadApp();
    await app.startReview();
    expect(document.getElementById("screen-runner").classList.contains("hidden")).toBe(false);
    app.nextStep(); app.nextStep(); app.nextStep(); // idx 0 -> 3 (deck length 3) -> practiceDone
    expect(document.getElementById("screen-funfact").classList.contains("hidden")).toBe(false);
    expect(document.getElementById("funfact-text").textContent).toContain("راجعت");
  });
});
