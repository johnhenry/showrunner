"""Ollama local image generation provider (Z-Image Turbo / FLUX.2)."""

from __future__ import annotations

import os
from pathlib import Path

from showrunner.providers.image.base import ImageProvider

DEFAULT_HOST = "http://localhost:11434"


class OllamaImageProvider(ImageProvider):
    """Ollama — local image generation via Z-Image Turbo or FLUX.2.

    Requires Ollama with image generation support (currently macOS only,
    Linux support planned). Uses the Ollama HTTP API.
    """

    def __init__(
        self,
        model: str = "x/z-image-turbo",
        host: str | None = None,
    ):
        self._model = model
        self._host = host or os.environ.get("OLLAMA_HOST", DEFAULT_HOST)

    def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        aspect_ratio: str = "1:1",
        output_path: Path,
    ) -> Path:
        import httpx

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse size for width/height
        w, h = (int(x) for x in size.split("x"))

        resp = httpx.post(
            f"{self._host}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "width": w,
                    "height": h,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        if "images" not in data or not data["images"]:
            raise RuntimeError(
                f"Ollama returned no images. Is {self._model} installed? "
                f"Is image generation supported on this platform?"
            )

        import base64

        img_bytes = base64.b64decode(data["images"][0])
        output_path.write_bytes(img_bytes)

        return output_path
