#!/usr/bin/env python3
"""Generate game art via the Gemini API (Imagen / Gemini-image models).

Reads GEMINI_API_KEY from the environment or the repo-root .env (gitignored).
Stdlib only — no extra dependencies.

Examples
--------
# Painterly Arcane two-world background (uses the built-in style preset):
python scripts/gen_art.py --preset arcane-bg \
    --prompt "vertical scene: Zaun undercity rising to golden Piltover" \
    --out content/assets/art/map_bg.png --aspect 9:16

# A champion portrait token:
python scripts/gen_art.py --preset arcane-champion \
    --prompt "the Tinkerer: goggled inventor, brass cogwork, warm gold" \
    --out content/assets/art/champ_tinkerer.png --aspect 1:1

# Edit / restyle an existing image (Gemini-image models only):
python scripts/gen_art.py --prompt "repaint in Arcane style, magenta shimmer" \
    --ref some_input.png --out out.png

Notes
-----
* Image models require **billing enabled** on the Google Cloud project — the
  Gemini free tier has 0 image quota (HTTP 429). Text still works on free tier.
* Model method is auto-detected: names containing "imagen" use :predict,
  everything else uses :generateContent (inline image parts).
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://generativelanguage.googleapis.com/v1beta/models"

# ---- Arcane visual DNA (kept in sync with docs/superpowers/specs/2026-06-30-arcane-design-dna.md) ----
STYLE = (
    "Painterly digital illustration in the visual style of Netflix's Arcane (Fortiche): "
    "hand-painted oil brush-stroke texture, volumetric god-rays, cinematic moody lighting, "
    "deep contrast and bloom. Two-world palette — luminous Piltover gold (#c8aa6e) with "
    "hextech cyan (#0ac8b9) and art-deco geometry, versus the Zaun undercity's shimmer-magenta "
    "(#ff2e97) and toxic chemtech acid-green (#2fe6a0), smog and grime. No text, no watermarks, no logos."
)
PRESETS = {
    "arcane-bg": STYLE + " Full-bleed atmospheric background, no characters, no UI. Composition reads "
                 "clearly behind dark translucent panels; keep the mid-region calm.",
    "arcane-champion": STYLE + " A single stylized character bust/portrait, centered, facing the viewer, "
                       "strong rim light, plain dark vignette background suitable for a circular token crop.",
    "arcane-banner": STYLE + " A wide dramatic scene banner for a level/station header.",
    "arcane-scene": STYLE + " A rich environmental scene illustration.",
    "none": "",
}


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()
    env = os.path.join(REPO_ROOT, ".env")
    if os.path.isfile(env):
        for line in open(env, encoding="utf-8"):
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("ERROR: GEMINI_API_KEY not set (env or .env).")


def _post(model: str, body: dict, key: str) -> dict:
    method = "predict" if "imagen" in model else "generateContent"
    url = f"{API}/{model}:{method}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:600]
        if e.code == 429:
            sys.exit("ERROR 429: image quota exceeded. The Gemini free tier has 0 image quota — "
                     "enable BILLING on the Google Cloud project to use image models.\n" + detail)
        sys.exit(f"ERROR {e.code}: {detail}")


def gen(model: str, prompt: str, aspect: str, ref: str | None, key: str) -> bytes:
    if "imagen" in model:
        body = {"instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": aspect}}
        d = _post(model, body, key)
        preds = d.get("predictions", [])
        if preds and "bytesBase64Encoded" in preds[0]:
            return base64.b64decode(preds[0]["bytesBase64Encoded"])
        sys.exit(f"No image in response: {json.dumps(d)[:300]}")
    # Gemini-image models (generateContent)
    parts: list = [{"text": f"{prompt}\n\nTarget aspect ratio: {aspect}."}]
    if ref:
        with open(ref, "rb") as f:
            parts.append({"inlineData": {"mimeType": "image/png",
                                         "data": base64.b64encode(f.read()).decode()}})
    body = {"contents": [{"parts": parts}]}
    d = _post(model, body, key)
    cparts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    for p in cparts:
        if "inlineData" in p:
            return base64.b64decode(p["inlineData"]["data"])
    txt = " ".join(p.get("text", "") for p in cparts)
    sys.exit(f"No image returned. Model said: {txt[:300]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate game art via Gemini.")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="output PNG path (repo-relative ok)")
    ap.add_argument("--model", default="gemini-2.5-flash-image",
                    help="e.g. gemini-2.5-flash-image, gemini-3-pro-image, imagen-4.0-generate-001")
    ap.add_argument("--aspect", default="1:1", help="e.g. 1:1, 9:16, 16:9")
    ap.add_argument("--preset", default="none", choices=list(PRESETS))
    ap.add_argument("--ref", default=None, help="optional input image to edit/restyle (Gemini-image only)")
    args = ap.parse_args()

    key = load_key()
    prompt = (PRESETS[args.preset] + "\n\n" + args.prompt).strip()
    out = args.out if os.path.isabs(args.out) else os.path.join(REPO_ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    data = gen(args.model, prompt, args.aspect, args.ref, key)
    with open(out, "wb") as f:
        f.write(data)
    print(f"OK  {out}  ({len(data)} bytes, model={args.model})")


if __name__ == "__main__":
    main()
