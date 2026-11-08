import unittest

from orbitlink.analytics.simulator import run_simulation
from orbitlink.core.models import LookAngle
from orbitlink.mobility.handover import HandoverManager


class HandoverSimulatorTests(unittest.TestCase):
    def test_hysteresis_prevents_small_switches_then_switches(self):
        manager = HandoverManager(hysteresis_deg=5, minimum_elevation_deg=25)
        manager.update(0, [LookAngle("A", 1, 0, 40, True)])
        manager.update(10, [LookAngle("A", 1, 0, 40, True), LookAngle("B", 1, 0, 43, True)])
        self.assertEqual(manager.serving_satellite_id, "A")
        manager.update(20, [LookAngle("A", 1, 0, 35, True), LookAngle("B", 1, 0, 42, True)])
        self.assertEqual(manager.serving_satellite_id, "B")
        self.assertEqual(len(manager.events), 2)

    def test_end_to_end_demo_is_measured_and_deterministic(self):
        result = run_simulation(duration_seconds=7200, timestep_seconds=10)
        self.assertEqual(len(result.satellite_states[0]), 24)
        self.assertEqual(len(result.times_seconds), 721)
        self.assertGreater(result.summary()["availability_percent"], 0)
        self.assertIsNotNone(result.summary()["mean_propagation_delay_ms"])
        self.assertEqual(result.summary(), run_simulation(duration_seconds=7200, timestep_seconds=10).summary())


if __name__ == "__main__":
    unittest.main()
