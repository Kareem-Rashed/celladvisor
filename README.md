# Project 1, Option 2: celladvisor

celladvisor finds the small logic functions that synthesized designs compute
over and over, checks which ones the sky130_fd_sc_hd (HD) library already
provides, proposes new cells for the ones it lacks, and measures how much area
those cells save when Yosys and ABC map the designs with them.

**Checkpoint 2 headline:** five new cells, chosen by the tool, cut the total
best-of-both area of the six required designs by **1.70%** (86,559.27 to
85,089.11 um2), with estimated areas. All 24 mappings pass ABC's `cec`.

## 1. Group

| Name                | Student ID |
| ------------------- | ---------- |
| Kareem Rashed       | 900233328  |
| Joshua Makar        | 900231109  |
| Mahinour Abdelgawad | 900231870  |

Group GB3 (new cells are named `dd2_gb3__...`) · Option 2 · AI used as a development aid

## 2. Quick start

Tools: Yosys 0.70+post (with its ABC, `yosys-abc`), Python 3.11 or newer.
Icarus Verilog and OpenSTA are not used yet (see section 9).

The handout measured its numbers with Yosys 0.33. Section 9 lists what that
changes.

    make setup     # links pdk/ and given/
    make check     # tool versions, PDK link, given files
    make test      # every test, including the broken cases (a few minutes: some run Yosys)
    make all       # the whole flow, step by step (about 15 minutes, most of it Table 5)

`make setup` expects the student pack next to the repository
(`../DD2_Project1_student_pack/given`) and the PDK in `~/.ciel/sky130A`.
Override with `make setup GIVEN=<path> PDK_ROOT=<path>`.

## 3. What the tool does

One Make target per step of the Option 2 handout, section 4:

| Step | What happens                                                                                                                                                         | Target                         | Output                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------ |
| 1    | Synthesize each design and write it as an and-inverter graph (AIG), raw, with duplicate nodes merged (`strash`), and after ABC restructuring (`strash; dch; strash`) | `make aigs`                    | `build/aig/`, `results/aig_sizes.csv`                              |
| (2)  | Handout Table 1: every design on the usable and reduced HD libraries, scripts A and B                                                                                | `make table1`                  | `results/table1.csv`                                               |
| 2    | Enumerate every cut of up to 4 inputs, bottom-up over the AIG                                                                                                        | `make cuts`                    | `results/cut_counts.csv`                                           |
| 2, 3 | Truth table of every cut, class up to input order (P) and up to input order and output inversion (PN), frequency per design                                          | `make candidates`              | `results/class_counts.csv`                                         |
| 5    | Classify every class against the full HD library as Exists, Exists with an inverter, Contained or New (Table 3), and keep or drop it                                 | `make candidates`              | `results/candidates.csv`, `results/candidates_kept.csv`            |
| 4    | Cost each class as CMOS: transistors, single or multi-stage                                                                                                          | (used by `candidates`, `rank`) | `src/cost.py`                                                      |
| 6    | Area model: width in sites against transistor count, fitted on HD's x1 cells, one line for single-stage and one for multi-stage cells                                | `make area-model`              | `results/area_model.csv`                                           |
| 7    | Rank: what HD pays now for each function (mapped on its own) against the new cell's estimated area, times frequency                                                  | `make rank`                    | `results/ranked.csv`                                               |
| 8    | The top 5 ranked classes as new cells: the extended Liberty file, one Appendix A request per cell, and a check that Yosys loads it                                   | `make liberty`                 | `libs/new_cells.csv`, `libs/hd_extended.lib`, `results/requests/`  |
| 9    | Map every design with and without the new cells, scripts A and B (24 runs), and check every mapping with ABC's `cec`                                                 | `make table5`                  | `results/mapped/`, `results/table5.csv`, `results/table5_best.csv` |

Steps 10 (greedy selection), 11 (real cells) and 12 (the 30% test) are not
done yet.

Module interfaces and owners: [docs/interfaces.md](docs/interfaces.md).

## 4. Commands

