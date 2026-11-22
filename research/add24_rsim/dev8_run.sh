#!/bin/bash
# LUOT8 DEV8: fx_dev6 (Q2 day du, N10 dang giu, ssz_inputs_l7) + mkt toan san LOC phut gia sim cham bac (SLX/OPN, 06-04..06-12 UTC) + L12 tier luoi.
# Bo cham moi: score_rsim (R1 R2 R6) + classify_sx + verdict_rsim (R7). Lane sim.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev8; N=DEV8_sim; O=$S/out_dev8
mkdir -p $O; rm -rf $FX; cp -r $S/fx_dev6 $FX
python3 -I $B/mkt_filter.py $S/mkt_q2t/mkt.csv.gz $S/l7/pricedue_q2.csv $FX/mkt.csv.gz 1780531200000 1781308800000 20000000 > $FX/mkt_filter.json || exit 1
python3 - <<'PZ'
import json, gzip
fx = '/dev/shm/add24/b/fx_dev8'; m = json.load(open(fx + '/manifest.json'))
m['mkt'] = {'from': min(int(x.split(',')[1]) for x in gzip.open(fx + '/mkt.csv.gz', 'rt') if not x.startswith('symbol'))}   # = build_fx --mkt
json.dump(m, open(fx + '/manifest.json', 'w')); print('mkt.from', m['mkt'])
PZ
ADD24_SIMTIER=$B/l6_inputs/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $O || exit 7
$B/run_ssz.sh $O/$N $FX || exit 8
python3 $B/score_rsim.py $O/$N $FX 20260401 20260615 --quarter 2026Q2 --vtier $S/l6/vtier_dev5.json --json $O/$N/score.json > $O/$N/score.txt 2>&1 || exit 9
python3 $B/gates_rsim.py $O/$N $FX > $O/$N/gates.json || exit 10
python3 $B/classify_sx.py $O/$N $FX 20260401 20260615 sim > $O/$N/classify.txt 2>&1 || exit 11
python3 $B/verdict_rsim.py $O/$N $FX $S/l6/vtier_dev5.json > $O/$N/verdict_rsim.txt 2>&1 || exit 12
echo DEV8_DONE
