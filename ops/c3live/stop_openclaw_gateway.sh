#!/usr/bin/env bash
# =============================================================================
# stop_openclaw_gateway.sh — DUNG openclaw gateway tren Oracle + TAT tu khoi dong lai. KHONG xoa du lieu/workspace openclaw.
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/stop_openclaw_gateway.sh   # chi in trang thai + ke hoach
#   bash ~/claude_master/v12/c3live/ops/c3live/stop_openclaw_gateway.sh         # chay THAT sau khi go YES
# Ly do: openclaw tung tu xoa 15 GB du lieu nghien cuu (skill host-disk-reclaim, 10-28); claw tam dung nhung gateway van ghi sqlite.
# Cach dung chuan (gateway chay duoi systemd --user, unit openclaw-gateway.service, Restart=always, enabled, Linger=yes):
#   1) systemctl --user disable <unit>   (khong tu bat khi user-manager/boot khoi dong; dao nguoc duoc)
#   2) systemctl --user stop <unit>      (Restart=always KHONG kich hoat khi stop co chu dich)
#   3) con process khop cmdline (chay ngoai unit) => TERM, 15 s sau van con => KILL (chi process cua user nay, khop dung cmdline)
#   4) crontab co dong chua 'openclaw' (ca @reboot) => backup crontab, comment dong do bang '#OC_OFF '
# Bat lai (in ra cuoi): systemctl --user enable --now <unit>  [+ khoi phuc crontab tu backup neu buoc 4 co doi]
# =============================================================================
set -uo pipefail
DRY=${DRY:-0}
UNIT=${OC_UNIT:-openclaw-gateway.service}
PAT=${OC_PAT:-openclaw/dist/index.js gateway}
SC=${OC_SYSTEMCTL:-systemctl}; CT=${OC_CRONTAB:-crontab}
LOGDIR=${OC_LOGDIR:-$HOME/claude_master/deploy}
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "$XDG_RUNTIME_DIR/bus" ] && export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
TS=$(date +%Y%m%d_%H%M%S); mkdir -p "$LOGDIR"
LOG=$LOGDIR/stop_openclaw_gateway_${TS}$([ "$DRY" = 1 ] && echo _dry).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(date '+%F %T')] $*"; }
NF=0; ok() { say "OK   $*"; }; bad() { say "FAIL $*"; NF=$((NF + 1)); }
pids() { pgrep -u "$(id -u)" -f -- "$PAT" 2>/dev/null | grep -vx "$$" || true; }
cronl() { $CT -l 2>/dev/null | grep -n -i 'openclaw' | grep -v '^[0-9]*:#' || true; }
state() {
  say "--- trang thai ($1)"
  local p; p=$(pids | tr '\n' ' ')
  echo "   process khop '$PAT': ${p:-khong co}"
  for x in $p; do echo "     pid $x start=$(ps -o lstart= -p "$x" 2>/dev/null) rss=$(ps -o rss= -p "$x" 2>/dev/null | tr -d ' ')KB cgroup=$(sed -n 's/^0:://p' /proc/$x/cgroup 2>/dev/null)"; done
  echo "   unit $UNIT: active=$($SC --user is-active "$UNIT" 2>/dev/null) enabled=$($SC --user is-enabled "$UNIT" 2>/dev/null)"
  echo "   crontab dong openclaw (chua comment): $(cronl | wc -l)"; cronl | sed 's/^/     /' | cut -c1-160
  for f in "$HOME"/.openclaw/state/openclaw.sqlite*; do [ -f "$f" ] && echo "   $(basename "$f"): $(stat -c '%s byte, mtime %y' "$f" | cut -c1-60)"; done
}
say "=== stop_openclaw_gateway DRY=$DRY (unit $UNIT) ==="
state TRUOC
P0=$(pids); A0=$($SC --user is-active "$UNIT" 2>/dev/null); E0=$($SC --user is-enabled "$UNIT" 2>/dev/null); C0=$(cronl)
say "--- ke hoach:"
[ "$E0" = enabled ] && echo "   + systemctl --user disable $UNIT" || echo "   = unit khong enabled ($E0) — khong doi"
[ "$A0" = active ] && echo "   + systemctl --user stop $UNIT" || echo "   = unit khong active ($A0)"
echo "   + process con lai khop cmdline => TERM, 15 s => KILL"
[ -n "$C0" ] && echo "   + comment $(wc -l <<< "$C0") dong crontab chua openclaw (backup truoc)" || echo "   = crontab: khong co dong openclaw"
echo "   = KHONG xoa ~/.openclaw (du lieu, workspace, sqlite)"
if [ "$DRY" = 1 ]; then say "DRY=1: khong doi gi. (DRY PASS)"; exit 0; fi
say ">>> Go YES de DUNG openclaw gateway + tat tu khoi dong:"
read -r ANS || ANS=""; [ "$ANS" = YES ] || { say "Huy. Khong doi gi."; exit 0; }
CBK=""
if [ "$E0" = enabled ]; then $SC --user disable "$UNIT" >/dev/null 2>&1 && ok "disable $UNIT" || bad "disable $UNIT"; fi
if [ "$A0" = active ] || [ "$A0" = activating ] || [ "$A0" = reloading ]; then $SC --user stop "$UNIT" >/dev/null 2>&1 && ok "stop $UNIT" || bad "stop $UNIT"; fi
for i in $(seq 1 30); do [ -z "$(pids)" ] && break; sleep 1; done
if [ -n "$(pids)" ]; then
  say "process van con sau stop unit: $(pids | tr '\n' ' ') => TERM"; kill -TERM $(pids) 2>/dev/null
  for i in $(seq 1 15); do [ -z "$(pids)" ] && break; sleep 1; done
  if [ -n "$(pids)" ]; then say "van con => KILL"; kill -KILL $(pids) 2>/dev/null; sleep 2; fi
fi
if [ -n "$C0" ]; then
  CBK=$LOGDIR/crontab.bak_openclaw_$TS
  if $CT -l > "$CBK" 2>/dev/null && [ -s "$CBK" ]; then
    sed '/^[[:space:]]*#/! { /[Oo][Pp][Ee][Nn][Cc][Ll][Aa][Ww]/ s/^/#OC_OFF / }' "$CBK" | $CT - && ok "crontab: comment dong openclaw (backup $CBK)" || bad "ghi crontab"
  else bad "backup crontab"; fi
fi
sleep 3
state SAU
[ -z "$(pids)" ] && ok "0 process openclaw gateway" || bad "con process: $(pids | tr '\n' ' ')"
A1=$($SC --user is-active "$UNIT" 2>/dev/null); E1=$($SC --user is-enabled "$UNIT" 2>/dev/null)
[ "$A1" != active ] && ok "unit khong active ($A1)" || bad "unit van active"
[ "$E1" != enabled ] && ok "unit khong enabled ($E1)" || bad "unit van enabled"
[ -z "$(cronl)" ] && ok "crontab: 0 dong openclaw dang bat" || bad "crontab con dong openclaw"
say "--- BAT LAI khi can (1 lenh):"
echo "   systemctl --user enable --now $UNIT${CBK:+ && crontab $CBK}"
[ "$NF" = 0 ] && { say "=== XONG: openclaw gateway DA DUNG, khong tu khoi dong lai. Log: $LOG"; exit 0; } || { say "=== FAIL ($NF muc). Log: $LOG"; exit 1; }
