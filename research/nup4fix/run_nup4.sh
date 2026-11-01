#!/bin/bash
# NUP4-fix: owner chay 1 lenh. start (tu tach nen) | status | stop | dry | clearhalt
#   bash ~/claude_master/nup4_fix/orch/run_nup4.sh start      (DRY=1 ... start = chi in ke hoach, khong push)
OD=/home/ubuntu/claude_master/nup4_fix/orch
PY="python3 $OD/nup4_orch.py"
PID=$OD/orch.pid
alive() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
case "${1:-status}" in
  start)
    if [ "${DRY:-0}" = "1" ]; then exec $PY dry; fi
    if alive; then echo "dang chay pid $(cat $PID)"; exit 0; fi
    setsid nohup $PY run >> "$OD/orch.out" 2>&1 < /dev/null &
    echo $! > "$PID"
    echo "NUP4 orchestrator chay nen pid $(cat $PID). Xem: bash $0 status | Dung: bash $0 stop | Log: $OD/orch.log"
    ;;
  status)
    if alive; then echo "orchestrator: DANG CHAY pid $(cat $PID)"; else echo "orchestrator: KHONG chay"; fi
    $PY status
    tail -n 5 "$OD/orch.log" 2>/dev/null
    ;;
  stop)
    if alive; then kill -TERM "$(cat $PID)"; echo "da gui SIGTERM pid $(cat $PID) (kernel Kaggle dang chay van tiep; start lai de resume)"; else echo "khong chay"; fi
    ;;
  dry) exec $PY dry ;;
  clearhalt) exec $PY clearhalt ;;
  *) echo "dung: $0 start|status|stop|dry|clearhalt"; exit 1 ;;
esac
