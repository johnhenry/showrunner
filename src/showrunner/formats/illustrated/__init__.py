"""Illustrated format — generates still images or multi-panel pages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from showrunner.feedback import Feedback
from showrunner.formats.base import Format
from showrunner.formats.illustrated.assets import generate_all_images
from showrunner.formats.illustrated.composer import compose_panels, compose_single
from showrunner.formats.illustrated.planner import generate_plan
from showrunner.plan import Plan
class IllustratedFormat(Format):
    """AI-generated still images — single or multi-panel layouts."""

    name = "illustrated"
    description = "AI-generated still images with optional panel layouts and text overlay"
    required_providers = ["llm", "image", "render"]

    def plan(self, topic: str, style: Any, config: Any, llm: Any) -> Plan:
        return generate_plan(topic, style=style, llm=llm, config=config)

    def generate_assets(self, plan: Plan, providers: dict, work_dir: Path) -> dict:
        image = providers["image"]

        aspect_ratio = getattr(self, "_aspect_ratio", "1:1")
        parallel = getattr(self, "_parallel", False)

        # Map aspect ratios to image sizes
        size_map = {
            "1:1": "1024x1024",
            "9:16": "1024x1536",
            "16:9": "1536x1024",
            "4:5": "1024x1280",
        }
        size = size_map.get(aspect_ratio, "1024x1024")

        images_dir = work_dir / "images"
        images = generate_all_images(
            plan, image=image, output_dir=images_dir,
            size=size, aspect_ratio=aspect_ratio, parallel=parallel,
        )

        return {
            "images": images,
            "has_audio": False,
        }

    def compose(self, plan: Plan, assets: dict, work_dir: Path, **kwargs) -> None:
        images = assets.get("images", {})
        pages_dir = work_dir / "pages"

        layout = getattr(self, "_layout", "single")
        text_overlay = kwargs.get("captions", getattr(self, "_text_overlay", False))
        panels_per_page = getattr(self, "_panels_per_page", 4)
        page_size = getattr(self, "_page_size", (1200, 1600))

        if layout == "panels":
            compose_panels(
                plan, images, pages_dir,
                panels_per_page=panels_per_page,
                page_size=page_size,
                text_overlay=text_overlay,
            )
        else:
            compose_single(
                plan, images, pages_dir,
                text_overlay=text_overlay,
            )

    def revise(self, plan: Plan, feedback: Feedback, llm: Any) -> Plan:
        if feedback.edits:
            return Plan.from_dict({**plan.to_dict(), **feedback.edits})
        if feedback.text:
            revised = llm.generate_json(
                system="You are an art director for illustrated content. Revise the storyboard based on feedback. The visual field should be an AI image generation prompt (describe images, not video). Return valid JSON.",
                prompt=f"Current storyboard:\n{plan.to_json()}\n\nFeedback: {feedback.text}\n\nReturn revised JSON.",
            )
            return Plan.from_dict(revised)
        return plan
