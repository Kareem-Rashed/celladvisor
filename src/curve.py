"""
if we add the final cells one at a time, in the order the greedy selection chose them, how much does the total area drop after each one?

For each step k = 0, 1, 2, ... we
  1. build a Liberty file = hd_reduced.lib + the first k chosen cells,
  2. map all six required designs with BOTH script A and script B,
  3. for every design keep the smaller of the two areas ("best of both"),
  4. add the six numbers up: that is the total for step k.

Step 0 has no new cells, so it is the baseline. The curve is steps 0..N.

Usage
    python3 src/curve.py estimated # libs/final_estimated.csv, estimated areas
    python3 src/curve.py real # libs/final_real.csv, real areas
    python3 src/curve.py estimated_real # the estimated final set, but with the real areas from results/real_areas.csv
"""

import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "src")
from greedy import BASE_LIB, WORKERS, count_cells
from liberty_writer import write_library
from table5 import DESIGNS, SCRIPTS, design_file, map_design


def read_cells(path):
    """
    Read a cells CSV (name, expression, area_um2) in the order it is written.

    That order IS the order the greedy chose them, so we must not sort it.
    """
    with open(path) as f:
        return [(row["name"], row["expression"], float(row["area_um2"])) for row in csv.DictReader(f)]


def read_real_area_lookup(path = "results/real_areas.csv"):
    """
    {cell name: real area in um2} from the cell generator's output
    """
    with open(path) as f:
        return {row["name"]: float(row["area_um2"]) for row in csv.DictReader(f)}


def load_chosen_cells(mode):
    """
    The final cells for this mode, in greedy order
    """
    if mode == "estimated":
        return read_cells("libs/final_estimated.csv")
    
    if mode == "real":
        return read_cells("libs/final_real.csv")
    
    if mode == "estimated_real":
        # Same cells and same order as the estimated run, real areas swapped in.
        real_area = read_real_area_lookup()
        return [(name, expression, real_area[name])
                for name, expression, _ in read_cells("libs/final_estimated.csv")]
    
    sys.exit(f"unknown mode '{mode}': use estimated, real or estimated_real")



def measure_step(cells, mode, step):
    """
    Map every design with these cells and both scripts A and B

    Returns:
      (total, per_design, cell_uses): per_design is a list of (design, area_A, area_B, best_area),
                                    total is the sum of the best areas,
                                    cell_uses counts how often each new cell appears in the netlists.
    """
    work = f"build/curve/{mode}_step{step}"
    os.makedirs(work, exist_ok=True)

    # Step 0 uses the plain reduced library
    lib = BASE_LIB
    if cells:
        lib = f"{work}/lib.lib"
        write_library(BASE_LIB, cells, lib)

    per_design = []
    cell_uses = {}
    for design, top in DESIGNS:
        areas = {}
        for script in SCRIPTS: # "A" and "B"
            netlist = f"{work}/{design}_{script}.v"
            verilog = design_file(design)

            areas[script] = map_design(verilog, top, lib,
                                       script, netlist,
                                       f"{work}/{design}_{script}.stat")
            
            for cell, n in count_cells(netlist).items():
                cell_uses[cell] = cell_uses.get(cell, 0) + n

        best = min(areas.values()) # best of both scripts

        per_design.append((design, areas["A"], areas["B"], best))

    total = sum(best for _, _, _, best in per_design)
    return total, per_design, cell_uses



def write_curve_csv(path, rows, designs):
    header = ["step", "cell_added", "total_best_um2", "change_vs_previous_um2",
              "change_vs_baseline_um2", "saving_vs_baseline_pct"]
    
    header += [f"{d}_best_um2" for d in designs]
    header += ["total_script_A_um2", "total_script_B_um2"]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def plot_curve(path, labels, totals, title, totals_b=None):
    """
    Total best-of-both area after each added cell, and (dashed) the script B
    total, the number the greedy selection optimizes
    """
    try:
        import matplotlib
        matplotlib.use("Agg") # no window needed
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: try (pip install matplotlib)")
        return

    steps = list(range(len(totals)))
    baseline = totals[0]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.axhline(baseline, color="grey", linestyle="--", linewidth=1,
               label="baseline (no new cells)")
    ax.plot(steps, totals, marker="o", linewidth=2, label="best of A and B (with new cells)")
    if totals_b is not None:
        ax.plot(steps, totals_b, marker="s", linewidth=1.5, linestyle="--",
                color="tab:orange", label="script B only (what greedy optimizes)")

    # Write the change next to every point: this shows which cell did the work.
    for i in range(1, len(totals)):
        change = totals[i] - totals[i - 1]
        ax.annotate(f"{change:+.1f}", (i, totals[i]), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=9)

    ax.set_xticks(steps)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("total area of the 8 designs (um$^2$)")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def build_curve(mode):
    chosen = load_chosen_cells(mode)

    if not chosen:
        print(f"libs/final_{mode}.csv has no cells: the curve is only the baseline.")

    # Step k uses the first k chosen cells
    #  Steps are independent, so they can be run in parallel (each step is 12 Yosys runs)

    steps = range(len(chosen) + 1)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        jobs = [pool.submit(measure_step, chosen[:k], mode, k) for k in steps]
        results = [job.result() for job in jobs]

    designs = [d for d, _ in DESIGNS]

    rows, labels, totals, totals_b = [], [], [], []
    for k, (total, per_design, cell_uses) in enumerate(results):
        name = "(baseline)" if k == 0 else chosen[k - 1][0]

        previous = totals[-1] if totals else total
        baseline = totals[0] if totals else total

        rows.append([k, name, round(total, 4), round(total - previous, 4),
                     round(total - baseline, 4),
                     round((baseline - total) / baseline * 100, 3)]
                    + [round(best, 4) for _, _, _, best in per_design]
                    + [round(sum(a for _, a, _, _ in per_design), 4),
                       round(sum(b for _, _, b, _ in per_design), 4)])

        labels.append("baseline" if k == 0 else name.replace("dd2_gb3__", ""))
        totals.append(total)
        totals_b.append(sum(b for _, _, b, _ in per_design))
        print(f"step {k}  {name:20} total {total:11.4f}  "
              f"change {total - previous:+9.4f}  uses {cell_uses}")

    os.makedirs("results", exist_ok=True)
    write_curve_csv(f"results/curve_{mode}.csv", rows, designs)
    plot_curve(f"results/curve_{mode}.png", labels, totals,
               f"Cell-by-cell curve ({mode} areas)", totals_b)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build_curve(sys.argv[1])