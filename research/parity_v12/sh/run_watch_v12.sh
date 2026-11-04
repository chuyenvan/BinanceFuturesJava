#!/bin/bash
# Owner: bash ~/claude_master/vz_e1_wt/research/parity_v12/sh/run_watch_v12.sh start|status|stop
R=$HOME/claude_master/vz_e1_wt/research/parity_v12
W=$HOME/claude_master/parity_v12w
PID=$W/watch_v12.pid
alive() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
case "${1:-status}" in
  start)
    if alive; then echo "dang chay pid $(cat $PID)"; exit 0; fi
    setsid nohup bash $R/sh/watch_daily_v12.sh >> $W/watch_v12.out 2>&1 < /dev/null &
    echo $! > $PID; sleep 2
    alive && echo "watcher v12 chay nen pid $(cat $PID). Xem: bash $0 status | Dung: bash $0 stop" || { echo "KHONG khoi dong duoc"; tail -5 $W/watch_v12.out; }
    ;;
  status)
    if alive; then echo "watcher v12: DANG CHAY pid $(cat $PID)"; else echo "watcher v12: KHONG chay"; fi
    grep -E "DAY |START|LOI" $W/watch_v12.log 2>/dev/null | tail -10
    ;;
  stop)
    if alive; then pkill -TERM -P "$(cat $PID)" 2>/dev/null; kill -TERM "$(cat $PID)"; echo "da dung pid $(cat $PID)"; else echo "khong chay"; fi
    ;;
  *) echo "dung: $0 start|status|stop"; exit 1 ;;
esac
