#!/bin/bash
# DEV7 (ERRATA4 1a): = DEV6 (fx_dev6: N10 dang giu) + TIER LUOI sim trong rig (L12). So voi DEV6: phai khong doi.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev6; N=DEV7_sim; O=$S/out_dev7
mkdir -p $O
ADD24_SIMTIER=$S/l6/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $O || exit 7
$B/run_ssz.sh $O/$N $FX || exit 8
python3 $B/score_rsim.py $O/$N $FX 20260401 20260615 --quarter 2026Q2 --json $O/$N/score_raw.json > $O/$N/score_raw.txt 2>&1 || exit 9
python3 $B/score_rsim.py $O/$N $FX 20260401 20260615 --quarter 2026Q2 --vtier $S/l6/vtier_dev5.json --json $O/$N/score.json > $O/$N/score.txt 2>&1 || exit 9
python3 $B/gates_rsim.py $O/$N $FX > $O/$N/gates.json || exit 10
python3 $B/classify_sx.py $O/$N $FX 20260401 20260615 sim > $O/$N/classify.txt 2>&1 || exit 11
python3 $B/verdict_e3.py $O/$N $FX > $O/$N/verdict.txt 2>&1 || exit 12
echo DEV7_DONE
