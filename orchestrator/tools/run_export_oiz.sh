#!/bin/bash
# Build WFO dataset voi funding selector = predict_wf_oiz (oi_z veto long).
# Chay qua CE bg_run tren Oracle. WFO_SEL_HORIZON_IDX=0 (p6 pack vao ca 4 slot nen horizon nao cung = p6).
set -e
cd /home/ubuntu/java/simulator
WFO_SET_PRED=ai_pred_market_gate_wfo \
WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/predict_wf_oiz \
WFO_SEL_HORIZON_IDX=0 \
java -Xmx12g -cp binance-futures-preflight.jar \
  com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset \
  /home/ubuntu/claudedata/wfo_ds_oiz
