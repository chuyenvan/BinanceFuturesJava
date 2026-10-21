#!/bin/bash
# AUDIT 1021 — replay ExportGateDataset tu Oracle aerospike-wfo (127.0.0.1:3222, ns test) CHI DOC.
# Moi host trong config ep ve 127.0.0.1 (khong co duong toi 242). Ghi guard bat. Monitor ket noi ra 103.157.218.242.
set -u
W=/home/ubuntu/claude_master/audit_1021/replay
mkdir -p $W/logs && cd $W || exit 1
JAR=/home/ubuntu/claude_master/v11_settle/jar/binance-java-sdk-1.2.4.jar_v11b_d7824f6d
sed -E -e 's/^AEROSPIKE_HOST=.*/AEROSPIKE_HOST=127.0.0.1/' -e 's/^AEROSPIKE_HOST_226=.*/AEROSPIKE_HOST_226=127.0.0.1/' \
       -e 's/^AEROSPIKE_PORT=.*/AEROSPIKE_PORT=3222/' -e 's/^AEROSPIKE_PORT_226=.*/AEROSPIKE_PORT_226=3222/' \
       -e 's/^AEROSPIKE_READ_CLUSTER=.*/AEROSPIKE_READ_CLUSTER=226/' -e 's/103\.157\.218\.[0-9]+/127.0.0.1/g' \
       /home/ubuntu/java/simulator/config.properties > config.properties
if grep -q '103\.157' config.properties; then echo "ABORT: con IP ngoai trong config"; exit 2; fi
echo "SYMBOL_MAPPER_DUP_POLICY=WARN" >> config.properties
grep -E '^(AEROSPIKE_(HOST|PORT|READ_CLUSTER|NAMESPACE)|SYMBOL_MAPPER)' config.properties > logs/config_hosts.txt
cp /home/ubuntu/java/simulator/logback.xml . 2>/dev/null || true
md5sum $JAR > logs/jar.md5
export LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false SYMBOL_MAPPER_DUP_POLICY=WARN
START=${1:-20210101}; END=${2:-20260401}; OUT=$W/gate_replay_${START}_${END}.csv
nohup java -Xmx9g -Duser.timezone=Asia/Ho_Chi_Minh -cp $JAR com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset \
   $START $END $OUT > logs/replay_${START}_${END}.out 2>&1 &
JP=$!
echo "PID $JP" > logs/pid.txt
# monitor: bat ky ket noi nao toi 103.157.218.* -> kill ngay
( while kill -0 $JP 2>/dev/null; do
    if ss -tnp 2>/dev/null | grep "pid=$JP," | grep -q '103\.157\.218\.'; then
      echo "$(date) VIOLATION ket noi ra 103.157.218.x -> KILL" >> logs/guard.txt; kill -9 $JP; fi
    sleep 2
  done; echo "$(date) java exit" >> logs/guard.txt ) > /dev/null 2>&1 &
echo started $JP
