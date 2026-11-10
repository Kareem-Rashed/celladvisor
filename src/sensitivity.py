"""Step 12 of the Option 2 handout: the 30% experiment.

ABC only sees the numbers in the Liberty file. If we make one new cell 30%
smaller in the Liberty file, change nothing else, and map the designs again,
we see how much our result depends on the area we estimated.

What we agreed:
  - the cells: the final set chosen by the greedy (libs/final_estimated.csv)
  - the cell we shrink: the first cell the greedy chose
  - how we measure: like the greedy, the total area of all the designs with
    script B, so the numbers can be compared with the greedy's result

Output: results/sensitivity.csv, one row per design plus a total row.

Usage: python3 src/sensitivity.py
"""

import csv
import os
import sys

sys.path.insert(0, "src")
from greedy import count_cells
from table5 import DESIGNS, design_file, map_design
from liberty_writer import write_library

FINAL_CELLS = "libs/final_estimated.csv"
BASE_LIB = "given/hd_reduced.lib"
FACTOR = 0.7
SCRIPT = "B"


def read_cells(path):
    """Read the final cells. Each cell is (name, expression, area)."""
    cells = []
    with open(path) as f:
        for row in csv.DictReader(f):
            cell = (row["name"], row["expression"], float(row["area_um2"]))
            cells.append(cell)
    return cells


def shrink(cells, name_to_shrink, factor):
    """Return a copy of the cells where only one cell's area is multiplied
    by factor. Every other cell stays exactly the same."""
    found = False
    new_cells = []
    for name, expression, area in cells:
        if name == name_to_shrink:
            area = round(area * factor, 4)
            found = True
        new_cells.append((name, expression, area))

    if not found:
        raise ValueError(name_to_shrink + " is not in the final set")
    return new_cells


def map_all_designs(cells, folder_name):
    """Build a library with these cells, map every design with script B, and
    return two dictionaries: the area of each design, and how many times
    each new cell was used in each design."""
    work = "build/sensitivity/" + folder_name
    os.makedirs(work, exist_ok=True)

    lib = work + "/lib.lib"
    write_library(BASE_LIB, cells, lib)

    areas = {}
    cells_used = {}
    for design, top in DESIGNS:
        verilog = design_file(design)   # given/designs/ or designs/ (SPM, mul)
        netlist = work + "/" + design + ".v"
        stat_file = work + "/" + design + ".stat"

        area = map_design(verilog, top, lib, SCRIPT, netlist, stat_file)
        areas[design] = area
        cells_used[design] = count_cells(netlist)
    return areas, cells_used


def main():
    cells = read_cells(FINAL_CELLS)

    # The cell to shrink is the first cell the greedy chose.
    first_cell = cells[0]
    name = first_cell[0]
    old_area = first_cell[2]
    new_area = round(old_area * FACTOR, 4)
    print(name + ": area " + str(old_area) + " -> " + str(new_area) + " um2")

    small_cells = shrink(cells, name, FACTOR)

    # Map everything twice: with the normal areas and with the shrunk cell.
    areas_before, used_before = map_all_designs(cells, "estimated")
    areas_after, used_after = map_all_designs(small_cells, "shrunk")

    rows = []
    total_before = 0.0
    total_after = 0.0
    count_before = 0
    count_after = 0

    for design, top in DESIGNS:
        area_before = areas_before[design]
        area_after = areas_after[design]
        change = area_after - area_before

        # How many times the shrunk cell was used in this design.
        n_before = used_before[design][name]
        n_after = used_after[design][name]

        rows.append([design, round(area_before, 4), round(area_after, 4),
                     round(change, 4), n_before, n_after])
        print(design, round(area_before, 2), "->", round(area_after, 2),
              "| used", n_before, "->", n_after)

        total_before = total_before + area_before
        total_after = total_after + area_after
        count_before = count_before + n_before
        count_after = count_after + n_after

    total_change = total_after - total_before
    rows.append(["total", round(total_before, 4), round(total_after, 4),
                 round(total_change, 4), count_before, count_after])
    print("total", round(total_before, 2), "->", round(total_after, 2),
          "| used", count_before, "->", count_after)

    with open("results/sensitivity.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["design", "area_um2", "area_shrunk_um2", "change_um2",
                         "instances", "instances_shrunk"])
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
