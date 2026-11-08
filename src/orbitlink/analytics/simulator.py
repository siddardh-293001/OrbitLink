"""Deterministic end-to-end V1 simulation runner."""

from __future__ import annotations

from orbitlink.communication.rf_link import link_budget
from orbitlink.core.models import GroundSite, SimulationResult
from orbitlink.geometry.visibility import visible_satellites
from orbitlink.mobility.handover import HandoverManager
from orbitlink.orbit.constellation import generate_constellation
from orbitlink.orbit.keplerian import propagate


def run_simulation(*, site: GroundSite | None = None, duration_seconds: int = 7200,
                   timestep_seconds: int = 10, minimum_elevation_deg: float = 25,
                   hysteresis_deg: float = 5, planes: int = 3, satellites_per_plane: int = 8,
                   altitude_km: float = 550, inclination_deg: float = 53,
                   earth_rotation: bool = True) -> SimulationResult:
    if duration_seconds < 0 or timestep_seconds <= 0:
        raise ValueError("duration must be non-negative and timestep must be positive")
    site = site or GroundSite("Demo terminal", 37.7749, -122.4194)
    elements = generate_constellation(planes=planes, satellites_per_plane=satellites_per_plane,
                                      altitude_km=altitude_km, inclination_deg=inclination_deg)
    manager = HandoverManager(hysteresis_deg, minimum_elevation_deg)
    result = SimulationResult()
    for t in range(0, duration_seconds + 1, timestep_seconds):
        states = [propagate(item, t, earth_rotation=earth_rotation) for item in elements]
        visible = visible_satellites(site, states, minimum_elevation_deg)
        serving_id = manager.update(t, visible)
        serving = next((x for x in visible if x.satellite_id == serving_id), None)
        budget = link_budget(serving.range_m) if serving else None
        result.times_seconds.append(float(t))
        result.visible_counts.append(len(visible))
        result.serving_satellite_ids.append(serving_id)
        result.serving_elevations_deg.append(serving.elevation_deg if serving else None)
        result.serving_delays_ms.append(budget.propagation_delay_s * 1000 if budget else None)
        result.serving_snr_db.append(budget.snr_db if budget else None)
        result.satellite_states.append(states)
    result.handovers = manager.events
    return result
