import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

// Two spot questions: correct red flags are chips [0, 2] of 4.
const SPOT_QS = [0, 1].map((n) => ({
  id: n, type: "spot", prompt_ar: "حدد العلامات", concept: "predatory_signs",
  options_ar: ["علم أ", "شرك ب", "علم ج", "شرك د"], correct_indices: [0, 2],
  chip_explanations_ar: ["", "", "", ""], explanation_ar: "أحسنت", hint_ar: "",
}));

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {} } };
  const fetchStub = vi.fn((url) =>
    Promise.resolve({
      ok: true,
      json: async () =>
        url.includes("/questions")
          ? { quiz: { slug: "x", title_ar: "X" }, questions: SPOT_QS, fun_facts_ar: ["f1", "f2", "f3"] }
          : [],
    })
  );
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const factory = new Function("window", "document", "fetch",
    src + "\n; return { spotIsCorrect, startQuiz, nextStep, show };");
  return factory(window, document, fetchStub);
}

describe("spot interaction", () => {
  it("spotIsCorrect requires exact set match (order-independent)", () => {
    const app = loadApp();
    expect(app.spotIsCorrect([2, 0], [0, 2])).toBe(true);
    expect(app.spotIsCorrect([0], [0, 2])).toBe(false);       // missing one
    expect(app.spotIsCorrect([0, 1, 2], [0, 2])).toBe(false); // extra one
    expect(app.spotIsCorrect([], [0])).toBe(false);
  });

  it("renders chips, rejects a wrong set, accepts the exact set", async () => {
    const app = loadApp();
    await app.startQuiz("x");
    const chips = () => [...document.querySelectorAll(".spot-chip")];
    expect(chips().length).toBe(4);
    // wrong: select only chip 0 (correct is [0,2]) then check
    chips()[0].click();
    document.querySelector(".runner-submit").click();
    expect(document.getElementById("q-feedback").textContent).toContain("❌");
    // fix: also select chip 2 -> exact match
    chips()[2].click();
    document.querySelector(".runner-submit").click();
    expect(document.getElementById("q-feedback").textContent).toContain("✅");
  });
});
