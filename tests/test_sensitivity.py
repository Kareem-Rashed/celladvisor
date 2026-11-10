"""Tests for the 30% experiment (src/sensitivity.py).

The shrunk cell list must be the same as the final list, except that one
cell's area is exactly 30% smaller."""

import sys

sys.path.insert(0, "src")
from sensitivity import shrink

CELL_A = ("dd2_x__a_1", "(A&B) | C", 8.7584)
CELL_B = ("dd2_x__b_1", "!(A&B&C)", 7.5072)
CELLS = [CELL_A, CELL_B]


def test_only_the_named_cell_changes():
    small = shrink(CELLS, "dd2_x__a_1", 0.7)

    # cell A: same name and expression, area 30% smaller
    assert small[0][0] == "dd2_x__a_1"
    assert small[0][1] == "(A&B) | C"
    assert small[0][2] == round(8.7584 * 0.7, 4)

    # cell B: not touched at all
    assert small[1] == CELL_B


def test_order_is_kept():
    small = shrink(CELLS, "dd2_x__b_1", 0.7)
    assert small[0][0] == "dd2_x__a_1"
    assert small[1][0] == "dd2_x__b_1"


def test_unknown_cell_is_refused():
    try:
        shrink(CELLS, "dd2_x__missing_1", 0.7)
    except ValueError:
        return  # good: the unknown cell was refused
    raise AssertionError("a cell that is not in the list was accepted")


if __name__ == "__main__":
    test_only_the_named_cell_changes()
    print("pass test_only_the_named_cell_changes")
    test_order_is_kept()
    print("pass test_order_is_kept")
    test_unknown_cell_is_refused()
    print("pass test_unknown_cell_is_refused")
