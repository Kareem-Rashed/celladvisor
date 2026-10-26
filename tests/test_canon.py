import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from canon import canon_p, canon_pn, permute, used_inputs


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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)