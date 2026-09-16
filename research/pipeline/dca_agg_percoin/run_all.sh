#!/bin/bash
# DCA-AGG-PERCOIN (docs/PREREG_DCA_AGG_PERCOIN.md) — parity + 3 bien the, TUAN TU, 1 slot JVM.
# KHONG push. DEV 2021-07..2025-12 (wfo_ds_x1_2021). SIM_END_DATE=20251231.
set -u
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
CFG=$R/configs/sim_dev_file_2021.properties
DS=/home/ubuntu/wfo_ds_x1_2021
B=/home/ubuntu/java/devrun
P=$R/profiles
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo
REF_MD5=efb793e2468ca3a7318da0f0ad23d4fc
mkdir -p $B/logs

[ -n "$(pgrep -f 'java.*SimulatorMarketLevelTicker1MStopLoss' || true)" ] && { echo "ABORT: SIM_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
[ "$FREE" -lt 8 ] && { echo "ABORT: DISK_LOW"; exit 3; }

# tao profile clone cho 3 bien the (base x1_gs_t170 + key moi)
cp -f $P/x1_gs_t170.properties $P/x1_gs_t170_loose_agg30.properties
printf '\n# DCA-AGG-PERCOIN LOOSE_AGG30 (docs/PREREG_DCA_AGG_PERCOIN.md)\nDCA_GRID_LEVELS=-0.30,-0.55,-0.75\nCONC_CAP_AGG_DCA_ENABLED=true\nCONC_CAP_AGG_DCA_PCT=0.30\n' >> $P/x1_gs_t170_loose_agg30.properties

cp -f $P/x1_gs_t170.properties $P/x1_gs_t170_loose_agg30_pc15.properties
printf '\n# DCA-AGG-PERCOIN LOOSE_AGG30_PC15 (docs/PREREG_DCA_AGG_PERCOIN.md)\nDCA_GRID_LEVELS=-0.30,-0.55,-0.75\nCONC_CAP_AGG_DCA_ENABLED=true\nCONC_CAP_AGG_DCA_PCT=0.30\nCONC_CAP_PERCOIN_ENABLED=true\nCONC_CAP_PERCOIN_PCT=0.15\n' >> $P/x1_gs_t170_loose_agg30_pc15.properties

cp -f $P/x1_gs_t170.properties $P/x1_gs_t170_loose_pc15.properties
printf '\n# DCA-AGG-PERCOIN LOOSE_PC15 (docs/PREREG_DCA_AGG_PERCOIN.md)\nDCA_GRID_LEVELS=-0.30,-0.55,-0.75\nCONC_CAP_PERCOIN_ENABLED=true\nCONC_CAP_PERCOIN_PCT=0.15\n' >> $P/x1_gs_t170_loose_pc15.properties

runx() { TAG=$1; PROF=$2; D=$B/$TAG
  echo "### $(date +%T) RUN $TAG prof=$PROF"
  mkdir -p $D/storage $D/logs; cd $D; cp -f $CFG config.properties; rm -f storage/*
  ln -sfn $TICK kaggle_data_hpo
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  echo "$TAG rc=$?"
  grep -a '\[CONC-PC\]' logs/sim.out | head -8
  grep -a '\[CONC-CAP\]' logs/sim.out | head -8
  grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
  wc -l storage/printDone.csv; md5sum storage/printDone.csv
  cd $B; }

# 1. PARITY (flag OFF, profile goc)
runx X1_GS_T170_2021_PC_PARITY $P/x1_gs_t170.properties
MD=$(md5sum $B/X1_GS_T170_2021_PC_PARITY/storage/printDone.csv | awk '{print $1}')
echo "PARITY md5=$MD"
if [ "$MD" != "$REF_MD5" ]; then
  echo "ABORT: PARITY MD5 MISMATCH (got $MD, want $REF_MD5)"
  exit 9
fi
echo "PARITY OK byte-identical"

# 2. 3 bien the
runx X1_GS_T170_2021_LOOSE_AGG30       $P/x1_gs_t170_loose_agg30.properties
runx X1_GS_T170_2021_LOOSE_AGG30_PC15  $P/x1_gs_t170_loose_agg30_pc15.properties
runx X1_GS_T170_2021_LOOSE_PC15        $P/x1_gs_t170_loose_pc15.properties

df -BG --output=avail / | tail -1
echo "DCA_AGG_PERCOIN_DONE $(date +%T)"
