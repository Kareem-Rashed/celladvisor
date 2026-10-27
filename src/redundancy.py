import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canon import canon_p
from hdlib import pad_to_4
from contained import load_hd_cells, build_contained_table

FULL = 0xFFFF


def flip_input(tt, k):
    """Truth table with input k inverted."""
    out = 0
    for i in range(16):
        out |= ((tt >> (i ^ (1 << k))) & 1) << i
    return out


class Redundancy:
    def __init__(self, lib_path):
        cells = load_hd_cells(lib_path)
        self.by_class = {}  # canon_p -> (area, cheapest cell name)
        for name, area, pins, tt in cells:
            if len(pins) > 4:
                continue
            c = canon_p(pad_to_4(tt, len(pins)))
            if c not in self.by_class or area < self.by_class[c][0]:
                self.by_class[c] = (area, name)
        self.contained = build_contained_table(cells)

    def classify_full(self, tt):
        """(label, cell name, cell area) for a 16-bit candidate truth table."""
        hit = self.by_class.get(canon_p(tt))
        if hit:
            return "Exists", hit[1], hit[0]
        variants = [FULL ^ tt] + [flip_input(tt, k) for k in range(4)]
        for v in variants:
            hit = self.by_class.get(canon_p(v))
            if hit:
                return "Exists with inverter", hit[1], hit[0]
        hit = self.contained.get(tt)
        if hit:
            return "Contained", hit[1], hit[0]
        return "New", None, None

    def classify(self, tt):
        label, name, _ = self.classify_full(tt)
        return label, name


_default = None


def classify(tt, lib=None):
    global _default
    if _default is None:
        path = lib or os.environ.get(
            "HD_LIB",
            "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")
        _default = Redundancy(path)
    return _default.classify(tt)