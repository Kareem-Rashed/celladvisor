import csv
import os
import subprocess

from areamodel import estimate_area

LIB = "given/hd_reduced.lib"
MAP = "given/scripts/map.sh"
STAND_IN = 7 * 0.46 * 2.72


def verilog_for(tt):
    return f"""module f(input A, input B, input C, input D, output Y);
  wire [15:0] T = 16'h{tt:04x};
  assign Y = T[{{D, C, B, A}}];
endmodule
"""


def map_area(verilog_path, script):
    result = subprocess.run(
        ["sh", MAP, verilog_path, "f", LIB, script],
        capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if "Chip area" in line:
            return float(line.split(":")[-1])
    return None


def hd_area(tt):
    os.makedirs("build/rank", exist_ok=True)
    path = f"build/rank/f_{tt:04x}.v"
    with open(path, "w") as f:
        f.write(verilog_for(tt))
    areas = [map_area(path, "A"), map_area(path, "B")]
    areas = [a for a in areas if a is not None]
    return min(areas) if areas else None


def top_candidates(n=None): #takes all not 30
    rows = []
    with open("results/candidates_kept.csv") as f:
        for row in csv.DictReader(f):
            if row["graph"] == "abc":
                rows.append(row)
    rows.sort(key=lambda r: int(r["total"]), reverse=True)
    return rows[:n]


def new_cell_area(tt):
    return estimate_area(tt), "model"


def saving(row):
    tt = int(row["class"], 16)
    count = int(row["total"])
    now = hd_area(tt)
    new, source = new_cell_area(tt)

    if now is None or new is None: #fallback in case area was not found
        return None
    
    each = now - new
    return now, new, source, each, count * each


def main():
    ranked = []
    for row in top_candidates():
        result = saving(row)
        if result is None:
            print("skipped", row["class"], "(no area)")
            continue
        now, new, source, each, total = result
        ranked.append([row["class"], row["total"], round(now, 4), round(new, 4),
                       source, round(each, 4), round(total, 1)])
        print(row["class"], row["total"], "HD now", round(now, 2),
              "new", round(new, 2), "saving", round(total, 1))

    ranked.sort(key=lambda r: r[-1], reverse=True)
    with open("results/ranked.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["class", "count", "hd_area_now", "new_area", "new_area_source",
                    "saving_each", "saving_total"])
        w.writerows(ranked)


if __name__ == "__main__":
    main()