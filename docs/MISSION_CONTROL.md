# Orbital Midnight mission control

Stage 1: the existing Streamlit dashboard uses the supplied semantic palette and retains research, packet, experiment and educational views. Run `streamlit run src/orbitlink/dashboard/app.py`.

Stage 2: React mission control uses the same Python engine via `/api/scenario`, with cached 30-minute orbital scenarios, catalog selection, terminal controls, selectable satellites, playback and event history. Run `python -m orbitlink.dashboard.server`, then open http://localhost:8000. React, Plotly and fonts currently load from public CDNs. This preview retains Plotly as its globe renderer; a dedicated globe renderer and full feature parity with Streamlit remain future work.

The CSS tokens are in frontend/design-system.css and Python tokens in src/orbitlink/dashboard/colors.py. Only calculated orbital and simulated link values are displayed; operator telemetry is unavailable.
