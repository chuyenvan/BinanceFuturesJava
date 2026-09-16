#!/bin/bash
# Run ONE BD-SIZE-ADAPT variant (docs/PREREG_BD_SIZE_ADAPT.md). Usage: run_one.sh TAG PROFILE
set -u
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
CFG=$R/configs/sim_dev_file_2021.properties
DS=/home/ubuntu/wfo_ds_x1_2021
B=/home/ubuntu/java/devrun
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
TAG=$1; PROF=$2; D=$B/$TAG
mkdir -p $D/storage $D/logs; cd $D; cp -f $CFG config.properties; rm -f storage/*
ln -sfn $TICK kaggle_data_hpo
echo "### $(date +%T) RUN $TAG prof=$PROF"
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
  EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
echo "$TAG rc=$?"
grep -a '\[BD-SIZE-ADAPT\]' logs/sim.out | head -3
wc -l storage/printDone.csv; md5sum storage/printDone.csv
grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
echo "ONE_DONE $TAG $(date +%T)"
