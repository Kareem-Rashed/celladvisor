import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hdlib import eval_function, support, pad_to_4, build_table
from canon import canon_p, canon_pn

HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
)


def test_and2():
    assert eval_function("(A&B)", ["A", "B"]) == 0b1000


def test_inv_padded():
    tt = pad_to_4(eval_function("!A", ["A"]), 1)
    assert tt == 0x5555  # A is bit 0, so output is 1 on even rows


def test_xor_and_precedence():
    assert pad_to_4(eval_function("A^B", ["A", "B"]), 2) == 0x6666
    # & binds tighter than |
    assert eval_function("A|B&C", ["A", "B", "C"]) == eval_function("A|(B&C)", ["A", "B", "C"])


def test_a2bb2o():
    expr = "(B1&B2) | (!A1_N&!A2_N)"
    order = support(expr)
    assert order == ["A1_N", "A2_N", "B1", "B2"]
    assert eval_function(expr, order) == 0xF111


def test_support_ignores_constants():
    assert support("(A&1)|0") == ["A"]


FAKE = '''
cell ("x__and2_1") {
  pg_pin ("VPWR") { pg_type : "primary_power"; }
  pin ("A") { direction : "input"; }
  pin ("B") { direction : "input"; }
  pin ("X") { direction : "output"; function : "(A&B)";
              power_down_function : "(!VPWR + VGND)"; }
}
cell ("x__dff_1") {
  ff ("IQ", "IQN") { clocked_on : "CLK"; next_state : "D"; }
  pin ("Q") { direction : "output"; function : "IQ"; }
}
cell ("x__and2_2") {
  pin ("A") { direction : "input"; }
  pin ("B") { direction : "input"; }
  pin ("X") { direction : "output"; function : "(A&B)"; }
}
'''


def test_reader_and_classes():
    with tempfile.NamedTemporaryFile("w", suffix=".lib", delete=False) as f:
        f.write(FAKE)
        path = f.name
    rows, wide, skipped = build_table(path, canon_p, canon_pn)
    os.unlink(path)
    assert [r[0] for r in rows] == ["x__and2_1", "x__and2_2"]
    assert rows[0][2] == "8888"
    assert rows[0][3] == rows[1][3]  # two drives, one P class
    assert skipped == ["x__dff_1"]


def test_real_library():
    assert os.path.exists(HD_LIB), f"HD library not found: {HD_LIB}"
    rows, wide, skipped = build_table(HD_LIB, canon_p, canon_pn)
    by_name = {r[0].split("__")[-1]: r for r in rows}
    assert by_name["and2_1"][2] == "8888"
    assert by_name["inv_1"][2] == "5555"
    assert by_name["xor2_1"][2] == "6666"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)