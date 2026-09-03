#!/bin/bash
# VIEC 3 — chay lai cap exit-thuan R5_arm7 / R6_arm8 voi TICKLOG BAT.
# Tai lap CHINH XAC dev_rob2.sh (env-mode, KHONG TRADING_PROFILE) de printDone.csv phai
# byte-identical voi ban da luu 2026-09-02 => cap do duoc dung la cap ma PAIRED_CALIB da do.
set -u
JAR=/home/ubuntu/src/BinanceFuturesJava/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
DS=/home/ubuntu/wfo_ds_tlpair
df -h / | tail -1
AV=$(df -BG / | awk 'NR==2{print $4}' | tr -dc '0-9')
echo "avail=${AV}G"
if [ "$AV" -lt 6 ]; then echo "*** DUNG: dia con ${AV}G < 6G ***"; exit 9; fi
if [ -n "$(pgrep -a java || true)" ]; then echo "*** DUNG: dang co JVM chay ***"; pgrep -a java; exit 3; fi
[ -f /home/ubuntu/java/simulator/config.properties ] || { echo "thieu simulator/config.properties"; exit 1; }
[ -f $B/G1_giveback5/config.properties ] || { echo "thieu G1_giveback5/config.properties"; exit 1; }
cd $B || exit 1
export WFO_SET_PRED=ai_pred_market_gate_wfo
export WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2
export WFO_CODE_SHA=3071c33-maps1a2
mkdir -p logs
rm -rf /home/ubuntu/tick/R5_TL /home/ubuntu/tick/R6_TL

cp -f /home/ubuntu/java/simulator/config.properties $B/config.properties
WFO_SEL_HORIZON_IDX=0 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build_tlpair.out 2>&1
echo "build rc=$?"
grep -aE 'HOLDOUT SEAL|binsSha256|foldCount|Exception' logs/build_tlpair.out | tail -4
du -sh $DS; df -h / | tail -1

run() { local TAG=$1; shift; local D=$B/$TAG; mkdir -p $D/storage $D/logs; cd $D
  cp -f $B/G1_giveback5/config.properties config.properties; rm -f storage/*
  local T0=$(date +%s)
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 SELECTOR_RANK_TOPK=8 SIM_MIN_MOMENTUM_15M=0.008 SIM_APPLY_FUNDING=true SIM_BREAKER_MODE=OFF \
      DCA_GRID_ENABLED=true DCA_GRID_LEVELS=-0.50,-0.75,-0.90 DCA_GRID_WEIGHTS=1,0,0,0 SIM_FUNDING_MARK=true SIM_LOSER_TIME_STOP_HOURS=168 \
      SIM_TS_GIVEBACK=1 SIM_RATE_PROFIT_STOP_MARKET=0.05 SIM_TICKLOG=1 SIM_TICKLOG_TAG=$TAG "$@" \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  local RC=$?; local T1=$(date +%s)
  echo "=== $TAG rc=$RC wall=$((T1-T0))s ==="
  grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+' | tr '\n' ' '; echo
  grep -a TICKLOG logs/sim.out | tail -2
  grep -a "PROFILE. days=" logs/sim.out | tail -1
  cd $B; }

run R5_TL SIM_RATE_PROFIT_STOP_MARKET=0.07
run R6_TL SIM_RATE_PROFIT_STOP_MARKET=0.08
rm -rf $DS
echo
echo "=== CONG BYTE-IDENTITY vs ban luu 2026-09-02 ==="
cmp -s <(tail -n +2 $B/R5_TL/storage/printDone.csv) <(tail -n +2 $B/R5_arm7/storage/printDone.csv) && echo "R5_TL vs R5_arm7 = PASS" || echo "R5_TL vs R5_arm7 = FAIL"
cmp -s <(tail -n +2 $B/R6_TL/storage/printDone.csv) <(tail -n +2 $B/R6_arm8/storage/printDone.csv) && echo "R6_TL vs R6_arm8 = PASS" || echo "R6_TL vs R6_arm8 = FAIL"
md5sum $B/R5_TL/storage/printDone.csv $B/R5_arm7/storage/printDone.csv $B/R6_TL/storage/printDone.csv $B/R6_arm8/storage/printDone.csv
echo
du -sh /home/ubuntu/tick/R5_TL /home/ubuntu/tick/R6_TL
cat /home/ubuntu/tick/R5_TL/meta.txt
df -h / | tail -1
pgrep -a java || echo "khong con JVM"
echo TL_PAIR_DONE
