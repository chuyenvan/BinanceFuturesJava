#!/bin/bash
# HO4-P3 cong K-a/K-b (ADDENDUM-5 §5.3): Vision klines 1m vs ticker DEV, theo thang (RAM thap). Tach nen.
cd /home/ubuntu/claude_master/1010/ho4
mkdir -p k
P=/home/ubuntu/src/BinanceFuturesJava/research/analysis/ho3_b2_kline_vision.py
for pr in "20250701 20250801" "20250801 20250901" "20250901 20251001" "20251001 20251101" "20251101 20251201" "20251201 20260101"; do
  set -- $pr
  [ -s k/k_$1.json ] && continue
  python3 $P --ref ticker --lo $1 --hi $2 --out k/k_$1.json > k/k_$1.log 2>&1
done
echo K_DONE > k/DONE
