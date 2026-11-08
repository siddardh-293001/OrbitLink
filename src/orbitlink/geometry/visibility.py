"""Visibility helpers for a ground terminal and a state snapshot."""

from orbitlink.core.models import EarthFixedState, GroundSite, LookAngle
from orbitlink.geometry.transforms import look_angle


def visible_satellites(site: GroundSite, states: list[EarthFixedState], minimum_elevation_deg: float) -> list[LookAngle]:
    angles = [look_angle(site, state.satellite_id, state.position_ecef_m, minimum_elevation_deg)
              for state in states]
    return sorted((angle for angle in angles if angle.visible), key=lambda angle: angle.elevation_deg, reverse=True)
