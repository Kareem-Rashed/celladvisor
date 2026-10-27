"""Broken case for the cut checker (overview, rule 4.3.3; Option 2 handout, 9.1).

The cut checker takes a cut (a root AND node and up to 4 leaf nodes of an AIG)
and a claimed 16-bit truth table, simulates the cut for all 16 input rows, and
says whether the claim is right. It must accept the right truth table and
reject a wrong one.

Expected interface, from whoever writes task 1 (the cut enumerator):
    src/cuts.py:  verify_cut(aig_path, root, leaves, tt) -> bool
where root and leaves are AIGER variable numbers and leaves[k] is input k
(A, B, C, D). If the real function has another name, change only the import.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

BROKEN = Path(__file__).parent / "broken"
CASE = json.loads((BROKEN / "wrong_cut_tt.json").read_text())
AIG = str(BROKEN / CASE["aig"])


def test_correct_truth_table_by_hand():
    # node5 = !(a & b) & !c, with a = A, b = B, c = C.
    A, B, C = 0xAAAA, 0xCCCC, 0xF0F0
    assert ~(A & B) & ~C & 0xFFFF == int(CASE["correct_truth_table"], 16)


def test_checker_accepts_the_correct_truth_table():
    # Without this, a checker that rejects everything would also "pass".
    from cuts import verify_cut
    tt = int(CASE["correct_truth_table"], 16)
    assert verify_cut(AIG, CASE["root"], CASE["leaves"], tt)


def test_checker_rejects_a_wrong_truth_table():
    from cuts import verify_cut
    tt = int(CASE["wrong_truth_table"], 16)
    assert not verify_cut(AIG, CASE["root"], CASE["leaves"], tt)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
