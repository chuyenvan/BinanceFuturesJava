set -u
R=~/claude_master/v12/a3c
B=~/claude_master/v12/a3c_parity/kh
rm -rf $B; mkdir -p $B/c3canary/run/canary $B/v_t_m/run $B/ing
MC=com.binance.chuyennd.c3live.canary.C3LiveCanary
spawn() {  # spawn <cwd> <args...>  -> echo pid
  local d=$1; shift
  ( cd "$d" && exec python3 -c 'import time; time.sleep(600)' "$@" ) > /dev/null 2>&1 &
  echo $!
}
nowms() { echo $(( $(date +%s) * 1000 )); }
old=$(( ($(date +%s) - 900) * 1000 )); stale=$(( ($(date +%s) - 400) * 1000 ))
run_kh() {
  ( export CANARY_MODE=early CANARY_HOME=$B/c3canary VTM_DIR=$B/v_t_m SSH_242="bash -c" LOGDIR=$B/log CL_TS=t
    . $R/ops/c3live/canary/canary_lib.sh; cl_kill_hung; echo "CL_KILLED=$CL_KILLED" )
}
alive() { kill -0 $1 2>/dev/null && echo ALIVE || echo DEAD; }
# T1: java-like process in v_t_m with main class, claims lock pid, stale => must keep (cwd != canary)
p1=$(spawn $B/v_t_m $MC step K4); echo "x pid=$p1 since=$old" > $B/c3canary/run/c3live_account.lock; echo "pid=$p1 ms=$stale cmd=x" > $B/c3canary/run/canary/canary_jvm.hb
sleep 0.5; echo "T1 (cwd v_t_m):"; run_kh | sed 's/^/  /'; echo "  p1=$(alive $p1)"
# T2: bot-like / ingestor-like processes (no exact main-class arg) in canary dir, holding lock => never counted
p2=$(spawn $B/c3canary BinanceOrderTradingManager "$MC-x"); echo "x pid=$p2 since=$old" > $B/c3canary/run/c3live_account.lock; echo "pid=$p2 ms=$stale cmd=x" > $B/c3canary/run/canary/canary_jvm.hb
sleep 0.5; echo "T2 (no exact main arg):"; run_kh | sed 's/^/  /'; echo "  p2=$(alive $p2)"
# T3: shell wrapper whose single arg contains main class
( cd $B/c3canary && exec bash -c "sleep 600; echo $MC step K4" ) > /dev/null 2>&1 & p3=$!
echo "x pid=$p3 since=$old" > $B/c3canary/run/c3live_account.lock
sleep 0.5; echo "T3 (shell wrapper):"; run_kh | sed 's/^/  /'; echo "  p3=$(alive $p3)"
# T4: real-like canary JVM in canary dir but NOT lock holder
p4=$(spawn $B/c3canary $MC step K4); echo "x pid=999999 since=$old" > $B/c3canary/run/c3live_account.lock
sleep 0.5; echo "T4 (not lock holder):"; run_kh | sed 's/^/  /'; echo "  p4=$(alive $p4)"
# T5: lock holder, lock old, heartbeat FRESH => keep
echo "x pid=$p4 since=$old" > $B/c3canary/run/c3live_account.lock; echo "pid=$p4 ms=$(nowms) cmd=x" > $B/c3canary/run/canary/canary_jvm.hb
echo "T5 (hb fresh):"; run_kh | sed 's/^/  /'; echo "  p4=$(alive $p4)"
# T6: lock holder, lock young (2 min), hb stale => keep
echo "x pid=$p4 since=$(( ($(date +%s) - 120) * 1000 ))" > $B/c3canary/run/c3live_account.lock; echo "pid=$p4 ms=$stale cmd=x" > $B/c3canary/run/canary/canary_jvm.hb
echo "T6 (lock young):"; run_kh | sed 's/^/  /'; echo "  p4=$(alive $p4)"
# T7: symlinked canary dir == v_t_m? CANARY_HOME pointing to v_t_m is refused by cl_init (not called here) — check cwd==V guard
# T8: lock holder + lock old + hb stale => KILL
echo "x pid=$p4 since=$old" > $B/c3canary/run/c3live_account.lock
echo "T8 (hung):"; run_kh | sed 's/^/  /'; echo "  p4=$(alive $p4)"
# T9: hb file of another pid (stale), lock holder p5 old => hb_age falls back to lock age => kill (by design)
p5=$(spawn $B/c3canary $MC step K7); echo "x pid=$p5 since=$old" > $B/c3canary/run/c3live_account.lock; echo "pid=1 ms=$(nowms) cmd=x" > $B/c3canary/run/canary/canary_jvm.hb
sleep 0.5; echo "T9 (hb other pid):"; run_kh | sed 's/^/  /'; echo "  p5=$(alive $p5)"
kill $p1 $p2 $p3 $p4 $p5 2>/dev/null; pkill -f "sleep 600; echo $MC" 2>/dev/null; true
