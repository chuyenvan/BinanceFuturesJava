#!/bin/bash
# rank-K sweep tren frozen giveback-0.3, full-16, jobstore LOCAL. Usage: <topk> <tag>
TOPK=$1; TAG=$2
JAR=/tmp/patch:/home/ubuntu/java/simulator/gatecount.jar
CWD=/home/ubuntu/claudedata/.run/oracle_worker_cwd
LOGD=/home/ubuntu/claudedata/.run/mcp_ce
E="WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff WFO_SMART_CACHE=1 WFO_SEED_BASE=42 WFO_MAX_OOS_DATE=20260101 WFO_STATE_HOST=127.0.0.1 WFO_STATE_PORT=3222 WFO_STATE_NS=test WFO_N_SAMPLES=1 WFO_HARNESS_FIX=true TS_GIVEBACK_FLOOR=true TS_MIN_GAP=0.01 TS_GIVEBACK_RATIO=0.3 DCA_GRID_ENABLED=false DCA_GRID_SCALAR=false DCA_TIER_MARGIN_ENABLED=false SIM_BREAKER_MODE=OFF SIM_APPLY_FUNDING=true SIM_MIN_MOMENTUM_15M=0.008 SELECTOR_RANK_TOPK=$TOPK SELECTOR_RANK_OFFSET=0"
pkill -f 'WfoWorker strategy_window' 2>/dev/null || true
sleep 2
cd $CWD
env $E java -cp $JAR com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator reset strategy_window > $LOGD/${TAG}_reset.log 2>&1
tail -n1 $LOGD/${TAG}_reset.log
for i in 0 1; do
  setsid nohup env $E java -cp $JAR com.binance.chuyennd.ai_ml.wfo.framework.WfoWorker strategy_window > $LOGD/wfo_${TAG}_w$i.log 2>&1 &
done
sleep 4
echo "LAUNCHED $TAG topk=$TOPK workers=$(pgrep -c -f 'WfoWorker strategy_window')"
