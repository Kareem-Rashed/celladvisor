"""The cec check of src/table5.py must pass a correct mapping and fail on the
broken case tests/broken/cec_swapped_gate.json (one gate replaced by another
with the same pins). Needs yosys and yosys-abc on the PATH and the given files."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from table5 import cec, map_design, reference

CASE = json.loads((ROOT / "tests" / "broken" / "cec_swapped_gate.json").read_text())
WORK = "build/test_cec"


def mapped():
    os.makedirs(WORK, exist_ok=True)
    verilog = f"given/designs/{CASE['design']}.v"
    ref_v, impl_v = f"{WORK}/ref.v", f"{WORK}/impl.v"
    map_design(verilog, CASE["top"], CASE["library"], CASE["script"], impl_v, f"{WORK}/stat.txt")
    reference(verilog, CASE["top"], CASE["library"], ref_v)
    return ref_v, impl_v


def test_cec_passes_the_real_mapping():
    ref_v, impl_v = mapped()
    passed, line = cec(ref_v, impl_v, CASE["top"], CASE["library"], f"{WORK}/good")
    assert passed, line


def test_cec_rejects_a_swapped_gate():
    ref_v, impl_v = mapped()
    text = open(impl_v).read()
    assert CASE["replace"] in text, "the netlist has no gate to swap"
    bad_v = f"{WORK}/bad.v"
    with open(bad_v, "w") as f:
        f.write(text.replace(CASE["replace"], CASE["with"], 1))
    passed, line = cec(ref_v, bad_v, CASE["top"], CASE["library"], f"{WORK}/bad")
    assert not passed, "cec accepted a netlist with a swapped gate"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
