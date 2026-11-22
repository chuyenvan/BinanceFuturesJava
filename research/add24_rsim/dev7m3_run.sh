#!/bin/bash
# LUOT7 EB25 thu: DEV7 + mkt toan san 6 ngay UTC 06-25..06-30 (sat END: ReplayData cap phat n_sym x 5 x (END - mkt.from) float) -> rig CO nhanh DCA (gridDue duoc goi).
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev7m; N=DEV7M_sim; O=$S/out_dev7

[ -s $S/mkt_q2e/mkt_manifest.json ] || python3 -I $B/dl_mkt_days.py 2026-06-25,2026-06-26,2026-06-27,2026-06-28,2026-06-29,2026-06-30 $S/mkt_q2e > $B/dl_mkt_q2e.log 2>&1 || exit 1
rm -rf $FX; cp -r $S/fx_dev6 $FX; cp $S/mkt_q2e/mkt.csv.gz $FX/mkt.csv.gz
python3 - <<'PZ'
import json, gzip
fx = '/dev/shm/add24/b/fx_dev7m'; m = json.load(open(fx + '/manifest.json'))
m['mkt'] = {'from': min(int(x.split(',')[1]) for x in gzip.open(fx + '/mkt.csv.gz', 'rt') if not x.startswith('symbol'))}   # = build_fx --mkt (MKT_FROM)
json.dump(m, open(fx + '/manifest.json', 'w'))
PZ
ADD24_SIMTIER=$B/l6_inputs/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $O || exit 7
$B/run_ssz.sh $O/$N $FX || exit 8
python3 $B/score_rsim.py $O/$N $FX 20260401 20260615 --quarter 2026Q2 --vtier $S/l6/vtier_dev5.json --json $O/$N/score.json > $O/$N/score.txt 2>&1 || exit 9
python3 $B/score_rsim.py $O/$N $FX 20260401 20260701 --json $O/$N/score_q2full.json > $O/$N/score_q2full.txt 2>&1 || exit 9
python3 $B/classify_sx.py $O/$N $FX 20260401 20260615 sim > $O/$N/classify.txt 2>&1
python3 $B/verdict_e3.py $O/$N $FX > $O/$N/verdict.txt 2>&1
echo DEV7M_DONE
