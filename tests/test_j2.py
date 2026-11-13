import math
import unittest
from orbitlink.orbit.constellation import generate_constellation
from orbitlink.orbit.j2 import secular_rates, propagate_j2
from orbitlink.analytics.simulator import run_simulation

class J2Tests(unittest.TestCase):
    def test_sun_synchronous_reference(self):
        element=generate_constellation(planes=1,satellites_per_plane=1,altitude_km=7000-6378.137,inclination_deg=97.87377)[0]
        self.assertAlmostEqual(math.degrees(secular_rates(element)[0])*86400,.9856,delta=.001)
    def test_polar_node_and_velocity(self):
        element=generate_constellation(planes=1,satellites_per_plane=1,inclination_deg=90)[0]
        self.assertAlmostEqual(secular_rates(element)[0],0,places=15)
        state=propagate_j2(element,600)
        before=propagate_j2(element,599.5).position_eci_m
        after=propagate_j2(element,600.5).position_eci_m
        for v,a,b in zip(state.velocity_eci_m_s,before,after):
            self.assertAlmostEqual(v,b-a,delta=.01)
    def test_pipeline(self):
        result=run_simulation(duration_seconds=60,timestep_seconds=30,include_j2=True)
        self.assertEqual(result.model_name,'Synthetic secular J2')
        self.assertEqual(len(result.satellite_states),3)
