"""Elevation-based serving selection with hysteresis and event history."""

from __future__ import annotations

from orbitlink.core.models import HandoverEvent, LookAngle


class HandoverManager:
    def __init__(self, hysteresis_deg: float = 5.0, minimum_elevation_deg: float = 25.0) -> None:
        if hysteresis_deg < 0:
            raise ValueError("hysteresis must be non-negative")
        self.hysteresis_deg = hysteresis_deg
        self.minimum_elevation_deg = minimum_elevation_deg
        self.serving_satellite_id: str | None = None
        self.events: list[HandoverEvent] = []

    def update(self, time_seconds: float, candidates: list[LookAngle]) -> str | None:
        eligible = {candidate.satellite_id: candidate for candidate in candidates
                    if candidate.visible and candidate.elevation_deg >= self.minimum_elevation_deg}
        current = eligible.get(self.serving_satellite_id) if self.serving_satellite_id else None
        best = max(eligible.values(), key=lambda x: x.elevation_deg, default=None)
        next_id = self.serving_satellite_id if current else (best.satellite_id if best else None)
        if current and best and best.satellite_id != current.satellite_id:
            if best.elevation_deg >= current.elevation_deg + self.hysteresis_deg:
                next_id = best.satellite_id
        if next_id != self.serving_satellite_id:
            old = self.serving_satellite_id
            reason = "initial acquisition" if old is None else ("serving satellite below threshold" if current is None else "elevation advantage exceeded hysteresis")
            self.events.append(HandoverEvent(time_seconds, old, next_id, reason))
            self.serving_satellite_id = next_id
        return self.serving_satellite_id
