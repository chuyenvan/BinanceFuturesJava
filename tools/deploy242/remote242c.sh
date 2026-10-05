#!/bin/bash
# READ-ONLY snapshot RSS lan 2
cd /home/chuyennd/java/v_t_m || exit 1
date '+%F %T %z'
ps -eo pid,etime,rss,args --sort=-rss | grep -i 'java' | grep -v grep | cut -c1-120
free -m | head -3
grep -a '\[GATE\]' logs/full.log | tail -1 | cut -c1-200
grep -a '^02/10/2026' logs/full.log | grep -ac -E 'OutOfMemoryError|Exception| ERROR '
grep -a '^02/10/2026' logs/full.log | grep -a -E 'New price SL|Update SL|TS-GAP' | wc -l
