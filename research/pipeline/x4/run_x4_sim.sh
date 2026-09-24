#!/bin/bash
# X4 SIM tren Oracle (TICKER_SOURCE=file) - quet 4 hang so trailing tren jar SACH (sau B1).
#   bash run_x4_sim.sh          -> dataset + X4_PARITY + cong hoi quy + 9 arm
#   bash run_x4_sim.sh parity   -> chi dataset + X4_PARITY + cong hoi quy
#   bash run_x4_sim.sh arms     -> chi 9 arm (gia dinh cong hoi quy DA PASS)
#   bash run_x4_sim.sh combo    -> chi X4_COMBO (run 11, chi khi >= 2 truc doi)
# Cong C1 (hoi quy): X4_PARITY phai ra md5 printDone = d39da2940dfd815f60772f70517750bf (= X1_C3).
# Cong C2 (key song): moi arm phai ra md5 KHAC parity; arm dau tien trung parity => exit 10.
# Xem docs/prereg/PREREG_X4.md muc 3.
set -u
MODE=${1:-all}
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_x1
P=$R/profiles
L=/home/ubuntu/x4log
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
MD5_X1C3=d39da2940dfd815f60772f70517750bf
mkdir -p $L $B/logs

[ -n "$(pgrep java || true)" ] && { echo "X4_ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
NEED=8; [ -f $DS/market.bin ] && NEED=3
[ "$FREE" -lt "$NEED" ] && { echo "X4_ABORT: DISK_LOW ($FREE G < ${NEED}G)"; exit 3; }
N=$(ls /home/ubuntu/predwf_map_s1a2_x1/predict_wf_*.bin | wc -l)
[ "$N" = "16" ] || { echo "X4_ABORT: co $N bins, can 16"; exit 6; }

SHA=$(cd $R && git rev-parse --short HEAD)
echo "code_sha=$SHA jar_md5=$(md5sum $JAR | cut -d' ' -f1)"
if [ ! -f $DS/market.bin ]; then
  echo "### $(date +%T) BUILD DATASET $DS (code $SHA)"
  cd $B && cp -f $CFGF $B/config.properties
  env TRADING_PROFILE=$P/x1_c3.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
      WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$SHA \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
      com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > $L/build_ds.out 2>&1
  echo "build rc=$?"
  grep -aE 'HOLDOUT SEAL|Exception|EXPORT xong|FAIL|THIEU BINS' $L/build_ds.out | tail -6
fi
[ -f $DS/market.bin ] || { echo "X4_ABORT: dataset khong sinh ra"; tail -20 $L/build_ds.out; exit 7; }
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
  wc -l storage/printDone.csv; md5sum storage/printDone.csv
  cd $B; }

if [ "$MODE" = "all" ] || [ "$MODE" = "parity" ]; then
  runx X4_PARITY $P/x1_c3.properties
  GOT=$(md5sum $B/X4_PARITY/storage/printDone.csv | cut -d' ' -f1)
  echo "C1_REGRESS got=$GOT want=$MD5_X1C3"
  [ "$GOT" != "$MD5_X1C3" ] && { echo "X4_ABORT_C1: printDone KHONG byte-identical X1_C3"; exit 9; }
  echo "C1_REGRESS=PASS"
fi
[ "$MODE" = "parity" ] && { echo "X4_SIM_PARITY_DONE $(date +%T)"; exit 0; }

PAR=$(md5sum $B/X4_PARITY/storage/printDone.csv | cut -d' ' -f1)
chk() { T=$1; G=$(md5sum $B/$T/storage/printDone.csv | cut -d' ' -f1)
  if [ "$G" = "$PAR" ]; then echo "C2_KEYALIVE $T = **DEAD** (md5 trung parity)"; return 1
  else echo "C2_KEYALIVE $T = OK (md5 $G khac parity)"; return 0; fi; }

if [ "$MODE" = "combo" ]; then
  runx X4_COMBO $P/x4_combo.properties; chk X4_COMBO
  echo "X4_COMBO_DONE $(date +%T)"; exit 0
fi

runx X4_G05  $P/x4_g05.properties
chk X4_G05 || { echo "X4_ABORT_C2: truc G la KEY CHET tren jar nay => DUNG"; exit 10; }
runx X4_H20  $P/x4_h20.properties
chk X4_H20 || { echo "X4_ABORT_C2: truc H la KEY CHET tren jar nay => DUNG"; exit 10; }
runx X4_G12  $P/x4_g12.properties;  chk X4_G12
runx X4_H40  $P/x4_h40.properties;  chk X4_H40
runx X4_W015 $P/x4_w015.properties; chk X4_W015
runx X4_W05  $P/x4_w05.properties;  chk X4_W05
runx X4_R03  $P/x4_r03.properties;  chk X4_R03
runx X4_R07  $P/x4_r07.properties;  chk X4_R07
runx X4_U05  $P/x4_u05.properties;  chk X4_U05

echo "=== C4 TSloss BAT BIEN (n STOP_LOSS_DONE phai = parity) ==="
for T in X4_PARITY X4_G05 X4_G12 X4_W015 X4_W05 X4_R03 X4_R07 X4_H20 X4_H40 X4_U05; do
  echo "$T n_SL=$(grep -ac ',STOP_LOSS_DONE,' $B/$T/storage/printDone.csv || true)"
done
df -BG --output=avail / | tail -1
echo "X4_SIM_DONE $(date +%T)"
