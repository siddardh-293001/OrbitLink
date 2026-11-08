"""Extended RF terms with separately reported model assumptions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitlink.core.constants import BOLTZMANN_J_K, SPEED_OF_LIGHT_M_S


@dataclass(frozen=True)
class AdvancedRFResult:
    free_space_path_loss_db: float
    total_path_loss_db: float
    received_power_dbw: float
    noise_power_dbw: float
    snr_db: float
    carrier_to_noise_density_db_hz: float
    doppler_shift_hz: float
    link_margin_db: float
    shannon_capacity_bps: float


def evaluate_rf_link(*, distance_m: float, frequency_hz: float, transmit_power_dbw: float,
                     transmit_gain_dbi: float, receive_gain_dbi: float,
                     bandwidth_hz: float, receiver_noise_temperature_k: float = 290.0,
                     atmospheric_loss_db: float = 0.0, rain_loss_db: float = 0.0,
                     pointing_loss_db: float = 0.0, polarization_loss_db: float = 0.0,
                     interference_power_dbw: float | None = None,
                     radial_velocity_m_s: float = 0.0, required_snr_db: float = 0.0) -> AdvancedRFResult:
    """Compute link metrics; channel losses are caller-supplied assumptions in dB.

    `shannon_capacity_bps` is an idealized upper bound, not simulated throughput.
    """
    if min(distance_m, frequency_hz, bandwidth_hz, receiver_noise_temperature_k) <= 0:
        raise ValueError("distance, frequency, bandwidth and receiver noise temperature must be positive")
    losses = (atmospheric_loss_db, rain_loss_db, pointing_loss_db, polarization_loss_db)
    if any(value < 0 for value in losses):
        raise ValueError("loss terms must be non-negative")
    fspl = 20 * math.log10(4 * math.pi * distance_m * frequency_hz / SPEED_OF_LIGHT_M_S)
    total_loss = fspl + sum(losses)
    received = transmit_power_dbw + transmit_gain_dbi + receive_gain_dbi - total_loss
    thermal_noise_w = BOLTZMANN_J_K * receiver_noise_temperature_k * bandwidth_hz
    noise_w = thermal_noise_w + (10 ** (interference_power_dbw / 10) if interference_power_dbw is not None else 0)
    noise_dbw = 10 * math.log10(noise_w)
    snr_db = received - noise_dbw
    snr_linear = 10 ** (snr_db / 10)
    cn0 = received - 10 * math.log10(BOLTZMANN_J_K * receiver_noise_temperature_k)
    doppler = -radial_velocity_m_s / SPEED_OF_LIGHT_M_S * frequency_hz
    return AdvancedRFResult(fspl, total_loss, received, noise_dbw, snr_db, cn0, doppler,
                            snr_db - required_snr_db, bandwidth_hz * math.log2(1 + snr_linear))
