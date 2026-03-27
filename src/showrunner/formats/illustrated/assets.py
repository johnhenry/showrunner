"""Asset generation for illustrated format: image generation + optional TTS."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from showrunner.plan import Plan
from showrunner.providers.image.base import ImageProvider


def generate_all_images(
    plan: Plan,
    *,
    image: ImageProvider,
    output_dir: Path,
    size: str = "1024x1024",
    aspect_ratio: str = "1:1",
    parallel: bool = False,
) -> dict[str, Path]:
    """Generate images for all scenes. Returns {scene_id: image_path}."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(plan.scenes)

    if parallel:
        return _generate_images_parallel(
            plan, image=image, output_dir=output_dir,
            size=size, aspect_ratio=aspect_ratio, total=total,
        )

    images = {}
    for i, scene in enumerate(plan.scenes, 1):
        print(f"  [{i}/{total}] Generating image: {scene.id}...")
        img_path = output_dir / f"{scene.id}.png"
        image.generate(
            scene.visual,
            size=size,
            aspect_ratio=aspect_ratio,
            output_path=img_path,
        )
        images[scene.id] = img_path
    return images


def _generate_images_parallel(plan, *, image, output_dir, size, aspect_ratio, total):
    images = {}
    errors = []
    with ThreadPoolExecutor(max_workers=min(3, total)) as pool:
        futures = {}
        for i, scene in enumerate(plan.scenes, 1):
            img_path = output_dir / f"{scene.id}.png"
            future = pool.submit(
                image.generate, scene.visual,
                size=size, aspect_ratio=aspect_ratio, output_path=img_path,
            )
            futures[future] = (scene, img_path, i)

        for future in as_completed(futures):
            scene, img_path, index = futures[future]
            try:
                future.result()
                images[scene.id] = img_path
                print(f"  [{index}/{total}] {scene.id} done")
            except Exception as e:
                errors.append(f"{scene.id}: {e}")

    if errors:
        raise RuntimeError(f"{len(errors)} image(s) failed:\n" + "\n".join(errors))
    return images
