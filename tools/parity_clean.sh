#!/bin/bash
# CONG KIEM CHUNG BYTE-IDENTITY cho refactor xoa tham so tro.
#   Chay: bash parity_clean.sh <TAG>
#   So printDone.csv (bo dong header) voi ban nen /home/ubuntu/java/devrun/C2b/storage/printDone.csv
# Dataset dung CHUNG /home/ubuntu/wfo_ds_clean (build 1 lan, giu lai giua cac dot -> input GIONG HET).
set -u
TAG=${1:-CLEAN}
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
CFGF=$R/configs/sim_dev.properties
B=/home/ubuntu/java/devrun; P=/home/ubuntu/java/profiles; DS=/home/ubuntu/wfo_ds_clean

echo "=== build jar ==="
cd $R && mvn -q -DskipTests package 2>&1 | tail -20
RC=${PIPESTATUS[0]}
echo "build rc=$RC jar=$(md5sum $JAR | cut -c1-12)"
[ "$RC" = "0" ] || { echo "PARITY_ABORT: build FAIL"; exit 1; }

echo "=== check_cfg_gateway ==="
bash $R/tools/check_cfg_gateway.sh || { echo "PARITY_ABORT: cfg gateway FAIL"; exit 1; }

cd $B
export WFO_SET_PRED=ai_pred_market_gate_wfo WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2 WFO_CODE_SHA=clean
if [ ! -f $DS/market.bin ]; then
  echo "=== build dataset $DS (1 lan) ==="
  cp -f $CFGF $B/config.properties
  WFO_SEL_HORIZON_IDX=0 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build_clean.out 2>&1
  echo "dataset rc=$? size=$(du -sh $DS | cut -f1)"
else
  echo "=== dataset $DS da co, dung lai ==="
fi

runp() { local T=$1; local PROF=$2; local D=$B/$T
  mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties; rm -f storage/*
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
      EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
      com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  echo "=== $T rc=$? ==="; grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
  grep -a '\[CFG\]' logs/sim.out | head -3; cd $B; }

runp $TAG $P/c2b_min.properties

echo
echo "=== VERDICT byte-identity voi C2b ==="
if cmp -s <(tail -n +2 $B/$TAG/storage/printDone.csv) <(tail -n +2 $B/C2b/storage/printDone.csv); then
  echo "$TAG: IDENTICAL"
else
  echo "$TAG: **KHAC** <-- co thay doi hanh vi"
  wc -l $B/$TAG/storage/printDone.csv $B/C2b/storage/printDone.csv
  diff <(tail -n +2 $B/$TAG/storage/printDone.csv) <(tail -n +2 $B/C2b/storage/printDone.csv) | head -20
fi
df -h / | tail -1
echo PARITY_DONE
