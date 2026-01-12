import unittest
from mdeval.munkres import linear_sum_assignment

class TestMunkres(unittest.TestCase):
    def test_simple_assignment(self):
        # 3x3 matrix where diagonal is best (min cost)
        # [[1, 2, 3],
        #  [2, 1, 3],
        #  [3, 2, 1]]
        # But wait, logic finds min cost.
        cost_matrix = [
            [1, 10, 10],
            [10, 1, 10],
            [10, 10, 1]
        ]
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        self.assertEqual(list(row_ind), [0, 1, 2])
        self.assertEqual(list(col_ind), [0, 1, 2])
        self.assertEqual(sum(cost_matrix[r][c] for r, c in zip(row_ind, col_ind)), 3)

    def test_rectangular_matrix(self):
        # 2x3 matrix
        cost_matrix = [
            [1, 10, 10],
            [10, 1, 10]
        ]
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        self.assertEqual(list(row_ind), [0, 1])
        self.assertEqual(list(col_ind), [0, 1])
        
    def test_rectangular_matrix_transposed(self):
        # 3x2 matrix
        cost_matrix = [
            [1, 10],
            [10, 1],
            [10, 10]
        ]
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        # Should match rows 0 and 1
        matched_rows = sorted(list(row_ind))
        self.assertEqual(matched_rows, [0, 1])
        
if __name__ == '__main__':
    unittest.main()
