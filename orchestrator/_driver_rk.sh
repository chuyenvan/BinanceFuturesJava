#!/bin/bash
wait_done(){ sleep 20; while pgrep -f 'WfoWorker strategy_window' >/dev/null 2>&1; do sleep 15; done; }
rm -f /tmp/rk_done.flag
bash /tmp/run_rk.sh 5 rk05
wait_done
bash /tmp/run_rk.sh 8 rk08
wait_done
bash /tmp/run_rk.sh 12 rk12
wait_done
echo ALL_DONE > /tmp/rk_done.flag
