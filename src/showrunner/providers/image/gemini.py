"""Google Gemini (Imagen) image generation provider."""

from __future__ import annotations

import os
from pathlib import Path

from showrunner.providers.image.base import ImageProvider

ASPECT_RATIOS = {"1:1", "9:16", "16:9", "4:3", "3:4"}


class GeminiImageProvider(ImageProvider):
    """Google Gemini — AI image generation via Imagen through google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "imagen-3.0-generate-002",
    ):
        self._api_key = (
            api_key
            or os.environ.get("GOOGLE_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
        )
        if not self._api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY, or pass api_key="
            )
        self._model = model

        from google import genai

        self._client = genai.Client(api_key=self._api_key)

    def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        aspect_ratio: str = "1:1",
        output_path: Path,
    ) -> Path:
        from google.genai import types

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ar = aspect_ratio if aspect_ratio in ASPECT_RATIOS else "1:1"

        response = self._client.models.generate_images(
            model=self._model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=ar,
            ),
        )

        if not response.generated_images:
            raise RuntimeError(f"Gemini Imagen returned no images for prompt: {prompt[:80]}")

        image = response.generated_images[0]
        image_bytes = image.image.image_bytes
        output_path.write_bytes(image_bytes)

        return output_path
