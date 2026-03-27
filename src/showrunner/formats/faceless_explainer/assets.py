"""Asset generation: scene code (TSX) + TTS narration + optional images."""

from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from showrunner.plan import Plan, Scene
from showrunner.providers.tts.base import TTSProvider

MAX_RETRIES = 3

CODEGEN_SYSTEM_PROMPT = """You are a React/Remotion developer. Generate a single React component for a video scene.

RULES:
- Export default a single React component
- Use ONLY these Remotion imports: useCurrentFrame, useVideoConfig, interpolate, spring, Sequence, AbsoluteFill, Img, staticFile
- Canvas size: {width}x{height} pixels at {fps}fps
- Scene duration: {duration_frames} frames ({duration}s)
- DO NOT import Easing — it does not exist in Remotion v4
- Use spring() for easing effects instead
- interpolate() input and output ranges MUST have the same length
- Always use extrapolateLeft: "clamp", extrapolateRight: "clamp" with interpolate()

MOBILE-FIRST DESIGN:
- Title text: 64-84px minimum
- Body text: 32-48px minimum
- Keep 60px safe zone padding on all sides
- High contrast — test against the background color
- Center-align most content vertically and horizontally

ANIMATION PATTERNS (use these):
- Fade in: interpolate(frame, [0, 15], [0, 1])
- Counting numbers: Math.round(interpolate(frame, [0, duration], [0, targetValue]))
- Bar chart growth: interpolate(frame, [start, end], [0, maxHeight])
- Text reveal: opacity + translateY entrance
- List stagger: each item fades in with a delay
- Emphasis pulse: scale spring after delay
- Circle/ring chart: strokeDashoffset animation

STYLE CONTEXT:
{style_context}

Return ONLY the TSX code inside a single code fence. No explanations."""

CODEGEN_IMAGE_ADDENDUM = """
SCENE IMAGE AVAILABLE:
An image is available for this scene at: staticFile("images/{image_filename}")
Use Remotion's Img component to reference it: <Img src={{staticFile("images/{image_filename}")}} />

The "Visual description" below tells you HOW to use this image in the scene.
Follow those instructions for placement, sizing, animation, and compositing.

Common patterns you can use:
- Full-bleed background: position absolute, top/left 0, width/height 100%, objectFit "cover"
- Inset/thumbnail: fixed size, positioned in a corner or region of the canvas
- Ken Burns: animate transform scale from 1.0 to 1.05 over the scene duration
- Reveal: animate clip-path or opacity to reveal the image progressively
- Side-by-side: image on one half, text/graphics on the other

If the visual description does NOT specify how to use the image, default to:
- Full-bleed background with objectFit "cover"
- Semi-transparent dark overlay (rgba(0,0,0,0.5)) for text readability
- Subtle Ken Burns zoom (scale 1.0 → 1.05)

IMPORTANT:
- Do NOT generate procedural backgrounds when an image is available — use the image
- Ensure strong contrast for any text overlaid on the image (text shadows, backdrop panels)
"""

CODEGEN_USER_TEMPLATE = """Create a Remotion scene component.

Scene ID: {scene_id}
Component name: {component_name}
Duration: {duration} seconds ({duration_frames} frames at {fps}fps)
Canvas: {width}x{height}

Narration (what's being said): {narration}
Visual description (what to animate): {visual}

Return the complete TSX component."""


def _extract_code(text: str) -> str:
    """Extract TSX code from markdown fences."""
    match = re.search(r"```(?:tsx|typescript|jsx)?\s*\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def generate_scene_code(
    *,
    scene: Scene,
    style_context: str,
    llm: object,
    validate_fn: Callable[[str], tuple[bool, str]],
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    quiet: bool = False,
    image_filename: str | None = None,
) -> str:
    """Generate and validate TSX code for a single scene. Retries on failure."""
    component_name = "".join(w.capitalize() for w in scene.id.split("_"))
    duration_frames = scene.duration * fps

    system = CODEGEN_SYSTEM_PROMPT.format(
        width=width, height=height, fps=fps,
        duration_frames=duration_frames, duration=scene.duration,
        style_context=style_context,
    )

    if image_filename:
        system += CODEGEN_IMAGE_ADDENDUM.format(image_filename=image_filename)

    prompt = CODEGEN_USER_TEMPLATE.format(
        scene_id=scene.id,
        component_name=component_name,
        duration=scene.duration,
        duration_frames=duration_frames,
        fps=fps,
        width=width,
        height=height,
        narration=scene.narration,
        visual=scene.visual,
    )

    for attempt in range(MAX_RETRIES + 1):
        response = llm.generate(system=system, prompt=prompt, max_tokens=4096)
        code = _extract_code(response)

        ok, error = validate_fn(code)
        if ok:
            return code

        if attempt < MAX_RETRIES:
            if not quiet:
                print(f"    Validation failed (attempt {attempt + 1}), retrying...")
            prompt = (
                f"Previous code had errors. Fix them.\n\n"
                f"Error:\n{error}\n\n"
                f"Previous code:\n```tsx\n{code}\n```\n\n"
                f"Common fixes:\n"
                f"- interpolate() input/output ranges must have same length\n"
                f"- Do NOT import Easing (not available in Remotion v4)\n"
                f"- Use spring() for easing instead\n"
                f"- Ensure all variables are defined before use\n"
            )

    raise RuntimeError(f"Scene '{scene.id}' failed validation after {MAX_RETRIES} retries:\n{error}")


