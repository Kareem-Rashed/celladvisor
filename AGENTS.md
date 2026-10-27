# Instructions for the AI assistant

Written before any code and committed first (overview, section 4.1).

## The project
celladvisor is our tool for DD2 Project 1, Option 2 (CSCE 3304, Fall 2026). It reads each synthesized design as an and-inverter graph (Yosys, `write_aiger`), enumerates cuts of up to 4 inputs with a truth table for each, classifies the truth tables up to input order and output inversion (and counts NPN classes for comparison), costs each class as a CMOS cell, checks every candidate against the full sky130_fd_sc_hd library, estimates the area of the missing cells with a model fitted to HD's own cells, writes cell requests (overview, Appendix A) and an extended Liberty file, and measures the area of every design with Yosys and ABC. It is written in Python 3.11 and calls Yosys, ABC, Icarus Verilog and OpenSTA. AI is used as a development aid only: no AI model runs when the tool runs.

## How this project is checked
- `make check`: tool versions, the PDK link and the given-file links.
- `make test`: every test, including the broken cases in `tests/broken/`:
  - each cut's truth table matches a simulation of its logic over every input combination;
  - every combinational HD cell, fed to the redundancy checker as a candidate, comes out as Exists;
  - over the 3,904 classes of 4-input functions that depend on all four inputs, the checker reproduces Table 4 of the Option 2 handout exactly: 24 Exists, 20 Exists with an inverter, 38 Contained, 3,822 New;
  - every Liberty file we write loads in Yosys with `read_liberty -lib` and reports 189 plus the number of new cells;
  - every mapped netlist passes ABC's `cec` against the RTL.
- `make all`: the whole flow from a clean checkout.

## Rules the assistant follows (overview, section 4.3)
1. Pass or fail comes from the check scripts, never from the assistant's opinion.
2. Every number in a report or the README comes from a file the flow wrote in `results/`. Design rule values come from the PDK, never from the assistant.
3. Every check has a broken case in `tests/broken/` that it must fail on.
4. The assistant never changes the check scripts, the broken cases or the PDK.
5. Truth tables are integers where bit i is the output for the input combination in which input k equals bit k of i, so A is the least significant input (overview, Appendix A). Never change this convention.
6. The same input always gives the same output: no network access, no model calls and no unseeded randomness at run time.
7. Every mapping uses the commands of the Option 2 handout, section 2 (`given/scripts/map.sh`), with only the library changed, and with both script A and script B.
8. The baseline for every area comparison is `hd_reduced.lib`. Redundancy checks use the full HD Liberty, all drives and all kinds.

## What the assistant must never do
- Edit anything in `tests/broken/`, the check scripts, `given/` or `pdk/`.
- Weaken, skip or loosen a check, or change an expected count or tolerance, to make a test pass.
- Invent a number, or copy a number into a report that no file in `results/` contains.
- Create, move or delete the tags `cp1`, `cp2` or `final`, push, or rewrite git history, unless a group member asks for that exact action.
- Commit the PDK, copies of the given files, build trees, or any file over 50 MB.

## Conventions
- Code in `src/celladvisor/`, tests in `tests/`, generated tables, figures and logs in `results/`, generated Liberty files in `libs/`.
- One Make target or command per step of section 4 of the Option 2 handout.
- Python 3.11, standard library first; any new dependency goes in `requirements.txt`.
- Each group member commits under their own name. Every AI-assisted commit ends with the trailer `AI-assisted: <tool>/<model>`.
- Every AI interaction whose output we kept is logged in `ai/use_log.md`, and every AI mistake our checks caught is logged in `ai/mistakes_log.md`.

## Current layout (added 2026-10-27, Joshua)
- The code lives directly in `src/` (for example `src/canon.py`), not in `src/celladvisor/` as the Conventions section above says. Follow the repository as it is.
- Before calling or writing another member's module, read `docs/interfaces.md`: it lists every public function, its owner, the shared truth-table convention, and the interfaces the existing broken-case tests expect (`redundancy.classify`, `cuts.verify_cut`). Update it when you add or change a public function.
