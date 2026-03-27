# tests/test_text_overlay.py
from pathlib import Path

from PIL import Image

from showrunner.formats.illustrated.text_overlay import overlay_caption, _wrap_text, _load_font


def _make_test_png(path: Path, w=400, h=400):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), (128, 128, 128))
    img.save(path)


def test_overlay_caption_bottom(tmp_path):
    src = tmp_path / "src.png"
    out = tmp_path / "out.png"
    _make_test_png(src)

    result = overlay_caption(src, "Hello world", out, position="bottom")
    assert result == out
    assert out.exists()
    img = Image.open(out)
    assert img.size == (400, 400)


def test_overlay_caption_top(tmp_path):
    src = tmp_path / "src.png"
    out = tmp_path / "out.png"
    _make_test_png(src)

    result = overlay_caption(src, "Top caption", out, position="top")
    assert result == out
    assert out.exists()


def test_overlay_empty_text(tmp_path):
    src = tmp_path / "src.png"
    out = tmp_path / "out.png"
    _make_test_png(src)

    result = overlay_caption(src, "", out)
    assert result == out


def test_wrap_text():
    from PIL import ImageDraw
    img = Image.new("RGB", (400, 400))
    draw = ImageDraw.Draw(img)
    font = _load_font(28)
    lines = _wrap_text(draw, "This is a long sentence that should wrap across multiple lines", font, 200)
    assert len(lines) >= 2


def test_load_font():
    font = _load_font(24)
    assert font is not None
