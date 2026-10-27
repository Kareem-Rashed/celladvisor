"""The "Contained" redundancy test (Option 2 handout, section 5, Table 3).

A candidate is Contained if some HD cell computes it once each of the cell's
pins is connected to one of the candidate's inputs (A, B, C, D) or to 0 or 1.
Several pins may share one input.

Instead of searching backwards from each candidate, we go forwards once:
try every wiring of every HD cell and record which 4-input truth table comes
out. Checking a candidate is then one dictionary lookup.

Conventions:
  * a candidate truth table is a 16-bit int; bit i is the output for row i,
    and input A is bit 0 of the row number, B bit 1, C bit 2, D bit 3;
  * an HD cell is (name, area, pins, truth_table); its truth table has
    2**len(pins) bits and pin j is bit j of the row number (as hdlib does).

Usage:  python3 src/contained.py <HD liberty> <output csv>
"""

import csv
import os
import re
import sys
from itertools import product

N_ROWS = 16  # rows of a 4-input truth table

# What each wiring choice looks like as a 16-bit truth table over A..D.
SOURCES = {
    "A": 0xAAAA,
    "B": 0xCCCC,
    "C": 0xF0F0,
    "D": 0xFF00,
    "0": 0x0000,
    "1": 0xFFFF,
}


def wire(cell_tt, wiring):
    """Truth table (over A..D) of a cell whose pin j is driven by wiring[j].

    For every row of the candidate's truth table, work out which value each
    cell pin sees, assemble those values into a row number of the cell's own
    truth table, and read the cell's output from there.
    """
    sources = [SOURCES[w] for w in wiring]
    tt = 0
    for row in range(N_ROWS):
        cell_row = 0
        for j, src in enumerate(sources):
            cell_row |= ((src >> row) & 1) << j
        tt |= ((cell_tt >> cell_row) & 1) << row
    return tt


def load_hd_cells(lib_path):
    """[(name, area, pins, truth_table)] for every single-output
    combinational cell of a Liberty file, using Mahinour's parser (hdlib)
    for the functions. hdlib skips sequential, tri-state and multi-output
    cells; this adds the area, which the Contained rule needs."""
    from hdlib import _block_end, eval_function, read_cells, support

    text = re.sub(r"/\*.*?\*/", "", open(lib_path).read(), flags=re.S)
    areas = {}
    for m in re.finditer(r'\bcell\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text):
        body = text[m.end() - 1:_block_end(text, m.end() - 1)]
        am = re.search(r"\barea\s*:\s*([0-9.]+)", body)
        if am:
            areas[m.group(1)] = float(am.group(1))

    cells = []
    for name, outs, nonlogic in read_cells(lib_path):
        if nonlogic or len(outs) != 1:
            continue
        expr = outs[0][1]
        pins = support(expr)
        cells.append((name, areas[name], pins, eval_function(expr, pins)))
    return cells


def _cheapest_per_function(cells):
    """Keep one cell per (pin count, truth table): the one with the smallest area.

    Drive strengths (x1, x2, x4...) of one function have the same truth table,
    so this avoids repeating identical work.
    """
    best = {}
    for name, area, pins, cell_tt in cells:
        key = (len(pins), cell_tt)
        if key not in best or area < best[key][1]:
            best[key] = (name, area, list(pins), cell_tt)
    return list(best.values())


def build_contained_table(cells):
    """Return {truth_table: (area, cell_name, wiring)} over all HD cells.

    wiring maps each cell pin to "A", "B", "C", "D", "0" or "1". For every
    truth table we keep the cheapest cell that produces it, because Table 3
    says a Contained candidate is dropped unless it is smaller than that cell.
    """
    table = {}
    for name, area, pins, cell_tt in _cheapest_per_function(cells):
        for wiring in product(SOURCES, repeat=len(pins)):
            tt = wire(cell_tt, wiring)
            current = table.get(tt)
            if current is None or area < current[0]:
                table[tt] = (area, name, dict(zip(pins, wiring)))
    return table


def contained_in(tt, table):
    """None if no HD cell contains tt, else (area, cell_name, wiring)."""
    return table.get(tt)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    table = build_contained_table(load_hd_cells(sys.argv[1]))
    os.makedirs(os.path.dirname(sys.argv[2]) or ".", exist_ok=True)
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tt_hex", "cell", "area_um2", "wiring"])
        for tt in sorted(table):
            area, name, wiring = table[tt]
            w.writerow([f"{tt:04x}", name, area,
                        " ".join(f"{p}={s}" for p, s in wiring.items())])
    print(f"{len(table)} truth tables reachable by tying HD cell pins")
