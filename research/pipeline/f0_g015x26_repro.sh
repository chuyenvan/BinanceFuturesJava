#!/bin/bash
# F0 item 3 — tai lap predwf_G015x26 (16 fold DEV) bang predict tu 18 model goc da luu.
# Chay: nohup bash research/pipeline/f0_g015x26_repro.sh > /home/ubuntu/f0_repro/g015x26_repro.out 2>&1 &
set -u
R=/home/ubuntu/src/BinanceFuturesJava
OUT=/home/ubuntu/f0_repro/g015x26_regen
mkdir -p "$OUT"
# 16 cutoff cua predwf_G015x26 = fold 0..15 cua 18 cutoff goc (20220101..20260401)
CUTS="20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 \
      20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001"
i=0
for C in $CUTS; do
  echo "### $(date +%T) fold $i cutoff $C"
  CUTOFF=$C FOLD_IDX=$i OUT="$OUT/predict_wf_${C}.bin" \
    nice -n 10 python3 "$R/research/pipeline/g015x26_train.py" || { echo "ABORT fold $i rc=$?"; exit 1; }
  i=$((i+1))
done
echo "G015X26_REPRO_DONE $(date +%T)"
