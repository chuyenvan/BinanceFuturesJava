#!/usr/bin/env bash
# Run mot sim devrun. Dung: run_one.sh <TAG> <PROFILE> [SIM_MS_DOWN_BIG_AVG]
set -uo pipefail
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
DS=/home/ubuntu/wfo_ds_x1_2021

TAG="${1:?tag}"; PROF="${2:?profile}"
OVR="${3:-}"

D=$B/$TAG
mkdir -p "$D/storage" "$D/logs"
cd "$D" || exit 2
cp -f "$R/configs/sim_dev_file_2021.properties" config.properties
ln -sfn /home/ubuntu/java/simulator/kaggle_data_hpo kaggle_data_hpo
rm -f storage/*

if [ -n "$OVR" ]; then
  # clone profile + them SIM_MS_DOWN_BIG_AVG
  cp -f "$PROF" profile.properties
  echo "SIM_MS_DOWN_BIG_AVG=$OVR" >> profile.properties
  PROF="$D/profile.properties"
fi

env WFO_DATA_DIR="$DS" WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
  EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE="$PROF" \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp "$JAR" \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
echo "RC=$?"
