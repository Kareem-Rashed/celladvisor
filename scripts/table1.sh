#!/bin/bash
# Table 1 of the Option 2 handout: map each required design onto the usable and
# reduced HD libraries with scripts A and B, and compare with the handout.
set -e

DESIGNS="cpu8:cpu8 dsp8:dsp8 arlet6502:cpu uart_apb:uart_apb_master risc8:cpu fir10:fir10"
CSV=results/table1.csv
HANDOUT=scripts/table1_handout.csv
mkdir -p results

echo "design,top,script,library,area_um2,handout_um2,diff_pct" > $CSV

for pair in $DESIGNS; do
    design=${pair%%:*}
    top=${pair##*:}
    for script in A B; do
        for lib in usable reduced; do
            echo "$design $script $lib"
            area=$(sh given/scripts/map.sh given/designs/$design.v $top given/hd_$lib.lib $script | grep "Chip area" | awk '{print $NF}')
            [ -n "$area" ] || { echo "no area for $design $script $lib"; exit 1; }
            handout=$(grep "^$design,$script,$lib," $HANDOUT | cut -d, -f4)
            diff=$(awk -v a=$area -v h=$handout 'BEGIN { printf "%.2f", (a - h) / h * 100 }')
            echo "$design,$top,$script,$lib,$area,$handout,$diff" >> $CSV
        done
    done
done
