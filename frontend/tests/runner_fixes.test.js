/**
 * Runner correctness and readability fixes (issues #24 #25 #26 #27).
 *
 * #25 in particular is a regression from the phone play-area work: ordering
 * feedback still marked rows by their DOM position, but since tap-in-sequence
 * the answer is the TAP order — so the colours marked positions the learner
 * never chose.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const css = readFileSync(join(dir, "..", "styles.css"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

const ORDER_Q = {
  id: 1, type: "order", prompt_ar: "رتّب", concept: "c",
  items_ar: ["أ", "ب", "ج", "د"],
  correct_sequence: [0, 1, 2, 3],
};

function loadApp(q) {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {}, showAlert() {} } };
  const fetchStub = vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }));
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const app = new Function("window", "document", "fetch",
    src + "\n; return { renderOrder, checkComplex, readOrderSequence, state };"
  )(window, document, fetchStub);
  app.state.questions = [q];
  app.state.idx = 0;
  app.state.answers = [];
  app.state.curRetries = 0;
  return app;
}

const rows = () => [...document.querySelectorAll("#q-options .order-row")];

describe("#25 ordering feedback reflects the learner's chosen order", () => {
  it("marks a correctly-placed item green and a misplaced one red", () => {
    const app = loadApp(ORDER_Q);
    app.renderOrder(ORDER_Q);
    const byItem = {};
    rows().forEach((r) => { byItem[r.dataset.orig] = r; });

    // Tap: أ (0) first — correct for position 1. Then ج (2) — wrong for position 2.
    byItem["0"].click();
    byItem["2"].click();
    byItem["1"].click();
    byItem["3"].click();

    app.checkComplex({ sequence: app.readOrderSequence() });

    expect(byItem["0"].classList.contains("correct")).toBe(true);
    expect(byItem["0"].classList.contains("wrong")).toBe(false);
    expect(byItem["2"].classList.contains("wrong")).toBe(true);
    expect(byItem["2"].classList.contains("correct")).toBe(false);
  });

  it("leaves untapped items unmarked rather than colouring them at random", () => {
    const app = loadApp(ORDER_Q);
    app.renderOrder(ORDER_Q);
    const byItem = {};
    rows().forEach((r) => { byItem[r.dataset.orig] = r; });

    byItem["1"].click();   // a single, wrong first pick

    app.checkComplex({ sequence: app.readOrderSequence() });

    expect(byItem["1"].classList.contains("wrong")).toBe(true);
    ["0", "2", "3"].forEach((k) => {
      expect(byItem[k].classList.contains("wrong")).toBe(false);
      expect(byItem[k].classList.contains("correct")).toBe(false);
    });
  });

  it("accepts a fully correct order", () => {
    // A second question follows, so accepting the first advances the runner
    // instead of running the whole submit chain (which would need a report
    // payload and would throw asynchronously — CI catches that, a printed
    // summary does not).
    const filler = {
      id: 99, type: "mcq", prompt_ar: "س", concept: "c",
      options_ar: ["أ", "ب"], correct_index: 0, option_explanations_ar: ["", ""],
    };
    const app = loadApp(ORDER_Q);
    app.state.questions = [ORDER_Q, filler];
    app.renderOrder(ORDER_Q);
    const byItem = {};
    rows().forEach((r) => { byItem[r.dataset.orig] = r; });
    ["0", "1", "2", "3"].forEach((k) => byItem[k].click());

    app.checkComplex({ sequence: app.readOrderSequence() });

    expect(app.state.answers.length).toBe(1);   // accepted
    expect(app.state.answers[0].question_id).toBe(ORDER_Q.id);
  });
});

describe("#26 no near-black text on dark cards", () => {
  it("spot chips do not use the near-black ink colour on a dark card", () => {
    const rule = css.match(/\.spot-chip\s*\{[^}]*\}/)[0];
    expect(rule).toContain("background:var(--card)");
    expect(rule).not.toContain("var(--ink");
  });
});

describe("#27 headings use a legible face, not the compressed display font", () => {
  it("h2/h3 no longer use the compressed display font", () => {
    const rule = css.match(/^h1,\s*h2,\s*h3\s*\{[^}]*\}/m);
    expect(rule).toBeNull();   // the shared h1/h2/h3 rule must be split
    expect(css).toMatch(/h2,\s*h3\s*\{[^}]*--font-body/);
  });
});

describe("#24 image questions keep room for their options", () => {
  it("the runner image is height-capped so it cannot starve the options", () => {
    expect(css).toMatch(/#screen-runner\s+#q-image[^}]*max-height/);
    expect(css).toMatch(/#screen-runner\s+#q-options[^}]*min-height:\s*(?!0)/);
  });
});
