#!/bin/bash
# PRE-REG: docs/PREREG_BR.md. Bat circuit breaker (kiem soat phoi nhiem tang danh muc).
set -u
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
CFGF=$R/configs/sim_dev.properties
B=/home/ubuntu/java/devrun
P=/home/ubuntu/java/profiles
DS=/home/ubuntu/wfo_ds_br

# --- sinh 3 profile tu c2b ---
sed 's/^SIM_BREAKER_MODE=.*/SIM_BREAKER_MODE=MARGIN/' $P/c2b.properties > $P/br1.properties
sed 's/^SIM_BREAKER_MODE=.*/SIM_BREAKER_MODE=BOTH/'   $P/c2b.properties > $P/br2.properties
sed -e 's/^SIM_BREAKER_MODE=.*/SIM_BREAKER_MODE=MARGIN/' \
    -e 's/^SIM_MIN_MOMENTUM_15M=.*/SIM_MIN_MOMENTUM_15M=0.006/' $P/c2b.properties > $P/br3.properties
for v in br1 br2 br3; do echo "--- $v ---"; grep -E 'BREAKER_MODE|MIN_MOMENTUM_15M' $P/$v.properties; done

cd $B
# 2026-09-03: bins selector KHONG con cap qua env. No khai trong profile va di qua cong
# Cfg; dat CA HAI (env + profile) => Cfg fail-fast exit 2. Buoc build dataset la noi DOC
# bins nen cung phai co TRADING_PROFILE. Xem tools/run_c2b_dev.sh.
cp -f $CFGF $B/config.properties
env WFO_SET_PRED=ai_pred_market_gate_wfo WFO_CODE_SHA=prereg-BR WFO_SEL_HORIZON_IDX=0 \
    TRADING_PROFILE=$P/c2b.properties \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build_br.out 2>&1
echo "dataset rc=$?"

runp() { local TAG=$1; local PROF=$2; local D=$B/$TAG
  mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties; rm -f storage/*
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
      EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
      com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  echo "=== $TAG rc=$? ==="
  grep -aE '^\[CFG\]' logs/sim.out | head -1 | cut -c1-130
  grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
  cd $B; }

runp BR1_margin $P/br1.properties
runp BR2_both   $P/br2.properties
runp BR3_mg006  $P/br3.properties
rm -rf $DS

echo "=== CHAM DIEM theo docs/PREREG_BR.md ==="
python3 /home/ubuntu/java/fsrun/qret.py C2b K0_h1a_prof BR1_margin BR2_both BR3_mg006 2>&1 \
  | grep -aE '^===|nam %|maxDD|quy >=|underwater'
df -h / | tail -1
echo DEV_BR_DONE
