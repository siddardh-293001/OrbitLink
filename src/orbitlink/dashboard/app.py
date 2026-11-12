"""Interactive ORBITLINK dashboard for synthetic and TLE-driven scenarios."""

from __future__ import annotations

import math
import random
import hashlib
from datetime import datetime, timedelta, timezone

import plotly.graph_objects as go
import streamlit as st

from orbitlink.analytics.simulator import run_simulation, run_tle_simulation
from orbitlink.analytics.experiments import experiment_csv, run_parameter_sweep, summarize_experiment
from orbitlink.core.constants import EARTH_RADIUS_M, EARTH_ROTATION_RAD_S
from orbitlink.core.constants import SPEED_OF_LIGHT_M_S
from orbitlink.core.models import GroundSite
from orbitlink.communication.laser_link import optical_link
from orbitlink.geometry.transforms import geodetic_to_ecef
from orbitlink.geometry.visibility import visible_satellites
from orbitlink.network.packet import Packet, simulate_packets
from orbitlink.network.topology import LinkEdge, NetworkGraph
from orbitlink.orbit.constellation import generate_constellation
from orbitlink.orbit.keplerian import orbital_period_seconds, propagate
from orbitlink.orbit.tle import parse_tle_catalog

st.set_page_config(page_title="ORBITLINK | LEO Simulator", page_icon="🛰️", layout="wide")
st.title("🛰️ ORBITLINK")
st.caption("Explore how satellites connect a location on Earth to the internet.")
st.info("Start with the ready-made 40-satellite example. Open Earth view to explore it, or expand Advanced setup in the sidebar to change the scenario.")

with st.sidebar:
    st.header("Set up your simulation")
    st.caption("1. Choose your location · 2. Adjust the satellites · 3. Run")
    latitude = st.number_input("Terminal latitude (°)", min_value=-90.0, max_value=90.0, value=37.7749)
    longitude = st.number_input("Terminal longitude (°)", min_value=-180.0, max_value=180.0, value=-122.4194)
    duration_hours = st.slider("Duration (hours)", 0.25, 2.0, 2.0, 0.25)
    with st.expander("Advanced setup · orbit data and precision", expanded=False):
        model_mode = st.radio("Orbit source", ["Synthetic demo", "TLE catalog + SGP4"],
                              help="Synthetic uses a repeatable Walker-style constellation. TLE mode propagates uploaded element sets with SGP4.")
        min_elevation = st.slider("Minimum elevation (°)", 5, 60, 25)
        uploaded_catalog = None
        sim_date, sim_time = datetime.now(timezone.utc).date(), datetime.now(timezone.utc).time().replace(microsecond=0)
        max_tle_age = 14.0
        planes, satellites_per_plane, altitude_km, inclination_deg, phase_factor = 5, 8, 550.0, 53.0, 1
        eccentricity, raan_offset_deg = 0.0, 0.0
        timestep = 60
        if model_mode == "Synthetic demo":
            st.caption("Synthetic Walker-style constellation")
            timestep = st.select_slider("Sample interval", options=[10, 30, 60], value=10,
                                        format_func=lambda value: f"{value} seconds")
            planes = st.slider("Orbital planes", 1, 8, 5)
            satellites_per_plane = st.slider("Satellites per plane", 2, 12, 8)
            altitude_km = st.slider("Orbit altitude (km)", 300, 2_000, 550, 50)
            inclination_deg = st.slider("Inclination (°)", 0, 120, 53)
            phase_factor = st.slider("Walker phase factor", 0, planes * satellites_per_plane, 1,
                                      help="Controls how satellites are offset between adjacent planes.")
            with st.expander("Advanced orbit settings"):
                eccentricity = st.slider("Eccentricity", 0.0, 0.2, 0.0, 0.005,
                                         help="Zero is circular. Larger values create elliptical demo orbits.")
                raan_offset_deg = st.slider("First plane RAAN offset (°)", 0.0, 359.0, 0.0, 1.0)
        else:
            uploaded_catalog = st.file_uploader("Upload TLE catalog (.tle or .txt)", type=["tle", "txt"])
            sim_date = st.date_input("Start date (UTC)", value=sim_date)
            sim_time = st.time_input("Start time (UTC)", value=sim_time)
            timestep = st.select_slider("Sample interval", options=[30, 60, 120], value=60,
                                        format_func=lambda value: f"{value} seconds")
            max_tle_age = st.number_input("Maximum TLE age (days)", min_value=1.0, max_value=30.0, value=14.0)
    run = st.button("Run simulation", type="primary", use_container_width=True)

