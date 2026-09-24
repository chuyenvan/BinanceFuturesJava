#!/bin/bash
# X2 SIM — build dataset WFO 48 thang 1 LAN roi chay 6 arm TUAN TU tren Oracle (TICKER_SOURCE=file).
# Cong hoi quy: X2_PARITY phai ra md5 printDone = d39da2940dfd815f60772f70517750bf (= X1_C3).
# FAIL => DUNG, khong chay 5 arm con lai. Xem docs/prereg/PREREG_X2.md muc 3-4.
set -u
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_x1
P=$R/profiles
L=/home/ubuntu/x2log
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
MD5_X1C3=d39da2940dfd815f60772f70517750bf
mkdir -p $L $B/logs

[ -n "$(pgrep java || true)" ] && { echo "X2_ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
[ "$FREE" -lt 8 ] && { echo "X2_ABORT: DISK_LOW ($FREE G < 8G)"; exit 3; }
N=$(ls /home/ubuntu/predwf_map_s1a2_x1/predict_wf_*.bin | wc -l)
[ "$N" = "16" ] || { echo "X2_ABORT: co $N bins, can 16"; exit 6; }

SHA=$(cd $R && git rev-parse --short HEAD)
if [ ! -f $DS/market.bin ]; then
  echo "### $(date +%T) BUILD DATASET $DS (code $SHA)"
  cd $B && cp -f $CFGF $B/config.properties
  env TRADING_PROFILE=$P/x2_parity.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
      WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$SHA \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
      com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > $L/build_ds.out 2>&1
  echo "build rc=$?"
  grep -aE 'HOLDOUT SEAL|Exception|EXPORT xong|FAIL|THIEU BINS' $L/build_ds.out | tail -6
fi
[ -f $DS/market.bin ] || { echo "X2_ABORT: dataset khong sinh ra"; tail -20 $L/build_ds.out; exit 7; }
grep -E "foldCount|leakFreeFrom|binsSha256|Count=" $DS/manifest.txt
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
  grep -a '\[CFG\]' logs/sim.out | head -1
  grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
  grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
  echo "$T n_PREARM_SL=$(grep -ac 'PREARM_SL ' logs/sim.out || true)"
  wc -l storage/printDone.csv; md5sum storage/printDone.csv
  cd $B; }

runx X2_PARITY $P/x2_parity.properties
GOT=$(md5sum $B/X2_PARITY/storage/printDone.csv | cut -d' ' -f1)
echo "REGRESS_GATE got=$GOT want=$MD5_X1C3"
if [ "$GOT" != "$MD5_X1C3" ]; then
  echo "X2_ABORT_REGRESS: printDone KHONG byte-identical X1_C3 => DUNG, khong chay tiep"
  exit 9
fi
echo "REGRESS_GATE=PASS"

runx X2_T120 $P/x2_t120.properties
runx X2_T96  $P/x2_t96.properties
runx X2_T72  $P/x2_t72.properties
runx X2_S20  $P/x2_s20.properties
runx X2_S30  $P/x2_s30.properties
df -BG --output=avail / | tail -1
echo "X2_SIM_DONE $(date +%T)"
