#!/usr/bin/env bash
# run_106_parallel.sh — push 8 kernel ff40 SONG SONG (jar moi 1440+retry), cho xong, validate, tai ve.
# Da function-test filter + do toc do (extractFeatures 95%, ~26ph/nam). Chay song song 5 Kaggle.
set -uo pipefail
DATA="/d/claudedata"; LOG="$DATA/run106p.log"
KERNELS=(ff40-2021 ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2 ff40-2025h1 ff40-2025h2x ff40-2026x)
log(){ echo "$(date '+%H:%M:%S') $*" >> "$LOG"; }

count_running(){ local n=0; for k in "${KERNELS[@]}"; do kaggle kernels status chuyendinh/$k 2>&1 | grep -qiE "running|queued" && n=$((n+1)); done; echo $n; }
wait_slot(){ while [ "$(count_running)" -ge 5 ]; do sleep 45; done; }
wait_kernel(){ local k=$1; while ! kaggle kernels status chuyendinh/$k 2>&1 | grep -qiE "complete|error"; do sleep 60; done; kaggle kernels status chuyendinh/$k 2>&1 | grep -oiE "complete|error"; }
check_kernel(){
  local k=$1; local out="$DATA/oi-ff40-${k#ff40-}"
  rm -rf "$out"; kaggle kernels output chuyendinh/$k -p "$out" >/dev/null 2>&1
  local t1="$out/features_export_python_v3"
  local sz=$(du -sm "$t1" 2>/dev/null | cut -f1)
  local fails=$(grep -ho "AEROSPIKE-FAIL" "$out"/*.log 2>/dev/null | wc -l)
  local zero=$(find "$t1" -name "*.bin.gz" -size -100c 2>/dev/null | wc -l)
  local nfile=$(find "$t1" -name "*.bin.gz" 2>/dev/null | wc -l)
  log "  [$k] Tool1=${sz}MB files=$nfile rong=$zero AEROSPIKE-FAIL=$fails"
}

log "=== PUSH 8 KERNEL SONG SONG (jar 1440+retry) ==="
for k in "${KERNELS[@]}"; do
  # ff40-2023 dang chay jar moi roi -> bo qua push lai
  if [ "$k" = "ff40-2023" ] && kaggle kernels status chuyendinh/$k 2>&1 | grep -qi running; then
    log "  $k dang RUNNING (jar moi) -> giu nguyen"; continue
  fi
  wait_slot
  log "  push $k (running=$(count_running))"
  ( cd "/c/Users/pc/$k" && kaggle kernels push -p . >/dev/null 2>&1 )
  sleep 25
done

log "=== CHO 8 KERNEL XONG ==="
for k in "${KERNELS[@]}"; do st=$(wait_kernel $k); log "  $k: $st"; done

log "=== VALIDATE + TAI VE ==="
for k in "${KERNELS[@]}"; do check_kernel $k; done

log "=== VALIDATE TONG (validate_106.py) ==="
python "$DATA/validate_106.py" $DATA/oi-ff40-*/features_export_python_v3 >> "$LOG" 2>&1

# tong hop nhanh
total_fail=$(grep -o "AEROSPIKE-FAIL=[0-9]*" "$LOG" | grep -oE "[0-9]+" | paste -sd+ | bc 2>/dev/null || echo "?")
total_zero=$(grep -o "rong=[0-9]*" "$LOG" | grep -oE "[0-9]+" | paste -sd+ | bc 2>/dev/null || echo "?")
log "🏁 XONG. Tong AEROSPIKE-FAIL=$total_fail | tong file rong=$total_zero"
log "   Neu fail=0 va rong=0 -> data DU+DUNG, san sang merge 039."
