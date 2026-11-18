# ORBITLINK expo demonstration and evidence

## 5-minute presentation

1. **Problem (30 seconds):** remote-site teams need to plan terminal placement and preserve important messages during connectivity interruptions.
2. **Orbit context (45 seconds):** show Starlink or Iridium, catalog retrieval date, and predicted positions. These are public mean-element predictions, not live operator telemetry.
3. **Planning (60 seconds):** open Site planner, compare rooftop/building/tree masks at identical coordinates. Explain azimuth sectors and user-entered elevations. Compare sampled visibility and export the printable report. A five-minute sample can miss brief gaps.
4. **Working resilience system (90 seconds):** open Resilience lab and run the automated trial. Identify the outage, three queued messages, restored link and measured delivery delays. The trial compares five queued-path messages with the two-message direct-only baseline under its stated drop assumption. Read the actual displayed result rather than promising a result in advance.
5. **Explanation and evidence (45 seconds):** show Signal journey, then distinguish the illustrative route from calculated geometry and real local HTTP/SQLite message handling.
6. **Conclusion (30 seconds):** demonstrate the exported reports and explain field validation as the next step.

## Questions to prepare for

- **Is it live Starlink control?** No. Public orbit data drives predictions. Operator routing, capacity and private telemetry are unavailable.
- **What is implemented beyond visualization?** Obstruction-mask comparison, ranking and reports; real HTTP message handling; SQLite queue persistence; controlled outage/recovery; baseline measurement and exports.
- **Is the predicted visibility percentage service availability?** No. It is the proportion of sampled moments with a geometrically reachable satellite after the supplied mask.
- **Does queue persistence survive hosting redeploys?** Not on the current free hosting filesystem. Durable production storage is future work.
- **What is validated?** Controlled obstruction effects, gap calculations, malformed-mask rejection, message isolation, input validation, database reopening, outage recovery, and repeated-recovery delivery accounting. Earlier orbital tests cover reference vectors and J2 behaviour.
- **What remains?** Browser interaction automation, higher-resolution planning, surveyed obstructions, field measurements, durable authenticated operation and production hosting performance.

## Reproducible focused checks

`PYTHONPATH=src python -m unittest discover -s tests -p test_planning_resilience.py -v`

Four tests passed locally on 2026-11-19. This establishes controlled software behaviour, not independent field validation or guaranteed real-world improvements.
