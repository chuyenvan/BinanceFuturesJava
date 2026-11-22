#!/bin/bash
# DEV6 (ERRATA3 B1-B4): luot 2 cua DEV5b (lane sim): N10 = dang giu (xoa nen symbol N10 trong khoang sim giu) roi S-G2 THO + doc S-X moi + N11.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b
python3 $B/n10_held.py $S/out_dev5/DEV5b_sim $S/fx_dev5 $S/fx_dev6 || exit 1
mkdir -p $S/out_dev6; N=DEV6_sim
ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $S/fx_dev6 $S/out_dev6 || exit 7
$B/run_ssz.sh $S/out_dev6/$N $S/fx_dev6 || exit 8
python3 $B/score_rsim.py $S/out_dev6/$N $S/fx_dev6 20260401 20260615 --quarter 2026Q2 --json $S/out_dev6/$N/score.json > $S/out_dev6/$N/score.txt 2>&1 || exit 9
python3 $B/gates_rsim.py $S/out_dev6/$N $S/fx_dev6 > $S/out_dev6/$N/gates.json || exit 10
python3 $B/classify_sx.py $S/out_dev6/$N $S/fx_dev6 20260401 20260615 sim > $S/out_dev6/$N/classify.txt 2>&1 || exit 11
python3 $B/verdict_e3.py $S/out_dev6/$N $S/fx_dev6 > $S/out_dev6/$N/verdict.txt 2>&1 || exit 12
echo DEV6_DONE
