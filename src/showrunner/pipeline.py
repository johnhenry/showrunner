"""Pipeline orchestrator — drives format through plan -> assets -> compose -> render."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from showrunner.config import Config, load_config
from showrunner.formats.registry import get_registry
from showrunner.plan import Plan
from showrunner.styles.resolver import resolve_style


class Pipeline:
    """Orchestrates video generation through a Format plugin."""

    def __init__(self, format_name: str = "faceless-explainer", config: Config | None = None):
        self.format_name = format_name
        self.config = config or load_config()

    def run(
        self,
        topic: str,
        *,
        style: str | None = None,
        style_override: str | None = None,
        output_path: Path | None = None,
        aspect_ratio: str = "9:16",
        voice: str = "af_heart",
        speed: float = 1.0,
        captions: bool = False,
        watermark: str | None = None,
        parallel: bool = False,
        auto_approve: bool = False,
        no_audio: bool = False,
        dry_run: bool = False,
        preview: bool = False,
        layout: str = "single",
        text_overlay: bool = False,
        image_output: str = "pdf",
        panels_per_page: int = 4,
        page_size: tuple[int, int] = (1200, 1600),
        with_images: bool = False,
        images_dir: Path | None = None,
    ) -> Path | Plan:
        """Run the full pipeline."""
        registry = get_registry()
        fmt = registry.get(self.format_name)

        style_name = style or self.config.default_style
        resolved_style = resolve_style(style_name, overrides=style_override)

        # Determine render provider — illustrated format uses pillow by default
        is_illustrated = self.format_name == "illustrated"
        default_render = "pillow" if is_illustrated else "remotion"
        render_name = self.config.providers.get("render", default_render)
        if is_illustrated and render_name in ("remotion", "ffmpeg"):
            render_name = "pillow"

        # Resolve image provider — needed for illustrated format or --with-images
        image_name = self.config.providers.get("image")
        if with_images and not images_dir and not image_name:
            raise ValueError(
                "Image provider required for --with-images without --images. "
                "Set providers.image in .showrunner.yaml (openai, gemini, or ollama)"
            )

        providers = self._create_providers(
            llm_name=self.config.providers.get("llm", "anthropic"),
            tts_name=self.config.providers.get("tts", "kokoro"),
            render_name=render_name,
            provider_config=self.config.provider_config,
            video_name=self.config.providers.get("video"),
            image_name=image_name,
            image_output=image_output,
        )

        # Set format options
        fmt._style = resolved_style
        fmt._aspect_ratio = aspect_ratio
        fmt._voice = voice
        fmt._speed = speed
        fmt._parallel = parallel
        fmt._layout = layout
        fmt._text_overlay = text_overlay
        fmt._panels_per_page = panels_per_page
        fmt._page_size = page_size
        fmt._with_images = with_images or images_dir is not None
        fmt._images_dir = images_dir

        # Plan
        plan = fmt.plan(topic, resolved_style, self.config, providers["llm"])

        if dry_run:
            return plan

        # Setup work dir
        work_dir = Path(tempfile.mkdtemp(prefix="showrunner-"))
        providers["render"].setup(work_dir)

        # Assets
        if not no_audio:
            assets = fmt.generate_assets(plan, providers, work_dir)
        else:
            assets = {"has_audio": False, "durations": {}, "width": 1080, "height": 1920}

        # Compose
        fmt.compose(plan, assets, work_dir, captions=captions, watermark=watermark)

        if preview:
            providers["render"].preview(work_dir)
            return plan

        # Render
        if output_path is None:
            ext = ".pdf" if is_illustrated else ".mp4"
            output_path = Path.cwd() / "output" / f"{_slugify(plan.title)}{ext}"

        result = providers["render"].render(work_dir=work_dir, output_path=output_path)
        return result

    def _create_providers(
        self, llm_name: str, tts_name: str, render_name: str, provider_config: dict,
        video_name: str | None = None, image_name: str | None = None,
        image_output: str = "pdf",
    ) -> dict:
        providers = {}

        if llm_name == "anthropic":
            from showrunner.providers.llm.anthropic import AnthropicLLMProvider

            cfg = provider_config.get("anthropic", {})
            providers["llm"] = AnthropicLLMProvider(
                model=cfg.get("model", "claude-sonnet-4-5-20250929")
            )
        elif llm_name == "openai":
            from showrunner.providers.llm.openai import OpenAILLMProvider

            cfg = provider_config.get("openai", {})
            providers["llm"] = OpenAILLMProvider(model=cfg.get("model", "gpt-4o"))
        else:
            raise ValueError(f"Unknown LLM provider: {llm_name}")

        if tts_name == "kokoro":
            from showrunner.providers.tts.kokoro import KokoroTTSProvider

            providers["tts"] = KokoroTTSProvider()
        elif tts_name == "elevenlabs":
            from showrunner.providers.tts.elevenlabs import ElevenLabsTTSProvider

            cfg = provider_config.get("elevenlabs", {})
            providers["tts"] = ElevenLabsTTSProvider(api_key=cfg.get("api_key"))
        else:
            raise ValueError(f"Unknown TTS provider: {tts_name}")

        if render_name == "remotion":
            from showrunner.providers.render.remotion import RemotionRenderProvider

            providers["render"] = RemotionRenderProvider()
        elif render_name == "ffmpeg":
            from showrunner.providers.render.ffmpeg import FFmpegRenderProvider

            providers["render"] = FFmpegRenderProvider()
        elif render_name == "pillow":
            from showrunner.providers.render.pillow import PillowRenderProvider

            providers["render"] = PillowRenderProvider(output_format=image_output)
        else:
            raise ValueError(f"Unknown render provider: {render_name}")

        if image_name:
            if image_name == "openai":
                from showrunner.providers.image.openai import OpenAIImageProvider

                cfg = provider_config.get("openai", {})
                providers["image"] = OpenAIImageProvider(
                    api_key=cfg.get("api_key"),
                    model=cfg.get("image_model", "gpt-image-1"),
                    quality=cfg.get("image_quality", "auto"),
                )
            elif image_name == "gemini":
                from showrunner.providers.image.gemini import GeminiImageProvider

                cfg = provider_config.get("gemini", {})
                providers["image"] = GeminiImageProvider(
                    api_key=cfg.get("api_key"),
                    model=cfg.get("image_model", "imagen-3.0-generate-002"),
                )
            elif image_name == "ollama":
                from showrunner.providers.image.ollama import OllamaImageProvider

                cfg = provider_config.get("ollama", {})
                providers["image"] = OllamaImageProvider(
                    model=cfg.get("image_model", "x/z-image-turbo"),
                    host=cfg.get("host"),
                )
            else:
                raise ValueError(f"Unknown image provider: {image_name}")

        if video_name:
            if video_name == "minimax":
                from showrunner.providers.video.minimax import MinimaxVideoProvider

                cfg = provider_config.get("minimax", {})
                providers["video"] = MinimaxVideoProvider(
                    api_key=cfg.get("api_key"), model=cfg.get("model", "video-01-live2d")
                )
            elif video_name == "gemini":
                from showrunner.providers.video.gemini import GeminiVideoProvider

                cfg = provider_config.get("gemini", {})
                providers["video"] = GeminiVideoProvider(
                    api_key=cfg.get("api_key"), model=cfg.get("model", "veo-3.1-generate-preview")
                )
            else:
                raise ValueError(f"Unknown video provider: {video_name}")

        return providers


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-")[:80]
