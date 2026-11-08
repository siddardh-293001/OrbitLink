import unittest

from orbitlink.core.models import LookAngle
from orbitlink.mobility.selection import select_candidate
from orbitlink.network.packet import Packet, simulate_packets
from orbitlink.network.topology import LinkEdge, NetworkGraph


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.graph = NetworkGraph(edges=[
            LinkEdge("terminal", "sat-A", 0.02, 600_000, capacity_bps=8000),
            LinkEdge("sat-A", "gateway", 0.02, 600_000, congestion_penalty=0.2, capacity_bps=8000),
            LinkEdge("terminal", "sat-B", 0.03, 700_000, quality_penalty=0.1, capacity_bps=16000),
            LinkEdge("sat-B", "gateway", 0.03, 700_000, quality_penalty=0.1, capacity_bps=16000),
        ])

    def test_route_strategies_choose_by_cost_and_ignore_blocked_edges(self):
        path, cost = self.graph.shortest_path("terminal", "gateway")
        self.assertEqual(path, ["terminal", "sat-A", "gateway"])
        self.assertAlmostEqual(cost, 0.04)
        blocked = NetworkGraph(edges=[LinkEdge("a", "b", 1, available=False)])
        self.assertIsNone(blocked.shortest_path("a", "b"))

    def test_packets_are_accounted_and_queues_increase_latency(self):
        packets = [Packet("p1", "terminal", "gateway", 1000, 0), Packet("p2", "terminal", "gateway", 1000, 0)]
        metrics = simulate_packets(packets, self.graph)
        self.assertEqual(metrics.packets_generated, 2)
        self.assertEqual(metrics.packets_delivered + metrics.packets_lost, 2)
        self.assertEqual(metrics.packets_delivered, 2)
        self.assertEqual(metrics.delivery_ratio, 1.0)
        self.assertGreater(metrics.mean_latency_s, 0.04)
        self.assertGreater(metrics.throughput_bps, 0)

    def test_unroutable_packets_are_reported_as_lost(self):
        metrics = simulate_packets([Packet("lost", "x", "y", 200, 0)], self.graph)
        self.assertEqual(metrics.packets_lost, 1)
        self.assertEqual(metrics.delivery_ratio, 0)
        self.assertIsNone(metrics.mean_latency_s)

    def test_predictive_and_multi_criteria_selection(self):
        candidates = [LookAngle("A", 1, 0, 45, True), LookAngle("B", 1, 0, 35, True)]
        self.assertEqual(select_candidate(candidates, strategy="predictive",
            elevation_rate_by_id={"A": -1, "B": 0.5}).satellite_id, "B")
        self.assertEqual(select_candidate(candidates, strategy="strongest_signal",
            snr_by_id={"A": 5, "B": 10}).satellite_id, "B")


if __name__ == "__main__":
    unittest.main()
