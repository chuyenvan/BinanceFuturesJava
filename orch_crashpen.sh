#!/bin/bash
# Orch: wait cp-g2-p150 -> fetch all 6 -> run crashpen driver. Read-only, nice.
set -u
R=/home/ubuntu/src/BinanceFuturesJava
echo "=== $(date '+%F %T') WAIT cp-g2-p150 ==="
python3 -u -c "
import sys; sys.path.insert(0,'$R')
from tools import kaggle_sim as ks
ref=ks.kernel_ref('cp-g2-p150')
print('wait ->', ks.wait([ref], poll_s=60, timeout_s=10800), flush=True)
" 2>&1 | grep -aviE 'outdated API|B/s\]|Warning'
echo "=== $(date '+%F %T') FETCH all 6 ==="
python3 -u -c "
import sys; sys.path.insert(0,'$R')
from tools import kaggle_sim as ks
for t in ['cp-r4-parity','cp-g2-parity','cp-r4-p069','cp-r4-p150','cp-g2-p069','cp-g2-p150']:
    o=ks.fetch(t); print(t,'->',o['dir'],'res=',o['result'], flush=True)
" 2>&1 | grep -aviE 'outdated API|B/s\]|Warning'
echo "=== $(date '+%F %T') DRIVER ==="
cd $R
nice -n 10 python3 research/analysis/reset_rule_crashpen_driver.py \
  --json docs/result/crash_penalty.json --report /home/ubuntu/crash_penalty_report.txt 2>&1
echo "=== $(date '+%F %T') DONE rc=$? ==="
