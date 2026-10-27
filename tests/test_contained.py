"""Tests for the Contained check (src/contained.py).
Cell format: (name, area, pins, truth_table), pin j = bit j of the row number."""

import os
import sys
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contained import SOURCES, build_contained_table, contained_in, load_hd_cells, wire

HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
)

A, B, C, D = 0xAAAA, 0xCCCC, 0xF0F0, 0xFF00
MASK = 0xFFFF

NAND2 = ("nand2_1", 3.75, ["A", "B"], 0x7)
NAND3 = ("nand3_1", 5.0, ["A", "B", "C"], 0x7F)          # 0 only at row 7
MUX2 = ("mux2_1", 11.26, ["A0", "A1", "S"], 0xCA)        # S ? A1 : A0
AND4 = ("and4_1", 8.76, ["A", "B", "C", "D"], 0x8000)    # 1 only at row 15
AND4_X2 = ("and4_2", 10.0, ["A", "B", "C", "D"], 0x8000)


def test_sources_follow_the_group_convention():
    # Input A is bit 0 of the row number, so A is 1 on odd rows, and so on.
    for name, bit in zip("ABCD", range(4)):
        expected = sum(1 << row for row in range(16) if (row >> bit) & 1)
        assert SOURCES[name] == expected


def test_nand3_with_one_pin_tied_high_is_nand2():
    assert wire(NAND3[3], ("A", "B", "1")) == ~(A & B) & MASK == 0x7777


def test_mux2_with_select_tied_low_passes_A0():
    assert wire(MUX2[3], ("A", "B", "0")) == A
    assert wire(MUX2[3], ("A", "B", "1")) == B


def test_shared_input():
    # nand2 with both pins on C is an inverter of C.
    assert wire(NAND2[3], ("C", "C")) == ~C & MASK


def test_four_pin_cell_wired_straight_through_finds_itself():
    table = build_contained_table([AND4])
    assert contained_in(A & B & C & D, table)[1] == "and4_1"


def test_cheapest_cell_is_kept():
    table = build_contained_table([AND4_X2, AND4])
    area, name, wiring = contained_in(A & B & C & D, table)
    assert (name, area) == ("and4_1", 8.76)
    assert wiring == {"A": "A", "B": "B", "C": "C", "D": "D"}


def test_table_is_closed_under_input_order():
    # Every wiring is tried, so every input permutation of a reachable
    # function must also be reachable.
    table = build_contained_table([NAND3, MUX2])
    for tt in table:
        for perm in permutations(range(4)):
            permuted = 0
            for row in range(16):
                src_row = sum(((row >> perm[k]) & 1) << k for k in range(4))
                permuted |= ((tt >> src_row) & 1) << row
            assert permuted in table


def test_function_no_cell_makes_is_not_contained():
    # XOR cannot come from nand3 or mux2 with inputs tied to A..D, 0, 1.
    table = build_contained_table([NAND3, MUX2])
    assert contained_in(A ^ B, table) is None


def test_real_library():
    assert os.path.exists(HD_LIB), f"HD library not found: {HD_LIB}"
    cells = load_hd_cells(HD_LIB)
    by_name = {c[0].split("__")[-1]: c for c in cells}
    assert by_name["nand2_1"][1] > 0                      # area was read
    assert by_name["nand2_1"][3] == 0x7                   # !(A&B) over 2 pins
    table = build_contained_table(cells)
    # nand2 is reachable, and the cheapest cell that makes it is a nand2.
    assert "nand2" in contained_in(0x7777, table)[1]
    # The handout's example of a cell HD lacks is not reachable by tying pins.
    assert contained_in(0x077F, table) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
