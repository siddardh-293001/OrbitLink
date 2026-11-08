"""Simple optical inter-satellite line-of-sight and availability model."""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitlink.core.constants import EARTH_RADIUS_M, SPEED_OF_LIGHT_M_S


@dataclass(frozen=True)
class OpticalLink:
    distance_m: float
    propagation_delay_s: float
    available: bool
    reason: str


def earth_occludes_segment(a_m: tuple[float, float, float], b_m: tuple[float, float, float],
                           *, earth_radius_m: float = EARTH_RADIUS_M) -> bool:
    delta = tuple(b_m[i] - a_m[i] for i in range(3))
    length_sq = sum(value * value for value in delta)
    if length_sq == 0:
        return math.sqrt(sum(value * value for value in a_m)) < earth_radius_m
    fraction = max(0.0, min(1.0, -sum(a_m[i] * delta[i] for i in range(3)) / length_sq))
    closest = tuple(a_m[i] + fraction * delta[i] for i in range(3))
    return math.sqrt(sum(value * value for value in closest)) < earth_radius_m


def optical_link(a_m: tuple[float, float, float], b_m: tuple[float, float, float], *,
                 minimum_range_m: float = 0.0, maximum_range_m: float = 5_000_000.0,
                 earth_radius_m: float = EARTH_RADIUS_M) -> OpticalLink:
    distance = math.dist(a_m, b_m)
    reason = "available"
    available = True
    if distance < minimum_range_m:
        available, reason = False, "below minimum range"
    elif distance > maximum_range_m:
        available, reason = False, "above maximum range"
    elif earth_occludes_segment(a_m, b_m, earth_radius_m=earth_radius_m):
        available, reason = False, "Earth blocks line of sight"
    return OpticalLink(distance, distance / SPEED_OF_LIGHT_M_S, available, reason)
