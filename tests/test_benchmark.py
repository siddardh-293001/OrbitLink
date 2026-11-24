import unittest
from orbitlink.analytics.benchmark import benchmark
class BenchmarkTests(unittest.TestCase):
 def test_reproducible_and_accounted(self):
  a=benchmark();self.assertEqual(a,benchmark())
  for r in a['results']:self.assertEqual(r['generated'],r['delivered']+r['pending']+r['dropped'])
 def test_no_loss_queue_recovers(self):
  r=benchmark(loss_percent=0)['results']
  self.assertLess(r[0]['delivered'],20);self.assertEqual(r[2]['delivered'],20);self.assertEqual(r[2]['pending'],0)
 def test_total_loss_stays_pending(self):
  r=benchmark(loss_percent=100)['results'];self.assertEqual(r[2]['pending'],20);self.assertEqual(r[0]['dropped'],20)
