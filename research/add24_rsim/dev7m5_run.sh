#!/bin/bash
# LUOT7 EB25 thu BO NHO: fx_dev6 (Q2 day du, END 07-01) + mkt 06-25..06-30 nhung manifest mkt.from = 2026-06-15 07:00 +07 (=> mang
# n_sym x 5 x 16 ngay ~ bang OW1: mkt tu 09-15 07:00 +07 toi END 10-01). Chi kiem bo nho (khong cham).
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev7m5; N=DEV7M5_sim; O=$S/out_dev7
rm -rf $FX; cp -r $S/fx_dev6 $FX; cp $S/mkt_q2e/mkt.csv.gz $FX/mkt.csv.gz
python3 -c "
import json; fx='$FX'; m=json.load(open(fx+'/manifest.json')); m['mkt']={'from': 1781481600000}; json.dump(m, open(fx+'/manifest.json','w'))"
ADD24_SIMTIER=$B/l6_inputs/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $O
grep -c OutOfMemory $O/$N/run.log; grep 'xong' $O/$N/run.log | cut -c1-120
echo DEV7M5_DONE
