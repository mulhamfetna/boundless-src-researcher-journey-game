"""Unit tests for the pure logic in agy_gen.py (no agy calls, no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agy_gen import (
    extract_image_path,
    sniff_format,
    is_transient_error,
    build_image_prompt,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP_MAGIC = b"RIFF\x00\x00\x00\x00WEBPVP8 "


def test_extract_image_path_marker():
    out = "some chatter\nIMAGE_PATH: /home/u/.gemini/brain/x/apple.jpg\ndone"
    assert extract_image_path(out) == "/home/u/.gemini/brain/x/apple.jpg"


def test_extract_image_path_case_and_spacing():
    assert extract_image_path("image_path:/a/b.png") == "/a/b.png"
    assert extract_image_path("IMAGE_PATH:   /a/c.webp  ") == "/a/c.webp"


def test_extract_image_path_missing():
    assert extract_image_path("no marker, just prose") is None


def test_sniff_format(tmp_path):
    p = tmp_path / "a.png"; p.write_bytes(PNG_MAGIC)
    assert sniff_format(str(p)) == "png"
    j = tmp_path / "b.bin"; j.write_bytes(JPEG_MAGIC)
    assert sniff_format(str(j)) == "jpeg"
    w = tmp_path / "c.bin"; w.write_bytes(WEBP_MAGIC)
    assert sniff_format(str(w)) == "webp"


def test_sniff_format_jpeg_under_png_name(tmp_path):
    # agy sometimes writes JPEG bytes under a .png name — sniff the real type
    f = tmp_path / "actually_jpeg.png"; f.write_bytes(JPEG_MAGIC)
    assert sniff_format(str(f)) == "jpeg"


def test_sniff_format_not_an_image(tmp_path):
    f = tmp_path / "x.txt"; f.write_bytes(b"hello world not an image")
    assert sniff_format(str(f)) is None


def test_is_transient_error():
    assert is_transient_error("image generation failed due to an exhausted quota")
    assert is_transient_error("HTTP 429 Too Many Requests")
    assert is_transient_error("Our servers are experiencing high traffic right now")
    assert is_transient_error("RESOURCE_EXHAUSTED")
    assert not is_transient_error("IMAGE_PATH: /a/b.png")
    assert not is_transient_error("Here is your generated image.")


def test_build_image_prompt_contents():
    p = build_image_prompt("a red apple", 1024, 1024, style="PAINTERLY ARCANE STYLE")
    assert "generate_image" in p
    assert "1024x1024" in p or "1024 x 1024" in p
    assert "IMAGE_PATH:" in p
    assert "a red apple" in p
    assert "PAINTERLY ARCANE STYLE" in p
    # must instruct not to shell out (keeps it to generate_image only, headless-safe)
    assert "shell" in p.lower() or "run_command" in p.lower()


def test_build_image_prompt_no_style():
    p = build_image_prompt("a blue cube", 512, 768, style=None)
    assert "a blue cube" in p
    assert "512x768" in p or "512 x 768" in p
