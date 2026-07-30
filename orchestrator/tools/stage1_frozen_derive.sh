#!/bin/bash
# stage1_frozen_derive.sh — Stage-1 of "frozen leakage-free genome" experiment (R-vs-M, Probe C step-2).
# Derive a PRE-2023 genome: run HPO N=30 on w0-w3 ONLY, rank-K8, DCA off, on the -ff leak-free dataset.
# MOM15 NOT pinned here (HPO explores range [0.010,0.045]). Funding fee OFF (matches Probe C harness baseline).
# Detached via `ce bg_run`. Markers: STAGE1_WIN_START <w> / STAGE1_WIN <w> rc=.. RESULT_JSON.. / STAGE1_DONE / STAGE1_ERROR.
# After DONE: derive element-wise MEDIAN of the 4 bestGenome vectors, FORCE MIN_MOMENTUM_15M=0.010 -> frozen CSV.
set -u
JAR=/home/ubuntu/java/simulator/binance-lf-frozen-1.0.0.jar
DS=wfo_ds_ret2wf_4h_ff
OUT=/home/ubuntu/claudedata/.run/stage1_frozen.log
mkdir -p /home/ubuntu/claudedata/.run
cd /home/ubuntu/java/simulator || { echo "STAGE1_ERROR cd fail"; exit 1; }
: > "$OUT"
echo "STAGE1_BEGIN jar=$JAR ds=$DS $(date -u +%FT%TZ)" | tee -a "$OUT"
for W in 0 1 2 3; do
  echo "STAGE1_WIN_START $W $(date -u +%FT%TZ)" | tee -a "$OUT"
  WFO_N_SAMPLES=30 SELECTOR_RANK_TOPK=8 WFO_DISABLE_DCA=1 \
    TICKER_SOURCE=file WFO_DATA_DIR=$DS \
    java -Xmx8g -cp "$JAR" com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow "$W" \
    > /tmp/stage1_w${W}.log 2>&1
  RC=$?
  RJ=$(grep -a "RESULT_JSON" /tmp/stage1_w${W}.log | tail -1 | grep -ao 'RESULT_JSON {.*}')
  echo "STAGE1_WIN $W rc=$RC $RJ" | tee -a "$OUT"
  if [ "$RC" -ne 0 ] || [ -z "$RJ" ]; then echo "STAGE1_ERROR win $W rc=$RC (see /tmp/stage1_w${W}.log)" | tee -a "$OUT"; fi
done
echo "STAGE1_DONE $(date -u +%FT%TZ)" | tee -a "$OUT"
