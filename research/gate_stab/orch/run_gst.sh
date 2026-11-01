#!/bin/bash
# GATE SEED A (ADD3/4/5): owner chay 1 lenh. start | status | stop | dry
#   bash ~/claude_master/gst1030/orch/run_gst.sh start
OD=/home/ubuntu/claude_master/gst1030/orch
export LIVE_IS_SHADOW_HOST=true
PY="python3 $OD/gst_orch.py"
PID=$OD/orch.pid
alive() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
case "${1:-status}" in
  start)
    if [ "${DRY:-0}" = "1" ]; then exec $PY dry; fi
    if alive; then echo "dang chay pid $(cat $PID)"; exit 0; fi
    setsid nohup $PY run >> "$OD/orch.out" 2>&1 < /dev/null &
    echo $! > "$PID"
    echo "GST orchestrator chay nen pid $(cat $PID). Xem: bash $0 status | Dung: bash $0 stop | Log: $OD/orch.log"
    ;;
  status)
    if alive; then echo "orchestrator: DANG CHAY pid $(cat $PID)"; else echo "orchestrator: KHONG chay"; fi
    $PY status | head -40
    ls -la /home/ubuntu/claude_master/locks/kaggle_priority 2>/dev/null || echo "kaggle_priority: khong co"
    tail -n 8 "$OD/orch.log" 2>/dev/null
    ;;
  stop)
    if alive; then kill -TERM "$(cat $PID)"; echo "da gui SIGTERM pid $(cat $PID)"; else echo "khong chay"; fi
    sleep 2; rm -f /home/ubuntu/claude_master/locks/kaggle_priority && echo "da xoa kaggle_priority"
    ;;
  dry) exec $PY dry ;;
  *) echo "dung: $0 start|status|stop|dry"; exit 1 ;;
esac
