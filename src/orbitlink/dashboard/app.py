"""Interactive V1 dashboard for the ORBITLINK demonstration."""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from orbitlink.analytics.simulator import run_simulation
from orbitlink.analytics.experiments import experiment_csv, run_parameter_sweep, summarize_experiment
from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.core.constants import SPEED_OF_LIGHT_M_S
from orbitlink.core.models import GroundSite
from orbitlink.communication.laser_link import optical_link
from orbitlink.geometry.transforms import geodetic_to_ecef
from orbitlink.geometry.visibility import visible_satellites
from orbitlink.network.packet import Packet, simulate_packets
from orbitlink.network.topology import LinkEdge, NetworkGraph
from orbitlink.orbit.constellation import generate_constellation
from orbitlink.orbit.keplerian import propagate

st.set_page_config(page_title="ORBITLINK | LEO Simulator", page_icon="🛰️", layout="wide")
st.title("🛰️ ORBITLINK")
st.caption("LEO satellite connectivity simulator · Synthetic two-body demonstration scenario")

with st.sidebar:
    st.header("Scenario")
    latitude = st.number_input("Terminal latitude (°)", min_value=-90.0, max_value=90.0, value=37.7749)
    longitude = st.number_input("Terminal longitude (°)", min_value=-180.0, max_value=180.0, value=-122.4194)
    min_elevation = st.slider("Minimum elevation (°)", 5, 60, 25)
    duration_hours = st.slider("Duration (hours)", 0.25, 2.0, 2.0, 0.25)
    timestep = st.select_slider("Timestep (seconds)", options=[10, 30, 60], value=10)
    run = st.button("Run simulation", type="primary", use_container_width=True)

site = GroundSite("Dashboard terminal", latitude, longitude)
if "result" not in st.session_state or run:
    with st.spinner("Propagating constellation and measuring links…"):
        st.session_state.result = run_simulation(site=site, duration_seconds=int(duration_hours * 3600),
            timestep_seconds=timestep, minimum_elevation_deg=min_elevation)
result = st.session_state.result
summary = result.summary()

overview, orbit_tab, ground_tab, communication, handover, analytics, network_tab, experiment_tab = st.tabs(
    ["Overview", "Orbit Viewer", "Ground Track", "Communication", "Handover", "Analytics", "Network", "Experiments"])

with overview:
    metrics = st.columns(4)
    metrics[0].metric("Constellation", "24", "3 planes × 8 satellites")
    metrics[1].metric("Availability", f"{summary['availability_percent']:.1f}%")
    metrics[2].metric("Visible satellites", f"{summary['mean_visible_satellites']:.2f}", "mean per sample")
    metrics[3].metric("Handovers", str(summary["handover_count"]))
    st.info("Calculated geometry and link metrics are shown. Throughput and packet loss require a traffic model and are not estimated in this phase.")

with orbit_tab:
    index = st.slider("Simulation sample", 0, len(result.times_seconds) - 1, min(0, len(result.times_seconds) - 1))
    states = result.satellite_states[index]
    u, v = 36, 18
    sphere_x, sphere_y, sphere_z = [], [], []
    for i in range(u + 1):
        row_x, row_y, row_z = [], [], []
        lat_r = math.pi * (i / u - 0.5)
        for j in range(v + 1):
            lon_r = 2 * math.pi * j / v
            row_x.append(EARTH_RADIUS_M * math.cos(lat_r) * math.cos(lon_r) / 1000)
            row_y.append(EARTH_RADIUS_M * math.cos(lat_r) * math.sin(lon_r) / 1000)
            row_z.append(EARTH_RADIUS_M * math.sin(lat_r) / 1000)
        sphere_x.append(row_x); sphere_y.append(row_y); sphere_z.append(row_z)
    fig = go.Figure(go.Surface(x=sphere_x, y=sphere_y, z=sphere_z, colorscale=[[0, "#112744"], [1, "#23558a"]],
                               showscale=False, opacity=0.88, name="Earth"))
    fig.add_trace(go.Scatter3d(x=[s.position_ecef_m[0]/1000 for s in states],
        y=[s.position_ecef_m[1]/1000 for s in states], z=[s.position_ecef_m[2]/1000 for s in states],
        mode="markers", marker={"size": 4, "color": "#ffcc66"}, text=[s.satellite_id for s in states], name="Satellites"))
    fig.update_layout(height=650, margin={"l": 0, "r": 0, "t": 20, "b": 0}, scene={"aspectmode": "data"})
    st.plotly_chart(fig, use_container_width=True)

