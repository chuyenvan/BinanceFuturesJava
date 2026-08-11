#!/bin/bash
cd /home/ubuntu/java/simulator || exit 1
rm -rf /home/ubuntu/claudedata/wfo_ds_oiz75
export WFO_SET_PRED=ai_pred_market_gate_wfo
export WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/predict_wf_oiz75
export WFO_SEL_HORIZON_IDX=0
nohup java -Xmx12g -cp binance-futures-preflight.jar \
  com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset \
  /home/ubuntu/claudedata/wfo_ds_oiz75 \
  > /home/ubuntu/claudedata/export_oiz75.log 2>&1 &
echo "PID=$!"
