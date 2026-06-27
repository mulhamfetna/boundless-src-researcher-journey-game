import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "sprites.js"), "utf8");
beforeEach(() => { new Function("window", src)(window); });

describe("sprites", () => {
  it("returns an svg for known ids", () => {
    for (const id of ["scholar", "owl", "book", "magnifier", "crown", "star", "check"]) {
      expect(window.sprite(id)).toMatch(/^<svg/);
    }
  });
  it("falls back to scholar for unknown ids", () => {
    expect(window.sprite("zzz")).toBe(window.sprite("scholar"));
  });
  it("exposes the id maps with expected keys", () => {
    expect(window.AVATAR_SPRITES.length).toBeGreaterThanOrEqual(6);
    expect(Object.keys(window.STAGE_SPRITES).sort()).toEqual(["foundations", "journals", "paper-parts", "paper-types"]);
    expect(Object.keys(window.BADGE_SPRITES).sort()).toEqual(["first_finish", "perfect_quiz", "self_reliant", "streak_master"]);
  });
});