with ground_tab:
    fig = go.Figure()
    for sat_id in ["P01-S01", "P02-S01", "P03-S01", "P01-S05"]:
        element = next(x for x in generate_constellation() if x.satellite_id == sat_id)
        latitudes, longitudes = [], []
        for t in range(0, int(duration_hours * 3600) + 1, max(timestep, 30)):
            x, y, z = propagate(element, t).position_ecef_m
            latitudes.append(math.degrees(math.atan2(z, math.hypot(x, y))))
            longitudes.append(math.degrees(math.atan2(y, x)))
        fig.add_trace(go.Scatter(x=longitudes, y=latitudes, mode="lines", name=sat_id))
    fig.add_trace(go.Scatter(x=[longitude], y=[latitude], mode="markers", marker={"size": 12, "color": "red"}, name="Terminal"))
    fig.update_layout(xaxis_title="Longitude (°)", yaxis_title="Latitude (°)", height=520,
                      xaxis={"range": [-180, 180]}, yaxis={"range": [-90, 90]})
    st.plotly_chart(fig, use_container_width=True)

with communication:
    col1, col2 = st.columns(2)
    col1.metric("Mean propagation delay", f"{summary['mean_propagation_delay_ms']:.2f} ms" if summary["mean_propagation_delay_ms"] is not None else "—")
    col2.metric("Mean link SNR", f"{summary['mean_snr_db']:.1f} dB" if summary["mean_snr_db"] is not None else "—")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[t/60 for t in result.times_seconds], y=result.serving_delays_ms, name="Propagation delay", connectgaps=False))
    fig.update_layout(xaxis_title="Simulation time (minutes)", yaxis_title="Delay (ms)", height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Single-hop free-space propagation delay and a basic configurable RF link budget; no throughput claim is made.")

with handover:
    st.metric("Handover events", len(result.handovers))
    st.line_chart({"Serving elevation (°)": result.serving_elevations_deg}, x_label="Sample", y_label="Elevation (°)")
    st.dataframe([{"time_min": event.time_seconds / 60, "from": event.previous_satellite_id,
                   "to": event.next_satellite_id, "reason": event.reason} for event in result.handovers], use_container_width=True)

with analytics:
    st.json(summary)
    st.line_chart({"Visible satellites": result.visible_counts}, x_label="Sample", y_label="Count")
    csv = "time_s,visible_satellites,serving_satellite,elevation_deg,delay_ms,snr_db\n" + "\n".join(
        f"{t},{count},{serving or ''},{elev or ''},{delay or ''},{snr or ''}"
        for t, count, serving, elev, delay, snr in zip(result.times_seconds, result.visible_counts,
            result.serving_satellite_ids, result.serving_elevations_deg, result.serving_delays_ms, result.serving_snr_db))
    st.download_button("Download measurements (CSV)", csv, "orbitlink-v1-metrics.csv", "text/csv")

with network_tab:
    st.caption("Connectivity is rebuilt from geometry at the selected orbit sample. Packet capacity is an explicit scenario assumption.")
    capacity_mbps = st.number_input("Per-link packet capacity assumption (Mbps)", min_value=1.0, max_value=100000.0, value=50.0, step=1.0)
    gateway = GroundSite("Demo gateway", 34.0522, -118.2437)
    states = result.satellite_states[index]
    terminal_links = visible_satellites(site, states, min_elevation)
    gateway_links = visible_satellites(gateway, states, min_elevation)
    graph = NetworkGraph(nodes={"terminal", "gateway"})
    capacity_bps = capacity_mbps * 1_000_000
    for view in terminal_links:
        distance = view.range_m
        graph.add_edge(LinkEdge("terminal", view.satellite_id, distance / SPEED_OF_LIGHT_M_S,
            distance, capacity_bps=capacity_bps, link_type="rf"))
        graph.add_edge(LinkEdge(view.satellite_id, "terminal", distance / SPEED_OF_LIGHT_M_S,
            distance, capacity_bps=capacity_bps, link_type="rf"))
    for view in gateway_links:
        distance = view.range_m
        graph.add_edge(LinkEdge(view.satellite_id, "gateway", distance / SPEED_OF_LIGHT_M_S,
            distance, capacity_bps=capacity_bps, link_type="rf"))
        graph.add_edge(LinkEdge("gateway", view.satellite_id, distance / SPEED_OF_LIGHT_M_S,
            distance, capacity_bps=capacity_bps, link_type="rf"))
    for left in states:
        for right in states:
            if left.satellite_id >= right.satellite_id:
                continue
            optical = optical_link(left.position_ecef_m, right.position_ecef_m, maximum_range_m=5_000_000)
            if optical.available:
                graph.add_edge(LinkEdge(left.satellite_id, right.satellite_id, optical.propagation_delay_s,
                    optical.distance_m, capacity_bps=capacity_bps, link_type="optical"))
                graph.add_edge(LinkEdge(right.satellite_id, left.satellite_id, optical.propagation_delay_s,
                    optical.distance_m, capacity_bps=capacity_bps, link_type="optical"))
    route = graph.shortest_path("terminal", "gateway", strategy="minimum_delay")
    packets = [Packet(f"pkt-{n:03d}", "terminal", "gateway", 1200, n * 0.1) for n in range(20)]
    traffic = simulate_packets(packets, graph)
    cols = st.columns(4)
    cols[0].metric("Route", "Available" if route else "Unavailable")
    cols[1].metric("Packet delivery", f"{traffic.delivery_ratio * 100:.1f}%")
    cols[2].metric("Mean end-to-end latency", f"{traffic.mean_latency_s * 1000:.2f} ms" if traffic.mean_latency_s is not None else "—")
    cols[3].metric("Measured throughput", f"{traffic.throughput_bps / 1e6:.2f} Mbps")
    if route:
        st.write("Selected route:", " → ".join(route[0]))
    else:
        st.warning("No path connects the terminal and gateway at this simulation time.")
    points = {state.satellite_id: tuple(value / 1000 for value in state.position_ecef_m) for state in states}
    points["terminal"] = tuple(value / 1000 for value in geodetic_to_ecef(site))
    points["gateway"] = tuple(value / 1000 for value in geodetic_to_ecef(gateway))
    network_fig = go.Figure()
    for edge_list in graph.edges.values():
        for edge in edge_list:
            if edge.source > edge.target:
                continue
            a, b = points[edge.source], points[edge.target]
            network_fig.add_trace(go.Scatter3d(x=[a[0], b[0]], y=[a[1], b[1]], z=[a[2], b[2]],
                mode="lines", line={"width": 2, "color": "#29c7ac" if edge.link_type == "optical" else "#f3b34c"},
                hoverinfo="text", text=f"{edge.source} → {edge.target} · {edge.link_type}", showlegend=False))
    active_nodes = set(graph.nodes)
    active_points = [(node, points[node]) for node in active_nodes]
    network_fig.add_trace(go.Scatter3d(x=[p[0] for _, p in active_points], y=[p[1] for _, p in active_points],
        z=[p[2] for _, p in active_points], mode="markers+text", text=[n for n, _ in active_points],
        marker={"size": 5, "color": ["#ff605c" if n in ("terminal", "gateway") else "#ffcc66" for n, _ in active_points]},
        name="Network nodes"))
    network_fig.update_layout(height=520, margin={"l": 0, "r": 0, "t": 10, "b": 0}, scene={"aspectmode": "data"})
    st.plotly_chart(network_fig, use_container_width=True)
    st.dataframe([{"packet": o.packet_id, "delivered": o.delivered, "route": " → ".join(o.route),
                    "latency_ms": o.latency_s * 1000 if o.latency_s is not None else None,
                    "reason": o.reason} for o in traffic.outcomes], use_container_width=True)

with experiment_tab:
    st.caption("Each run uses the same deterministic initial phase distribution. Repeated identical runs check reproducibility; confidence intervals stay blank when there is no observed variation.")
    parameter = st.selectbox("Vary parameter", ["altitude_km", "minimum_elevation_deg", "planes", "satellites_per_plane", "inclination_deg"])
    raw_values = st.text_input("Scenario values (comma-separated)", "450,550,650" if parameter == "altitude_km" else "20,25,35")
    repetitions = st.number_input("Repetitions per value", min_value=1, max_value=20, value=3)
    experiment_duration = st.select_slider("Experiment duration (minutes)", options=[10, 30, 60, 120], value=60)
    if st.button("Run parameter sweep", type="primary"):
        try:
            values = [float(value.strip()) for value in raw_values.split(",") if value.strip()]
            runs = run_parameter_sweep(parameter=parameter, values=values, repetitions=int(repetitions),
                duration_seconds=experiment_duration * 60, timestep_seconds=timestep,
                minimum_elevation_deg=min_elevation, site=site)
            st.session_state.experiment_runs = runs
        except ValueError as exc:
            st.error(str(exc))
    if "experiment_runs" in st.session_state:
        runs = st.session_state.experiment_runs
        summaries = summarize_experiment(runs)
        metric_choice = st.selectbox("Plot measured metric", ["availability_percent", "mean_visible_satellites",
            "mean_propagation_delay_ms", "mean_snr_db", "handover_count"])
        x_values, y_values, error_values = [], [], []
        for value, metric_summaries in summaries.items():
            stats = metric_summaries[metric_choice]
            if stats["mean"] is not None:
                x_values.append(float(value)); y_values.append(stats["mean"])
                error_values.append((stats["ci95_high"] - stats["mean"]) if stats["ci95_high"] is not None else None)
        chart = go.Figure(go.Scatter(x=x_values, y=y_values, error_y={"type": "data", "array": [v or 0 for v in error_values], "visible": any(v is not None for v in error_values)}, mode="lines+markers"))
        chart.update_layout(xaxis_title=parameter, yaxis_title=metric_choice, height=400)
        st.plotly_chart(chart, use_container_width=True)
        st.json(summaries)
        st.download_button("Download experiment runs (CSV)", experiment_csv(runs), "orbitlink-experiment.csv", "text/csv")
