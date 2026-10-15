#!/bin/bash
# QUEUE_1015 P2 watchdog (cron */5): (re)start liq_ws.py if it is not running.
# Oracle only -- never 242. Uses pidfile + cmdline check to avoid duplicates.
STORE="/home/ubuntu/collect/liq"
SCRIPT="/home/ubuntu/claude_master/vz_e1_wt/research/pipeline/collector/liq_ws.py"
PID="$STORE/liq_ws.pid"
mkdir -p "$STORE"

alive=0
if [ -f "$PID" ]; then
  p=$(cat "$PID" 2>/dev/null)
  if [ -n "$p" ] && [ -r "/proc/$p/cmdline" ] && tr '\0' ' ' < "/proc/$p/cmdline" | grep -q "liq_ws.py"; then
    alive=1
  fi
fi

if [ "$alive" -eq 0 ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) watchdog: not alive -> starting" >> "$STORE/liq_ws.log"
  cd "$(dirname "$SCRIPT")" || exit 1
  setsid nohup /usr/bin/python3 "$SCRIPT" >> "$STORE/liq_wrap.out" 2>&1 &
  sleep 2
fi
exit 0
