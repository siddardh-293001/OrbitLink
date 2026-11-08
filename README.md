# ORBITLINK

ORBITLINK is a reproducible simulator for how low Earth orbit (LEO) satellite geometry affects ground-terminal connectivity. It starts with a validated synthetic Keplerian demo and grows in place into a configurable network and research simulator.

## Project phases

| Phase | Scope | Exit check |
|---|---|---|
| 1. Foundation and demo | Core models, 24-satellite Keplerian constellation, visibility, RF link budget, satellite selection, handover, analytics, Streamlit dashboard | Numerical checks pass; 24 unique satellites; two-hour run produces measured coverage and handover metrics |
| 2. Realism | TLE ingestion, SGP4/TEME transforms, configurable Walker constellations and coordinate validation | Propagation comparisons and epoch/data-quality checks pass |
| 3. Communications | Extended RF, optical line-of-sight links and dynamic link eligibility | Hand-calculated RF references and optical visibility scenarios pass |
| 4. Network intelligence | Dynamic graph, routing strategies, queues and packet traffic, predictive handover | Controlled routing, traffic and handover scenarios pass |
| 5. Research and refinement | Reproducible experiments, statistical summaries, exports, dashboard refinement and validation report | Repeated runs reproduce results and report uncertainty transparently |

Each phase is designed to be verified independently before its milestone is committed. Version 1 values are demonstration assumptions, not official constellation or proprietary hardware specifications. The V1 demo reports geometry and RF link metrics. The later packet model reports throughput and packet loss only from its simulated packets and explicitly assumed link capacities.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dashboard,dev]'
python -m unittest discover -s tests -v
streamlit run src/orbitlink/dashboard/app.py
```

Run the deterministic simulation summary with `python -m orbitlink.cli` (after `pip install -e .`). See [docs/PHASES.md](docs/PHASES.md) for detailed milestones and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module map.

Run an experiment sweep, for example `orbitlink-experiment altitude_km 450,550,650 --repetitions 3 --duration-seconds 3600`. The dashboard also exposes route and packet scenarios and can export raw experiment runs as CSV. Packet throughput depends on the link-capacity assumption shown in the scenario controls.

## Architecture

The simulation engine is independent of Streamlit. Core models and configuration sit below orbit propagation, geometry, communication, mobility and analytics. Visualization and the dashboard consume engine outputs through explicit data models.
