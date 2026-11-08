import unittest
from datetime import datetime, timedelta, timezone
import math

from orbitlink.orbit.sgp4_backend import gmst_radians, teme_to_ecef
from orbitlink.orbit.sgp4_backend import propagate_tle
from orbitlink.orbit.tle import TLERecord, parse_tle_catalog


class TLETests(unittest.TestCase):
    # Publicly documented Vanguard 1 element set, epoch 2000 day 179.
    TLE = """VANGUARD 1
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 331.5174 1849677 331.7664  19.3264 10.82419157413661"""
    VALLADO_TLE = """VANGUARD 1
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667"""

    def test_parse_and_epoch(self):
        record = TLERecord.parse(self.TLE)
        self.assertEqual(record.satellite_id, "00005")
        self.assertEqual(record.epoch.year, 2000)
        self.assertEqual(record.epoch.tzinfo, timezone.utc)
        self.assertEqual(record.quality(record.epoch), ())

    def test_stale_data_is_flagged(self):
        record = TLERecord.parse(self.TLE)
        issues = record.quality(record.epoch + timedelta(days=15))
        self.assertTrue(any("stale" in issue for issue in issues))

    def test_invalid_checksum_is_rejected(self):
        lines = self.TLE.splitlines()
        with self.assertRaisesRegex(ValueError, "checksum"):
            TLERecord.parse("\n".join([lines[0], lines[1][:-1] + "0", lines[2]]))

    def test_teme_rotation_preserves_distance_and_z(self):
        position = (7_000_000.0, 0.0, 1_000_000.0)
        instant = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ecef = teme_to_ecef(position, instant)
        self.assertAlmostEqual(math.dist(position, (0, 0, 0)), math.dist(ecef, (0, 0, 0)), places=6)
        self.assertEqual(ecef[2], position[2])
        self.assertTrue(0 <= gmst_radians(instant) < 2 * math.pi)

    def test_catalog_parser_accepts_named_and_unnamed_sets(self):
        second = self.TLE.splitlines()[1:]
        named = parse_tle_catalog("\ufeff" + self.VALLADO_TLE)
        unnamed = parse_tle_catalog("\n".join(second))
        self.assertEqual(named[0].name, "VANGUARD 1")
        self.assertEqual(unnamed[0].satellite_id, "00005")

    def test_catalog_rejects_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate satellite IDs"):
            parse_tle_catalog(self.VALLADO_TLE + "\n" + self.VALLADO_TLE)

    def test_vallado_epoch_reference_vector_in_teme(self):
        """Vallado AIAA 2006-6753 Vanguard 1 vector, converted km to meters."""
        record = TLERecord.parse(self.VALLADO_TLE)
        state = propagate_tle(record, record.epoch)
        expected_position_m = (7_022_465.29266, -1_400_082.96755, 39.95155)
        expected_velocity_m_s = (1_893.841015, 6_405.893759, 4_534.807250)
        for actual, expected in zip(state.position_teme_m, expected_position_m):
            self.assertAlmostEqual(actual, expected, delta=0.02)
        for actual, expected in zip(state.velocity_teme_m_s, expected_velocity_m_s):
            self.assertAlmostEqual(actual, expected, delta=0.00002)

    def test_tle_model_produces_common_visibility_result(self):
        from orbitlink.analytics.simulator import run_tle_simulation
        record = TLERecord.parse(self.VALLADO_TLE)
        result = run_tle_simulation([record], start_time_utc=record.epoch,
                                    duration_seconds=120, timestep_seconds=60,
                                    max_age_days=30)
        self.assertEqual(result.model_name, "TLE + SGP4")
        self.assertEqual(result.reference_time_utc, record.epoch.isoformat())
        self.assertEqual(result.times_seconds, [0.0, 60.0, 120.0])
        self.assertEqual(len(result.satellite_states[0]), 1)


if __name__ == "__main__":
    unittest.main()
