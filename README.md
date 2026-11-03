# Project 1, Option 2: celladvisor

## 1. Group

- Kareem Rashed, 900233328
- Joshua Makar, 900231109
- Mahinour Abdelgawad, 900231870

Option 2 · AI used as a development aid

## 2. Quick start

Tools: Yosys 0.70, Icarus Verilog <version>, OpenSTA <version>, Python 3.11+

The Option 2 handout measured its numbers with Yosys 0.33; see section 9.

    make setup     # links pdk/ and given/; <minutes>
    make check     # verifies tool versions and the PDK link
    make test      # every project test, including the broken cases
    make all       # full flow for the project pipeline

## 3. What the tool does

celladvisor finds the small functions a synthesized design computes again and
again, checks which of them the sky130_fd_sc_hd (HD) library already has,
writes a Liberty file that adds cells for the ones it lacks, and measures how
much area those cells save when Yosys maps the designs with them.

Steps, in order (Option 2 handout, section 4): extract the AIG of each design;
enumerate cuts of up to 4 inputs with a truth table each; verify each cut against
its simulated logic; classify the truth tables up to input order and output
inversion; cost each class as a CMOS cell; drop what HD already has (Exists,
Exists with an inverter, Contained); estimate the area of the rest; rank; write
cell requests and the extended Liberty file; map and measure every design; select
up to 10 cells greedily; replace estimates with real cells; run the 30%
sensitivity test.

The current public interfaces and implementation status are described in
[docs/interfaces.md](docs/interfaces.md).

## 4. Commands

| Command | Input | Output |
| --- | --- | --- |
| `make test` | the modules in `src/`, `HD_LIB` | pass or fail for every test |
| `make hd-table` | `HD_LIB` | `results/hd_classes.csv`: every HD cell of up to 4 inputs with its truth table, P class and PN class |
| `make contained-table` | `HD_LIB` | `results/contained_table.csv`: every 4-input truth table an HD cell gives with its pins tied to A-D, 0 or 1, with the cheapest such cell and its wiring |
| `python3 src/hdlib.py <lib> <csv>` | a Liberty file | the HD class table |
| `python3 src/contained.py <lib> <csv>` | a Liberty file | the Contained table |
| `make new-cells GROUP=<n> N=5` | `results/ranked.csv` | `libs/new_cells.csv`: the top N candidates as cells (name, expression, area) |
| `make liberty` | `libs/new_cells.csv` | `libs/hd_extended.lib` (hd_reduced.lib plus the new cells, handout section 6), `results/requests/<cell>.json` (overview, Appendix A), and the check that Yosys loads it: 189 + N cell types, every function parses |
| `make table5` | the 6 required designs, both libraries | `results/mapped/<design>_<baseline\|extended>_<A\|B>.v`, `results/mapped/logs/`, `results/table5.csv`, `results/table5_best.csv`; every mapping checked with ABC's `cec` |
| `make demo IN=<file>` | a design | not written yet |

`HD_LIB` defaults to the full HD Liberty in the PDK
(`pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib`).

## 5. Layout

- `src/`: the tool, one module per step (`canon.py`, `hdlib.py`, `contained.py`, ..., `liberty_writer.py`, `check_liberty.py`, `table5.py`); see `docs/interfaces.md`
- `tests/`: the tests; every file runs as a script and with pytest
- `tests/broken/`: the broken cases each check must fail on (never edited to make a test pass)
- `results/`: every table, figure and log the reports use
- `libs/`: the Liberty files the tool writes, and `new_cells.csv`, the cells they add
- `docs/`: `interfaces.md`, and the cell request and response examples (overview, Appendix A)
- `ai/`: AI use log and AI mistakes log
- `report/`: `report.pdf` and `ai_report.pdf` with their sources

## 6. Results

