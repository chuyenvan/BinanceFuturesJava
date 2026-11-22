#!/bin/bash
# LUOT6 1a: DEV-2 lai voi TIER LUOI sim trong rig (L12). FX = fx_dev2 (giu nguyen). Lane sim.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev2; N=DEV2T
ADD24_SIMTIER=$S/l6/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $S/out_dev2 || exit 9
$B/run_ssz.sh $S/out_dev2/$N $FX || exit 10
python3 $B/score_rsim.py $S/out_dev2/$N $FX 20260130 20260207 --json $S/out_dev2/$N/score.json > $S/out_dev2/$N/score.txt 2>&1 || exit 11
echo DEV2T_DONE