site = GroundSite("Dashboard terminal", latitude, longitude)
tle_records, tle_issues, tle_error = (), (), None
simulation_start = datetime.combine(sim_date, sim_time).replace(tzinfo=timezone.utc)
catalog_digest = hashlib.sha256(uploaded_catalog.getvalue()).hexdigest() if uploaded_catalog is not None else None
requested_config = {
    "model": model_mode, "latitude": latitude, "longitude": longitude,
    "minimum_elevation": min_elevation, "duration_hours": duration_hours,
    "timestep": timestep, "planes": planes, "satellites_per_plane": satellites_per_plane,
    "altitude_km": altitude_km, "inclination_deg": inclination_deg,
    "phase_factor": phase_factor, "eccentricity": eccentricity,
    "raan_offset_deg": raan_offset_deg, "catalog_digest": catalog_digest,
    "start_time": simulation_start.isoformat() if model_mode == "TLE catalog + SGP4" else None, "max_tle_age": max_tle_age,
}
if model_mode == "TLE catalog + SGP4" and uploaded_catalog is not None:
    try:
        tle_records = parse_tle_catalog(uploaded_catalog.getvalue().decode("utf-8-sig"))
        quality_end = simulation_start + timedelta(seconds=int(duration_hours * 3600))
        tle_issues = [(record.name, issue) for record in tle_records
                      for sample in (simulation_start, quality_end)
                      for issue in record.quality(sample, max_age_days=max_tle_age)]
        st.sidebar.caption(f"Catalog: {len(tle_records)} satellites · max age {max_tle_age:g} days")
    except (UnicodeDecodeError, ValueError) as exc:
        tle_error = str(exc)
        st.sidebar.error(f"Catalog could not be read: {tle_error}")
if model_mode == "TLE catalog + SGP4":
    if tle_error:
        st.error(f"TLE input error: {tle_error}")
    elif uploaded_catalog is None:
        st.info("Upload a TLE catalog in the sidebar to configure a real-orbit scenario.")
    elif tle_issues:
        st.warning("TLE quality check found issues. Adjust the UTC start time or upload fresher element sets. "
                   + " · ".join(f"{name}: {issue}" for name, issue in tle_issues[:5]))
    else:
        st.success(f"TLE quality check passed for all {len(tle_records)} satellites across the selected run.")
if "result" not in st.session_state or run:
    try:
        with st.spinner("Propagating orbits and measuring links…"):
            if model_mode == "TLE catalog + SGP4":
                if not tle_records or tle_issues:
                    st.error("Resolve the TLE catalog quality checks before running the simulation.")
                    st.stop()
                st.session_state.result = run_tle_simulation(
                    tle_records, site=site, start_time_utc=simulation_start,
                    duration_seconds=int(duration_hours * 3600), timestep_seconds=timestep,
                    minimum_elevation_deg=min_elevation, max_age_days=max_tle_age)
            else:
                st.session_state.result = run_simulation(site=site, duration_seconds=int(duration_hours * 3600),
                    timestep_seconds=timestep, minimum_elevation_deg=min_elevation,
                    planes=planes, satellites_per_plane=satellites_per_plane,
                    altitude_km=altitude_km, inclination_deg=inclination_deg, phase_factor=phase_factor,
                    eccentricity=eccentricity, raan_offset_deg=raan_offset_deg)
            st.session_state.result_config = requested_config
    except (ValueError, RuntimeError) as exc:
        st.error(f"Simulation could not run: {exc}")
        st.stop()
result = st.session_state.result
summary = result.summary()
result_config = st.session_state.get("result_config", requested_config)
if result_config != requested_config:
    st.warning("Scenario controls have changed since this result was run. Click **Run simulation** to refresh the charts.")
display_planes = result_config.get("planes", planes)
display_satellites_per_plane = result_config.get("satellites_per_plane", satellites_per_plane)
display_altitude_km = result_config.get("altitude_km", altitude_km)
display_inclination_deg = result_config.get("inclination_deg", inclination_deg)
display_phase_factor = result_config.get("phase_factor", phase_factor)
display_eccentricity = result_config.get("eccentricity", eccentricity)
display_raan_offset = result_config.get("raan_offset_deg", raan_offset_deg)
display_site = GroundSite("Last run terminal", result_config.get("latitude", latitude),
                          result_config.get("longitude", longitude))
