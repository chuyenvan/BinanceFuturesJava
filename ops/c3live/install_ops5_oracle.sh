#!/usr/bin/env bash
# =============================================================================
# install_ops5_oracle.sh - [OPS5] OWNER chay tren ORACLE: them 2 cron (KHONG cham 242, KHONG restart):
#   (1) golive_deadman.sh  */2  - ban GHIM $DM_PIN_ROOT/golive_deadman_<md5_12>/ (chi doc), flock -n + timeout 90     (muc 2a)
#   (2) golive_first_trade_check.sh */5 FT_CRON=1 - chay tu repo nay (pin m1 + manifest moi luot), flock -n + timeout 110 (muc 1)
#   DRY=1 bash $OPS/install_ops5_oracle.sh        # chi in dong cron se them / bo, KHONG ghi
#   bash $OPS/install_ops5_oracle.sh              # go YES; crontab cu => $LOGDIR/crontab.bak_ops5_<TS>
#   MODE=rollback bash $OPS/install_ops5_oracle.sh  # go 2 dong cron OPS5 (ban ghim giu lai de doi chieu)
# Idempotent: dong cron co the "# golive_deadman (OPS5 2a)" / "# golive_first_trade (OPS5 1)" duoc thay, khong nhan doi.
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
if [ -z "${_IO_MASKED:-}" ]; then export _IO_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
MODE=${MODE:-install}
DM_PIN_ROOT=${DM_PIN_ROOT:-$LOGDIR/pinned}
LOCKS=${OPS5_LOCKS:-/home/ubuntu/claude_master/locks}
CT=${ORA_CRONTAB_CMD:-crontab}
TAG_DM='# golive_deadman (OPS5 2a)'; TAG_FT='# golive_first_trade (OPS5 1)'
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
M12=$(md5sum < "$_OPS/golive_deadman.sh" | cut -c1-12); PIN=$DM_PIN_ROOT/golive_deadman_$M12
L_DM="*/2 * * * * flock -n $LOCKS/golive_deadman.lock timeout -k 5 90 bash $PIN/golive_deadman.sh >/dev/null 2>&1 $TAG_DM"
L_FT="*/5 * * * * FT_CRON=1 flock -n $LOCKS/golive_first_trade.lock timeout -k 5 110 bash $_OPS/golive_first_trade_check.sh >/dev/null 2>&1 $TAG_FT"
say "=== install_ops5_oracle MODE=$MODE DRY=$DRY repo=$_OPS HEAD=${_HC:0:12} deadman_md5_12=$M12"
CUR=$($CT -l 2>/dev/null) || CUR=""
KEEP=$(printf '%s\n' "$CUR" | grep -vF "$TAG_DM" | grep -vF "$TAG_FT" | sed '/^$/d')
case "$MODE" in
  install) NEW=$(printf '%s\n%s\n%s\n' "$KEEP" "$L_DM" "$L_FT" | sed '/^$/d');;
  rollback) NEW=$KEEP;;
  *) say "MODE phai la install | rollback"; exit 1;;
esac
say "cron OPS5 hien co:"; printf '%s\n' "$CUR" | grep -F -e "$TAG_DM" -e "$TAG_FT" | sed 's/^/   CU : /'
[ "$MODE" = install ] && { say "cron OPS5 se dat:"; printf '   MOI: %s\n   MOI: %s\n' "$L_DM" "$L_FT"; }
if [ "$(printf '%s\n' "$CUR" | sed '/^$/d')" = "$NEW" ] && { [ "$MODE" = rollback ] || [ -f "$PIN/golive_deadman.sh" ]; }; then say "KHONG DOI (da dung)"; exit 0; fi
[ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi gi. (DRY PASS)"; exit 0; }
gl_yes "OPS5 $MODE: sua crontab Oracle (user $(id -un)) nhu tren."
mkdir -p "$LOGDIR" "$LOCKS"; printf '%s\n' "$CUR" > "$LOGDIR/crontab.bak_ops5_$TS"
if [ "$MODE" = install ]; then
  if [ ! -f "$PIN/golive_deadman.sh" ]; then
    mkdir -p "$PIN" && cp -p "$_OPS/golive_deadman.sh" "$PIN/golive_deadman.sh.tmp" && mv -f "$PIN/golive_deadman.sh.tmp" "$PIN/golive_deadman.sh" && chmod a-w "$PIN/golive_deadman.sh" "$PIN" \
      || { say "LOI ghim deadman $PIN"; exit 1; }
  fi
  [ "$(md5sum < "$PIN/golive_deadman.sh" | cut -c1-12)" = "$M12" ] || { say "LOI: ban ghim $PIN khac md5 repo - KHONG doi cron"; exit 1; }
fi
printf '%s\n' "$NEW" | $CT - || { say "LOI ghi crontab - khoi phuc"; printf '%s\n' "$CUR" | $CT -; exit 1; }
CHK=$($CT -l 2>/dev/null)
if [ "$MODE" = install ]; then
  printf '%s\n' "$CHK" | grep -qxF "$L_DM" && printf '%s\n' "$CHK" | grep -qxF "$L_FT" || { say "LOI: crontab sau ghi KHONG co 2 dong OPS5"; exit 1; }
  say "XONG: 2 cron OPS5 da dat. Rollback: MODE=rollback bash $_OPS/install_ops5_oracle.sh (backup $LOGDIR/crontab.bak_ops5_$TS)"
else
  printf '%s\n' "$CHK" | grep -qF -e "$TAG_DM" -e "$TAG_FT" && { say "LOI: con dong OPS5"; exit 1; }
  say "XONG rollback: da go 2 cron OPS5 (backup $LOGDIR/crontab.bak_ops5_$TS)"
fi
exit 0
