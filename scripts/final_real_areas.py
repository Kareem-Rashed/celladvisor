"""The final cells (libs/final_estimated.csv) with their real areas instead of
the estimated ones, taken from results/real_areas.csv (column area_um2).

Usage: python3 scripts/final_real_areas.py libs/final_estimated.csv results/real_areas.csv libs/final_real.csv
"""

import csv
import sys


def main(final_csv, real_csv, out_csv):
    # The real area of every cell that has one.
    real_area = {}
    with open(real_csv) as f:
        for row in csv.DictReader(f):
            real_area[row["name"]] = row["area_um2"]

    rows = []
    with open(final_csv) as f:
        for row in csv.DictReader(f):
            name = row["name"]
            if name not in real_area:
                raise ValueError(name + " has no real area in " + real_csv)
            rows.append([name, row["expression"], real_area[name]])

    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["name", "expression", "area_um2"])
        for row in rows:
            writer.writerow(row)
    print(str(len(rows)) + " cells with real areas -> " + out_csv)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
