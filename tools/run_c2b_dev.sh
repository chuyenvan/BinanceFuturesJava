#!/bin/bash
# =============================================================================
# CHAY C2b tren DEV (2022-01-01 .. 2024-06-30) — BAN CHUAN sau khi PIN BINS (2026-09-03).
#
# Khac ban cu (dev_c2.sh / dev_min.sh): KHONG con `export WFO_FUNDING_PRED_DIR=...`.
# Bins selector nay khai trong PROFILE va di qua cong Cfg. Dat CA HAI (env + profile)
# => Cfg fail-fast exit 2 ("hai nguon su that"). CA HAI buoc (build dataset + sim) deu
# phai co TRADING_PROFILE, vi buoc build la noi doc bins.
#
# Cong nghiem thu: printDone.csv (bo dong header) phai BYTE-IDENTICAL voi baseline C2b
# (equity cuoi 60390, TICKER_SOURCE=aerospike tren Oracle).
#
# CHI DEV. KHONG cham VALIDATION (2024-07-15..2025-12-31), KHONG cham HOLDOUT 2026.
#   usage: run_c2b_dev.sh [profile] [tag] [dataset_dir] [baseline_dir]
# =============================================================================
set -u
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
CFGF=$R/configs/sim_dev.properties
B=/home/ubuntu/java/devrun
PROF=${1:-$R/profiles/c2b.properties}
TAG=${2:-C2b_PIN}
DS=${3:-/home/ubuntu/wfo_ds_c2b_pin}
BASE=${4:-$B/C2b}

# --- 0. mot slot java duy nhat: khong duoc chen len job dang chay ---
if [ -n "$(pgrep -a java || true)" ]; then
  echo "*** DUNG: dang co JVM chay ***"; pgrep -a java; exit 3
fi
[ -f "$JAR" ] || { echo "khong thay jar $JAR"; exit 1; }
[ -f "$PROF" ] || { echo "khong thay profile $PROF"; exit 1; }
[ -f "$BASE/storage/printDone.csv" ] || { echo "khong thay baseline $BASE/storage/printDone.csv"; exit 1; }
echo "jar md5=$(md5sum $JAR | cut -c1-12) profile=$PROF"
echo "profile bins: $(grep -E '^WFO_FUNDING_PRED_DIR=' $PROF)"
echo "baseline: $BASE  equity=$(grep -a 'done:' $BASE/logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+')"

# --- 1. build dataset (bins doc TU PROFILE) ---
mkdir -p $B/logs; cd $B || exit 1
cp -f $CFGF $B/config.properties
env TRADING_PROFILE=$PROF WFO_SET_PRED=ai_pred_market_gate_wfo WFO_SEL_HORIZON_IDX=0 \
    WFO_CODE_SHA=$(cd $R && git rev-parse --short HEAD) \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build_${TAG}.out 2>&1
RC=$?
echo "=== build rc=$RC ==="
grep -aE 'HOLDOUT SEAL|bins\.|binsSha256|fundingPredDir|foldCount|Exception|THIEU BINS' logs/build_${TAG}.out | tail -12
[ $RC -eq 0 ] || { echo "*** build FAIL -> dung ***"; exit 1; }
du -sh $DS; df -h / | tail -1

# --- 2. sim ---
D=$B/$TAG; mkdir -p $D/storage $D/logs; cd $D || exit 1
cp -f $CFGF config.properties; rm -f storage/*
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
RC=$?
echo "=== sim $TAG rc=$RC ==="
grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
grep -aE '^\[CFG\]|bins\.dir=|bins\.sha256_16=' logs/sim.out | head -6

# --- 3. CONG NGHIEM THU: byte-identity voi baseline ---
cd $B || exit 1
echo
echo "=== CONG BYTE-IDENTITY ==="
echo "cmp -s <(tail -n +2 $D/storage/printDone.csv) <(tail -n +2 $BASE/storage/printDone.csv)"
if cmp -s <(tail -n +2 $D/storage/printDone.csv) <(tail -n +2 $BASE/storage/printDone.csv); then
  echo "PASS: $TAG printDone.csv BYTE-IDENTICAL voi $(basename $BASE)"
  VERDICT=PASS
else
  echo "*** FAIL: KHAC baseline -> ban sua SAI, phai revert phan gay lech ***"
  wc -l $D/storage/printDone.csv $BASE/storage/printDone.csv
  diff <(tail -n +2 $D/storage/printDone.csv) <(tail -n +2 $BASE/storage/printDone.csv) | head -20
  VERDICT=FAIL
fi
md5sum $D/storage/printDone.csv $BASE/storage/printDone.csv
rm -rf $DS
echo "=== $TAG VERDICT=$VERDICT ==="
df -h / | tail -1
