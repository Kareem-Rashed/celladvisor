import csv
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, "src")
from aig_reader import read_aag
from candidates import classes_in, HD_LIB
from canon import canon_pn
from liberty_writer import read_cells, write_library
from redundancy import Redundancy
from table5 import map_design, reference, cec, new_cell_instances

BASELINE = "given/hd_reduced.lib"
FINAL = {"estimated": "libs/final_estimated.csv", "real": "libs/final_real.csv"}
SCRIPTS = ["A", "B"]
START = time.time()


def say(text=""):
    print(text, flush=True)


def step(title):
    say(f"\n[{time.time() - START:5.0f}s] {title}")


def yosys(script):
    r = subprocess.run(["yosys", "-q", "-p", script], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("yosys failed:\n" + (r.stdout + r.stderr)[-1500:])


def abc(script):
    subprocess.run(["yosys-abc", "-c", script], capture_output=True, text=True)


def find_top(src, flag):
    r = subprocess.run(["yosys", "-p", f"read_verilog {flag}{src}; hierarchy -auto-top"],
                       capture_output=True, text=True)
    m = re.search(r"Automatically selected (\S+) as design top module", r.stdout)
    if not m:
        sys.exit("cannot find the top module: give it, e.g. make demo IN=file.v TOP=<module>")
    return m.group(1).lstrip("\\")


def write_aigs(src, top, flag, work):
    """raw, strash and ABC-restructured AIGs, as in scripts/aigs.sh."""
    raw = f"{work}/raw"
    yosys(f"read_verilog {flag}{src}; synth -flatten -top {top}; async2sync; dffunmap; "
          f"aigmap; write_aiger -ascii {raw}.aag; write_aiger {raw}.aig")
    abc(f"read_aiger {raw}.aig; strash; write_aiger {work}/strash.aig")
    abc(f"read_aiger {raw}.aig; strash; dch; strash; write_aiger {work}/abc.aig")
    for graph in ("strash", "abc"):
        yosys(f"read_aiger {work}/{graph}.aig; simplemap; write_aiger -ascii {work}/{graph}.aag")
    sizes = {}
    for graph in ("raw", "strash", "abc"):
        header = open(f"{work}/{graph}.aag").readline().split()
        sizes[graph] = (int(header[2]), int(header[3]), int(header[5]))  # inputs, latches, ANDs
    return sizes


def final_classes(path):
    """class (int) of every cell of a final-set CSV, from its name dd2_g..__c<class>_1."""
    return {int(re.search(r"__c([0-9a-f]{4})_", name).group(1), 16): name
            for name, _, _ in read_cells(path)}


def libraries(work):
    """baseline, and the baseline plus the final cells with estimated and with real areas."""
    libs = {"baseline": BASELINE}
    for kind, csv_path in FINAL.items():
        if not os.path.exists(csv_path):
            say(f"  (no {csv_path}: skipping the {kind} library)")
            continue
        lib = f"{work}/hd_{kind}.lib"
        write_library(BASELINE, read_cells(csv_path), lib)
        libs[kind] = lib
    return libs


def main(src, top=None, sv=False):
    if not os.path.exists(src):
        sys.exit(f"{src}: no such file")
    flag = "-sv " if sv or src.endswith(".sv") else ""
    name = Path(src).stem
    work = f"build/demo/{name}"
    os.makedirs(work, exist_ok=True)

    say(f"celladvisor demo on {src}")
    top = top or find_top(src, flag)
    say(f"top module: {top}")

    step("1. AIG (raw, strash, after ABC)")
    sizes = write_aigs(src, top, flag, work)
    for graph, (inputs, latches, ands) in sizes.items():
        say(f"  {graph:7} inputs {inputs:5}  flip-flops {latches:5}  AND nodes {ands:6}")

    step("2. cuts of up to 4 inputs and their classes (ABC graph)")
    ands, counts = classes_in(f"{work}/abc.aag")
    pn = len({canon_pn(c) for c in counts})
    say(f"  {sum(counts.values())} cuts of 2 to 4 inputs, {len(counts)} classes up to input "
        f"order (P), {pn} up to input order and output inversion (PN)")

    step("3. redundancy against the full HD library (Table 3)")
    red = Redundancy(HD_LIB)
    labels = Counter()
    by_label = {}
    for cls, n in counts.items():
        label, cell, _ = red.classify_full(cls)
        labels[label] += 1
        by_label.setdefault(label, []).append((n, cls, cell))
    for label in ("Exists", "Exists with inverter", "Contained", "New"):
        say(f"  {label:22} {labels[label]:5} classes")
    say("  most frequent classes HD does not have (New):")
    for n, cls, _ in sorted(by_label.get("New", []), reverse=True)[:5]:
        say(f"    class {cls:04x}  {n:6} cuts")
    ours = final_classes(FINAL["estimated"]) if os.path.exists(FINAL["estimated"]) else {}
    present = [(counts[c], c, nm) for c, nm in ours.items() if c in counts]
    say("  classes of the final cells that occur in this design:")
    for n, cls, nm in sorted(present, reverse=True) or []:
        say(f"    {nm.split('__')[1]:10} class {cls:04x}  {n:6} cuts")
    if not present:
        say("    none")

    step("4. mapping with the baseline and with the final cells, scripts A and B")
    libs = libraries(work)
    verilog = flag + src            # map_design and reference put this after read_verilog
    rows = []
    for kind, lib in libs.items():
        ref_v = f"{work}/{kind}_ref.v"
        reference(verilog, top, lib, ref_v)
        for script in SCRIPTS:
            out_v = f"{work}/{kind}_{script}.v"
            area = map_design(verilog, top, lib, script, out_v, f"{work}/{kind}_{script}.stat")
            used = new_cell_instances(out_v)
            ok, _ = cec(ref_v, out_v, top, lib, f"{work}/{kind}_{script}")
            rows.append([kind, script, area, used, "pass" if ok else "FAIL"])
            say(f"  {kind:10} script {script}  area {area:11.2f} um2  new cells {used:5}  "
                f"cec {'pass' if ok else 'FAIL'}")

    step("5. result")
    best = {k: min(r[2] for r in rows if r[0] == k) for k in libs}
    say(f"  {'library':10} {'script A':>12} {'script B':>12} {'best of both':>13} {'vs baseline':>12}")
    for kind in libs:
        a = next(r[2] for r in rows if r[0] == kind and r[1] == "A")
        b = next(r[2] for r in rows if r[0] == kind and r[1] == "B")
        change = (best["baseline"] - best[kind]) / best["baseline"] * 100
        say(f"  {kind:10} {a:12.2f} {b:12.2f} {best[kind]:13.2f} {change:+11.2f}%")
    with open(f"{work}/summary.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["library", "script", "area_um2", "new_cell_instances", "cec"])
        w.writerows(rows)
    say(f"\ndone in {time.time() - START:.0f}s; files in {work}/")
    if any(r[4] != "pass" for r in rows):
        sys.exit("some mapping failed cec")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if not args or not args[0]:
        sys.exit(__doc__)
    top = args[1] if len(args) > 1 and args[1] else None
    sv = len(args) > 2 and args[2] not in ("", "0")
    main(args[0], top, sv)
