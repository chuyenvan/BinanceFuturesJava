#!/usr/bin/env bash
# =============================================================================
# golive_legacy_verify.sh — [V12 R4o] CHI DOC: sau khi owner tu dong 44 vi the LEGACY (+ huy lenh/algo LEGACY) tren UI
# (GOLIVE_SCENARIO ADD1 §5). Chay tren ORACLE:  bash ~/claude_master/v12/c3live/ops/c3live/golive_legacy_verify.sh
#   (DRY=1: kiem nhu that nhung KHONG ghi file ket qua)
# DAT <=> tren san (key c3, goi ky tu 242): vi the NGOAI so c3 = 0, lenh thuong cid khong 'c3' = 0, algo cid khong 'c3' = 0
#   VA log v_t_m '[LEGACY] managed 0' moi (<= 600 s).
# DAT => ghi ~/claude_master/deploy/gates/LEGACY_CUT_VERIFIED.ok (golive_pilot_on.sh doi file nay <= 24 h).
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_init golive_legacy_verify
gl_read_state
[ "$(sv KEYS_OK)" = 1 ] || die "file key $KEYS_FILE khong hop le"
API=$(gl_api242 scope) || die "ssh toi 242 loi"
echo "$API" | grep -v '^END_API$' | sed 's/^/   san: /'
echo "$API" | grep -qx END_API || die "goi API khong tron ven"
echo "$API" | grep -q '^ERR=' && die "$(echo "$API" | grep '^ERR=')"
V=DAT; WHY=""
[ "$(av API_OK)" = 1 ] || { V=TRUOT; WHY="$WHY doc_san_loi"; }
for k in POS_NONC3 ORD_NONC3 ALGO_NONC3; do n=$(av $k | awk '{print $1}'); [ "$n" = 0 ] || { V=TRUOT; WHY="$WHY $k=$(av $k)"; }; done
[ "$(sv LEGACY_N)" = 0 ] || { V=TRUOT; WHY="$WHY log_LEGACY_managed=$(sv LEGACY_N)"; }
A0=$(sv LEGACY_AGE); { [ "$A0" -ge 0 ] && [ "$A0" -le 600 ]; } 2>/dev/null || { V=TRUOT; WHY="$WHY log_LEGACY_cu=${A0}s"; }
R="golive_legacy_verify $TS KET QUA: $V${WHY:+ (}${WHY# }${WHY:+)} | POS_TOTAL=$(av POS_TOTAL) c3_book=$(av C3_BOOK_SYMBOLS) ORD_C3=$(av ORD_C3) ALGO_C3=$(av ALGO_C3) LEGACY_managed=$(sv LEGACY_N) key_sha8=$(av KEY_SHA8)"
say "$R"
if [ "$V" = DAT ] && [ "$DRY" != 1 ]; then
  mkdir -p "$GATE_DIR"; echo "$R" > "$GATE_DIR/LEGACY_CUT_VERIFIED.ok.tmp" && mv -f "$GATE_DIR/LEGACY_CUT_VERIFIED.ok.tmp" "$GATE_DIR/LEGACY_CUT_VERIFIED.ok"
  say "Ghi $GATE_DIR/LEGACY_CUT_VERIFIED.ok"
fi
[ "$V" = DAT ] && exit 0 || { say "TRUOT: owner dong not vi the/lenh LEGACY tren UI roi chay lai."; exit 3; }
