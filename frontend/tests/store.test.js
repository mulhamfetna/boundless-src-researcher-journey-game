import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "store.js"), "utf8");

function load() {
  delete window.Telegram; // force localStorage fallback
  new Function("window", "document", "localStorage", src)(window, document, window.localStorage);
}

describe("store (profile persistence)", () => {
  beforeEach(() => { window.localStorage.clear(); load(); });

  it("defaults when nothing stored", async () => {
    const p = await window.loadProfile();
    expect(p).toEqual({ name: "", avatar: "🧑‍🎓", onboarded: false });
  });

  it("round-trips via localStorage fallback", async () => {
    await window.saveProfile({ name: "لينا", avatar: "🦊", onboarded: true });
    const p = await window.loadProfile();
    expect(p.name).toBe("لينا");
    expect(p.avatar).toBe("🦊");
    expect(p.onboarded).toBe(true);
  });

  it("partial save leaves other fields at defaults", async () => {
    await window.saveProfile({ name: "سامي" });
    const p = await window.loadProfile();
    expect(p.name).toBe("سامي");
    expect(p.avatar).toBe("🧑‍🎓");
    expect(p.onboarded).toBe(false);
  });

  it("prefers CloudStorage when available", async () => {
    const mem = { rq_name: "كلاود", rq_avatar: "🦉", rq_onboarded: "1" };
    window.Telegram = { WebApp: { CloudStorage: {
      getItems: (keys, cb) => cb(null, Object.fromEntries(keys.map(k => [k, mem[k] || ""]))),
      setItem: (k, v, cb) => { mem[k] = v; cb(null, true); },
    } } };
    new Function("window", "document", "localStorage", src)(window, document, window.localStorage);
    const p = await window.loadProfile();
    expect(p.name).toBe("كلاود");
    expect(p.avatar).toBe("🦉");
    expect(p.onboarded).toBe(true);
  });
});
