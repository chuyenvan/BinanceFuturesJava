#!/bin/bash
# book_snap.sh — V12 ADD1: anh chup so giay twin (ShadowBookC3 open_positions.csv) + MOI su kien [SHADOW] open/closed tu full.log 242
# (CHI DOC) cung mot luc => tap coin dang giu theo phut = anh chup tru/cong su kien sau phut do (truy nguoc).
set -euo pipefail
O=$HOME/claude_master/parity_v12w/shadow_book; mkdir -p $O
TS=$(date -u +%Y%m%dT%H%M%SZ)
ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242 \
  'date +%s%3N; cat /home/chuyennd/java/shadow_c3/open_positions.csv; echo "@@EV"; grep -a -h -E "ShadowBookC3: \[SHADOW\] (open|closed) " /home/chuyennd/java/v_t_m/logs/full.log' < /dev/null > $O/snap_$TS.txt
head -1 $O/snap_$TS.txt; grep -c -v -E '^(#|sym,)' <(sed -n '2,/^@@EV/p' $O/snap_$TS.txt | grep -v '^@@EV') || true
echo "$O/snap_$TS.txt"
