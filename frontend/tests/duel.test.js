import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

const Q = { id: 9, type: "mcq", prompt_ar: "س", concept: "c", options_ar: ["أ", "ب"], correct_index: 0, option_explanations_ar: ["", ""], hint_ar: "" };

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "x", ready() {}, expand() {}, showAlert() {} } };
  const fetchStub = vi.fn((url, opts) => {
    let body = [];
    if (url.includes("/duels/tok123/answer")) body = { token: "tok123", winner: "opponent", creator: { name: "Vi", correct: true, time_ms: 4000 }, opponent: { name: "Me", correct: true, time_ms: 2000 } };
    else if (url.includes("/duels/tok123")) body = { token: "tok123", status: "open", question: Q, creator: { name: "Vi", correct: true, time_ms: 4000 } };
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const factory = new Function("window", "document", "fetch", src + "\n; return { startDuelAnswer, show };");
  return factory(window, document, fetchStub);
}

describe("peer-review duel (answer via deep-link)", () => {
  it("loads the challenged question, plays it, shows the winner", async () => {
    const app = loadApp();
    await app.startDuelAnswer("tok123");
    expect(document.getElementById("screen-duel").classList.contains("hidden")).toBe(false);
    const opts = document.querySelectorAll("#duel-options .opt");
    expect(opts.length).toBe(2);
    opts[0].click();
    await new Promise((r) => setTimeout(r, 0)); // let finishDuel's await resolve
    expect(document.getElementById("duel-result").textContent).toContain("الفائز");
  });
});
