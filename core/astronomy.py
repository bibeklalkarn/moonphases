"""
Self-contained lunar ephemeris (standard library only).

Moon and Sun positions follow Paul Schlyter's low-precision method
("How to compute planetary positions", stjarnhimlen.se), including the main
lunar perturbation terms. Accuracy is roughly 1-2 arcminutes in position,
which is good to about a minute or two for rise/set times and well under
0.1% for illumination.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import asin, atan2, cos, degrees, radians, sin, sqrt
from typing import Optional

EARTH_RADIUS_KM = 6378.14
AU_KM = 149_597_870.7


def _rev(x: float) -> float:
    """Normalises an angle to [0, 360)."""
    return x % 360.0


def _sind(x: float) -> float:
    return sin(radians(x))


def _cosd(x: float) -> float:
    return cos(radians(x))


def _day_number(dt: datetime) -> float:
    """Days since 2000 Jan 0.0 UT (Schlyter's d), i.e. JD - 2451543.5."""
    dt = dt.astimezone(timezone.utc)
    epoch = datetime(1999, 12, 31, tzinfo=timezone.utc)
    return (dt - epoch).total_seconds() / 86400.0


def _solve_kepler(m_deg: float, e: float) -> float:
    """Returns the eccentric anomaly (degrees) for mean anomaly m_deg."""
    E = m_deg + degrees(e * _sind(m_deg) * (1.0 + e * _cosd(m_deg)))
    for _ in range(10):
        delta = (E - degrees(e * _sind(E)) - m_deg) / (1.0 - e * _cosd(E))
        E -= delta
        if abs(delta) < 1e-6:
            break
    return E


@dataclass
class _Sun:
    lon: float          # ecliptic longitude of date, degrees
    distance_au: float
    mean_anomaly: float
    mean_lon: float


def _sun(d: float) -> _Sun:
    w = 282.9404 + 4.70935e-5 * d
    e = 0.016709 - 1.151e-9 * d
    M = _rev(356.0470 + 0.9856002585 * d)
    E = _solve_kepler(M, e)
    xv = _cosd(E) - e
    yv = sqrt(1.0 - e * e) * _sind(E)
    v = degrees(atan2(yv, xv))
    return _Sun(lon=_rev(v + w), distance_au=sqrt(xv * xv + yv * yv), mean_anomaly=M, mean_lon=_rev(M + w))


@dataclass
class MoonPosition:
    lon: float           # geocentric ecliptic longitude of date, degrees
    lat: float           # geocentric ecliptic latitude, degrees
    distance_km: float
    ra: float            # right ascension, degrees
    dec: float           # declination, degrees


def moon_position(dt: datetime) -> MoonPosition:
    d = _day_number(dt)
    sun = _sun(d)

    N = _rev(125.1228 - 0.0529538083 * d)
    i = 5.1454
    w = _rev(318.0634 + 0.1643573223 * d)
    a = 60.2666
    e = 0.054900
    M = _rev(115.3654 + 13.0649929509 * d)

    E = _solve_kepler(M, e)
    xv = a * (_cosd(E) - e)
    yv = a * sqrt(1.0 - e * e) * _sind(E)
    v = degrees(atan2(yv, xv))
    r = sqrt(xv * xv + yv * yv)

    xh = r * (_cosd(N) * _cosd(v + w) - _sind(N) * _sind(v + w) * _cosd(i))
    yh = r * (_sind(N) * _cosd(v + w) + _cosd(N) * _sind(v + w) * _cosd(i))
    zh = r * (_sind(v + w) * _sind(i))
    lon = degrees(atan2(yh, xh))
    lat = degrees(atan2(zh, sqrt(xh * xh + yh * yh)))

    # Main perturbations
    Ms = sun.mean_anomaly
    Lm = M + w + N
    D = Lm - sun.mean_lon
    F = Lm - N
    lon += (
        -1.274 * _sind(M - 2 * D)
        + 0.658 * _sind(2 * D)
        - 0.186 * _sind(Ms)
        - 0.059 * _sind(2 * M - 2 * D)
        - 0.057 * _sind(M - 2 * D + Ms)
        + 0.053 * _sind(M + 2 * D)
        + 0.046 * _sind(2 * D - Ms)
        + 0.041 * _sind(M - Ms)
        - 0.035 * _sind(D)
        - 0.031 * _sind(M + Ms)
        - 0.015 * _sind(2 * F - 2 * D)
        + 0.011 * _sind(M - 4 * D)
    )
    lat += (
        -0.173 * _sind(F - 2 * D)
        - 0.055 * _sind(M - F - 2 * D)
        - 0.046 * _sind(M + F - 2 * D)
        + 0.033 * _sind(F + 2 * D)
        + 0.017 * _sind(2 * M + F)
    )
    r += -0.58 * _cosd(M - 2 * D) - 0.46 * _cosd(2 * D)
    lon = _rev(lon)

    # Ecliptic -> equatorial
    ecl = 23.4393 - 3.563e-7 * d
    x = _cosd(lon) * _cosd(lat)
    y = _sind(lon) * _cosd(lat)
    z = _sind(lat)
    ye = y * _cosd(ecl) - z * _sind(ecl)
    ze = y * _sind(ecl) + z * _cosd(ecl)
    ra = _rev(degrees(atan2(ye, x)))
    dec = degrees(atan2(ze, sqrt(x * x + ye * ye)))

    return MoonPosition(lon=lon, lat=lat, distance_km=r * EARTH_RADIUS_KM, ra=ra, dec=dec)


def illumination_percent(dt: datetime) -> float:
    """Fraction of the Moon's disc that is lit, as a percentage."""
    d = _day_number(dt)
    moon = moon_position(dt)
    sun = _sun(d)

    # Elongation (Sun-Earth-Moon angle) and phase angle (Sun-Moon-Earth)
    cos_elong = _cosd(moon.lat) * _cosd(moon.lon - sun.lon)
    elong = degrees(atan2(sqrt(max(0.0, 1.0 - cos_elong * cos_elong)), cos_elong))
    sun_km = sun.distance_au * AU_KM
    phase_angle = degrees(atan2(sun_km * _sind(elong), moon.distance_km - sun_km * _cosd(elong)))
    return (1.0 + _cosd(phase_angle)) / 2.0 * 100.0


def _moon_altitude(dt: datetime, lat: float, lon: float) -> tuple:
    """Returns (altitude, standard rise/set altitude h0) in degrees."""
    moon = moon_position(dt)
    jd = _day_number(dt) + 2451543.5
    gmst = _rev(280.46061837 + 360.98564736629 * (jd - 2451545.0))
    ha = gmst + lon - moon.ra
    alt = degrees(asin(_sind(lat) * _sind(moon.dec) + _cosd(lat) * _cosd(moon.dec) * _cosd(ha)))
    # h0 = 0.7275 * horizontal parallax - 34' refraction (Meeus, ch. 15)
    parallax = degrees(asin(EARTH_RADIUS_KM / moon.distance_km))
    return alt, 0.7275 * parallax - 0.5667


@dataclass
class RiseSet:
    rise: Optional[datetime]   # local time (tz-aware), None if no rise that day
    set: Optional[datetime]
    always_up: bool = False
    always_down: bool = False


def moon_rise_set(day: date, lat: float, lon: float, utc_offset: float = 0.0, step_minutes: int = 10) -> RiseSet:
    """
    Finds moonrise and moonset on the given local calendar day.

    lat/lon are in degrees (north and east positive). Times are returned in
    the zone given by utc_offset (hours). The Moon rises about 50 minutes
    later each day, so on roughly one day a month there is no rise or no set.
    """
    tz = timezone(timedelta(hours=utc_offset))
    start = datetime(day.year, day.month, day.day, tzinfo=tz)

    def f(t: datetime) -> float:
        alt, h0 = _moon_altitude(t, lat, lon)
        return alt - h0

    def refine(t0: datetime, t1: datetime, v0: float) -> datetime:
        for _ in range(20):  # 10 min / 2^20 is far below a second
            mid = t0 + (t1 - t0) / 2
            vm = f(mid)
            if (vm > 0) == (v0 > 0):
                t0, v0 = mid, vm
            else:
                t1 = mid
        return (t0 + (t1 - t0) / 2).replace(microsecond=0)

    rise = set_ = None
    step = timedelta(minutes=step_minutes)
    t_prev, v_prev = start, f(start)
    any_up = v_prev > 0
    all_up = v_prev > 0
    steps = (24 * 60) // step_minutes
    for n in range(1, steps + 1):
        t = start + n * step
        v = f(t)
        any_up |= v > 0
        all_up &= v > 0
        if v_prev <= 0 < v and rise is None:
            rise = refine(t_prev, t, v_prev)
        elif v_prev > 0 >= v and set_ is None:
            set_ = refine(t_prev, t, v_prev)
        t_prev, v_prev = t, v

    # A crossing found in the last bucket can land exactly on midnight of the next day
    if rise is not None and rise.date() != day:
        rise = None
    if set_ is not None and set_.date() != day:
        set_ = None

    return RiseSet(
        rise=rise,
        set=set_,
        always_up=rise is None and set_ is None and all_up,
        always_down=rise is None and set_ is None and not any_up,
    )
