#!/usr/bin/env bash
# =============================================================================
# golive_check_key.sh — [V12 R4o / ADD4] KIEM key c3 tren 242, CHI DOC san. Chay tren ORACLE (owner):
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/golive_check_key.sh   # chi kiem file key + python tren 242, KHONG goi san
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_check_key.sh         # goi san CHI DOC (ky tu 242)
# C3_ACCOUNT=SUB (mac dinh, ADD4 §2: tk con, /root/.config/c3live/keys_sub.env) | MAIN (ADD1 §3: tk chinh keys.env — chi khi chi dinh ro).
# MAIN: DAT <=> apiRestrictions HTTP 200 VA enableWithdrawals=false VA ipRestrict=true VA enableFutures=true.
# SUB (ADD4 §2) DAT <=> nhu MAIN VA sha256(key)[:8] != key tk chinh ($MAIN_KEY_SHA8) VA 0 vi the VA 0 lenh mo VA 0 algo VA
#   dualSidePosition=false VA (BFUSD co so du => marginAvailable=true). Ghi lai multiAssetsMargin, totalMarginBalance, so du,
#   tai san margin, weight (W_NOMINAL fapi danh nghia ~150-155, W_USED_1M header cuoi; weight IP dung chung LEGACY).
#   Endpoint CHI DOC: sapi apiRestrictions; fapi v3/account (+v2/account neu v3 thieu marginAvailable), multiAssetsMargin,
#   positionSide/dual, v3/positionRisk, openOrders, openAlgoOrders.
# KHONG in key/secret (chi sha256(key)[:8]). Ket qua: ~/claude_master/deploy/gates/KEY_CHECK[_SUB]_<TS>.txt (MASTER dan vao gate G-MICRO).
# Ma thoat: 0 DAT | 3 TRUOT | 1 DUNG (loi truoc khi danh gia).
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_init golive_check_key
say "tai khoan c3: C3_ACCOUNT=$C3_ACCOUNT, file key $KEYS_FILE"
gl_read_state
[ "$(sv KEYS_OK)" = 1 ] && say "OK file key $KEYS_FILE (600, 2 dong C3_LIVE_API_KEY/SECRET)" || die "file key $KEYS_FILE thieu / quyen khac 600 / sai dinh dang"
if [ "$DRY" = 1 ]; then
  s242 "[ -x $PY242 ]" && say "OK python rieng $PY242" || die "thieu python rieng $PY242 tren 242"
  say "DRY=1: KHONG goi san. (DRY PASS)"; exit 0
fi
if [ "$C3_ACCOUNT" = SUB ]; then
  API=$(gl_api242 sub) || die "ssh toi 242 loi"
  echo "$API" | grep -vE '^END_API$' | sed 's/^/   san: /'
  gl_sub_eval 1
  V=$SUBV; WHY=$SUBWHY
  mkdir -p "$GATE_DIR"
  R=$GATE_DIR/KEY_CHECK_SUB_$TS.txt
  { echo "golive_check_key SUB $TS key_sha8=$(av KEY_SHA8) KET QUA: $V${WHY:+ (}${WHY# }${WHY:+)}"
    echo "$API" | grep -E '^(HTTP|API_ERR|ipRestrict|enable|permits|ACC_|TMB|AVAIL|BAL|MARGIN_ASSETS|BFUSD_|MULTI|DUAL|POS_TOTAL|POS_NONC3|ORD_TOTAL|ORD_NONC3|ALGO_TOTAL|ALGO_NONC3|W_|API_OK|ERR)'; } > "$R"
  say "ghi lai: key_sha8=$(av KEY_SHA8) multiAssetsMargin=$(av MULTI) dualSidePosition=$(av DUAL) totalMarginBalance=$(av TMB) availableBalance=$(av AVAIL)"
  say "ghi lai: so_du=[$(av BAL)] tai_san_margin=[$(av MARGIN_ASSETS)] BFUSD=$(av BFUSD_WALLET) marginAvailable=$(av BFUSD_MARGIN)"
  say "ghi lai: weight fapi danh nghia=$(av W_NOMINAL) X-MBX-USED-WEIGHT-1M cuoi=$(av W_USED_1M)"
  say "KET QUA: $V${WHY:+ —$WHY}. File: $R"
  [ "$V" = DAT ] && exit 0 || exit 3
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
