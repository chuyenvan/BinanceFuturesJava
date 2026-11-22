#!/bin/bash
# ADD24: mvn -o test-compile trong add24_wt (PrivateConfig STUB, LIVE_IS_SHADOW_HOST=true). CAM package. Log -> add24/a.
set -u
W=$(cd "$(dirname "$0")/../.." && pwd); A=$HOME/claude_master/w3/add24/a
export LIVE_IS_SHADOW_HOST=true MAVEN_OPTS=-Xmx2g
cmp -s $W/tools/add24/stub/PrivateConfig.java.stub $W/src/main/java/com/binance/chuyennd/config/PrivateConfig.java || \
  cp $W/tools/add24/stub/PrivateConfig.java.stub $W/src/main/java/com/binance/chuyennd/config/PrivateConfig.java
LOG=$A/build_wt_$(date +%m%d_%H%M%S).log; cd $W
if [ "${1:-}" = --no-lock ]; then /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -q -T 1 test-compile -DskipTests > $LOG 2>&1
else flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -q -T 1 test-compile -DskipTests > $LOG 2>&1; fi
RC=$?; echo "EXIT=$RC" >> $LOG; echo "$LOG RC=$RC"; exit $RC
