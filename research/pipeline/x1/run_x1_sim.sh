#!/bin/bash
# X1 SIM — build dataset 1 lan tu bins X1 roi chay 2 arm TUAN TU tren Oracle voi TICKER_SOURCE=file.
# Ly do duong `file` (khong phai aerospike): C3/C3_FULL chay tren Kaggle = duong `file`; neo 60395.
# Xem docs/PREREG_X1.md muc 1.4 + 3.
set -u
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_x1
P=$R/profiles
L=/home/ubuntu/x1log
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
mkdir -p $L $B/logs

[ -n "$(pgrep java || true)" ] && { echo "X1_ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
[ "$FREE" -lt 8 ] && { echo "X1_ABORT: DISK_LOW ($FREE G < 8G)"; exit 3; }
grep -q '^WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1$' $P/x1_c3.properties || { echo "X1_ABORT: profile khong tro bins X1"; exit 4; }
[ -f /home/ubuntu/predwf_map_s1a2_x1/predict_wf_20251001.bin ] || { echo "X1_ABORT: thieu bins fold 20251001"; exit 5; }
N=$(ls /home/ubuntu/predwf_map_s1a2_x1/predict_wf_*.bin | wc -l)
[ "$N" = "16" ] || { echo "X1_ABORT: co $N bins, can 16"; exit 6; }

SHA=$(cd $R && git rev-parse --short HEAD)
echo "### $(date +%T) BUILD DATASET $DS (code $SHA)"
cd $B && cp -f $CFGF $B/config.properties
env TRADING_PROFILE=$P/x1_c3.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
    WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$SHA \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > $L/build.out 2>&1
echo "build rc=$?"
grep -aE 'HOLDOUT SEAL|Exception|EXPORT xong|FAIL|THIEU BINS' $L/build.out | tail -6
[ -f $DS/market.bin ] || { echo "X1_ABORT: dataset khong sinh ra"; tail -20 $L/build.out; exit 7; }
grep -E "foldCount|maxFoldSpan|marketRange|leakFreeFrom|binsSha256|Count=" $DS/manifest.txt
du -sh $DS; df -BG --output=avail / | tail -1

runx() { T=$1; PROF=$2; D=$B/$T
  echo "### $(date +%T) RUN $T ($PROF)"
  mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties; rm -f storage/*
  ln -sfn $TICK kaggle_data_hpo
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
      EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
      com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  echo "$T rc=$?"
  grep -a 'Loaded Symbol Mapper' logs/sim.out | head -1
  grep -a '\[CFG\]' logs/sim.out | head -2
  grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
  grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
  wc -l storage/printDone.csv; md5sum storage/printDone.csv
  cd $B; }

runx X1_C3      $P/x1_c3.properties
runx X1_C3_FULL $P/x1_c3_full.properties
df -BG --output=avail / | tail -1
echo "X1_SIM_DONE $(date +%T)"
