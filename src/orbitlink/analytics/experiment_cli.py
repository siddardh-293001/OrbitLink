"""CLI entry point for a small reproducible parameter sweep."""

from __future__ import annotations

import argparse
import json

from orbitlink.analytics.experiments import run_parameter_sweep, summarize_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a reproducible ORBITLINK scenario sweep")
    parser.add_argument("parameter", choices=["minimum_elevation_deg", "planes", "satellites_per_plane", "altitude_km", "inclination_deg"])
    parser.add_argument("values", help="Comma-separated scenario values")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--duration-seconds", type=int, default=3600)
    parser.add_argument("--timestep-seconds", type=int, default=30)
    args = parser.parse_args()
    values = [float(value) for value in args.values.split(",")]
    runs = run_parameter_sweep(parameter=args.parameter, values=values,
        repetitions=args.repetitions, duration_seconds=args.duration_seconds,
        timestep_seconds=args.timestep_seconds)
    print(json.dumps({"summaries": summarize_experiment(runs),
                      "runs": [run.__dict__ for run in runs]}, indent=2))


if __name__ == "__main__":
    main()
