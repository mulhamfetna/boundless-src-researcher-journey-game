/**
 * Copyright attribution (issue #18).
 *
 * The work is jointly held by Boundless Academic Services, the Scientific
 * Research Camp initiative, and Mulham Fetna. AGPL-3.0 expects the notice to be
 * visible to users of the running program, not only to people reading the repo —
 * so the credit appears in the app itself and on the cards learners share.
 *
 * The strings live in ONE place (CREDITS) so the app, the cards and the repo
 * metadata cannot drift apart.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8");
const cardSrc = readFileSync(join(dir, "..", "card.js"), "utf8");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

const BOUNDLESS_AR = "باوندلس للخدمات الأكاديمية";
const CAMP_AR = "معسكر البحث العلمي";

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "", ready() {}, expand() {}, showAlert() {} } };
  const fetchStub = vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }));
  const src = appSrc.replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
  return new Function(
    "window", "document", "fetch",
    src + "\n; return { CREDITS, renderCredits, showAbout, show };"
  )(window, document, fetchStub);
}

describe("attribution strings", () => {
  it("names both organisations and the author in one shared constant", () => {
    const { CREDITS } = loadApp();
    expect(CREDITS.orgs_ar).toEqual([BOUNDLESS_AR, CAMP_AR]);
    expect(CREDITS.orgs_en).toEqual([
      "Boundless Academic Services",
      "Scientific Research Camp initiative",
    ]);
    expect(CREDITS.author).toBe("Mulham Fetna");
    expect(CREDITS.year).toBe("2026");
  });

  it("builds a copyright line carrying every holder", () => {
    const { CREDITS } = loadApp();
    expect(CREDITS.line_ar).toContain("©");
    expect(CREDITS.line_ar).toContain(BOUNDLESS_AR);
    expect(CREDITS.line_ar).toContain(CAMP_AR);
  });
});

describe("the credit is visible inside the app", () => {
  it("renders on the home screen", () => {
    const app = loadApp();
    app.renderCredits();
    const el = document.getElementById("credits");
    expect(el.textContent).toContain(BOUNDLESS_AR);
    expect(el.textContent).toContain(CAMP_AR);
  });

  it("renders on the onboarding screen, so it is seen on first launch", () => {
    const app = loadApp();
    app.renderCredits();
    const el = document.getElementById("ob-credits");
    expect(el.textContent).toContain(BOUNDLESS_AR);
    expect(el.textContent).toContain(CAMP_AR);
  });

  it("has an About screen listing the holders and the licence", () => {
    const app = loadApp();
    app.showAbout();
    expect(document.getElementById("screen-about").classList.contains("hidden")).toBe(false);
    const text = document.getElementById("about-body").textContent;
    expect(text).toContain(BOUNDLESS_AR);
    expect(text).toContain(CAMP_AR);
    expect(text).toContain("Mulham Fetna");
    expect(text).toContain("AGPL");
  });
});

describe("shared cards carry the attribution off-platform", () => {
  it("draws both organisations onto the card footer", () => {
    document.body.innerHTML = "";
    const drawn = [];
    // Every canvas method returns a shape that satisfies both gradient and
    // metrics callers, so drawCard can run to completion whatever it reaches for.
    const ctx = new Proxy({}, {
      get: (_, k) =>
        k === "fillText"
          ? (t) => drawn.push(String(t))
          : () => ({ addColorStop() {}, width: 10 }),
      set: () => true,
    });
    // Use the real jsdom document (showCard builds an overlay), but hand back an
    // instrumented canvas so we can read what was painted.
    const realCreate = document.createElement.bind(document);
    const spy = vi.spyOn(document, "createElement").mockImplementation((tag) =>
      tag === "canvas"
        ? { width: 0, height: 0, getContext: () => ctx, toDataURL: () => "data:," }
        : realCreate(tag)
    );
    const win = {};
    new Function("window", "document", "navigator", cardSrc)(win, document, {});
    win.certificateCard({ name: "لينا" }, { total_score: 2705, items: [] });
    spy.mockRestore();

    const all = drawn.join(" | ");
    expect(all).toContain(BOUNDLESS_AR);
    expect(all).toContain(CAMP_AR);
  });

  it("the card credit matches CREDITS in app.js, so they cannot drift", () => {
    const { CREDITS } = loadApp();
    const cardLine = cardSrc.match(/var CARD_CREDIT = "([^"]+)"/)[1];
    CREDITS.orgs_ar.forEach((org) => expect(cardLine).toContain(org));
    expect(cardLine).toContain(CREDITS.year);
  });
});
