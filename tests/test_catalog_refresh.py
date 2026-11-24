import unittest
import tempfile
import os
from unittest.mock import patch
from pathlib import Path
from orbitlink.orbit.catalog import refresh_catalog, REFRESH_STATUS
class RefreshTests(unittest.TestCase):
 def test_failed_refresh_preserves_snapshot(self):
  with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'ORBITLINK_DATA_DIR':directory}):
   path=Path(directory)/'catalogs/starlink.json';path.parent.mkdir();path.write_text('previous valid snapshot')
   with patch('orbitlink.orbit.catalog.fetch_catalog',side_effect=TimeoutError('offline')):refresh_catalog('Starlink')
   self.assertEqual(path.read_text(),'previous valid snapshot')
   self.assertFalse(REFRESH_STATUS['Starlink']['ok'])
