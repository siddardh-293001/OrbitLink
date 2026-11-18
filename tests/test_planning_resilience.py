import tempfile
import unittest
from orbitlink.analytics.planning import compare_sites
from orbitlink.network.resilience import ResilienceDemo

class PlanningTests(unittest.TestCase):
    def test_obstruction_changes_visibility_and_gap(self):
        frames=[dict(time=t,satellites=[dict(id='north',xyz=[7000,0,500])]) for t in (0,60,120)]
        sites=[dict(name='clear',lat=0,lon=0,mask=[0]*8),dict(name='blocked',lat=0,lon=0,mask=[89,0,0,0,0,0,0,0])]
        report=compare_sites(frames,sites)
        self.assertEqual(report['recommended'],'clear')
        self.assertEqual(report['sites'][0]['sampled_visibility_percent'],100)
        self.assertEqual(report['sites'][1]['sampled_visibility_percent'],0)
        self.assertEqual(report['sites'][1]['longest_sampled_gap_s'],120)
    def test_invalid_mask_rejected(self):
        with self.assertRaises(ValueError):
            compare_sites([dict(time=0,satellites=[])],[dict(name='bad',lat=0,lon=0,mask=[float('nan')]*8)])

class ResilienceTests(unittest.TestCase):
    def test_outage_persistence_recovery_and_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            path=directory+'/queue.sqlite'
            demo=ResilienceDemo(path);demo.send('initial');demo.link(False)
            for i in range(3):demo.send('outage '+str(i))
            self.assertEqual(demo.status()['queued'],3)
            reopened=ResilienceDemo(path)
            self.assertEqual(reopened.status()['queued'],3)
            reopened.link(True);result=reopened.send('recovery')
            self.assertEqual((result['generated'],result['delivered'],result['direct_delivered']),(5,5,2))
            self.assertEqual(reopened.link(True)['delivered'],5)
            self.assertTrue(all(m['delay_seconds']>=0 for m in result['messages']))
    def test_input_and_session_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            first=ResilienceDemo(directory+'/a.sqlite');second=ResilienceDemo(directory+'/b.sqlite')
            first.send('one');self.assertEqual(second.status()['generated'],0)
            for body in ('', ' '*3, 'x'*501, None):
                with self.assertRaises(ValueError):first.send(body)