- HD class table: `results/hd_classes.csv`, 258 cells of up to 4 inputs in 56 classes up to input order and 29 up to input order and output inversion.
- Table 1 (baseline areas): not in `results/` yet.
- First Table 5, with the handout's example cell (`dd2_g5__maj4n_1`, estimated area) as the only new cell: `results/table5.csv` and `results/table5_best.csv`. All 24 mappings pass `cec`. Script A never uses the cell (it has an input used twice); script B uses it in dsp8 (8 times) and fir10 (55 times). Best of both, total over the six required designs: 85,779.77 um2 without and 85,797.29 um2 with the cell (-0.02%). The real top candidates replace it next.

## 7. Tests

| Test file | What it checks | Broken case |
| --- | --- | --- |
| `tests/test_canon.py` | input permutation, class IDs, used inputs; 3,904 classes of full-support 4-input functions | |
| `tests/test_hdlib.py` | the Liberty expression parser and the HD class table | |
| `tests/test_contained.py` | the Contained table: nand3 with a pin tied high is nand2, mux2 with its select tied passes one input, a 4-pin cell finds itself, the cheapest drive is kept, the table is closed under input order, the real library | |
| `tests/test_cuts.py` | cut enumeration helpers: dominated cuts are removed, combine respects size limits, duplicates are rejected, and the tiny-cut cases behave as expected | the broken cut cases in `tests/broken/` |
| `tests/test_cut_check.py` | the cut checker accepts a correct truth table and rejects a wrong one | `tests/broken/wrong_cut_tt.json` on `tests/broken/small_aig.aag`: one bit flipped |
| `tests/test_redundancy_check.py` | every HD cell of up to 4 inputs, fed as a candidate, is Exists; the handout's `0x077F` is New | `tests/broken/hd_cell_as_candidate.json`: nand2_1 must be Exists |
| `tests/test_liberty_writer.py` | the request for the handout's example is truth table 0x077F (Appendix A); the cell group equals `given/examples/new_cell_example.lib`; timing senses; `sop` reproduces 305 truth tables; the extended library loads with 190 cell types | `tests/broken/liberty_missing_brace.lib` (not valid Liberty) and `tests/broken/liberty_unknown_pin.lib` (function names a pin the cell lacks: `read_liberty -lib` accepts it, the full read must not) |
| `tests/test_cec.py` | `cec` passes cpu8 mapped with script A | `tests/broken/cec_swapped_gate.json`: one nand2_1 replaced by nor2_1 must fail `cec` |
| `tests/test_table4.py` | the full Table 4 classification counts: 24 Exists, 20 Exists with an inverter, 38 Contained, 3,822 New | the handout's count-based self-check |

The current project passes the implemented milestone checks under `make test`.

## 8. AI use

AGENTS.md · ai/use_log.md · ai/mistakes_log.md · report/ai_report.pdf

## 9. Limitations

- The current milestone checks are implemented and pass, but the end-to-end mapping flow and final reporting deliverables are still downstream work.
- We use Yosys 0.70; the handout used 0.33. Our Table 1 areas differ from the handout's by up to about 4%, and the reduced library costs script A up to about 3% instead of under 0.5%. We are asking the TA which version is graded.
- Yosys's AIG keeps duplicate AND nodes; they must be removed before counting cuts.
- `cec` compares each mapped netlist with the RTL after Yosys synthesis and flip-flop mapping (before ABC), not with the Verilog source directly; flip-flops are matched by order, which holds because they keep their instance names. The gate-level testbenches of Tutorial 4 are not run yet.
- Script A areas differ slightly between machines with the same Yosys version (cpu8: 4,181.51 vs 4,195.27 um2 in `results/table1.csv`); script B areas match. Baseline and extended areas in Table 5 always come from the same run.
- The new cells' capacitance and timing are placeholders (handout section 6); OpenSTA delays are not in Table 5 yet.
- `make all` and `make demo` are still part of the broader pipeline beyond the current milestone checks.

## 10. Third-party files

<file, source, licence>
