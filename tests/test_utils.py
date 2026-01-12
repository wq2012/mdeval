import unittest
from mdeval.utils import Segment, merge_segments

class TestUtils(unittest.TestCase):
    def test_segment_init(self):
        s = Segment(1.0, 2.0)
        self.assertEqual(s.tbeg, 1.0)
        self.assertEqual(s.tend, 2.0)
        self.assertEqual(s.tdur, 1.0)
        
    def test_segment_equality(self):
        s1 = Segment(1.0, 2.0)
        s2 = Segment(1.0, 2.0)
        s3 = Segment(1.5, 2.5)
        self.assertEqual(s1, s2)
        self.assertNotEqual(s1, s3)
        
    def test_merge_segments(self):
        # Test merging overlapping segments
        segs = [
            Segment(1.0, 3.0),
            Segment(2.0, 4.0),
            Segment(5.0, 6.0)
        ]
        merged = merge_segments(segs)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].tbeg, 1.0)
        self.assertEqual(merged[0].tend, 4.0)
        self.assertEqual(merged[1].tbeg, 5.0)
        self.assertEqual(merged[1].tend, 6.0)
        
    def test_merge_segments_empty(self):
        self.assertEqual(merge_segments([]), [])


if __name__ == '__main__':
    unittest.main()
