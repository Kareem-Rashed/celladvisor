import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aig_reader import read_aag
from cutter import remove_dominated, combine, enumerate_cuts

# a, b, c, d = vars 1-4;  n1 = a & b (5);  n2 = c & !d (6);  y = !n1 & !n2 (7)
TINY = """aag 7 4 0 1 3
2
4
6
8
14
10 2 4
12 6 9
14 11 13
"""

# a, b, c = vars 1-3;  x = a & b (4);  z = x & c (5);  y = x & z (6)
# the circuit from the diagram, which has a dominated cut
DOMINATED = """aag 6 3 0 1 3
2
4
6
12
8 2 4
10 8 6
12 8 10
"""


def cut(*vars):
    return frozenset(vars)


def test_remove_dominated():
    # {1,2,3} contains {1,3}, so it goes; {2,4} contains nothing, so it stays
    cut_list = [cut(1, 3), cut(1, 2, 3), cut(2, 4)]
    assert remove_dominated(cut_list) == [cut(1, 3), cut(2, 4)]


def test_combine():
    # the 2 x 2 table for gate 7
    left = [cut(5), cut(1, 2)]
    right = [cut(6), cut(3, 4)]
    expected = {cut(5, 6), cut(3, 4, 5), cut(1, 2, 6), cut(1, 2, 3, 4)}
    assert set(combine(left, right)) == expected


def test_combine_size_limit():
    # {1,2,3} | {4,5} has 5 leaves: too big for a 4-input cell
    assert combine([cut(1, 2, 3)], [cut(4, 5)]) == []

def test_combine_no_duplicates():
    # {1,2}|{3} and {1,3}|{2} both give {1,2,3}; it must appear once
    result = combine([cut(1, 2), cut(1, 3)], [cut(3), cut(2)])
    assert result.count(cut(1, 2, 3)) == 1
    assert result == [cut(1, 2, 3), cut(1, 2), cut(1, 3)]



def test_tiny_cuts():
    sources, ands = read_aag(TINY)
    cuts = enumerate_cuts(sources, ands)
    assert cuts[1] == [cut(1)]
    assert set(cuts[5]) == {cut(5), cut(1, 2)}
    assert set(cuts[7]) == {cut(7), cut(5, 6), cut(1, 2, 6), cut(3, 4, 5), cut(1, 2, 3, 4)}


def test_dominated_cut_removed():
    sources, ands = read_aag(DOMINATED)
    cuts = enumerate_cuts(sources, ands)
    # {a,b,c,x} = {1,2,3,4} is dominated by {c,x} = {3,4}
    assert cut(1, 2, 3, 4) not in cuts[6]
    assert set(cuts[6]) == {cut(6), cut(4, 5), cut(3, 4), cut(1, 2, 5), cut(1, 2, 3)}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
