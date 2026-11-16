#!/usr/bin/env bash
# =============================================================================
# golive_legacy_verify.sh — [V12 R4o] CHI DOC: sau khi owner tu dong TOAN BO vi the LEGACY (+ huy lenh/algo LEGACY) tren UI
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit; MASTER cap duong dan)
# (GOLIVE_SCENARIO ADD1 §5). Chay tren ORACLE:  bash $OPS/golive_legacy_verify.sh
#   (DRY=1: kiem nhu that nhung KHONG ghi file ket qua)
# DAT <=> tren san (key c3, goi ky tu 242): [R4q MAJ-2] so QTY tung symbol: |vi the san| - qty MO c3 (cum mo cua so) = 0 moi symbol
#   (phan vuot = LEGACY con sot, KE CA tren symbol c3 dang giu / MERGED; vi the am = LEGACY), qty c3 khong vuot san, 0 leg c3 chua xac
#   dinh; lenh thuong cid khong 'c3' = 0, algo cid khong 'c3' = 0 VA log v_t_m '[LEGACY] managed 0' moi (<= 600 s).
# DAT => ghi ~/claude_master/deploy/gates/LEGACY_CUT_VERIFIED.ok (golive_pilot_on.sh doi file nay <= 24 h).
# =============================================================================
set -uo pipefail
# [WAVE1c m1 / OPS-MICRO3 n4] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_manifest_check "$0" || exit 1   # [WAVE1b M5 / OPS-MICRO3 n4] script + lib + manifest khop md5 da commit, lech => TU CHOI truoc moi viec
gl_init golive_legacy_verify
[ "$C3_ACCOUNT" = MAIN ] || die "ADD4 §3: c3 chay tai khoan CON — BO golive_legacy_verify (LEGACY doc lap o tk chinh). Chi dung voi C3_ACCOUNT=MAIN."
gl_read_state
[ "$(sv KEYS_OK)" = 1 ] || die "file key $KEYS_FILE khong hop le"
API=$(gl_api242 scope) || die "ssh toi 242 loi"
echo "$API" | grep -v '^END_API$' | sed 's/^/   san: /'
echo "$API" | grep -qx END_API || die "goi API khong tron ven"
echo "$API" | grep -q '^ERR=' && die "$(echo "$API" | grep '^ERR=')"
V=DAT; WHY=""
[ "$(av API_OK)" = 1 ] || { V=TRUOT; WHY="$WHY doc_san_loi"; }
for k in POS_NONC3 POS_C3_MISMATCH C3_UNRESOLVED ORD_NONC3 ALGO_NONC3; do n=$(av $k | awk '{print $1}'); [ "$n" = 0 ] || { V=TRUOT; WHY="$WHY $k=$(av $k)"; }; done
[ "$(sv LEGACY_N)" = 0 ] || { V=TRUOT; WHY="$WHY log_LEGACY_managed=$(sv LEGACY_N)"; }
A0=$(sv LEGACY_AGE); { [ "$A0" -ge 0 ] && [ "$A0" -le 600 ]; } 2>/dev/null || { V=TRUOT; WHY="$WHY log_LEGACY_cu=${A0}s"; }
R="golive_legacy_verify $TS KET QUA: $V${WHY:+ (}${WHY# }${WHY:+)} | POS_TOTAL=$(av POS_TOTAL) c3_book=$(av C3_BOOK_SYMBOLS) ORD_C3=$(av ORD_C3) ALGO_C3=$(av ALGO_C3) LEGACY_managed=$(sv LEGACY_N) key_sha8=$(av KEY_SHA8)"
say "$R"
if [ "$V" = DAT ] && [ "$DRY" != 1 ]; then
  mkdir -p "$GATE_DIR"; echo "$R" > "$GATE_DIR/LEGACY_CUT_VERIFIED.ok.tmp" && mv -f "$GATE_DIR/LEGACY_CUT_VERIFIED.ok.tmp" "$GATE_DIR/LEGACY_CUT_VERIFIED.ok"
  say "Ghi $GATE_DIR/LEGACY_CUT_VERIFIED.ok"
fi
[ "$V" = DAT ] && exit 0 || { say "TRUOT: owner dong not vi the/lenh LEGACY tren UI roi chay lai."; exit 3; }
