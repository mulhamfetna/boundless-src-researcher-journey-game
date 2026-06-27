import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8").replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {} } };
  const questions = [{ id: 1, type: "mcq", prompt_ar: "ما هذا القسم؟", concept: "abstract",
    options_ar: ["مقدمة", "ملخص"], correct_index: 1, option_explanations_ar: ["", ""], hint_ar: "",
    passage: "We propose a novel method and report gains.", source_url: "https://doaj.org/a/1" }];
  const fetchMock = vi.fn((url) => Promise.resolve({ ok: true, json: async () =>
    String(url).includes("/questions") ? { quiz: { slug: "x", title_ar: "X" }, questions, fun_facts_ar: [] } : [] }));
  global.fetch = fetchMock;
  const factory = new Function("window", "document", "fetch", appSrc + "\n; return { startQuiz, show };");
  return factory(window, document, fetchMock);
}

describe("passage block", () => {
  it("renders the excerpt and a source link in the runner", async () => {
    const app = loadApp();
    await app.startQuiz("x");
    const p = document.getElementById("q-passage");
    expect(p.classList.contains("hidden")).toBe(false);
    expect(p.textContent).toContain("novel method");
    expect(p.querySelector("a").getAttribute("href")).toBe("https://doaj.org/a/1");
  });
});
