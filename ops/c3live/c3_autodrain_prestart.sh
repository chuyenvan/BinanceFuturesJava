#!/usr/bin/env bash
# =============================================================================
# c3_autodrain_prestart.sh - [OPS5 muc 4] (cai tren 242 thanh /usr/local/sbin/h242-prestart-c3.sh boi install_242_autodrain.sh)
#   Boc prestart goc (/usr/local/sbin/h242-prestart.sh <APP> <MainClass>): watchdog (WD_PRESTART) va systemd h242-trading (ExecStartPre)
#   goi TRUOC khi start bot. Script go-live (golive_*/deploy_*/rollback_*) start bang bin/daemon.sh truc tiep + PAUSE watchdog => KHONG qua day.
#   => moi lan start qua day = khoi dong lai NGOAI y muon (watchdog HB_STALE_KILL / TRADING_DOWN / boot may).
# Neu prestart goc rc=0 va conf/env.sh co LIVE_ADAPTER=live: tao run/KILL_SWITCH (set -C, KHONG ghi de file co san) TRUOC khi start =>
#   bot len o trang thai DRAIN (van quan ly vi the c3, KHONG mo lenh moi) + Telegram. Mo lai: MODE=undrain bash <OPS>/golive_live_off.sh.
# KHONG BAO GIO chan start (vi the can duoc quan ly): dat KILL_SWITCH loi => van exit 0 + Telegram KHAN. prestart goc rc!=0 => tra nguyen rc.
# Bien (test): AD_ORIG_PRESTART AD_STATE_DIR AD_TG_ENV AD_TG_SINK AD_TG_API
# =============================================================================
set -uo pipefail
ORIG=${AD_ORIG_PRESTART:-/usr/local/sbin/h242-prestart.sh}
STATE=${AD_STATE_DIR:-/var/lib/c3_autodrain}
TG_ENV=${AD_TG_ENV:-/root/.config/h242_watchdog/tg.env}
APP=${1:-/home/chuyennd/java/v_t_m}
mkdir -p "$STATE" 2>/dev/null
log() { echo "$(date '+%F %T%z') $*" >> "$STATE/autodrain.log" 2>/dev/null; echo "[c3_autodrain] $*"; }
tg() {
  local msg tok chat code
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/[CHE]/g' | head -c 3000)
  if [ -n "${AD_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$AD_TG_SINK"; return 0; fi
  [ -r "$TG_ENV" ] || { log "NO_CHANNEL khong doc duoc file Telegram"; echo "$(date '+%F %T%z') $msg" >> "$STATE/ALERT_PENDING.txt"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || { log "file Telegram thieu token/chat"; return 1; }
  code=$(printf 'url = "%s/bot%s/sendMessage"\n' "${AD_TG_API:-https://api.telegram.org}" "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null); tok=""; chat=""
  log "telegram http=$code"
}
"$ORIG" "$@"; rc=$?
[ "$rc" = 0 ] || { log "prestart goc rc=$rc (bot KHONG duoc start) - khong drain"; exit "$rc"; }
AD=$(sed -n 's/^[[:space:]]*export[[:space:]][[:space:]]*LIVE_ADAPTER=//p' "$APP/conf/env.sh" 2>/dev/null | tail -1 | tr -d "\"' \r")
[ "$AD" = live ] || { log "LIVE_ADAPTER=${AD:-?} (khong live) - khong drain"; exit 0; }
CALLER=$(ps -o comm= -p "$PPID" 2>/dev/null | tr -d ' '); TOKEN="c3_autodrain $(date +%Y%m%d_%H%M%S) caller=${CALLER:-?}"
KS=$APP/run/KILL_SWITCH
if [ -e "$KS" ]; then R="run/KILL_SWITCH DA CO (giu nguyen: $(head -c 60 "$KS" 2>/dev/null | tr -cd 'A-Za-z0-9_ .=:-'))"; LV=INFO
elif ( set -C; printf '%s\n' "$TOKEN" > "$KS" ) 2>/dev/null && [ -e "$KS" ]; then R="DA DAT run/KILL_SWITCH ($TOKEN)"; LV=OK
else R="KHONG dat duoc run/KILL_SWITCH (quyen/dia?) - bot se len MO LENH MOI"; LV=KHAN; fi
log "$LV $R"
tg "[242-AUTODRAIN] $([ $LV = KHAN ] && echo 'KHAN ')bot c3 LIVE khoi dong lai NGOAI quy trinh golive (caller=${CALLER:-?}: watchdog/boot): $R. Bot quan ly vi the, KHONG mo lenh moi. Kiem nguyen nhan (watchdog.log, logs/full.log) roi mo lai: MODE=undrain bash <OPS>/golive_live_off.sh"
exit 0
