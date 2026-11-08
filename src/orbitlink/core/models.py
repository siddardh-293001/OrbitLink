"""Small, dependency-free data models shared by simulator modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GroundSite:
    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_m: float = 0.0

    def __post_init__(self) -> None:
        if not -90 <= self.latitude_deg <= 90:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude_deg <= 180:
            raise ValueError("longitude must be between -180 and 180 degrees")


@dataclass(frozen=True)
class OrbitalElements:
    satellite_id: str
    semi_major_axis_m: float
    eccentricity: float
    inclination_rad: float
    raan_rad: float
    argument_of_perigee_rad: float
    mean_anomaly_epoch_rad: float
    epoch_seconds: float = 0.0


@dataclass(frozen=True)
class SatelliteState:
    satellite_id: str
    time_seconds: float
    position_eci_m: tuple[float, float, float]
    velocity_eci_m_s: tuple[float, float, float]
    position_ecef_m: tuple[float, float, float]


@dataclass(frozen=True)
class LookAngle:
    satellite_id: str
    range_m: float
    azimuth_deg: float
    elevation_deg: float
    visible: bool


@dataclass(frozen=True)
class LinkBudget:
    distance_m: float
    frequency_hz: float
    free_space_path_loss_db: float
    received_power_dbw: float
    noise_power_dbw: float
    snr_db: float
    propagation_delay_s: float
    available: bool


@dataclass(frozen=True)
class HandoverEvent:
    time_seconds: float
    previous_satellite_id: str | None
    next_satellite_id: str | None
    reason: str


@dataclass
class SimulationResult:
    times_seconds: list[float] = field(default_factory=list)
    visible_counts: list[int] = field(default_factory=list)
    serving_satellite_ids: list[str | None] = field(default_factory=list)
    serving_elevations_deg: list[float | None] = field(default_factory=list)
    serving_delays_ms: list[float | None] = field(default_factory=list)
    serving_snr_db: list[float | None] = field(default_factory=list)
    handovers: list[HandoverEvent] = field(default_factory=list)
    satellite_states: list[list[SatelliteState]] = field(default_factory=list)

    def summary(self) -> dict[str, float | int | None]:
        n = len(self.times_seconds)
        connected = sum(s is not None for s in self.serving_satellite_ids)
        delays = [x for x in self.serving_delays_ms if x is not None]
        snrs = [x for x in self.serving_snr_db if x is not None]
        return {
            "samples": n,
            "handover_count": len(self.handovers),
            "availability_percent": (100.0 * connected / n) if n else 0.0,
            "mean_visible_satellites": (sum(self.visible_counts) / n) if n else 0.0,
            "mean_propagation_delay_ms": (sum(delays) / len(delays)) if delays else None,
            "mean_snr_db": (sum(snrs) / len(snrs)) if snrs else None,
        }
