#!/bin/bash
cd /home/ubuntu/claude_master/audit_1021
for i in $(seq 1 60); do grep -q ALLDONE replay/logs/win_status.txt && break; sleep 10; done
python3 scripts/a4_replay.py /home/ubuntu/claude_master/gvz/store/gate_dataset_full.csv a4_replay.json \
  replay/gate_replay_20210101_20260401.csv replay/win_*.csv > a4.log 2>&1
echo A4DONE >> a4.log
