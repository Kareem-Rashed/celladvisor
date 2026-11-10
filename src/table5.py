"""Step 9 of the Option 2 handout: map every design with and without the new
cells, and check every mapping with ABC's cec (handout, sections 2 and 7).

24 runs: 6 designs x {baseline, extended} x {script A, script B}. Each mapping
uses exactly the commands of handout section 2 (given/scripts/map.sh); the
mapped netlist is written only after stat:

  read_verilog; synth -flatten -top T; dfflibmap -liberty L
  abc -liberty L -script S; opt_clean -purge; stat -liberty L
  write_verilog  results/mapped/<run>.v

Nothing may be written before abc: a write_verilog between dfflibmap and abc
changes what ABC produces (cpu8, script A: 4,181.5 instead of 4,209.0 um2 with
Yosys 0.70), so the area would no longer be the handout's flow.

The reference for cec comes from a second Yosys run with the same commands up
to dfflibmap: the RTL after synthesis and flip-flop mapping, before ABC.
Synthesis is deterministic, so its flip-flops have the same instance names.

cec: both netlists are read with the Liberty cell models (so each new cell is
checked against its declared function), flattened, and written as BLIF; ABC's
cec then proves the combinational logic between flip-flops equal. Flip-flops
keep their instance names (write_verilog -norename), so they appear in the
same order in both files and are matched by order (cec -n).

Writes:
  results/mapped/<design>_<baseline|extended>_<A|B>.v
  results/mapped/logs/<run>.log         stat and cec output of every run
  results/table5.csv                    two rows per design (handout Table 5)
  results/table5_best.csv               best of both scripts, per design and total
"""

import csv
import os
import re
import subprocess
import sys

DESIGNS = [("cpu8", "cpu8"), ("dsp8", "dsp8"), ("arlet6502", "cpu"),
           ("uart_apb", "uart_apb_master"), ("risc8", "cpu"), ("fir10", "fir10"),
           ("spm", "SPM"), ("mul", "mul")]
LIBS = {"baseline": "given/hd_reduced.lib", "extended": "libs/hd_extended.lib"}
SCRIPTS = {"A": "+strash;dch,-f;amap;topo",
           "B": "+strash;&get,-n;&dch,-f;&nf,-R,1000;&put"}
NEW_CELL_PREFIX = "dd2_"
BUILD = "build/table5"
MAPPED = "results/mapped"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def yosys(script):
    return run(["yosys", "-q", "-p", script])


def map_design(verilog, top, lib, script, out_v, stat_txt):
    """The handout's commands; the netlist is written after stat."""
    code, log = yosys(
        f"read_verilog {verilog}; synth -flatten -top {top}; "
        f"dfflibmap -liberty {lib}; "
        f"abc -liberty {lib} -script {SCRIPTS[script]}; opt_clean -purge; "
        f"tee -q -o {stat_txt} stat -liberty {lib}; "
        f"write_verilog -noattr -norename {out_v}")
    if code != 0:
        raise RuntimeError(f"mapping failed: {verilog} {lib} {script}\n{log[-2000:]}")
    m = re.search(r"Chip area for module .*?:\s*([0-9.]+)", open(stat_txt).read())
    return float(m.group(1))


def reference(verilog, top, lib, ref_v):
    """The RTL after synthesis and flip-flop mapping, before ABC."""
    code, log = yosys(
        f"read_verilog {verilog}; synth -flatten -top {top}; "
        f"dfflibmap -liberty {lib}; write_verilog -noattr -norename {ref_v}")
    if code != 0:
        raise RuntimeError(f"reference failed: {verilog}\n{log[-2000:]}")


def new_cell_instances(netlist):
    pattern = re.compile(r"^\s*(" + NEW_CELL_PREFIX + r"\S+)\s+\S+\s*\(", re.M)
    return len(pattern.findall(open(netlist).read()))


