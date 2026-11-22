#!/bin/bash
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev2
KL_DIR=$S/kl_dev2 python3 $B/ssz_inputs.py 20260130 20260207 $FX || exit 8
flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh DEV2W $FX $S/out_dev2 || exit 9
$B/run_ssz.sh $S/out_dev2/DEV2W $FX || exit 10
python3 $B/score_rsim.py $S/out_dev2/DEV2W $FX 20260130 20260207 --json $S/out_dev2/DEV2W/score.json || exit 11
python3 $B/gates_rsim.py $S/out_dev2/DEV2W $FX > $S/out_dev2/DEV2W/gates.json
echo DEV2_DONE
