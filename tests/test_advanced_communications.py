import unittest

from orbitlink.communication.advanced_rf import evaluate_rf_link
from orbitlink.communication.laser_link import earth_occludes_segment, optical_link
from orbitlink.core.constants import EARTH_RADIUS_M


class AdvancedCommunicationTests(unittest.TestCase):
    def test_advanced_rf_loss_and_doppler_are_consistent(self):
        base = evaluate_rf_link(distance_m=1_000_000, frequency_hz=12e9,
            transmit_power_dbw=10, transmit_gain_dbi=30, receive_gain_dbi=30, bandwidth_hz=10e6)
        lossy = evaluate_rf_link(distance_m=1_000_000, frequency_hz=12e9,
            transmit_power_dbw=10, transmit_gain_dbi=30, receive_gain_dbi=30, bandwidth_hz=10e6,
            atmospheric_loss_db=1.5, rain_loss_db=2, pointing_loss_db=0.5,
            polarization_loss_db=1, radial_velocity_m_s=1000, required_snr_db=10)
        self.assertAlmostEqual(lossy.total_path_loss_db - base.total_path_loss_db, 5)
        self.assertAlmostEqual(lossy.received_power_dbw, base.received_power_dbw - 5)
        self.assertLess(lossy.doppler_shift_hz, 0)
        self.assertAlmostEqual(lossy.link_margin_db, lossy.snr_db - 10)
        self.assertGreater(lossy.shannon_capacity_bps, 0)

    def test_optical_link_rejects_earth_occlusion(self):
        a = (EARTH_RADIUS_M + 500_000, 0, 0)
        b = (-EARTH_RADIUS_M - 500_000, 0, 0)
        self.assertTrue(earth_occludes_segment(a, b))
        self.assertFalse(optical_link(a, b).available)

    def test_optical_link_accepts_clear_path_and_reports_delay(self):
        a = (EARTH_RADIUS_M + 500_000, 0, 0)
        b = (EARTH_RADIUS_M + 500_000, 1_000_000, 0)
        link = optical_link(a, b)
        self.assertTrue(link.available, link.reason)
        self.assertAlmostEqual(link.propagation_delay_s, link.distance_m / 299_792_458)


if __name__ == "__main__":
    unittest.main()
