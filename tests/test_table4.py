import os, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from canon import canon_p, used_inputs
from redundancy import Redundancy

HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")

EXPECTED = {"Exists": 24, "Exists with inverter": 20,
            "Contained": 38, "New": 3822}


def test_table4():
    red = Redundancy(HD_LIB)
    reps = {canon_p(tt) for tt in range(1 << 16)
            if used_inputs(tt) == {0, 1, 2, 3}}
    assert len(reps) == 3904
    counts = Counter(red.classify(tt)[0] for tt in reps)
    print(dict(counts))
    assert dict(counts) == EXPECTED


if __name__ == "__main__":
    test_table4()
    print("pass test_table4")