"""Optional SGP4 propagation with explicit TEME to Earth-fixed conversion.

SGP4 returns TEME coordinates. This module keeps that frame in its result and
uses the standard GMST rotation to a PEF/Earth-fixed frame. Polar motion is not
modeled in this phase; timestamps use UTC as an UT1 approximation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from orbitlink.orbit.tle import TLERecord


@dataclass(frozen=True)
class SGP4State:
    satellite_id: str
    time_utc: datetime
    position_teme_m: tuple[float, float, float]
    velocity_teme_m_s: tuple[float, float, float]
    position_pef_m: tuple[float, float, float]
    coordinate_frame: str = "TEME"

    @property
    def position_ecef_m(self) -> tuple[float, float, float]:
        """Compatibility alias for the app's GMST-rotated PEF approximation.

        This does not include polar motion, so it should not be treated as a
        precision ITRF/ECEF solution.
        """
        return self.position_pef_m


def julian_date(time_utc: datetime) -> float:
    value = (time_utc.replace(tzinfo=timezone.utc) if time_utc.tzinfo is None
             else time_utc.astimezone(timezone.utc))
    year, month = value.year, value.month
    day = value.day + (value.hour + (value.minute + (value.second + value.microsecond / 1e6) / 60) / 60) / 24
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5


def gmst_radians(time_utc: datetime) -> float:
    jd = julian_date(time_utc)
    t = (jd - 2451545.0) / 36525.0
    degrees = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t**2 - t**3 / 38710000.0
    return math.radians(degrees % 360.0)


def teme_to_ecef(position_teme_m: tuple[float, float, float], time_utc: datetime) -> tuple[float, float, float]:
    theta = gmst_radians(time_utc)
    c, s = math.cos(theta), math.sin(theta)
    x, y, z = position_teme_m
    return c*x + s*y, -s*x + c*y, z


def propagate_tle(record: TLERecord, time_utc: datetime, *, max_age_days: float = 14) -> SGP4State:
    time_utc = time_utc.replace(tzinfo=timezone.utc) if time_utc.tzinfo is None else time_utc.astimezone(timezone.utc)
    issues = record.quality(time_utc, max_age_days=max_age_days)
    if issues:
        raise ValueError("; ".join(issues))
    try:
        from sgp4.api import Satrec, jday
    except ImportError as exc:
        raise RuntimeError("SGP4 backend needs the optional dependency: pip install 'orbitlink[full]'") from exc
    satellite = Satrec.twoline2rv(record.line1, record.line2)
    jd, fr = jday(time_utc.year, time_utc.month, time_utc.day, time_utc.hour,
                  time_utc.minute, time_utc.second + time_utc.microsecond / 1e6)
    error, position_km, velocity_km_s = satellite.sgp4(jd, fr)
    if error:
        raise ValueError(f"SGP4 propagation failed with code {error}")
    position = tuple(component * 1000 for component in position_km)
    velocity = tuple(component * 1000 for component in velocity_km_s)
    return SGP4State(record.satellite_id, time_utc, position, velocity, teme_to_ecef(position, time_utc))
