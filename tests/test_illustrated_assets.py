# tests/test_illustrated_assets.py
from unittest.mock import MagicMock
from pathlib import Path

from showrunner.formats.illustrated.assets import generate_all_images
from showrunner.plan import Plan, Scene


def _make_fake_image_provider():
    mock = MagicMock()
    def fake_generate(prompt, *, size, aspect_ratio, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-image-bytes")
        return output_path
    mock.generate.side_effect = fake_generate
    return mock


def test_generate_all_images_sequential(tmp_path):
    plan = Plan(
        title="Test", total_duration=0,
        scenes=[
            Scene(id="s1", duration=0, narration="N", visual="V1"),
            Scene(id="s2", duration=0, narration="N", visual="V2"),
        ],
    )
    provider = _make_fake_image_provider()
    result = generate_all_images(plan, image=provider, output_dir=tmp_path)

    assert len(result) == 2
    assert "s1" in result
    assert "s2" in result
    assert provider.generate.call_count == 2


def test_generate_all_images_parallel(tmp_path):
    plan = Plan(
        title="Test", total_duration=0,
        scenes=[
            Scene(id="s1", duration=0, narration="N", visual="V1"),
            Scene(id="s2", duration=0, narration="N", visual="V2"),
        ],
    )
    provider = _make_fake_image_provider()
    result = generate_all_images(plan, image=provider, output_dir=tmp_path, parallel=True)

    assert len(result) == 2
    assert provider.generate.call_count == 2


def test_generate_images_passes_size_and_ratio(tmp_path):
    plan = Plan(
        title="Test", total_duration=0,
        scenes=[Scene(id="s1", duration=0, narration="N", visual="A sunset")],
    )
    provider = _make_fake_image_provider()
    generate_all_images(
        plan, image=provider, output_dir=tmp_path,
        size="1536x1024", aspect_ratio="16:9",
    )

    call_kwargs = provider.generate.call_args
    assert call_kwargs.kwargs["size"] == "1536x1024"
    assert call_kwargs.kwargs["aspect_ratio"] == "16:9"
