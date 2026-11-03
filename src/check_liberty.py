"""Check that Yosys accepts a Liberty file (Option 2 handout, section 6).

Two reads, because they catch different mistakes:
  1. read_liberty -lib  must print "Imported N cell types" with N as expected
     (189 for hd_reduced.lib plus the number of new cells);
  2. read_liberty       (without -lib) parses every function attribute.
     -lib alone accepts a function that names a pin the cell does not have,
     or that is not a valid expression; ABC would then map with a wrong cell.

Usage: python3 src/check_liberty.py <lib> [expected_cell_count]
Exit status 0 if both reads pass, 1 otherwise.
"""

import re
import subprocess
import sys


def yosys(command):
    result = subprocess.run(["yosys", "-p", command],
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def check_liberty(path, expected=None):
    """(ok, message)."""
    code, log = yosys(f"read_liberty -lib {path}")
    if code != 0:
        return False, f"read_liberty -lib rejected {path}: " + _error(log)
    m = re.search(r"Imported (\d+) cell types", log)
    if not m:
        return False, f"read_liberty -lib printed no cell count for {path}"
    count = int(m.group(1))
    if expected is not None and count != expected:
        return False, f"{path}: imported {count} cell types, expected {expected}"
    code, log = yosys(f"read_liberty {path}")
    if code != 0:
        return False, f"read_liberty rejected a function in {path}: " + _error(log)
    return True, f"{path}: imported {count} cell types, every function parses"


def _error(log):
    lines = [l for l in log.splitlines() if "ERROR" in l]
    return lines[0].strip() if lines else "no error message"


if __name__ == "__main__":
    expected = int(sys.argv[2]) if len(sys.argv) > 2 else None
    ok, message = check_liberty(sys.argv[1], expected)
    print(message)
    sys.exit(0 if ok else 1)
