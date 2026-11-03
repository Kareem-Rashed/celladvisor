# Module interfaces and status

Read this before writing code that calls another member's module. It lists
what each module in `src/` exposes, who owns it, and what is not written yet.
Update it in the same commit whenever you add or change a public function.

Last updated: 2026-11-03 (Joshua).

## Shared conventions

- **Layout.** Modules live directly in `src/` (not `src/celladvisor/`). Tests
  live in `tests/`, add `src/` to `sys.path`, and import modules by name
  (`from canon import canon_p`). Every test file also runs as a script
  (`python3 tests/test_x.py`), which is what `make test` does, and works with
  `pytest`.
- **Truth tables** are Python ints. For a 4-input function: 16 bits, bit i is
  the output for row i, and input A is bit 0 of the row number (B bit 1, C
  bit 2, D bit 3). So A = `0xAAAA`, B = `0xCCCC`, C = `0xF0F0`, D = `0xFF00`.
  For an HD cell with k pins: 2**k bits, pin j is bit j of the row number,
  pins in the order `hdlib.support(expr)` returns (sorted names).
- **HD library path** comes from the environment variable `HD_LIB` (the
  Makefile sets it to the full PDK Liberty,
  `pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib`).
  Redundancy checks always use the full library, never `hd_reduced.lib`.

## Status

| Step (Option 2 handout, section 4) | Module | Owner | Status |
|---|---|---|---|
| 1. AIG extraction, Table 1 | scripts (to add) | Kareem | Run by hand; scripts not in repo yet |
| 2. Cut enumeration and cut check | `src/cuts.py` | current implementation | **Implemented and verified** by `tests/test_cut_check.py` |
| 3. Classes up to input order / output inversion | `src/canon.py` | Kareem | Done, tested (3,904 classes) |
| HD class table | `src/hdlib.py` | Mahinour | Done, tested; writes `results/hd_classes.csv` |
| 5. Redundancy: Exists, Exists with an inverter | `src/redundancy.py` | Mahinour | **Implemented and verified** by `tests/test_redundancy_check.py` |
| 5. Redundancy: Contained | `src/contained.py` | Joshua | Done, tested |
| 5. Table 4 self-test | in `tests/` | Mahinour | Implemented and passing (`tests/test_table4.py`) |
| 8. Liberty file and cell requests | `src/liberty_writer.py`, `src/check_liberty.py` | Joshua | Done, tested; `make liberty` |
| 9. Mapping, Table 5, cec | `src/table5.py` | Joshua | Done, tested; `make table5` |

## `src/canon.py` (Kareem)

- `canon_p(tt) -> int`: class ID up to input order (smallest truth table over
  the 24 input permutations). Use for the Exists test.
- `canon_pn(tt) -> int`: class ID up to input order and output inversion.
- `permute(tt, p) -> int`: truth table with inputs reordered by `p`.
- `used_inputs(tt) -> set[int]`: inputs (0 = A ... 3 = D) the function
  depends on. Full support is `{0, 1, 2, 3}`.

## `src/hdlib.py` (Mahinour)

- `read_cells(path)`: yields `(name, [(pin, function)...], nonlogic)` per
  Liberty cell; `nonlogic` is true for sequential and tri-state cells.
- `support(expr) -> list[str]`: input pin names in an expression, sorted.
- `eval_function(expr, order) -> int`: truth table, pin `order[k]` = bit k.
- `pad_to_4(tt, n) -> int`: an n-input table extended to 16 bits.
- `build_table(lib, canon_p, canon_pn) -> (rows, wide, skipped)`: rows are
  `(name, n_inputs, tt_hex, class_p_hex, class_pn_hex)` for cells of up to 4
  inputs; `wide` holds `(name, n, order, tt)` for 5 and 6 input cells.
- Does **not** read cell area. `contained.load_hd_cells` adds it.

## `src/contained.py` (Joshua)

The Contained test of Table 3: an HD cell with each pin tied to A, B, C, D, 0
or 1 (pins may share an input) computes the candidate.

- `load_hd_cells(lib_path) -> [(name, area, pins, tt)]`: every single-output
  combinational cell, through `hdlib`, plus its area. Use this when you need
  cells with their area.
