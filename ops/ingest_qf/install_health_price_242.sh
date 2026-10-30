#!/usr/bin/env bash
# =============================================================================
# install_health_price_242.sh — them kiem TUOI GIA collectData vao ~/ops/health_242.sh (Oracle, cron */5). Owner chay SAU deploy QF2.
#   DRY=1 bash ~/claude_master/deploy/install_health_price_242.sh   # in ban va, chay health --dry-run tren ban tam, khong doi gi
#   bash ~/claude_master/deploy/install_health_price_242.sh          # go YES 1 lan; tu khoi phuc neu ban moi loi
# Them: doc dong [REST-BUDGET] moi nhat cua collectData (full.log 242): canh bao PRICE_REALTIME_STALE khi price_gap_max_ms
#       > 15000 hoac price_age_ms > 15000; INGEST_BUDGET_LOG_STALE khi dong budget cu > MAX_AGE. Chi kich hoat khi log CO
#       dong [REST-BUDGET] (jar QF2) — jar cu khong bao nham. KHONG dong cham 242 ngoai doc log.
# =============================================================================
set -uo pipefail
H=/home/ubuntu/ops/health_242.sh
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
TMP=$(mktemp /tmp/health_242_new_XXXX.sh)
[ -f "$H" ] || { echo "DUNG: khong co $H"; exit 1; }
grep -q 'PRICE_REALTIME_STALE' "$H" && { echo "DUNG: $H da co kiem tuoi gia (da cai?)"; exit 1; }
python3 - "$H" "$TMP" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
def sub(old, new):
    global s
    if s.count(old) != 1:
        sys.exit("FAIL anchor khop %d lan: %r" % (s.count(old), old[:70]))
    s = s.replace(old, new)
sub('DISK_WARN=${HEALTH242_DISK_WARN:-92}',
    'DISK_WARN=${HEALTH242_DISK_WARN:-92}\nPRICE_GAP_WARN=${HEALTH242_PRICE_GAP_WARN:-15000}   # [ingqf2] ms: tuoi/khoang ghi price_realtime collectData')
sub('echo "probe_ok=1"',
    '# [ingqf2] tuoi gia collectData tu dong [REST-BUDGET] moi nhat (chi co o jar QF2)\n'
    'bl=$(tail -c 3000000 $C 2>/dev/null | LC_ALL=C grep -aF \'[REST-BUDGET] calls=\' | tail -1)\n'
    'echo "budget_n=$([ -n "$bl" ] && echo 1 || echo 0)"\n'
    'echo "budget_age=$(age $C \'[REST-BUDGET] calls=\')"\n'
    'echo "price_gap=$(printf \'%s\' "$bl" | sed -nE \'s/.*price_gap_max_ms=(-?[0-9]+).*/\\1/p\')"\n'
    'echo "price_age=$(printf \'%s\' "$bl" | sed -nE \'s/.*price_age_ms=(-?[0-9]+).*/\\1/p\')"\n'
    'echo "probe_ok=1"')
sub('  [ "$(g disk_pct)" -lt "$DISK_WARN" ] 2>/dev/null || P+=("DISK_$(g disk_pct)pct")',
    '  [ "$(g disk_pct)" -lt "$DISK_WARN" ] 2>/dev/null || P+=("DISK_$(g disk_pct)pct")\n'
    '  if [ "$(g budget_n)" = 1 ]; then   # [ingqf2]\n'
    '    stale budget_age && P+=("INGEST_BUDGET_LOG_STALE(age=$(g budget_age)s)")\n'
    '    { [ "$(g price_gap)" -le "$PRICE_GAP_WARN" ] 2>/dev/null && [ "$(g price_age)" -le "$PRICE_GAP_WARN" ] 2>/dev/null; } \\\n'
    '      || P+=("PRICE_REALTIME_STALE(gap=$(g price_gap)ms age=$(g price_age)ms)")\n'
    '  fi')
open(dst, "w", encoding="utf-8").write(s)
print("PATCH_OK")
PY
[ $? = 0 ] || { echo "DUNG: va loi (khong doi gi)"; rm -f "$TMP"; exit 1; }
bash -n "$TMP" || { echo "DUNG: ban va loi cu phap"; rm -f "$TMP"; exit 1; }
echo "=== diff ==="; diff "$H" "$TMP"
echo "=== chay thu ban moi --dry-run (chi doc 242) ==="
OUT=$(HEALTH242_DIR=$(mktemp -d) bash "$TMP" --dry-run 2>&1); echo "$OUT" | tail -15
echo "$OUT" | grep -q 'budget_n=' || echo "$OUT" | grep -q 'summary\|trading_n' || { echo "DUNG: dry-run khong ra probe"; rm -f "$TMP"; exit 1; }
if [ "${DRY:-0}" = 1 ]; then echo "DRY=1: khong cai."; rm -f "$TMP"; exit 0; fi
echo ">>> Cai ban moi vao $H (backup $H.bak_ingqf2_$TS)? Go YES:"
read -r ANS; [ "$ANS" = YES ] || { echo "Huy."; rm -f "$TMP"; exit 1; }
cp -p "$H" "$H.bak_ingqf2_$TS" && cat "$TMP" > "$H" && rm -f "$TMP" || { echo "LOI cai — khoi phuc"; cp -p "$H.bak_ingqf2_$TS" "$H"; exit 2; }
bash -n "$H" || { echo "LOI cu phap sau cai — khoi phuc"; cp -p "$H.bak_ingqf2_$TS" "$H"; exit 2; }
echo "XONG. Go bo: cp -p $H.bak_ingqf2_$TS $H"
