import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "game.js"), "utf8");
beforeEach(() => { new Function("window", src)(window); });

const QUIZZES = [
  { slug: "foundations", title_ar: "الأسس" },
  { slug: "paper-parts", title_ar: "الأجزاء" },
  { slug: "journals", title_ar: "المجلات" },
];

describe("mapState", () => {
  it("marks done from best_by_quiz, first non-done as next, rest open", () => {
    const dash = { stats: { best_by_quiz: { foundations: 120 } } };
    const s = window.mapState(QUIZZES, dash);
    expect(s.map(x => x.status)).toEqual(["done", "next", "open"]);
    expect(s[0].index).toBe(0);
  });

  it("first stage is next when nothing done", () => {
    const s = window.mapState(QUIZZES, { stats: { best_by_quiz: {} } });
    expect(s.map(x => x.status)).toEqual(["next", "open", "open"]);
  });

  it("handles missing dashboard", () => {
    const s = window.mapState(QUIZZES, null);
    expect(s[0].status).toBe("next");
  });
});

describe("mentorLineFor", () => {
  it("interpolates {name}", () => {
    expect(window.mentorLineFor("welcome", { name: "لينا" })).toContain("لينا");
  });
  it("resolves stage keys", () => {
    expect(window.mentorLineFor("stage:journals", {})).toContain("🕵️");
  });
  it("falls back for unknown keys", () => {
    expect(typeof window.mentorLineFor("nope", {})).toBe("string");
  });
});
