import unittest
import tempfile
import os
from mdeval.io import load_rttm, load_uem

class TestIO(unittest.TestCase):
    def test_load_rttm(self):
        content = """SPEAKER file1 1 0.0 5.0 <NA> <NA> spk1 <NA> <NA>
SPEAKER file1 1 5.0 5.0 <NA> <NA> spk2 <NA> <NA>
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            data = load_rttm(tmp_path)
            self.assertIn('file1', data)
            self.assertIn('1', data['file1'])
            spk_data = data['file1']['1']['SPEAKER']
            self.assertEqual(len(spk_data), 2)
            self.assertEqual(spk_data[0]['SPKR'], 'spk1')
            self.assertAlmostEqual(spk_data[0]['TDUR'], 5.0)
        finally:
            os.remove(tmp_path)
            
    def test_load_uem(self):
        content = """file1 1 0.0 10.0
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            uem = load_uem(tmp_path)
            self.assertIn('file1', uem)
            self.assertIn('1', uem['file1'])
            self.assertEqual(len(uem['file1']['1']), 1)
            self.assertEqual(uem['file1']['1'][0].tbeg, 0.0)
            self.assertEqual(uem['file1']['1'][0].tend, 10.0)
        finally:
            os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
