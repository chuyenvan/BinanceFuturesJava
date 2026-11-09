#!/usr/bin/env bash
# =============================================================================
# golive_rebase_equity.sh — [ADD4 ERRATA 2 §5] OWNER chay tren ORACLE SAU KHI NAP / RUT von tk con co chu dich:
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_rebase_equity.sh "nap 500 USDT"     # go YES
#   DRY=1 bash .../golive_rebase_equity.sh "ly do"                                         # chi in
# Lop phu golive_monitor do eq = C3_CAPITAL + (tmb - tmb0). Nap/rut lam tmb doi KHONG do c3 => phai dat lai tmb0 = tmb hien tai
#   (doc san CHI DOC: v3/account + scope, 90 weight), C3_CAPITAL = env process bot. Dinh eq tu dat lai theo moc moi.
# Chi khi co co micro/pilot (~/claude_master/deploy/golive_monitor.on). Ghi ~/claude_master/deploy/c3sub_eq_base.txt (+ .bak_<TS>)
#   va log ly do ~/claude_master/deploy/c3sub_eq_base.log. KHONG ghi 242. Ma thoat 0 XONG | 1 DUNG.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
REASON=${1:-${REASON:-}}
gl_init golive_rebase_equity
[ -n "$REASON" ] || die "can ly do: bash $0 \"nap 500 USDT\""
[ "$C3_ACCOUNT" = SUB ] || die "chi dung cho C3_ACCOUNT=SUB (ADD4)"
[ -f "$GL_MON_FLAG" ] || die "khong co co micro/pilot ($GL_MON_FLAG) — khong can rebase (micro_on / pilot_on tu ghi tmb0)"
gl_read_state
CAP=$(sv ENV_C3_CAPITAL)
[[ "$CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "khong doc duoc C3_CAPITAL cua process bot ('$CAP')"
[ "$(sv ENV_LIVE_C3_KEYS_FILE)" = "$KEYS_FILE" ] || say "WARN bot dung LIVE_C3_KEYS_FILE='$(sv ENV_LIVE_C3_KEYS_FILE)' khac $KEYS_FILE"
API=$(gl_api242 mon) || die "ssh toi 242 loi"
echo "$API" | grep -qx END_API || die "doc san khong tron ven"
TMB=$(av TMB); KS8=$(av KEY_SHA8)
[[ "$TMB" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "totalMarginBalance khong hop le ('$TMB')"
[ -n "$KS8" ] && [ "$KS8" != "$MAIN_KEY_SHA8" ] || die "key doc san = key tk chinh / thieu ($KS8)"
OB=$(sed -n 's/^tmb0=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1); OC=$(sed -n 's/^c3_capital=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1)
if [[ "$OB" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ "$OC" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  say "moc cu: tmb0=$OB C3_CAPITAL=$OC => eq hien tai theo moc cu = $(awk -v c="$OC" -v t="$TMB" -v b="$OB" 'BEGIN{printf "%.2f", c+t-b}') (tmb=$TMB)"
else
  say "moc cu: KHONG co / khong hop le"
fi
say "--- se ghi moc moi: tmb0=$TMB C3_CAPITAL=$CAP key_sha8=$KS8 ly_do='$REASON' => eq = $CAP, dinh eq dat lai"
[ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi. (DRY PASS)"; exit 0; }
gl_yes "REBASE tmb0 ${OB:-?} -> $TMB (chi sau NAP/RUT co chu dich; dung de 'xoa lo' la SAI)."
gl_eq_base_set "$TMB" "$CAP" "$KS8" "golive_rebase_equity: $REASON" || die "ghi moc loi"
say "=== XONG: moc eq moi tmb0=$TMB C3_CAPITAL=$CAP"
tg "[golive] REBASE eq tk con TS=$TS: tmb0 ${OB:-?} -> $TMB (C3_CAPITAL=$CAP). Ly do: $REASON. Log $LOG"
exit 0
