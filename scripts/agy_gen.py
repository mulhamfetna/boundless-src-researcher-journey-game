#!/usr/bin/env python3
"""Stable Gemini generation via the Antigravity CLI (`agy`).

Two subcommands:

  image  — generate a raster image with agy's native `generate_image` tool
           (Nano Banana Pro via Antigravity OAuth — no Cloud billing needed),
           harvest the artifact from agy's brain dir, validate/resize, save.
  text   — run a single creative/content prompt non-interactively and print it.

Why this wrapper (see the `agy` skill / memory for the full rationale):
  * `agy -p` is headless; asking it to ONLY call generate_image and NOT run a
    shell keeps it to one tool, so it never trips the run_command permission
    that headless mode auto-denies — no `--dangerously-skip-permissions`.
  * agy writes the artifact to ~/.gemini/antigravity-cli/brain/<uuid>/ (NOT the
    CWD) and sometimes writes JPEG bytes under a .png name, so we sniff the real
    format and copy the file out ourselves.
  * There is a small shared image quota (429 / "exhausted", resets in hours) —
    we detect it and fail fast with a clear message rather than spin.

Examples
--------
  python scripts/agy_gen.py image --prompt "the Tinkerer, brass cogwork, gold rim light" \
      --preset arcane-champion --size 1024 --out content/assets/art/champ.png
  python scripts/agy_gen.py text --model gemini-3.1-pro-high \
      --prompt "اكتب حقيقة ممتعة قصيرة عن معامل التأثير للمجلات، بالعربية"

PIL (Pillow) is optional: with it, images are resized/cropped to --size and
converted to the --out extension; without it, the raw artifact is copied as-is.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

BRAIN_DIR = os.path.expanduser("~/.gemini/antigravity-cli/brain")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
DEFAULT_IMAGE_MODEL = "gemini-3.6-flash-medium"   # flash is enough; quality is backend-fixed
DEFAULT_TEXT_MODEL = "gemini-3.1-pro-high"        # pro for creative content

_MARKER_RE = re.compile(r"IMAGE_PATH:\s*(\S+)", re.IGNORECASE)
_QUOTA_KWS = ("quota", "exhausted", "429", "resource_exhausted")
_TRANSIENT_KWS = _QUOTA_KWS + ("high traffic", "rate limit", "overloaded", "unavailable")


# ---------------------------- pure helpers (unit-tested) ----------------------------

def extract_image_path(stdout: str) -> str | None:
    """Pull the absolute path out of a `IMAGE_PATH: <path>` marker line."""
    m = _MARKER_RE.search(stdout or "")
    return m.group(1) if m else None


def sniff_format(path: str) -> str | None:
    """Return the true image type from magic bytes (handles jpeg-under-.png)."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return None
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


def is_transient_error(text: str) -> bool:
    """True if agy output looks like a retryable/quota failure (not an image)."""
    low = (text or "").lower()
    return any(kw in low for kw in _TRANSIENT_KWS)


def _is_quota(text: str) -> bool:
    low = (text or "").lower()
    return any(kw in low for kw in _QUOTA_KWS)


def build_image_prompt(desc: str, width: int, height: int, style: str | None = None) -> str:
    """Assemble the agy prompt: generate_image only, exact pixels, marker reply."""
    head = (style.strip() + "\n\n") if style else ""
    return (
        f"{head}Use your generate_image tool to create this image:\n{desc}\n\n"
        f"Render it at exactly {width}x{height} pixels. Do NOT run any shell command "
        f"or run_command — ONLY call generate_image. After the image is generated, "
        f"reply with ONLY this single line and nothing else:\n"
        f"IMAGE_PATH: <absolute path to the generated image file>"
    )


# ---------------------------- agy invocation ----------------------------

