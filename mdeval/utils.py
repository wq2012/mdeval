from typing import List, Tuple, Dict, Any, Optional

class Segment:
    def __init__(self, tbeg: float, tend: float):
        self.tbeg = tbeg
        self.tend = tend

    @property
    def tdur(self) -> float:
        return self.tend - self.tbeg

    def intersect(self, other: 'Segment') -> Optional['Segment']:
        max_tbeg = max(self.tbeg, other.tbeg)
        min_tend = min(self.tend, other.tend)
        if max_tbeg < min_tend:
            return Segment(max_tbeg, min_tend)
        return None

    def __repr__(self):
        return f"Segment({self.tbeg:.2f}, {self.tend:.2f})"

    def __eq__(self, other):
        if not isinstance(other, Segment):
            return False
        return abs(self.tbeg - other.tbeg) < 1e-9 and abs(self.tend - other.tend) < 1e-9


def merge_segments(segments: List[Segment]) -> List[Segment]:
    if not segments:
        return []
    sorted_segs = sorted(segments, key=lambda s: s.tbeg)
    merged = [sorted_segs[0]]
    for current in sorted_segs[1:]:
        last = merged[-1]
        if current.tbeg <= last.tend:
            last.tend = max(last.tend, current.tend)
        else:
            merged.append(current)
    return merged
