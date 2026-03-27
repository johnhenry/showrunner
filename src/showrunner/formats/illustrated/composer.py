"""Composition engine for illustrated format — single-image and multi-panel layouts."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from showrunner.formats.illustrated.text_overlay import overlay_caption
from showrunner.plan import Plan


# Panel layout presets: number of panels → list of (x, y, w, h) as ratios of page size
PANEL_LAYOUTS = {
    1: [(0.02, 0.02, 0.96, 0.96)],
    2: [
        (0.02, 0.02, 0.96, 0.48),
        (0.02, 0.50, 0.96, 0.48),
    ],
    3: [
        (0.02, 0.02, 0.96, 0.48),
        (0.02, 0.50, 0.48, 0.48),
        (0.50, 0.50, 0.48, 0.48),
    ],
    4: [
        (0.02, 0.02, 0.48, 0.48),
        (0.50, 0.02, 0.48, 0.48),
        (0.02, 0.50, 0.48, 0.48),
        (0.50, 0.50, 0.48, 0.48),
    ],
    5: [
        (0.02, 0.02, 0.60, 0.48),
        (0.62, 0.02, 0.36, 0.48),
        (0.02, 0.50, 0.32, 0.48),
        (0.34, 0.50, 0.32, 0.48),
        (0.66, 0.50, 0.32, 0.48),
    ],
    6: [
        (0.02, 0.02, 0.32, 0.48),
        (0.34, 0.02, 0.32, 0.48),
        (0.66, 0.02, 0.32, 0.48),
        (0.02, 0.50, 0.32, 0.48),
        (0.34, 0.50, 0.32, 0.48),
        (0.66, 0.50, 0.32, 0.48),
    ],
}


def compose_single(
    plan: Plan,
    images: dict[str, Path],
    output_dir: Path,
    *,
    text_overlay: bool = False,
    caption_position: str = "bottom",
) -> list[Path]:
    """One image per scene — optionally overlay narration text.

    Returns list of output image paths in scene order.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = []

    for i, scene in enumerate(plan.scenes):
        img_path = images.get(scene.id)
        if not img_path or not Path(img_path).exists():
            continue

        out_path = output_dir / f"page_{i + 1:03d}.png"

        if text_overlay and scene.narration:
            overlay_caption(
                img_path, scene.narration, out_path,
                position=caption_position,
            )
        else:
            import shutil
            shutil.copy2(img_path, out_path)

        pages.append(out_path)

    return pages


def compose_panels(
    plan: Plan,
    images: dict[str, Path],
    output_dir: Path,
    *,
    panels_per_page: int = 4,
    page_size: tuple[int, int] = (1200, 1600),
    text_overlay: bool = False,
    caption_position: str = "bottom",
    gutter_color: tuple[int, int, int] = (255, 255, 255),
) -> list[Path]:
    """Multi-panel layout — group scenes into pages with grid layouts.

    Returns list of composed page image paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect scene images in order
    scene_images = []
    for scene in plan.scenes:
        img_path = images.get(scene.id)
        if img_path and Path(img_path).exists():
            scene_images.append((scene, img_path))

    # Group into pages
    pages = []
    page_w, page_h = page_size
    ppp = max(1, min(panels_per_page, 6))

    for page_idx in range(0, len(scene_images), ppp):
        batch = scene_images[page_idx:page_idx + ppp]
        n = len(batch)
        layout = PANEL_LAYOUTS.get(n, PANEL_LAYOUTS[min(n, 6)])

        # Create page canvas
        page = Image.new("RGB", (page_w, page_h), gutter_color)

        for (scene, img_path), (rx, ry, rw, rh) in zip(batch, layout):
            panel_x = int(rx * page_w)
            panel_y = int(ry * page_h)
            panel_w = int(rw * page_w)
            panel_h = int(rh * page_h)

            panel_img = Image.open(img_path)
            panel_img = _fit_image(panel_img, panel_w, panel_h)
            page.paste(panel_img, (panel_x, panel_y))

        page_path = output_dir / f"page_{len(pages) + 1:03d}.png"
        page.save(page_path)

        # Overlay captions if requested (on the composed page)
        if text_overlay:
            captions = [s.narration for s, _ in batch if s.narration]
            if captions:
                combined_text = " | ".join(captions)
                overlay_caption(
                    page_path, combined_text, page_path,
                    position=caption_position,
                )

        pages.append(page_path)

    return pages


def _fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize and crop image to exactly fill target dimensions."""
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        # Image is wider — scale by height, crop width
        new_h = target_h
        new_w = int(img_ratio * target_h)
    else:
        # Image is taller — scale by width, crop height
        new_w = target_w
        new_h = int(target_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    return img
