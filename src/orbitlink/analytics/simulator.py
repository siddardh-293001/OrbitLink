"""Deterministic end-to-end V1 simulation runner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
                   earth_rotation: bool = True, eccentricity: float = 0,
                   phase_factor: int = 1, raan_offset_deg: float = 0,
                   plane_altitudes_km: list[float] | None = None,
                   plane_inclinations_deg: list[float] | None = None) -> SimulationResult:
    if duration_seconds < 0 or timestep_seconds <= 0:
        raise ValueError("duration must be non-negative and timestep must be positive")
    site = site or GroundSite("Demo terminal", 37.7749, -122.4194)
    elements = generate_constellation(planes=planes, satellites_per_plane=satellites_per_plane,
                                      altitude_km=altitude_km, inclination_deg=inclination_deg,
                                      eccentricity=eccentricity, phase_factor=phase_factor,
                                      raan_offset_deg=raan_offset_deg,
                                      plane_altitudes_km=plane_altitudes_km,
                                      plane_inclinations_deg=plane_inclinations_deg)
    manager = HandoverManager(hysteresis_deg, minimum_elevation_deg)
    result = SimulationResult(model_name="Synthetic Keplerian")
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


def run_tle_simulation(records, *, start_time_utc: datetime, site: GroundSite | None = None,
                       duration_seconds: int = 7200, timestep_seconds: int = 60,
                       minimum_elevation_deg: float = 25, hysteresis_deg: float = 5,
                       max_age_days: float = 14) -> SimulationResult:
    """Run the same link/visibility pipeline using TLEs propagated by SGP4.

    SGP4 outputs TEME states; ``propagate_tle`` rotates positions into the
    app's approximate Earth-fixed frame before the common geometry is applied.
    """
    from orbitlink.orbit.sgp4_backend import propagate_tle

    if duration_seconds < 0 or timestep_seconds <= 0:
        raise ValueError("duration must be non-negative and timestep must be positive")
    if not records:
        raise ValueError("at least one TLE record is required")
    catalog_ids = [record.satellite_id for record in records]
    if len(set(catalog_ids)) != len(catalog_ids):
        raise ValueError("TLE input contains duplicate satellite IDs")
    start = _as_utc(start_time_utc)
    end = start + timedelta(seconds=duration_seconds)
    problems = [(record.name, issue) for record in records
                for sample_time in (start, end)
                for issue in record.quality(sample_time, max_age_days=max_age_days)]
    if problems:
        raise ValueError("; ".join(f"{name}: {issue}" for name, issue in problems[:8]))

    site = site or GroundSite("Demo terminal", 37.7749, -122.4194)
    manager = HandoverManager(hysteresis_deg, minimum_elevation_deg)
    result = SimulationResult(model_name="TLE + SGP4", reference_time_utc=start.isoformat())
    for t in range(0, duration_seconds + 1, timestep_seconds):
        sample_time = start + timedelta(seconds=t)
        states = [propagate_tle(record, sample_time, max_age_days=max_age_days) for record in records]
        visible = visible_satellites(site, states, minimum_elevation_deg)
        serving_id = manager.update(t, visible)
        serving = next((item for item in visible if item.satellite_id == serving_id), None)
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


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
