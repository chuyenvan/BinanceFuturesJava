#!/usr/bin/env bash
# Chay VerifyOneWindow TUAN TU cho 10 window NHE (0,1,2,4,5,6,7,11,13,14) tren Oracle,
# doc ticker tu Aerospike LOCAL (config.properties CE_SIM_CWD: TICKER_SOURCE=aerospike,
# AEROSPIKE_HOST_226=127.0.0.1) - KHONG dung ticker file da hong. TS_RATCHET_DECOUPLED=true,
# thay the WfoWorker/fanout dang bug (xem EXIT_MACHINE PHAN 5).
set -x
cd /home/ubuntu/java/simulator
JAR=/home/ubuntu/java/simulator/binance-exit003-20260730.jar
for w in 0 1 2 4 5 6 7 11 13 14; do
  echo "=== BAT DAU window $w ==="
  WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff \
  WFO_N_SAMPLES=30 WFO_SEED_BASE=42 WFO_MAX_OOS_DATE=20260101 \
  TS_RATCHET_DECOUPLED=true \
  java -Xmx8g -cp "$JAR" com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow "$w"
  echo "=== KET THUC window $w rc=$? ==="
done
echo DONE_ALL_LIGHT
