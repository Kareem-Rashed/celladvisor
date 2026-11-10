import csv
import os
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "src")
from table5 import DESIGNS, design_file, map_design
from liberty_writer import write_library, cells_from_ranked

BASE_LIB = "given/hd_reduced.lib"
MAX_CELLS = 10
WORKERS = 4

# table5.DESIGNS: the six required designs plus the SPM of Tutorial 4 and the
# multiplier of Tutorial 2 (handout, section 3).
# Each entry: (Verilog file, top module, short name).
DESIGN_FILES = [(design_file(d), top, d) for d, top in DESIGNS]


def count_cells(netlist):
    pattern = re.compile(r"^\s*\\?(dd2_\S+)\s+\S+\s*\(", re.M)
    return Counter(pattern.findall(open(netlist).read()))


def total_area(cells, tag, scripts="B"):
    work = f"build/greedy/{tag}"
    os.makedirs(work, exist_ok=True)
    lib = BASE_LIB
    if cells:
        lib = f"{work}/lib.lib"
        write_library(BASE_LIB, cells, lib)
    total = 0.0
    used = Counter()
    for verilog, top, design in DESIGN_FILES:
        areas = []
        for script in scripts:
            area = map_design(verilog, top, lib, script,
                              f"{work}/{design}_{script}.v",
                              f"{work}/{design}_{script}.stat")
            areas.append(area)
            used += count_cells(f"{work}/{design}_{script}.v")
        total += min(areas)
    return total, used


def read_pool(mode):
    if mode == "estimated":
        return cells_from_ranked("results/ranked.csv", None, "b3")
    with open("results/real_areas.csv") as f:
        return [(r["name"], r["expression"], float(r["area_um2"]))
                for r in csv.DictReader(f)]
    

def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def greedy(mode):
    remaining = read_pool(mode)
    chosen = []
    current, _ = total_area([], f"{mode}_baseline")
    print("baseline (script B)", round(current, 4))
    baseline = current
    steps = [[0, "(baseline)", 0, round(current, 4), 0.0]]
    trials = []
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for rnd in range(1, MAX_CELLS + 1):
            jobs = [(cell, pool.submit(total_area, chosen + [cell],
                                       f"{mode}_r{rnd}_{cell[0]}"))
                    for cell in remaining]
            best_total, best_cell, best_used = None, None, None
            for cell, job in jobs:
                total, used = job.result()
                dead = [c[0] for c in chosen + [cell] if used[c[0]] == 0]
                print(rnd, cell[0], round(total - current, 4), "unused:", len(dead))
                trials.append([rnd, cell[0], round(total - current, 4), len(dead)])
                if dead:
                    continue
                if best_total is None or total < best_total:
                    best_total, best_cell, best_used = total, cell, used
            if best_total is None or best_total >= current:
                print("no candidate passes: stop")
                break
            chosen.append(best_cell)
            remaining.remove(best_cell)
            current = best_total
            steps.append([rnd, best_cell[0], best_used[best_cell[0]],
                          round(current, 4), round(current - baseline, 4)])
            print("added", best_cell[0], "total", round(current, 4))
    write_csv(f"results/greedy_{mode}.csv",
              ["step", "cell_added", "instances", "total_script_B_um2",
               "change_vs_baseline_um2"], steps)
    write_csv(f"results/greedy_{mode}_trials.csv",
              ["round", "candidate", "change_um2", "unused_cells"], trials)
    write_csv(f"libs/final_{mode}.csv", ["name", "expression", "area_um2"], chosen)
    return chosen, current


if __name__ == "__main__":
    greedy(sys.argv[1])
