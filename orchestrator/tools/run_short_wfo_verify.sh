#!/bin/bash
# RUNBOOK — SHORT-WFO function-test (jobstore-free, 1 window). CHAY TREN ORACLE.
# ⚠️ CHI chay khi Oracle RANH RAM (>=14G available) — export -Xmx12g + verify se dung nhieu RAM.
#    KHONG chay khi con WfoWorker cua agent khac dang chay (dung `pgrep -af WfoWorker` kiem tra truoc).
# Tien dieu kien DA LAM san (agent short prep):
#   - jar short: /home/ubuntu/java/simulator/preflight-v42-short.jar (Java byte-identical df542c5, ENABLE_SHORT wired)
#   - predict_wf_short: /home/ubuntu/claudedata/predict_wf_short (14 window, score=1-ps trong Java)
set -e
JAR=/home/ubuntu/java/simulator/preflight-v42-short.jar
DS=/home/ubuntu/claudedata/wfo_ds_short
PRED=/home/ubuntu/claudedata/predict_wf_short
TICKER=/home/ubuntu/java/simulator/kaggle_data_hpo/daily/
WIN=${1:-4}   # 4 = 2024Q1 (win index tu FIRST_OOS=202301, OOS 3 thang)

echo "== guard: khong duoc co WfoWorker khac =="
pgrep -af WfoWorker && { echo "ABORT: WfoWorker dang chay — cho xong roi hay chay."; exit 1; } || true

echo "== [1] BUILD DATASET SHORT (ExportWfoDataset) =="
cd /home/ubuntu/java/simulator
WFO_SET_PRED=ai_pred_market_gate_wfo WFO_FUNDING_PRED_DIR=$PRED WFO_SEL_HORIZON_IDX=0 \
  java -Xmx12g -cp $JAR com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS
echo "== dataset san: =="; du -sh $DS; ls $DS | head

echo "== [2] VERIFY ONE WINDOW (short, win=$WIN) =="
cd /home/ubuntu/java/simulator
ENABLE_SHORT=1 WFO_DISABLE_DCA=1 SHORT_SL_PCT=0.25 SHORT_TIME_STOP_HOURS=24 \
  WFO_LOG_ENTRIES=1 TICKER_SOURCE=file WFO_DATA_DIR=$DS \
  java -Xmx8g -cp $JAR com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow $WIN 2>&1 | tee /tmp/verify_short_w${WIN}.log

echo "== KIEM TRA =="
echo "-- so ENTRY_DUMP ... PREDICT_SYMBOL_TRADE (entry short SELL) --"
grep -c "ENTRY_DUMP" /tmp/verify_short_w${WIN}.log || true
grep "RESULT_JSON" /tmp/verify_short_w${WIN}.log | tail -1
echo "(⚠️ REVIEW-POINT: P(HIT_short) max=0.666, entry gate maxThres≈0.321 -> can ps>=0.68 -> co the 0 entry;"
echo " neu oosTrades≈0 => can chinh gate/score-map cho thang do ps thap cua short.)"
