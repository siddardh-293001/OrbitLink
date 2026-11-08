import math
import unittest

from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.orbit.constellation import generate_constellation
from orbitlink.orbit.keplerian import orbital_period_seconds, propagate, solve_kepler


class OrbitTests(unittest.TestCase):
    def test_kepler_solver_residual(self):
        for mean, eccentricity in [(0.1, 0.0), (2.4, 0.3), (5.9, 0.7)]:
            eccentric = solve_kepler(mean, eccentricity)
            self.assertAlmostEqual(eccentric - eccentricity * math.sin(eccentric), mean % (2 * math.pi), places=11)

    def test_demo_orbital_period(self):
        a = EARTH_RADIUS_M + 550_000
        period = orbital_period_seconds(a)
        self.assertAlmostEqual(period / 60, 95.5, delta=0.3)

    def test_constellation_has_24_unique_satellites(self):
        constellation = generate_constellation()
        ids = [s.satellite_id for s in constellation]
        self.assertEqual(len(ids), 24)
        self.assertEqual(len(set(ids)), 24)

    def test_circular_orbit_closes_after_one_period(self):
        element = generate_constellation(planes=1, satellites_per_plane=1)[0]
        period = orbital_period_seconds(element.semi_major_axis_m)
        initial = propagate(element, 0, earth_rotation=False).position_eci_m
        final = propagate(element, period, earth_rotation=False).position_eci_m
        self.assertLess(math.dist(initial, final), 1e-3)


if __name__ == "__main__":
    unittest.main()
