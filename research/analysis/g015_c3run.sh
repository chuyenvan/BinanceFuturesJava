#!/bin/bash
# C3 = C2b env, doi WFO_FUNDING_PRED_DIR->predwf_G015_v2 + SIM_MIN_MOMENTUM_15M->cal. CHI DEV.
set -u
JAR=/home/ubuntu/src/BinanceFuturesJava/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
DS=/home/ubuntu/wfo_ds_c3
PRED=/home/ubuntu/predwf_G015_v2
MM=0.014052
cd "$B" || exit 1
if [ -n "$(pgrep java)" ]; then echo JAVA_BUSY_ABORT; exit 2; fi
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
if [ "$FREE" -lt 6 ]; then echo DISK_LOW_ABORT; exit 3; fi
export WFO_SET_PRED=ai_pred_market_gate_wfo
export WFO_FUNDING_PRED_DIR="$PRED" WFO_CODE_SHA=g015v2-C3
cp -f /home/ubuntu/java/simulator/config.properties "$B/config.properties"
WFO_SEL_HORIZON_IDX=0 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp "$JAR" \
  com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset "$DS" > "$B/logs_build_c3.out" 2>&1
echo "build rc=$?"
grep -aE 'HOLDOUT SEAL|Exception|EXPORT xong|FAIL' "$B/logs_build_c3.out" | tail -4
du -sh "$DS" 2>/dev/null; df -BG --output=avail / | tail -1
D="$B/C3"; mkdir -p "$D/storage" "$D/logs"; cd "$D"
cp -f "$B/G1_giveback5/config.properties" config.properties; rm -f storage/*
env WFO_DATA_DIR="$DS" WFO_SMART_CACHE=1 SIM_END_DATE=20240630 SELECTOR_RANK_TOPK=8 \
  SIM_MIN_MOMENTUM_15M="$MM" SIM_APPLY_FUNDING=true SIM_BREAKER_MODE=OFF \
  DCA_GRID_ENABLED=true DCA_GRID_LEVELS=-0.50,-0.75,-0.90 DCA_GRID_WEIGHTS=1,0,0,0 \
  SIM_FUNDING_MARK=true SIM_LOSER_TIME_STOP_HOURS=168 SIM_TS_GIVEBACK=1 \
  SIM_RATE_PROFIT_STOP_MARKET=0.07 DCA_GRID_SCALE=1.5 TS_GAP_CONST=1 TIER_FLAT=1 \
  SELECTOR_ONLY_ENTRY=1 WFO_FUNDING_PRED_DIR="$PRED" \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp "$JAR" \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
echo "=== C3 rc=$? ==="
grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
grep -aE 'Exception|Error' logs/sim.out | tail -3
cd "$B"; rm -rf "$DS"; df -BG --output=avail / | tail -1
python3 /home/ubuntu/java/fsrun/qret.py C2b C3 | grep -aE '===|nam %|quy >=|2 quy|underwater|maxDD'
echo C3_DONE
