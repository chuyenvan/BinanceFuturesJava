#!/bin/bash
# AUDIT 1021 — replay ExportGateDataset theo CUA SO (tuan tu) tu Oracle aerospike-wfo, CHI DOC; config ep 127.0.0.1.
set -u
W=/home/ubuntu/claude_master/audit_1021/replay
cd $W || exit 1
JAR=/home/ubuntu/claude_master/v11_settle/jar/binance-java-sdk-1.2.4.jar_v11b_d7824f6d
if grep -q '103\.157' config.properties; then echo "ABORT ip ngoai"; exit 2; fi
export LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false SYMBOL_MAPPER_DUP_POLICY=WARN
for WIN in 20210322:20210401 20210815:20210825 20220505:20220515 20230310:20230320 20240801:20240811 20250405:20250415 20251008:20251018 20260301:20260311; do
  S=${WIN%%:*}; E=${WIN##*:}; OUT=$W/win_${S}_${E}.csv
  java -Xmx7g -Duser.timezone=Asia/Ho_Chi_Minh -cp $JAR com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset \
     $S $E $OUT > logs/win_${S}_${E}.out 2>&1 &
  JP=$!
  while kill -0 $JP 2>/dev/null; do
    if ss -tnp 2>/dev/null | grep "pid=$JP," | grep -q '103\.157\.218\.'; then echo "$(date) VIOLATION $WIN -> KILL" >> logs/guard.txt; kill -9 $JP; fi
    sleep 2
  done
  wait $JP; echo "$WIN rc=$?" >> logs/win_status.txt
done
echo ALLDONE >> logs/win_status.txt
