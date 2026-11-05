#!/bin/bash
# E2E_REPLAY: build/test qua lock Oracle. argv: compile | test <TestClass[#method]>
set -u
MODE=${1:-compile}
TEST=${2:-CrashDayReplayE2ETest}
W=~/claude_master/v12/e2e_wt
L=~/claude_master/e2e1105/logs
mkdir -p $L ~/claude_master/locks
FREE=$(free -m | awk '/^Mem:/{print $7}')
DISK=$(df -BG / | awk 'NR==2{gsub("G","",$4);print $4}')
echo "free=${FREE}MB disk=${DISK}G"
if [ "$FREE" -lt 4000 ] || [ "$DISK" -lt 15 ]; then echo "TU CHOI: tai nguyen thap"; exit 9; fi
export LIVE_IS_SHADOW_HOST=true
export MAVEN_OPTS=-Xmx2g
export SIM_GATE_DYN_SCALE=1.55 SIM_MIN_MOMENTUM_15M=0.008 SELECTOR_RANK_TOPK=24 LIVE_KILLSW_C2_SIGNED=1
export E2E_FX_DIR=~/claude_master/e2e1105/fx E2E_OUT=~/claude_master/e2e1105/out
MVN=/home/ubuntu/tools/apache-maven-3.9.9/bin/mvn
cd $W
TS=$(date +%H%M%S)
if [ "$MODE" = compile ]; then
  CMD="$MVN -o -q -T 1 test-compile -DskipTests"
  LOG=$L/compile_$TS.log
else
  CMD="$MVN -o -T 1 test -Dtest=$TEST -DfailIfNoTests=false -Dsurefire.failIfNoSpecifiedTests=false -DargLine=-Xmx3g"
  LOG=$L/test_$TS.log
fi
echo "LOG=$LOG"
setsid nohup bash -c "flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 $CMD > $LOG 2>&1; echo EXIT=\$? >> $LOG" > /dev/null 2>&1 < /dev/null &
echo started
