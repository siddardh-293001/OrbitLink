"""Two-body Keplerian propagation into inertial and Earth-fixed frames."""

from __future__ import annotations

import math

from orbitlink.core.constants import EARTH_MU_M3_S2, EARTH_ROTATION_RAD_S
from orbitlink.core.models import OrbitalElements, SatelliteState


def solve_kepler(mean_anomaly_rad: float, eccentricity: float, *, tolerance: float = 1e-12) -> float:
    if not 0 <= eccentricity < 1:
        raise ValueError("elliptic orbit eccentricity must be in [0, 1)")
    mean = mean_anomaly_rad % (2.0 * math.pi)
    estimate = mean if eccentricity < 0.8 else math.pi
    for _ in range(50):
        delta = (estimate - eccentricity * math.sin(estimate) - mean) / (1.0 - eccentricity * math.cos(estimate))
        estimate -= delta
        if abs(delta) <= tolerance:
            return estimate
    raise ArithmeticError("Kepler solver did not converge")


def orbital_period_seconds(semi_major_axis_m: float) -> float:
    return 2.0 * math.pi * math.sqrt(semi_major_axis_m**3 / EARTH_MU_M3_S2)


def propagate(elements: OrbitalElements, time_seconds: float, *, earth_rotation: bool = True) -> SatelliteState:
    a, e = elements.semi_major_axis_m, elements.eccentricity
    if a <= 0 or not 0 <= e < 1:
        raise ValueError("semi-major axis must be positive and eccentricity must be in [0, 1)")
    n = math.sqrt(EARTH_MU_M3_S2 / a**3)
    mean = elements.mean_anomaly_epoch_rad + n * (time_seconds - elements.epoch_seconds)
    eccentric = solve_kepler(mean, e)
    cos_e, sin_e = math.cos(eccentric), math.sin(eccentric)
    root = math.sqrt(1.0 - e * e)
    r_pf = (a * (cos_e - e), a * root * sin_e, 0.0)
    rate = n / (1.0 - e * cos_e)
    v_pf = (-a * rate * sin_e, a * rate * root * cos_e, 0.0)
    co, so = math.cos(elements.raan_rad), math.sin(elements.raan_rad)
    cw, sw = math.cos(elements.argument_of_perigee_rad), math.sin(elements.argument_of_perigee_rad)
    ci, si = math.cos(elements.inclination_rad), math.sin(elements.inclination_rad)
    rot = ((co*cw-so*sw*ci, -co*sw-so*cw*ci, so*si),
           (so*cw+co*sw*ci, -so*sw+co*cw*ci, -co*si),
           (sw*si, cw*si, ci))
    position = tuple(sum(rot[row][j] * r_pf[j] for j in range(3)) for row in range(3))
    velocity = tuple(sum(rot[row][j] * v_pf[j] for j in range(3)) for row in range(3))
    theta = EARTH_ROTATION_RAD_S * time_seconds if earth_rotation else 0.0
    ct, st = math.cos(theta), math.sin(theta)
    ecef = (ct * position[0] + st * position[1], -st * position[0] + ct * position[1], position[2])
    return SatelliteState(elements.satellite_id, time_seconds, position, velocity, ecef)
