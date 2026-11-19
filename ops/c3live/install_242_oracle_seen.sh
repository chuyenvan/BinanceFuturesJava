#!/usr/bin/env bash
# =============================================================================
# install_242_oracle_seen.sh - [OPS5 muc 2b] OWNER chay tren ORACLE: cai c3_oracle_seen_242.sh len 242 (/usr/local/sbin/c3_oracle_seen.sh)
#   + 1 dong cron root */5 "# C3_ORACLE_SEEN (OPS5 2b)". KHONG cham bot, KHONG restart.
#   DRY=1 bash $OPS/install_242_oracle_seen.sh | bash $OPS/install_242_oracle_seen.sh (go YES) | MODE=rollback bash ... (go cron, script -> .off_)
# Bien (test): SSH_242 AD_SBIN AD_CT242
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
if [ -z "${_OS_MASKED:-}" ]; then export _OS_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
MODE=${MODE:-install}; case "$MODE" in install|rollback) ;; *) echo "MODE phai la install | rollback"; exit 1;; esac
AD_SBIN=${AD_SBIN:-/usr/local/sbin}; AD_CT242=${AD_CT242:-crontab}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
W5=$(md5sum < "$_OPS/c3_oracle_seen_242.sh" | cut -c1-32); B64=$(base64 -w0 < "$_OPS/c3_oracle_seen_242.sh")
say "=== install_242_oracle_seen MODE=$MODE DRY=$DRY HEAD=${_HC:0:12} script_md5=$W5"
RSCRIPT=$(cat <<'EOR'
STEP=$1; MODE=$2; TS=$3; SB=$4; CT=$5; W5=$6; B64=$7
SC=$SB/c3_oracle_seen.sh; TAG='# C3_ORACLE_SEEN (OPS5 2b)'; LINE="*/5 * * * * $SC >/dev/null 2>&1 $TAG"
CUR=$($CT -l 2>/dev/null)
echo "CRON_N=$(printf '%s\n' "$CUR" | grep -cF "$TAG")"; echo "CRON_OK=$(printf '%s\n' "$CUR" | grep -cxF "$LINE")"
echo "SCRIPT_MD5=$([ -f "$SC" ] && md5sum < "$SC" | cut -c1-32)"
if [ "$STEP" = apply ]; then
  printf '%s\n' "$CUR" > /root/crontab.bak_oracle_seen_$TS 2>/dev/null || printf '%s\n' "$CUR" > "$SB/../crontab.bak_oracle_seen_$TS"
  KEEP=$(printf '%s\n' "$CUR" | grep -vF "$TAG" | sed '/^$/d')
  if [ "$MODE" = install ]; then
    printf '%s' "$B64" | base64 -d > "$SC.new_$TS" && [ "$(md5sum < "$SC.new_$TS" | cut -c1-32)" = "$W5" ] && chmod 755 "$SC.new_$TS" && mv -f "$SC.new_$TS" "$SC" || { echo "ERR=ghi_script"; echo END_OS; exit 0; }
    printf '%s\n%s\n' "$KEEP" "$LINE" | sed '/^$/d' | $CT - || { echo "ERR=ghi_crontab"; echo END_OS; exit 0; }
  else
    printf '%s\n' "$KEEP" | $CT - || { echo "ERR=ghi_crontab"; echo END_OS; exit 0; }
    [ -f "$SC" ] && mv -f "$SC" "$SC.off_$TS"
  fi
  CUR=$($CT -l 2>/dev/null)
  echo "POST_CRON_N=$(printf '%s\n' "$CUR" | grep -cF "$TAG")"; echo "POST_CRON_OK=$(printf '%s\n' "$CUR" | grep -cxF "$LINE")"
  echo "POST_SCRIPT_MD5=$([ -f "$SC" ] && md5sum < "$SC" | cut -c1-32)"
fi
echo END_OS
EOR
)
RARGS="$MODE $TS $AD_SBIN '$AD_CT242' $W5 $B64"
P=$(printf '%s\n' "$RSCRIPT" | s242in "bash -s -- plan $RARGS") || P="ERR=ssh"
echo "$P" | grep -v '^END_OS$' | sed 's/^/   242: /'
pv() { echo "$P" | sed -n "s/^$1=//p" | head -1; }
echo "$P" | grep -qx END_OS && ! echo "$P" | grep -q '^ERR=' || die "doc 242 loi"
if [ "$MODE" = install ]; then
  [ "$(pv CRON_N)" = 1 ] && [ "$(pv CRON_OK)" = 1 ] && [ "$(pv SCRIPT_MD5)" = "$W5" ] && { say "KHONG DOI (da cai)"; exit 0; }
else
  [ "$(pv CRON_N)" = 0 ] && { say "KHONG DOI (chua cai)"; exit 0; }
fi
[ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi gi. (DRY PASS)"; exit 0; }
gl_yes "ORACLE_SEEN $MODE tren 242 (cron root + $AD_SBIN/c3_oracle_seen.sh)."
R=$(printf '%s\n' "$RSCRIPT" | s242in_once "bash -s -- apply $RARGS") || R="ERR=ssh_apply"
echo "$R" | grep -v '^END_OS$' | sed 's/^/   242: /'
rv() { echo "$R" | sed -n "s/^$1=//p" | head -1; }
echo "$R" | grep -qx END_OS && ! echo "$R" | grep -q '^ERR=' || { say "KHAN: apply loi/khong ro - DRY=1 bash $0 de doc lai"; exit 1; }
if [ "$MODE" = install ]; then
  [ "$(rv POST_CRON_N)" = 1 ] && [ "$(rv POST_CRON_OK)" = 1 ] && [ "$(rv POST_SCRIPT_MD5)" = "$W5" ] || { say "KHAN: hau kiem SAI - MODE=rollback"; exit 1; }
  say "XONG: 242 se bao Telegram khi Oracle khong cham > 15'. Rollback: MODE=rollback bash $0"
else
  [ "$(rv POST_CRON_N)" = 0 ] || { say "KHAN: con dong cron"; exit 1; }
  say "XONG rollback oracle_seen."
fi
exit 0
