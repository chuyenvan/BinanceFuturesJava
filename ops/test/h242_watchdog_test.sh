#!/usr/bin/env bash
# ops/test/h242_watchdog_test.sh — test GIA LAP cho ops/h242_watchdog.sh (chay tren Oracle, KHONG dung 242).
# Process gia (script ten "java", cmdline co main class, cwd = app gia), heartbeat gia, daemon.sh gia, stub Telegram 127.0.0.1.
# argv: <duong dan h242_watchdog.sh> [thu muc test]. In PASS/FAIL tung kich ban; exit 1 neu co FAIL.
set -u
WD=$(readlink -f "$1")
T=${2:-$(mktemp -d /tmp/wdtest.XXXXXX)}
MC=com.binance.chuyennd.trading.BinanceOrderTradingManager
TOKEN="123456789:TESTTOKENabcdefghijklmnopqrstuvwxyz0123"
CHAT=99887766
PORT=$((18000 + RANDOM % 1000))
ts(){ date '+%F %T'; }
say(){ echo "$(ts) $*"; }
FAILS=0; NPASS=0
ok(){ if eval "$2"; then NPASS=$((NPASS+1)); say "PASS $1"; else FAILS=$((FAILS+1)); say "FAIL $1  [$2]"; fi; }

mkdir -p "$T"/{app/bin,app/run,app/logs,app/target,jdk/bin,other/run,state,cfg}
# ---- java gia: giu cmdline "... -cp target/... MC", cwd = app; run/FAKE_HB => cham heartbeat moi 1 s; run/FAKE_HANG_TERM => bo qua SIGTERM
cat > "$T/jdk/bin/java" <<'EOF'
#!/bin/bash
if [ -e run/FAKE_HANG_TERM ]; then trap '' TERM; else trap 'exit 0' TERM; fi
while true; do [ -e run/FAKE_HB ] && touch run/heartbeat; sleep 1; done
EOF
chmod +x "$T/jdk/bin/java"
cat > "$T/app/bin/daemon.sh" <<EOF
#!/bin/bash
cd "\$(dirname "\$0")/.."
PF=run/$MC.pid
case "\$1" in
  start) [ -e run/FAKE_START_FAIL ] && { echo "fake start: khong chay"; exit 0; }
         nohup $T/jdk/bin/java -server -cp target/binance-java-sdk-1.2.4.jar $MC > logs/nohup.out 2>&1 &
         echo \$! > \$PF; echo "fake start pid \$(cat \$PF)";;
  stop)  [ -f \$PF ] || { echo "no pidfile"; exit 0; }; p=\$(cat \$PF); kill \$p 2>/dev/null
         for i in 1 2 3; do kill -0 \$p 2>/dev/null || break; sleep 1; done; rm -f \$PF; echo "fake stop \$p";;
esac
EOF
chmod +x "$T/app/bin/daemon.sh"
printf 'tele-token: %s\ntele-chat-id: %s\n' "$TOKEN" "$CHAT" > "$T/cfg/tg.env"; chmod 600 "$T/cfg/tg.env"
python3 "$(dirname "$0")/tg_stub.py" $PORT "$T/tg.jsonl" "$TOKEN" 2> "$T/stub.err" &
STUB=$!; sleep 1

REAL_BEFORE=$(pgrep -f -- "$MC" | while read p; do readlink -f /proc/$p/cwd; done | grep -v "^$T" | sort | tr '\n' ' ')

