"""OpenAI image generation provider (gpt-image-1 / DALL-E 3)."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from showrunner.providers.image.base import ImageProvider

SUPPORTED_SIZES = {
    "1024x1024",
    "1024x1536",
    "1536x1024",
    "auto",
}

ASPECT_TO_SIZE = {
    "1:1": "1024x1024",
    "9:16": "1024x1536",
    "16:9": "1536x1024",
    "4:5": "1024x1536",
}


class OpenAIImageProvider(ImageProvider):
    """OpenAI image generation via gpt-image-1."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-image-1",
        quality: str = "auto",
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY or pass api_key="
            )
        self._model = model
        self._quality = quality

        from openai import OpenAI

        self._client = OpenAI(api_key=self._api_key)

    def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        aspect_ratio: str = "1:1",
        output_path: Path,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        resolved_size = ASPECT_TO_SIZE.get(aspect_ratio, size)
        if resolved_size not in SUPPORTED_SIZES:
            resolved_size = "auto"

        result = self._client.images.generate(
            model=self._model,
            prompt=prompt,
            n=1,
            size=resolved_size,
            quality=self._quality,
        )

        image_data = result.data[0]

        if image_data.b64_json:
            img_bytes = base64.b64decode(image_data.b64_json)
            output_path.write_bytes(img_bytes)
        elif image_data.url:
            import httpx

            resp = httpx.get(image_data.url, timeout=60)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
        else:
            raise RuntimeError("OpenAI returned no image data")

        return output_path
