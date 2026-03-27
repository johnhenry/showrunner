"""Abstract image generation provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ImageProvider(ABC):
    """Generate images from text prompts."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        aspect_ratio: str = "1:1",
        output_path: Path,
    ) -> Path:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate.
            size: Image dimensions as "WxH" (e.g. "1024x1024", "1200x1600").
            aspect_ratio: Aspect ratio hint (e.g. "1:1", "16:9", "9:16").
            output_path: Where to save the generated image.

        Returns:
            Path to the saved image file.
        """
