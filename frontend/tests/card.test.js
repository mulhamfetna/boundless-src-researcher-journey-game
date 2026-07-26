import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, it, expect } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "..", "card.js"), "utf8");
// card.js is an IIFE that attaches helpers to window.
new Function("window", "document", "navigator", src)(window, document, {});

describe("shareable cards", () => {
  it("shortHash is deterministic, 8 hex chars", () => {
    expect(window.shortHash("Lina|capstone|2705")).toMatch(/^[0-9A-F]{8}$/);
    expect(window.shortHash("x")).toBe(window.shortHash("x"));
    expect(window.shortHash("a")).not.toBe(window.shortHash("b"));
  });
  it("exposes certificate + notebook builders", () => {
    expect(typeof window.certificateCard).toBe("function");
    expect(typeof window.notebookCard).toBe("function");
  });
});
