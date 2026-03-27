# tests/test_illustrated_format.py
from unittest.mock import MagicMock, patch
from pathlib import Path

from showrunner.formats.illustrated import IllustratedFormat
from showrunner.formats.base import Format
from showrunner.feedback import Feedback
from showrunner.plan import Plan, Scene
from showrunner.styles.resolver import resolve_style


def test_is_format_subclass():
    assert issubclass(IllustratedFormat, Format)


def test_format_metadata():
    fmt = IllustratedFormat()
    assert fmt.name == "illustrated"
    assert "image" in fmt.required_providers
    assert "llm" in fmt.required_providers
    assert "render" in fmt.required_providers


def test_plan_delegates_to_planner():
    fmt = IllustratedFormat()
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "title": "Test", "totalDuration": 0,
        "scenes": [{"id": "intro", "duration": 0, "narration": "N", "visual": "A sunset"}],
    }
    style = resolve_style("dramatic-story")
    plan = fmt.plan("test", style, None, mock_llm)
    assert isinstance(plan, Plan)
    assert plan.scenes[0].visual == "A sunset"


def test_generate_assets_calls_image_provider(tmp_path):
    fmt = IllustratedFormat()
    fmt._aspect_ratio = "1:1"
    fmt._parallel = False

    plan = Plan(
        title="Test", total_duration=0,
        scenes=[Scene(id="intro", duration=0, narration="N", visual="A sunset")],
    )

    mock_image = MagicMock()
    def fake_generate(prompt, *, size, aspect_ratio, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-image")
        return output_path
    mock_image.generate.side_effect = fake_generate

    providers = {"image": mock_image}
    assets = fmt.generate_assets(plan, providers, tmp_path)

    assert "images" in assets
    assert "intro" in assets["images"]
    mock_image.generate.assert_called_once()


def _make_test_png(path: Path, w=100, h=100):
    from PIL import Image
    img = Image.new("RGB", (w, h), (128, 128, 128))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def test_compose_single_layout(tmp_path):
    fmt = IllustratedFormat()
    fmt._layout = "single"
    fmt._text_overlay = False

    plan = Plan(
        title="Test", total_duration=0,
        scenes=[
            Scene(id="s1", duration=0, narration="First", visual="V1"),
            Scene(id="s2", duration=0, narration="Second", visual="V2"),
        ],
    )

    img1 = tmp_path / "images" / "s1.png"
    img2 = tmp_path / "images" / "s2.png"
    _make_test_png(img1)
    _make_test_png(img2)

    assets = {"images": {"s1": img1, "s2": img2}}
    fmt.compose(plan, assets, tmp_path)

    pages = sorted((tmp_path / "pages").glob("*.png"))
    assert len(pages) == 2


def test_compose_panels_layout(tmp_path):
    fmt = IllustratedFormat()
    fmt._layout = "panels"
    fmt._text_overlay = False
    fmt._panels_per_page = 2
    fmt._page_size = (400, 600)

    plan = Plan(
        title="Test", total_duration=0,
        scenes=[
            Scene(id="s1", duration=0, narration="N1", visual="V1"),
            Scene(id="s2", duration=0, narration="N2", visual="V2"),
            Scene(id="s3", duration=0, narration="N3", visual="V3"),
        ],
    )

    for sid in ["s1", "s2", "s3"]:
        _make_test_png(tmp_path / "images" / f"{sid}.png")

    assets = {"images": {
        "s1": tmp_path / "images" / "s1.png",
        "s2": tmp_path / "images" / "s2.png",
        "s3": tmp_path / "images" / "s3.png",
    }}
    fmt.compose(plan, assets, tmp_path)

    pages = sorted((tmp_path / "pages").glob("*.png"))
    assert len(pages) == 2  # 3 scenes / 2 per page = 2 pages


def test_compose_single_with_text_overlay(tmp_path):
    fmt = IllustratedFormat()
    fmt._layout = "single"
    fmt._text_overlay = True

    plan = Plan(
        title="Test", total_duration=0,
        scenes=[Scene(id="s1", duration=0, narration="Hello world", visual="V1")],
    )

    _make_test_png(tmp_path / "images" / "s1.png", w=400, h=400)
    assets = {"images": {"s1": tmp_path / "images" / "s1.png"}}

    fmt.compose(plan, assets, tmp_path, captions=True)
    pages = sorted((tmp_path / "pages").glob("*.png"))
    assert len(pages) == 1


def test_revise_with_text():
    fmt = IllustratedFormat()
    plan = Plan(title="Test", total_duration=0, scenes=[Scene(id="s1", duration=0, narration="N", visual="V")])
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "title": "Revised", "totalDuration": 0,
        "scenes": [{"id": "s1", "duration": 0, "narration": "Better", "visual": "Better image"}],
    }
    feedback = Feedback(level="plan", text="Make more dramatic")
    revised = fmt.revise(plan, feedback, mock_llm)
    assert revised.title == "Revised"


def test_revise_with_edits():
    fmt = IllustratedFormat()
    plan = Plan(title="Test", total_duration=0, scenes=[Scene(id="s1", duration=0, narration="N", visual="V")])
    feedback = Feedback(level="plan", edits={"title": "New Title"})
    revised = fmt.revise(plan, feedback, MagicMock())
    assert revised.title == "New Title"