fakepids(){ pgrep -f -- "$T/jdk/bin/java" | sort | tr '\n' ' ' | sed 's/ *$//'; }
killfakes(){ pkill -KILL -f -- "$T/jdk/bin/java" 2>/dev/null; sleep 0.5; }
spawn(){ (cd "$1" && nohup "$T/jdk/bin/java" -cp target/binance-java-sdk-1.2.4.jar $MC > /dev/null 2>&1 &) ; sleep 0.5; }
reset_case(){ killfakes; rm -rf "$T/state"/* "$T/state"/.[!.]* "$T/app/run"/* "$T/tg.jsonl"; touch "$T/tg.jsonl"; }
tgn(){ grep -c "$1" "$T/tg.jsonl" 2>/dev/null || true; }
wd(){ env WD_APP="$T/app" WD_STATE_DIR="$T/state" WD_TG_ENV="${TGENV:-$T/cfg/tg.env}" WD_TG_API="http://127.0.0.1:$PORT" \
      WD_PRESTART="${PRE:-/nonexistent}" WD_GRACE_SEC="${GRACE:-0}" WD_START_BACKOFF_SEC="${BACKOFF:-0}" \
      WD_START_WAIT_SEC=6 WD_STOP_WAIT_SEC=9 WD_TERM_WAIT_SEC=6 WD_DOUBLE_MIN_AGE_SEC="${DMA:-0}" WD_REMIND_SEC=1800 \
      bash "$WD" "$@"; }
L="$T/state/watchdog.log"

say "== S1 khong co process: dry-run chi in, khong start, khong gui"
reset_case
out=$(wd --dry-run)
ok "S1 dry-run WOULD_START" '[[ "$out" == *WOULD_START* ]]'
ok "S1 dry-run khong start" '[ -z "$(fakepids)" ]'
ok "S1 dry-run khong gui" '[ "$(tgn .)" = 0 ]'
ok "S1 dry-run khong ghi state" '[ ! -e "$T/state/state" ]'

say "== S2 khong co process: that => canh bao + start + START_OK"
wd; sleep 1
ok "S2 da start 1 process" '[ $(fakepids | wc -w) = 1 ]'
ok "S2 Telegram TRADING_DOWN" '[ "$(tgn TRADING_DOWN:)" = 1 ]'
ok "S2 Telegram START_OK" '[ "$(tgn START_OK)" = 1 ]'
ok "S2 token dung, chat dung" '[ "$(grep -c "\"token_ok\": true" $T/tg.jsonl)" = 2 ] && grep -q "\"chat_id\": \"$CHAT\"" $T/tg.jsonl'
ok "S2 log START_OK" 'grep -q START_OK "$L"'
P2=$(fakepids)

say "== S3 lan sau: process song, heartbeat moi => khong lam gi"
touch "$T/app/run/FAKE_HB"; sleep 2
wd
ok "S3 van dung pid cu" '[ "$(fakepids)" = "$P2" ]'
ok "S3 khong gui them" '[ "$(wc -l < $T/tg.jsonl)" = 2 ]'

say "== S4 heartbeat cu 6 phut => HB_STALE canh bao, KHONG kill"
rm -f "$T/app/run/FAKE_HB"; sleep 1.5; touch -d '-6 min' "$T/app/run/heartbeat"
wd
ok "S4 khong kill" '[ "$(fakepids)" = "$P2" ]'
ok "S4 Telegram HB_STALE" '[ "$(tgn HB_STALE:)" = 1 ]'
ok "S4 state hb_warned=1" 'grep -q "^hb_warned=1" $T/state/state'

say "== S5 heartbeat cu 11 phut + da canh bao => stop + start (pid moi)"
touch -d '-11 min' "$T/app/run/heartbeat"
wd; sleep 1
P5=$(fakepids)
ok "S5 pid cu da chet" '! kill -0 $P2 2>/dev/null'
ok "S5 co dung 1 process moi" '[ $(echo $P5 | wc -w) = 1 ] && [ "$P5" != "$P2" ]'
ok "S5 Telegram HB_STALE_KILL" '[ "$(tgn HB_STALE_KILL:)" = 1 ]'
ok "S5 log STOP_OK + START_OK" 'grep -q "STOP_OK pid $P2" "$L" && [ $(grep -c "START_OK rc=" "$L") = 2 ]'

say "== S6 heartbeat cu 11 phut NHUNG chua canh bao (lan dau thay) => chi canh bao"
reset_case; spawn "$T/app"; P6=$(fakepids); touch -d '-11 min' "$T/app/run/heartbeat"
wd
ok "S6 khong kill lan dau" '[ "$(fakepids)" = "$P6" ]'
ok "S6 HB_STALE" '[ "$(tgn HB_STALE:)" = 1 ] && [ "$(tgn HB_STALE_KILL:)" = 0 ]'

say "== S7 khong co file heartbeat => HB_MISSING, khong bao gio kill"
rm -f "$T/app/run/heartbeat"; rm -f "$T/state/state"
wd; wd; wd
ok "S7 khong kill sau 3 lan" '[ "$(fakepids)" = "$P6" ]'
ok "S7 HB_MISSING 1 tin (chong lap)" '[ "$(tgn HB_MISSING)" = 1 ]'

say "== S8 grace: process tre + heartbeat cu => OK_GRACE"
reset_case; spawn "$T/app"; P8=$(fakepids); touch -d '-20 min' "$T/app/run/heartbeat"; touch "$T/state/state"
GRACE=600 wd; GRACE=600 wd
ok "S8 khong kill trong grace" '[ "$(fakepids)" = "$P8" ] && grep -q OK_GRACE "$L"'

say "== S9 hai process trading => DOUBLE_JVM chi canh bao (lan 2), khong kill/start"
reset_case; spawn "$T/app"; spawn "$T/app"; P9=$(fakepids)
touch "$T/app/run/FAKE_HB"; sleep 1.5
wd
ok "S9 lan 1 chua bao" '[ "$(tgn DOUBLE_JVM)" = 0 ]'
wd
ok "S9 lan 2 bao DOUBLE_JVM" '[ "$(tgn DOUBLE_JVM)" = 1 ]'
ok "S9 van 2 process cu" '[ "$(fakepids)" = "$P9" ]'
DMA=600 wd
ok "S9b vua reset (<min age) => DOUBLE_TRANSIENT" 'grep -q DOUBLE_TRANSIENT "$L"'

say "== S10 process trading o thu muc KHAC (vd shadow Oracle) khong duoc tinh"
reset_case; spawn "$T/other"; PO=$(fakepids); touch "$T/app/run/FAKE_START_FAIL"
wd
ok "S10 coi la DOWN (khong dem process thu muc khac)" 'grep -q "DOWN 0 process" "$L"'
ok "S10 khong dung process thu muc khac" 'kill -0 $PO 2>/dev/null'
ok "S10 start that bai => START_FAIL" '[ "$(tgn START_FAIL)" = 1 ]'

say "== S11 backoff: lan ke trong 10 phut => START_BACKOFF, khong start lai"
BACKOFF=600 wd
ok "S11 START_BACKOFF" 'grep -q START_BACKOFF "$L" && [ "$(tgn START_BACKOFF)" = 1 ]'
ok "S11 khong spawn moi" '[ "$(fakepids)" = "$PO" ]'

say "== S12 prestart rc=1 => KHONG start"
reset_case; rm -f "$T/app/run/FAKE_START_FAIL"
printf '#!/bin/bash\necho "dang chay - khong start lan 2"; exit 1\n' > "$T/prestart.sh"; chmod +x "$T/prestart.sh"
PRE="$T/prestart.sh" wd
ok "S12 khong start" '[ -z "$(fakepids)" ] && grep -q "PRESTART rc=1" "$L"'
printf '#!/bin/bash\necho "deps ok $1 $2"; exit 0\n' > "$T/prestart.sh"
PRE="$T/prestart.sh" wd; sleep 1
ok "S12b prestart rc=0 => start, nhan dung APP + MC" '[ $(fakepids | wc -w) = 1 ] && grep -q "deps ok $T/app $MC" "$L"'

say "== S13 flock: lan chay chong => lock busy, thoat 0"
reset_case; spawn "$T/app"
( exec 9>"$T/state/.lock"; flock 9; sleep 4 ) & LK=$!; sleep 0.5
out=$(wd 2>&1); rc=$?
ok "S13 lock busy" '[[ "$out" == *"lock busy"* ]] && [ $rc = 0 ]'
wait $LK

say "== S14 JVM con KHONG giu fd lock (cron sau khong bi 'lock busy' mai)"
reset_case; wd; sleep 1
out=$(wd 2>&1)
ok "S14 lan sau van chay duoc" '[[ "$out" != *"lock busy"* ]]'
NP=$(fakepids); ok "S14 fd 9 cua JVM khong tro toi .lock" '! ls -l /proc/$NP/fd 2>/dev/null | grep -q "state/.lock"'

say "== S15 PAUSE => khong lam gi"
killfakes; touch "$T/state/PAUSE"; : > "$T/tg.jsonl"
wd
ok "S15 PAUSE khong start" '[ -z "$(fakepids)" ] && [ "$(wc -l < $T/tg.jsonl)" = 0 ]'
rm -f "$T/state/PAUSE"

say "== S16 SIGTERM bi bo qua => kill dung PID (TERM roi KILL)"
reset_case; touch "$T/app/run/FAKE_HANG_TERM"; spawn "$T/app"; PH=$(fakepids)
echo "hb_warned=1" > "$T/state/state"; touch -d '-11 min' "$T/app/run/heartbeat"
rm -f "$T/app/run/$MC.pid"   # pidfile mat => stop script khong kill duoc
wd; sleep 1
ok "S16 pid treo da bi kill" '! kill -0 $PH 2>/dev/null && grep -q "SIGKILL pid $PH" "$L"'
rm -f "$T/app/run/FAKE_HANG_TERM"

say "== S17 khong co tg.env => NO_CHANNEL + ALERT_PENDING, khong loi"
reset_case; touch "$T/app/run/FAKE_START_FAIL"
TGENV=/nonexistent/tg.env wd
ok "S17 ALERT_PENDING" '[ -s "$T/state/ALERT_PENDING.txt" ] && grep -q NO_CHANNEL "$L"'
rm -f "$T/app/run/FAKE_START_FAIL"

say "== S18 khong lo token"
ok "S18 token khong co trong log/state/stdout" '! grep -rq "TESTTOKEN" "$T/state" "$T/app/logs" "$T/stub.err" 2>/dev/null'

killfakes; kill $STUB 2>/dev/null
REAL_AFTER=$(pgrep -f -- "$MC" | while read p; do readlink -f /proc/$p/cwd; done | grep -v "^$T" | sort | tr '\n' ' ')
ok "S19 process that ngoai test khong bi dung (truoc='$REAL_BEFORE')" '[ "$REAL_BEFORE" = "$REAL_AFTER" ]'
say "TONG: PASS=$NPASS FAIL=$FAILS dir=$T"
[ $FAILS = 0 ]
