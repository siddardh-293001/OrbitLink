"""Alternative and predictive serving-satellite scoring strategies."""

from __future__ import annotations

from orbitlink.core.models import LookAngle


def select_candidate(candidates: list[LookAngle], *, strategy: str = "maximum_elevation",
                     snr_by_id: dict[str, float] | None = None,
                     elevation_rate_by_id: dict[str, float] | None = None,
                     lookahead_seconds: float = 30.0) -> LookAngle | None:
    eligible = [candidate for candidate in candidates if candidate.visible]
    if not eligible:
        return None
    snr_by_id = snr_by_id or {}
    elevation_rate_by_id = elevation_rate_by_id or {}
    if strategy == "maximum_elevation":
        score = lambda x: x.elevation_deg
    elif strategy == "strongest_signal":
        score = lambda x: snr_by_id.get(x.satellite_id, float("-inf"))
    elif strategy == "predictive":
        score = lambda x: x.elevation_deg + elevation_rate_by_id.get(x.satellite_id, 0.0) * lookahead_seconds
    elif strategy == "multi_criteria":
        score = lambda x: x.elevation_deg + 0.25 * snr_by_id.get(x.satellite_id, 0.0)
    else:
        raise ValueError(f"unknown satellite-selection strategy: {strategy}")
    return max(eligible, key=score)