display_min_elevation = result_config.get("minimum_elevation", min_elevation)

st.caption(f"Last run model: **{result.model_name}**" +
           (f" · Reference time: {result.reference_time_utc}" if result.reference_time_utc else ""))

overview, orbit_tab, details_tab = st.tabs(["Connection summary", "Earth view", "Explore details"])
with details_tab:
    st.caption("Optional: inspect the measurements behind the summary or compare different scenarios.")
    ground_tab = st.expander("Where do satellites travel over Earth?")
    communication = st.expander("How strong and fast is the connection?")
    handover = st.expander("When does the connection switch satellites?")
    analytics = st.expander("View measurements and download results")
    network_tab = st.expander("How does a message travel through the network?")
    experiment_tab = st.expander("Compare different satellite setups")

with overview:
    metrics = st.columns(4)
    metrics[0].metric("Spacecraft", str(len(result.satellite_states[0])), result.model_name)
    metrics[1].metric("Time connected", f"{summary['availability_percent']:.1f}%")
    metrics[2].metric("Satellites in reach", f"{summary['mean_visible_satellites']:.2f}", "mean per sample")
    metrics[3].metric("Satellite switches", str(summary["handover_count"]))
    st.write(f"Your location can reach a satellite in **{summary['availability_percent']:.1f}% of the sampled moments**. "
             f"The connection switches between satellites **{summary['handover_count']} times** during this run.")
    st.caption("Time connected means a satellite is high enough above the horizon to serve your location. This is a simulation estimate, not a guarantee of real internet service.")

