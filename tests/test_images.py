# tests/test_images.py
"""Tests for user-provided image matching and loading."""
from pathlib import Path

import pytest

from showrunner.images import load_user_images, _find_scene_match
from showrunner.plan import Plan, Scene


def _make_plan(*scene_ids):
    return Plan(
        title="Test", total_duration=0,
        scenes=[Scene(id=sid, duration=0, narration="N", visual="V") for sid in scene_ids],
    )


def _touch(path: Path, content=b"fake-image"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class TestFindSceneMatch:
    def test_exact_match(self):
        assert _find_scene_match("hook", ["hook", "main"], {}) == "hook"

    def test_case_insensitive(self):
        assert _find_scene_match("Hook", ["hook", "main"], {}) == "hook"

    def test_underscore_collapse(self):
        assert _find_scene_match("solarsystem", ["solar_system", "mars"], {}) == "solar_system"

    def test_no_match(self):
        assert _find_scene_match("unknown", ["hook", "main"], {}) is None

    def test_skips_already_matched(self):
        assert _find_scene_match("hook", ["hook", "main"], {"hook": Path("/x")}) is None


class TestLoadUserImages:
    def test_match_by_name(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "hook.png")
        _touch(images_dir / "main.jpg")

        plan = _make_plan("hook", "main", "outro")
        output_dir = tmp_path / "output"

        result = load_user_images(images_dir, plan, output_dir)

        assert "hook" in result
        assert "main" in result
        assert "outro" not in result
        assert result["hook"].exists()
        assert result["main"].exists()

    def test_match_by_order(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "001.png")
        _touch(images_dir / "002.png")

        plan = _make_plan("intro", "body")
        output_dir = tmp_path / "output"

        result = load_user_images(images_dir, plan, output_dir)

        assert "intro" in result
        assert "body" in result

    def test_name_match_takes_priority(self, tmp_path):
        """Named files match first, remaining match by order."""
        images_dir = tmp_path / "input"
        _touch(images_dir / "001.png")  # no name match → order
        _touch(images_dir / "outro.png")  # name match

        plan = _make_plan("intro", "outro")
        output_dir = tmp_path / "output"

        result = load_user_images(images_dir, plan, output_dir)

        assert "outro" in result
        # 001.png should match "intro" by order (it's the only remaining)
        assert "intro" in result

    def test_mixed_name_and_order(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "hook.png")
        _touch(images_dir / "background_001.png")
        _touch(images_dir / "background_002.png")

        plan = _make_plan("hook", "middle", "end")
        output_dir = tmp_path / "output"

        result = load_user_images(images_dir, plan, output_dir)

        assert "hook" in result
        assert "middle" in result  # background_001 by order
        assert "end" in result     # background_002 by order

    def test_empty_directory(self, tmp_path):
        images_dir = tmp_path / "input"
        images_dir.mkdir()

        plan = _make_plan("hook")
        result = load_user_images(images_dir, plan, tmp_path / "output")

        assert result == {}

    def test_nonexistent_directory(self, tmp_path):
        plan = _make_plan("hook")
        with pytest.raises(ValueError, match="does not exist"):
            load_user_images(tmp_path / "nope", plan, tmp_path / "output")

    def test_more_images_than_scenes(self, tmp_path):
        images_dir = tmp_path / "input"
        for i in range(5):
            _touch(images_dir / f"{i:03d}.png")

        plan = _make_plan("a", "b")
        result = load_user_images(images_dir, plan, tmp_path / "output")

        assert len(result) == 2

    def test_fewer_images_than_scenes(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "001.png")

        plan = _make_plan("a", "b", "c")
        result = load_user_images(images_dir, plan, tmp_path / "output")

        assert len(result) == 1
        assert "a" in result

    def test_filters_non_image_files(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "readme.txt")
        _touch(images_dir / "data.json")
        _touch(images_dir / "hook.png")

        plan = _make_plan("hook", "main")
        result = load_user_images(images_dir, plan, tmp_path / "output")

        assert len(result) == 1
        assert "hook" in result

    def test_hyphenated_filename_matches_underscore_scene(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "solar-system.png")

        plan = _make_plan("solar_system")
        result = load_user_images(images_dir, plan, tmp_path / "output")

        assert "solar_system" in result

    def test_copies_to_output_dir(self, tmp_path):
        images_dir = tmp_path / "input"
        _touch(images_dir / "hook.png", content=b"original-bytes")

        plan = _make_plan("hook")
        output_dir = tmp_path / "output"
        result = load_user_images(images_dir, plan, output_dir)

        assert result["hook"].parent == output_dir
        assert result["hook"].read_bytes() == b"original-bytes"
