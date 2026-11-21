#!/usr/bin/env bash
# =============================================================================
# golive_check_lev.sh - [OPS5 muc 3] BAO leverage + marginType TUNG symbol cua tai khoan c3 (mac dinh SUB), CHI DOC san. Chay tren ORACLE.
#   DRY=1 bash $OPS/golive_check_lev.sh   # chi doc trang thai 242 (C3_CAPITAL process), KHONG goi san
#   bash $OPS/golive_check_lev.sh         # gl_api242 lev: GET /fapi/v3/account (5) + GET /fapi/v1/symbolConfig (5) = 10 weight IP, ky tu 242
# Universe = run/c3live_exchangeInfo.json tren 242 (TRADING, USDT, PERPETUAL). Canh bao (exit 3) khi co symbol:
#   leverage != LEV_EXPECT (mac dinh 1) - [OPS5_FIX M-2] jar AccountModeGuard chi cho symbol isCrossed() && leverage == expectedLeverage
#     (AccountModeGuard.java:105; C3LiveRuntime dung ctor 2 tham so => expectedLeverage=1, dong 134). lev 20x = jar CHAN symbol do => CANH BAO.
#   maxNotionalValue < LEV_CLUSTER_MAX = 4 x 0,0225 x C3_CAPITAL (cum: leg mo + 3 leg DCA o U=0) - san tu choi leg DCA cuoi
#   marginType != LEV_MARGIN_EXPECT (mac dinh CROSSED = jar bat buoc isCrossed())
# In W_USED_1M. Ket qua: $LOGDIR/lev_check/LEV_CHECK_<acc>_<TS>.txt. KHONG in key/secret. Ma thoat 0 DAT | 3 CANH BAO | 1 DUNG.
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
if [ -z "${_LV_MASKED:-}" ]; then export _LV_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
gl_init golive_check_lev
LEV_EXPECT=${LEV_EXPECT:-1}; LEV_MARGIN_EXPECT=${LEV_MARGIN_EXPECT:-CROSSED}; LEV_SHOW=${LEV_SHOW:-30}
gl_read_state
CAP=$(sv ENV_C3_CAPITAL); [ -n "$CAP" ] || CAP=$(sv ENVSH_C3_CAPITAL)
[[ "$CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "C3_CAPITAL khong doc duoc (process='$(sv ENV_C3_CAPITAL)' env.sh='$(sv ENVSH_C3_CAPITAL)')"
# [OPS6 T10] LEV_CAP=<von> (vd 10000 truoc pilot): kiem LEV_CLUSTER_MAX cho von SE dung thay von process hien tai (chi doi nguong, CHI DOC)
if [ -n "${LEV_CAP:-}" ]; then
  [[ "$LEV_CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v c="$LEV_CAP" 'BEGIN{exit !(c>0)}' || die "LEV_CAP='$LEV_CAP' khong hop le"
  say "INFO LEV_CAP=$LEV_CAP ghi de von process $CAP cho nguong maxNotional (kiem truoc pilot)"; CAP=$LEV_CAP
fi
say "tai khoan c3: C3_ACCOUNT=$C3_ACCOUNT C3_CAPITAL=$CAP adapter=$(sv ENV_LIVE_ADAPTER)"
[ "$DRY" = 1 ] && { say "DRY=1: KHONG goi san. (DRY PASS)"; exit 0; }
API=$(gl_api242 lev) || die "ssh toi 242 loi"
echo "$API" | grep -qx END_API || die "goi API khong tron ven (ssh dut?)"
echo "$API" | grep -q '^ERR=' && die "$(echo "$API" | grep '^ERR=' | head -1)"
TMB=$(av TMB)
say "san: key_sha8=$(av KEY_SHA8) totalMarginBalance=$TMB LEV_HTTP=$(av LEV_HTTP) universe=$(av LEV_UNI) thieu_cfg=$(av LEV_MISS) $(av LEV_UNI_ERR)"
say "weight: danh nghia=$(av W_NOMINAL) X-MBX-USED-WEIGHT-1M cuoi=$(av W_USED_1M)"
[ "$(av API_OK)" = 1 ] || die "doc san loi ($(echo "$API" | grep '^ERR' | tr '\n' ' '))"
[ -n "$C3_ACCOUNT" ] && [ "$C3_ACCOUNT" = SUB ] && [ "$(av KEY_SHA8)" != "$SUB_KEY_SHA8" ] && die "key doc san $(av KEY_SHA8) != key tk con da dang ky $SUB_KEY_SHA8"
[[ "$TMB" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v t="$TMB" 'BEGIN{exit !(t>0)}' || die "totalMarginBalance khong hop le ('$TMB')"
EV=$(echo "$API" | sed -n 's/^LEVSYM=//p' | awk -F: -v cap="$CAP" -v need="$LEV_EXPECT" -v mt="$LEV_MARGIN_EXPECT" -v show="$LEV_SHOW" '
  BEGIN { need=need+0; cm=4*0.0225*cap; mt=toupper(mt) }
  { n++; L[$2]++; M[toupper($3)]++; w=""
    if ($2+0 != need) { w=w " lev=" $2 "!=" need; nl++ }
    if (toupper($3) != mt) { w=w " margin=" $3; nm++ }
    if ($4 != "" && $4 != "None" && $4 !~ /^INF/ && $4+0 < cm) { w=w " maxNotional=" $4 "<" cm; nn++ }
    if (w != "") { nb++; if (nb <= show) bad = bad " " $1 ":" substr(w,2) } }
  END { printf "LEV_NEED=%d\nCLUSTER_MAX=%.2f\nN=%d\nN_BAD=%d\nN_LEV=%d\nN_MARGIN=%d\nN_NOTIONAL=%d\n", need, cm, n, nb, nl, nm, nn
        s=""; for (k in L) s=s sprintf("%sx:%d ", k, L[k]); print "DIST_LEV=" s
        s=""; for (k in M) s=s sprintf("%s:%d ", k, M[k]); print "DIST_MARGIN=" s
        print "BAD=" bad }')
ev() { echo "$EV" | sed -n "s/^$1=//p" | head -1; }
say "nguong: leverage == $(ev LEV_NEED) (jar AccountModeGuard expectedLeverage), maxNotionalValue >= $(ev CLUSTER_MAX) (4 leg x 2,25 % von), marginType = $LEV_MARGIN_EXPECT"
say "phan bo leverage: $(ev DIST_LEV)"
say "phan bo marginType: $(ev DIST_MARGIN)"
V=DAT; [ "$(ev N_BAD)" = 0 ] || V=CANH_BAO
[ "$(ev N)" -gt 0 ] 2>/dev/null || { V=CANH_BAO; say "!! 0 symbol co cau hinh (symbolConfig rong?)"; }
say "symbol lech: $(ev N_BAD)/$(ev N) (leverage != $LEV_EXPECT: $(ev N_LEV), marginType khac $(ev N_MARGIN), maxNotional thap $(ev N_NOTIONAL)); toi da $LEV_SHOW dau:$(ev BAD)"
mkdir -p "$LOGDIR/lev_check"; R=$LOGDIR/lev_check/LEV_CHECK_${C3_ACCOUNT}_$TS.txt
{ echo "golive_check_lev $C3_ACCOUNT $TS key_sha8=$(av KEY_SHA8) KET QUA: $V"; echo "$EV"; echo "W_USED_1M=$(av W_USED_1M)"; echo "$API" | grep '^LEVSYM='; } > "$R"
say "KET QUA: $V. File: $R"
[ "$V" = DAT ] && exit 0 || exit 3