| Command                       | Input                                  | Output                                                                                                               |
| ----------------------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `make aigs`                   | `given/designs/`                       | AIGs in `build/aig/`, sizes in `results/aig_sizes.csv`                                                               |
| `make table1`                 | `given/designs/`, both given libraries | `results/table1.csv`, with the handout's numbers and the difference                                                  |
| `make hd-table`               | `HD_LIB`                               | `results/hd_classes.csv`: every HD cell of up to 4 inputs with its truth table and classes                           |
| `make contained-table`        | `HD_LIB`                               | `results/contained_table.csv`: every 4-input function an HD cell computes with its pins tied to the inputs or to 0/1 |
| `make cuts`                   | `build/aig/`                           | `results/cut_counts.csv`                                                                                             |
| `make candidates`             | `build/aig/`, `HD_LIB`                 | `results/class_counts.csv`, `results/candidates.csv`, `results/candidates_kept.csv`                                  |
| `make area-model`             | `HD_LIB`, `SPICE`                      | `results/area_model.csv` and the fit's error                                                                         |
| `make rank`                   | `results/candidates_kept.csv`          | `results/ranked.csv` (maps each top function on its own: about a minute)                                             |
| `make new-cells GROUP=b3 N=5` | `results/ranked.csv`                   | `libs/new_cells.csv`                                                                                                 |
| `make liberty`                | `results/ranked.csv`                   | `libs/hd_extended.lib`, `results/requests/<cell>.json`, and the Yosys load check                                     |
| `make table5`                 | the 6 designs, both libraries          | netlists, logs, `results/table5.csv`, `results/table5_best.csv`                                                      |
| `make demo IN=<file>`         | a design                               | not written yet                                                                                                      |

`HD_LIB` is the full HD Liberty
(`pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib`), used
for redundancy and the area model. `SPICE` is the HD SPICE netlist
(`pdk/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice`). `GROUP` is our
group (`b3`). Mapping always uses `given/hd_reduced.lib` as the baseline.

## 5. Layout

- `src/`: the tool, one module per step; see `docs/interfaces.md`
- `scripts/`: the shell scripts for the AIGs and Table 1
- `tests/`: the tests; every file runs as a script (`python3 tests/test_x.py`)
- `tests/broken/`: the broken cases each check must fail on (never edited to make a test pass)
- `results/`: every table, netlist and log the report uses
- `libs/`: the Liberty file the tool writes, and `new_cells.csv`, the cells it adds
- `docs/`: `interfaces.md`, and the cell request and response examples (overview, Appendix A)
- `ai/`: AI use log and AI mistakes log
- `report/`: `report.pdf` and `ai_report.pdf` with their sources (not written yet)

## 6. Results

Every number below comes from a file in `results/` or `libs/`.

### Table 1 reproduced (`results/table1.csv`)

All 24 runs work. Our areas are within about 4.5% of the handout's, mostly
smaller (Yosys 0.70 against 0.33). The reduced library costs script B almost
nothing, as in the handout, but costs script A up to 3.0% (fir10: 25,557.01
usable against 26,322.75 reduced), where the handout reports at most 0.5%.

### AIGs, cuts and classes (`results/aig_sizes.csv`, `results/cut_counts.csv`, `results/class_counts.csv`)

Flip-flop counts match the handout's Table 2 exactly. AND counts are lower
(Yosys 0.70). ABC's restructuring makes every graph smaller and gives fewer
cuts and fewer classes:

| Design    | ANDs (strash / abc) | Cuts of 2 to 4 inputs (strash / abc) | PN classes (strash / abc) |
| --------- | ------------------- | ------------------------------------ | ------------------------- |
| cpu8      | 881 / 849           | 5,693 / 5,111                        | 180 / 167                 |
| dsp8      | 1,348 / 1,293       | 10,337 / 9,346                       | 199 / 185                 |
| arlet6502 | 2,380 / 2,091       | 17,368 / 14,478                      | 200 / 187                 |
| uart_apb  | 2,212 / 1,770       | 14,081 / 8,996                       | 140 / 102                 |
| risc8     | 5,214 / 4,876       | 35,989 / 31,408                      | 190 / 167                 |
| fir10     | 6,503 / 6,390       | 62,886 / 60,831                      | 209 / 197                 |

### Redundancy (`results/candidates.csv`)

Classes across all six designs, by Table 3 label:

