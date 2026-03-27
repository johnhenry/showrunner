# tests/test_render_pillow.py
from pathlib import Path

import pytest

from showrunner.providers.render.pillow import PillowRenderProvider
from showrunner.providers.render.base import RenderProvider


def test_pillow_is_render_provider():
    assert issubclass(PillowRenderProvider, RenderProvider)


def test_setup_creates_directories(tmp_path):
    provider = PillowRenderProvider()
    work_dir = tmp_path / "work"
    provider.setup(work_dir)
    assert (work_dir / "images").is_dir()
    assert (work_dir / "pages").is_dir()


def _make_test_png(path: Path, w=100, h=100, color=(255, 0, 0)):
    from PIL import Image
    img = Image.new("RGB", (w, h), color)
    img.save(path)


def test_render_pdf(tmp_path):
    provider = PillowRenderProvider(output_format="pdf")
    work_dir = tmp_path / "work"
    (work_dir / "pages").mkdir(parents=True)

    _make_test_png(work_dir / "pages" / "page_001.png")
    _make_test_png(work_dir / "pages" / "page_002.png", color=(0, 255, 0))

    output = tmp_path / "out.pdf"
    result = provider.render(work_dir=work_dir, output_path=output)
    assert result.suffix == ".pdf"
    assert result.exists()
    assert result.stat().st_size > 0


def test_render_png_sequence(tmp_path):
    provider = PillowRenderProvider(output_format="png")
    work_dir = tmp_path / "work"
    (work_dir / "pages").mkdir(parents=True)

    _make_test_png(work_dir / "pages" / "page_001.png")
    _make_test_png(work_dir / "pages" / "page_002.png")

    output = tmp_path / "out.pdf"
    result = provider.render(work_dir=work_dir, output_path=output)
    assert result.is_dir()
    assert len(list(result.glob("*.png"))) == 2


def test_render_both(tmp_path):
    provider = PillowRenderProvider(output_format="both")
    work_dir = tmp_path / "work"
    (work_dir / "pages").mkdir(parents=True)

    _make_test_png(work_dir / "pages" / "page_001.png")

    output = tmp_path / "out.pdf"
    result = provider.render(work_dir=work_dir, output_path=output)
    assert result.suffix == ".pdf"
    assert result.exists()
    # PNG dir should also exist
    png_dir = tmp_path / "out_images"
    assert png_dir.is_dir()


def test_render_no_images_raises(tmp_path):
    provider = PillowRenderProvider()
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "pages").mkdir()
    (work_dir / "images").mkdir()

    with pytest.raises(RuntimeError, match="No images"):
        provider.render(work_dir=work_dir, output_path=tmp_path / "out.pdf")


def test_render_falls_back_to_images_dir(tmp_path):
    provider = PillowRenderProvider(output_format="pdf")
    work_dir = tmp_path / "work"
    (work_dir / "pages").mkdir(parents=True)
    (work_dir / "images").mkdir(parents=True)

    # No pages, but images exist
    _make_test_png(work_dir / "images" / "scene_1.png")

    output = tmp_path / "out.pdf"
    result = provider.render(work_dir=work_dir, output_path=output)
    assert result.exists()
