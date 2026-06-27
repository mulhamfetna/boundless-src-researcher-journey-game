import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect, vi } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const appSrc = readFileSync(join(dir, "..", "app.js"), "utf8").replace(/loadHome\(\)\.catch[^\n]*\n?/, "");
const mainHtml = html.match(/<main[\s\S]*<\/main>/)[0];

function loadApp() {
  document.body.innerHTML = mainHtml;
  window.Telegram = { WebApp: { initData: "INIT", platform: "ios", version: "7.2", ready() {}, expand() {} } };
  const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: async () => ({ ok: true }) }));
  global.fetch = fetchMock;
  const factory = new Function("window", "document", "fetch", appSrc + "\n; return { showReport, show };");
  return { app: factory(window, document, fetchMock), fetchMock };
}

describe("report screen", () => {
  it("POSTs the entered text with the init-data header", async () => {
    const { app, fetchMock } = loadApp();
    app.showReport();
    document.getElementById("report-text").value = "زر لا يعمل";
    document.getElementById("report-send").click();
    await Promise.resolve();
    const call = fetchMock.mock.calls.find((c) => String(c[0]).includes("/api/report"));
    expect(call).toBeTruthy();
    expect(call[1].headers["X-Init-Data"]).toBe("INIT");
    expect(JSON.parse(call[1].body).text).toBe("زر لا يعمل");
  });
});
