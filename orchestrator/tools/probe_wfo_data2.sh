#!/bin/bash
OUT=/home/ubuntu/claudedata/.run/mcp_ce/probe_out2.txt
exec > "$OUT" 2>&1
J=/home/ubuntu/java/simulator
echo "=== 1. jar mac dinh cua nut label_export ==="
ls -la $J/gatecount.jar 2>&1
echo "=== 2. jar nao co BAN VA merge (mergeAllQuarters / countRowsInPb) ==="
for f in $J/gatecount.jar $J/gatecount_gate_20260808.jar $J/gatecount_t1c2b_20260808.jar $J/gatecount_pb_20260807.jar; do
  if [ -f "$f" ]; then
    n=$(javap -p -cp "$f" com.binance.chuyennd.ai_ml.features.export.ExportFundingLabel 2>/dev/null | grep -cE "mergeAllQuarters|countRowsInPb")
    echo "$(basename $f) : match=$n"
  fi
done
echo "=== 3. label_ds_1m: file da GOP (khong .partN) vs parts ==="
echo -n "merged files: "; ls $J/../../claudedata/wfo1m/label_ds_1m 2>/dev/null | grep -c "\.pb$" 
ls -la /home/ubuntu/claudedata/wfo1m/label_ds_1m | grep -v part | head -12
echo -n "part files: "; ls /home/ubuntu/claudedata/wfo1m/label_ds_1m | grep -c part
echo -n "du -sh: "; du -sh /home/ubuntu/claudedata/wfo1m/label_ds_1m
echo "=== 4. aerospike symbol_lifecycle co du lieu khong ==="
AS=$(find / -maxdepth 5 -name asinfo -type f 2>/dev/null | head -1)
echo "asinfo=$AS"
if [ -n "$AS" ]; then "$AS" -h 127.0.0.1 -p 3222 -v "sets/test" | tr ';' '\n' | grep -E "symbol_lifecycle|symbol_mapper|kline_1m_opt|market_data" ; fi
echo "=== 5. t1c + features_new ==="
echo -n "t1c: "; ls /home/ubuntu/claudedata/wfo1m/t1c | wc -l
echo -n "features_new: "; ls /home/ubuntu/claudedata/wfo1m/features_export_python_v3_1m_new | wc -l
echo "=== 6. git sha source tren Oracle ==="
cd /home/ubuntu/BinanceFuturesJava 2>/dev/null && git log -1 --format="%h %ad %s" --date=short 2>&1 | head -2
echo "=== DONE ==="
