import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from areamodel import count_transistors, is_single_stage, x1_cells, fit

HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")
SPICE = os.environ.get(
    "SPICE",
    "pdk/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice")


def test_transistor_counts():
    counts = count_transistors(SPICE)
    assert counts["sky130_fd_sc_hd__inv_1"] == 2
    assert counts["sky130_fd_sc_hd__nand2_1"] == 4
    assert counts["sky130_fd_sc_hd__a21oi_1"] == 6


def test_single_stage():
    assert is_single_stage(0x7, 2)
    assert not is_single_stage(0x8, 2)
    assert not is_single_stage(0x6, 2)
    assert is_single_stage(0x1, 1)


def test_twelve_transistors_is_eight_sites():
    cells = x1_cells(HD_LIB, SPICE)
    slope, intercept = fit(cells, True)
    assert round(slope * 12 + intercept) == 8


def test_mean_error_under_one_site():
    cells = x1_cells(HD_LIB, SPICE)
    for single in (True, False):
        slope, intercept = fit(cells, single)
        errors = [abs(round(slope * t + intercept) - sites)
                  for name, sites, t, one in cells if one == single]
        assert sum(errors) / len(errors) < 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)