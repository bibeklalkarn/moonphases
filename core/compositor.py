import requests
from io import BytesIO
from PIL import Image


def generate_wallpaper(width: int, height: int, nasa_url: str, top_safe: int, bottom_safe: int) -> BytesIO:
    """
    Spawns a pure black canvas matching device screen boundaries, resizes the
    NASA moon asset, and positions it precisely inside the designated safe zones.
    """
    # 1. Initialize pitch-black RGB canvas layer
    canvas = Image.new("RGB", (width, height), (0, 0, 0))

    # 2. Ingest the static hourly moon frame from NASA server
    response = requests.get(nasa_url, timeout=10)
    response.raise_for_status()
    moon_img = Image.open(BytesIO(response.content)).convert("RGB")

    # 3. Scales moon sphere relative to the hardware screen width
    target_width = int(width * 0.75)  # Scale to fit 75% of screen width
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

    # 5. Pack canvas object array data directly into stream
    output_buffer = BytesIO()
    canvas.save(output_buffer, format="PNG", optimize=True)
    output_buffer.seek(0)

    return output_buffer
