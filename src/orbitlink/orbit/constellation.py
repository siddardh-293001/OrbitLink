"""Construct repeatable synthetic circular constellations."""

from __future__ import annotations

import math

from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.core.models import OrbitalElements


def generate_constellation(*, planes: int = 3, satellites_per_plane: int = 8,
                           altitude_km: float = 550, inclination_deg: float = 53,
                           eccentricity: float = 0, phase_factor: int = 1,
                           raan_offset_deg: float = 0) -> list[OrbitalElements]:
    if planes < 1 or satellites_per_plane < 1:
        raise ValueError("planes and satellites per plane must be positive")
    if not math.isfinite(altitude_km) or altitude_km <= 0:
        raise ValueError("altitude must be a finite positive number")
    if not math.isfinite(inclination_deg) or not 0 <= inclination_deg <= 180:
        raise ValueError("inclination must be between 0 and 180 degrees")
    if not math.isfinite(eccentricity) or not 0 <= eccentricity < 1:
        raise ValueError("elliptic orbit eccentricity must be in [0, 1)")
    if not math.isfinite(raan_offset_deg):
        raise ValueError("RAAN offset must be finite")
    if not isinstance(phase_factor, int) or phase_factor < 0:
        raise ValueError("Walker phase factor must be a non-negative integer")
    items = []
    for p in range(planes):
        raan = math.radians(raan_offset_deg + 360.0 * p / planes)
        for s in range(satellites_per_plane):
            phase = 2.0 * math.pi * (s / satellites_per_plane + (phase_factor * p / (planes * satellites_per_plane)))
            items.append(OrbitalElements(
                satellite_id=f"P{p + 1:02d}-S{s + 1:02d}",
                semi_major_axis_m=EARTH_RADIUS_M + altitude_km * 1000.0,
                eccentricity=eccentricity,
                inclination_rad=math.radians(inclination_deg),
                raan_rad=raan,
                argument_of_perigee_rad=0.0,
                mean_anomaly_epoch_rad=phase,
            ))
    return items