| Graph  | Exists | Exists with an inverter | Contained | New | Kept | Dropped |
| ------ | ------ | ----------------------- | --------- | --- | ---- | ------- |
| strash | 51     | 28                      | 30        | 409 | 442  | 76      |
| abc    | 46     | 28                      | 30        | 346 | 379  | 71      |

The checker reproduces the handout's Table 4 exactly (24 / 20 / 38 / 3,822),
and every HD cell fed to it comes out as Exists.

### Area model (`results/area_model.csv`)

| Group        | HD x1 cells | Mean error | Worst error |
| ------------ | ----------- | ---------- | ----------- |
| Single-stage | 27          | 0.22 sites | 1 site      |
| Multi-stage  | 58          | 0.53 sites | 2 sites     |

Low-power, delay and probe cells are left out of the fit (section 9).

### Ranking (`results/ranked.csv`)

Of the 30 most frequent kept classes, 10 are estimated to save area, 1 breaks
even and 19 lose area. Frequency is not saving: `000e` is the second most
frequent but HD builds it for 8.76 um2 against an estimated 11.26 um2 for a new
cell (-5,610 um2 in total), while `000b`, as frequent, saves an estimated
5,603 um2. Every XOR-like class loses.

### Table 5, first version (`results/table5.csv`, `results/table5_best.csv`)

The top 5 ranked classes as new cells (`libs/new_cells.csv`), with estimated
areas. Yosys loads the extended library with 194 cell types. All 24 mappings
pass `cec`.

| Design    | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence |
| --------- | ------ | -------------- | -------------------- | --------- | ------------------ | ----------- |
| cpu8      | A      | 4,195.27       | 4,197.78             | -0.06%    | 34                 | pass        |
| cpu8      | B      | 4,321.64       | 4,296.62             | 0.58%     | 4                  | pass        |
| dsp8      | A      | 5,794.31       | 5,741.76             | 0.91%     | 9                  | pass        |
| dsp8      | B      | 6,102.10       | 6,160.91             | -0.96%    | 20                 | pass        |
| arlet6502 | A      | 9,320.19       | 9,197.57             | 1.32%     | 5                  | pass        |
| arlet6502 | B      | 9,546.66       | 9,550.41             | -0.04%    | 20                 | pass        |
| uart_apb  | A      | 12,817.29      | 12,634.62            | 1.43%     | 10                 | pass        |
| uart_apb  | B      | 13,030.00      | 13,038.76            | -0.07%    | 8                  | pass        |
| risc8     | A      | 28,187.03      | 27,709.08            | 1.70%     | 24                 | pass        |
| risc8     | B      | 28,109.46      | 28,383.47            | -0.97%    | 44                 | pass        |
| fir10     | A      | 26,322.75      | 25,608.31            | 2.71%     | 9                  | pass        |
| fir10     | B      | 28,935.25      | 28,742.57            | 0.67%     | 212                | pass        |

Best of both scripts: cpu8 -0.06%, dsp8 0.91%, arlet6502 1.32%, uart_apb
1.43%, risc8 1.42%, fir10 2.71%. **Total: 86,559.27 to 85,089.11 um2, 1.70%.**

What stands out:

- Script A gains in five of six designs. The five cells have no input used
  twice, so script A's structural matching can use them.
- Script B uses the new cells more (212 times in fir10, 44 in risc8) but ends
  up larger in four designs. Using a cell more often does not mean saving more.
- cpu8 gains nothing: the five cells come from the most frequent classes
  overall, which fir10 and risc8 dominate.
- Part of script A's gain may be refilling what the reduced library removed:
  risc8 with script A on the extended library (27,709.08) is smaller than on
  the full usable library (27,764.13 in Table 1).

## 7. Tests

`make test` runs every file below. All pass.

