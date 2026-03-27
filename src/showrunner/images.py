"""User-provided image matching and loading for scene backgrounds."""

from __future__ import annotations

import shutil
from pathlib import Path

from showrunner.plan import Plan

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def load_user_images(
    images_dir: Path,
    plan: Plan,
    output_dir: Path,
) -> dict[str, Path]:
    """Match user-provided images to scenes and copy to output_dir.

    Matching strategy (in priority order):
    1. By filename: "hook.png" matches scene with id "hook"
    2. By numeric order: "001.png", "002.png" match scenes in plan order

    Returns {scene_id: output_path} for matched scenes.
    """
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not images_dir.is_dir():
        raise ValueError(f"Images directory does not exist: {images_dir}")

    # Collect image files
    image_files = sorted(
        f for f in images_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        return {}

    scene_ids = [s.id for s in plan.scenes]
    matched: dict[str, Path] = {}

    # Pass 1: Match by stem name (e.g. "hook.png" → scene "hook")
    remaining_files = []
    for img_file in image_files:
        stem = img_file.stem.lower().replace("-", "_")
        match = _find_scene_match(stem, scene_ids, matched)
        if match:
            dest = output_dir / f"{match}{img_file.suffix}"
            shutil.copy2(img_file, dest)
            matched[match] = dest
        else:
            remaining_files.append(img_file)

    # Pass 2: Match remaining files by order to unmatched scenes
    unmatched_scenes = [sid for sid in scene_ids if sid not in matched]
    for img_file, scene_id in zip(remaining_files, unmatched_scenes):
        dest = output_dir / f"{scene_id}{img_file.suffix}"
        shutil.copy2(img_file, dest)
        matched[scene_id] = dest

    return matched


def _find_scene_match(stem: str, scene_ids: list[str], already_matched: dict) -> str | None:
    """Find a scene ID that matches the given filename stem."""
    stem_lower = stem.lower().replace("-", "_")
    for sid in scene_ids:
        if sid in already_matched:
            continue
        sid_lower = sid.lower()
        # Exact match
        if stem_lower == sid_lower:
            return sid
        # Match without underscores (e.g. "solarsystem" matches "solar_system")
        if stem_lower.replace("_", "") == sid_lower.replace("_", ""):
            return sid
    return None
