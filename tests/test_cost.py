import itertools, time, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cost import cost, VAR, MASK

A, B, C, D = VAR
def inv(t): return ~t & MASK

def test_basic():
    assert cost(inv(A & B)) == (4, True)                 # nand2
    assert cost(inv(A | B)) == (4, True)                 # nor2
    assert cost(inv(A & B & C)) == (6, True)             # nand3
    assert cost(inv((A & B) | C)) == (6, True)           # aoi21
    assert cost(inv(A)) == (2, True)                     # inverter

def test_and_or_are_two_stage():
    t, s = cost(A & B)
    assert not s and t == 6                              # nand + inv
    t, s = cost(A | B)
    assert not s and t == 6

def test_maj4n_example():
    # handout section 5: !((C&D) | (A&B&(C|D))) -> 6 literals, 12 transistors
    f = inv((C & D) | (A & B & (C | D)))
    assert cost(f) == (12, True)

def test_nand4_is_single_stage():
    assert cost(inv(A & B & C & D)) == (8, True)   # 4 in series, but areamodel says single

def test_xor_is_rough_but_multistage():
    t, s = cost(A ^ B)
    assert not s and t > 8
    t, s = cost(A ^ B ^ C ^ D)
    assert not s and t >= 12

def test_all_tts_run():
    t0 = time.time()
    for tt in range(0, 65536, 7):
        t, s = cost(tt)
        assert t >= 0
    assert time.time() - t0 < 60


def test_matches_areamodel_definition():
    from areamodel import is_single_stage
    for tt in range(65536):
        assert cost(tt)[1] == is_single_stage(tt, 4), hex(tt)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
