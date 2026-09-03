#!/bin/bash
# PRE-REG: docs/PREREG_K.md (viet TRUOC khi chay). K0 doi chung tai lap H1a; K1/K2 them tran lenh dong thoi.
# Dung he TRADING_PROFILE moi: moi tham so giao dich trong file profile, KHONG env.
set -u
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
CFGF=$R/configs/sim_dev.properties
B=/home/ubuntu/java/devrun
P=/home/ubuntu/java/profiles
DS=/home/ubuntu/wfo_ds_k

# --- sinh 3 profile tu c2b ---
mkdir -p $P
for v in k0 k1 k2; do
  sed 's/^SIM_MIN_MOMENTUM_15M=.*/SIM_MIN_MOMENTUM_15M=0.006/' $P/c2b.properties > $P/$v.properties
done
printf '\n# K1: tran lenh dong thoi (C2b thuc te max 29 p95 22; H1a max 37 p95 29)\nMAX_CONCURRENT=25\n' >> $P/k1.properties
printf '\n# K2: tran lenh dong thoi chat hon\nMAX_CONCURRENT=20\n' >> $P/k2.properties
for v in k0 k1 k2; do echo "--- $v ---"; grep -E 'MIN_MOMENTUM|MAX_CONCURRENT' $P/$v.properties; done

cd $B
export WFO_SET_PRED=ai_pred_market_gate_wfo WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2 WFO_CODE_SHA=prereg-K
cp -f $CFGF $B/config.properties
WFO_SEL_HORIZON_IDX=0 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build_k.out 2>&1
echo "dataset rc=$?"

runp() { local TAG=$1; local PROF=$2; local D=$B/$TAG
  mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties; rm -f storage/*
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
      EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
      com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  echo "=== $TAG rc=$? ==="
  grep -aE '^\[CFG\]' logs/sim.out | head -2 | cut -c1-130
  grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
  cd $B; }

runp K0_h1a_prof $P/k0.properties
runp K1_conc25   $P/k1.properties
runp K2_conc20   $P/k2.properties
rm -rf $DS

echo "=== CHAM DIEM (tieu chi trong docs/PREREG_K.md) ==="
python3 /home/ubuntu/java/fsrun/qret.py C2b H1a_mom006 K0_h1a_prof K1_conc25 K2_conc20 2>&1 | grep -aE '^===|nam %|maxDD|quy >=|underwater'
df -h / | tail -1
echo DEV_K_DONE
