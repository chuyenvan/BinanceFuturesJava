#!/usr/bin/env bash
# =============================================================================
# golive_check_key.sh — [V12 R4o] KIEM QUYEN key c3 TAI KHOAN CHINH (/root/.config/c3live/keys.env tren 242), CHI DOC.
# GOLIVE_SCENARIO ADD1 §3 muc 3. Chay tren ORACLE (owner):
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/golive_check_key.sh   # chi kiem file key + python tren 242, KHONG goi san
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_check_key.sh         # goi GET /sapi/v1/account/apiRestrictions (ky tu 242)
# DAT <=> HTTP 200 (loi goi ky tu IP 242 duoc chap nhan) VA enableWithdrawals=false VA ipRestrict=true VA enableFutures=true.
# KHONG in key/secret (chi sha256(key)[:8]). Ket qua: ~/claude_master/deploy/gates/KEY_CHECK_<TS>.txt (MASTER dan vao gate G-MICRO).
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_init golive_check_key
gl_read_state
[ "$(sv KEYS_OK)" = 1 ] && say "OK file key $KEYS_FILE (600, 2 dong C3_LIVE_API_KEY/SECRET)" || die "file key $KEYS_FILE thieu / quyen khac 600 / sai dinh dang"
if [ "$DRY" = 1 ]; then
  s242 "[ -x $PY242 ]" && say "OK python rieng $PY242" || die "thieu python rieng $PY242 tren 242"
  say "DRY=1: KHONG goi san. (DRY PASS)"; exit 0
fi
API=$(gl_api242 restrictions) || die "ssh toi 242 loi"
echo "$API" | grep -vE '^END_API$'
echo "$API" | grep -qx END_API || die "goi API khong tron ven (ssh dut?)"
echo "$API" | grep -q '^ERR=' && die "$(echo "$API" | grep '^ERR=')"
V=DAT; WHY=""
[ "$(av HTTP)" = 200 ] || { V=TRUOT; WHY="$WHY HTTP=$(av HTTP) $(av API_ERR)"; }
[ "$(av enableWithdrawals)" = false ] || { V=TRUOT; WHY="$WHY enableWithdrawals=$(av enableWithdrawals)"; }
[ "$(av ipRestrict)" = true ] || { V=TRUOT; WHY="$WHY ipRestrict=$(av ipRestrict)"; }
[ "$(av enableFutures)" = true ] || { V=TRUOT; WHY="$WHY enableFutures=$(av enableFutures)"; }
mkdir -p "$GATE_DIR"
R=$GATE_DIR/KEY_CHECK_$TS.txt
{ echo "golive_check_key $TS key_sha8=$(av KEY_SHA8) KET QUA: $V${WHY:+ (}${WHY# }${WHY:+)}"
  echo "$API" | grep -E '^(HTTP|ipRestrict|enable|permits)'; } > "$R"
say "KET QUA: $V${WHY:+ —$WHY}. File: $R"
[ "$V" = DAT ] && exit 0 || exit 3
