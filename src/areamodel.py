
from contained import load_hd_cells
from statistics import linear_regression
import csv
import sys, os



SITE_AREA = 0.46 * 2.72

SKIP = ("lpflow_", "dly", "probe")

HD_LIB = os.environ.get(
    "HD_LIB",
    "pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")

SPICE = os.environ.get(
    "SPICE",
    "pdk/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice")

_LINES = None


def x1_cells(lib_path, spice_path):
    transistors = count_transistors(spice_path)
    result = []
    for name, area, pins, tt in load_hd_cells(lib_path):
        if not name.endswith("_1") or name not in transistors:
            continue
        if any(word in name for word in SKIP):
            continue
        sites = round(area / SITE_AREA)
        single = is_single_stage(tt, len(pins))
        result.append((name, sites, transistors[name], single))
    return result


def count_transistors(spice_path):
    counts = {}
    current = None
    for line in open(spice_path):
        words = line.split()
        if not words:
            continue
        first = words[0].lower()
        if first == ".subckt":
            current = words[1]
            counts[current] = 0
        elif first == ".ends":
            current = None
        elif current is not None and ("nfet" in line or "pfet" in line):
            counts[current] += 1
    return counts





def is_single_stage(tt, k):
    for pin in range(k):
        for row in range(1 << k):
            if (row >> pin) & 1:
                continue
            high_row = row | (1 << pin)
            out_low = (tt >> row) & 1
            out_high = (tt >> high_row) & 1
            if out_low == 0 and out_high == 1:
                return False
    return True




def fit(cells, single):
    xs = [t for name, sites, t, one in cells if one == single]
    ys = [sites for name, sites, t, one in cells if one == single]
    slope, intercept = linear_regression(xs, ys)
    return slope, intercept



def predict(transistors, slope, intercept):
    sites = round(slope * transistors + intercept)
    return sites * SITE_AREA

def error_table(cells, path):
    single_slope, single_intercept = fit(cells, True)
    multi_slope, multi_intercept = fit(cells, False)

    single_errors = []
    multi_errors = []

    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["cell", "single_stage", "transistors", "real_sites", "predicted_sites", "error_sites"])

        for name, sites, t, single in cells:
            if single:
                guess = round(single_slope * t + single_intercept)
                single_errors.append(abs(guess - sites))
            else:
                guess = round(multi_slope * t + multi_intercept)
                multi_errors.append(abs(guess - sites))
            w.writerow([name, single, t, sites, guess, guess - sites])

    print("single-stage: mean error", round(sum(single_errors) / len(single_errors), 2),
          "sites, worst", max(single_errors), "sites")
    print("multi-stage:  mean error", round(sum(multi_errors) / len(multi_errors), 2),
          "sites, worst", max(multi_errors), "sites")


def estimate_area(tt):
    from cost import cost 

    global _LINES

    if _LINES is None:
        cells = x1_cells(HD_LIB, SPICE)
        _LINES = {True: fit(cells, True), False: fit(cells, False)}

    transistors, single = cost(tt)
    if transistors == 0:
        return None
    
    slope, intercept = _LINES[single]
    return max(predict(transistors, slope, intercept), SITE_AREA)
    

if __name__ == "__main__":
    lib = sys.argv[1]
    spice = sys.argv[2]
    
    cells = x1_cells(lib, spice)
    error_table(cells, "results/area_model.csv")