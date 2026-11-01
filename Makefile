# DD2 Project 1: the targets the overview requires (section 5.1).
# Fill in every target; the placeholders fail until you do.

PDK_ROOT ?= $(HOME)/.ciel
GIVEN    ?= ../DD2_Project1_student_pack/given
IN       ?=
HD_LIB ?= pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
export HD_LIB

.PHONY: setup check test all demo clean aigs table1 hd-table contained-table

setup:            ## environment, and links to the PDK and the given files
	ln -sfn $(PDK_ROOT)/sky130A pdk
	ln -sfn $(GIVEN) given
	@echo "add your own setup steps here"

check:            ## tool versions, PDK, and the ngspice stress test for Option 1
	@test -d pdk || (echo "pdk link missing: run make setup" && exit 1)
	@test -f given/hd_reduced.lib || (echo "given files missing: run make setup" && exit 1)
	yosys -V
	iverilog -V | head -1
	python3 --version
	@# Option 1: run the ngspice stress test inside the course image:
	@#   /opt/dd2/stress_test/check_stress.sh   (from the student pack's container/ folder)

test:             ## every test, including the broken cases in tests/broken/
	python3 tests/test_aig_reader.py
	python3 tests/test_canon.py
	python3 tests/test_hdlib.py
	python3 tests/test_contained.py
	python3 tests/test_cuts.py
	python3 tests/test_cut_check.py
	python3 tests/test_redundancy_check.py
	python3 tests/test_table4.py

cuts:             ## step 2: cut counts for every design, before and after ABC
	python3 src/run_cuts.py

all: aigs table1 hd-table contained-table   ## the flow so far, one target per step

aigs:             ## step 1: AIGs of every required design, raw / strash / after ABC
	bash scripts/aigs.sh

table1:           ## handout Table 1: areas on the usable and reduced libraries
	bash scripts/table1.sh

demo:             ## what the interview runs: make demo IN=<request or design>
	@test -n "$(IN)" || (echo "usage: make demo IN=<request or design>" && exit 1)
	@echo "not written yet" && exit 1

clean:
	rm -rf build

hd-table:
	python3 src/hdlib.py $(HD_LIB) results/hd_classes.csv

contained-table:
	python3 src/contained.py $(HD_LIB) results/contained_table.csv	

