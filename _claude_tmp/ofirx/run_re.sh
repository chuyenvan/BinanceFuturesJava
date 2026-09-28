#!/bin/bash
W=/home/ubuntu/claude_audit_0928/ofirx
R=/home/ubuntu/src/BinanceFuturesJava
cd $R
KD=$W/kout42,$W/kout43,$W/kout44,$W/kout45
echo "=== RE orient +1 (tai lap)"; date
nice -n 10 python3 research/analysis/ofi_money_score_v2.py --kdirs $KD --orient 1 --out $W/ofi_money_orient_p1.json > $W/re_p1.log 2>&1; echo rc=$?
echo "=== RE orient -1"; date
nice -n 10 python3 research/analysis/ofi_money_score_v2.py --kdirs $KD --orient -1 --out $W/ofi_money_reorient.json > $W/re_m1.log 2>&1; echo rc=$?
echo "=== trades +1 compare"; date
nice -n 10 python3 research/analysis/ofi_ext_trades_build.py --kdirs $W/kout43,$W/kout44,$W/kout45 --orient 1 --out $W/ofi_ext_trades_p1.parquet --compare $W/exttrades_old/ofi_ext_trades.parquet > $W/tr_p1.log 2>&1; echo rc=$?
echo "=== trades -1"; date
mkdir -p $W/ds_reorient
nice -n 10 python3 research/analysis/ofi_ext_trades_build.py --kdirs $W/kout43,$W/kout44,$W/kout45 --orient -1 --out $W/ds_reorient/ofi_ext_trades.parquet > $W/tr_m1.log 2>&1; echo rc=$?
date; echo ALLDONE