with orbit_tab:
    st.subheader("Satellites around Earth")
    st.caption("Drag to rotate Earth. Scroll to zoom. Green curves are orbit paths; straight green lines are possible links between satellites.")
    index = st.select_slider("Explore a moment in the simulation", options=list(range(len(result.times_seconds))), value=0, format_func=lambda i: f"{result.times_seconds[i] / 60:g} minutes after start")
    states = result.satellite_states[index]
    # Build a higher-resolution Earth surface and shade land, ocean, relief, and
    # polar ice separately so the orbital view reads as a planet, not a plain ball.
    u, v = 72, 144
    sphere_x, sphere_y, sphere_z = [], [], []
    earth_colors = []
    landmasses = [
        [(-168, 64), (-157, 72), (-143, 70), (-133, 58), (-124, 50), (-117, 33), (-108, 23), (-98, 18), (-91, 20), (-84, 26), (-81, 33), (-75, 41), (-66, 46), (-59, 52), (-67, 59), (-80, 62), (-91, 69), (-108, 72), (-125, 70), (-143, 72), (-157, 69)],
        [(-52, 60), (-43, 61), (-34, 70), (-40, 81), (-54, 84), (-62, 78), (-59, 68)],
        [(-81, 12), (-70, 10), (-61, 4), (-50, 1), (-45, -8), (-39, -14), (-43, -23), (-49, -31), (-54, -42), (-64, -55), (-71, -48), (-74, -31), (-78, -13)],
        [(-11, 36), (-17, 30), (-17, 19), (-12, 9), (-16, 1), (-8, -5), (3, -5), (10, -14), (19, -34), (29, -34), (35, -24), (42, -11), (50, 1), (43, 12), (50, 17), (42, 30), (32, 32), (28, 37), (17, 36), (9, 42), (-1, 36)],
        [(-11, 36), (-10, 44), (-5, 49), (2, 51), (9, 55), (18, 55), (25, 60), (34, 58), (40, 52), (50, 55), (58, 61), (72, 66), (88, 70), (103, 68), (116, 62), (128, 55), (140, 51), (153, 58), (166, 61), (177, 53), (169, 44), (158, 39), (146, 42), (135, 35), (127, 31), (121, 23), (113, 18), (108, 8), (100, 4), (96, 14), (87, 21), (80, 8), (77, 7), (74, 18), (69, 25), (62, 26), (56, 25), (51, 29), (45, 24), (42, 16), (35, 33), (27, 37), (18, 36), (9, 42), (1, 41), (-6, 37)],
        [(112, -11), (123, -10), (132, -12), (141, -17), (153, -25), (151, -36), (140, -39), (130, -35), (119, -32), (114, -24)],
        [(47, -13), (50, -16), (49, -25), (46, -26), (44, -18)],
        [(129, 31), (136, 34), (142, 42), (145, 44), (140, 36)],
        [(-180, -68), (-150, -72), (-120, -70), (-90, -74), (-60, -70), (-30, -73), (0, -69), (30, -73), (60, -70), (90, -74), (120, -70), (150, -72), (180, -68), (180, -90), (-180, -90)],
    ]

    def on_land(longitude_deg: float, latitude_deg: float) -> bool:
        for polygon in landmasses:
            inside = False
            previous = polygon[-1]
            for current in polygon:
                x1, y1 = previous
                x2, y2 = current
                if (y1 > latitude_deg) != (y2 > latitude_deg):
                    crossing = (x2 - x1) * (latitude_deg - y1) / (y2 - y1) + x1
                    if longitude_deg < crossing:
                        inside = not inside
                previous = current
            if inside:
                return True
        return False

    for i in range(u + 1):
        row_x, row_y, row_z = [], [], []
        color_row = []
        lat_r = math.pi * (i / u - 0.5)
        latitude_deg = math.degrees(lat_r)
        for j in range(v + 1):
            lon_r = 2 * math.pi * j / v
            longitude_deg = (math.degrees(lon_r) + 180) % 360 - 180
            row_x.append(EARTH_RADIUS_M * math.cos(lat_r) * math.cos(lon_r) / 1000)
            row_y.append(EARTH_RADIUS_M * math.cos(lat_r) * math.sin(lon_r) / 1000)
            row_z.append(EARTH_RADIUS_M * math.sin(lat_r) / 1000)
            if abs(latitude_deg) >= 78:
                color = 0.91
            elif on_land(longitude_deg, latitude_deg):
                # Deterministic geographic shading adds forests, dry regions, and
                # highlands while keeping the map lightweight and self-contained.
                terrain = (math.sin(math.radians(longitude_deg * 2.7 + latitude_deg * 3.1))
                           + math.cos(math.radians(longitude_deg * 5.1 - latitude_deg * 2.2))) / 2
                if abs(latitude_deg) < 22 and terrain < -0.12:
                    color = 0.57 + 0.035 * terrain
                elif terrain > 0.55:
                    color = 0.76
                else:
                    color = 0.40 + max(0, terrain) * 0.15
            else:
                ocean = math.sin(math.radians(longitude_deg * 2.4 + latitude_deg * 1.7)) * math.cos(math.radians(latitude_deg * 2.8))
                color = 0.13 + (ocean + 1) * 0.035
            color_row.append(color)
        sphere_x.append(row_x); sphere_y.append(row_y); sphere_z.append(row_z); earth_colors.append(color_row)
    earth_scale = [
        [0.00, "#071c36"], [0.13, "#0c3153"], [0.20, "#15517a"], [0.25, "#287ba0"],
        [0.34, "#327747"], [0.45, "#61964f"], [0.56, "#a4a15c"], [0.67, "#b68550"],
        [0.77, "#ded08b"], [0.86, "#d9d5b8"], [0.93, "#f3f4e8"], [1.00, "#ffffff"],
    ]
    fig = go.Figure(go.Surface(x=sphere_x, y=sphere_y, z=sphere_z, surfacecolor=earth_colors,
                               cmin=0, cmax=1, colorscale=earth_scale, showscale=False,
                               lighting={"ambient": 0.38, "diffuse": 0.92, "specular": 0.12, "roughness": 0.82},
                               lightposition={"x": 1200, "y": 900, "z": 1400}, name="Earth"))
    # A fixed star field gives the globe the deep-space setting from the reference.
    star_rng = random.Random(42)
    star_positions = [[], [], []]
    for _ in range(650):
        z_unit = star_rng.uniform(-1, 1)
        angle = star_rng.uniform(0, 2 * math.pi)
        radius = 12_500
        planar = math.sqrt(1 - z_unit * z_unit)
        star_positions[0].append(radius * planar * math.cos(angle))
        star_positions[1].append(radius * planar * math.sin(angle))
        star_positions[2].append(radius * z_unit)
    fig.add_trace(go.Scatter3d(x=star_positions[0], y=star_positions[1], z=star_positions[2],
        mode="markers", marker={"size": 1.3, "color": "#b8c7d9", "opacity": 0.72},
        hoverinfo="skip", showlegend=False, name="Stars"))
    # Soft atmospheric rim around the planet.
    atmosphere_radius = EARTH_RADIUS_M * 1.012 / 1000
    atmosphere_x = [[atmosphere_radius * math.cos(math.pi * (i / u - 0.5)) * math.cos(2 * math.pi * j / v) for j in range(v + 1)] for i in range(u + 1)]
    atmosphere_y = [[atmosphere_radius * math.cos(math.pi * (i / u - 0.5)) * math.sin(2 * math.pi * j / v) for j in range(v + 1)] for i in range(u + 1)]
    atmosphere_z = [[atmosphere_radius * math.sin(math.pi * (i / u - 0.5)) for _ in range(v + 1)] for i in range(u + 1)]
    fig.add_trace(go.Surface(x=atmosphere_x, y=atmosphere_y, z=atmosphere_z,
        colorscale=[[0, "#3b9dff"], [1, "#8fcaff"]], showscale=False, opacity=0.10,
        hoverinfo="skip", name="Atmosphere"))
    # Draw each complete orbital plane at the selected simulation instant. The
    # earlier trail used only the finite run window in rotating ECEF coordinates,
    # so its ends could not meet. Build a full inertial revolution, then rotate
    # that orbit into the Earth's fixed frame at the current slider time.
    simulation_time = result.times_seconds[index]
    if result.model_name == "Synthetic Keplerian":
        elements = generate_constellation(planes=display_planes, satellites_per_plane=display_satellites_per_plane,
            altitude_km=display_altitude_km, inclination_deg=display_inclination_deg,
            eccentricity=display_eccentricity, phase_factor=display_phase_factor,
            raan_offset_deg=display_raan_offset)
        elements_by_id = {element.satellite_id: element for element in elements}
        earth_angle = EARTH_ROTATION_RAD_S * simulation_time
        cos_earth, sin_earth = math.cos(earth_angle), math.sin(earth_angle)
        orbit_samples = 160
        for plane in range(1, display_planes + 1):
            element = elements_by_id[f"P{plane:02d}-S01"]
            period = orbital_period_seconds(element.semi_major_axis_m)
            path_x, path_y, path_z = [], [], []
            for sample_index in range(orbit_samples + 1):
                orbit_time = simulation_time + period * sample_index / orbit_samples
                state = propagate(element, orbit_time, earth_rotation=False)
                x_eci, y_eci, z_eci = state.position_eci_m
                path_x.append((cos_earth * x_eci + sin_earth * y_eci) / 1000)
                path_y.append((-sin_earth * x_eci + cos_earth * y_eci) / 1000)
                path_z.append(z_eci / 1000)
            fig.add_trace(go.Scatter3d(x=path_x, y=path_y, z=path_z,
                mode="lines", line={"color": "#7cff52", "width": 2}, opacity=0.48,
                hoverinfo="skip", showlegend=False, name=f"Plane {plane} orbit"))
    else:
        # TLE-mode trails use the actual SGP4 samples in this run, so the
        # visualization never invents a synthetic orbit for real catalog data.
        tracked_ids = [state.satellite_id for state in states[:min(8, len(states))]]
        for satellite_id in tracked_ids:
            path = [next((item for item in snapshot if item.satellite_id == satellite_id), None)
                    for snapshot in result.satellite_states]
            path = [item for item in path if item is not None]
            fig.add_trace(go.Scatter3d(x=[p.position_ecef_m[0] / 1000 for p in path],
                y=[p.position_ecef_m[1] / 1000 for p in path], z=[p.position_ecef_m[2] / 1000 for p in path],
                mode="lines", line={"color": "#7cff52", "width": 2}, opacity=0.48,
                hoverinfo="skip", showlegend=False, name=f"{satellite_id} sampled path"))

    # Draw only links the geometry model says have line of sight and fit its
    # 5,000 km optical link range, matching the network view's link assumptions.
    crosslink_x, crosslink_y, crosslink_z = [], [], []
    for left_index, left in enumerate(states):
        for right in states[left_index + 1:]:
            link = optical_link(left.position_ecef_m, right.position_ecef_m, maximum_range_m=5_000_000)
            if link.available:
                crosslink_x.extend([left.position_ecef_m[0] / 1000, right.position_ecef_m[0] / 1000, None])
                crosslink_y.extend([left.position_ecef_m[1] / 1000, right.position_ecef_m[1] / 1000, None])
                crosslink_z.extend([left.position_ecef_m[2] / 1000, right.position_ecef_m[2] / 1000, None])
    fig.add_trace(go.Scatter3d(x=crosslink_x, y=crosslink_y, z=crosslink_z,
        mode="lines", line={"color": "#a5ff43", "width": 2}, opacity=0.76,
        hoverinfo="skip", showlegend=False, name="Optical crosslinks"))

    # Satellite markers stay bright and identifiable against the space backdrop.
    fig.add_trace(go.Scatter3d(x=[s.position_ecef_m[0]/1000 for s in states],
        y=[s.position_ecef_m[1]/1000 for s in states], z=[s.position_ecef_m[2]/1000 for s in states],
        mode="markers+text", marker={"size": 4.5, "color": "#e5eaf0", "line": {"color": "#89ff43", "width": 1}},
        text=[s.satellite_id for s in states], textposition="top center",
        textfont={"size": 8, "color": "#a5ff43"}, customdata=[s.satellite_id for s in states],
        hovertemplate="%{customdata}<extra>Satellite</extra>", name="Satellites"))
    sim_time = int(result.times_seconds[index])
    hours, remainder = divmod(sim_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Spacecraft", len(states))
    m2.metric("Orbital planes", str(display_planes) if result.model_name == "Synthetic Keplerian" else "Catalog")
    m3.metric("Optical crosslinks", len(crosslink_x) // 3)
    if result.model_name == "TLE + SGP4" and result.reference_time_utc:
        actual_time = datetime.fromisoformat(result.reference_time_utc) + timedelta(seconds=sim_time)
        simulation_label = actual_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        simulation_label = f"{hours:02d}:{minutes:02d}:{seconds:02d} elapsed"
    m4.metric("Simulation time", simulation_label)
    fig.update_layout(
        height=720, margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="#03070d", plot_bgcolor="#03070d",
        scene={
            "aspectmode": "cube",
            "bgcolor": "#03070d",
            "xaxis": {"visible": False, "range": [-12_500, 12_500]},
            "yaxis": {"visible": False, "range": [-12_500, 12_500]},
            "zaxis": {"visible": False, "range": [-12_500, 12_500]},
            "camera": {"eye": {"x": 1.65, "y": 1.65, "z": 1.1}, "projection": {"type": "orthographic"}},
        },
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    if result.model_name == "TLE + SGP4":
        st.caption("TLE states are propagated in TEME. Ground geometry uses a GMST-rotated PEF approximation (UTC≈UT1, no polar-motion correction); green paths show the sampled run window.")

with ground_tab:
    fig = go.Figure()
    track_ids = [state.satellite_id for state in result.satellite_states[0][:min(8, len(result.satellite_states[0]))]]
    for sat_id in track_ids:
        positions = [next(item.position_ecef_m for item in snapshot if item.satellite_id == sat_id)
                     for snapshot in result.satellite_states]
        latitudes = [math.degrees(math.atan2(z, math.hypot(x, y))) for x, y, z in positions]
        longitudes = [math.degrees(math.atan2(y, x)) for x, y, _ in positions]
        fig.add_trace(go.Scatter(x=longitudes, y=latitudes, mode="lines", name=sat_id))
    fig.add_trace(go.Scatter(x=[result_config.get("longitude", longitude)], y=[result_config.get("latitude", latitude)], mode="markers", marker={"size": 12, "color": "red"}, name="Terminal"))
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
    st.download_button("Download measurements (CSV)", csv, "orbitlink-v2-metrics.csv", "text/csv")

with network_tab:
    st.caption("Connectivity is rebuilt from geometry at the selected orbit sample. Packet capacity is an explicit scenario assumption.")
    capacity_mbps = st.number_input("Per-link packet capacity assumption (Mbps)", min_value=1.0, max_value=100000.0, value=50.0, step=1.0)
    gateway = GroundSite("Demo gateway", 34.0522, -118.2437)
    states = result.satellite_states[index]
    terminal_links = visible_satellites(display_site, states, display_min_elevation)
    gateway_links = visible_satellites(gateway, states, display_min_elevation)
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
    points["terminal"] = tuple(value / 1000 for value in geodetic_to_ecef(display_site))
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