def _run_agy(prompt: str, model: str, timeout_min: int, extra: list[str] | None = None) -> str:
    cmd = ["agy", "-p", prompt, "--model", model, "--print-timeout", f"{timeout_min}m"]
    if extra:
        cmd += extra
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_min * 60 + 30)
    except subprocess.TimeoutExpired:
        return "ERROR: agy timed out"
    return (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")


def _newest_brain_image(since: float) -> str | None:
    newest, newest_mt = None, since - 5
    for root, _dirs, files in os.walk(BRAIN_DIR):
        for fn in files:
            if fn.lower().endswith(IMG_EXTS):
                p = os.path.join(root, fn)
                try:
                    mt = os.path.getmtime(p)
                except OSError:
                    continue
                if mt >= newest_mt:
                    newest, newest_mt = p, mt
    return newest


def _save_image(src: str, out: str, width: int, height: int) -> dict:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    real = sniff_format(src)
    resized = False
    try:
        from PIL import Image, ImageOps  # optional
        im = Image.open(src).convert("RGB")
        if im.size != (width, height):
            im = ImageOps.fit(im, (width, height))  # crop-to-fill, no distortion
            resized = True
        save_fmt = "PNG" if out.lower().endswith(".png") else "JPEG"
        im.save(out, save_fmt)
    except ImportError:
        shutil.copyfile(src, out)  # no PIL: keep raw bytes
    return {"real_format": real, "resized": resized, "pil": resized or True}


def run_image(args) -> int:
    style = None
    if args.preset and args.preset != "none":
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from gen_art import PRESETS  # reuse the Arcane DNA presets
            style = PRESETS.get(args.preset)
        except Exception:
            style = None
    prompt = build_image_prompt(args.prompt, args.size, args.size, style)

    last = ""
    for attempt in range(args.retries + 1):
        start = time.time()
        out = _run_agy(prompt, args.model, args.timeout)
        last = out
        path = extract_image_path(out)
        if not (path and os.path.isfile(path)):
            path = _newest_brain_image(start)
        if path and os.path.isfile(path) and sniff_format(path):
            info = _save_image(path, args.out, args.size, args.size)
            print(json.dumps({"status": "ok", "out": args.out, "model": args.model,
                              "artifact": path, **info}, ensure_ascii=False))
            return 0
        if _is_quota(out):  # resets in hours — retrying now is futile
            break
        if attempt < args.retries and is_transient_error(out):
            time.sleep(8 * (attempt + 1))
    reason = "quota_exhausted" if _is_quota(last) else "no_image"
    print(json.dumps({"status": "error", "reason": reason,
                      "detail": last.strip()[:400]}, ensure_ascii=False), file=sys.stderr)
    return 1


def run_text(args) -> int:
    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    if not prompt.strip():
        print("ERROR: empty prompt", file=sys.stderr)
        return 2
    out = _run_agy(prompt, args.model, args.timeout, extra=["--sandbox"])
    sys.stdout.write(out.rstrip() + "\n")
    return 1 if is_transient_error(out) else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate images/content via agy (Antigravity CLI).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("image", help="generate a raster image via generate_image")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("--out", required=True, help="output path (repo-relative ok)")
    pi.add_argument("--size", type=int, default=1024, help="square pixel size (default 1024)")
    pi.add_argument("--model", default=DEFAULT_IMAGE_MODEL)
    pi.add_argument("--preset", default="none",
                    help="Arcane DNA preset from gen_art.py (e.g. arcane-bg, arcane-champion)")
    pi.add_argument("--timeout", type=int, default=12, help="agy print-timeout in minutes")
    pi.add_argument("--retries", type=int, default=1, help="retries on transient (non-quota) errors")
    pi.set_defaults(func=run_image)

    pt = sub.add_parser("text", help="run a single content/creative prompt")
    pt.add_argument("--prompt", default=None, help="prompt text (or pipe via stdin)")
    pt.add_argument("--model", default=DEFAULT_TEXT_MODEL)
    pt.add_argument("--timeout", type=int, default=5, help="agy print-timeout in minutes")
    pt.set_defaults(func=run_text)

    args = ap.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
