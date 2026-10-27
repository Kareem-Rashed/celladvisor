import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aig_reader import read_aag




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


def test_read_tiny():
    sources, ands = read_aag(TINY)
    assert sources == [1, 2, 3, 4]
    assert ands == {5: (2, 4), 6: (6, 9), 7: (11, 13)}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
