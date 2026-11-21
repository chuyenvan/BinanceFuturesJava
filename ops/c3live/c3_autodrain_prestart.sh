#!/usr/bin/env bash
_RC=0
trap 'exit $_RC' EXIT
# ^ [VONG3 nit R1b] trap DAU TIEN (truoc header): loi cu phap o bat ky dong sau => van rc 0 (khong chan start)
# =============================================================================
# c3_autodrain_prestart.sh - [OPS5 muc 4] (cai tren 242 thanh /usr/local/sbin/h242-prestart-c3.sh boi install_242_autodrain.sh)
#   Boc prestart goc (/usr/local/sbin/h242-prestart.sh <APP> <MainClass>): watchdog (WD_PRESTART) va systemd h242-trading (ExecStartPre)
#   goi TRUOC khi start bot. Script go-live (golive_*/deploy_*/rollback_*) start bang bin/daemon.sh truc tiep + PAUSE watchdog => KHONG qua day.
#   => moi lan start qua day = khoi dong lai NGOAI y muon (watchdog HB_STALE_KILL / TRADING_DOWN / boot may).
# Neu conf/env.sh co LIVE_ADAPTER=live: THEM dong token c3_autodrain vao run/KILL_SWITCH (>>, KHONG ghi de file co san) TRUOC khi start =>
#   bot len o trang thai DRAIN (van quan ly vi the c3, KHONG mo lenh moi) + Telegram. Mo lai: bash <OPS>/golive_boot_undrain.sh (CHI go dong
#   c3_autodrain). [OPS6 T20] KS co san (dong nguoi khac) => THEM dong token cua minh (>>), khong ghi de, khong xoa.
# KHONG BAO GIO chan start (vi the can duoc quan ly) - [OPS5_FIX A-1]:
#   - moi nhanh cua wrapper tra rc 0 (dat KILL_SWITCH loi, run/ mat, STATE/tg.env loi, dia day, bien rong ...);
#   - prestart goc MAT / mat quyen x / rc 126|127 (khong exec duoc) => log KHAN + Telegram (curl -m 15), BO QUA buoc goc, van xet drain, rc 0
#     (= hanh vi watchdog truoc OPS5: `[ -x PRESTART ]` sai => start khong prestart);
#   - NGOAI LE DUY NHAT: prestart goc chay duoc va TU tra rc != 0 (vd 1 = deps chua san) => tra nguyen rc (watchdog truoc OPS5 cung vay).
#   - KHONG set -e/-u/pipefail; trap EXIT ep rc ve _RC (chi gan khi ngoai le tren) => loi ngam (bien rong, pipe, ghi loi) khong doi rc.
# Bien (test): AD_ORIG_PRESTART AD_STATE_DIR AD_TG_ENV AD_TG_SINK AD_TG_API
# [OPS6 luot3 m-4] fail-closed: LIVE_ADAPTER rong / khong doc duoc => coi nhu live; dong token ghi TRUOC prestart goc. GIOI HAN (ngoai tam
#   wrapper): h242_watchdog.sh:127 `[ -x "$PRESTART" ]` FAIL-OPEN (wrapper mat file / mat quyen x => watchdog start KHONG qua wrapper, KHONG
#   drain); start TAY (bin/daemon.sh start, java tay) khong qua wrapper. golive_monitor.sh moi luot kiem boot guard (wrapper ton tai + x + md5,
#   drop-in, cron WD_PRESTART) => mat => KHAN (chi DOC 242).
# =============================================================================
set +e +u
ORIG=${AD_ORIG_PRESTART:-/usr/local/sbin/h242-prestart.sh}
STATE=${AD_STATE_DIR:-/var/lib/c3_autodrain}
TG_ENV=${AD_TG_ENV:-/root/.config/h242_watchdog/tg.env}
APP=${1:-/home/chuyennd/java/v_t_m}
mkdir -p "$STATE" 2>/dev/null
log() { echo "$(date '+%F %T%z') $*" >> "$STATE/autodrain.log" 2>/dev/null; echo "[c3_autodrain] $*" 2>/dev/null; return 0; }
tg() {
  local msg tok chat code
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/[CHE]/g' | head -c 3000)
  if [ -n "${AD_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$AD_TG_SINK" 2>/dev/null; return 0; fi
  [ -r "$TG_ENV" ] || { log "NO_CHANNEL khong doc duoc file Telegram"; echo "$(date '+%F %T%z') $msg" >> "$STATE/ALERT_PENDING.txt" 2>/dev/null; return 0; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$TG_ENV" 2>/dev/null | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$TG_ENV" 2>/dev/null | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || { log "file Telegram thieu token/chat"; return 0; }
  code=$(printf 'url = "%s/bot%s/sendMessage"\n' "${AD_TG_API:-https://api.telegram.org}" "$tok" | timeout 20 curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null); tok=""; chat=""
  log "telegram http=$code"; return 0
}
# [OPS6 luot3 m-4] FAIL-CLOSED + SOM NHAT: doc LIVE_ADAPTER (DONG CUOI "export LIVE_ADAPTER=" cua conf/env.sh) TRUOC prestart goc. Chi khi
#   doc duoc gia tri KHAC live ro rang (vd dry) => khong drain. Rong / khong doc duoc (file mat, quyen, dinh dang la) => COI NHU live.
#   Dong token ghi NGAY (truoc prestart goc) => ke ca prestart goc treo / bi giet / rc != 0 thi KS da co truoc khi JVM co the len.
AD=$(sed -n 's/^[[:space:]]*export[[:space:]][[:space:]]*LIVE_ADAPTER=//p' "$APP/conf/env.sh" 2>/dev/null | tail -1 | tr -d "\"' \r")
NOLIVE=0; [ -n "$AD" ] && [ "$AD" != live ] && NOLIVE=1
if [ "$NOLIVE" = 0 ]; then
  CALLER=$(ps -o comm= -p "$PPID" 2>/dev/null | tr -cd 'A-Za-z0-9_.-'); TOKEN="c3_autodrain $(date +%Y%m%d_%H%M%S) caller=${CALLER:-unknown}"   # [VONG3 F1] khop regex token chuan
  KS=$APP/run/KILL_SWITCH
  # [OPS6 T20] ghi THEO DONG: dong token RIENG "c3_autodrain <ts> caller=<..>" LUON co trong run/KILL_SWITCH TRUOC khi start (them >>, KHONG ghi de /
  #   KHONG xoa dong nguoi khac). Da co dong c3_autodrain => giu (khong them dong thu 2). Mo lai: golive_boot_undrain.sh CHI go dong c3_autodrain.
  ADRX='^c3_autodrain [0-9]{8}_[0-9]{6}( caller=[A-Za-z0-9_.-]*)?$'
  KS0=$([ -e "$KS" ] && head -c 60 "$KS" 2>/dev/null | tr -cd 'A-Za-z0-9_ .=:-')
  if [ -e "$KS" ] && grep -qxE "$ADRX" "$KS" 2>/dev/null; then R="run/KILL_SWITCH DA CO dong c3_autodrain (giu nguyen, khong them: $KS0)"; LV=INFO
  else
    [ -s "$KS" ] && [ -n "$(tail -c 1 "$KS" 2>/dev/null)" ] && printf '\n' >> "$KS" 2>/dev/null   # dong cuoi thieu xuong dong => khong dinh vao dong nguoi khac
    if printf '%s\n' "$TOKEN" >> "$KS" 2>/dev/null && grep -qxF "$TOKEN" "$KS" 2>/dev/null; then
      if [ -n "$KS0" ]; then R="DA THEM dong $TOKEN vao run/KILL_SWITCH co san (dong nguoi khac GIU NGUYEN: $KS0)"; else R="DA DAT run/KILL_SWITCH ($TOKEN)"; fi; LV=OK
    elif [ -e "$KS" ]; then R="run/KILL_SWITCH CO nhung ghi dong token LOI (dia day?) - bot van DRAIN vi file ton tai"; LV=KHAN
    else R="KHONG dat duoc run/KILL_SWITCH (quyen/dia?) - bot se len MO LENH MOI"; LV=KHAN; fi
  fi
  [ -n "$AD" ] || { R="$R; LIVE_ADAPTER KHONG doc duoc tu conf/env.sh => COI NHU live (fail-closed)"; [ "$LV" = INFO ] && LV=OK; }
  log "$LV $R (ghi TRUOC prestart goc)"
fi
PRE_NOTE=""
if [ -f "$ORIG" ] && [ -x "$ORIG" ]; then
  "$ORIG" "$@"; rc=$?
  if [ "$rc" = 126 ] || [ "$rc" = 127 ]; then
    PRE_NOTE="prestart goc $ORIG KHONG exec duoc (rc=$rc) - BO QUA buoc goc, VAN start bot"; log "KHAN $PRE_NOTE"
  elif [ "$rc" != 0 ]; then
    log "prestart goc rc=$rc (bot KHONG duoc start - giong truoc OPS5)$([ "$NOLIVE" = 0 ] && echo ' - dong token c3_autodrain DA ghi truoc (giu: lan start sau van drain)' || echo ' - khong drain (khong live)')"; _RC=$rc; exit "$rc"
  fi
else
  PRE_NOTE="prestart goc $ORIG MAT/khong co quyen x - BO QUA buoc goc, VAN start bot (giong watchdog truoc OPS5)"; log "KHAN $PRE_NOTE"
fi
if [ "$NOLIVE" = 1 ]; then
  log "LIVE_ADAPTER=$AD (khong live, doc ro rang) - khong drain"
  [ -n "$PRE_NOTE" ] && tg "[242-AUTODRAIN] KHAN $PRE_NOTE. LIVE_ADAPTER=$AD (khong live) - khong drain. Can owner kiem /usr/local/sbin."
  exit 0
fi
[ -n "$PRE_NOTE" ] && LV=KHAN
log "$LV $R"
tg "[242-AUTODRAIN] $([ "$LV" = KHAN ] && echo 'KHAN ')bot c3 LIVE khoi dong lai NGOAI quy trinh golive (caller=${CALLER:-?}: watchdog/boot): $R. Bot quan ly vi the, KHONG mo lenh moi.${PRE_NOTE:+ CANH BAO: $PRE_NOTE.} Kiem nguyen nhan (watchdog.log, logs/full.log) roi mo lai (CHI go dong c3_autodrain): bash <OPS>/golive_boot_undrain.sh"
exit 0
