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

describe("levelFromXp", () => {
  it("xp 0 is level 1, rank طالب, progress in [0,1)", () => {
    const r = window.levelFromXp(0);
    expect(r.level).toBe(1);
    expect(r.rank_ar).toBe("طالب");
    expect(r.progress).toBeGreaterThanOrEqual(0);
    expect(r.progress).toBeLessThan(1);
  });
  it("crossing a threshold raises the level", () => {
    expect(window.levelFromXp(299).level).toBe(1);
    expect(window.levelFromXp(300).level).toBe(2);
  });
  it("high xp reaches بروفيسور", () => {
    expect(window.levelFromXp(100000).rank_ar).toBe("بروفيسور");
  });
  it("handles missing/negative xp", () => {
    expect(window.levelFromXp(undefined).level).toBe(1);
    expect(window.levelFromXp(-50).level).toBe(1);
  });
});

describe("worldFromLevel", () => {
  it("is 0 at level 1 (deep Zaun) and 1 at level 10+ (Piltover)", () => {
    expect(window.worldFromLevel(1)).toBe(0);
    expect(window.worldFromLevel(10)).toBe(1);
    expect(window.worldFromLevel(100)).toBe(1);
  });
  it("climbs monotonically in between", () => {
    const a = window.worldFromLevel(3), b = window.worldFromLevel(6);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeGreaterThan(a);
    expect(b).toBeLessThan(1);
  });
  it("clamps below 1", () => { expect(window.worldFromLevel(0)).toBe(0); });
});

describe("pickBoss", () => {
  it("picks the highest base_points and moves it last", () => {
    const qs = [{ id: 1, base_points: 100 }, { id: 2, base_points: 120 }, { id: 3, base_points: 90 }];
    const { bossId, ordered } = window.pickBoss(qs);
    expect(bossId).toBe(2);
    expect(ordered[ordered.length - 1].id).toBe(2);
    expect(ordered.length).toBe(3);
  });
  it("ties resolve to the last max", () => {
    const qs = [{ id: 1, base_points: 120 }, { id: 2, base_points: 120 }];
    expect(window.pickBoss(qs).bossId).toBe(2);
  });
  it("empty input is safe", () => {
    expect(window.pickBoss([])).toEqual({ bossId: null, ordered: [] });
  });
});
