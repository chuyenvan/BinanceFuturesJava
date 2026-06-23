#!/usr/bin/env bash
# run_final.sh — push het 8 kernel ff40 (jar 10080+retry), cho xong, validate, tai ve.
# Jar dataset = 98876658 (10080+retry, ban dung). Kaggle chay 5 song song, con lai xep hang.
set -uo pipefail
DATA="/d/claudedata"; LOG="$DATA/runfinal.log"
KERNELS=(ff40-2021 ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2 ff40-2025h1 ff40-2025h2x ff40-2026x)
log(){ echo "$(date '+%H:%M:%S') $*" >> "$LOG"; }

# dem kernel ff40 dang chiem slot (running/queued)
count_running(){ local n=0; for kk in "${KERNELS[@]}"; do kaggle kernels status chuyendinh/$kk 2>&1 | grep -qiE "running|queued" && n=$((n+1)); done; echo $n; }
# kernel da COMPLETE voi jar moi chua? (tranh push lai cai dang chay dung jar dung)
is_done(){ kaggle kernels status chuyendinh/$1 2>&1 | grep -qiE "complete"; }

log "=== PUSH 8 KERNEL (jar 10080+retry, dataset 98876658) — DOI SLOT <5 ==="
for k in "${KERNELS[@]}"; do
  # neu dang RUNNING (jar moi push truoc do) thi giu nguyen, khong push de
  if kaggle kernels status chuyendinh/$k 2>&1 | grep -qiE "running|queued"; then
    log "  $k dang RUNNING -> giu nguyen"; continue
  fi
  # doi slot trong (<5 ff40 dang chay) — Kaggle gioi han 5 CPU session
  while [ "$(count_running)" -ge 4 ]; do log "  ...$k cho slot (dang chay $(count_running))"; sleep 60; done
  ( cd "/c/Users/pc/$k" && kaggle kernels push -p . >/dev/null 2>&1 ) && log "  pushed $k" || log "  PUSH LOI $k (thu lai sau)"
  sleep 25
done

log "=== CHO 8 KERNEL XONG (poll 90s) ==="
for k in "${KERNELS[@]}"; do
  while ! kaggle kernels status chuyendinh/$k 2>&1 | grep -qiE "complete|error"; do sleep 90; done
  st=$(kaggle kernels status chuyendinh/$k 2>&1 | grep -oiE "complete|error")
  log "  $k: $st"
done

log "=== TAI VE + CHECK tung kernel ==="
for k in "${KERNELS[@]}"; do
  yr=${k#ff40-}; out="$DATA/oi-ff40-$yr"
  rm -rf "$out"; kaggle kernels output chuyendinh/$k -p "$out" >/dev/null 2>&1
  t1="$out/features_export_python_v3"
  sz=$(du -sm "$t1" 2>/dev/null | cut -f1)
  fails=$(grep -ho "AEROSPIKE-FAIL" "$out"/*.log 2>/dev/null | wc -l)
  ndata=$(find "$t1" -name "*.bin.gz" -size +1k 2>/dev/null | wc -l)
  log "  [$k] Tool1=${sz}MB file_co_data=$ndata AEROSPIKE-FAIL=$fails"
done

log "=== VALIDATE TONG ==="
python "$DATA/validate_106.py" $DATA/oi-ff40-*/features_export_python_v3 >> "$LOG" 2>&1
log "🏁 XONG. Kiem: 2024/2025 phai LON (bull), AEROSPIKE-FAIL phai 0, du 4 quy moi nam."
