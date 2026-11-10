import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from canon import canon_p, canon_pn, canon_npn, negate_inputs, permute, used_inputs


def test_permute_swap():
    assert permute(0x2222, (1, 0, 2, 3)) == 0x4444


def test_permute_identity():
    assert permute(0x2222, (0, 1, 2, 3)) == 0x2222


def test_canon_same_gate():
    assert canon_p(0x2222) == canon_p(0x4444) == 0x00AA


def test_used_inputs():
    assert used_inputs(0x2222) == {0, 1}
    assert used_inputs(0x00AA) == {0, 3}


def test_3904_classes():
    full = {canon_p(tt) for tt in range(1 << 16) if used_inputs(tt) == {0, 1, 2, 3}}
    assert len(full) == 3904

def test_npn_merges_nand_nor_and_or():
    nand2, nor2 = 0x7777, 0x1111
    and2, or2 = 0x8888, 0xEEEE
    assert len({canon_npn(t) for t in (nand2, nor2, and2, or2)}) == 1   # NPN: one class
    assert len({canon_pn(t) for t in (nand2, nor2, and2, or2)}) == 2    # PN: two classes


def test_222_npn_classes():
    # Independent check: group all 65,536 functions with union-find over the
    # basic moves (swap inputs, invert an input, invert the output).
    parent = list(range(1 << 16))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for tt in range(1 << 16):
        moves = [0xFFFF - tt] + [negate_inputs(tt, 1 << i) for i in range(4)]
        moves += [permute(tt, p) for p in [(1, 0, 2, 3), (0, 2, 1, 3), (0, 1, 3, 2)]]
        for other in moves:
            parent[find(tt)] = find(other)

    groups = {}
    for tt in range(1 << 16):
        groups.setdefault(find(tt), []).append(tt)
    assert len(groups) == 222                       # the known count for 4 inputs
    assert len({canon_npn(g[0]) for g in groups.values()}) == 222
    assert all(canon_npn(g[0]) == canon_npn(g[-1]) for g in groups.values())


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)