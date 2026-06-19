#!/usr/bin/env bash
# ============================================================================
# run_106.sh — Xuat lai feature Tool1 (filter + fix 1440) len Kaggle, TU DONG.
# Chay trong GIT BASH (khong PowerShell): bash run_106.sh
# Tu lam: upload jar -> test 1 kernel -> validate -> push 7 kernel con lai -> validate tong.
# Log: /d/claudedata/run106.log (xem song song: tail -f /d/claudedata/run106.log o cua so khac)
# ============================================================================
set -uo pipefail
REPO="/e/educa/source/github/20260415/BinanceFuturesJava"
STAGE="/c/Users/pc/java-run-lc-stage"
DATA="/d/claudedata"
LOG="$DATA/run106.log"
JAR="$REPO/target/binance-java-sdk-1.2.4-shaded.jar"
KERNELS=(ff40-2021 ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2 ff40-2025h1 ff40-2025h2x ff40-2026x)

log(){ echo "$(date '+%H:%M:%S') $*" | tee -a "$LOG"; }

# --- B0: kiem jar ---
log "=== B0: kiem jar ==="
[ -f "$JAR" ] || { log "❌ KHONG thay jar $JAR — chay 'mvn package -DskipTests' truoc"; exit 1; }
nclass=$(unzip -l "$JAR" 2>/dev/null | grep -c -E "EntrySignalFilter.class|ExportFeaturesForPythonTool.class|DataManagerAerospikeFloatSim.class")
[ "$nclass" -eq 3 ] || { log "❌ jar thieu class (thay $nclass/3) — rebuild"; exit 1; }
unzip -p "$JAR" com/binance/chuyennd/config/PrivateConfig.class 2>/dev/null > "$DATA/_pc.class"
grep -aq SANITIZED "$DATA/_pc.class" || { log "❌ jar CHUA sanitized — DUNG, khong upload (lo secret)"; exit 1; }
rm -f "$DATA/_pc.class"
log "✅ jar OK: 3 class + sanitized"

# --- B1: upload jar len dataset ---
log "=== B1: upload jar len Kaggle dataset java-run-lc ==="
cp "$JAR" "$STAGE/binance-java-sdk-1.2.4-shaded.jar"
( cd "$STAGE" && kaggle datasets version -p . -m "106 fix: filter + minutesToRead=1440 + retry" 2>&1 | tail -2 ) | tee -a "$LOG"
log "...cho dataset ready"
while [ "$(kaggle datasets status chuyendinh/java-run-lc 2>&1 | tr -d '[:space:]')" != "ready" ]; do sleep 15; done
log "✅ dataset ready"

# --- B2: xoa Tool1 cu local ---
log "=== B2: xoa Tool1 cu local (giu OI) ==="
rm -rf $DATA/oi-ff40-*/features_export_python_v3 2>/dev/null
df -h /c | tail -1 | tee -a "$LOG"

# --- ham cho 1 kernel COMPLETE ---
wait_kernel(){ local k=$1; while ! kaggle kernels status chuyendinh/$k 2>&1 | grep -qiE "complete|error"; do sleep 60; done; kaggle kernels status chuyendinh/$k 2>&1 | grep -oiE "complete|error"; }

# --- ham validate 1 kernel: in size Tool1 + so AEROSPIKE-FAIL + 0-record files ---
check_kernel(){
  local k=$1; local out="$DATA/out-$k"
  rm -rf "$out"; kaggle kernels output chuyendinh/$k -p "$out" >/dev/null 2>&1
  local t1="$out/features_export_python_v3"
  local sz=$(du -sm "$t1" 2>/dev/null | cut -f1)
  local fails=$(grep -ho "AEROSPIKE-FAIL" "$out"/*.log 2>/dev/null | wc -l)
  local zero=$(find "$t1" -name "*.bin.gz" -size -100c 2>/dev/null | wc -l)
  local nfile=$(find "$t1" -name "*.bin.gz" 2>/dev/null | wc -l)
  log "  [$k] Tool1=${sz}MB | files=$nfile | file_rong(<100B)=$zero | AEROSPIKE-FAIL=$fails"
  # tra ve loi neu co fail hoac file rong
  [ "$fails" -eq 0 ] && [ "$zero" -eq 0 ]
}

# --- B3: TEST 1 kernel (ff40-2021) ---
log "=== B3: TEST kernel ff40-2021 (cong quyet dinh) ==="
( cd "$STAGE/../ff40-2021" 2>/dev/null && kaggle kernels push -p . 2>&1 | tail -1 ) | tee -a "$LOG"
log "...cho ff40-2021 chay xong (poll 60s)"
st=$(wait_kernel ff40-2021); log "ff40-2021 status: $st"
if check_kernel ff40-2021; then
  log "✅ TEST PASS: filter ap dung, khong mat data. Tiep tuc push 7 kernel con lai."
else
  log "❌ TEST FAIL (file rong hoac AEROSPIKE-FAIL>0). DUNG. Kiem log truoc khi push tiep."
  exit 1
fi

# --- B4: push 7 kernel con lai (so le, dot <=4) ---
log "=== B4: push 7 kernel con lai (so le) ==="
REST=(ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2 ff40-2025h1 ff40-2025h2x ff40-2026x)
for k in "${REST[@]}"; do
  # cho slot < 4 (dem kernel dang chay cua minh)
  while true; do
    running=0
    for kk in "${KERNELS[@]}"; do kaggle kernels status chuyendinh/$kk 2>&1 | grep -qi running && running=$((running+1)); done
    [ "$running" -lt 4 ] && break
    sleep 60
  done
  log "  push $k (dang chay: $running)"
  ( cd "/c/Users/pc/$k" && kaggle kernels push -p . 2>&1 | tail -1 ) | tee -a "$LOG"
  sleep 20
done

# --- B5: cho tat ca COMPLETE + validate tong ---
log "=== B5: cho 8 kernel COMPLETE ==="
for k in "${KERNELS[@]}"; do st=$(wait_kernel $k); log "  $k: $st"; done

log "=== B6: validate tong ==="
total_fail=0; total_zero=0
for k in "${KERNELS[@]}"; do
  check_kernel $k || true
done
# tai het ve oi-ff40-* de merge (dong nhat ten thu muc)
log "=== B7: tai output ve $DATA/oi-ff40-* de merge 039 ==="
for k in "${KERNELS[@]}"; do
  yr=${k#ff40-}
  rm -rf "$DATA/oi-ff40-$yr"; kaggle kernels output chuyendinh/$k -p "$DATA/oi-ff40-$yr" >/dev/null 2>&1
done
log "=== validate_106.py tong ==="
python "$DATA/validate_106.py" $DATA/oi-ff40-*/features_export_python_v3 2>&1 | tee -a "$LOG"

log "🏁 XONG run_106.sh. Doc ket qua o tren + $LOG. Neu PASS -> data san sang merge 039."
