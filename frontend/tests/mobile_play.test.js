/**
 * Phone-first play area (issue #15).
 *
 * `match` and `order` used to require dragging a chip across a page that had to
 * scroll — impractical one-handed, which is how nearly every learner plays.
 * Tapping now does everything; dragging is kept for anyone who prefers it.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

const MATCH_Q = {
  id: 1, type: "match", prompt_ar: "طابِق", concept: "c",
  left_ar: ["يسار ١", "يسار ٢", "يسار ٣"],
  right_ar: ["يمين ١", "يمين ٢", "يمين ٣"],
  correct_pairs: [[0, 0], [1, 1], [2, 2]],
};

const ORDER_Q = {
  id: 2, type: "order", prompt_ar: "رتِّب", concept: "c",
  items_ar: ["أولًا", "ثانيًا", "ثالثًا", "رابعًا"],
  correct_sequence: [0, 1, 2, 3],
};

function loadApp(question) {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {}, showAlert() {} } };
  const fetchStub = vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }));
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  const factory = new Function(
    "window", "document", "fetch",
    src + "\n; return { renderMatch, renderOrder, fitToBox, readOrderSequence, state };"
  );
  const app = factory(window, document, fetchStub);
  // checkComplex reads the live question out of state.
  app.state.questions = [question];
  app.state.idx = 0;
  return app;
}

const chips = () => [...document.querySelectorAll("#q-options .chip")];
const slots = () => [...document.querySelectorAll("#q-options .slot")];
const rows = () => [...document.querySelectorAll("#q-options .order-row")];

describe("match — tap to link (no dragging required)", () => {
  it("tapping a chip then a slot places it, with no drag involved", () => {
    const app = loadApp(MATCH_Q);
    app.renderMatch(MATCH_Q);

    const chip = chips()[0];
    chip.click();
    expect(chip.classList.contains("selected")).toBe(true);

    const slot = slots()[0];
    slot.click();

    expect(slot.querySelector(".chip")).toBe(chip);
    expect(chip.classList.contains("selected")).toBe(false);
  });

  it("selecting a different chip moves the selection rather than stacking it", () => {
    const app = loadApp(MATCH_Q);
    app.renderMatch(MATCH_Q);

    chips()[0].click();
    chips()[1].click();

    expect(chips()[0].classList.contains("selected")).toBe(false);
    expect(chips()[1].classList.contains("selected")).toBe(true);
  });

  it("tapping a filled slot picks the chip back up so it can be re-placed", () => {
    const app = loadApp(MATCH_Q);
    app.renderMatch(MATCH_Q);

    const chip = chips()[0];
    chip.click();
    slots()[0].click();
    expect(slots()[0].querySelector(".chip")).toBe(chip);

    slots()[0].click();               // tap the filled slot
    expect(slots()[0].querySelector(".chip")).toBe(null);
    expect(chip.classList.contains("selected")).toBe(true);
  });

  it("a filled row is marked linked, so CSS can collapse it and free screen space", () => {
    const app = loadApp(MATCH_Q);
    app.renderMatch(MATCH_Q);

    chips()[0].click();
    slots()[0].click();

    expect(slots()[0].closest(".match-row").classList.contains("linked")).toBe(true);
  });
});

describe("order — tap in sequence (no reordering required)", () => {
  it("tapping rows assigns 1..n badges in tap order", () => {
    const app = loadApp(ORDER_Q);
    app.renderOrder(ORDER_Q);

    const r = rows();
    r[2].click();
    r[0].click();

    expect(r[2].dataset.seq).toBe("1");
    expect(r[0].dataset.seq).toBe("2");
    expect(r[1].dataset.seq).toBeUndefined();
    expect(r[2].classList.contains("picked")).toBe(true);
  });

  it("tapping a picked row unsets it and renumbers the rest", () => {
    const app = loadApp(ORDER_Q);
    app.renderOrder(ORDER_Q);

    const r = rows();
    r[0].click();
    r[1].click();
    r[2].click();
    expect(r[1].dataset.seq).toBe("2");

    r[0].click();                     // remove the first pick

    expect(r[0].dataset.seq).toBeUndefined();
    expect(r[0].classList.contains("picked")).toBe(false);
    expect(r[1].dataset.seq).toBe("1");
    expect(r[2].dataset.seq).toBe("2");
  });

  it("the submitted sequence follows the taps, not the on-screen order", () => {
    const app = loadApp(ORDER_Q);
    app.renderOrder(ORDER_Q);

    const r = rows();
    const tapped = [r[3], r[1], r[0], r[2]];
    tapped.forEach((row) => row.click());

    const submitted = app.readOrderSequence();
    expect(submitted).toEqual(tapped.map((row) => Number(row.dataset.orig)));
  });

  it("with no taps at all it falls back to on-screen order, so dragging still works", () => {
    const app = loadApp(ORDER_Q);
    app.renderOrder(ORDER_Q);

    const submitted = app.readOrderSequence();
    expect(submitted).toEqual(rows().map((row) => Number(row.dataset.orig)));
  });
});

describe("fitToBox — text scales to the play area instead of the page growing", () => {
  it("shrinks the font until the content fits its box", () => {
    const app = loadApp(ORDER_Q);
    const el = document.createElement("div");
    // Fits only at 13px or below.
    const measure = () => ({
      content: parseFloat(el.style.fontSize) > 13 ? 500 : 300,
      box: 360,
    });
    const size = app.fitToBox(el, { measure });
    expect(size).toBe(13);
    expect(el.style.fontSize).toBe("13px");
  });

  it("keeps the largest size when everything already fits", () => {
    const app = loadApp(ORDER_Q);
    const el = document.createElement("div");
    const size = app.fitToBox(el, { measure: () => ({ content: 100, box: 360 }) });
    expect(size).toBe(16);
  });

  it("stops at the floor rather than shrinking text into illegibility", () => {
    const app = loadApp(ORDER_Q);
    const el = document.createElement("div");
    const size = app.fitToBox(el, { measure: () => ({ content: 9999, box: 10 }) });
    expect(size).toBe(12);
  });
});
