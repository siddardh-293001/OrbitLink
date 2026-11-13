"""First-order secular J2 mean-element approximation (no drag/short-period terms).

Reference: https://juliaspace.github.io/SatelliteToolboxPropagators.jl/stable/man/propagators/j2/
"""
import math
from dataclasses import replace
from orbitlink.core.constants import EARTH_MU_M3_S2, EARTH_RADIUS_M, EARTH_ROTATION_RAD_S
from orbitlink.core.models import OrbitalElements, SatelliteState
from orbitlink.orbit.keplerian import propagate

EARTH_J2 = 1.08262668e-3


def secular_rates(elements: OrbitalElements) -> tuple[float, float, float]:
    """Return RAAN, perigee, and corrected mean-anomaly rates in rad/s."""
    a, e = elements.semi_major_axis_m, elements.eccentricity
    if not math.isfinite(a) or a <= 0 or not 0 <= e < 1:
        raise ValueError("J2 requires finite positive semimajor axis and elliptic eccentricity")
    n = math.sqrt(EARTH_MU_M3_S2 / a**3)
    factor = EARTH_J2 * n * (EARTH_RADIUS_M / (a * (1-e*e)))**2
    c = math.cos(elements.inclination_rad)
    return (-1.5*factor*c, .75*factor*(5*c*c-1),
            n + .75*factor*math.sqrt(1-e*e)*(3*c*c-1))


def propagate_j2(elements: OrbitalElements, time_seconds: float, *, earth_rotation: bool = True) -> SatelliteState:
    node, perigee, mean = secular_rates(elements)
    def position(t):
        dt = t-elements.epoch_seconds
        updated = replace(elements, raan_rad=elements.raan_rad+node*dt,
            argument_of_perigee_rad=elements.argument_of_perigee_rad+perigee*dt,
            mean_anomaly_epoch_rad=elements.mean_anomaly_epoch_rad+mean*dt, epoch_seconds=t)
        return propagate(updated,t,earth_rotation=False).position_eci_m
    xyz = position(time_seconds)
    # Differentiate the complete moving mean-element trajectory, including precession.
    before, after = position(time_seconds-.05), position(time_seconds+.05)
    velocity = tuple((b-a)/.1 for a,b in zip(before,after))
    theta = EARTH_ROTATION_RAD_S*time_seconds if earth_rotation else 0
    c,s=math.cos(theta),math.sin(theta)
    fixed=(c*xyz[0]+s*xyz[1],-s*xyz[0]+c*xyz[1],xyz[2])
    return SatelliteState(elements.satellite_id,time_seconds,xyz,velocity,fixed)
