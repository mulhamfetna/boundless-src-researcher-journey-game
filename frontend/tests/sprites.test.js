import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "sprites.js"), "utf8");
beforeEach(() => { new Function("window", src)(window); });

describe("sprites", () => {
  it("exposes Arcane champion avatars", () => {
    expect(window.AVATAR_SPRITES).toEqual(["tinkerer", "brawler", "sniper", "alchemist", "enforcer", "gremlin"]);
  });
  it("renders every champion + boss + mentor as svg", () => {
    for (const n of [...window.AVATAR_SPRITES, "boss", "mentor"]) {
      expect(window.sprite(n)).toMatch(/^<svg/);
    }
  });
  it("returns an svg for stage/badge/misc ids", () => {
    for (const id of ["book", "magnifier", "doc", "puzzle", "crown", "star", "check", "bug", "flag"]) {
      expect(window.sprite(id)).toMatch(/^<svg/);
    }
  });
  it("falls back to a champion for unknown ids", () => {
    expect(window.sprite("zzz")).toBe(window.sprite("tinkerer"));
  });
  it("exposes the id maps with expected keys", () => {
    expect(window.AVATAR_SPRITES.length).toBe(6);
    expect(Object.keys(window.STAGE_SPRITES).sort()).toEqual(["capstone", "foundations", "journals", "paper-parts", "paper-types", "publishing", "submission"]);
    expect(Object.keys(window.BADGE_SPRITES).sort()).toEqual(
      ["all_stations", "dedicated", "first_finish", "flawless", "perfect_capstone",
       "perfect_quiz", "self_reliant", "senior_researcher", "streak_10", "streak_master"]);
  });

  it("renders the capstone node + every badge sprite as svg", () => {
    expect(window.sprite("capstone")).toMatch(/^<svg/);
    for (const code of Object.values(window.BADGE_SPRITES)) {
      expect(window.sprite(code)).toMatch(/^<svg/);
    }
  });
  it("maps champion raster art to png filenames", () => {
    expect(Object.keys(window.AVATAR_ART).sort()).toEqual(["alchemist", "brawler", "gremlin", "sniper", "tinkerer"]);
  });
  it("champArt returns an <img> for arted champions, null otherwise", () => {
    expect(window.champArt("tinkerer")).toMatch(/<img[^>]+champ_tinkerer\.png/);
    expect(window.champArt("gremlin")).toMatch(/champ_gremlin\.png/);
    expect(window.champArt("enforcer")).toBeNull(); // no art -> keeps the SVG sprite
    expect(window.champArt("zzz")).toBeNull();
  });
});
