#!/bin/bash
OUT=/home/ubuntu/claudedata/.run/mcp_ce/probe_out3.txt
exec > "$OUT" 2>&1
L=/home/ubuntu/claudedata/wfo1m/label_ds_1m/label_export_pb.log
echo "=== 1. lifecycle nap bao nhieu symbol (lan chay 07-08/08) ==="
grep -E "SymbolLifecycleManager|symbol_lifecycle" "$L" | head -6
echo "=== 2. dong dau + dong cuoi cua log ==="
head -3 "$L"
echo "--- tail ---"
tail -6 "$L"
echo "=== 3. cac quy da DONG (dem lan) ==="
grep -oE "dong file quy [0-9_a-z]+|đóng file quý [0-9_a-z]+" "$L" | sort | uniq -c | head -30
echo "=== 4. co dong GOP nao khong ==="
grep -cE "Da gop|Đã gộp|mergeAllQuarters" "$L"
echo "=== 5. lifecycle lastSeen moi nhat (neu log co) ==="
grep -iE "lastSeen|alive|20260[4-7]" "$L" | head -5
echo "=== DONE ==="
