#!/usr/bin/env bash
# =============================================================================
# install_242_autodrain.sh - [OPS5 muc 4] OWNER chay tren ORACLE: cai "sau crash khong tu len LIVE" (tang ops, KHONG doi jar, KHONG restart bot)
#   DRY=1 bash $OPS/install_242_autodrain.sh             # chi doc 242 + in ke hoach
#   bash $OPS/install_242_autodrain.sh                   # go YES: (1) /usr/local/sbin/h242-prestart-c3.sh = c3_autodrain_prestart.sh (md5 kiem)
#        (2) cron watchdog: them tien to WD_PRESTART=/usr/local/sbin/h242-prestart-c3.sh (crontab cu => /root/crontab.bak_autodrain_<TS>)
#        (3) systemd drop-in h242-trading.service.d/c3-autodrain.conf (ExecStartPre = wrapper) + daemon-reload (KHONG restart service)
#   MODE=rollback bash $OPS/install_242_autodrain.sh     # go (2)(3), wrapper -> .off_<TS>
# Dieu kien: h242_watchdog.sh co ho tro WD_PRESTART; dung 1 dong cron watchdog; prestart goc ton tai. Lech => TU CHOI, khong doi gi.
# Bien (test): SSH_242 AD_SBIN AD_WD AD_SYSTEMD_DIR AD_SYSTEMCTL AD_CT242
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
if [ -z "${_AD_MASKED:-}" ]; then export _AD_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
MODE=${MODE:-install}
case "$MODE" in install|rollback) ;; *) echo "MODE phai la install | rollback"; exit 1;; esac
AD_SBIN=${AD_SBIN:-/usr/local/sbin}; AD_WD=${AD_WD:-$AD_SBIN/h242_watchdog.sh}; AD_SYSTEMD_DIR=${AD_SYSTEMD_DIR:-/etc/systemd/system}
AD_SYSTEMCTL=${AD_SYSTEMCTL:-systemctl}; AD_CT242=${AD_CT242:-crontab}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
W5=$(md5sum < "$_OPS/c3_autodrain_prestart.sh" | cut -c1-32); B64=$(base64 -w0 < "$_OPS/c3_autodrain_prestart.sh")
say "=== install_242_autodrain MODE=$MODE DRY=$DRY HEAD=${_HC:0:12} wrapper_md5=$W5"
# script chay tren 242 (buoc plan = CHI DOC; apply = ghi, chay DUNG 1 LAN qua s242in_once)
RSCRIPT=$(cat <<'EOR'
STEP=$1; MODE=$2; TS=$3; SB=$4; WD=$5; SD=$6; SC=$7; CT=$8; W5=$9; APP=${10}; B64=${11}
WR=$SB/h242-prestart-c3.sh; OR=$SB/h242-prestart.sh; DI=$SD/h242-trading.service.d; DF=$DI/c3-autodrain.conf
MC=com.binance.chuyennd.trading.BinanceOrderTradingManager
RX='^\*/2 \* \* \* \* (WD_PRESTART=[^ ]+ )?'"$(printf '%s' "$WD" | sed 's/[.]/\\./g')"'( |$)'
CUR=$($CT -l 2>/dev/null); NL=$(printf '%s\n' "$CUR" | grep -cE "$RX")
echo "WD_SUPPORT=$(grep -c 'PRESTART=\${WD_PRESTART:-' "$WD" 2>/dev/null)"
echo "ORIG=$([ -x "$OR" ] && echo 1 || echo 0)"
echo "CRON_N=$NL"; echo "CRON_HOOK=$(printf '%s\n' "$CUR" | grep -E "$RX" | grep -c "WD_PRESTART=$WR ")"
echo "WRAPPER_MD5=$([ -f "$WR" ] && md5sum < "$WR" | cut -c1-32)"
echo "DROPIN=$([ -f "$DF" ] && echo 1 || echo 0)"
if [ "$STEP" = apply ]; then
  [ "$NL" = 1 ] || { echo "ERR=cron_watchdog_khong_dung_1_dong($NL)"; echo END_AD; exit 0; }
  printf '%s\n' "$CUR" > /root/crontab.bak_autodrain_$TS 2>/dev/null || printf '%s\n' "$CUR" > "$SB/../crontab.bak_autodrain_$TS"
  if [ "$MODE" = install ]; then
    printf '%s' "$B64" | base64 -d > "$WR.new_$TS" && [ "$(md5sum < "$WR.new_$TS" | cut -c1-32)" = "$W5" ] && chmod 755 "$WR.new_$TS" && mv -f "$WR.new_$TS" "$WR" || { echo "ERR=ghi_wrapper"; echo END_AD; exit 0; }
    NEW=$(printf '%s\n' "$CUR" | sed -E "s#^(\*/2 \* \* \* \* )(WD_PRESTART=[^ ]+ )?($(printf '%s' "$WD" | sed 's/[.]/\\./g'))( |\$)#\1WD_PRESTART=$WR \3\4#")
    printf '%s\n' "$NEW" | $CT - || { echo "ERR=ghi_crontab"; echo END_AD; exit 0; }
    mkdir -p "$DI" && printf '[Service]\nExecStartPre=\nExecStartPre=%s %s %s\n' "$WR" "$APP" "$MC" > "$DF.tmp" && mv -f "$DF.tmp" "$DF" || { echo "ERR=ghi_dropin"; echo END_AD; exit 0; }
    $SC daemon-reload || echo "WARN=daemon_reload_loi"
  else
    NEW=$(printf '%s\n' "$CUR" | sed -E "s#^(\*/2 \* \* \* \* )WD_PRESTART=[^ ]+ #\1#")
    printf '%s\n' "$NEW" | $CT - || { echo "ERR=ghi_crontab"; echo END_AD; exit 0; }
    rm -f "$DF"; rmdir "$DI" 2>/dev/null; $SC daemon-reload || echo "WARN=daemon_reload_loi"
    [ -f "$WR" ] && mv -f "$WR" "$WR.off_$TS"
  fi
  CUR=$($CT -l 2>/dev/null)
  echo "POST_CRON_HOOK=$(printf '%s\n' "$CUR" | grep -E "$RX" | grep -c "WD_PRESTART=$WR ")"
  echo "POST_CRON_N=$(printf '%s\n' "$CUR" | grep -cE "$RX")"
  echo "POST_WRAPPER_MD5=$([ -f "$WR" ] && md5sum < "$WR" | cut -c1-32)"
  echo "POST_DROPIN=$([ -f "$DF" ] && echo 1 || echo 0)"
fi
echo END_AD
EOR
)
RARGS="$MODE $TS $AD_SBIN $AD_WD $AD_SYSTEMD_DIR '$AD_SYSTEMCTL' '$AD_CT242' $W5 $A $B64"
P=$(printf '%s\n' "$RSCRIPT" | s242in "bash -s -- plan $RARGS") || P="ERR=ssh"
echo "$P" | grep -v '^END_AD$' | sed 's/^/   242: /'
pv() { echo "$P" | sed -n "s/^$1=//p" | head -1; }
echo "$P" | grep -qx END_AD && ! echo "$P" | grep -q '^ERR=' || die "doc 242 loi"
[ "$(pv WD_SUPPORT)" -ge 1 ] 2>/dev/null || die "watchdog $AD_WD KHONG ho tro WD_PRESTART - khong cai"
[ "$(pv ORIG)" = 1 ] || die "thieu prestart goc $AD_SBIN/h242-prestart.sh"
[ "$(pv CRON_N)" = 1 ] || die "cron watchdog tren 242 khong dung 1 dong (co $(pv CRON_N))"
if [ "$MODE" = install ]; then
  [ "$(pv CRON_HOOK)" = 1 ] && [ "$(pv WRAPPER_MD5)" = "$W5" ] && [ "$(pv DROPIN)" = 1 ] && { say "KHONG DOI (da cai dung ban $W5)"; exit 0; }
  say "ke hoach: ghi $AD_SBIN/h242-prestart-c3.sh (md5 $W5); cron watchdog them WD_PRESTART=$AD_SBIN/h242-prestart-c3.sh; drop-in $AD_SYSTEMD_DIR/h242-trading.service.d/c3-autodrain.conf + daemon-reload. KHONG restart bot."
