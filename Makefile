# DD2 Project 1: the targets the overview requires (section 5.1).
# Fill in every target; the placeholders fail until you do.

PDK_ROOT ?= $(HOME)/.ciel
GIVEN    ?= ../DD2_Project1_student_pack/given
IN       ?=
HD_LIB ?= pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
export HD_LIB

GROUP ?= b3

.PHONY: setup check test all demo clean aigs table1 hd-table contained-table liberty table5 new-cells cw-setup real-areas greedy docker-images check-cells real-cells real-cells-soft curve sensitivity table5-final table5-real

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
	python3 tests/test_cost.py
	python3 tests/test_liberty_writer.py
	python3 tests/test_cec.py
	python3 tests/test_areamodel.py
	python3 tests/test_sensitivity.py

cuts:             ## step 2: cut counts for every design, before and after ABC
	python3 src/run_cuts.py

candidates:       ## steps 2, 3, 5: classes per design, frequency, Table 3 label
	python3 src/candidates.py

all: aigs table1 hd-table contained-table cuts candidates area-model rank liberty table5 greedy sensitivity real-cells-soft


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

SPICE ?= pdk/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice

area-model:       ## step 6: area model fitted on HD x1 cells, with its error
	python3 src/areamodel.py $(HD_LIB) $(SPICE)


rank:             ## step 7: rank candidates by estimated saving
	python3 src/rank.py

N     ?= 5

new-cells:        ## the top N ranked candidates as new cells: make new-cells GROUP=<group number> N=5
	@test -n "$(GROUP)" || (echo "usage: make new-cells GROUP=<group number> [N=5]" && exit 1)
	python3 src/liberty_writer.py --from-ranked results/ranked.csv $(N) $(GROUP) libs/new_cells.csv


liberty:          ## step 8: top ranked candidates -> extended Liberty + requests
	python3 src/liberty_writer.py --from-ranked results/ranked.csv 5 $(GROUP) libs/new_cells.csv
	python3 src/liberty_writer.py libs/new_cells.csv given/hd_reduced.lib libs/hd_extended.lib results/requests
	python3 src/check_liberty.py libs/hd_extended.lib 194

table5:           ## step 9: 32 mappings with cec -> Table 5
	python3 src/table5.py

table5-final:     ## Table 5 for the final greedy cells, estimated areas -> results/final_estimated
	python3 src/liberty_writer.py libs/final_estimated.csv given/hd_reduced.lib libs/hd_final_estimated.lib results/requests_final
	python3 src/check_liberty.py libs/hd_final_estimated.lib 199
	python3 src/table5.py libs/hd_final_estimated.lib results/final_estimated

table5-real:      ## Table 5 for the final greedy cells, real areas -> results/final_real
	python3 scripts/final_real_areas.py libs/final_estimated.csv results/real_areas.csv libs/final_real.csv
	python3 src/liberty_writer.py libs/final_real.csv given/hd_reduced.lib libs/hd_final_real.lib build/requests_real
	python3 src/check_liberty.py libs/hd_final_real.lib 199
	python3 src/table5.py libs/hd_final_real.lib results/final_real

greedy:           ## step 10: greedy selection on script B, on estimated and on real areas (about 15 minutes)
	python3 -u src/greedy.py estimated > results/greedy_estimated.txt
	python3 -u src/greedy.py real > results/greedy_real.txt

sensitivity:      ## step 12: the first greedy cell 30% smaller in the Liberty, script B -> results/sensitivity.csv
	python3 src/sensitivity.py

cw-setup:         ## step 11, once: check out the cell generator and make its Python 3.12 environment (needs network)
	git submodule update --init cellweaver
	python3.12 -m venv build/cwvenv
	build/cwvenv/bin/pip install -r cellweaver/requirements.lock

real-areas:       ## step 11: real area of every ranked candidate from the generator -> results/real_areas.csv (needs make cw-setup)
	python3 scripts/real_areas.py

docker-images:    ## step 11: the course image and the generator image (needs Docker and network; about 10 minutes the first time)
	docker build -t dd2-layout-tools $(GIVEN)/../container
	docker build -t dd2-cellweaver -f docker/cellweaver.Dockerfile cellweaver

check-cells:      ## step 11: the generator's own checks (DRC, LVS, simulation) on the final set -> results/real_cell_checks.csv
	python3 scripts/check_cells.py libs/final_estimated.csv results/real_cell_checks.csv

real-cells:       ## step 11 in full, from nothing: generator, real areas, images, checks
	$(MAKE) cw-setup real-areas docker-images check-cells

real-cells-soft:  ## part of make all: runs the checks if Docker and the generator are there, otherwise says it skipped them
	@if docker info >/dev/null 2>&1 && [ -d cellweaver/scl_gen ]; then \
		$(MAKE) docker-images check-cells; \
	else \
		echo "SKIPPED check-cells: needs Docker and the cellweaver submodule (make cw-setup). Verdicts of the tagged run: results/real_cell_checks.csv"; \
	fi

curve: 
	python3 -u src/curve.py estimated
	python3 -u src/curve.py estimated_real
	python3 -u src/curve.py real
delays:           ## worst path delay of every mapped netlist with OpenSTA -> results/delays.csv (needs make docker-images)
	python3 scripts/sta_delay.py
