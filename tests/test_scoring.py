import unittest
from mdeval.scoring import apply_collars, exclude_overlapping_speech, score_speaker_diarization, map_speakers
from mdeval.utils import Segment

class TestScoring(unittest.TestCase):
    def test_apply_collars_simple(self):
        uem = [Segment(0.0, 10.0)]
        # Ref data: spk1 from 5.0 to 6.0
        ref_data = {'spk1': [{'TBEG': 5.0, 'TEND': 6.0}]}
        # Collar 0.0 -> No change
        res = apply_collars(uem, ref_data, 0.0)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].tdur, 10.0)
        
        # Collar 0.5 -> Exclude 4.5-6.5
        res = apply_collars(uem, ref_data, 0.5)
        # Should be [0.0, 4.5] and [6.5, 10.0]
        self.assertEqual(len(res), 2)
        self.assertAlmostEqual(res[0].tend, 4.5)
        self.assertAlmostEqual(res[1].tbeg, 6.5)
        
    def test_exclude_overlap(self):
        uem = [Segment(0.0, 10.0)]
        # Two speakers overlapping 4.0-6.0
        ref_data = {
            'spk1': [{'TBEG': 0.0, 'TEND': 6.0, 'TDUR': 6.0}],
            'spk2': [{'TBEG': 4.0, 'TEND': 10.0, 'TDUR': 6.0}]
        }
        res = exclude_overlapping_speech(uem, ref_data)
        # Overlap is 4.0-6.0.
        # Should return [0.0, 4.0], [6.0, 10.0]
        self.assertEqual(len(res), 2)
        self.assertAlmostEqual(res[0].tend, 4.0)
        self.assertAlmostEqual(res[1].tbeg, 6.0)
        
    def test_map_speakers(self):
        # spk1(ref) overlaps spkA(sys) by 10
        # spk2(ref) overlaps spkB(sys) by 10
        overlap = {
            'spk1': {'spkA': 10.0, 'spkB': 0.0},
            'spk2': {'spkA': 0.0, 'spkB': 10.0}
        }
        mapping = map_speakers(overlap)
        self.assertEqual(mapping['spk1'], 'spkA')
        self.assertEqual(mapping['spk2'], 'spkB')

if __name__ == '__main__':
    unittest.main()
