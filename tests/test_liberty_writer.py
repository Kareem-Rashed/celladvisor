"""Tests for the Liberty writer, the request writer and the Liberty check
(Option 2 handout, sections 4 step 8 and 6; overview, Appendix A).
The last tests need yosys on the PATH and the given files (make setup)."""

import os
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from check_liberty import check_liberty
from hdlib import eval_function
from liberty_writer import cell_group, request, sop, timing_sense, write_library

MAJ4N = ("dd2_g5__maj4n_1", "!((C&D) | (A&B&(C|D)))", 8.7584)
BROKEN = ROOT / "tests" / "broken"


def test_request_matches_appendix_a():
    # Overview, Appendix A: this expression is truth table 0x077F.
    r = request(*MAJ4N, "B-017")
    assert r["truth_table"] == "0x077F"
    assert r["inputs"] == ["A", "B", "C", "D"] and r["output"] == "Y"
    assert r["sizing"] == "hd" and r["estimated_area_um2"] == 8.7584


def test_cell_group_matches_the_handout_example():
    # The writer reproduces given/examples/new_cell_example.lib exactly.
    example = open("given/examples/new_cell_example.lib").read()
    example = example[example.index('  cell ("'):]
    example = example.replace("    /* one timing group like this for each of B, C and D */\n", "")
    assert cell_group(*MAJ4N) == example


def test_timing_sense():
    assert timing_sense(0b0111, 2, 0) == "negative_unate"   # nand2
    assert timing_sense(0b1000, 2, 1) == "positive_unate"   # and2
    assert timing_sense(0b0110, 2, 0) == "non_unate"        # xor2


def test_sop_gives_the_same_function():
    rng = random.Random(1)
    tts = [0x077F, 0x8000, 0x0001, 0x6996, 0x00AF] + [rng.randrange(1, 0xFFFF) for _ in range(300)]
    for tt in tts:
        assert eval_function(sop(tt), ["A", "B", "C", "D"]) == tt, hex(tt)


def test_duplicate_cell_name_is_refused():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "x.lib")
        write_library("given/hd_reduced.lib", [MAJ4N], out)
        try:
            write_library(out, [MAJ4N], os.path.join(d, "y.lib"))
        except ValueError:
            return
    raise AssertionError("a cell already in the library was added again")


def test_extended_library_loads_in_yosys():
    with tempfile.TemporaryDirectory(dir="build" if os.path.isdir("build") else None) as d:
        out = os.path.join(d, "hd_extended.lib")
        write_library("given/hd_reduced.lib", [MAJ4N], out)
        ok, message = check_liberty(out, 189 + 1)
        assert ok, message


def test_broken_liberty_missing_brace_is_rejected():
    ok, message = check_liberty(str(BROKEN / "liberty_missing_brace.lib"))
    assert not ok, message


def test_broken_liberty_unknown_pin_is_rejected():
    # read_liberty -lib alone accepts this file; check_liberty must not.
    ok, message = check_liberty(str(BROKEN / "liberty_unknown_pin.lib"))
    assert not ok, message


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
