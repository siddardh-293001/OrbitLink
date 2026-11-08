import unittest

from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.core.models import GroundSite
from orbitlink.communication.rf_link import link_budget
from orbitlink.geometry.transforms import look_angle


class GeometryCommunicationTests(unittest.TestCase):
    def setUp(self):
        self.site = GroundSite("test", 0, 0)

    def test_overhead_satellite_is_visible(self):
        angle = look_angle(self.site, "overhead", (EARTH_RADIUS_M + 550_000, 0, 0), 25)
        self.assertAlmostEqual(angle.elevation_deg, 90)
        self.assertTrue(angle.visible)

    def test_satellite_below_horizon_is_not_visible(self):
        angle = look_angle(self.site, "opposite", (-(EARTH_RADIUS_M + 550_000), 0, 0), 0)
        self.assertLess(angle.elevation_deg, 0)
        self.assertFalse(angle.visible)

    def test_link_budget_reference(self):
        budget = link_budget(1_000_000, frequency_hz=12e9)
        self.assertAlmostEqual(budget.free_space_path_loss_db, 174.03, delta=0.02)
        self.assertAlmostEqual(budget.propagation_delay_s, 1_000_000 / 299_792_458)
        self.assertAlmostEqual(budget.received_power_dbw, 10 + 30 + 30 - 2 - budget.free_space_path_loss_db)


if __name__ == "__main__":
    unittest.main()
