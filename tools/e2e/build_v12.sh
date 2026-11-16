#!/bin/bash
# E2E_REPLAY_V12: bien dich test-classes (khong chay test) qua lock Oracle. Log: ~/claude_master/e2e_v12/logs/compile_<ts>.log
set -u
W=$(cd "$(dirname "$0")/../.." && pwd)
L=~/claude_master/e2e_v12/logs; mkdir -p $L ~/claude_master/locks
export LIVE_IS_SHADOW_HOST=true MAVEN_OPTS=-Xmx2g
MVN=/home/ubuntu/tools/apache-maven-3.9.9/bin/mvn
LOG=$L/compile_$(date +%m%d_%H%M%S).log
cd $W
flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 $MVN -o -q -T 1 test-compile -DskipTests > $LOG 2>&1
RC=$?; echo "EXIT=$RC" >> $LOG; echo "$LOG RC=$RC"; exit $RC
