

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "dd2-cellweaver"
PDK = Path.home() / ".ciel" / "sky130A"
OUT = ROOT / "build" / "cw_check"
CHECKS = ["geometry", "drc", "lvs", "abutment", "simulation"]


def read_cells(path):
    with open(path) as f:
        return [(r["name"], r["expression"]) for r in csv.DictReader(f)]


def run_in_container(name, expression):
    cmd = ["docker", "run", "--rm", "-e", "PYTHONDONTWRITEBYTECODE=1",
           "-v", f"{ROOT}:/work", "-v", f"{PDK}:/pdk/sky130A:ro",
           "-w", "/work/cellweaver", IMAGE,
           "/opt/cwvenv/bin/python", "-m", "scl_gen.cli",
           "--function", expression, "--name", name,
           "--output", f"/work/build/cw_check/{name}", "--pdk", "/pdk/sky130A",
           "--verify", "--simulate"]
    return subprocess.run(cmd, capture_output=True, text=True)


def verdict(name):
    report = OUT / name / "report.json"
    if not report.exists():
        return ["no_report"] * len(CHECKS)
    checks = json.loads(report.read_text())["checks"]
    return [checks.get(c, {}).get("status", "not_run") for c in CHECKS]


def main(cells_csv, out_csv):
    rows = []
    for name, expression in read_cells(cells_csv):
        result = run_in_container(name, expression)
        status = verdict(name)
        overall = "pass" if all(s == "pass" for s in status) else "fail"
        rows.append([name, *status, overall, result.returncode])
        print(name, *status, overall)
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["cell", *CHECKS, "overall", "exit_code"])
        w.writerows(rows)
    print("wrote", out_csv)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python3 scripts/check_cells.py <cells.csv> <out.csv>")
    main(sys.argv[1], sys.argv[2])
