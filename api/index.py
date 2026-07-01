from pathlib import Path

from fastapi import FastAPI, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from core.calculator import get_nasa_asset_url
from core.compositor import generate_wallpaper

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

INDEX_HTML = (STATIC_DIR / "index.html").read_text()


@app.get("/", response_class=HTMLResponse)
async def index_page():
    return INDEX_HTML


@app.get("/api/wallpaper")
async def get_wallpaper_endpoint(
    w: int = Query(1179, ge=1, le=4096, description="Screen width in pixels"),
    h: int = Query(2556, ge=1, le=4096, description="Screen height in pixels"),
    orientation: str = Query("north", description="North up or south up frame mapping"),
    top_safe: int = Query(380, ge=0, description="Top margin boundary to stay clear of system widgets"),
    bottom_safe: int = Query(500, ge=0, description="Bottom margin boundary to keep clear of layout dock elements"),
    scale: float = Query(0.80, ge=0.5, le=0.95, description="Moon width as a fraction of screen width"),
):
    try:
        # Step 1: Calculate specific target asset path
        nasa_url = get_nasa_asset_url(orientation=orientation)

        # Step 2: Render composite background image payload
        image_stream = generate_wallpaper(
            width=w,
            height=h,
            nasa_url=nasa_url,
            top_safe=top_safe,
            bottom_safe=bottom_safe,
            scale=scale,
        )

        # Step 3: Stream raw binary asset buffer with clear caching directives
        return StreamingResponse(
            image_stream,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=1800, stale-while-revalidate=600"
            },
        )
    except Exception as e:
        return Response(content=f"Error generating dynamic asset frame: {str(e)}", status_code=500)
