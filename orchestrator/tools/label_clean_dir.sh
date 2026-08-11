#!/bin/bash
# Xoa output DANG DO cua lan chay bi huy (fixed-code APPEND khi mo lai -> con file cu = nhan doi dong).
# Chi xoa trong label_ds_1m, va chi khi thu muc quarantine _BROKEN_ da ton tai (=> du lieu cu da an toan).
OUT=/home/ubuntu/claudedata/.run/mcp_ce/label_clean.txt
exec > "$OUT" 2>&1
D=/home/ubuntu/claudedata/wfo1m/label_ds_1m
B=/home/ubuntu/claudedata/wfo1m/label_ds_1m_BROKEN_20260808
[ -d "$B" ] || { echo "ABORT: khong thay quarantine $B"; exit 3; }
echo "truoc khi don:"; ls -la "$D"
rm -f "$D"/*.pb "$D"/*.meta.json "$D"/*.log
echo "sau khi don:"; ls -la "$D"
echo -n "so file con lai: "; ls "$D" | wc -l
echo "=== DONE ==="
