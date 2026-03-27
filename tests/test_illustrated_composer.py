# tests/test_illustrated_composer.py
from pathlib import Path

from PIL import Image

from showrunner.formats.illustrated.composer import (
    compose_single,
    compose_panels,
    _fit_image,
)
from showrunner.plan import Plan, Scene


def _make_test_png(path: Path, w=200, h=200, color=(128, 128, 128)):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), color)
    img.save(path)


def _make_plan(n_scenes=3):
    return Plan(
        title="Test", total_duration=0,
        scenes=[
            Scene(id=f"s{i}", duration=0, narration=f"Caption {i}", visual=f"V{i}")
            for i in range(1, n_scenes + 1)
        ],
    )


def test_compose_single_basic(tmp_path):
    plan = _make_plan(3)
    images = {}
    for s in plan.scenes:
        p = tmp_path / "images" / f"{s.id}.png"
        _make_test_png(p)
        images[s.id] = p

    pages = compose_single(plan, images, tmp_path / "pages")
    assert len(pages) == 3
    for p in pages:
        assert p.exists()


def test_compose_single_with_overlay(tmp_path):
    plan = _make_plan(1)
    img_path = tmp_path / "images" / "s1.png"
    _make_test_png(img_path, w=400, h=400)

    pages = compose_single(
        plan, {"s1": img_path}, tmp_path / "pages",
        text_overlay=True,
    )
    assert len(pages) == 1


def test_compose_single_skips_missing(tmp_path):
    plan = _make_plan(2)
    img_path = tmp_path / "images" / "s1.png"
    _make_test_png(img_path)

    pages = compose_single(plan, {"s1": img_path}, tmp_path / "pages")
    assert len(pages) == 1  # s2 missing, skipped


def test_compose_panels_basic(tmp_path):
    plan = _make_plan(4)
    images = {}
    for s in plan.scenes:
        p = tmp_path / "images" / f"{s.id}.png"
        _make_test_png(p)
        images[s.id] = p

    pages = compose_panels(
        plan, images, tmp_path / "pages",
        panels_per_page=2, page_size=(400, 600),
    )
    assert len(pages) == 2  # 4 scenes / 2 per page


def test_compose_panels_uneven(tmp_path):
    plan = _make_plan(5)
    images = {}
    for s in plan.scenes:
        p = tmp_path / "images" / f"{s.id}.png"
        _make_test_png(p)
        images[s.id] = p

    pages = compose_panels(
        plan, images, tmp_path / "pages",
        panels_per_page=4, page_size=(800, 1000),
    )
    assert len(pages) == 2  # 4 + 1


def test_compose_panels_with_overlay(tmp_path):
    plan = _make_plan(2)
    images = {}
    for s in plan.scenes:
        p = tmp_path / "images" / f"{s.id}.png"
        _make_test_png(p, w=300, h=300)
        images[s.id] = p

    pages = compose_panels(
        plan, images, tmp_path / "pages",
        panels_per_page=2, page_size=(600, 800),
        text_overlay=True,
    )
    assert len(pages) == 1


def test_fit_image_wider():
    img = Image.new("RGB", (400, 200), (0, 0, 0))
    result = _fit_image(img, 100, 100)
    assert result.size == (100, 100)


def test_fit_image_taller():
    img = Image.new("RGB", (200, 400), (0, 0, 0))
    result = _fit_image(img, 100, 100)
    assert result.size == (100, 100)


def test_fit_image_exact():
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    result = _fit_image(img, 100, 100)
    assert result.size == (100, 100)
