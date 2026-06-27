import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, beforeEach, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const uiSrc = readFileSync(join(dir, "..", "ui.js"), "utf8");

function loadUi() {
  document.body.innerHTML = '<div id="fx-layer"></div><button id="b">x</button>';
  new Function("window", "document", uiSrc)(window, document);
}

describe("ui juice", () => {
  beforeEach(() => { vi.useFakeTimers(); loadUi(); });

  it("confetti creates the requested number of pieces in the fx layer", () => {
    const n = window.confetti({ count: 10, life: 500 });
    expect(n).toBe(10);
    expect(document.querySelectorAll("#fx-layer .confetti-piece").length).toBe(10);
  });

  it("confetti cleans up its pieces after life ms", () => {
    window.confetti({ count: 6, life: 500 });
    vi.advanceTimersByTime(600);
    expect(document.querySelectorAll(".confetti-piece").length).toBe(0);
  });

  it("confetti defaults to 24 pieces", () => {
    expect(window.confetti()).toBe(24);
  });

  it("burst anchored on an element creates pieces and is a no-op on null", () => {
    expect(window.burst(null)).toBe(0);
    const made = window.burst(document.getElementById("b"), { count: 8 });
    expect(made).toBe(8);
  });
});

describe("mentorSay", () => {
  beforeEach(() => { loadUi(); });

  it("renders an overlay with the given text", () => {
    window.mentorSay("مرحبا");
    const ov = document.querySelector(".mentor-overlay");
    expect(ov).not.toBeNull();
    expect(ov.querySelector(".mentor-text").textContent).toBe("مرحبا");
  });

  it("clicking متابعة removes the overlay and calls onDone", () => {
    let done = false;
    window.mentorSay("هيا", { onDone: () => { done = true; } });
    document.querySelector(".mentor-next").click();
    expect(document.querySelector(".mentor-overlay")).toBeNull();
    expect(done).toBe(true);
  });
});
