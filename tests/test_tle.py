import unittest
from datetime import datetime, timedelta, timezone
import math

from orbitlink.orbit.sgp4_backend import gmst_radians, teme_to_ecef
from orbitlink.orbit.tle import TLERecord


class TLETests(unittest.TestCase):
    # Publicly documented Vanguard 1 element set, epoch 2000 day 179.
    TLE = """VANGUARD 1
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 331.5174 1849677 331.7664  19.3264 10.82419157413661"""

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


if __name__ == "__main__":
    unittest.main()
