# Moon Phase Wallpaper

A tiny web service that turns **today's real Moon** into a phone wallpaper. It
fetches NASA's image of the Moon for the current hour, centres it on a black
canvas sized to your screen, and returns a PNG. Point your phone's automation
at the URL and your lock screen always shows the Moon as it looks right now.

- Real NASA imagery ([Dial-A-Moon](https://svs.gsfc.nasa.gov/5048/)), not an illustration
- Sized to your device, with safe zones so the clock and dock never overlap the Moon
- North-up or south-up, for either hemisphere
- Optional text under the Moon: illumination, distance, apparent size, age, **moonrise and moonset**
- Four fonts, adjustable text and Moon size
- A web page to build and preview your link, and a plain HTTP API for everything else

## Try it

Open the hosted web page, choose your device, adjust the options, and copy the
generated link. That link is all you need; there's nothing to install. See
[Using it on your phone](#using-it-on-your-phone) below.

## Using it on your phone

Use the link from the web page (it ends in `/api/wallpaper?...`).

- **iOS:** Shortcuts → *Get Contents of URL* → *Set Wallpaper*, run on a daily or hourly Automation.
- **Android:** Tasker or MacroDroid → HTTP GET → set wallpaper.

Responses are cached for 30 minutes, so frequent refreshes are cheap.

## API

`GET /api/wallpaper` returns `image/png`.

| Parameter | Default | Description |
|---|---|---|
| `w`, `h` | 1179, 2556 | Screen size in pixels (1–4096) |
| `orientation` | `north` | `north` or `south` (south-up for the southern hemisphere) |
| `scale` | 0.80 | Moon width as a fraction of screen width (0.5–0.95) |
| `top_safe`, `bottom_safe` | 380, 500 | Pixels kept clear at the top (clock/widgets) and bottom (dock) |
| `utc_offset` | now | UTC offset in hours (−12 to 14). With `local_hour`, renders that hour today |
| `local_hour` | now | Hour 0–23 in your local time, used with `utc_offset` |
| `show_illumination` | false | Percent of the disc that is lit |
| `show_distance` | false | Distance from Earth in km |
| `show_angular_size` | false | Apparent size in arcseconds |
| `show_age` | false | Days into the lunar cycle |
| `show_moonrise`, `show_moonset` | false | Rise / set time for your location (needs `lat` and `lon`) |
| `lat`, `lon` | none | Your position in degrees (north and east positive) |
| `font` | `orbitron` | `orbitron`, `cinzel`, `spacemono` or `exo2` |
| `font_size` | 16 | Detail text size in px (10–48) |

Example, an iPhone wallpaper showing illumination plus moonrise and moonset in
New York (UTC−5):

```
/api/wallpaper?w=1179&h=2556&show_illumination=true&show_moonrise=true&show_moonset=true&lat=40.71&lon=-74.01&utc_offset=-5&local_hour=20
```

Invalid values return `422`. If NASA is unreachable you get `502`; other
failures return `500` with a generic message (details are logged server-side).

### How the numbers are produced

- **Image, illumination, distance, age, apparent size:** NASA's Dial-A-Moon service.
- **Illumination and distance fallback:** if NASA's response is missing either
  value, they are computed locally (see below), so the text still renders.
- **Moonrise and moonset:** always computed locally, since NASA doesn't supply
  them. Times are shown in the `utc_offset` you pass (UTC if omitted), for that
  offset's calendar day. Some days have no moonrise or no moonset because the
  Moon rises about 50 minutes later each day; the wallpaper says so. Near the
  poles the Moon can stay up or down all day, and that is shown too.

`core/astronomy.py` is a standard-library-only lunar ephemeris (low-precision
theory with the main perturbation terms). Checked against NASA, illumination
agrees to within 0.05 percentage points and distance to within about 0.2%.
Rise and set times place the Moon on the horizon to within 0.003°, which is
good to roughly a minute or two. It ignores local terrain and weather.

## Project layout

```
api/
  index.py          FastAPI app: the web page and /api/wallpaper
  static/           index.html (builder UI), favicon, icon
core/
  calculator.py     Picks the target time and queries NASA Dial-A-Moon
  astronomy.py      Local moon ephemeris: illumination, distance, rise/set
  compositor.py     Pillow: canvas, Moon placement, text rendering
  fonts/            Bundled OFL-licensed fonts (licenses included)
vercel.json         Routes every request to the FastAPI app
```

## Development

Only needed if you want to change the code or host your own copy.

```bash
git clone https://github.com/bibeklalkarn/moonphases.git && cd moonphases
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Then open <http://localhost:8000>.

### Host your own on Vercel

```bash
npm i -g vercel
vercel --prod
```

`vercel.json` already rewrites all paths to `api/index.py`, and dependencies
come from `requirements.txt`. There is no database, API key or configuration to
set up. The `.vercel/` folder the CLI creates holds your account's project IDs,
so it's git-ignored; don't commit it.

## License

[MIT](LICENSE). The bundled fonts keep their own SIL Open Font License (see `core/fonts/licenses/`).

## Credits

- Moon imagery and data: NASA Scientific Visualization Studio, Dial-A-Moon.
- Fonts: Orbitron, Cinzel, Exo 2, Space Mono, each under the SIL Open Font
  License (see `core/fonts/licenses/`).
- Moon position method: Paul Schlyter, *How to compute planetary positions*.
