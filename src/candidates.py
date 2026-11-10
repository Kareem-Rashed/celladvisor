import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aig_reader import read_aag
from cutter import enumerate_cuts
from cuts import cut_truth_table
from canon import canon_p, canon_pn, canon_npn, used_inputs
from redundancy import Redundancy
from areamodel import estimate_area

DESIGNS = ["cpu8", "dsp8", "arlet6502", "uart_apb", "risc8", "fir10", "spm", "mul"]
GRAPHS = ["strash", "abc"]
HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")

HEADER = (["graph", "class", "pn_class", "n_inputs", "total"] + DESIGNS
          + ["label", "hd_cell", "hd_cost", "estimated_area", "decision"])
COL = {name: i for i, name in enumerate(HEADER)}

class_of = {}


def get_class(tt):
    if tt not in class_of:
        class_of[tt] = canon_p(tt)
    return class_of[tt]


def classes_in(path):
    sources, ands = read_aag(open(path).read())
    cuts = enumerate_cuts(sources, ands)
    counts = Counter()
    for g in ands:
        for cut in cuts[g]:
            if len(cut) < 2:
                continue
            leaves = sorted(cut)
            tt = cut_truth_table(ands, g, leaves)
            counts[get_class(tt)] += 1
    return len(ands), counts


def inverter_area(red):
    area, _ = red.by_class[canon_p(0x5555)]
    return area


def hd_cost(label, area, inv_area):
    if label == "Exists with inverter":
        return area + inv_area
    return area


def estimated_area(cls):
    return estimate_area(cls)


def decide(label, cost, new_area):
    # ======================================================================
    # TABLE 3 DECISION (Option 2 handout, section 5)
    #
    #   Exists                -> drop
    #   Exists with inverter  -> keep only if new_area < HD cell + inverter
    #   Contained             -> keep only if new_area < HD cell
    #   New                   -> keep
    #
    # cost is already "HD cell + inverter" for the inverter case and
    # "HD cell" for the Contained case (see hd_cost), so both use the same
    # comparison. When estimated_area() returns a number, these rows turn
    # into "keep" or "drop" with no other change.
    # ======================================================================
    if label == "Exists":
        return "drop"
    if label == "New":
        return "keep"
    if new_area is None:
        return "pending"
    if new_area < cost:
        return "keep"
    return "drop"


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def main():
    red = Redundancy(HD_LIB)
    inv_area = inverter_area(red)
    os.makedirs("results", exist_ok=True)

    summary = []
    per_class = {}

    for graph in GRAPHS:
        for design in DESIGNS:
            path = f"build/aig/{design}_{graph}.aag"
            ands, counts = classes_in(path)
            n_cuts = sum(counts.values())

            p_classes = len(counts)
            pn_classes = len({canon_pn(c) for c in counts})
            npn_classes = len({canon_npn(c) for c in counts})
            
            summary.append([design, graph, ands, n_cuts, p_classes, pn_classes, npn_classes])

            print(f"{design:10} {graph:6} cuts {n_cuts:6}  "
                  f"P classes {p_classes:4}  PN classes {pn_classes:4}  NPN classes {npn_classes:4}")
            for cls, n in counts.items():
                per_class.setdefault((graph, cls), Counter())[design] = n

    with open("results/class_counts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "graph", "ands", "cuts_2_to_4",
                    "p_classes", "pn_classes", "npn_classes"])
        w.writerows(summary)

    rows = []
    for (graph, cls), by_design in per_class.items():
        label, cell, area = red.classify_full(cls)
        cost = hd_cost(label, area, inv_area) if area is not None else None
        new_area = estimated_area(cls)
        rows.append([graph, f"{cls:04x}", f"{canon_pn(cls):04x}",
                     len(used_inputs(cls)), sum(by_design.values())]
                    + [by_design[d] for d in DESIGNS]
                    + [label, cell or "",
                       "" if cost is None else round(cost, 4),
                       "" if new_area is None else round(new_area, 4),
                       decide(label, cost, new_area)])
    rows.sort(key=lambda r: (r[COL["graph"]], -r[COL["total"]]))

    write_csv("results/candidates.csv", rows)
    write_csv("results/candidates_kept.csv",
              [r for r in rows if r[COL["decision"]] == "keep"])

    for graph in GRAPHS:
        mine = [r for r in rows if r[COL["graph"]] == graph]
        print(graph, "labels:", dict(Counter(r[COL["label"]] for r in mine)))
        print(graph, "decisions:", dict(Counter(r[COL["decision"]] for r in mine)))


if __name__ == "__main__":
    main()