def generate_all_scene_code(
    *,
    plan: Plan,
    style_context: str,
    llm: object,
    write_fn: Callable[[str, str], Path],
    validate_fn: Callable[[str], tuple[bool, str]],
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    parallel: bool = False,
    scene_images: dict[str, Path] | None = None,
) -> None:
    """Generate TSX code for all scenes."""
    total = len(plan.scenes)
    scene_images = scene_images or {}

    if parallel:
        _generate_parallel(
            plan=plan, style_context=style_context, llm=llm,
            write_fn=write_fn, validate_fn=validate_fn,
            width=width, height=height, fps=fps, total=total,
            scene_images=scene_images,
        )
    else:
        for i, scene in enumerate(plan.scenes, 1):
            img_path = scene_images.get(scene.id)
            img_filename = img_path.name if img_path else None
            print(f"  [{i}/{total}] Generating {scene.id}{'  (with image)' if img_filename else ''}...")
            code = generate_scene_code(
                scene=scene, style_context=style_context, llm=llm,
                validate_fn=validate_fn, width=width, height=height, fps=fps,
                image_filename=img_filename,
            )
            write_fn(scene.id, code)


def _generate_parallel(*, plan, style_context, llm, write_fn, validate_fn, width, height, fps, total, scene_images):
    errors = []
    with ThreadPoolExecutor(max_workers=min(4, total)) as pool:
        futures = {}
        for i, scene in enumerate(plan.scenes, 1):
            img_path = scene_images.get(scene.id)
            img_filename = img_path.name if img_path else None
            future = pool.submit(
                _generate_and_write,
                scene=scene, style_context=style_context, llm=llm,
                write_fn=write_fn, validate_fn=validate_fn,
                width=width, height=height, fps=fps, index=i, total=total,
                image_filename=img_filename,
            )
            futures[future] = scene
        for future in as_completed(futures):
            try:
                future.result()
            except RuntimeError as e:
                errors.append(str(e))
    if errors:
        raise RuntimeError(f"{len(errors)} scene(s) failed:\n" + "\n".join(errors))


def _generate_and_write(*, scene, style_context, llm, write_fn, validate_fn, width, height, fps, index, total, image_filename=None):
    code = generate_scene_code(
        scene=scene, style_context=style_context, llm=llm,
        validate_fn=validate_fn, width=width, height=height, fps=fps, quiet=True,
        image_filename=image_filename,
    )
    write_fn(scene.id, code)
    print(f"  [{index}/{total}] {scene.id} done")


def generate_scene_images(
    plan: Plan,
    *,
    image: object,
    output_dir: Path,
    width: int = 1080,
    height: int = 1920,
    parallel: bool = False,
) -> dict[str, Path]:
    """Generate background images for all scenes. Returns {scene_id: image_path}."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(plan.scenes)
    size = f"{width}x{height}"

    # Map to aspect ratio string for providers that use it
    ratio = "9:16" if height > width else "16:9" if width > height else "1:1"

    if parallel:
        return _generate_images_parallel(
            plan, image=image, output_dir=output_dir,
            size=size, aspect_ratio=ratio, total=total,
        )

    images = {}
    for i, scene in enumerate(plan.scenes, 1):
        print(f"  [{i}/{total}] Generating image: {scene.id}...")
        img_path = output_dir / f"{scene.id}.png"
        image.generate(
            scene.visual,
            size=size, aspect_ratio=ratio, output_path=img_path,
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
                print(f"  [{index}/{total}] {scene.id} image done")
            except Exception as e:
                errors.append(f"{scene.id}: {e}")
    if errors:
        raise RuntimeError(f"{len(errors)} image(s) failed:\n" + "\n".join(errors))
    return images


def generate_all_narrations(
    plan: Plan,
    *,
    tts: TTSProvider,
    output_dir: Path,
    voice: str = "af_heart",
    speed: float = 1.0,
) -> dict[str, float]:
    """Generate TTS narration for all scenes. Returns {scene_id: duration}."""
    durations = {}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for scene in plan.scenes:
        output_path = output_dir / f"{scene.id}.wav"
        result = tts.synthesize(scene.narration, output_path=output_path, voice=voice, speed=speed)
        durations[scene.id] = result.duration
        # Extend scene if audio is longer
        if result.duration > scene.duration:
            scene.duration = math.ceil(result.duration) + 1

    plan.total_duration = sum(s.duration for s in plan.scenes)
    return durations
