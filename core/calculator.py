from datetime import datetime, timezone

import requests

DIALAMOON_API = "https://svs.gsfc.nasa.gov/api/dialamoon/{timestamp}"


def get_nasa_asset_url(orientation: str = "north") -> str:
    """
    Queries NASA's Dial-A-Moon API for the current UTC hour and returns the
    matching 730x730 frame URL (north-up or south-up per orientation).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    response = requests.get(DIALAMOON_API.format(timestamp=timestamp), timeout=10)
    response.raise_for_status()
    data = response.json()

    image_key = "image" if orientation.lower() == "north" else "su_image"
    return data[image_key]["url"]
