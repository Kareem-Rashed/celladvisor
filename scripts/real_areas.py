import sys

sys.path.insert(0, "src")
from liberty_writer import cells_from_ranked


import subprocess
from pathlib import Path
import json
import csv

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / "build" / "cwvenv" / "bin" / "python"
PDK = Path.home() / ".ciel" / "sky130A"
OUT = ROOT / "build" / "cw_pool"

SITE = 0.46

def generate(name, expression):
    out_dir = OUT / name
    cmd = [str(PY), "-m", "scl_gen.cli", "--function", expression,
           "--name", name, "--output", str(out_dir), "--pdk", str(PDK)]
    result = subprocess.run(cmd, cwd=ROOT / "cellweaver",
                            capture_output=True, text=True)
    return result, out_dir


def read_report(out_dir):
    report = json.loads((out_dir / "report.json").read_text())
    width = report["width_um"]
    height = report["height_um"]
    sites = round(width / SITE)
    assert abs(width / SITE - sites) < 0.01, "width is not a whole number of sites"
    return {
        "width_um": width,
        "height_um": height,
        "sites": sites,
        "area_um2": round(width * height, 4),
        "transistors": report["transistor_count"],
        "backend": report.get("layout_backend", ""),
    }

cells = cells_from_ranked("results/ranked.csv", 30, "b3")

rows = []
for name, expression, estimated in cells:
    result, out_dir = generate(name, expression)
    if result.returncode != 0:
        print(f"FAILED {name}: {result.stdout[-200:]} {result.stderr[-200:]}")
        continue
    info = read_report(out_dir)
    row = {"name": name, "expression": expression,
           "estimated_area_um2": estimated, **info}
    rows.append(row)
    print(f"{name}  {info['sites']} sites  {info['area_um2']} um2  "
          f"(estimated {estimated})  {info['backend']}")

print(len(rows), "of", len(cells), "cells generated")

FIELDS = ["name", "expression", "estimated_area_um2", "width_um", "height_um",
          "sites", "area_um2", "transistors", "backend"]
with open(ROOT / "results" / "real_areas.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print("wrote results/real_areas.csv")