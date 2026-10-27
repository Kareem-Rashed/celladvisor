#!/bin/bash
# Step 1: write each required design as an AIG three ways (raw Yosys, ABC strash,
# ABC strash+dch) and record each graph's size in results/aig_sizes.csv.
set -e

DESIGNS="cpu8:cpu8 dsp8:dsp8 arlet6502:cpu uart_apb:uart_apb_master risc8:cpu fir10:fir10"
OUT=build/aig
CSV=results/aig_sizes.csv
mkdir -p $OUT results

to_ascii() {
    yosys -q -p "read_aiger $1.aig; simplemap; write_aiger -ascii $1.aag"
}

# Outputs are left out: converting ABC's binary files with Yosys merges some
# output ports (dsp8 26 -> 25, risc8 83 -> 72); ANDs and latches stay exact.
echo "design,graph,inputs,latches,ands" > $CSV

for pair in $DESIGNS; do
    design=${pair%%:*}
    top=${pair##*:}
    echo "$design"

    yosys -q -p "read_verilog given/designs/$design.v; synth -flatten -top $top; async2sync; dffunmap; aigmap; write_aiger -ascii $OUT/${design}_raw.aag; write_aiger $OUT/${design}_raw.aig"
    yosys-abc -c "read_aiger $OUT/${design}_raw.aig; strash; write_aiger $OUT/${design}_strash.aig" > /dev/null
    yosys-abc -c "read_aiger $OUT/${design}_raw.aig; strash; dch; strash; write_aiger $OUT/${design}_abc.aig" > /dev/null
    to_ascii $OUT/${design}_strash
    to_ascii $OUT/${design}_abc

    for graph in raw strash abc; do
        read -r _ _ inputs latches _ ands < $OUT/${design}_$graph.aag
        echo "$design,$graph,$inputs,$latches,$ands" >> $CSV
    done
done
