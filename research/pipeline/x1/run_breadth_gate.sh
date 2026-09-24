#!/bin/bash
# BREADTH_GATE — chay MOT arm sim cho TASK B2 Buoc 6 (docs/prereg/PREREG_BREADTH_GATE_SIM.md).
#   run_breadth_gate.sh OFFCHECK -> jar moi + x1_gs_t170.properties (cong OFF byte-identical)
#   run_breadth_gate.sh BR       -> jar moi + x1_c3_full_regime_br.properties  (bien the chinh)
#   run_breadth_gate.sh BR0      -> jar moi + x1_c3_full_regime_br0.properties (doi chung)
# Giu nguyen khuon `runx` cua research/pipeline/x1/run_flatgate.sh, doi DS sang wfo_ds_x1_2021
# (dung dataset ma cac tag X1_*_2021_REGIME_* truoc day dung - xem RESULT_REGIME_GATE.md/
# RESULT_REGIME_UPDOWN.md). Xem docs/prereg/PREREG_BREADTH_GATE_SIM.md.
set -u
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
CFGF=$R/configs/sim_dev_file.properties
DS=/home/ubuntu/wfo_ds_x1_2021
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo

case "${1:-}" in
  OFFCHECK) T=X1_C3_FULL_2021_REGIME_BR_OFFCHECK; PROF=$R/profiles/x1_gs_t170.properties ;;
  BR)       T=X1_C3_FULL_2021_REGIME_BR;          PROF=$R/profiles/x1_c3_full_regime_br.properties ;;
  BR0)      T=X1_C3_FULL_2021_REGIME_BR0;         PROF=$R/profiles/x1_c3_full_regime_br0.properties ;;
  *) echo "dung: run_breadth_gate.sh OFFCHECK|BR|BR0"; exit 2 ;;
esac

[ -n "$(pgrep java || true)" ] && { echo "ABORT: JAVA_BUSY"; exit 2; }
FREE=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "disk_free_G=$FREE"
[ "$FREE" -lt 8 ] && { echo "ABORT: DISK_LOW ($FREE G < 8G)"; exit 3; }
[ -f $DS/market.bin ] || { echo "ABORT: thieu dataset $DS"; exit 4; }
[ -f $JAR ] || { echo "ABORT: thieu jar"; exit 5; }
[ -f $PROF ] || { echo "ABORT: thieu profile $PROF"; exit 6; }

D=$B/$T
echo "### $(date +%T) RUN $T ($PROF) code=$(cd $R && git rev-parse --short HEAD)"
mkdir -p $D/storage $D/logs; cd $D; cp -f $CFGF config.properties
sed -i 's/^TIME_RUN=.*/TIME_RUN=20210701/' config.properties  # khop tag family 2021 (X1_GS_T170_2021 etc.)
rm -f storage/*
ln -sfn $TICK kaggle_data_hpo
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
echo "$T rc=$?"
grep -a '\[CFG\]' logs/sim.out | head -3
grep -a '\[REGIME\]' logs/sim.out | head -3
grep -a 'done:' logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+'
grep -aE 'Exception|OutOfMemory' logs/sim.out | head -3
wc -l storage/printDone.csv; md5sum storage/printDone.csv
echo "BREADTH_GATE_RUN_DONE $T $(date +%T)"
