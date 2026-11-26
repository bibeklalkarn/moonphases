from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).parent / "fonts"
FONTS = {
    "orbitron": FONTS_DIR / "Orbitron.ttf",
    "cinzel": FONTS_DIR / "Cinzel.ttf",
    "spacemono": FONTS_DIR / "SpaceMono-Regular.ttf",
    "exo2": FONTS_DIR / "Exo2.ttf",
}
DEFAULT_FONT = "orbitron"


@lru_cache(maxsize=16)
def _fetch_image_bytes(url: str) -> bytes:
    """Downloads a moon frame; cached so warm instances skip repeat downloads."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.content


def generate_wallpaper(
    width: int,
    height: int,
    nasa_url: str,
    top_safe: int,
    bottom_safe: int,
    scale: float = 0.80,
    detail_lines: Optional[list] = None,
    font: str = DEFAULT_FONT,
    font_size: int = 16,
) -> BytesIO:
    """
    Spawns a pure black canvas matching device screen boundaries, resizes the
    NASA moon asset, and positions it precisely inside the designated safe zones.
    Optionally draws small centered detail text below the moon.
    """
    # 1. Initialize pitch-black RGB canvas layer
    canvas = Image.new("RGB", (width, height), (0, 0, 0))

    # 2. Ingest the static hourly moon frame from NASA server
    moon_img = Image.open(BytesIO(_fetch_image_bytes(nasa_url))).convert("RGB")

    # 3. Scales moon sphere relative to the hardware screen width
    target_width = int(width * scale)
    aspect_ratio = moon_img.height / moon_img.width
    target_height = int(target_width * aspect_ratio)

    moon_resized = moon_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 4. Math calculation to isolate space between system UI safe zones
    available_top = top_safe
    available_bottom = height - bottom_safe
    center_y = available_top + ((available_bottom - available_top) // 2)

    # Center coordinates for pasting the image matrix
    paste_x = (width - target_width) // 2
    paste_y = center_y - (target_height // 2)

    canvas.paste(moon_resized, (paste_x, paste_y))

    # 5. Draw optional detail text centered below the moon
    if detail_lines:
        draw = ImageDraw.Draw(canvas)
        font_obj = ImageFont.truetype(str(FONTS.get(font, FONTS[DEFAULT_FONT])), font_size)

        line_y = paste_y + target_height + int(font_size * 0.8)
        for line in detail_lines:
            bbox = draw.textbbox((0, 0), line, font=font_obj)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            draw.text(
                ((width - line_width) // 2, line_y),
                line,
                font=font_obj,
                fill=(200, 200, 200),
            )
            line_y += int(line_height * 1.6)

    # 6. Pack canvas object array data directly into stream
    output_buffer = BytesIO()
    canvas.save(output_buffer, format="PNG", optimize=True)
    output_buffer.seek(0)

    return output_buffer
