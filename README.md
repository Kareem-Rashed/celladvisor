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
| `make demo IN=<file>` | a design | not written yet |

`HD_LIB` defaults to the full HD Liberty in the PDK
(`pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib`).

## 5. Layout

- `src/`: the tool, one module per step (`canon.py`, `hdlib.py`, `contained.py`); see `docs/interfaces.md`
- `tests/`: the tests; every file runs as a script and with pytest
- `tests/broken/`: the broken cases each check must fail on (never edited to make a test pass)
- `results/`: every table, figure and log the reports use
- `libs/`: the Liberty files the tool writes
- `docs/`: `interfaces.md`, and the cell request and response examples (overview, Appendix A)
- `ai/`: AI use log and AI mistakes log
- `report/`: `report.pdf` and `ai_report.pdf` with their sources

## 6. Results

- HD class table: `results/hd_classes.csv`, 258 cells of up to 4 inputs in 56 classes up to input order and 29 up to input order and output inversion.
- Table 1 (baseline areas): not in `results/` yet.
- Redundancy report, area model, Table 5: not done yet.

## 7. Tests

| Test file | What it checks | Broken case |
| --- | --- | --- |
| `tests/test_canon.py` | input permutation, class IDs, used inputs; 3,904 classes of full-support 4-input functions | |
| `tests/test_hdlib.py` | the Liberty expression parser and the HD class table | |
| `tests/test_contained.py` | the Contained table: nand3 with a pin tied high is nand2, mux2 with its select tied passes one input, a 4-pin cell finds itself, the cheapest drive is kept, the table is closed under input order, the real library | |
| `tests/test_cuts.py` | cut enumeration helpers: dominated cuts are removed, combine respects size limits, duplicates are rejected, and the tiny-cut cases behave as expected | the broken cut cases in `tests/broken/` |
| `tests/test_cut_check.py` | the cut checker accepts a correct truth table and rejects a wrong one | `tests/broken/wrong_cut_tt.json` on `tests/broken/small_aig.aag`: one bit flipped |
| `tests/test_redundancy_check.py` | every HD cell of up to 4 inputs, fed as a candidate, is Exists; the handout's `0x077F` is New | `tests/broken/hd_cell_as_candidate.json`: nand2_1 must be Exists |
| `tests/test_table4.py` | the full Table 4 classification counts: 24 Exists, 20 Exists with an inverter, 38 Contained, 3,822 New | the handout's count-based self-check |

The current project passes the implemented milestone checks under `make test`.

## 8. AI use

AGENTS.md · ai/use_log.md · ai/mistakes_log.md · report/ai_report.pdf

## 9. Limitations

- The current milestone checks are implemented and pass, but the end-to-end mapping flow and final reporting deliverables are still downstream work.
- We use Yosys 0.70; the handout used 0.33. Our Table 1 areas differ from the handout's by up to about 4%, and the reduced library costs script A up to about 3% instead of under 0.5%. We are asking the TA which version is graded.
- Yosys's AIG keeps duplicate AND nodes; they must be removed before counting cuts.
- `make all` and `make demo` are still part of the broader pipeline beyond the current milestone checks.

## 10. Third-party files

<file, source, licence>
