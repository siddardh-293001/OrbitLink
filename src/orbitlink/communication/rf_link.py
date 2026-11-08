"""Transparent first-order RF link budget and propagation delay."""

from __future__ import annotations

import math

from orbitlink.core.constants import BOLTZMANN_J_K, SPEED_OF_LIGHT_M_S
from orbitlink.core.models import LinkBudget


def link_budget(distance_m: float, *, frequency_hz: float = 12e9, transmit_power_dbw: float = 10.0,
                transmit_gain_dbi: float = 30.0, receive_gain_dbi: float = 30.0,
                bandwidth_hz: float = 10e6, system_noise_temperature_k: float = 290.0,
                other_losses_db: float = 2.0) -> LinkBudget:
    if distance_m <= 0 or frequency_hz <= 0 or bandwidth_hz <= 0 or system_noise_temperature_k <= 0:
        raise ValueError("distance, frequency, bandwidth, and noise temperature must be positive")
    distance_km, frequency_ghz = distance_m / 1000.0, frequency_hz / 1e9
    fspl = 92.45 + 20.0 * math.log10(frequency_ghz) + 20.0 * math.log10(distance_km)
    received = transmit_power_dbw + transmit_gain_dbi + receive_gain_dbi - other_losses_db - fspl
    noise_dbw = 10.0 * math.log10(BOLTZMANN_J_K * system_noise_temperature_k * bandwidth_hz)
    return LinkBudget(distance_m, frequency_hz, fspl, received, noise_dbw, received - noise_dbw,
                      distance_m / SPEED_OF_LIGHT_M_S, True)
