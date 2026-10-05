#!/bin/bash
# READ-ONLY probe 242 (2): dem theo ngay, cadence [GATE], OOM cuoi, su kien SL legacy tu 01/10 11:03
cd /home/chuyennd/java/v_t_m || exit 1
L=logs/full.log
echo "@@BYDAY"
for d in 28/09/2026 29/09/2026 30/09/2026 01/10/2026 02/10/2026; do
  printf "%s " $d
  for p in "OutOfMemoryError" "Exception" " ERROR " "\[GATE\]" "New price SL" "Update SL" "TS-GAP" "Create order market" "would-BUY" "Thiếu data BTC" "c3_shadow\] BAT"; do
    printf "%s=%s | " "$p" "$(grep -a "^$d" $L | grep -ac -- "$p")"; done; echo; done
echo "@@OOM_LAST"; grep -a 'OutOfMemoryError' $L | tail -3 | cut -c1-160
echo "@@BTC_LAST"; grep -a 'Thiếu data BTC' $L | tail -3 | cut -c1-120
echo "@@GATE_MIN_SINCE"
grep -a '\[GATE\]' $L | awk '{split($1,d,"/"); k=d[3] d[2] d[1] substr($2,1,2) substr($2,4,2); if (k>="202610011104") print k}' | sort -u | awk 'NR==1{f=$1} {n++; h=substr($1,1,10); c[h]++} END{print "gate_minutes_distinct=" n " first=" f " last=" $1; for (x in c) if (c[x]<58) print "short_hour " x " " c[x]}' | sort
echo "@@SL_EVENTS_SINCE_0110"
grep -a -E '^(01/10/2026|02/10/2026)' $L | grep -a -E 'New price SL|Update SL|TS-GAP|Create order market|SHADOW\] (arm|closed|would-BUY)' | awk '$2>="00" ' | cut -c1-200 | tail -40
echo "@@PASS_TIMING_0210"
grep -a '^02/10/2026' $L | grep -a 'selector tick total=' | sed -E 's/.*total=([0-9]+)ms.*/\1/' | sort -n | awk '{a[NR]=$1} END{print "n="NR" p50="a[int(NR*0.5)]" p90="a[int(NR*0.9)]" p99="a[int(NR*0.99)]" max="a[NR]}'
echo "@@SHADOWDIR"; ls -la --time-style=long-iso /home/chuyennd/java/shadow_c3/ 2>&1 | head; wc -l /home/chuyennd/java/shadow_c3/*.csv 2>&1 | head
echo "@@PREDSYM"; ls storage/data/predictionSymbol 2>&1 | head -3; ls storage/data/predictionSymbol 2>/dev/null | wc -l; ls storage/data/predictionSymbol 2>/dev/null | tail -3
for d in $(ls storage/data/predictionSymbol 2>/dev/null | tail -12); do echo "$d $(ls storage/data/predictionSymbol/$d | wc -l)"; done
echo "@@NOHUP"; grep -ac OutOfMemoryError logs/nohup.out; grep -a -E 'OutOfMemory|Killed|GC overhead' logs/nohup.out | tail -3 | cut -c1-160
echo "@@DMESG"; dmesg -T 2>/dev/null | grep -i -E 'killed process|out of memory' | tail -5 | cut -c1-200
echo "@@STARTSH"; grep -v -i -E "key|secret" bin/start.sh | grep -i -E 'java|Xm' | cut -c1-200
echo "@@FEATHEAD"; f=$(ls feat_dump/feat_dump_*.csv.gz | tail -2 | head -1); zcat $f 2>/dev/null | head -3 | cut -c1-600; zcat $f 2>/dev/null | wc -l
echo "@@END"
