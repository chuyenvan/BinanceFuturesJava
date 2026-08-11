#!/bin/bash
# Chuan bi truoc khi export lai label 1m bang jar DA VA:
# cach ly output cu (bug merge, 44 part mo coi + 1 quy 0-byte) sang thu muc _broken,
# tao thu muc sach. KHONG xoa gi — chi doi ten, con dao nguoc duoc.
OUT=/home/ubuntu/claudedata/.run/mcp_ce/label_prep.txt
exec > "$OUT" 2>&1
set -x
D=/home/ubuntu/claudedata/wfo1m/label_ds_1m
B=/home/ubuntu/claudedata/wfo1m/label_ds_1m_BROKEN_20260808
if [ -d "$B" ]; then echo "QUARANTINE DA TON TAI - dung lai, khong ghi de"; exit 3; fi
mv "$D" "$B" || exit 4
mkdir -p "$D" || exit 5
set +x
echo "=== ket qua ==="
echo -n "broken dir: "; du -sh "$B"
echo -n "new dir:    "; ls -la "$D" | wc -l
echo -n "disk free:  "; df -h /home | tail -1
echo "=== DONE ==="
