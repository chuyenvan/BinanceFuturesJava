#!/bin/bash
wait_done(){ sleep 20; while pgrep -f 'WfoWorker strategy_window' >/dev/null 2>&1; do sleep 15; done; }
rm -f /tmp/ab_done.flag
bash /tmp/run_ab.sh -1 abcur
wait_done
bash /tmp/run_ab.sh 0 abgrid
wait_done
echo ALL_DONE > /tmp/ab_done.flag
