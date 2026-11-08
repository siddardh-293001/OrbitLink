"""Geodetic ground-site conversion and Earth-fixed look angles."""

from __future__ import annotations

import math

from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.core.models import GroundSite, LookAngle


def geodetic_to_ecef(site: GroundSite) -> tuple[float, float, float]:
    lat, lon = math.radians(site.latitude_deg), math.radians(site.longitude_deg)
    radius = EARTH_RADIUS_M + site.altitude_m
    return (radius * math.cos(lat) * math.cos(lon),
            radius * math.cos(lat) * math.sin(lon),
            radius * math.sin(lat))


def look_angle(site: GroundSite, satellite_id: str, satellite_ecef_m: tuple[float, float, float],
               minimum_elevation_deg: float = 25.0) -> LookAngle:
    sx, sy, sz = satellite_ecef_m
    gx, gy, gz = geodetic_to_ecef(site)
    dx, dy, dz = sx - gx, sy - gy, sz - gz
    lat, lon = math.radians(site.latitude_deg), math.radians(site.longitude_deg)
    east = -math.sin(lon) * dx + math.cos(lon) * dy
    north = -math.sin(lat) * math.cos(lon) * dx - math.sin(lat) * math.sin(lon) * dy + math.cos(lat) * dz
    up = math.cos(lat) * math.cos(lon) * dx + math.cos(lat) * math.sin(lon) * dy + math.sin(lat) * dz
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    elevation = math.degrees(math.atan2(up, math.hypot(east, north)))
    azimuth = math.degrees(math.atan2(east, north)) % 360.0
    return LookAngle(satellite_id, distance, azimuth, elevation, elevation >= minimum_elevation_deg)
