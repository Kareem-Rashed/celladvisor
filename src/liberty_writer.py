"""Steps 8 of the Option 2 handout: the extended Liberty file and the cell requests.

Input: a CSV of new cells with the columns  name, expression, area_um2
  name        starts with dd2_g<group>__ (overview, Appendix A)
  expression  uses the input names with ! & | ^ and parentheses, e.g.
              !((C&D) | (A&B&(C|D)))
  area_um2    the estimated area (area model), replaced later by the real cell

Output:
  * the extended Liberty file: hd_reduced.lib with one cell group per new cell
    added inside its library group (handout, section 6), so the units and
    templates are shared;
  * one request JSON per cell in the format of the overview, Appendix A.

Capacitance and timing are placeholders (handout, section 6: both mapping
scripts aim at area), but they must be present: with only area, pins and
function, Yosys 0.33's ABC crashes in its map command.

Usage:
  python3 src/liberty_writer.py <cells.csv> <base.lib> <out.lib> <requests_dir>
  python3 src/liberty_writer.py --from-ranked <ranked.csv> <n> <group> <cells.csv>
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hdlib import eval_function, support

OUTPUT_PIN = "Y"
CAPACITANCE = 0.0024        # pF, placeholder from the handout's example cell
CELL_RISE, CELL_FALL = "0.10", "0.08"              # ns, placeholders
RISE_TRANSITION, FALL_TRANSITION = "0.10", "0.08"  # ns, placeholders


def truth_table(expression, inputs):
    """Truth table over `inputs`: bit i is the output when input k = bit k of i."""
    return eval_function(expression, inputs)


def timing_sense(tt, n_inputs, pin):
    """positive_unate, negative_unate or non_unate for input `pin` (0 = first)."""
    rises = falls = False
    for row in range(1 << n_inputs):
        if (row >> pin) & 1:
            continue
        low = (tt >> row) & 1
        high = (tt >> (row | (1 << pin))) & 1
        rises |= high > low
        falls |= high < low
    if not rises and not falls:
        raise ValueError(f"input {pin} does not affect the function")
    if rises and falls:
        return "non_unate"
    return "positive_unate" if rises else "negative_unate"


def cell_group(name, expression, area):
    """One Liberty cell group in the form of the handout, section 6."""
    inputs = support(expression)
    if not 1 <= len(inputs) <= 4:
        raise ValueError(f"{name}: {len(inputs)} inputs, the tools accept 1 to 4")
    if OUTPUT_PIN in inputs:
        raise ValueError(f"{name}: an input is named {OUTPUT_PIN}, the output pin")
    tt = truth_table(expression, inputs)
    lines = [f'  cell ("{name}") {{', f"    area : {area};"]
    for pin in inputs:
        lines.append(f'    pin ("{pin}") {{ direction : "input"; '
                     f"capacitance : {CAPACITANCE}; }}")
    lines += [f'    pin ("{OUTPUT_PIN}") {{',
              '      direction : "output";',
              f'      function : "{expression}";']
    for k, pin in enumerate(inputs):
        lines += ["      timing () {",
                  f'        related_pin : "{pin}";',
                  f'        timing_sense : "{timing_sense(tt, len(inputs), k)}";',
                  f'        cell_rise (scalar) {{ values ("{CELL_RISE}"); }}',
                  f'        cell_fall (scalar) {{ values ("{CELL_FALL}"); }}',
                  f'        rise_transition (scalar) {{ values ("{RISE_TRANSITION}"); }}',
                  f'        fall_transition (scalar) {{ values ("{FALL_TRANSITION}"); }}',
                  "      }"]
    lines += ["    }", "  }"]
    return "\n".join(lines) + "\n"


def write_library(base_path, cells, out_path):
    """Copy base_path with the new cell groups added before its final '}'."""
    text = open(base_path).read()
    end = text.rstrip().rfind("}")
    if end < 0:
        raise ValueError(f"{base_path}: no closing brace")
    for name, _, _ in cells:
        if f'cell ("{name}")' in text:
            raise ValueError(f"{name} is already in {base_path}")
    groups = "".join(cell_group(*cell) for cell in cells)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="\n") as f:
        f.write(text[:end] + groups + text[end:])


def request(name, expression, area, request_id):
    """A cell request in the format of the overview, Appendix A."""
    inputs = support(expression)
    tt = truth_table(expression, inputs)
    digits = max(1, (1 << len(inputs)) // 4)
    return {
        "request_id": request_id,
        "name": name,
        "inputs": inputs,
        "output": OUTPUT_PIN,
        "expression": expression,
        "truth_table": f"0x{tt:0{digits}X}",
        "sizing": "hd",
        "estimated_area_um2": area,
    }


def read_cells(path):
    with open(path) as f:
        return [(r["name"], r["expression"], float(r["area_um2"]))
                for r in csv.DictReader(f)]


def write_requests(cells, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for i, (name, expression, area) in enumerate(cells, 1):
        with open(os.path.join(out_dir, f"{name}.json"), "w", newline="\n") as f:
            json.dump(request(name, expression, area, f"R-{i:03d}"), f, indent=2)
            f.write("\n")


# --- turning ranked candidates into cells ----------------------------------

NAMES = "ABCD"


def sop(tt, n_inputs=4):
    """A small sum-of-products expression for tt (Quine-McCluskey prime
    implicants, then a greedy cover). Constant functions are refused."""
    rows = range(1 << n_inputs)
    ones = [r for r in rows if (tt >> r) & 1]
    if not ones or len(ones) == len(rows):
        raise ValueError("constant function")
    # an implicant is (value, mask): mask bits are "don't care"
    level = {(r, 0) for r in ones}
    primes = set()
    while level:
        merged, used = set(), set()
        for a in level:
            for b in level:
                if a[1] == b[1] and bin(a[0] ^ b[0]).count("1") == 1:
                    bit = a[0] ^ b[0]
                    merged.add((a[0] & ~bit, a[1] | bit))
                    used |= {a, b}
        primes |= level - used
        level = merged

    def covers(imp, r):
        return (r & ~imp[1]) == (imp[0] & ~imp[1])

    left, chosen = set(ones), []
    while left:
        best = max(sorted(primes), key=lambda p: (sum(covers(p, r) for r in left),
                                                  bin(p[1]).count("1")))
        chosen.append(best)
        left -= {r for r in left if covers(best, r)}

    terms = []
    for value, mask in chosen:
        lits = [("" if (value >> k) & 1 else "!") + NAMES[k]
                for k in range(n_inputs) if not (mask >> k) & 1]
        terms.append("(" + "&".join(lits) + ")" if len(lits) > 1 else lits[0])
    return " | ".join(terms)


def cells_from_ranked(ranked_csv, n, group):
    """The top n rows of results/ranked.csv as (name, expression, area)."""
    with open(ranked_csv) as f:
        rows = list(csv.DictReader(f))[:n]
    return [(f"dd2_g{group}__c{r['class']}_1", sop(int(r["class"], 16)),
             float(r["new_area"])) for r in rows]


def main(argv):
    if argv[:1] == ["--from-ranked"]:
        ranked, n, group, out = argv[1], int(argv[2]), argv[3], argv[4]
        with open(out, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["name", "expression", "area_um2"])
            w.writerows(cells_from_ranked(ranked, n, group))
        print(f"wrote {n} cells to {out}")
        return
    cells_csv, base, out_lib, req_dir = argv
    cells = read_cells(cells_csv)
    write_library(base, cells, out_lib)
    write_requests(cells, req_dir)
    print(f"{len(cells)} new cells -> {out_lib}, requests in {req_dir}/")


if __name__ == "__main__":
    main(sys.argv[1:])