| Test file                        | What it checks                                                                                                                                                                | Broken case                                                                                                                                     |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_aig_reader.py`       | the AIGER reader                                                                                                                                                              |                                                                                                                                                 |
| `tests/test_canon.py`            | input permutation, class IDs, used inputs; exactly 3,904 classes of 4-input functions that use all 4 inputs                                                                   |                                                                                                                                                 |
| `tests/test_cuts.py`             | cut enumeration: dominated cuts removed, size limit, the hand-traced cuts and truth tables of a tiny AIG                                                                      |                                                                                                                                                 |
| `tests/test_cut_check.py`        | the cut check accepts a correct truth table and rejects a wrong one                                                                                                           | `tests/broken/wrong_cut_tt.json` on `tests/broken/small_aig.aag`: one bit flipped                                                               |
| `tests/test_hdlib.py`            | the Liberty expression parser and the HD class table                                                                                                                          |                                                                                                                                                 |
| `tests/test_contained.py`        | the Contained table: nand3 with a pin tied high is nand2, mux2 with its select tied passes one input, the cheapest drive is kept                                              |                                                                                                                                                 |
| `tests/test_redundancy_check.py` | every HD cell of up to 4 inputs is Exists; the handout's `0x077F` is New                                                                                                      | `tests/broken/hd_cell_as_candidate.json`: nand2_1 must be Exists                                                                                |
| `tests/test_table4.py`           | the handout's Table 4: 24 Exists, 20 Exists with an inverter, 38 Contained, 3,822 New                                                                                         |                                                                                                                                                 |
| `tests/test_cost.py`             | nand2 4, aoi21 6, the handout's majority cell 12 transistors; and2 and xor2 multi-stage; agrees with the area model's single-stage test on all 65,536 functions               |                                                                                                                                                 |
| `tests/test_areamodel.py`        | transistor counts from SPICE (inv 2, nand2 4, a21oi 6); the single-stage test; 12 transistors give 8 sites; mean error under 1 site                                           |                                                                                                                                                 |
| `tests/test_liberty_writer.py`   | the writer reproduces the handout's example cell exactly; its request is `0x077F` (Appendix A); timing senses; the SOP writer on 305 truth tables; the extended library loads | `tests/broken/liberty_missing_brace.lib` (not valid Liberty) and `tests/broken/liberty_unknown_pin.lib` (a function names a pin the cell lacks) |
| `tests/test_cec.py`              | `cec` passes cpu8 mapped with script A                                                                                                                                        | `tests/broken/cec_swapped_gate.json`: one nand2_1 replaced by nor2_1 must fail `cec`                                                            |

## 8. AI use

AGENTS.md · ai/use_log.md · ai/mistakes_log.md · report/ai_report.pdf (not written yet)

## 9. Limitations

- **Yosys version.** We use 0.70; the handout used 0.33. Areas differ by up to
  about 4.5%, AND counts are lower, and the reduced library costs script A up
  to 3.0% instead of under 0.5%.
- **Areas are estimates.** Every new cell's area comes from the area model and
  the cost estimate, not from a real layout. Real cells (step 11) and the 30%
  test (step 12) are not done yet.
- **Area model.** Fitted on HD's x1 cells with low-power (`lpflow_`), delay
  (`dly`) and probe cells left out: their width comes from their electrical
  purpose (two power wells, deliberately slow devices), not their logic, and
  with them the multi-stage worst error was 15 sites. HD's smallest cells are 3
  sites wide whatever their transistor count, so the model underestimates the
  inverter. It overestimates compact multi-stage cells such as `maj3_1` (12
  predicted against 8 real sites).
- **Cost.** The 3-transistors-in-series limit is not enforced yet, so `nand4`
  counts as one stage. Multi-stage costs are a rough estimate (inverted inputs
  plus one stage, or an output inverter); XOR-like functions get a fixed
  estimate of 40 transistors.
- **Ranking** maps each function on its own and multiplies by its frequency.
  Cuts overlap, so not every occurrence can be replaced at once.
- **cec** compares each mapped netlist with the design after Yosys synthesis
  and flip-flop mapping (before ABC), not with the Verilog source; flip-flops
  are matched by order. Tutorial 4's gate-level testbenches are not run yet.
- **Timing.** The new cells' capacitance and timing are placeholders (handout
  section 6). OpenSTA delays are not in Table 5 yet.
- Script A areas can differ slightly between machines with the same Yosys
  version (cpu8: 4,181.51 against 4,195.27 um2). Baseline and extended areas in
  Table 5 always come from the same run.
- `make demo` is not written yet.

## 10. Third-party files

None. The given files (`given/`) and the PDK (`pdk/`) are linked by
`make setup`, not copied into the repository.
