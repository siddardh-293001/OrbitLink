import tempfile
import unittest
from orbitlink.network.resilience import ResilienceDemo
class EvidenceTests(unittest.TestCase):
 def test_failed_attempt_and_ack_are_persisted(self):
  with tempfile.TemporaryDirectory() as d:
   path=d+'/queue.sqlite';q=ResilienceDemo(path);q.configure(loss_percent=100);q.send('critical')
   q.configure(loss_percent=0);r=q.link(True)
   self.assertEqual([a['acknowledged'] for a in r['attempts']],[False,True])
   self.assertEqual(r['messages'][0]['attempt_count'],2)
   self.assertEqual(len(ResilienceDemo(path).status()['attempts']),2)
 def test_offline_queue_is_not_a_network_attempt(self):
  with tempfile.TemporaryDirectory() as d:
   q=ResilienceDemo(d+'/q.sqlite');q.link(False);r=q.send('offline')
   self.assertEqual(r['attempts'],[])
