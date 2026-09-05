#!/bin/bash
# X3 SIM tren Oracle (TICKER_SOURCE=file) — build dataset WFO 48 thang 1 LAN roi chay cac arm.
#   bash run_x3_sim.sh            -> dataset + X3_PARITY + cong hoi quy + 4 arm
#   bash run_x3_sim.sh parity     -> chi dataset + X3_PARITY + cong hoi quy
#   bash run_x3_sim.sh arms       -> chi 4 arm (gia dinh cong hoi quy DA PASS)
# Cong hoi quy: X3_PARITY phai ra md5 printDone = d39da2940dfd815f60772f70517750bf (= X1_C3).
# FAIL => exit 9, KHONG chay arm nao. Xem docs/PREREG_X3.md muc 3.1.
set -u
MODE=${1:-all}
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_x1
P=$R/profiles
L=/home/ubuntu/x3log
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
MD5_X1C3=d39da2940dfd815f60772f70517750bf
mkdir -p $L $B/logs

[ -n "$(pgrep java || true)" ] && { echo "X3_ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
# Nguong 8G chi co y nghia khi CON PHAI BUILD dataset (~4G). Dataset da co roi thi moi run
# chi ton them ~sim.out; nguong 3G la du. (Bug cua ban dau: chan ca luc dataset da san sang.)
NEED=8; [ -f $DS/market.bin ] && NEED=3
[ "$FREE" -lt "$NEED" ] && { echo "X3_ABORT: DISK_LOW ($FREE G < ${NEED}G)"; exit 3; }
N=$(ls /home/ubuntu/predwf_map_s1a2_x1/predict_wf_*.bin | wc -l)
[ "$N" = "16" ] || { echo "X3_ABORT: co $N bins, can 16"; exit 6; }

SHA=$(cd $R && git rev-parse --short HEAD)
if [ ! -f $DS/market.bin ]; then
  echo "### $(date +%T) BUILD DATASET $DS (code $SHA)"
  cd $B && cp -f $CFGF $B/config.properties
  env TRADING_PROFILE=$P/x3_parity.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
      WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$SHA \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
      com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > $L/build_ds.out 2>&1
  echo "build rc=$?"
  grep -aE 'HOLDOUT SEAL|Exception|EXPORT xong|FAIL|THIEU BINS' $L/build_ds.out | tail -6
fi
[ -f $DS/market.bin ] || { echo "X3_ABORT: dataset khong sinh ra"; tail -20 $L/build_ds.out; exit 7; }
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
  grep -a '\[CFG\]' logs/sim.out | head -2
  grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
  grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
  echo "$T n_PREARM_SL=$(grep -ac 'PREARM_SL ' logs/sim.out || true) n_SELRANK=$(grep -ac 'SELRANK ' logs/sim.out || true)"
  wc -l storage/printDone.csv; md5sum storage/printDone.csv
  cd $B; }

if [ "$MODE" != "arms" ]; then
  runx X3_PARITY $P/x3_parity.properties
  GOT=$(md5sum $B/X3_PARITY/storage/printDone.csv | cut -d' ' -f1)
  echo "REGRESS_GATE got=$GOT want=$MD5_X1C3"
  if [ "$GOT" != "$MD5_X1C3" ]; then
    echo "X3_ABORT_REGRESS: printDone KHONG byte-identical X1_C3 => DUNG, khong chay tiep"
    exit 9
  fi
  echo "REGRESS_GATE=PASS"
fi
[ "$MODE" = "parity" ] && { echo "X3_SIM_PARITY_DONE $(date +%T)"; exit 0; }

runx X3_R2  $P/x3_r2.properties
runx X3_R4  $P/x3_r4.properties
runx X3_R6  $P/x3_r6.properties
runx X3_S50 $P/x3_s50.properties
df -BG --output=avail / | tail -1
echo "X3_SIM_DONE $(date +%T)"
