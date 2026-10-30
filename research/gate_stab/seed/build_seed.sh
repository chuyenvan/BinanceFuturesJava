#!/bin/bash
# build_seed.sh — PREREG_PARITY_V12_DRY ADD3/ADD4. Dung lai seed = A (sim, ts < T_cut) U C (live sach tu T_cut toi bay gio).
# CHI DOC 242 (scp/tar/grep). Khong ghi 242. Chay tren Oracle:  bash ~/claude_master/gst1030/seed/build_seed.sh
# Bien: A=<file dump sim> (mac dinh seed/A_dump.bin), TCUT_MS (mac dinh 2026-11-01 00:00 +07), EXINFO (exchangeInfo moi nhat)
set -euo pipefail
S=~/claude_master/gst1030/seed
A=${A:-$S/A_dump.bin}
TCUT_MS=${TCUT_MS:-1793466000000}
EXINFO=${EXINFO:-$HOME/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz}
TS=$(date +%Y%m%d_%H%M%S); L=$S/live_$TS; mkdir -p $L/sel
AV=$(df --output=avail -BG / | tail -1 | tr -dc 0-9); [ "$AV" -ge 15 ] || { echo "DIA < 15G -> DUNG"; exit 3; }
K="-P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"; R=root@103.157.218.242; V=/home/chuyennd/java/v_t_m
scp -q $K $R:$V/run/gate_ratio_live.bin $L/gate_ratio_live.bin
ssh ${K/-P/-p} $R "cd $V/feat_dump && tar cf - sel_dump_*.csv.gz" < /dev/null | tar xf - -C $L/sel
ssh ${K/-P/-p} $R "cd $V && grep -a -h -E 'ShadowBookC3: \[SHADOW\] (open|closed)' logs/full.log.1 logs/full.log" < /dev/null | sed -E 's/INFO.*\[SHADOW\]//' > $L/shadow_events_all.txt
md5sum $L/gate_ratio_live.bin; ls $L/sel | wc -l; wc -l < $L/shadow_events_all.txt
AARG=""; [ -f "$A" ] && AARG="--a $A" || echo "CANH BAO: khong co A ($A) -> seed chi gom C"
mkdir -p ~/claude_master/locks
flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 python3 $S/seed_build.py --live $L --tcut-ms $TCUT_MS $AARG --exinfo $EXINFO --out $S/out_$TS
ls -la $S/out_$TS; (cd $S/out_$TS && md5sum seed_*.bin)
