# ORBITLINK — LEO Connectivity Planning and Resilience Platform

## Problem statement
Remote and temporary sites need dependable data delivery despite intermittent connectivity. Orbital visualization alone does not reveal application behaviour during an outage. ORBITLINK combines public orbital predictions with controlled link emulation and persistent message delivery to help engineers explain connectivity gaps and evaluate recovery strategies.

## Working exhibit
Open Resilience lab. Send one message while connected, trigger an outage, send two more messages, and restore the connection. Compare direct-only delivery with the SQLite-backed queue, inspect delivery delays, and export the report. These are real HTTP application messages handled by the demo server; the link state is controlled emulation rather than satellite transmission. Session queues are isolated using browser session identifiers, not authenticated accounts. Hosting filesystem persistence does not extend across Render redeployments.

## Evidence
Controlled checks cover queue persistence after reopening the database, successful recovery, direct-only baseline counts and idempotent repeated recovery. Results from the exhibit must be reported as measured demo results, not claims about Starlink performance.

## Next milestones
Obstruction-aware comparison of candidate sites; sky masks and visibility-gap reports; independent orbital reference comparisons; configurable latency/loss emulation; authenticated deployments with durable storage; measured field-network validation. These are not yet implemented.
