from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import requests

from core.astronomy import illumination_percent, moon_position

DIALAMOON_API = "https://svs.gsfc.nasa.gov/api/dialamoon/{timestamp}"


def resolve_target_time(utc_offset: Optional[float] = None, local_hour: Optional[int] = None) -> datetime:
    """
    Resolves the UTC timestamp to request: "now" by default, or today's date
    at the given local hour translated from the given UTC offset.
    """
    now_utc = datetime.now(timezone.utc)
    if utc_offset is None or local_hour is None:
        return now_utc

    local_now = now_utc + timedelta(hours=utc_offset)
    local_target = local_now.replace(hour=local_hour, minute=0, second=0, microsecond=0)
    return local_target - timedelta(hours=utc_offset)


@lru_cache(maxsize=64)
def _fetch_dialamoon(timestamp: str) -> dict:
    """Fetches Dial-A-Moon data for a minute-resolution timestamp; cached per instance."""
    response = requests.get(DIALAMOON_API.format(timestamp=timestamp), timeout=10)
    response.raise_for_status()
    return response.json()


def _number(value, fallback):
    """Returns value if it is a real number, otherwise computes the fallback."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return fallback()


def get_moon_data(orientation: str = "north", target_time: Optional[datetime] = None) -> dict:
    """
    Queries NASA's Dial-A-Moon API for the given UTC instant (default: now)
    and returns the frame URL plus illumination/distance/age/apparent-size details.
    """
    if target_time is None:
        target_time = datetime.now(timezone.utc)

    timestamp = target_time.strftime("%Y-%m-%dT%H:%M")
    data = _fetch_dialamoon(timestamp)

    image_key = "image" if orientation.lower() == "north" else "su_image"

    return {
        "url": data[image_key]["url"],
        # Prefer NASA's values; fall back to our own ephemeris if a field is missing.
        "illumination": _number(data.get("phase"), lambda: illumination_percent(target_time)),
        "age_days": data["age"],
        "distance_km": _number(data.get("distance"), lambda: moon_position(target_time).distance_km),
        "angular_diameter_arcsec": data["diameter"],
        "target_time": target_time,
    }
