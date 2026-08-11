#!/bin/bash
wait_done(){ sleep 20; while pgrep -f 'WfoWorker strategy_window' >/dev/null 2>&1; do sleep 15; done; }
rm -f /tmp/full_done.flag
bash /tmp/run_gvb_full.sh 0.3 gvbf03
wait_done
bash /tmp/run_gvb_full.sh 0.4 gvbf04
wait_done
echo ALL_DONE > /tmp/full_done.flag
