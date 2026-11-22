#!/bin/bash
# LUOT7 EB25 thu: DEV7 + mkt toan san LOC phut gia cham bac (mkt_filter.py) 06-05..06-08 UTC (SLX/OPN gia cham bac) -> rig CO nhanh DCA (gridDue duoc goi).
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev7m; N=DEV7M_sim; O=$S/out_dev7

grep -q 'mkt days=' $B/dl_mkt_q2t.log || exit 1
rm -rf $FX; cp -r $S/fx_dev6 $FX; cp $S/mkt_q2t/mkt_f.csv.gz $FX/mkt.csv.gz
ADD24_SIMTIER=$B/l6_inputs/simtier_code.csv ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $O || exit 7
$B/run_ssz.sh $O/$N $FX || exit 8
python3 $B/score_rsim.py $O/$N $FX 20260401 20260615 --quarter 2026Q2 --vtier $S/l6/vtier_dev5.json --json $O/$N/score.json > $O/$N/score.txt 2>&1 || exit 9
python3 $B/score_rsim.py $O/$N $FX 20260401 20260701 --json $O/$N/score_q2full.json > $O/$N/score_q2full.txt 2>&1 || exit 9
python3 $B/classify_sx.py $O/$N $FX 20260401 20260615 sim > $O/$N/classify.txt 2>&1
python3 $B/verdict_e3.py $O/$N $FX > $O/$N/verdict.txt 2>&1
echo DEV7M_DONE
