#!/bin/bash
# day G0' (B0 tren jar AS-FILE, enable_internet=False) ngay khi co slot; poll 60 s (uu tien hon seq 300 s)
cd /home/ubuntu/claude_master/res1109/r3_gate/orch
while true; do
  R3_ORCH_MOD=r3_orch_m python3 r3_push.py g0m 42 >> push_g0m.out 2>&1; rc=$?
  echo "$(date -u +%FT%TZ) rc=$rc"
  [ $rc -eq 2 ] || exit $rc
  sleep 60
done
