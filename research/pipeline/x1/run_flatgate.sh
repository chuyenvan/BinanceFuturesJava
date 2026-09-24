#!/bin/bash
# FLATGATE — chay MOT arm sim tren dataset X1 da co (KHONG build lai dataset).
#   run_flatgate.sh FLATOFF   -> jar moi + x1_c3_full.properties          (cong nghiem thu)
#   run_flatgate.sh FLATGATE  -> jar moi + x1_c3_full_flatgate.properties (bien the)
# Giu nguyen khuon `runx` cua research/pipeline/x1/run_x1_sim.sh. Xem docs/prereg/PREREG_FLATGATE.md.
set -u
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_x1
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo

case "${1:-}" in
  FLATOFF)  T=X1_C3_FULL_FLATOFF;  PROF=$R/profiles/x1_c3_full.properties ;;
  FLATGATE) T=X1_C3_FULL_FLATGATE; PROF=$R/profiles/x1_c3_full_flatgate.properties ;;
  *) echo "dung: run_flatgate.sh FLATOFF|FLATGATE"; exit 2 ;;
esac

[ -n "$(pgrep java || true)" ] && { echo "ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
[ "$FREE" -lt 8 ] && { echo "ABORT: DISK_LOW ($FREE G < 8G)"; exit 3; }
[ -f $DS/market.bin ] || { echo "ABORT: thieu dataset $DS"; exit 4; }
[ -f $JAR ] || { echo "ABORT: thieu jar"; exit 5; }

D=$B/$T
echo "### $(date +%T) RUN $T ($PROF) code=$(cd $R && git rev-parse --short HEAD)"
mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties; rm -f storage/*
ln -sfn $TICK kaggle_data_hpo
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
echo "$T rc=$?"
grep -a '\[CFG\]' logs/sim.out | head -3
grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
wc -l storage/printDone.csv; md5sum storage/printDone.csv
echo "FLATGATE_RUN_DONE $T $(date +%T)"
