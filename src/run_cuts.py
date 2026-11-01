import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aig_reader import read_aag
from cutter import enumerate_cuts

DESIGNS = ["cpu8", "dsp8", "arlet6502", "uart_apb", "risc8", "fir10"]
GRAPHS = ["strash", "abc"]


def count_cuts(path):
    sources, ands = read_aag(open(path).read())
    cuts = enumerate_cuts(sources, ands)
    by_size = [0, 0, 0, 0, 0]
    for g in ands:
        for cut in cuts[g]:
            by_size[len(cut)] += 1
    return len(ands), by_size


def main():
    os.makedirs("results", exist_ok=True)
    rows = []
    for design in DESIGNS:
        for graph in GRAPHS:
            path = f"build/aig/{design}_{graph}.aag"
            start = time.time()
            ands, by_size = count_cuts(path)
            seconds = round(time.time() - start, 1)
            total = sum(by_size)
            rows.append([design, graph, ands, total, by_size[1], by_size[2],
                         by_size[3], by_size[4], seconds])
            print(f"{design:10} {graph:6} ands {ands:5}  cuts {total:7}  "
                  f"(1/2/3/4 leaves: {by_size[1]}/{by_size[2]}/{by_size[3]}/{by_size[4]})  "
                  f"{seconds}s")

    with open("results/cut_counts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "graph", "ands", "cuts", "cuts_1", "cuts_2",
                    "cuts_3", "cuts_4", "seconds"])
        w.writerows(rows)


if __name__ == "__main__":
    main()