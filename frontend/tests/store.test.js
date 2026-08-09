import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

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

/**
 * A Telegram client that accepts a CloudStorage request and never answers used
 * to deadlock the whole app: loadProfile() never settled, so loadHome() never
 * ran and the player saw an empty background with no error and nothing to
 * report (#48). Boot must never depend on the client replying.
 */
describe("store: an unanswered CloudStorage never blocks boot", () => {
  const silent = { getItems: () => {}, setItem: () => {} }; // accepts, never calls back

  beforeEach(() => {
    vi.useFakeTimers();
    window.localStorage.clear();
    window.Telegram = { WebApp: { CloudStorage: silent } };
    new Function("window", "document", "localStorage", src)(window, document, window.localStorage);
  });
  afterEach(() => { vi.useRealTimers(); delete window.Telegram; });

  it("loadProfile falls back to localStorage instead of hanging", async () => {
    window.localStorage.setItem("rq_name", "محلي");
    window.localStorage.setItem("rq_onboarded", "1");

    const pending = window.loadProfile();
    await vi.advanceTimersByTimeAsync(2000);
    const p = await pending;

    expect(p.name).toBe("محلي");
    expect(p.onboarded).toBe(true);
  });

  // Two keys, one advance: the cloud writes must overlap. If they were
  // serialised, only the first would have fired by now and this would hang —
  // which is exactly the 1.5s-per-key stall the fix removes.
  it("saveProfile still resolves, so onboarding cannot stall", async () => {
    const pending = window.saveProfile({ name: "سلمى", onboarded: true });
    await vi.advanceTimersByTimeAsync(2000);

    await expect(pending).resolves.toBe(true);
    // The local copy is written before the cloud attempt, so nothing is lost.
    expect(window.localStorage.getItem("rq_name")).toBe("سلمى");
  });
});
