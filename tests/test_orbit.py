import math
import unittest

from orbitlink.core.constants import EARTH_RADIUS_M
from orbitlink.orbit.constellation import generate_constellation
from orbitlink.orbit.keplerian import orbital_period_seconds, propagate, solve_kepler


class OrbitTests(unittest.TestCase):
    def test_mixed_planes_and_surface_intersection(self):
        elements = generate_constellation(planes=2, satellites_per_plane=2,
            plane_altitudes_km=[550, 1200], plane_inclinations_deg=[53, 98])
        self.assertEqual(elements[0].semi_major_axis_m, EARTH_RADIUS_M + 550000)
        self.assertEqual(elements[2].semi_major_axis_m, EARTH_RADIUS_M + 1200000)
        self.assertAlmostEqual(elements[2].inclination_rad, math.radians(98))
        with self.assertRaisesRegex(ValueError, "perigee"):
            generate_constellation(altitude_km=550, eccentricity=0.2)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            generate_constellation(planes=2, plane_altitudes_km=[550])

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

    def test_configurable_walker_planes_and_ellipticity(self):
        constellation = generate_constellation(planes=3, satellites_per_plane=4,
            altitude_km=1000, inclination_deg=65, eccentricity=0.1,
            phase_factor=3, raan_offset_deg=45)
        self.assertEqual(len(constellation), 12)
        self.assertAlmostEqual(constellation[0].raan_rad, math.radians(45))
        self.assertAlmostEqual(constellation[4].raan_rad, math.radians(165))
        self.assertAlmostEqual(constellation[0].eccentricity, 0.1)
        self.assertAlmostEqual(constellation[4].mean_anomaly_epoch_rad - constellation[0].mean_anomaly_epoch_rad,
                               2 * math.pi * 3 / 12)

    def test_constellation_rejects_nonphysical_elements(self):
        with self.assertRaisesRegex(ValueError, "eccentricity"):
            generate_constellation(eccentricity=1.0)
        with self.assertRaisesRegex(ValueError, "inclination"):
            generate_constellation(inclination_deg=181)


if __name__ == "__main__":
    unittest.main()
