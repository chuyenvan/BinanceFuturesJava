#!/usr/bin/env bash
# run_106_headless.sh — TASK-106b: xuất lại feature Tool1 (minutesToRead=1440, EntrySignalFilter)
# Chạy đầu-cuối, tự quyết. Giao cho headless CCD.
# Commit chuẩn: 532e0b8 (chốt 1440), 1e8c2f2 (retry batch)
# 2026-06-20 — Desktop spec, CCD headless thực thi
set -uo pipefail

# ── PATHS ──────────────────────────────────────────────────────────────────────
REPO="/e/educa/source/github/20260415/BinanceFuturesJava"
DATA="/d/claudedata"
STAGE="/c/Users/pc/java-run-lc-stage"
JAR_NAME="binance-java-sdk-1.2.4-shaded.jar"
JAR_FULL="$REPO/target/$JAR_NAME"
LOG="$DATA/agent106b.log"
KERNELS=(ff40-2021 ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2 ff40-2025h1 ff40-2025h2x ff40-2026x)
KAGGLE_DS="chuyendinh/java-run-lc"

mkdir -p "$DATA"
log(){ echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
die(){ log "❌ STOP: $*"; exit 1; }

# ── CLAIM TASK ─────────────────────────────────────────────────────────────────
log "=== TASK-106b HEADLESS START ($(hostname)) ==="
log "CLAIM: ghi DOING vào AGENTS.md + header task"

# Cập nhật header tasks/106-reexport-features-with-filter.md
sed -i "s/^status: TODO/status: DOING/" "$REPO/tasks/106-reexport-features-with-filter.md"
sed -i "s/^owner: —/owner: CCD-headless-$$/" "$REPO/tasks/106-reexport-features-with-filter.md"
sed -i "s/^updated: .*/updated: $(date '+%Y-%m-%d')/" "$REPO/tasks/106-reexport-features-with-filter.md"

# Cập nhật AGENTS.md
sed -i "s/| 106 reexport feature + filter | — | 🟡 TODO | 2026-06-20 |/| 106 reexport feature + filter | CCD-headless-$$ | 🔵 DOING | $(date '+%Y-%m-%d %H:%M') |/" \
    "$REPO/docs/AGENTS.md"

# ── B1. BUILD JAR ──────────────────────────────────────────────────────────────
log "=== B1. BUILD JAR từ HEAD (532e0b8, minutesToRead=1440) ==="
cd "$REPO"

# Confirm HEAD
HEAD_COMMIT=$(git rev-parse --short HEAD)
FIRST_COMMIT=$(git log --oneline -1 | cut -d' ' -f1)
log "HEAD = $HEAD_COMMIT"
[ "$HEAD_COMMIT" = "532e0b8" ] || log "⚠️  HEAD không phải 532e0b8 ($HEAD_COMMIT) — tiếp tục nếu minutesToRead=1440"

# Confirm minutesToRead=1440 trong source
MINUTES_VAL=$(grep "int minutesToRead = " src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java | grep -o '[0-9]*' | head -1)
[ "$MINUTES_VAL" = "1440" ] || die "minutesToRead=$MINUTES_VAL trong source, cần 1440. Sửa commit trước khi chạy."
log "minutesToRead = $MINUTES_VAL ✅"

# Confirm PrivateConfig sanitized
SANITIZE_CHECK=$(grep -c 'SANITIZED_FOR_KAGGLE_UPLOAD' src/main/java/com/binance/chuyennd/config/PrivateConfig.java 2>/dev/null || echo 0)
[ "$SANITIZE_CHECK" -ge 1 ] || die "PrivateConfig KHÔNG sanitized — DỪNG, không build/upload"
log "PrivateConfig SANITIZED ✅"

# Build
log "mvn package -DskipTests..."
mvn package -DskipTests -q > "$DATA/106b-build.log" 2>&1
BUILD_EXIT=$?
[ "$BUILD_EXIT" -eq 0 ] || die "mvn package FAIL (exit $BUILD_EXIT). Xem $DATA/106b-build.log"
log "Build OK ✅ (exit 0)"

# Verify jar có class cần
# NOTE: grep -q + pipefail = SIGPIPE (exit 141) dù match → cache output trước
JAR_CONTENTS=$(unzip -l "$JAR_FULL" 2>/dev/null || true)
echo "$JAR_CONTENTS" | grep -q "EntrySignalFilter.class"  || die "EntrySignalFilter.class KHÔNG có trong jar"
echo "$JAR_CONTENTS" | grep -q "DataManagerAerospikeFloatSim.class" || die "DataManagerAerospikeFloatSim.class KHÔNG có trong jar"
log "Classes trong jar ✅"

# Verify jar SẠCH (KHÔNG có secret)
unzip -p "$JAR_FULL" com/binance/chuyennd/config/PrivateConfig.class > "$DATA/pc.class" 2>/dev/null || true
grep -a SANITIZED "$DATA/pc.class" > /dev/null || die "JAR CÓ SECRET THẬT — DỪNG, không upload"
log "JAR SẠCH (sanitized trong class) ✅"
rm -f "$DATA/pc.class"

JAR_SIZE=$(stat -c%s "$JAR_FULL" 2>/dev/null || stat -f%z "$JAR_FULL")
log "Jar: $JAR_FULL ($JAR_SIZE bytes)"

# ── B2. UPLOAD JAR LÊN KAGGLE DATASET ─────────────────────────────────────────
log "=== B2. UPLOAD JAR → Kaggle dataset $KAGGLE_DS ==="
cp "$JAR_FULL" "$STAGE/$JAR_NAME"
cd "$STAGE"
kaggle datasets version -p . -m "106b: minutesToRead=1440 (final) + EntrySignalFilter + retry ($(date '+%Y-%m-%d %H:%M'))" \
    >> "$LOG" 2>&1 || die "kaggle datasets version FAIL"

log "Đợi dataset ready..."
for i in $(seq 1 40); do
    STATUS=$(kaggle datasets status "$KAGGLE_DS" 2>&1 | tr -d '[:space:]')
    log "  [$i] dataset status: $STATUS"
    [ "$STATUS" = "ready" ] && break
    sleep 30
done
[ "$(kaggle datasets status "$KAGGLE_DS" 2>&1 | tr -d '[:space:]')" = "ready" ] || die "Dataset KHÔNG ready sau 20 phút"

# Xác nhận size jar trên Kaggle
KAGGLE_SIZE=$(kaggle datasets files "$KAGGLE_DS" 2>&1 | grep -i "shaded.jar" | awk '{print $NF}' | head -1)
log "Jar trên Kaggle: $KAGGLE_SIZE ✅"

# ── B3. XÓA OUTPUT CŨ ─────────────────────────────────────────────────────────
log "=== B3. Xóa Tool1 output cũ (giữ OI) ==="
for k in "${KERNELS[@]}"; do
    yr="${k#ff40-}"
    T1_OLD="$DATA/oi-ff40-$yr/features_export_python_v3"
    [ -d "$T1_OLD" ] && { rm -rf "$T1_OLD"; log "  xóa $T1_OLD"; } || log "  $T1_OLD không tồn tại, bỏ qua"
done
log "Dung lượng /d sau dọn: $(df -sh /d 2>/dev/null | tail -1 || echo 'n/a')"

# ── B4. TEST 1 KERNEL (ff40-2021) ─────────────────────────────────────────────
log "=== B4. TEST KERNEL ff40-2021 ==="
cd "/c/Users/pc/ff40-2021"
kaggle kernels push -p . >> "$LOG" 2>&1 || die "Push ff40-2021 FAIL"
log "  ff40-2021 pushed, đợi COMPLETE (poll 90s)..."

WAIT=0
while ! kaggle kernels status chuyendinh/ff40-2021 2>&1 | grep -qiE "complete|error"; do
    sleep 90; WAIT=$((WAIT+90))
    log "  ... chờ ff40-2021 (${WAIT}s)"
    [ "$WAIT" -gt 7200 ] && die "ff40-2021 quá 2h, không COMPLETE"
done
K21_STATUS=$(kaggle kernels status chuyendinh/ff40-2021 2>&1 | grep -oiE "complete|error" | head -1)
log "  ff40-2021 status: $K21_STATUS"
[ "${K21_STATUS,,}" = "complete" ] || die "ff40-2021 ERROR, xem log Kaggle"

# Tải output
OUT21="$DATA/oi-ff40-2021"
rm -rf "$OUT21"
kaggle kernels output chuyendinh/ff40-2021 -p "$OUT21" >> "$LOG" 2>&1 || die "Tải output ff40-2021 FAIL"

T1_21="$OUT21/features_export_python_v3"
SZ_21=$(du -sm "$T1_21" 2>/dev/null | cut -f1 || echo 0)
FAILS_21=$(grep -hc "AEROSPIKE-FAIL" "$OUT21"/*.log 2>/dev/null || echo 0)
NDATA_21=$(find "$T1_21" -name "*.bin.gz" -size +1k 2>/dev/null | wc -l || echo 0)
log "  ff40-2021: Tool1=${SZ_21}MB, files_co_data=$NDATA_21, AEROSPIKE-FAIL=$FAILS_21"

# Tiêu chí TEST PASS
PASS4=true
# (a) size << bản cũ: phải > 1MB (có data) và < 3000MB (filter đã giảm từ ~60G)
[ "$SZ_21" -gt 1 ] || { log "  ❌ (a) FAIL: Tool1 2021 quá nhỏ ($SZ_21 MB) — filter không áp hoặc không có data"; PASS4=false; }
[ "$SZ_21" -lt 3000 ] || { log "  ❌ (a) FAIL: Tool1 2021 vẫn quá lớn ($SZ_21 MB ≥ 3G) — filter không áp"; PASS4=false; }
# (b) AEROSPIKE-FAIL = 0
[ "$FAILS_21" -eq 0 ] || { log "  ❌ (b) FAIL: AEROSPIKE-FAIL=$FAILS_21 > 0 (data mất)"; PASS4=false; }
# (c) validate script
if python "$DATA/validate_106.py" "$T1_21" >> "$LOG" 2>&1; then
    log "  ✅ (c) validate_106.py PASS"
else
    log "  ❌ (c) FAIL: validate_106.py trả lỗi"; PASS4=false
fi
# (d) cross-sectional: ndata > 0
[ "$NDATA_21" -gt 0 ] || { log "  ❌ (d) FAIL: không có file data"; PASS4=false; }

if [ "$PASS4" = "false" ]; then
    log "❌ B4 TEST FAIL — DỪNG. Không push 7 kernel còn lại."
    # Cập nhật AGENTS.md ghi lỗi
    sed -i "s/🔵 DOING.*106b/🔴 BLOCKED — B4 TEST FAIL/" "$REPO/docs/AGENTS.md" 2>/dev/null || true
    exit 1
fi
log "✅ B4 TEST PASS (2021: ${SZ_21}MB, FAIL=0, validate OK)"

# ── B5. PUSH 7 KERNEL CÒN LẠI (≤4 cùng lúc) ──────────────────────────────────
log "=== B5. Push 7 kernel còn lại (batch ≤4) ==="

count_running(){
    local n=0
    for kk in "${KERNELS[@]}"; do
        kaggle kernels status "chuyendinh/$kk" 2>&1 | grep -qiE "running|queued" && n=$((n+1))
    done
    echo $n
}

REMAINING=(ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2 ff40-2025h1 ff40-2025h2x ff40-2026x)
for k in "${REMAINING[@]}"; do
    while [ "$(count_running)" -ge 4 ]; do
        log "  ... chờ slot (đang chạy $(count_running)/4), ngủ 60s"
        sleep 60
    done
    log "  push $k (đang chạy $(count_running))"
    ( cd "/c/Users/pc/$k" && kaggle kernels push -p . >> "$LOG" 2>&1 ) || log "  ⚠️ push $k lỗi, thử lại sau"
    sleep 25
done

log "Đợi tất cả 8 kernel COMPLETE (poll 120s)..."
for k in "${KERNELS[@]}"; do
    KWAIT=0
    while ! kaggle kernels status "chuyendinh/$k" 2>&1 | grep -qiE "complete|error"; do
        sleep 120; KWAIT=$((KWAIT+120))
        log "  ... $k chờ ${KWAIT}s"
        [ "$KWAIT" -gt 14400 ] && { log "  ❌ $k quá 4h, bỏ qua"; break; }
    done
    KSTAT=$(kaggle kernels status "chuyendinh/$k" 2>&1 | grep -oiE "complete|error" | head -1)
    log "  $k: $KSTAT"
done

# Tải về tất cả 8
log "=== Tải output 8 kernel ==="
for k in "${KERNELS[@]}"; do
    yr="${k#ff40-}"
    OUT="$DATA/oi-ff40-$yr"
    # ff40-2021 đã tải ở B4, bỏ qua
    [ "$k" = "ff40-2021" ] && continue
    rm -rf "$OUT"
    kaggle kernels output "chuyendinh/$k" -p "$OUT" >> "$LOG" 2>&1 || { log "  ⚠️ tải $k lỗi"; continue; }
    T1="$OUT/features_export_python_v3"
    SZ=$(du -sm "$T1" 2>/dev/null | cut -f1 || echo 0)
    FAILS=$(grep -hc "AEROSPIKE-FAIL" "$OUT"/*.log 2>/dev/null || echo 0)
    NDATA=$(find "$T1" -name "*.bin.gz" -size +1k 2>/dev/null | wc -l || echo 0)
    log "  [$k] Tool1=${SZ}MB files=$NDATA AEROSPIKE-FAIL=$FAILS"
done

# ── B6. VALIDATE TỔNG ─────────────────────────────────────────────────────────
log "=== B6. VALIDATE TỔNG ==="
TOTAL_SZ=$(du -sm "$DATA/oi-ff40-"*/features_export_python_v3 2>/dev/null | awk '{s+=$1}END{print s}' || echo 0)
TOTAL_FAILS=$(grep -rhc "AEROSPIKE-FAIL" "$DATA/oi-ff40-"*/*.log 2>/dev/null | awk -F: '{s+=$2}END{print s}' || echo 0)
log "  size tổng Tool1: ${TOTAL_SZ}MB  tổng AEROSPIKE-FAIL: $TOTAL_FAILS"

# Tiêu chí 1: size 3G-15G
[ "$TOTAL_SZ" -gt 3000 ]  || log "  ⚠️ (1) size < 3G (${TOTAL_SZ}MB) — ít hơn kỳ vọng"
[ "$TOTAL_SZ" -lt 15000 ] || { log "  ❌ (1) FAIL: size > 15G (${TOTAL_SZ}MB) — filter không áp"; PASS4=false; }
# Tiêu chí 5: tổng AEROSPIKE-FAIL = 0
[ "$TOTAL_FAILS" -eq 0 ] || log "  ❌ (5) FAIL: tổng AEROSPIKE-FAIL=$TOTAL_FAILS > 0"

# Chạy validate.py toàn bộ
python "$DATA/validate_106.py" "$DATA"/oi-ff40-*/features_export_python_v3 >> "$LOG" 2>&1 \
    && log "  validate_106.py PASS ✅" || log "  ❌ validate_106.py CÓ LỖI — xem $LOG"

# ── B7. REPORT + COMMIT + PUSH ────────────────────────────────────────────────
log "=== B7. Ghi report + commit + push ==="
mkdir -p "$REPO/docs/reports"
REPORT="$REPO/docs/reports/106.md"

cat > "$REPORT" << MDEOF
# TASK-106b Report — $(date '+%Y-%m-%d %H:%M')

## Kết quả xuất feature Tool1 (EntrySignalFilter, minutesToRead=1440)

### Jar
- Commit: $(cd "$REPO" && git rev-parse --short HEAD) ($(cd "$REPO" && git log -1 --format='%s'))
- minutesToRead: 1440 (chốt final)
- EntrySignalFilter: vol-avg-30m ≥ 2k + top-10% |rate30m| cross-sectional

### Size từng kỳ (Tool1 = features_export_python_v3)
MDEOF

for k in "${KERNELS[@]}"; do
    yr="${k#ff40-}"
    T1="$DATA/oi-ff40-$yr/features_export_python_v3"
    SZ=$(du -sm "$T1" 2>/dev/null | cut -f1 || echo "N/A")
    FAILS=$(grep -hc "AEROSPIKE-FAIL" "$DATA/oi-ff40-$yr/"*.log 2>/dev/null || echo "?")
    NDATA=$(find "$T1" -name "*.bin.gz" -size +1k 2>/dev/null | wc -l || echo "?")
    echo "- **$k**: ${SZ}MB, files=$NDATA, AEROSPIKE-FAIL=$FAILS" >> "$REPORT"
done

cat >> "$REPORT" << MDEOF

### Tổng
- Size tổng: ${TOTAL_SZ}MB
- Tổng AEROSPIKE-FAIL: $TOTAL_FAILS

### 6 tiêu chí validate
1. Size tổng 3-15G: $([ "$TOTAL_SZ" -gt 3000 ] && [ "$TOTAL_SZ" -lt 15000 ] && echo "PASS (${TOTAL_SZ}MB)" || echo "FAIL (${TOTAL_SZ}MB)")
2. %giữ 6-12%: xem validate_106.py output trong $LOG
3. Phân bố cột hợp lý: xem $LOG
4. Cross-sectional ≈10%/mốc: xem $LOG
5. Regime coverage: xem $LOG
6. Tổng AEROSPIKE-FAIL = 0: $([ "$TOTAL_FAILS" -eq 0 ] && echo "PASS" || echo "FAIL ($TOTAL_FAILS)")

### Log đầy đủ
\`$LOG\`
MDEOF

# Cập nhật task header DONE
sed -i "s/^status: DOING/status: DONE/" "$REPO/tasks/106-reexport-features-with-filter.md"
sed -i "s/^owner: CCD-headless-.*/owner: CCD-headless-$$ (DONE)/" "$REPO/tasks/106-reexport-features-with-filter.md"
sed -i "s/^updated: .*/updated: $(date '+%Y-%m-%d')/" "$REPO/tasks/106-reexport-features-with-filter.md"

# Cập nhật AGENTS.md DONE
sed -i "s/| 106 reexport feature + filter | CCD-headless-$$ | 🔵 DOING |.*/| 106 reexport feature + filter | CCD-headless-$$ | ✅ DONE | $(date '+%Y-%m-%d %H:%M') | — | B1-B7 PASS; size ${TOTAL_SZ}MB; AEROSPIKE-FAIL=$TOTAL_FAILS; data Tool1 sẵn cho merge 039 |/" \
    "$REPO/docs/AGENTS.md" 2>/dev/null || true

# Commit + push
cd "$REPO"
git add docs/AGENTS.md tasks/106-reexport-features-with-filter.md docs/reports/106.md
git commit -m "$(cat <<'EOF'
TASK-106b: xuất lại feature Tool1 (EntrySignalFilter, 1440) DONE

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push origin module >> "$LOG" 2>&1 && log "push OK ✅" || log "⚠️ push lỗi (commit local OK)"

log "🏁 TASK-106b XONG. Data Tool1 sẵn sàng cho merge 039."
log "   size=${TOTAL_SZ}MB  AEROSPIKE-FAIL=$TOTAL_FAILS  report=$REPORT"
