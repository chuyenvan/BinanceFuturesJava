#!/bin/bash
# LUOT7 EB25 thu nhanh DCA: ban sao fx_dev6, END = 2026-06-13 00:00 +07 (rut ngan de ReplayData.loadMkt vua Xmx3g: n_sym x 5 x (END - mkt.from) float),
# mkt toan san 9 ngay UTC 06-04..06-12 (SLX 06-02 / OPN 06-06 gia cham bac + thi truong BIG_DOWN/alt 06-06 01:53, 06-09 09:20 theo market.bin sim).
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev7m4; N=DEV7M4_sim; O=$S/out_dev7
rm -rf $FX; cp -r $S/fx_dev6 $FX; cp $S/mkt_q2t/mkt.csv.gz $FX/mkt.csv.gz
python3 - <<'PZ'
import json, gzip
fx = '/dev/shm/add24/b/fx_dev7m4'; m = json.load(open(fx + '/manifest.json'))
m['mkt'] = {'from': min(int(x.split(',')[1]) for x in gzip.open(fx + '/mkt.csv.gz', 'rt') if not x.startswith('symbol'))}
m['END'] = 1781283600000; m['END_DATA'] = 1781283600000
json.dump(m, open(fx + '/manifest.json', 'w')); print('manifest', m['mkt'], m['END'])
PZ
ADD24_SIMTIER=$B/l6_inputs/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $O || exit 7
python3 $B/score_rsim.py $O/$N $FX 20260401 20260613 --vtier $S/l6/vtier_dev5.json --json $O/$N/score.json > $O/$N/score.txt 2>&1 || exit 9
python3 $B/score_rsim.py $O/$N $FX 20260401 20260613 --json $O/$N/score_novtier.json > $O/$N/score_novtier.txt 2>&1 || exit 9
echo DEV7M4_DONE
