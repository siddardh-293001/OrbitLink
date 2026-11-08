"""Repeatable parameter sweeps over the simulator's measured outputs."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass

from orbitlink.analytics.simulator import run_simulation
from orbitlink.analytics.statistics import summarize
from orbitlink.core.models import GroundSite


@dataclass(frozen=True)
class ExperimentRun:
    experiment: str
    value: float
    repetition: int
    parameters_json: str
    availability_percent: float
    mean_visible_satellites: float
    mean_propagation_delay_ms: float | None
    mean_snr_db: float | None
    handover_count: int


def run_parameter_sweep(*, parameter: str, values: list[float], repetitions: int = 3,
                        duration_seconds: int = 3600, timestep_seconds: int = 30,
                        minimum_elevation_deg: float = 25, planes: int = 3,
                        satellites_per_plane: int = 8, altitude_km: float = 550,
                        inclination_deg: float = 53,
                        site: GroundSite | None = None) -> list[ExperimentRun]:
    allowed = {"minimum_elevation_deg", "planes", "satellites_per_plane", "altitude_km", "inclination_deg"}
    if parameter not in allowed:
        raise ValueError(f"parameter must be one of {sorted(allowed)}")
    if not values or repetitions < 1:
        raise ValueError("provide at least one scenario value and one repetition")
    base = {"minimum_elevation_deg": minimum_elevation_deg, "planes": planes,
            "satellites_per_plane": satellites_per_plane, "altitude_km": altitude_km,
            "inclination_deg": inclination_deg}
    records = []
    for value in values:
        params = dict(base)
        params[parameter] = int(value) if parameter in {"planes", "satellites_per_plane"} else value
        for repetition in range(1, repetitions + 1):
            result = run_simulation(site=site, duration_seconds=duration_seconds,
                timestep_seconds=timestep_seconds, minimum_elevation_deg=params["minimum_elevation_deg"],
                planes=int(params["planes"]), satellites_per_plane=int(params["satellites_per_plane"]),
                altitude_km=params["altitude_km"], inclination_deg=params["inclination_deg"])
            summary = result.summary()
            records.append(ExperimentRun(parameter, value, repetition,
                json.dumps(params, sort_keys=True), summary["availability_percent"],
                summary["mean_visible_satellites"], summary["mean_propagation_delay_ms"],
                summary["mean_snr_db"], int(summary["handover_count"])))
    return records


def summarize_experiment(records: list[ExperimentRun]) -> dict[str, dict[str, float | int | None]]:
    groups: dict[float, list[ExperimentRun]] = {}
    for record in records:
        groups.setdefault(record.value, []).append(record)
    result = {}
    for value, runs in sorted(groups.items()):
        label = str(int(value)) if float(value).is_integer() else str(value)
        result[label] = {
            "availability_percent": summarize([r.availability_percent for r in runs]),
            "mean_visible_satellites": summarize([r.mean_visible_satellites for r in runs]),
            "mean_propagation_delay_ms": summarize([r.mean_propagation_delay_ms for r in runs if r.mean_propagation_delay_ms is not None]),
            "mean_snr_db": summarize([r.mean_snr_db for r in runs if r.mean_snr_db is not None]),
            "handover_count": summarize([float(r.handover_count) for r in runs]),
        }
    return result


def experiment_csv(records: list[ExperimentRun]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(asdict(records[0]).keys()) if records else
                            [field for field in ExperimentRun.__dataclass_fields__])
    writer.writeheader()
    writer.writerows(asdict(record) for record in records)
    return output.getvalue()
