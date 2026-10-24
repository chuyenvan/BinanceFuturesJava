#!/bin/bash
# LIQX_S1 chain after s1_build: mkt -> episodes -> returns -> score -> x14 ; each with /usr/bin/time max RSS
cd ~/claude_master/vz_e1_wt/research/liqx_s1
S=~/claude_master/liqx_wk/s1
while ps aux | grep -q "[s]1_build.py"; do sleep 15; done
for st in s1_mkt s1_episodes s1_returns s1_score s1_x14; do
  echo "=== $st $(date -u +%H:%M:%S)"
  /usr/bin/time -f "MAXRSS_KB %M SEC %e EXIT %x" python3 $st.py || { echo "FAIL $st"; exit 1; }
done
echo "=== ALLDONE $(date -u +%H:%M:%S)"
