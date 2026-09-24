#!/bin/bash
# C4 SIM — ban SAO run_x1_sim.sh, tham so hoa theo ARM. Build dataset tu bins cua arm roi
# chay 1 sim tren Oracle voi TICKER_SOURCE=file (neo 60395, dung ho voi X1_C3).
# usage: run_c4_sim.sh <TAG> <profile.properties> <bins_dir>
# Xem docs/prereg/PREREG_C4.md.
set -u
TAG=$1; PROF=$2; BINS=$3
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_c4
L=/home/ubuntu/c4log
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
mkdir -p $L $B/logs

[ -n "$(pgrep java || true)" ] && { echo "C4_ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
[ "$FREE" -lt 8 ] && { echo "C4_ABORT: DISK_LOW ($FREE G < 8G)"; exit 3; }
grep -q "^WFO_FUNDING_PRED_DIR=$BINS\$" $PROF || { echo "C4_ABORT: profile khong tro $BINS"; exit 4; }
N=$(ls $BINS/predict_wf_*.bin 2>/dev/null | wc -l)
[ "$N" = "16" ] || { echo "C4_ABORT: co $N bins, can 16"; exit 6; }

rm -rf $DS
SHA=$(cd $R && git rev-parse --short HEAD)
echo "### $(date +%T) BUILD DATASET $DS tag=$TAG bins=$BINS (code $SHA)"
cd $B && cp -f $CFGF $B/config.properties
env TRADING_PROFILE=$PROF WFO_SET_PRED=ai_pred_market_gate_wfo \
    WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$SHA \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > $L/build_$TAG.out 2>&1
echo "build rc=$?"
grep -aE 'HOLDOUT SEAL|Exception|EXPORT xong|FAIL|THIEU BINS' $L/build_$TAG.out | tail -6
[ -f $DS/market.bin ] || { echo "C4_ABORT: dataset khong sinh ra"; tail -20 $L/build_$TAG.out; exit 7; }
grep -E "foldCount|maxFoldSpan|marketRange|leakFreeFrom|binsSha256|Count=" $DS/manifest.txt
du -sh $DS

D=$B/$TAG
echo "### $(date +%T) RUN $TAG ($PROF)"
mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties; rm -f storage/*
ln -sfn $TICK kaggle_data_hpo
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
echo "$TAG rc=$?"
grep -a 'Loaded Symbol Mapper' logs/sim.out | head -1
grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
wc -l storage/printDone.csv; md5sum storage/printDone.csv
cd $B; rm -rf $DS
df -BG --output=avail / | tail -1
echo "C4_SIM_DONE $TAG $(date +%T)"
