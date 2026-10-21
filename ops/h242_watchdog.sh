#!/usr/bin/env bash
# ops/h242_watchdog.sh — watchdog app trading v_t_m CHAY TREN 242 (root cron */2). Runbook: docs/runbooks/DEPLOY_V11D_242.md §4.
#
# Quyet dinh moi lan chay (1 lan / 2 phut):
#   - 0 process trading (dong lenh co dung main class + cwd = APP)  => log + Telegram + START bang script start hien tai
#     (prestart h242-prestart.sh neu co, roi `bin/daemon.sh start`), env giong unit h242-trading (PATH, LANG, nofile).
#     Chong chay doi: flock (moi lan cron), dem lai process NGAY TRUOC khi start, prestart tu chan neu dang chay,
#     backoff WD_START_BACKOFF_SEC giua 2 lan start (app chet ngay sau start => khong vong lap).
#   - >= 2 process trading (ngoai cua so Utils.reset) => chi CANH BAO (DOUBLE_JVM). Khong kill, khong start.
#   - 1 process, song < WD_GRACE_SEC => bo qua heartbeat (warm-up / vua tu-restart).
#   - heartbeat (mtime run/heartbeat) cu > WD_HB_WARN_SEC (300) => CANH BAO (khong kill).
#   - heartbeat cu > WD_HB_KILL_SEC (600) VA lan chay truoc DA canh bao HB_STALE => stop (`bin/daemon.sh stop`: SIGTERM,
#     <= 60 s, roi -9; neu PID van song => kill dung PID do) roi start.
#   - heartbeat KHONG co file => chi canh bao HB_MISSING (khong bao gio kill vi thieu file — vd quen LIVE_HEARTBEAT=1).
#   - file $STATE_DIR/PAUSE ton tai => thoat ngay (owner dat khi deploy/restart tay).
# Telegram: token/chat doc tu WD_TG_ENV (dong `TG_TOKEN=`/`tele-token:` va `TG_CHAT=`/`tele-chat-id:` — giong health_242.sh),
#   token truyen qua `curl -K -` (khong lo tren ps), KHONG BAO GIO in ra log. Khong co file => ghi ALERT_PENDING.txt.
# Moi nguong/duong dan co the doi qua env WD_* (xem khoi bien duoi); WD_TAG=" TEST" gan nhan vao tin (thu kenh).
# Dung:  h242_watchdog.sh            (cron)
#        h242_watchdog.sh --dry-run  (in quyet dinh ra stdout; khong gui, khong start/stop, khong ghi state)
set -u
APP=${WD_APP:-/home/chuyennd/java/v_t_m}
MC=${WD_MAIN_CLASS:-com.binance.chuyennd.trading.BinanceOrderTradingManager}
HB_FILE=${WD_HB_FILE:-$APP/run/heartbeat}
HB_MODE=${WD_HEARTBEAT:-1}
HB_WARN=${WD_HB_WARN_SEC:-300}
HB_KILL=${WD_HB_KILL_SEC:-600}
GRACE=${WD_GRACE_SEC:-600}
DOUBLE_MIN_AGE=${WD_DOUBLE_MIN_AGE_SEC:-120}
BACKOFF=${WD_START_BACKOFF_SEC:-600}
REMIND=${WD_REMIND_SEC:-1800}
START_WAIT=${WD_START_WAIT_SEC:-30}
STOP_WAIT=${WD_STOP_WAIT_SEC:-75}
TERM_WAIT=${WD_TERM_WAIT_SEC:-60}
STATE_DIR=${WD_STATE_DIR:-/var/lib/h242_watchdog}
LOGF=${WD_LOG:-$STATE_DIR/watchdog.log}
TG_ENV=${WD_TG_ENV:-/root/.config/h242_watchdog/tg.env}
TG_API=${WD_TG_API:-https://api.telegram.org}
PRESTART=${WD_PRESTART:-/usr/local/sbin/h242-prestart.sh}
START_CMD=${WD_START_CMD:-bin/daemon.sh start}
STOP_CMD=${WD_STOP_CMD:-bin/daemon.sh stop}
RUN_PATH=${WD_PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}
NOFILE=${WD_NOFILE:-65536}
LOG_MAX=${WD_LOG_MAX_BYTES:-5000000}
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

mkdir -p "$STATE_DIR" || { echo "$(date '+%F %T%z') khong tao duoc $STATE_DIR" >&2; exit 1; }
exec 9>"$STATE_DIR/.lock"
flock -n 9 || { echo "$(date '+%F %T%z') lock busy - bo qua lan nay" >&2; exit 0; }
now=$(date +%s)

log() {
  local m; m="$(date '+%F %T%z') $*"
  if [ $DRY = 1 ]; then echo "$m"; return; fi
  if [ -f "$LOGF" ] && [ "$(stat -c %s "$LOGF" 2>/dev/null || echo 0)" -gt "$LOG_MAX" ]; then mv -f "$LOGF" "$LOGF.1"; fi
  echo "$m" >> "$LOGF"
}

if [ -e "$STATE_DIR/PAUSE" ]; then log "PAUSE ($STATE_DIR/PAUSE ton tai) - khong lam gi"; exit 0; fi

# ---- state (key=value, chi so/chuoi ngan; KHONG co token) ----
SF="$STATE_DIR/state"
hb_warned=0; last_start=0; double_seen=0; down_alerted=0
declare -A LAST_ALERT=()
if [ -r "$SF" ]; then
  while IFS='=' read -r k v; do
    case "$k" in
      hb_warned|last_start|double_seen|down_alerted) printf -v "$k" '%s' "${v//[^0-9]/}" ;;
      la_*) LAST_ALERT[${k#la_}]=${v//[^0-9]/} ;;
    esac
  done < "$SF"
fi
save_state() {
  [ $DRY = 1 ] && return
  { echo "hb_warned=${hb_warned:-0}"; echo "last_start=${last_start:-0}"; echo "double_seen=${double_seen:-0}"
    echo "down_alerted=${down_alerted:-0}"
    # bash 4.2 (CentOS 7) + set -u: khong lap tren mang rong
    if [ "${#LAST_ALERT[@]}" -gt 0 ]; then for k in "${!LAST_ALERT[@]}"; do echo "la_$k=${LAST_ALERT[$k]}"; done; fi
  } > "$SF.tmp" && mv -f "$SF.tmp" "$SF"
}

tg_send() {   # $1 = noi dung (khong chua bi mat)
  local msg="[242-WATCHDOG${WD_TAG:-}] $1" code
  if [ $DRY = 1 ]; then echo "WOULD_SEND: $msg"; return 0; fi
  if [ ! -r "$TG_ENV" ]; then
    echo "$(date '+%F %T%z') $msg" >> "$STATE_DIR/ALERT_PENDING.txt"; log "NO_CHANNEL (khong doc duoc $TG_ENV) $msg"; return 0
  fi
  if ! command -v curl > /dev/null 2>&1; then log "NO_CURL $msg"; return 0; fi
  code=$( TOK=$(sed -nr 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"'"'"' ')
          CHAT=$(sed -nr 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"'"'"' ')
          [ -n "$TOK" ] && [ -n "$CHAT" ] || { echo "nokey"; exit 0; }
          printf 'url = "%s/bot%s/sendMessage"\n' "$TG_API" "$TOK" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
            --data-urlencode "chat_id=$CHAT" --data-urlencode "text=$msg" 2>/dev/null || echo "curl_err" )
  log "SENT http=$code $msg"
}

alert() {    # $1 = khoa chong lap, $2 = noi dung. Cung khoa => toi da 1 lan / REMIND giay.
  local key=$1 last=${LAST_ALERT[$1]:-0}
  if [ $((now - last)) -ge "$REMIND" ]; then tg_send "$2"; LAST_ALERT[$key]=$now; else log "ALERT_SUPPRESSED key=$key $2"; fi
}

# ---- tim process trading: dong lenh co arg == MC, cwd == APP ----
APP_REAL=$(readlink -f "$APP")
find_pids() {
  local p cwd
  for p in $(pgrep -f -- "$MC" 2>/dev/null); do
    [ "$p" = "$$" ] && continue
    [ -r "/proc/$p/cmdline" ] || continue
    tr '\0' '\n' < "/proc/$p/cmdline" 2>/dev/null | grep -qxF -- "$MC" || continue
    cwd=$(readlink -f "/proc/$p/cwd" 2>/dev/null) || continue
    [ "$cwd" = "$APP_REAL" ] || continue
    echo "$p"
  done
}
etimes() { ps -o etimes= -p "$1" 2>/dev/null | tr -d ' '; }

do_start() {   # $1 = ly do
  if [ $((now - ${last_start:-0})) -lt "$BACKOFF" ]; then
    log "START_BACKOFF lan start truoc cach $((now - last_start))s < ${BACKOFF}s - KHONG start"
    alert START_BACKOFF "START_BACKOFF: app van chua song sau lan start $((now - last_start))s truoc ($1). Can owner kiem logs/nohup.out."
    return 1
  fi
  if [ -n "$(find_pids)" ]; then log "START_SKIP process da xuat hien lai truoc khi start"; return 0; fi
  if [ $DRY = 1 ]; then echo "WOULD_START ($1): prestart=$PRESTART cmd='cd $APP && $START_CMD'"; return 0; fi
  last_start=$now; save_state
  local rc=0 envs="PATH=$RUN_PATH LANG=en_US.UTF-8 HOME=${HOME:-/root}"
  if [ -x "$PRESTART" ]; then
    env -i $envs "$PRESTART" "$APP" "$MC" >> "$LOGF" 2>&1 9>&-; rc=$?
    if [ $rc -ne 0 ]; then
      log "PRESTART rc=$rc - KHONG start"; alert START_FAIL "PRESTART rc=$rc ($1) - app KHONG duoc start. Can owner kiem."; return 1
    fi
  fi
  # 9>&- : JVM con KHONG duoc giu fd cua flock (neu giu => moi lan cron sau deu "lock busy")
  ( cd "$APP" && ulimit -n "$NOFILE" 2>/dev/null; env -i $envs bash -c "$START_CMD" ) >> "$LOGF" 2>&1 9>&-; rc=$?
  local i np=""
  for ((i = 0; i < START_WAIT; i += 2)); do sleep 2; np=$(find_pids); [ -n "$np" ] && break; done
  if [ -n "$np" ]; then
    log "START_OK rc=$rc pid=$(echo $np | tr '\n' ' ')"; tg_send "START_OK ($1) pid=$(echo $np | tr '\n' ' ')"
  else
    log "START_FAIL rc=$rc - sau ${START_WAIT}s van khong thay process"; alert START_FAIL "START_FAIL ($1) rc=$rc - khong thay process sau ${START_WAIT}s"
  fi
}

do_stop() {   # $1 = pid dang treo
  if [ $DRY = 1 ]; then echo "WOULD_STOP pid=$1 cmd='cd $APP && $STOP_CMD'"; return 0; fi
  ( cd "$APP" && env -i PATH="$RUN_PATH" LANG=en_US.UTF-8 bash -c "$STOP_CMD" ) >> "$LOGF" 2>&1 9>&-
  local i
  for ((i = 0; i < STOP_WAIT; i += 3)); do kill -0 "$1" 2>/dev/null || break; sleep 3; done
  if kill -0 "$1" 2>/dev/null; then
    log "STOP: pid $1 van song sau stop script - SIGTERM dung pid"; kill -TERM "$1" 2>/dev/null
    for ((i = 0; i < TERM_WAIT; i += 3)); do kill -0 "$1" 2>/dev/null || break; sleep 3; done
    kill -0 "$1" 2>/dev/null && { log "STOP: SIGKILL pid $1"; kill -KILL "$1" 2>/dev/null; sleep 2; }
  fi
  kill -0 "$1" 2>/dev/null && { log "STOP_FAIL pid $1 van song"; return 1; }
  log "STOP_OK pid $1"; return 0
}

# ---- quyet dinh ----
PIDS=$(find_pids); N=$(echo -n "$PIDS" | grep -c . || true)
if [ "$N" -eq 0 ]; then
  log "DOWN 0 process trading (main=$MC cwd=$APP)"
  if [ "${down_alerted:-0}" = 0 ]; then tg_send "TRADING_DOWN: khong thay process $MC - watchdog se start"; down_alerted=1; fi
  do_start "TRADING_DOWN"
  [ -n "$(find_pids)" ] && down_alerted=0
  hb_warned=0; double_seen=0
elif [ "$N" -ge 2 ]; then
  youngest=999999999; for p in $PIDS; do e=$(etimes "$p"); [ -n "$e" ] && [ "$e" -lt "$youngest" ] && youngest=$e; done
  if [ "$youngest" -lt "$DOUBLE_MIN_AGE" ]; then
    log "DOUBLE_TRANSIENT n=$N youngest=${youngest}s (< ${DOUBLE_MIN_AGE}s, co the la Utils.reset) - cho"
  else
    double_seen=$(( ${double_seen:-0} + 1 ))
    log "DOUBLE_JVM n=$N pids=$(echo $PIDS) youngest=${youngest}s seen=$double_seen"
    [ "$double_seen" -ge 2 ] && alert DOUBLE_JVM "DOUBLE_JVM: $N process trading (pids $(echo $PIDS)) - KHONG tu xu ly, can owner"
  fi
else
  double_seen=0; down_alerted=0
  P=$PIDS; up=$(etimes "$P"); up=${up:-0}
  if [ "$HB_MODE" != 1 ]; then
    [ $DRY = 1 ] && log "OK pid=$P up=${up}s (heartbeat tat)"
  elif [ "$up" -lt "$GRACE" ]; then
    log "OK_GRACE pid=$P up=${up}s < ${GRACE}s - chua xet heartbeat"
  elif [ ! -e "$HB_FILE" ]; then
    log "HB_MISSING pid=$P up=${up}s file=$HB_FILE"
    alert HB_MISSING "HB_MISSING: khong co $HB_FILE (LIVE_HEARTBEAT=1 chua bat?) - chi canh bao, KHONG kill"
  else
    age=$(( now - $(stat -c %Y "$HB_FILE") ))
    if [ "$age" -gt "$HB_KILL" ] && [ "${hb_warned:-0}" = 1 ]; then
      log "HB_STALE_KILL pid=$P up=${up}s hb_age=${age}s > ${HB_KILL}s (da canh bao truoc) => stop + start"
      tg_send "HB_STALE_KILL: heartbeat cu ${age}s > ${HB_KILL}s - stop pid $P roi start lai"
      if do_stop "$P"; then do_start "HB_STALE_KILL"; else alert STOP_FAIL "STOP_FAIL pid $P - can owner"; fi
      hb_warned=0
    elif [ "$age" -gt "$HB_WARN" ]; then
      log "HB_STALE pid=$P up=${up}s hb_age=${age}s > ${HB_WARN}s (kill khi > ${HB_KILL}s o lan sau)"
      [ "${hb_warned:-0}" = 0 ] && tg_send "HB_STALE: heartbeat cu ${age}s (pid $P) - se stop/start neu > ${HB_KILL}s"
      hb_warned=1
    else
      if [ "${hb_warned:-0}" = 1 ]; then tg_send "HB_RECOVERED pid=$P hb_age=${age}s"; log "HB_RECOVERED pid=$P hb_age=${age}s"; fi
      hb_warned=0
      [ $DRY = 1 ] && log "OK pid=$P up=${up}s hb_age=${age}s"
      # 1 dong OK / gio de biet watchdog con chay
      h=$(date +%H); [ "$(cat "$STATE_DIR/.ok_hour" 2>/dev/null)" != "$h" ] && [ $DRY = 0 ] && { echo "$h" > "$STATE_DIR/.ok_hour"; log "OK pid=$P up=${up}s hb_age=${age}s"; }
    fi
  fi
fi
save_state
exit 0
