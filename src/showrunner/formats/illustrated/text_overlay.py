"""Text overlay for illustrated images — captions, narration, titles."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DEFAULT_FONT_SIZE = 28
CAPTION_PADDING = 20
CAPTION_BG_OPACITY = 180  # 0-255, semi-transparent black


def overlay_caption(
    image_path: Path,
    text: str,
    output_path: Path,
    *,
    position: str = "bottom",
    font_size: int = DEFAULT_FONT_SIZE,
    max_width_ratio: float = 0.9,
) -> Path:
    """Overlay caption text on an image.

    Args:
        image_path: Source image path.
        text: Caption text to overlay.
        output_path: Where to save the result.
        position: "top" or "bottom".
        font_size: Font size in pixels.
        max_width_ratio: Max text width as ratio of image width.

    Returns:
        Path to the output image with caption overlay.
    """
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _load_font(font_size)
    max_text_width = int(img.width * max_width_ratio)

    # Word-wrap text
    lines = _wrap_text(draw, text, font, max_text_width)
    if not lines:
        img.save(output_path)
        return output_path

    # Calculate text block size
    line_height = font_size + 6
    block_height = len(lines) * line_height + CAPTION_PADDING * 2
    block_width = img.width

    # Draw semi-transparent background
    if position == "top":
        bg_y = 0
    else:
        bg_y = img.height - block_height

    draw.rectangle(
        [(0, bg_y), (block_width, bg_y + block_height)],
        fill=(0, 0, 0, CAPTION_BG_OPACITY),
    )

    # Draw text lines
    y = bg_y + CAPTION_PADDING
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (img.width - text_width) // 2
        draw.text((x, y), line, fill=(255, 255, 255, 255), font=font)
        y += line_height

    # Composite
    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")
    result.save(output_path)
    return output_path


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font, falling back to default if no TTF available."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)
