import sys

def linear_sum_assignment(cost_matrix):
    """
    Solve the linear sum assignment problem using the Hungarian algorithm (Munkres algorithm).
    Minimizes the total cost.
    Input: cost_matrix (list of lists of numbers)
    Output: row_ind, col_ind (lists of indices)
    """
    C = [row[:] for row in cost_matrix]
    n_rows = len(C)
    n_cols = len(C[0])
    
    # Ensure square matrix by padding with zeros if necessary (or large values for min cost?)
    # For min cost, padding with 0 might attract assignments?
    # If we want to force assignment of all rows (if rows <= cols), we want true min cost.
    # If we pad with 0s, the algorithm might pick 0s.
    # Scipy linear_sum_assignment handles rectangular.
    # If rows > cols, we can transpose.
    
    transposed = False
    if n_rows > n_cols:
        C = [[C[r][c] for r in range(n_rows)] for c in range(n_cols)]
        n_rows, n_cols = n_cols, n_rows
        transposed = True
        
    # Now n_rows <= n_cols
    
    # We can pad columns to make it square n_cols x n_cols
    # Padding with 0s is safe if we simply ignore the assignments to dummy columns later?
    # But 0s might be preferred over real costs.
    # If costs are negative (for max overlap, we negated them), valid costs are negative.
    # 0 is strictly worse than negative (good).
    # If original costs were positive (minimization), we'd pad with 0?
    # No, for minimization, 0 is best.
    # We are doing minimization (of negative overlap).
    # Costs are like -10.0, -5.0 etc.
    # So 0 is "high cost" (no overlap).
    # So padding with 0 is essentially "no overlap cost".
    # This works.
    
    # Use a simple implementation of Munkres for square matrix
    # Based on a standard implementation structure
    
    # Make square
    size = n_cols
    for row in C:
        row.extend([0] * (size - len(row)))
    while len(C) < size:
        C.append([0] * size)
        
    # Subtract row mins
    for r in range(size):
        min_val = min(C[r])
        for c in range(size):
            C[r][c] -= min_val
            
    # Subtract col mins
    for c in range(size):
        min_val = min(C[r][c] for r in range(size))
        for r in range(size):
            C[r][c] -= min_val
            
    # Star zeros
    stars = {} # (r, c)
    rows_covered = [False] * size
    cols_covered = [False] * size
    
    for r in range(size):
        for c in range(size):
            if C[r][c] == 0 and not rows_covered[r] and not cols_covered[c]:
                stars[(r, c)] = True
                rows_covered[r] = True
                cols_covered[c] = True
    
    rows_covered = [False] * size
    cols_covered = [False] * size
    
    prime_locations = {} # (r, c)
    
    def cover_starred_cols():
        covered_count = 0
        for r, c in stars.keys():
            cols_covered[c] = True
        for c in range(size):
            if cols_covered[c]: score = 1
        return sum(cols_covered)

    while True:
        # Step 1: Cover columns of starred zeros
        # If all columns covered, we are done
        count = 0
        cols_covered = [False] * size
        for (r, c) in stars.keys():
            cols_covered[c] = True
        
        if sum(cols_covered) == size:
            break
            
        # Step 2: Prime some uncovered zero
        while True:
            # Find an uncovered zero
            zero_loc = None
            for r in range(size):
                if not rows_covered[r]:
                    for c in range(size):
                        if not cols_covered[c] and abs(C[r][c]) < 1e-9:
                            zero_loc = (r, c)
                            break
                if zero_loc: break
            
            if not zero_loc:
                # Step 4: Update matrix
                min_uncovered = float('inf')
                for r in range(size):
                    if not rows_covered[r]:
                        for c in range(size):
                            if not cols_covered[c]:
                                if C[r][c] < min_uncovered:
                                    min_uncovered = C[r][c]
                
                if min_uncovered == float('inf'):
                    # Should not happen
                    return [], []
                    
                for r in range(size):
                    if rows_covered[r]:
                        for c in range(size):
                            C[r][c] += min_uncovered
                for c in range(size):
                    if not cols_covered[c]:
                        for r in range(size):
                            C[r][c] -= min_uncovered
                            
            else:
                # Prime it
                prime_locations[zero_loc] = True
                r, c = zero_loc
                
                # Check if there is a starred zero in this row
                starred_col = None
                for sc in range(size):
                    if (r, sc) in stars:
                        starred_col = sc
                        break
                
                if starred_col is not None:
                    rows_covered[r] = True
                    cols_covered[starred_col] = False
                else:
                    # Step 3: Make path
                    path = [zero_loc]
                    while True:
                        # Find starred zero in this column
                        last_c = path[-1][1]
                        starred_row = None
                        for sr in range(size):
                            if (sr, last_c) in stars:
                                starred_row = sr
                                break
                        
                        if starred_row is None:
                            break
                            
                        path.append((starred_row, last_c))
                        
                        # Find primed zero in this row
                        primed_col = None
                        for pc in range(size):
                            if (starred_row, pc) in prime_locations:
                                primed_col = pc
                                break
                        path.append((starred_row, primed_col))
                    
                    # Unstar starred, star primed
                    for r_p, c_p in path:
                        if (r_p, c_p) in stars:
                            del stars[(r_p, c_p)]
                        else:
                            stars[(r_p, c_p)] = True
                            
                    # Clear covers and primes
                    rows_covered = [False] * size
                    cols_covered = [False] * size
                    prime_locations = {}
                    break # Go back to Step 1

    # Assignments
    row_ind = []
    col_ind = []
    
    # Sort by row index
    for r, c in stars.keys():
        if r < n_rows and c < n_cols:
            if transposed:
                row_ind.append(c)
                col_ind.append(r)
            else:
                row_ind.append(r)
                col_ind.append(c)
                
    # Sort result
    if transposed:
        # Sort based on "original rows" which are now col_ind?
        # Wait, if transposed: original rows matching original cols
        # input was n_orig_row > n_orig_col
        # We transposed to n_new_row < n_new_col
        # stars are (r_new, c_new)
        # c_new corresponds to original rows
        # r_new corresponds to original cols
        # we swapped them
        # so output lists are:
        # row_ind (original cols) -> col_ind (original rows) which is backward
        # we want Matches for Original Rows.
        # But `linear_sum_assignment` returns (row_indices, col_indices) such that cost is minimized.
        # It returns essentially a set of pairs.
        # We want to return sorted by row index?
        # Scipy returns sorted row_ind and corresponding col_ind.
        zipped = sorted(zip(row_ind, col_ind))
        row_ind = [z[0] for z in zipped]
        col_ind = [z[1] for z in zipped]
    else:
        zipped = sorted(zip(row_ind, col_ind))
        row_ind = [z[0] for z in zipped]
        col_ind = [z[1] for z in zipped]
        
    return row_ind, col_ind
