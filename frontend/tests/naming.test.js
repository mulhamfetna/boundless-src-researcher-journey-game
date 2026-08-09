/**
 * Product naming (issue #44).
 *
 * The app was once «مسابقة المجلات العلمية» — a single quiz about journal
 * classification. It is now «رحلة الباحث», seven stations covering the whole
 * research-to-publication pipeline. The old name survived in three places long
 * after the rebrand, including the <title> Telegram renders in the Mini App
 * header and the bot's very first message to a new player.
 *
 * That mismatch is worse than untidy: the public launch announces «رحلة الباحث»,
 * so a player who arrives from the campaign must not be greeted by a different,
 * narrower product name. These assertions keep the old vocabulary from creeping
 * back in — including "مسابقة" as a generic word for a station, which is what
 * let it survive the first rebrand pass.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const botSrc = readFileSync(join(dir, "..", "..", "backend", "app", "bot.py"), "utf8");

const PRODUCT_NAME = "رحلة الباحث";
// Any inflection of the pre-rebrand word, e.g. "مسابقة" / "المسابقة".
const OLD_WORD = /مسابقة/;

describe("product naming", () => {
  it("the page title is the product name", () => {
    const title = html.match(/<title>([^<]*)<\/title>/)?.[1]?.trim();
    expect(title).toBe(PRODUCT_NAME);
  });

  it("no user-visible surface in the Mini App uses the old word", () => {
    expect(html).not.toMatch(OLD_WORD);
  });

  it("no bot message uses the old word", () => {
    expect(botSrc).not.toMatch(OLD_WORD);
  });

  it("the bot's welcome names the product", () => {
    expect(botSrc).toContain(PRODUCT_NAME);
  });
});
