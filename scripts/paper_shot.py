"""Make a real screenshot of a paragraph from an open-access paper PDF.

Given a PDF and a text snippet, find the paragraph by word bounding boxes, render
its page, highlight the matched region, and crop to it. Produces a real "screenshot
of a paper paragraph" for applied questions.

Usage (library): from paper_shot import shoot; shoot(pdf, "first words of paragraph", out_png)
"""
import html
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw


def _blocks_by_page(pdf):
    """Return [{w,h,blocks:[[(x0,y0,x1,y1,text),...], ...]}] from pdftotext -bbox-layout.

    Each <block> is roughly a paragraph."""
    xml = subprocess.check_output(["pdftotext", "-bbox-layout", pdf, "-"]).decode("utf-8", "replace")
    pages = []
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S):
        w, h, body = float(pm.group(1)), float(pm.group(2)), pm.group(3)
        blocks = []
        for bm in re.finditer(r'<block[^>]*>(.*?)</block>', body, re.S):
            words = [(float(a), float(b), float(c), float(d), html.unescape(t))
                     for a, b, c, d, t in re.findall(
                         r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',
                         bm.group(1), re.S)]
            if words:
                blocks.append(words)
        pages.append({"w": w, "h": h, "blocks": blocks})
    return pages


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _find(pages, snippet):
    """Find the paragraph block containing the snippet; return (page_index, bbox in pts)."""
    key = _norm(snippet)
    for pi, pg in enumerate(pages):
        for block in pg["blocks"]:
            text = _norm(" ".join(w[4] for w in block))
            if key in text:
                xs0 = min(w[0] for w in block); ys0 = min(w[1] for w in block)
                xs1 = max(w[2] for w in block); ys1 = max(w[3] for w in block)
                return pi, (xs0, ys0, xs1, ys1)
    return None


def shoot(pdf, snippet, out_png, dpi=170, margin=16, pad_lines=2):
    pages = _blocks_by_page(pdf)
    hit = _find(pages, snippet)
    if not hit:
        raise SystemExit(f"snippet not found: {snippet[:40]!r}")
    pi, (x0, y0, x1, y1) = hit
    pg = pages[pi]
    scale = dpi / 72.0
    # render the page
    prefix = out_png + ".page"
    subprocess.check_call(["pdftoppm", "-f", str(pi + 1), "-l", str(pi + 1), "-r", str(dpi), "-png", pdf, prefix])
    page_png = next(f for f in (f"{prefix}-{pi+1}.png", f"{prefix}-{pi+1:02d}.png", f"{prefix}-{pi+1:03d}.png") if os.path.exists(f))
    img = Image.open(page_png).convert("RGB")
    # widen the box to the text column and pad vertically a little
    bx0 = max(0, int(x0 * scale) - margin)
    by0 = max(0, int(y0 * scale) - margin)
    bx1 = min(img.width, int(x1 * scale) + margin)
    by1 = min(img.height, int(y1 * scale) + margin + int(pad_lines * 12 * scale / 12))
    # highlight overlay
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([bx0, by0, bx1, by1], fill=(255, 210, 60, 70), outline=(255, 160, 0, 255), width=3)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    crop = img.crop((bx0 - margin, by0 - margin, bx1 + margin, by1 + margin))
    crop.save(out_png)
    os.remove(page_png)
    print(f"wrote {out_png} ({crop.width}x{crop.height}) from page {pi+1}")


if __name__ == "__main__":
    shoot(sys.argv[1], sys.argv[2], sys.argv[3])
