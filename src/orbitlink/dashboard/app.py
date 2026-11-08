"""Interactive V1 dashboard for the ORBITLINK demonstration."""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from orbitlink.analytics.simulator import run_simulation
from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.core.models import GroundSite
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

overview, orbit_tab, ground_tab, communication, handover, analytics = st.tabs(
    ["Overview", "Orbit Viewer", "Ground Track", "Communication", "Handover", "Analytics"])

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