else
  [ "$(pv CRON_HOOK)" = 0 ] && [ "$(pv DROPIN)" = 0 ] && { say "KHONG DOI (chua cai)"; exit 0; }
  say "ke hoach rollback: go WD_PRESTART khoi cron watchdog, xoa drop-in + daemon-reload, wrapper -> .off_$TS. KHONG restart bot."
fi
[ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi gi. (DRY PASS)"; exit 0; }
gl_yes "AUTODRAIN $MODE tren 242 (cron root + systemd drop-in)."
R=$(printf '%s\n' "$RSCRIPT" | s242in_once "bash -s -- apply $RARGS") || R="ERR=ssh_apply"
echo "$R" | grep -v '^END_AD$' | sed 's/^/   242: /'
rv() { echo "$R" | sed -n "s/^$1=//p" | head -1; }
echo "$R" | grep -qx END_AD && ! echo "$R" | grep -q '^ERR=' || { say "KHAN: apply loi/khong ro ($(echo "$R" | grep '^ERR' | head -1)) - doc lai: DRY=1 bash $0 ; rollback: MODE=rollback bash $0"; tg "[golive] KHAN install_242_autodrain $MODE TS=$TS loi/khong ro"; exit 1; }
if [ "$MODE" = install ]; then
  [ "$(rv POST_CRON_HOOK)" = 1 ] && [ "$(rv POST_CRON_N)" = 1 ] && [ "$(rv POST_WRAPPER_MD5)" = "$W5" ] && [ "$(rv POST_DROPIN)" = 1 ] || { say "KHAN: hau kiem cai SAI - chay MODE=rollback"; exit 1; }
  say "XONG: autodrain da cai. Watchdog/boot start bot live => run/KILL_SWITCH (drain) + Telegram. Rollback: MODE=rollback bash $0"
  tg "[golive] install_242_autodrain XONG TS=$TS (wrapper $W5)"
else
  [ "$(rv POST_CRON_HOOK)" = 0 ] && [ "$(rv POST_CRON_N)" = 1 ] && [ "$(rv POST_DROPIN)" = 0 ] || { say "KHAN: hau kiem rollback SAI"; exit 1; }
  say "XONG rollback autodrain."
fi
exit 0
