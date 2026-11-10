"""Worst path delay of mapped netlists, from OpenSTA (Option 2 handout, section 7).

Runs `sta` inside the dd2-cellweaver container (make docker-images) on every
netlist of a folder written by table5.py, whose names are
<design>_<baseline|extended>_<A|B>.v, and writes one row per netlist.

  python3 scripts/sta_delay.py                               # every netlist of results/mapped/
  python3 scripts/sta_delay.py --only cpu8_baseline_A        # one netlist, to test
  python3 scripts/sta_delay.py --dir results/mapped --extended-lib libs/hd_extended.lib --out results/delays.csv

The delay is the data arrival time of the worst setup path (scripts/sta_delay.tcl).
The new cells' timing in our Liberty is a placeholder (handout, section 6), so a
path through a new cell has a delay that is not real; HD's own cells have real tables.

Run from the repository root.
"""

import argparse
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
from table5 import DESIGNS

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "dd2-cellweaver"
NAME = re.compile(r"^(?P<design>\w+?)_(?P<lib>baseline|extended)_(?P<script>[AB])\.v$")
ARRIVAL = re.compile(r"^\s*(-?\d+\.\d+)\s+data arrival time", re.M)
TOP = dict(DESIGNS)


def container_path(path, mounts):
    """Path of a file inside the container. The repository is mounted at /work;
    a file outside it (given/ is a symlink to the student pack) has its real
    folder mounted read-only at /ext."""
    real = Path(path).resolve()
    try:
        return str(Path("/work") / real.relative_to(ROOT))
    except ValueError:
        mounts.append(f"{real.parent}:/ext:ro")
        return f"/ext/{real.name}"


def run_sta(netlist, top, lib, use_docker):
    if use_docker:
        mounts = []
        env = {"STA_NETLIST": container_path(netlist, mounts), "STA_TOP": top,
               "STA_LIB": container_path(lib, mounts)}
        cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/work", "-w", "/work"]
        for mount in dict.fromkeys(mounts):
            cmd += ["-v", mount]
        for key, value in env.items():
            cmd += ["-e", f"{key}={value}"]
        cmd += [IMAGE, "sta", "-no_splash", "-exit", "scripts/sta_delay.tcl"]
        result = subprocess.run(cmd, capture_output=True, text=True)
    else:
        env = {"STA_NETLIST": netlist, "STA_TOP": top, "STA_LIB": lib}
        result = subprocess.run(["sta", "-no_splash", "-exit", "scripts/sta_delay.tcl"],
                                capture_output=True, text=True, env={**os.environ, **env})
    # report_checks prints one path per path group; the worst delay is the largest arrival
    arrivals = [float(x) for x in ARRIVAL.findall(result.stdout)]
    return (max(arrivals) if arrivals else None), result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="results/mapped")
    ap.add_argument("--baseline-lib", default="given/hd_reduced.lib")
    ap.add_argument("--extended-lib", default="libs/hd_extended.lib")
    ap.add_argument("--out", default="results/delays.csv")
    ap.add_argument("--only", help="one netlist name without .v, e.g. cpu8_baseline_A")
    ap.add_argument("--no-docker", action="store_true", help="use sta from the PATH")
    args = ap.parse_args()

    rows = []
    for path in sorted(Path(args.dir).glob("*.v")):
        m = NAME.match(path.name)
        if not m or (args.only and path.stem != args.only):
            continue
        design, kind, script = m["design"], m["lib"], m["script"]
        if design not in TOP:
            continue
        lib = args.baseline_lib if kind == "baseline" else args.extended_lib
        delay, result = run_sta(str(path), TOP[design], lib, not args.no_docker)
        if delay is None:
            print(f"{path.stem}: no delay found; last lines:\n{result.stdout[-400:]}{result.stderr[-400:]}")
        else:
            print(f"{path.stem:28} worst delay {delay:8.4f} ns")
        rows.append([path.stem, design, kind, script, "" if delay is None else delay])

    if not args.only:
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["netlist", "design", "library", "script", "worst_delay_ns"])
            w.writerows(rows)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