def to_blif(netlist, top, lib, blif):
    code, log = yosys(
        f"read_liberty -ignore_miss_func {lib}; read_verilog {netlist}; "
        f"hierarchy -top {top}; flatten; techmap; async2sync; dffunmap; "
        f"opt_clean -purge; write_blif {blif}")
    if code != 0:
        raise RuntimeError(f"cannot flatten {netlist}\n{log[-2000:]}")


def cec(ref_v, impl_v, top, lib, work):
    """(passed, abc output) for the mapped netlist impl_v against ref_v."""
    ref_blif, impl_blif = work + "_ref.blif", work + "_impl.blif"
    to_blif(ref_v, top, lib, ref_blif)
    to_blif(impl_v, top, lib, impl_blif)
    _, log = run(["yosys-abc", "-c", f"cec -n {ref_blif} {impl_blif}"])
    lines = [l for l in log.splitlines() if "equivalent" in l.lower()]
    return "Networks are equivalent" in log, (lines or log.strip().splitlines())[-1].strip()


def design_file(design):
    """The Table 2 designs are in given/designs; SPM and the multiplier
    (Tutorials 4 and 2) are in designs/."""
    path = f"given/designs/{design}.v"
    return path if os.path.exists(path) else f"designs/{design}.v"


def one_run(design, top, lib_name, script):
    name = f"{design}_{lib_name}_{script}"
    lib = LIBS[lib_name]
    ref_v = f"{BUILD}/{name}_ref.v"
    out_v = f"{MAPPED}/{name}.v"
    stat = f"{BUILD}/{name}_stat.txt"
    verilog = design_file(design)
    area = map_design(verilog, top, lib, script, out_v, stat)
    reference(verilog, top, lib, ref_v)
    used = new_cell_instances(out_v)
    passed, cec_line = cec(ref_v, out_v, top, lib, f"{BUILD}/{name}")
    with open(f"{MAPPED}/logs/{name}.log", "w", newline="\n") as f:
        f.write(open(stat).read())
        f.write(f"\ncec: {cec_line}\n")
    print(f"{name:26} area {area:10.2f}  new cells {used:5}  cec {'pass' if passed else 'FAIL'}")
    return area, used, passed


def main():
    for lib in LIBS.values():
        if not os.path.exists(lib):
            sys.exit(f"missing {lib}: run make setup / make liberty first")
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(f"{MAPPED}/logs", exist_ok=True)

    rows, best = [], []
    all_pass = True
    for design, top in DESIGNS:
        areas = {}
        for script in SCRIPTS:
            base, _, base_ok = one_run(design, top, "baseline", script)
            ext, used, ext_ok = one_run(design, top, "extended", script)
            ok = base_ok and ext_ok
            all_pass &= ok
            areas[script] = (base, ext)
            rows.append([design, script, round(base, 4), round(ext, 4),
                         round((base - ext) / base * 100, 2), used,
                         "pass" if ok else "FAIL"])
        b = min(a[0] for a in areas.values())
        e = min(a[1] for a in areas.values())
        best.append([design, round(b, 4), round(e, 4), round((b - e) / b * 100, 2)])

    tb = sum(r[1] for r in best)
    te = sum(r[2] for r in best)
    best.append(["total", round(tb, 4), round(te, 4), round((tb - te) / tb * 100, 2)])

    with open("results/table5.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["design", "script", "baseline_um2", "with_new_cells_um2",
                    "reduction_pct", "new_cell_instances", "equivalence"])
        w.writerows(rows)
    with open("results/table5_best.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["design", "baseline_best_um2", "with_new_cells_best_um2",
                    "reduction_pct"])
        w.writerows(best)
    print(f"best of both, total over the required designs: "
          f"{tb:.2f} -> {te:.2f} um2 ({(tb - te) / tb * 100:.2f}%)")
    if not all_pass:
        sys.exit("some mapping failed cec")


if __name__ == "__main__":
    main()
