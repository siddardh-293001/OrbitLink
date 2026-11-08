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
| 2. Realism | Full suite (29 tests), including Vallado Vanguard 1 epoch position/velocity reference, TLE catalog/duplicate/epoch checks, TLE-driven simulation, Walker parameter and physical-input checks; compile and whitespace checks | PARTIAL, substantially advanced. Catalog ingestion and SGP4 now run through the common visibility/handover pipeline; synthetic Walker phase, ellipticity, plane offset and basic scenario controls are configurable. The Vallado reference vector passes with the optional SGP4 dependency. The TEME→PEF rotation remains an explicitly approximate GMST/UTC implementation without UT1/polar-motion corrections; multi-altitude Walker, J2, a high-accuracy frame path and broader propagation comparisons remain. |
| 3. Communications | 3 advanced RF/optical checks; full suite (16 tests); compile and whitespace checks | PASS. Loss inputs and Doppler are reflected in SNR/margin; Shannon capacity is labeled as an idealized upper bound. Optical visibility rejects Earth occultation and reports propagation delay. |
| 4. Network intelligence | 4 graph/route/packet/selection checks; full suite (20 tests); compile and whitespace checks | PASS. Route costs are strategy-selectable, unavailable links are excluded, packet outcomes are accounted for, queues add serialization delay, and predictive/signal handover scoring is available. |
| 5. Research and refinement | 3 statistics/experiment checks; full suite (23 tests); compile, two-scenario sweep smoke run, and whitespace checks | PASS. Parameter sweeps are repeatable, raw runs export to CSV, percentiles and sample variability are reported, and confidence intervals are omitted for one-run or zero-variation samples. Dashboard runtime still needs the optional Streamlit/Plotly packages. |

## Remaining environment checks

- Phase 2 remains partial pending the higher-accuracy frame work and remaining orbital configuration/comparison items listed above.
- Streamlit AppTest covers the synthetic dashboard and the TLE-mode upload prompt; a real browser upload/deployment smoke test remains a separate release check.
- The repository is public at `https://github.com/siddardh-293001/OrbitLink`; Version 2 work is being delivered on `main` after local verification.
- The final project report and demonstration recording from the original deliverables list have not been produced.
