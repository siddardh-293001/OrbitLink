# Delivery phases and verification gates

## 1. Foundation and ORBITLINK DEMO

Implement shared models/configuration, a synthetic two-body Keplerian propagator, 3 planes × 8 satellites, Earth-fixed geometry, elevation visibility, a basic RF link budget, automatic selection with hysteresis, event logging, coverage/availability analytics and the initial dashboard.

**Gate:** standard-library unit tests cover Kepler's equation, orbital period, coordinate conversion, elevation, FSPL, delay and handover; a deterministic two-hour simulation has 24 unique satellites and produces a complete metrics summary. No assumed throughput or packet-loss figures are shown.

## 2. Realism

Add TLE parsing and validation, SGP4 propagation, explicit TEME-to-Earth-fixed transforms, Walker configuration, larger constellations, and reproducible propagation comparisons. Stale or malformed TLE data must be surfaced.

**Gate:** trusted reference vectors and epoch/data-quality cases pass; TEME is never labeled generic ECI/ECEF.

## 3. Communications

Extend RF with antenna, atmospheric, pointing, polarization, receiver noise, interference, Doppler and link-margin assumptions. Add optical inter-satellite line-of-sight, acquisition constraints and dynamic availability. Every engineering assumption remains configurable.

**Gate:** equations match reference calculations and optical links obey Earth occultation and constraints.

## 4. Network intelligence

Represent terminals, gateways, satellites and RF/optical links as a time-varying graph. Add shortest-delay/link-quality/congestion-aware routes, packet and queue simulation, and advanced/predictive handover.

**Gate:** graph connectivity, route cost, packet accounting, congestion and handover behavior pass controlled scenarios.

## 5. Research and refinement

Add experiment definitions for altitude, density, elevation, handover, routing, gateways, traffic and optical links; repeated-run statistics and CSV output; richer dashboard views; visual and numerical validation documentation.

**Gate:** seeded experiments reproduce, summaries include variability and confidence intervals where justified, and reported metrics come from implemented models.

## Delivery record

Record for each phase: scope completed, checks run and outcome, known limitations, and commit SHA. Do not begin the next phase until the previous exit gate is green.

| Phase | Verification | Outcome |
|---|---|---|
| 1. Foundation and demo | `python -m unittest discover -s tests -v` (9 tests); `python -m compileall -q src tests`; `python -m orbitlink.cli` | PASS. 24 unique satellites; 721 samples over two hours; 16 handovers; 26.21% availability; metrics are measured by the implemented geometric/RF model. Dashboard runtime needs the optional Streamlit/Plotly extras. |
