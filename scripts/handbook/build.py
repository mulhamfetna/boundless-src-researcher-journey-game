#!/usr/bin/env python3
"""Build the player handbook: one self-contained HTML file, and a PDF.

The handbook is meant to be forwarded — sent in a group, attached to an email,
printed. That only works if it is a single file with nothing to fetch: a page
whose screenshots live next to it arrives broken the moment it is moved, and one
that pulls fonts from a CDN renders in the wrong typeface for anyone offline and
leaks a request for everyone else.

So this script inlines everything:

  * screenshots from docs/launch/assets/*.png, resized and re-encoded to WebP
    (a 780px-wide PNG is ~1MB; at the size it is actually shown, WebP is ~32KB,
    and the whole document lands under a megabyte),
  * the two Arabic typefaces, as base64 woff2.

Placeholders in handbook.src.html:
    {{SHOT:screen-map}}     -> a data: URI for that screenshot
    {{FONT:Cairo-arabic}}   -> a data: URI for that font file

Usage:
    python scripts/handbook/build.py            # HTML + PDF
    python scripts/handbook/build.py --no-pdf   # HTML only
"""
import argparse
import base64
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "docs" / "handbook-player" / "handbook.src.html"
OUT_HTML = REPO / "docs" / "handbook-player" / "player-handbook.html"
OUT_PDF = REPO / "docs" / "handbook-player" / "player-handbook.pdf"
SHOTS = REPO / "docs" / "launch" / "assets"
FONTS = REPO / "frontend" / "fonts"

# Wide enough to read a screenshot's headline in print, small enough that the
# whole handbook stays a comfortable email attachment.
SHOT_WIDTH = 440
CHROME_CANDIDATES = [
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
]


def data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def webp_shot(name: str) -> str:
    png = SHOTS / f"{name}.png"
    if not png.exists():
        raise SystemExit(f"missing screenshot: {png}\nRun scripts/capture/run.sh --scene screens")
    with tempfile.TemporaryDirectory() as tmp:
        webp = Path(tmp) / f"{name}.webp"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(png),
             "-vf", f"scale={SHOT_WIDTH}:-2", "-quality", "82", str(webp)],
            check=True,
        )
        return data_uri(webp.read_bytes(), "image/webp")


def font_uri(name: str) -> str:
    f = FONTS / f"{name}.woff2"
    if not f.exists():
        raise SystemExit(f"missing font: {f}")
    return data_uri(f.read_bytes(), "font/woff2")


def find_chrome() -> str | None:
    return next((c for c in CHROME_CANDIDATES if Path(c).exists()), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()

    html = SRC.read_text(encoding="utf-8")
    shots = sorted(set(re.findall(r"\{\{SHOT:([a-z0-9-]+)\}\}", html)))
    fonts = sorted(set(re.findall(r"\{\{FONT:([A-Za-z0-9-]+)\}\}", html)))

    for n in shots:
        html = html.replace(f"{{{{SHOT:{n}}}}}", webp_shot(n))
    for n in fonts:
        html = html.replace(f"{{{{FONT:{n}}}}}", font_uri(n))

    leftover = re.findall(r"\{\{[A-Z]+:[^}]+\}\}", html)
    if leftover:
        raise SystemExit(f"unresolved placeholders: {sorted(set(leftover))}")

    OUT_HTML.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    print(f"wrote {OUT_HTML.relative_to(REPO)}  ({kb:.0f} KB, {len(shots)} screenshots, {len(fonts)} fonts)")

    if args.no_pdf:
        return 0
    chrome = find_chrome()
    if not chrome:
        print("no Chrome found — skipping the PDF (HTML is complete).")
        return 0

    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([
            chrome, "--headless", "--disable-gpu", "--no-sandbox",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={OUT_PDF}",
            OUT_HTML.as_uri(),
        ], check=True, capture_output=True)
    if not OUT_PDF.exists():
        raise SystemExit("Chrome reported success but produced no PDF")
    print(f"wrote {OUT_PDF.relative_to(REPO)}  ({OUT_PDF.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to re-encode the screenshots")
    sys.exit(main())
