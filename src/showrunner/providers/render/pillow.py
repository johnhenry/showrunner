"""Pillow render provider — assembles images into PDF or PNG sequence."""

from __future__ import annotations

import shutil
import sys
import subprocess
from pathlib import Path

from showrunner.providers.render.base import RenderProvider


class PillowRenderProvider(RenderProvider):
    """Render still images into PDF or PNG sequence output."""

    def __init__(self, output_format: str = "pdf", jpeg_quality: int = 85):
        self.output_format = output_format  # "pdf", "png", "both"
        self.jpeg_quality = jpeg_quality

    def setup(self, work_dir: Path) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "images").mkdir(exist_ok=True)
        (work_dir / "pages").mkdir(exist_ok=True)

    def render(self, *, work_dir: Path, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pages_dir = work_dir / "pages"
        page_files = sorted(pages_dir.glob("*.png"))

        if not page_files:
            # Fall back to raw images if no composed pages
            images_dir = work_dir / "images"
            page_files = sorted(images_dir.glob("*.png"))

        if not page_files:
            raise RuntimeError("No images found to render — compose() must run first")

        if self.output_format in ("png", "both"):
            png_dir = output_path.parent / f"{output_path.stem}_images"
            png_dir.mkdir(parents=True, exist_ok=True)
            for f in page_files:
                shutil.copy2(f, png_dir / f.name)
            if self.output_format == "png":
                return png_dir

        # Build PDF
        from PIL import Image

        pdf_path = output_path.with_suffix(".pdf")
        images = []
        for f in page_files:
            img = Image.open(f)
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        if not images:
            raise RuntimeError("No valid images for PDF assembly")

        first, *rest = images
        first.save(
            pdf_path,
            "PDF",
            save_all=True,
            append_images=rest,
            quality=self.jpeg_quality,
        )

        if self.output_format == "both":
            return pdf_path  # PNG dir was already created above

        return pdf_path

    def preview(self, work_dir: Path) -> None:
        pages_dir = work_dir / "pages"
        page_files = sorted(pages_dir.glob("*.png"))
        if not page_files:
            page_files = sorted((work_dir / "images").glob("*.png"))
        if page_files:
            target = str(page_files[0])
            if sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
