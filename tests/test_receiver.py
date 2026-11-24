import tempfile
import unittest
import os
from unittest.mock import patch
from orbitlink.network.receiver import ReceiverStore
from orbitlink.network.resilience import ResilienceDemo
class ReceiverTests(unittest.TestCase):
 def test_ack_idempotency_and_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   r=ReceiverStore(d+'/received.sqlite')
   self.assertFalse(r.accept('id','hello')['duplicate'])
   self.assertTrue(r.accept('id','hello')['duplicate'])
   with self.assertRaises(ValueError):r.accept('id','different')
 def test_failed_ack_queues_and_retry_delivers(self):
  with tempfile.TemporaryDirectory() as d:
   sender=ResilienceDemo(d+'/sent.sqlite')
   with patch.object(sender,'deliver',return_value=False):self.assertEqual(sender.send('hello')['queued'],1)
   with patch.object(sender,'deliver',return_value=True):self.assertEqual(sender.link(True)['delivered'],1)
