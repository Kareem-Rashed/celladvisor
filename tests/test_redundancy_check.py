"""Broken case for the redundancy checker (Option 2 handout, sections 5 and 9.1).

"Every combinational HD cell, fed to it as a candidate, must come out as
Exists." A checker with a bug in its Exists test would call HD's own cells
New, and the project would propose cells HD already has.

Expected interface, from the redundancy checker (Mahinour's part):
    src/redundancy.py:  classify(tt) -> (label, hd_cell_name)
        label is "Exists", "Exists with an inverter", "Contained" or "New"
If the real function has another name, change only the import.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contained import wire

BROKEN = Path(__file__).parent / "broken"
CASE = json.loads((BROKEN / "hd_cell_as_candidate.json").read_text())

HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
)


def test_hd_nand2_fed_as_candidate_is_exists():
    from redundancy import classify
    label, _ = classify(int(CASE["truth_table"], 16))
    assert label == CASE["expected"]


def test_every_hd_cell_up_to_4_inputs_is_exists():
    # Candidates are 4-input functions, so only HD cells with at most 4 inputs
    # can be fed in as candidates. Pin j of the cell goes to input j (A..D).
    from contained import load_hd_cells
    from redundancy import classify
    assert os.path.exists(HD_LIB), f"HD library not found: {HD_LIB}"
    cells = [c for c in load_hd_cells(HD_LIB) if len(c[2]) <= 4]
    assert cells, "no cells loaded"
    wrong = []
    for name, _area, pins, cell_tt in cells:
        tt = wire(cell_tt, "ABCD"[: len(pins)])
        label, _ = classify(tt)
        if label != "Exists":
            wrong.append((name, f"{tt:04x}", label))
    assert not wrong, f"HD cells not classed as Exists: {wrong}"


def test_handout_example_is_new():
    # !((C&D) | (A&B&(C|D))), the handout's example of a one-stage cell HD
    # lacks (Option 2 handout, section 5). Guards against a checker that says
    # Exists for everything.
    from redundancy import classify
    label, _ = classify(0x077F)
    assert label == "New"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
