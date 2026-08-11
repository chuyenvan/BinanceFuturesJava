#!/bin/bash
# Chay tuan tu cut 0.5, 0.7 sau khi cut hien tai (gvb03) xong. Jobstore local.
wait_done(){ sleep 20; while pgrep -f 'WfoWorker strategy_window' >/dev/null 2>&1; do sleep 15; done; }
rm -f /tmp/sweep_done.flag
wait_done                       # cho gvb03 xong
bash /tmp/run_gvb.sh 0.5 gvb05
wait_done
bash /tmp/run_gvb.sh 0.7 gvb07
wait_done
echo ALL_DONE > /tmp/sweep_done.flag
