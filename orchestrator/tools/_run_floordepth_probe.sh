#!/usr/bin/env bash
# Đo ĐỘ SÂU PHAO (spec §0.1) — đường "hồi theo độ sâu" khử survivorship.
# Chạy MaeDistributionProbe trên dữ liệu PACKED (market.bin, có sẵn trên Oracle),
# KHÔNG cần ticker thô (đã bị dọn). DCA-off => mỗi cụm = 1 leg đơn => recovery-by-depth
# là của ENTRY ĐƠN, không bị DCA làm nhiễu. SIM_TREAT_ZERO_VOL_AS_DELIST => delist tính là KHÔNG hồi.
# Chạy trên Oracle (đã scp tới /home/ubuntu/claudedata/.run/).
set -uo pipefail
JAR=/home/ubuntu/java/simulator/gatecount.jar
DS=/home/ubuntu/claudedata/wfo_ds_oiz75
LOG=/home/ubuntu/claudedata/.run/floordepth_probe.log
cd /home/ubuntu/java/simulator
WFO_DATA_DIR="$DS" TICKER_SOURCE=file WFO_DISABLE_DCA=1 SIM_TREAT_ZERO_VOL_AS_DELIST=true \
  MAE_FROM=20210101 MAE_TO=20260501 \
  java -Xmx8g -cp "$JAR" com.binance.chuyennd.ai_ml.wfo.framework.tasks.MaeDistributionProbe \
  > "$LOG" 2>&1
echo "PROBE_DONE rc=$? -> $LOG"
