import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import requests

from fastapi import FastAPI, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from core.astronomy import moon_rise_set
from core.calculator import get_moon_data, resolve_target_time
from core.compositor import generate_wallpaper

logger = logging.getLogger(__name__)

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

INDEX_HTML = (STATIC_DIR / "index.html").read_text()


def _fmt_event(t: Optional[datetime], always_up: bool, always_down: bool) -> str:
    if t is not None:
        return t.strftime("%H:%M")
    if always_up:
        return "up all day"
    if always_down:
        return "below horizon"
    return "none today"


@app.get("/", response_class=HTMLResponse)
async def index_page():
    return INDEX_HTML


@app.get("/api/wallpaper")
def get_wallpaper_endpoint(
    w: int = Query(1179, ge=1, le=4096, description="Screen width in pixels"),
    h: int = Query(2556, ge=1, le=4096, description="Screen height in pixels"),
    orientation: Literal["north", "south"] = Query("north", description="North up or south up frame mapping"),
    top_safe: int = Query(380, ge=0, description="Top margin boundary to stay clear of system widgets"),
    bottom_safe: int = Query(500, ge=0, description="Bottom margin boundary to keep clear of layout dock elements"),
    scale: float = Query(0.80, ge=0.5, le=0.95, description="Moon width as a fraction of screen width"),
    utc_offset: Optional[float] = Query(None, ge=-12, le=14, description="UTC offset in hours for the chosen time"),
    local_hour: Optional[int] = Query(None, ge=0, le=23, description="Hour (0-23) to render, paired with utc_offset"),
    show_illumination: bool = Query(False, description="Draw illumination percentage below the moon"),
    show_distance: bool = Query(False, description="Draw distance from Earth below the moon"),
    show_angular_size: bool = Query(False, description="Draw apparent angular size below the moon"),
    show_age: bool = Query(False, description="Draw moon age (days into lunar cycle) below the moon"),
    show_moonrise: bool = Query(False, description="Draw moonrise time for lat/lon (needs lat and lon)"),
    show_moonset: bool = Query(False, description="Draw moonset time for lat/lon (needs lat and lon)"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude in degrees, north positive"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude in degrees, east positive"),
    font: Literal["orbitron", "cinzel", "spacemono", "exo2"] = Query("orbitron", description="Detail text font: orbitron, cinzel, spacemono, or exo2"),
    font_size: int = Query(16, ge=10, le=48, description="Detail text font size in pixels"),
):
    try:
        # Step 1: Resolve which UTC instant to render and fetch its moon data
        target_time = resolve_target_time(utc_offset=utc_offset, local_hour=local_hour)
        moon_data = get_moon_data(orientation=orientation, target_time=target_time)

        # Step 2: Build the optional detail text lines
        detail_lines = []
        if show_illumination:
            detail_lines.append(f"Illumination: {moon_data['illumination']:.1f}%")
        if show_distance:
            detail_lines.append(f"Distance: {moon_data['distance_km']:,.0f} km")
        if show_angular_size:
            detail_lines.append(f"Apparent size: {moon_data['angular_diameter_arcsec']:.1f} arcsec")
        if show_age:
            detail_lines.append(f"Age: {moon_data['age_days']:.1f} days")

        if show_moonrise or show_moonset:
            if lat is None or lon is None:
                # Tell the user why instead of silently drawing nothing.
                if show_moonrise:
                    detail_lines.append("Moonrise: set location")
                if show_moonset:
                    detail_lines.append("Moonset: set location")
            else:
                offset = utc_offset or 0.0
                local_day = (target_time + timedelta(hours=offset)).date()
                rs = moon_rise_set(local_day, lat, lon, offset)
                if show_moonrise:
                    detail_lines.append(f"Moonrise: {_fmt_event(rs.rise, rs.always_up, rs.always_down)}")
                if show_moonset:
                    detail_lines.append(f"Moonset: {_fmt_event(rs.set, rs.always_up, rs.always_down)}")

        # Step 3: Render composite background image payload
        image_stream = generate_wallpaper(
            width=w,
            height=h,
            nasa_url=moon_data["url"],
            top_safe=top_safe,
            bottom_safe=bottom_safe,
            scale=scale,
            detail_lines=detail_lines,
            font=font,
            font_size=font_size,
        )

        # Step 4: Stream raw binary asset buffer with clear caching directives
        return StreamingResponse(
            image_stream,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=1800, stale-while-revalidate=600"
            },
        )
    except requests.RequestException:
        logger.exception("Upstream NASA request failed")
        return Response(content="Could not reach NASA's moon image service. Try again shortly.", status_code=502)
    except Exception:
        logger.exception("Wallpaper generation failed")
        return Response(content="Error generating wallpaper.", status_code=500)
