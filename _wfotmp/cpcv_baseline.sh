#!/bin/bash
# Baseline Oracle (K=8, recipe FROZEN) — 16 cell doi chieu parity voi Kaggle.
pkill -9 -f CpcvBatchRunner 2>/dev/null || true
sleep 3
cd /home/ubuntu/cpcv || exit 1
head -16 wf_full/cells.jsonl > baseline_cells.jsonl
rm -f baseline_oracle.jsonl
cd /home/ubuntu/cpcv/run || exit 1
export CPCV_CELLS=/home/ubuntu/cpcv/baseline_cells.jsonl
export CPCV_OUT=/home/ubuntu/cpcv/baseline_oracle.jsonl
export WFO_DATA_DIR=/home/ubuntu/wfo_ds_VAL
export WFO_SMART_CACHE=1
export SELECTOR_RANK_TOPK=8
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp /home/ubuntu/java/cpcv.jar com.binance.chuyennd.ai_ml.wfo.CpcvBatchRunner
echo "BASELINE_DONE rc=$?"
