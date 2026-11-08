# ORBITLINK Version 2 progress

Version 2 is in progress. This is a delivery ledger for the original project plan's realism and advanced-simulator scope; a green item here does not imply the whole Version 2 plan is complete.

## Delivered in this increment

- Parse named and unnamed TLE catalogs, reject malformed/checksum-invalid entries and duplicate catalog IDs, and report TLE epochs that are future-dated or older than the selected age limit.
- Propagate TLEs with SGP4 and preserve TEME position/velocity separately from the GMST-rotated PEF position used by shared ground-geometry calculations.
- Run TLE states through the same elevation visibility, RF link, handover, availability, delay, and SNR calculations used by the synthetic scenario.
- Compare the epoch state against the public Vallado AIAA 2006-6753 Vanguard 1 position and velocity vector.
- Configure synthetic plane count, satellites per plane, altitude, inclination, Walker phase, ellipticity, and initial RAAN; reject nonphysical inputs.
- Label the last-run model and reference time, report TLE quality before a run, distinguish elapsed simulation time from UTC, show sampled TLE trails, and warn when scenario controls have changed since the last run.

## Still in Version 2 scope

- Higher-accuracy TEME-to-terrestrial transforms using UT1 and polar motion, with a clear precision and time-data policy.
- Multi-altitude and multi-inclination Walker planes; J2 perturbations and broader orbit perturbation support.
- Reproducible propagation comparisons across more reference epochs and orbit regimes.
- Full advanced RF and optical assumptions, dynamic topology/routing/packet studies, and experiment/dashboard refinements described in `PHASES.md`.

## Verification

Run from the repository root after installing the `full` optional dependencies:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src tests
```

The TLE reference-vector test requires `sgp4`; UI smoke checks use Streamlit's `AppTest`.
