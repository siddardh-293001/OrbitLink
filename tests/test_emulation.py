import tempfile
import unittest
from unittest.mock import patch
from orbitlink.network.resilience import ResilienceDemo
class EmulationTests(unittest.TestCase):
 def test_loss_queues_then_recovery_delivers(self):
  with tempfile.TemporaryDirectory() as d:
   q=ResilienceDemo(d+'/q.sqlite');q.configure(loss_percent=100)
   self.assertEqual(q.send('critical')['queued'],1)
   q.configure(loss_percent=0)
   self.assertEqual(q.link(True)['delivered'],1)
 def test_delay_and_jitter_bounds(self):
  with tempfile.TemporaryDirectory() as d:
   q=ResilienceDemo(d+'/q.sqlite');q.configure(delay_ms=100,jitter_ms=20)
   with patch('orbitlink.network.resilience.random.uniform',return_value=-20),patch('orbitlink.network.resilience.time.sleep') as sleep:
    q.send('test');sleep.assert_called_once_with(.08)
   with self.assertRaises(ValueError):q.configure(loss_percent=101)