- `build_contained_table(cells) -> {tt: (area, cell_name, wiring)}`: every
  4-input truth table reachable by tying pins, with the **cheapest** cell that
  reaches it (Table 3 drops a Contained candidate unless it is smaller than
  that cell). `wiring` is e.g. `{"A1": "A", "A2": "B", "B1": "0"}`. Build it
  once (a few seconds) and reuse it.
- `contained_in(tt, table) -> None | (area, cell_name, wiring)`: the lookup.
- `wire(cell_tt, wiring) -> int`: 16-bit truth table of one cell under one
  wiring; `wire(cell_tt, "ABCD"[:k])` turns a k-pin cell into a candidate.
- Command line: `python3 src/contained.py <lib> <csv>` (`make contained-table`)
  writes every reachable truth table to `results/contained_table.csv`.

The table contains functions that also Exist (every cell wired straight
through finds itself). That is expected: `classify` must test in the order of
Table 3, so Contained is only reported when Exists and Exists with an
inverter have failed.

## Current public interfaces

These signatures are the ones the project currently uses and validates. If you
choose another name, change the import in the test, not the test's logic or the
files in `tests/broken/`.

### `src/redundancy.py` (Mahinour)

    classify(tt) -> (label, hd_cell_name_or_None)

`label` is one of `"Exists"`, `"Exists with an inverter"`, `"Contained"`,
`"New"`, tested in that order (Table 3). For Contained, call
`contained.contained_in`. Reads the library from `HD_LIB`. Checked by:

- `tests/test_redundancy_check.py`: nand2 (`0x7777`) is Exists; every HD cell
  of up to 4 inputs is Exists; the handout's `0x077F` is New.
- `tests/test_table4.py`: over the 3,904 full-support classes, exactly 24 /
  20 / 38 / 3,822 are returned as the correct counts for the four labels.

### `src/cuts.py` (task 1)

    verify_cut(aig_path, root, leaves, tt) -> bool

`root` and `leaves` are AIGER variable numbers (literal // 2); `leaves[k]` is
input k (A, B, C, D). Simulates the cut on all 16 rows and returns whether
`tt` is right. Checked by `tests/test_cut_check.py` with
`tests/broken/small_aig.aag` (`y = (a & b) | c`): root 5 with leaves
`[1, 2, 3]` must accept `0x0707` and reject the one-bit-wrong `0x0706`.

## `src/liberty_writer.py` (Joshua)

New cells are listed in `libs/new_cells.csv` with the columns
`name,expression,area_um2` (name starts with `dd2_g<group>__`; expression uses
the input names with `! & | ^` and parentheses; the output pin is always `Y`).

- `cell_group(name, expression, area) -> str`: one Liberty cell group in the
  form of handout section 6: area, input pins with a placeholder capacitance,
  the output function, one timing arc per input with its timing sense and
  placeholder delays. Inputs are `hdlib.support(expression)` (sorted).
- `write_library(base_lib, cells, out_lib)`: copies `base_lib` with the new
  groups added before its final `}`; refuses a name already in the library.
- `request(name, expression, area, request_id) -> dict`: an Appendix A request;
  `truth_table` is hex with the first input as bit 0 (0x077F for the handout's
  example).
- `sop(tt) -> str`: a small sum-of-products expression over A..D for a 16-bit
  truth table; `cells_from_ranked(ranked_csv, n, group)` uses it to turn the top
  rows of `results/ranked.csv` into cells (`make new-cells GROUP=<n> N=5`).

## `src/check_liberty.py` (Joshua)

- `check_liberty(path, expected=None) -> (ok, message)`: `read_liberty -lib`
  must print "Imported N cell types" with N = expected, and the full
  `read_liberty` must parse every function. `-lib` alone accepts a function
  that names a pin the cell does not have.

## `src/table5.py` (Joshua)

- `map_design(verilog, top, lib, script, out_v, stat_txt) -> area`: the
  handout's mapping commands; the netlist is written after `stat`. Writing it
  before `abc` changes ABC's result.
- `reference(verilog, top, lib, ref_v)`: the same commands up to `dfflibmap`.
- `cec(ref_v, impl_v, top, lib, work) -> (passed, abc_line)`: both netlists
  read with the Liberty models, flattened, written as BLIF, compared with
  `yosys-abc -c "cec -n ..."`.
- `main()`: the 24 runs, `results/table5.csv`, `results/table5_best.csv`.
