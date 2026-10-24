#!/bin/bash
cd ~/claude_master/vz_e1_wt/research/liqx_s1
echo "=== V1 $(date -u +%H:%M:%S)"
/usr/bin/time -f "MAXRSS_KB %M SEC %e EXIT %x" python3 v1_lookahead.py
echo "=== V3 $(date -u +%H:%M:%S)"
/usr/bin/time -f "MAXRSS_KB %M SEC %e EXIT %x" python3 v3_indep.py 2022-05-12 2022-06-13 2022-11-09
echo "=== V45 $(date -u +%H:%M:%S)"
/usr/bin/time -f "MAXRSS_KB %M SEC %e EXIT %x" python3 v45.py
echo "=== VALDONE $(date -u +%H:%M:%S)"
