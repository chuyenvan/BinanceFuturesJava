#!/usr/bin/env bash
# =============================================================================
# test_fake242.sh — chay THU (tren ORACLE) cac script owner ops/c3live/*.sh voi "242 GIA" tren dia Oracle:
# SSH_242="bash -c" (lenh chay cuc bo), SCP_242=cp, APP_DIR = thu muc gia (conf/env.sh, bin/start.sh, bin/daemon.sh gia
# chay 1 process ten BinanceOrderTradingManager = sleep, logs/full.log gia). KHONG ssh, KHONG dung 242, KHONG goi Binance.
#   bash ops/c3live/test/test_fake242.sh <thu_muc_tam>
# Ket qua: dong "TEST PASS n/n" hoac "TEST FAIL ...".
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
REPO=$(cd "$HERE/../.." && pwd)
W=${1:?"thieu thu muc tam"}
rm -rf "$W"; mkdir -p "$W"
F=$W/v_t_m
mkdir -p "$F/conf" "$F/bin" "$F/logs" "$F/run" "$F/target" "$W/deploylog"
cat > "$F/conf/env.sh" <<'EOF'
export LIVE_PROFILE=c3_shadow
export SHADOW_NO_PUSH=true
export LIVE_TS_MKT_EXT=1
# [v11d+exec-probe] chi van hanh (ADDENDUM d)
export LIVE_HEARTBEAT=1
export LIVE_KILLSW_MODE=log
export LIVE_PERIODIC_RESET_HOURS=0
export LIVE_EXEC_PROBE=1
EOF
cat > "$F/bin/start.sh" <<'EOF'
export JAVA_TOOL_OPTIONS="-Xmx3g -XX:+ExitOnOutOfMemoryError -Xlog:gc*:file=logs/gc_%p_%t.log"
EOF
cat > "$F/bin/daemon.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")/.."
case "$1" in
  stop) pkill -f 'BinanceOrderTradingManager fake242' ;;
  start)
    set -a; . conf/env.sh; set +a
    nohup bash -c 'exec -a "BinanceOrderTradingManager fake242" sleep 900' >/dev/null 2>&1 &
    sleep 1
    D=$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000')   # log 242 that ghi gio +07
    {
      echo "$D INFO [main] x: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager"
      echo "$D INFO [main] x: [HEARTBEAT] BAT file=run/heartbeat"
      echo "$D INFO [main] x: [TS-EXT] BAT LIVE_TS_MKT_EXT=1 profile=c3_shadow|c3_live"
      if [ "$LIVE_PROFILE" = c3_live ]; then
        echo "$D WARN [main] x: 🟠 [LIVE_PROFILE=c3_live] BAT — hanh vi C3 day du PUSH=OFF (SHADOW_NO_PUSH=true)"
        echo "$D WARN [main] x: [KILLSW] BAT mode=act (c3_live): ..."
        echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=DRY gateway=dry book=run/c3live_book.json cum=0 killSwitchArmed=true X14=true"
        echo "$D INFO [main] x: [C5] GLOBAL OK"
        echo "$D INFO [main] x: [UNIVERSE] listed=640 alive=600 tradable=480 buyable=470 +0 -0 tradfi_excl=110"
        echo "$D INFO [main] x: [C3-LIVE-RECON] khoi dong: ok=true closedWhileDown=[]"
        # [V12 R4b] dong cua jar R4b (chi khi co FAKE_R4) / exchangeInfo xau (FAKE_EXBAD)
        [ -f FAKE_R4 ] && echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=DRY gateway=c3scope(dry) cum=0 c3_capital=10000.0 tai_khoan=CHINH(pham vi c3) killSwitchArmed=true"
        [ -f FAKE_R4 ] && echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-SCOPE] LEGACY tren tai khoan chinh: 0 vi the (foreign DA BIET, khong phai cum ma, khong chan (A)); LEGACY-busy=0 symbol"
        [ -f FAKE_EXBAD ] && echo "$D ERROR [C3LIVE-OPS] x: [C3-LIVE UNIVERSE] exchangeInfo KHONG hop le (R7 fail-fast): gia lap"
        [ -f FAKE_LATCH ] && echo "$D WARN [main] x: [KILLSW] LATCH action=FLATTEN (truoc NONE) code=C6 codes=[C6] detail=dd=-0.7144"
      else
        echo "$D INFO [main] x: 🟡 [LIVE_PROFILE=c3_shadow] BAT"
      fi
    } >> logs/full.log
    # [2d] log xoay ngay sau start (dong start + LATCH nam o full.log.1) / mat log
    [ -f FAKE_ROTATE ] && { mv -f logs/full.log logs/full.log.1; echo "$D INFO [main] x: (sau xoay log)" > logs/full.log; }
    [ -f FAKE_NOLOG ] && rm -f logs/full.log logs/full.log.*
    touch run/heartbeat ;;
esac
EOF
chmod +x "$F/bin/daemon.sh"
printf 'fake-old-jar-dcae' > "$F/target/binance-java-sdk-1.2.4.jar"
printf 'fake-new-jar-v12dry' > "$W/new.jar"
OLD=$(md5sum < "$F/target/binance-java-sdk-1.2.4.jar" | cut -c1-32)
NEW=$(md5sum < "$W/new.jar" | cut -c1-32)
python3 - "$W/exinfo.json" <<'EOF'
import json, sys
json.dump({"symbols": [{"symbol": "S%03dUSDT" % i} for i in range(150)]}, open(sys.argv[1], "w"), separators=(",", ":"))
EOF
(cd "$F" && bin/daemon.sh start)

export PROC_PAT="BinanceOrderTradingManager fake242" SSH_242="bash -c" SCP_242=cp RHOST="" APP_DIR=$F LOGDIR=$W/deploylog WD_PAUSE=$W/PAUSE OLD_MD5=$OLD NJ=$W/new.jar \
  NJ_MD5=$NEW KILLSW_SH=$REPO/ops/killsw_reset.sh EXINFO_CMD="cat $W/exinfo.json" POST_WAIT_S=2 POST_ROUNDS=2 WAIT_S=3 \
  REANCHOR_WAIT=2 LATCH_WAIT_S=2
# KILLSW_MD5 KHONG dat => dung md5 pin mac dinh trong deploy_v12_dry.sh (kiem pin khop ops/killsw_reset.sh cua repo)
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }

echo "== 1. deploy DRY=1 (truoc 11-18: chi canh bao)"
OUT=$(DRY=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); echo "$OUT" | tail -4
chk "deploy DRY PASS" "echo \"\$OUT\" | grep -q 'DRY PASS'"
chk "deploy DRY khong doi env" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F/conf/env.sh && ! grep -q LIVE_ADAPTER $F/conf/env.sh"
OUT=$(DRY=1 KILLSW_MD5=00000000000000000000000000000000 bash "$HERE/deploy_v12_dry.sh" 2>&1)
chk "deploy tu choi khi md5 killsw_reset.sh sai (pin)" "echo \"\$OUT\" | grep -q 'md5 killsw_reset.sh sai'"
echo "== 2. deploy that KHONG FORCE_DATE (phai tu choi truoc 2026-11-18)"
OUT=$(echo YES | FORCE_TIME=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); echo "$OUT" | tail -2
if [ "$(date +%s)" -lt "$(date -d '2026-11-18 08:00 +07' +%s)" ]; then
  chk "tu choi truoc 11-18" "echo \"\$OUT\" | grep -q 'truoc 2026-11-18'"
fi
echo "== 3. deploy that (FORCE_DATE=1 FORCE_TIME=1, go YES) tren 242 gia"
OUT=$(echo YES | FORCE_DATE=1 FORCE_TIME=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); echo "$OUT" | tail -8
TS=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "deploy XONG" "echo \"\$OUT\" | grep -q '=== XONG'"
chk "deploy kiem 0 dong KILLSW LATCH sau start" "echo \"\$OUT\" | grep -q '0 dong \[KILLSW\] LATCH'"
chk "jar moi tren 242 gia" "[ \"\$(md5sum < $F/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEW ]"
chk "backup jar/env/start" "[ -f $F/target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS ] && [ -f $F/conf/env.sh.bak_v12pre_$TS ] && [ -f $F/bin/start.sh.bak_v12pre_$TS ]"
chk "env them LIVE_ADAPTER=dry + c3_live + act" "grep -qx 'export LIVE_ADAPTER=dry' $F/conf/env.sh && grep -qx 'export LIVE_PROFILE=c3_live' $F/conf/env.sh && grep -qx 'export LIVE_KILLSW_MODE=act' $F/conf/env.sh"
chk "process moi co env c3_live/dry" "tr '\\0' '\\n' < /proc/\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ | grep -qx 'LIVE_ADAPTER=dry'"
chk "exchangeInfo dat vao run/" "[ \$(grep -o '\"symbol\":\"' $F/run/c3live_exchangeInfo.json | wc -l) = 150 ]"
chk "killsw_reset.sh chep sang ops/" "cmp -s $REPO/ops/killsw_reset.sh $F/ops/killsw_reset.sh"
chk "PAUSE watchdog da xoa" "[ ! -f $W/PAUSE ]"
echo "== 4. deploy lan 2 phai tu choi (da co LIVE_ADAPTER)"
OUT=$(DRY=1 FORCE_DATE=1 bash "$HERE/deploy_v12_dry.sh" 2>&1)
chk "deploy lan 2 FAIL o kiem 242" "echo \"\$OUT\" | grep -q 'kiem 242 co muc FAIL'"
echo "== 5. status (chi doc)"
OUT=$(bash "$HERE/c3live_status.sh" 2>&1); echo "$OUT" | head -6
chk "status in env c3_live" "echo \"\$OUT\" | grep -q 'env LIVE_ADAPTER=dry'"
echo "== 6. killsw_reset (wrapper) DRY + YES"
OUT=$(bash "$HERE/killsw_reset.sh" 2>&1)
chk "killsw DRY khong ghi" "echo \"\$OUT\" | grep -q 'DRY: khong ghi' && [ ! -f $F/run/killsw_reset.req ]"
OUT=$(echo YES | DRY=0 bash "$HERE/killsw_reset.sh" 2>&1); echo "$OUT" | tail -3
chk "killsw YES ghi run/killsw_reset.req" "[ -f $F/run/killsw_reset.req ] && grep -q reset_at_ms $F/run/killsw_reset.req"
echo "== 7. reanchor DRY + YES"
OUT=$(bash "$HERE/c3live_reanchor.sh" 2>&1)
chk "reanchor DRY khong ghi" "[ ! -f $F/run/c3live_reanchor.req ]"
OUT=$(echo YES | DRY=0 bash "$HERE/c3live_reanchor.sh" 2>&1)
chk "reanchor YES ghi yeu cau" "[ -f $F/run/c3live_reanchor.req ]"
echo "== 8. rollback DRY + chot gio + YES"
OUT=$(DRY=1 bash "$HERE/rollback_v12.sh" "$TS" 2>&1)
chk "rollback DRY PASS" "echo \"\$OUT\" | grep -q 'DRY PASS'"
HH=$(TZ=Asia/Ho_Chi_Minh date +%-H); MM=$(TZ=Asia/Ho_Chi_Minh date +%-M)
TOK=1; { [ "$MM" -ge 10 ] && [ "$MM" -le 44 ]; } || TOK=0; case "$HH" in 7|19) TOK=0;; esac
if [ "$HH" -eq 1 ] || [ "$HH" -eq 13 ]; then [ "$MM" -gt 20 ] || TOK=0; fi
if [ "$TOK" = 0 ]; then
  OUT=$(echo YES | bash "$HERE/rollback_v12.sh" "$TS" 2>&1)
  chk "rollback tu choi ngoai khung gio (time_ok)" "echo \"\$OUT\" | grep -q 'khong hop le' && grep -qx 'export LIVE_ADAPTER=dry' $F/conf/env.sh"
else
  echo "  (bo qua kiem tu choi ngoai gio: dang trong khung gio hop le $HH:$MM)"
fi
echo '{"version":1,"clusters":[]}' > $F/run/c3live_book.json
echo '35015.29' > $F/run/c3live_killsw_peak
OUT=$(echo YES | FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS" 2>&1); echo "$OUT" | tail -4
chk "rollback xong" "echo \"\$OUT\" | grep -q 'Rollback xong'"
chk "env ve c3_shadow, khong LIVE_ADAPTER" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F/conf/env.sh && ! grep -q LIVE_ADAPTER $F/conf/env.sh"
chk "jar ve ban cu" "[ \"\$(md5sum < $F/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $OLD ]"
chk "so dry doi ten .rb_TS" "[ -f $F/run/c3live_book.json.rb_$TS ] && [ ! -f $F/run/c3live_book.json ]"
chk "process chay lai env c3_shadow" "tr '\\0' '\\n' < /proc/\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ | grep -qx 'LIVE_PROFILE=c3_shadow'"
chk "dinh C6 c3_live doi ten .rb_TS" "[ -f $F/run/c3live_killsw_peak.rb_$TS ] && [ ! -f $F/run/c3live_killsw_peak ]"
echo "== 9. [2c CRIT-1] deploy co dong [KILLSW] LATCH sau start => ROLLBACK TU DONG + FAIL"
touch "$F/FAKE_LATCH"
OUT=$(echo YES | FORCE_DATE=1 FORCE_TIME=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); RC=$?; echo "$OUT" | tail -5
rm -f "$F/FAKE_LATCH"
chk "deploy FAIL vi LATCH (rc!=0)" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'DEPLOY FAIL (kill-switch latch'"
chk "rollback tu dong da chay" "echo \"\$OUT\" | grep -q 'Rollback TU DONG' && echo \"\$OUT\" | grep -q 'Rollback xong'"
chk "sau rollback tu dong: env c3_shadow, jar cu" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F/conf/env.sh && ! grep -q LIVE_ADAPTER $F/conf/env.sh && [ \"\$(md5sum < $F/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $OLD ]"
chk "process chay env c3_shadow sau rollback tu dong" "tr '\\0' '\\n' < /proc/\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ | grep -qx 'LIVE_PROFILE=c3_shadow'"
echo "== 10. [2d] thieu logs/full.log sau start => KHONG duoc PASS gia: FAIL + rollback tu dong"
touch "$F/FAKE_NOLOG"
OUT=$(echo YES | FORCE_DATE=1 FORCE_TIME=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); RC=$?; echo "$OUT" | grep -a 'LATCH_COUNT\|DEPLOY FAIL' | head -3
rm -f "$F/FAKE_NOLOG"
chk "thieu log => FAIL (no_log) + rollback" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'LATCH_COUNT=no_log' && echo \"\$OUT\" | grep -q 'Rollback xong'"
chk "sau rollback (thieu log): env c3_shadow" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F/conf/env.sh && ! grep -q LIVE_ADAPTER $F/conf/env.sh"
echo "== 11. [2d] log xoay trong 120 s, dong LATCH nam o full.log.1 => van bat duoc: FAIL + rollback"
touch "$F/FAKE_ROTATE" "$F/FAKE_LATCH"
OUT=$(echo YES | FORCE_DATE=1 FORCE_TIME=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); RC=$?; echo "$OUT" | grep -a 'LATCH_COUNT\|DEPLOY FAIL' | head -3
rm -f "$F/FAKE_ROTATE" "$F/FAKE_LATCH"
chk "LATCH trong file da xoay => FAIL + rollback" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'LATCH_COUNT=1 ' && echo \"\$OUT\" | grep -q 'Rollback xong'"
chk "sau rollback (log xoay): jar cu" "[ \"\$(md5sum < $F/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $OLD ]"
echo "== 12. [2d] log xoay nhung KHONG co LATCH => buoc hau kiem LATCH dat (dem theo moc thoi gian, ke ca full.log.1)"
rm -f $F/logs/full.log.1
touch "$F/FAKE_ROTATE"
OUT=$(echo YES | FORCE_DATE=1 FORCE_TIME=1 bash "$HERE/deploy_v12_dry.sh" 2>&1); echo "$OUT" | grep -a 'LATCH_COUNT' | head -2
rm -f "$F/FAKE_ROTATE"
chk "log xoay, 0 LATCH => qua buoc LATCH (khong FAIL gia)" "echo \"\$OUT\" | grep -q 'LATCH_COUNT=0 files=2' && echo \"\$OUT\" | grep -q '0 dong \[KILLSW\] LATCH'"
chk "[2e] deploy in tz_shell + moc +07" "echo \"\$OUT\" | grep -q 'tz_shell=.*moc_start_+07='"
echo "== 13. [2e] c3live_ghost_clear.sh: symbol sai / chi xem / YES=1 ghi yeu cau + doc ket qua bot"
OUT=$(bash "$HERE/c3live_ghost_clear.sh" 'xrp;rm' 2>&1); RC=$?
chk "ghost: symbol sai => tu choi" "[ $RC = 2 ] && [ ! -f $F/run/c3live_ghost_clear.req ]"
OUT=$(bash "$HERE/c3live_ghost_clear.sh" XRPUSDT 2>&1)
chk "ghost: khong YES => chi xem, khong ghi" "echo \"\$OUT\" | grep -q 'CHI XEM' && [ ! -f $F/run/c3live_ghost_clear.req ]"
OUT=$(YES=1 GHOST_WAIT=2 bash "$HERE/c3live_ghost_clear.sh" XRPUSDT 2>&1); RC=$?
chk "ghost: YES=1 ghi yeu cau dung symbol; bot gia khong tra loi => exit 5" "[ $RC = 5 ] && [ \"\$(cat $F/run/c3live_ghost_clear.req)\" = XRPUSDT ]"
rm -f $F/run/c3live_ghost_clear.req
( for i in $(seq 1 20); do if [ -f $F/run/c3live_ghost_clear.req ]; then echo "1793000000000 REFUSED XRPUSDT: vi the != 0 (positionRisk=100 account=100)" > $F/run/c3live_ghost_clear.req.result; rm -f $F/run/c3live_ghost_clear.req; break; fi; sleep 0.5; done ) &
OUT=$(YES=1 GHOST_WAIT=8 bash "$HERE/c3live_ghost_clear.sh" XRPUSDT 2>&1); RC=$?; wait
chk "ghost: bot tu choi (vi the != 0) => in ly do, exit 4" "[ $RC = 4 ] && echo \"\$OUT\" | grep -q 'REFUSED XRPUSDT: vi the != 0'"
( for i in $(seq 1 20); do if [ -f $F/run/c3live_ghost_clear.req ]; then echo "1793000000000 OK XRPUSDT: huy stop [c3s-x], xoa cum khoi so" > $F/run/c3live_ghost_clear.req.result; rm -f $F/run/c3live_ghost_clear.req; break; fi; sleep 0.5; done ) &
OUT=$(YES=1 GHOST_WAIT=8 bash "$HERE/c3live_ghost_clear.sh" XRPUSDT 2>&1); RC=$?; wait
chk "ghost: bot OK => exit 0" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK XRPUSDT'"

echo "== 14. [V12 3] script canary (ops/c3live/canary): java GIA in dong RESULT theo file FAKE_* (KHONG goi san, KHONG key that)"
CN=$HERE/canary
cat > "$W/fakejava.sh" <<'FJ'
#!/usr/bin/env bash
# java GIA: bo qua tham so JVM toi lop main; ghi lenh vao run/canary/fake_calls.log; RESULT theo FAKE_TRUOT_<buoc> / FAKE_CANARY_LOCK
while [ $# -gt 0 ] && [ "$1" != com.binance.chuyennd.c3live.canary.C3LiveCanary ]; do shift; done
shift; CMD=${1:-}; K=${2:-}
D=${CANARY_DIR:-run/canary}; mkdir -p "$D"
# [3d] FAKE_SLOW: JVM gia chay 6 s, ghi moc ket thuc (kiem lenh ssh khoi dong tra ve TRUOC khi JVM xong)
[ -f FAKE_SLOW ] && { trap 'echo "END $(date +%s%3N)" >> FAKE_SLOW.log' EXIT; sleep 6; }
echo "$CMD $K TMB=${CANARY_EXPECT_TMB:-} INJ=${CANARY_INJECT_TIMEOUT:-} KF=${LIVE_C3_KEYS_FILE:-} CWD=$(pwd) ENVX=$(env | grep -c -E '^(LIVE_PROFILE|TRADING_PROFILE|LIVE_TS_MKT_EXT)=') REUSE=${CANARY_K0_REUSE_KEEPALIVE:-}" >> "$D/fake_calls.log"
echo "$CMD IPCAP=${CANARY_IP_WEIGHT_CAP:-}" >> "$D/fake_env.log"   # [3i] env -i cua cl_run co truyen nguong IP khong
echo "$CMD PRIOR=${CANARY_PRIOR_LOSS_USDT:-}" >> "$D/fake_prior.log"   # [3k] prior truyen vao JVM (file rieng, khong doi format cu)
sleep 1
[ -f FAKE_CANARY_LOCK ] && { echo "RESULT $CMD TU_CHOI | lock tai khoan con dang bi giu (gia)"; exit 2; }
case "$CMD" in
  keycheck)   # [3d] tmb theo file FAKE_TMB; pos=1 neu co FAKE_NOT_FLAT (flatten xoa, tru khi FAKE_NOT_FLAT_STICKY)
    T=10000; [ -f FAKE_TMB ] && T=$(cat FAKE_TMB); P=0; [ -f FAKE_NOT_FLAT ] && P=1
    # [3i] FAKE_KC_FAIL=<n>: n lan keycheck dau TRUOT vi guard IP (nhu 3h that 05:11:42), roi DAT
    if [ -f FAKE_KC_FAIL ] && [ "$(cat FAKE_KC_FAIL)" -gt 0 ]; then
      echo $(( $(cat FAKE_KC_FAIL) - 1 )) > FAKE_KC_FAIL
      echo "RESULT keycheck TRUOT | GatewayException: rate guard: het ngan sach, can cho 15660 ms > han 2000 ms (gia)"; exit 3
    fi
    echo "KEYCHECK serverTime=1 tmb=$T multiAssets=true dual=false assets={BFUSD=10000.00000000, USDT=1000.00000000} scope=C00USDT,C01USDT legacy=pos:44,orders:3,algos:1 pos=$P orders=0 algos=0"
    echo "RESULT keycheck DAT"; exit 0 ;;
  status) cat "$D/canary_state.json" 2>/dev/null; echo; echo "RESULT status DAT"; exit 0 ;;
  preflight) N=K0 ;;
  setup) N=SETUP ;;
  flatten) N=FLATTEN ;;
  cleanup) N=CLEANUP ;;
  step) case "$K" in K6_RESTART) N=K6;; K6B_RESTART) N=K6b;; K6B_OPEN) N=K6b_OPEN;; K7B) N=K7b;; *) N=$K;; esac ;;
  *) echo "RESULT $CMD TU_CHOI | lenh khong ho tro"; exit 2 ;;
esac
if [ "$K" = K6B_RESTART ] && [ -f "$D/c3live_book.json" ]; then echo "RESULT K6b TU_CHOI | K6b: so van con"; exit 2; fi
case "$K" in K1|K6_OPEN|K6B_OPEN) echo '{"version":1}' > "$D/c3live_book.json";; esac
V=DAT; RC=0
[ -f "FAKE_TRUOT_$N" ] && { V=TRUOT; RC=3; }
# [3d] K0 doi SETUP (CROSSED/20x) toi khi lenh setup chay; keepAlive dung lai (gia) neu REUSE=1 va da co K0 truoc
MSGX=""; KAX=""
if [ "$N" = K0 ] && [ -f FAKE_K0_NEEDSETUP ] && [ ! -f FAKE_SETUP_DONE ]; then
  V=TRUOT; RC=3; MSGX=" C00USDT CROSSED/20x (yeu cau CROSSED/1x — chay canary_step SETUP YES=1)"
fi
[ "$N" = SETUP ] && touch FAKE_SETUP_DONE
[ "$N" = FLATTEN ] && [ ! -f FAKE_NOT_FLAT_STICKY ] && rm -f FAKE_NOT_FLAT
if [ "$N" = K0 ] && [ "${CANARY_K0_REUSE_KEEPALIVE:-}" = 1 ]; then
  if grep -q '"K0"' "$D/canary_state.json" 2>/dev/null; then KAX=',"ws.keepAliveSkipped":"K0 luc X (gia) da DAT keepAliveOk=2; md5 jar trung","ws.keepAliveOk":2'
  else KAX=',"ws.keepAliveReuse":"khong dung lai duoc: chua co K0 truoc trong phien => chay du 65'"'"'","ws.keepAliveOk":2'; fi
fi
J="$D/canary_$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)_${CMD}${K:+_$K}.jsonl"
NOW=$(date +%s%3N)
echo "{\"ts\":$NOW,\"type\":\"CALL_W\",\"api\":\"newMarketOrder:BUY\",\"symbol\":\"C00USDT\",\"cid\":\"c3-C00USDT-$N-$RANDOM$RANDOM\",\"ok\":true,\"latMs\":42,\"w1m\":17,\"wOwn\":7}" >> "$J"
echo "{\"ts\":$NOW,\"type\":\"STEP_RESULT\",\"k\":\"$N\",\"verdict\":\"$V\"}" >> "$J"
python3 -I - "$D/canary_state.json" "$N" "$V" <<'PY'
import json, os, sys, time
f, n, v = sys.argv[1:4]
s = json.load(open(f)) if os.path.exists(f) else {"symMain": "C00USDT", "symAux": "C01USDT", "steps": {}}
LEG = {"legacy.callsOutside": 0, "legacy.canaryOutside": 0,
       "legacy.summary": "LEGACY vi the K0=44 cuoi=44 (doi=0 moi=0 mat=0); lenh K0=3 cuoi=3; algo K0=1 cuoi=1; symbol LEGACY doi=0 (gia); lenh canary ngoai pham vi=0"}
data = {"openLeg": {"streamLatMs": 120}, "ownWeight1mMax": 40}
if n == "CLEANUP": data.update(LEG)
s.setdefault("steps", {})[n] = {"result": v, "ms": int(time.time() * 1000), "fails": [] if v == "DAT" else ["gia"], "data": data}
json.dump(s, open(f, "w"))
PY
# [3b] moc test: doi v_t_m / restart bot / ha RAM ngay trong buoc (gia lap su co ngoai canary)
if [ -f FAKE_VTM_PATH ]; then
  VP=$(cat FAKE_VTM_PATH)
  [ -f "FAKE_VTM_TOUCH_$N" ] && echo "# doi boi test" >> "$VP/conf/env.sh"
  [ -f "FAKE_VTM_RESTART_$N" ] && (cd "$VP" && bin/daemon.sh stop; bin/daemon.sh start) > /dev/null 2>&1
fi
[ -f "FAKE_RAM_LOW_$N" ] && printf 'MemTotal: 8000000 kB\nMemAvailable: 500000 kB\n' > "$(cat FAKE_MEMINFO_PATH)"
[ -f "FAKE_HM_AFTER_$N" ] && cp "FAKE_HM_AFTER_$N" "$(cat FAKE_HM_PATH)"   # [3c] dong ho gia: het khung gio ngay sau buoc nay
MSG=""; [ -f "FAKE_MSG_$N" ] && MSG=" $(cat "FAKE_MSG_$N")"
echo "JOURNAL $J"
LGX=""; [ "$N" = CLEANUP ] && LGX=',"legacy.summary":"LEGACY vi the K0=44 cuoi=44 (gia); lenh canary ngoai pham vi=0"'
echo "DATA {\"symMain\":\"C00USDT\",\"symAux\":\"C01USDT\"$KAX$LGX}"
echo "RESULT $N $V$( [ $V = DAT ] || echo ' | gia')$MSG$MSGX"
exit $RC
FJ
mkdir -p "$W/canarylog"; echo ok > "$W/g1.ok"; echo ok > "$W/g2.ok"
cv() { env LOGDIR=$W/canarylog CANARY_JAR_MD5=$NEW JAVA_242="bash $W/fakejava.sh" CANARY_KEYS_FILE=$W/keys/c3live/keys.env \
  CANARY_KEYS_OWNER=$(id -un) POLL_S=1 GATE_FILES="$W/g1.ok $W/g2.ok" "$@"; }
calls() { awk '{print ($1=="step") ? $2 : $1}' $F/run/canary/fake_calls.log 2>/dev/null | tr '\n' ' ' | sed 's/ $//'; }
FK="TESTKEY$(date +%s%N | md5sum | cut -c1-32)abcdefghijklmnopqrstuv"; FS="TESTSEC$(date +%N%s | md5sum | cut -c1-32)ABCDEFGHIJKLMNOPQRSTUV"
echo "-- 14a keys_install"
OUT=$(printf '%s\n%s\n' "$FK" "$FS" | cv bash $CN/c3live_keys_install.sh 2>&1); RC=$?
chk "keys: khong YES => TU_CHOI, khong ghi" "[ $RC = 2 ] && [ ! -e $W/keys/c3live/keys.env ]"
OUT=$(printf '%s\n%s\n' "$FK" "$FS" | cv YES=1 bash $CN/c3live_keys_install.sh 2>&1); RC=$?; echo "$OUT" | grep -a 'GHI_XONG\|KET QUA' | head -3
chk "keys: YES=1 ghi 600 + thu muc 700 + 2 dong + keycheck DAT" "[ $RC = 0 ] && [ \$(stat -c %a $W/keys/c3live/keys.env) = 600 ] && [ \$(stat -c %a $W/keys/c3live) = 700 ] && [ \$(grep -c '^C3_LIVE_API_' $W/keys/c3live/keys.env) = 2 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
chk "keys: JVM keycheck nhan dung LIVE_C3_KEYS_FILE" "grep -q 'keycheck  TMB= INJ= KF=$W/keys/c3live/keys.env' $F/run/canary/fake_calls.log"
OUT2=$(printf '%s\n%s\n' "$FK" "$FS" | cv YES=1 bash $CN/c3live_keys_install.sh 2>&1); RC=$?
chk "keys: da co file, khong REPLACE => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT2\" | grep -q 'REPLACE=1'"
OUT2=$(printf '%s\n%s\n' "$FK" "$FS" | cv YES=1 REPLACE=1 bash $CN/c3live_keys_install.sh 2>&1); RC=$?
chk "keys: REPLACE=1 => backup .bak_ (600)" "[ $RC = 0 ] && ls $W/keys/c3live/keys.env.bak_* >/dev/null 2>&1 && [ \$(stat -c %a \$(ls $W/keys/c3live/keys.env.bak_* | head -1)) = 600 ]"
OUT2=$(printf 'abc\nxyz\n' | cv YES=1 REPLACE=1 bash $CN/c3live_keys_install.sh 2>&1); RC=$?
chk "keys: key sai dinh dang => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT2\" | grep -q 'sai dinh dang'"
chk "keys: KHONG lo key/secret ra output + log Oracle" "! echo \"\$OUT\$OUT2\" | grep -qF \"$FK\" && ! echo \"\$OUT\$OUT2\" | grep -qF \"$FS\" && ! grep -rqF \"$FK\" $W/canarylog && ! grep -rqF \"$FS\" $W/canarylog"
echo "-- 14b preflight (dieu kien vao §2)"
date +%s > $F/run/.v12_start_epoch
OUT=$(cv FORCE_TIME=1 bash $CN/canary_preflight.sh 2>&1); RC=$?
chk "preflight: thieu CANARY_EXPECT_TMB => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'CANARY_EXPECT_TMB'"
OUT=$(cv FORCE_TIME=1 CANARY_EXPECT_TMB=10000 CANARY_JAR_MD5=00000000000000000000000000000000 bash $CN/canary_preflight.sh 2>&1); RC=$?
chk "preflight: md5 jar khac pin => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'md5 jar tren 242 khac pin'"
OUT=$(cv FORCE_TIME=1 CANARY_EXPECT_TMB=10000 bash $CN/canary_preflight.sh 2>&1); RC=$?
chk "preflight: dry < 5 ngay => TU_CHOI (MO-1)" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'dry moi chay 0 ngay'"
echo $(( $(date +%s) - 6 * 86400 )) > $F/run/.v12_start_epoch
OUT=$(cv FORCE_TIME=1 CANARY_EXPECT_TMB=10000 GATE_FILES="$W/g1.ok $W/khong_co.ok" bash $CN/canary_preflight.sh 2>&1); RC=$?
chk "preflight: thieu file gate MASTER => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'thieu file gate MASTER'"
echo "$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000') WARN [main] x: [KILLSW] LATCH action=FLATTEN code=C6" >> $F/logs/full.log
OUT=$(cv FORCE_TIME=1 CANARY_EXPECT_TMB=10000 bash $CN/canary_preflight.sh 2>&1); RC=$?
sed -i '/\[KILLSW\] LATCH/d' $F/logs/full.log
chk "preflight: log dry co [KILLSW] LATCH => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'LATCH / \[C3-LIVE-ORDER\]'"
HH=$(TZ=Asia/Ho_Chi_Minh date +%-H); MM=$(TZ=Asia/Ho_Chi_Minh date +%-M)
TOK=1; { [ "$MM" -ge 10 ] && [ "$MM" -le 44 ]; } || TOK=0; case "$HH" in 7|19) TOK=0;; esac
if [ "$HH" -eq 1 ] || [ "$HH" -eq 13 ]; then [ "$MM" -gt 20 ] || TOK=0; fi
if [ "$TOK" = 0 ] && [ "$MM" -ne 9 ] && [ "$MM" -ne 20 ] && [ "$MM" -ne 59 ]; then   # tranh sat bien phut
  OUT=$(cv CANARY_EXPECT_TMB=10000 bash $CN/canary_preflight.sh 2>&1); RC=$?
  chk "preflight: ngoai khung gio => TU_CHOI (time_ok)" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khong hop le'"
fi
rm -f $F/run/canary/fake_calls.log
OUT=$(cv FORCE_TIME=1 CANARY_EXPECT_TMB=10000 bash $CN/canary_preflight.sh 2>&1); RC=$?
chk "preflight: khong YES => chi kiem, KHONG chay JVM" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'CHI KIEM' && [ ! -s $F/run/canary/fake_calls.log ]"
OUT=$(cv FORCE_TIME=1 CANARY_EXPECT_TMB=10000 YES=1 bash $CN/canary_preflight.sh 2>&1); RC=$?; echo "$OUT" | grep -a 'KET QUA\|symMain' | head -3
chk "preflight: YES=1 => K0 chay (tmb truyen vao JVM), DAT, in symbol" "[ $RC = 0 ] && grep -q '^preflight  TMB=10000 ' $F/run/canary/fake_calls.log && echo \"\$OUT\" | grep -q 'KET QUA: DAT' && echo \"\$OUT\" | grep -q 'symMain = \"C00USDT\"'"
chk "preflight: logback-canary.xml dat vao run/canary" "cmp -s $CN/logback-canary.xml $F/run/canary/logback-canary.xml"
echo "-- 14c canary.sh (chuoi K1..K8)"
OUT=$(cv FORCE_TIME=1 bash $CN/canary.sh 2>&1); RC=$?
chk "canary: khong YES => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'can YES=1'"
rm -f $F/run/canary/fake_calls.log
OUT=$(cv FORCE_TIME=1 YES=1 bash $CN/canary.sh 2>&1); RC=$?; echo "$OUT" | grep -a 'KET QUA' | tail -1
chk "canary: chuoi DAT, dung thu tu (K6 OPEN+RESTART, K6b OPEN+doi ten so+RESTART+flatten)" "[ $RC = 0 ] && [ \"\$(calls)\" = 'K1 K2 K3 K4 K5 K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART flatten K7 K7B K8' ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
chk "canary: K6b doi ten so (.k6b_TS)" "ls $F/run/canary/c3live_book.json.k6b_* >/dev/null 2>&1"
chk "canary: MO-5 mac dinh TAT (K1 INJ=0)" "grep -q '^step K1 TMB= INJ=0 ' $F/run/canary/fake_calls.log"
echo "-- 14d canary_report (bang chung + §5, khong key)"
OUT=$(cv bash $CN/canary_report.sh 2>&1); RC=$?; echo "$OUT" | grep -a 'KET QUA' | tail -2
RPT=$(echo "$OUT" | sed -n 's/.*Bao cao: //p' | tail -1)
chk "report: tong DAT, file txt co" "[ $RC = 0 ] && [ -s \"$RPT\" ] && grep -q 'KET QUA TONG: DAT' \"$RPT\" && grep -q 'K6b  DAT' \"$RPT\""
chk "report: 0 lenh trung cid + weight do duoc" "grep -q ' 1\. 0 lenh trung cid.*DAT' \"$RPT\" && grep -q 'X-MBX-USED-WEIGHT-1M (IP chung LEGACY)=17' \"$RPT\" && grep -q '5. weight canary tu goi < 600.*DAT.*canary tu goi max/phut (uoc tinh W_\\*, moi JVM)=40' \"$RPT\""
chk "report: khong chua key/secret" "! grep -qF \"$FK\" \"$RPT\" && ! grep -qF \"$FS\" \"$RPT\" && ! grep -rqF \"$FK\" $W/canarylog && ! grep -rqF \"$FS\" $W/canarylog"
echo "{\"type\":\"CALL_R\",\"msg\":\"lo $FK\"}" > $F/run/canary/canary_99999999_000000_leak.jsonl
OUT=$(cv bash $CN/canary_report.sh 2>&1); RC=$?
RPT=$(echo "$OUT" | sed -n 's/.*Bao cao: //p' | tail -1)
chk "report: file 242 co key => TRUOT tieu chi 6, KHONG keo file do, report khong co key" "[ $RC = 3 ] && grep -q ' 6\. 0 bi mat trong log.*TRUOT' \"$RPT\" && ! grep -rqF \"$FK\" $W/canarylog && ! ls $W/canarylog/report_*/files/canary_99999999_000000_leak.jsonl >/dev/null 2>&1"
rm -f $F/run/canary/canary_99999999_000000_leak.jsonl
echo "-- 14e canary_cleanup (doi ten run/canary)"
OUT=$(cv bash $CN/canary_cleanup.sh 2>&1); RC=$?
chk "cleanup: khong YES => TU_CHOI" "[ $RC = 2 ] && [ -d $F/run/canary ]"
OUT=$(cv YES=1 bash $CN/canary_cleanup.sh 2>&1); RC=$?
DONE=$(ls -d $F/run/canary_done_* 2>/dev/null | head -1)
chk "cleanup: YES=1 => DAT, run/canary -> run/canary_done_TS" "[ $RC = 0 ] && [ ! -e $F/run/canary ] && [ -f \"$DONE/canary_state.json\" ]"
OUT=$(cv bash $CN/canary_report.sh "run/$(basename "$DONE")" 2>&1); RC=$?
chk "report tren thu muc da cleanup: DAT" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
echo "-- 14f TRUOT dung chuoi + flatten"
touch $F/FAKE_TRUOT_K3
OUT=$(cv FORCE_TIME=1 YES=1 bash $CN/canary.sh 2>&1); RC=$?; rm -f $F/FAKE_TRUOT_K3
chk "canary: K3 TRUOT => dung, flatten, KHONG chay K4+, exit 3" "[ $RC = 3 ] && [ \"\$(calls)\" = 'K1 K2 K3 flatten' ] && echo \"\$OUT\" | grep -q 'KET QUA: TRUOT (buoc K3)'"
echo "-- 14g canary_step / lock / JVM canary khac / adapter live / flatten"
OUT=$(cv FORCE_TIME=1 YES=1 bash $CN/canary_step.sh 'K9;rm' 2>&1); RC=$?
chk "step: buoc la => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'thieu/sai buoc'"
rm -f $F/run/canary/fake_calls.log
OUT=$(cv FORCE_TIME=1 YES=1 CANARY_INJECT_TIMEOUT=1 bash $CN/canary_step.sh K1 2>&1); RC=$?
chk "step K1 + CANARY_INJECT_TIMEOUT=1 => JVM nhan INJ=1 (MO-5)" "[ $RC = 0 ] && grep -q '^step K1 TMB= INJ=1 ' $F/run/canary/fake_calls.log"
OUT=$(cv FORCE_TIME=1 YES=1 CANARY_INJECT_TIMEOUT=2 bash $CN/canary_step.sh K1 2>&1); RC=$?
chk "step: CANARY_INJECT_TIMEOUT khac 0/1 => TU_CHOI" "[ $RC = 2 ]"
touch $F/FAKE_CANARY_LOCK
OUT=$(cv FORCE_TIME=1 YES=1 bash $CN/canary_step.sh K2 2>&1); RC=$?; rm -f $F/FAKE_CANARY_LOCK
chk "step: lock tai khoan con bi giu => TU_CHOI (khong DAT)" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'lock tai khoan con dang bi giu' && echo \"\$OUT\" | grep -q 'KET QUA: TU_CHOI'"
( exec -a "java -cp x.jar com.binance.chuyennd.c3live.canary.C3LiveCanary step K4" sleep 20 ) &
SP=$!; sleep 0.5
OUT=$(cv FORCE_TIME=1 YES=1 bash $CN/canary_step.sh K2 2>&1); RC=$?; kill $SP 2>/dev/null; wait $SP 2>/dev/null
chk "step: co JVM canary khac dang chay => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'JVM canary khac'"
sed -i 's/^export LIVE_ADAPTER=dry$/export LIVE_ADAPTER=live/' $F/conf/env.sh; (cd $F && bin/daemon.sh stop; bin/daemon.sh start)
OUT=$(cv YES=1 bash $CN/canary_flatten.sh 2>&1); RC=$?
sed -i 's/^export LIVE_ADAPTER=live$/export LIVE_ADAPTER=dry/' $F/conf/env.sh; (cd $F && bin/daemon.sh stop; bin/daemon.sh start)
chk "flatten: bot o LIVE_ADAPTER=live => TU_CHOI (runtime chinh giu tai khoan)" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'LIVE_ADAPTER=live'"
OUT=$(cv YES=1 bash $CN/canary_flatten.sh 2>&1); RC=$?
chk "flatten: YES=1 => DAT + in trang thai" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT' && echo \"\$OUT\" | grep -q 'symMain'"
OUT=$(cv FORCE_TIME=1 YES=1 bash $CN/canary_step.sh SETUP 2>&1); RC=$?
chk "step SETUP => lenh setup, khong flatten" "[ $RC = 0 ] && [ \"\$(calls | awk '{print \$NF}')\" = setup ]"
chk "khong file nao trong log Oracle chua key/secret" "! grep -rqF \"$FK\" $W/canarylog && ! grep -rqF \"$FS\" $W/canarylog"

echo "-- 14h [3c MAJ-C1] canary.sh: khung gio dong GIUA phien (sau K1) => KHONG cho, chay tiep; ngoai gio o DAU phien => tu choi"
echo "10 15" > $W/hm; echo "$W/hm" > $F/FAKE_HM_PATH; echo "10 50" > $F/FAKE_HM_AFTER_K1
rm -f $F/run/canary/fake_calls.log
T0=$(date +%s)
OUT=$(cv YES=1 CL_FAKE_HM=$W/hm bash $CN/canary.sh 2>&1); RC=$?; DT=$(( $(date +%s) - T0 ))
chk "canary.sh: gio dong giua phien => khong cho, chuoi day du, ${DT}s" "[ $RC = 0 ] && [ \"\$(calls)\" = 'K1 K2 K3 K4 K5 K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART flatten K7 K7B K8' ] && ! echo \"\$OUT\" | grep -q 'ngoai khung gio' && [ $DT -lt 200 ]"
rm -f $F/run/canary/fake_calls.log
OUT=$(cv YES=1 CL_FAKE_HM=$W/hm bash $CN/canary.sh 2>&1); RC=$?
chk "canary.sh: ngoai khung gio o DAU phien => TU_CHOI, khong JVM" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khong hop le' && [ ! -s $F/run/canary/fake_calls.log ]"
rm -f $F/FAKE_HM_PATH $F/FAKE_HM_AFTER_K1 $W/hm

echo "== 15. [V12 3b] CANARY-EARLY (§ADD-1): thu muc rieng c3canary, v_t_m shadow CHI DOC + kiem khong doi moi buoc"
C3=$W/c3canary
cat > $F/conf/env.sh <<'EOF'
export LIVE_PROFILE=c3_shadow
export SHADOW_NO_PUSH=true
export LIVE_TS_MKT_EXT=1
export SYMBOL_MAPPER_DUP_POLICY=WARN
export LIVE_FEAT_DUMP=200000
EOF
(cd $F && bin/daemon.sh stop; bin/daemon.sh start)
printf 'MemTotal: 8000000 kB\nMemAvailable: 2500000 kB\n' > $W/meminfo
echo "XRPUSDT" > $F/run/legacy_symbols.csv
rm -rf $F/run/canary
ce() { cv CANARY_HOME=$C3 VTM_DIR=$F MEMINFO_FILE=$W/meminfo CANARY_JAR=$W/new.jar CL_RETRY_S=1 FORCE_TIME=1 "$@"; }
callsC() { awk '{print ($1=="step") ? $2 : $1}' "$1" 2>/dev/null | tr '\n' ' ' | sed 's/ $//'; }
vmd5() { cat $F/target/binance-java-sdk-1.2.4.jar $F/conf/env.sh $F/bin/start.sh | md5sum | cut -c1-32; }
lastres() { ls -t $W/canarylog/canary_early_result_*.txt 2>/dev/null | head -1; }
newsession() {   # phien moi: install lai (CANARY_RESET=1 neu phien cu co giao dich)
  OUTI=$(ce YES=1 CANARY_RESET=1 CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RCI=$?
  rm -f $C3/FAKE_*; echo "$F" > $C3/FAKE_VTM_PATH; echo "$W/meminfo" > $C3/FAKE_MEMINFO_PATH
}
V0=$(vmd5); P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
echo "-- 15a install: dieu kien vao §ADD-1"
OUT=$(ce bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: thieu CANARY_EXPECT_TMB => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q CANARY_EXPECT_TMB"
OUT=$(ce GATE_FILES=$W/khong_co.ok CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: thieu gate CODE => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'thieu file gate MASTER'"
OUT=$(ce CANARY_JAR_MD5=00000000000000000000000000000000 CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: jar Oracle khac pin => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khac pin'"
sed -i 's/^export LIVE_PROFILE=c3_shadow$/export LIVE_PROFILE=c3_live/' $F/conf/env.sh; (cd $F && bin/daemon.sh stop; bin/daemon.sh start)
OUT=$(ce CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
sed -i 's/^export LIVE_PROFILE=c3_live$/export LIVE_PROFILE=c3_shadow/' $F/conf/env.sh
chk "early install: v_t_m khong c3_shadow => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'phai c3_shadow'"
sed -i '/^export SHADOW_NO_PUSH=true$/d' $F/conf/env.sh; (cd $F && bin/daemon.sh stop; bin/daemon.sh start)
OUT=$(ce CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
sed -i '1a export SHADOW_NO_PUSH=true' $F/conf/env.sh; (cd $F && bin/daemon.sh stop; bin/daemon.sh start)
chk "early install: v_t_m thieu SHADOW_NO_PUSH=true => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'SHADOW_NO_PUSH'"
printf 'MemTotal: 8000000 kB\nMemAvailable: 900000 kB\n' > $W/meminfo
OUT=$(ce CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
printf 'MemTotal: 8000000 kB\nMemAvailable: 2500000 kB\n' > $W/meminfo
chk "early install: MemAvailable < 1 GB => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'RAM 242 khong du'"
OUT=$(ce CANARY_EXPECT_TMB=10000 CANARY_HOME=$F/c3canary bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: CANARY_HOME trong v_t_m => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'nam trong v_t_m'"
V0=$(vmd5); P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
OUT=$(ce CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: khong YES => chi kiem, KHONG ghi 242" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'CHI KIEM' && [ ! -e $C3 ]"
echo "-- 15b install YES=1 (copy jar rieng + K0 chi doc); env goi co LIVE_PROFILE/LIVE_TS_MKT_EXT/TRADING_PROFILE => JVM van env sach"
OUT=$(ce YES=1 CANARY_EXPECT_TMB=10000 LIVE_PROFILE=c3_shadow LIVE_TS_MKT_EXT=1 TRADING_PROFILE=/khong/co bash $CN/canary_early_install.sh 2>&1); RC=$?
echo "$OUT" | grep -a 'KET QUA\|LEGACY\|v_t_m khong doi' | head -6
chk "early install: DAT, jar rieng md5 = pin, thu muc 700" "[ $RC = 0 ] && [ \"\$(md5sum < $C3/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEW ] && [ \$(stat -c %a $C3) = 700 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
chk "early install: JVM chay trong c3canary, env sach (ENVX=0), keycheck + K0" "[ \"\$(callsC $C3/run/canary/fake_calls.log)\" = 'keycheck preflight' ] && grep -q '^preflight  TMB=10000 .*CWD=$C3 ENVX=0' $C3/run/canary/fake_calls.log && ! grep -q 'ENVX=[1-9]' $C3/run/canary/fake_calls.log"
chk "early install: LEGACY sao tu v_t_m (chi doc), logback rieng" "cmp -s $F/run/legacy_symbols.csv $C3/run/legacy_symbols.csv && cmp -s $CN/logback-canary.xml $C3/run/canary/logback-canary.xml"
chk "early install: v_t_m KHONG doi (md5 jar/env/start, PID), khong co run/canary trong v_t_m" "[ \"\$(vmd5)\" = $V0 ] && [ \"\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)\" = $P0 ] && [ ! -e $F/run/canary ] && echo \"\$OUT\" | grep -q 'v_t_m khong doi (sau K0)'"
echo "-- 15c run: hoi YES 1 lan; chuoi day du; report + cleanup + 1 file ket qua"
OUT=$(printf 'no\n' | ce bash $CN/canary_early_run.sh 2>&1); RC=$?
chk "early run: khong go YES => TU_CHOI, khong buoc nao" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khong go YES' && [ \"\$(callsC $C3/run/canary/fake_calls.log)\" = 'keycheck preflight' ]"
echo "$F" > $C3/FAKE_VTM_PATH; echo "$W/meminfo" > $C3/FAKE_MEMINFO_PATH
OUT=$(printf 'YES\n' | ce LIVE_PROFILE=c3_shadow bash $CN/canary_early_run.sh 2>&1); RC=$?; echo "$OUT" | grep -a 'KET QUA PHIEN\|File ket qua' | tail -2
DONE3=$(ls -d $C3/run/canary_done_* 2>/dev/null | head -1); RES=$(lastres)
chk "early run: DAT, dung thu tu, report + cleanup, doi ten canary_done" "[ $RC = 0 ] && [ \"\$(callsC $DONE3/fake_calls.log)\" = 'keycheck preflight status K1 K2 K3 K4 K5 K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART flatten K7 K7B K8 cleanup' ] && [ ! -e $C3/run/canary ]"
chk "early run: file ket qua DAT + report mode=early (tieu chi 4 KHONG_AP) + v_t_m tung buoc" "grep -q '^KET QUA PHIEN: DAT' \"$RES\" && grep -q 'mode=early' \"$RES\" && grep -q 'KET QUA TONG: DAT' \"$RES\" && grep -q 'KHONG_AP' \"$RES\" && [ \$(grep -c 'khong doi (pid' \"$RES\") -ge 20 ]"
chk "early run: v_t_m KHONG doi sau ca phien; khong key trong file ket qua/log" "[ \"\$(vmd5)\" = $V0 ] && [ \"\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)\" = $P0 ] && [ ! -e $F/run/canary ] && ! grep -qF \"$FK\" \"$RES\" && ! grep -rqF \"$FS\" $W/canarylog && ! grep -q 'ENVX=[1-9]' $DONE3/fake_calls.log"
echo "-- 15d v_t_m bi doi giua phien (env.sh doi trong K3) => DUNG ngay + flatten, khong K4"
newsession; touch $C3/FAKE_VTM_TOUCH_K3
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_run.sh 2>&1); RC=$?; RES=$(lastres)
sed -i '/doi boi test/d' $F/conf/env.sh
CL=$(callsC $C3/run/canary/fake_calls.log)
chk "early run: env v_t_m doi sau K3 => TRUOT, flatten, KHONG K4, giu run/canary" "[ $RCI = 0 ] && [ $RC != 0 ] && [ \"\${CL##*K2 }\" = 'K3 flatten cleanup' ] && grep -q 'v_t_m bi doi sau K3' \"$RES\" && grep -q '^KET QUA PHIEN: TRUOT' \"$RES\" && [ -d $C3/run/canary ]"
OUT=$(ce YES=1 CANARY_EXPECT_TMB=10000 bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: phien cu co giao dich, khong CANARY_RESET => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'CANARY_RESET=1'"
echo "-- 15e PID bot v_t_m doi (restart trong K2) => DUNG + flatten"
newsession; touch $C3/FAKE_VTM_RESTART_K2
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_run.sh 2>&1); RC=$?; RES=$(lastres)
CL=$(callsC $C3/run/canary/fake_calls.log)
chk "early run: PID v_t_m doi sau K2 => TRUOT, flatten, KHONG K3; CANARY_RESET giu phien cu canary_prev" "[ $RCI = 0 ] && [ $RC != 0 ] && [ \"\${CL##*K1 }\" = 'K2 flatten cleanup' ] && grep -q 'v_t_m bi doi sau K2.*BOT=' \"$RES\" && ls -d $C3/run/canary_prev_* >/dev/null 2>&1"
P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
echo "-- 15f RAM tut duoi 768 MB giua phien => DUNG + flatten"
newsession; touch $C3/FAKE_RAM_LOW_K2
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_run.sh 2>&1); RC=$?; RES=$(lastres)
printf 'MemTotal: 8000000 kB\nMemAvailable: 2500000 kB\n' > $W/meminfo
CL=$(callsC $C3/run/canary/fake_calls.log)
chk "early run: MemAvailable < 768 MB truoc K3 => TRUOT, flatten, KHONG K3" "[ $RCI = 0 ] && [ $RC != 0 ] && [ \"\${CL##*K1 }\" = 'K2 flatten cleanup' ] && grep -q 'MemAvailable 488 MB < 768' \"$RES\""
echo "-- 15g K1 -2019 (USDT = 0) => TRUOT + ghi phuong an B"
newsession; touch $C3/FAKE_TRUOT_K1; echo "-2019 Margin is insufficient." > $C3/FAKE_MSG_K1
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_run.sh 2>&1); RC=$?; RES=$(lastres)
chk "early run: K1 -2019 => TRUOT + PHUONG AN B (nap 50 USDT)" "[ $RCI = 0 ] && [ $RC != 0 ] && grep -q 'PHUONG AN B' \"$RES\" && [ \"\$(callsC $C3/run/canary/fake_calls.log | awk '{print \$(NF-2), \$(NF-1), \$NF}')\" = 'K1 flatten cleanup' ]"
echo "-- 15h dung khan cap: canary_flatten (early) dat file STOP; phien moi bi chan toi khi xoa STOP"
OUT=$(ce CANARY_MODE=early YES=1 bash $CN/canary_flatten.sh 2>&1); RC=$?
chk "early flatten: DAT + tao CANARY_STOP" "[ $RC = 0 ] && [ -f $W/canarylog/CANARY_STOP ] && grep -q '^flatten .*CWD=$C3' $C3/run/canary/fake_calls.log"
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_run.sh 2>&1); RC=$?
chk "early run: co CANARY_STOP => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'CANARY_STOP'"
rm -f $W/canarylog/CANARY_STOP
OUT=$(ce CANARY_MODE=early YES=1 bash $CN/canary.sh 2>&1); RC=$?
chk "canary.sh: CANARY_MODE=early => TU_CHOI (dung canary_early_run.sh)" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'canary_early_run'"
echo "== 16. [V12 3c] MAJ-C1 khung gio / MIN-C2 lo cong don / MIN-C3 kill JVM treo / MIN-C4 canary_early_flatten.sh"
echo "-- 16a early run: khung gio dong GIUA phien (sau K1) => KHONG cho, chuoi day du"
newsession; echo "10 15" > $W/hm; echo "$W/hm" > $C3/FAKE_HM_PATH; echo "10 50" > $C3/FAKE_HM_AFTER_K1
T0=$(date +%s)
OUT=$(printf 'YES\n' | ce FORCE_TIME=0 CL_FAKE_HM=$W/hm bash $CN/canary_early_run.sh 2>&1); RC=$?; DT=$(( $(date +%s) - T0 )); RES=$(lastres)
DONE4=$(ls -td $C3/run/canary_done_* 2>/dev/null | head -1)
chk "early run: gio dong sau K1 => khong cho, DAT, ${DT}s" "[ $RCI = 0 ] && [ $RC = 0 ] && grep -q '^KET QUA PHIEN: DAT' \"$RES\" && [ \"\$(callsC $DONE4/fake_calls.log | awk '{print \$NF}')\" = cleanup ] && ! echo \"\$OUT\" | grep -q 'ngoai khung gio' && [ $DT -lt 200 ]"
chk "early run: file ket qua ghi lo cong don + so lan CANARY_RESET" "grep -q 'lo cong don MOI phien canary-early: 0.0000 USDT (tran 4' \"$RES\" && grep -q 'so lan CANARY_RESET: [1-9]' \"$RES\""
OUT=$(printf 'YES\n' | ce FORCE_TIME=0 CL_FAKE_HM=$W/hm bash $CN/canary_early_run.sh 2>&1); RC=$?
chk "early run: ngoai khung gio o DAU phien => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khong hop le'"
rm -f $W/hm
echo "-- 16b lo cong don moi phien > 4 USDT => tu choi phien moi; MASTER doi tran bang file gate"
mkdir -p $C3/run/canary_prev_29990101_000000
echo '{"symMain":"C00USDT","symAux":"C01USDT","cumFeeStable":0.5,"cumRealized":-4.0,"cumFunding":0.0,"steps":{}}' > $C3/run/canary_prev_29990101_000000/canary_state.json
OUT=$(ce YES=1 CANARY_RESET=1 CANARY_EXPECT_TMB=10000 CUM_CAP_FILE=$W/cumcap.ok bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: lo cong don 4.5 > 4 USDT => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'tong lo cong don 4.5000 USDT > tran 4'"
OUT=$(printf 'YES\n' | ce CUM_CAP_FILE=$W/cumcap.ok bash $CN/canary_early_run.sh 2>&1); RC=$?
chk "early run: lo cong don > 4 USDT => TU_CHOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'tong lo cong don'"
echo 10 > $W/cumcap.ok
OUT=$(ce YES=1 CANARY_RESET=1 CANARY_EXPECT_TMB=10000 CUM_CAP_FILE=$W/cumcap.ok bash $CN/canary_early_install.sh 2>&1); RC=$?
chk "early install: MASTER dat tran 10 (file gate) => chay duoc" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'tran lo cong don do MASTER dat'"
rm -rf $C3/run/canary_prev_29990101_000000 $W/cumcap.ok
echo "-- 16c MIN-C3: canary_early_flatten.sh kill JVM canary TREO (chi cwd c3canary, giu lock >= 10', heartbeat cu >= 3')"
cat > $W/hang.sh <<'HG'
#!/usr/bin/env bash
# gia lap JVM canary TREO: $1 = thu muc canary; ghi "lock" (since 20' truoc) + heartbeat (cu 10' hoac moi neu HB_FRESH=1) voi pid nay
D=$1; mkdir -p "$D/run/canary"
echo "c3live-canary step pid=$$ since=$(( ($(date +%s) - 1200) * 1000 ))" > "$D/run/c3live_account.lock"
if [ -n "${HB_FRESH:-}" ]; then echo "pid=$$ ms=$(date +%s%3N) cmd=step" > "$D/run/canary/canary_jvm.hb"
else echo "pid=$$ ms=$(( ($(date +%s) - 600) * 1000 )) cmd=step" > "$D/run/canary/canary_jvm.hb"; fi
sleep 120
HG
hangpid() { pgrep -f "hang.sh $C3 com.binance.chuyennd.c3live.canary.C3LiveCanary" | head -1; }
(cd $C3 && bash $W/hang.sh $C3 com.binance.chuyennd.c3live.canary.C3LiveCanary step K2) > /dev/null 2>&1 &
sleep 1; HP=$(hangpid)
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_flatten.sh 2>&1); RC=$?
chk "early flatten: JVM treo (cwd c3canary, lock 20', hb cu 10') => KILL roi flatten DAT" "[ -n \"$HP\" ] && [ $RC = 0 ] && echo \"\$OUT\" | grep -q \"KILLED $HP\" && ! kill -0 $HP 2>/dev/null && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
rm -f $W/canarylog/CANARY_STOP
(cd $C3 && HB_FRESH=1 bash $W/hang.sh $C3 com.binance.chuyennd.c3live.canary.C3LiveCanary step K2) > /dev/null 2>&1 &
sleep 1; HP=$(hangpid)
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_flatten.sh 2>&1); RC=$?
chk "early flatten: JVM canary heartbeat MOI => KHONG kill, flatten TU_CHOI (phien tu dong)" "[ -n \"$HP\" ] && [ $RC = 2 ] && kill -0 $HP 2>/dev/null && echo \"\$OUT\" | grep -q \"GIU $HP dang song\""
kill $HP 2>/dev/null; rm -f $W/canarylog/CANARY_STOP
(cd $F && bash $W/hang.sh $C3 com.binance.chuyennd.c3live.canary.C3LiveCanary step K2) > /dev/null 2>&1 &
sleep 1; HP=$(hangpid)
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_flatten.sh 2>&1); RC=$?
chk "early flatten: process cwd = v_t_m => KHONG BAO GIO kill" "[ -n \"$HP\" ] && kill -0 $HP 2>/dev/null && echo \"\$OUT\" | grep -q \"GIU $HP cwd=\""
kill $HP 2>/dev/null; rm -f $W/canarylog/CANARY_STOP
OUT=$(printf 'no\n' | ce bash $CN/canary_early_flatten.sh 2>&1); RC=$?
chk "canary_early_flatten.sh: khong go YES => khong lam gi" "[ $RC = 2 ] && [ ! -e $W/canarylog/CANARY_STOP ]"
OUT=$(printf 'YES\n' | ce bash $CN/canary_early_flatten.sh 2>&1); RC=$?
chk "canary_early_flatten.sh: 1 lenh, tu dat CANARY_MODE=early (flatten trong c3canary) + tao STOP" "[ $RC = 0 ] && grep -q '^flatten .*CWD=$C3' $C3/run/canary/fake_calls.log && [ -f $W/canarylog/CANARY_STOP ]"
rm -f $W/canarylog/CANARY_STOP
chk "v_t_m KHONG doi qua toan bo muc 15-16 (tru thao tac cua chinh test), khong run/canary trong v_t_m" "[ \"\$(vmd5)\" = $V0 ] && [ ! -e $F/run/canary ]"

echo "== 17. [V12 3d] canary_early_all.sh MOT lenh: cho khung gio CHI khi phang -> SETUP -> K0 (tmb doc duoc, dung lai keepAlive) -> run -> Telegram"
TG=$W/tg_sink.txt
ca() { ce FORCE_TIME=0 CANARY_TG_SINK=$TG CL_FAKE_HM=$W/hm CL_WAIT_POLL_S=1 CL_FLAT_RECHECK_S=2 "$@"; }
fresh() { rm -rf $C3/run/canary; rm -f $C3/FAKE_* $TG; echo "$F" > $C3/FAKE_VTM_PATH; echo "$W/meminfo" > $C3/FAKE_MEMINFO_PATH; echo "10 15" > $W/hm; }
callsN() { awk '$1 != "keycheck" {print ($1=="step") ? $2 : $1}' "$1" 2>/dev/null | tr '\n' ' ' | sed 's/ $//'; }
lastsum() { ls -t $W/canarylog/canary_early_all_*.txt 2>/dev/null | head -1; }
echo "-- 17a khong go YES => khong chay gi"
fresh
OUT=$(printf 'no\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: khong go YES => TU_CHOI, khong JVM, khong Telegram" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khong go YES' && [ ! -e $C3/run/canary/fake_calls.log ] && [ ! -e $TG ]"
echo "-- 17b duong chuan: ngoai gio luc dau (phang => cho), tmb 10971.82, K0 lan 1 can SETUP -> SETUP -> K0 lan 2 dung lai keepAlive -> run DAT"
fresh; echo 10971.82 > $C3/FAKE_TMB; touch $C3/FAKE_K0_NEEDSETUP; echo "10 50" > $W/hm
( for i in $(seq 1 120); do grep -q '^keycheck' $C3/run/canary/fake_calls.log 2>/dev/null && break; sleep 0.5; done; sleep 5; echo "10 15" > $W/hm ) &
FLP=$!
T0=$(date +%s)
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?; DT=$(( $(date +%s) - T0 ))
wait $FLP 2>/dev/null
DONE5=$(ls -td $C3/run/canary_done_* 2>/dev/null | head -1); RES=$(lastres); SUM=$(lastsum)
echo "$OUT" | grep -a 'KET QUA MOT LENH\|CANARY_EXPECT_TMB=\|K0 keepAlive' | head -5
chk "all: DAT rc 0 (${DT}s), thu tu: status preflight setup preflight status K1..K8 cleanup" "[ $RC = 0 ] && [ \"\$(callsN $DONE5/fake_calls.log)\" = 'status preflight setup preflight status K1 K2 K3 K4 K5 K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART flatten K7 K7B K8 cleanup' ]"
chk "all: ngoai gio luc dau, tai khoan phang => CHO roi vao khung gio" "echo \"\$OUT\" | grep -q 'ngoai khung gio — CHO' && echo \"\$OUT\" | grep -q 'vao khung gio (SETUP/K0) sau' && echo \"\$OUT\" | grep -q 'pham vi canary phang (vao cho SETUP/K0: pos=0 orders=0 algos=0)'"
chk "all: ca 2 K0 voi CANARY_EXPECT_TMB = tmb doc duoc 10971.82 + CANARY_K0_REUSE_KEEPALIVE=1, log ro gia tri" "[ \$(grep -c '^preflight  TMB=10971.82 .*REUSE=1\$' $DONE5/fake_calls.log) = 2 ] && echo \"\$OUT\" | grep -q 'CANARY_EXPECT_TMB=10971.82 (chi GHI' && grep -q 'CANARY_EXPECT_TMB=10971.82' \"$SUM\""
chk "all: K0 lan 2 BO cho keepAlive + ly do; K0 lan 1 ghi vi sao chay du" "echo \"\$OUT\" | grep -q \"K0 keepAlive: BO cho keepAlive 65' — ly do: K0 luc X\" && echo \"\$OUT\" | grep -q 'khong dung lai duoc: chua co K0 truoc' && grep -q 'BO cho keepAlive' \"$SUM\""
chk "all: K0 TRUOT chi vi SETUP => SETUP roi K0 lai (dung 1 lan)" "echo \"\$OUT\" | grep -q 'K0 TRUOT chi vi marginType/leverage' && [ \$(grep -c '^setup ' $DONE5/fake_calls.log) = 1 ]"
chk "all: phien K1..K8 chay voi CANARY_INJECT_TIMEOUT=1 (K1 INJ=1)" "grep -q '^step K1 TMB= INJ=1 ' $DONE5/fake_calls.log"
chk "all: Telegram DAT + 1 dong + duong dan file ket qua phien (DAT)" "grep -q '^CANARY-EARLY DAT' $TG && grep -qF \"File ket qua: $RES\" $TG && grep -q '^KET QUA PHIEN: DAT' \"$RES\" && grep -qF \"$RES\" \"$SUM\""
chk "all: ghi chu USDT != 0 => pilot USDT = 0 KHONG duoc kiem; so du CHI trong file tom tat" "grep -q 'pilot USDT = 0 KHONG duoc kiem' \"$SUM\" && grep -q 'USDT=1000.00000000' \"$SUM\" && grep -q 'pilot USDT = 0' $TG"
chk "all: [3f] Telegram KHONG co so du (tmb/USDT/assets) + co dong LEGACY (chi dem); file ket qua co dong LEGACY" "! grep -qE 'tmb|10971|1000\.00000000|BFUSD' $TG && grep -q 'LEGACY vi the K0=44' $TG && grep -q '^LEGACY vi the K0=44' \"$RES\""
chk "all: v_t_m khong doi; khong key/secret trong log, Telegram, tom tat" "[ \"\$(vmd5)\" = $V0 ] && [ ! -e $F/run/canary ] && ! grep -rqF \"$FK\" $W/canarylog $TG && ! grep -rqF \"$FS\" $W/canarylog $TG"
echo "-- 17c [3f §ADD-4 H] tmb doc duoc 8000 (tai khoan chinh) => KHONG dung vi tmb (chi ghi); K0 + phien chay; Telegram DAT"
fresh; echo 8000 > $C3/FAKE_TMB
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: tmb 8000 => van K0 (khong kiem tmb tuyet doi), phien DAT, Telegram khong co tmb" "[ $RC = 0 ] && grep -q '^preflight  TMB=8000 ' \$(ls -td $C3/run/canary_done_* | head -1)/fake_calls.log && grep -q '^CANARY-EARLY DAT' $TG && ! grep -q 'tmb' $TG && ! echo \"\$OUT\" | grep -qF 'ngoai [9500'"
echo "-- 17d tai khoan KHONG phang luc dau (ngoai gio) => KHONG cho; flatten (early); Telegram LOI"
fresh; touch $C3/FAKE_NOT_FLAT; echo "10 50" > $W/hm
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: khong phang => DUNG ngay (khong cho), flatten DAT, khong SETUP/K0" "[ $RC = 2 ] && ! echo \"\$OUT\" | grep -q 'ngoai khung gio — CHO' && [ \"\$(callsN $C3/run/canary/fake_calls.log)\" = flatten ] && grep -q 'KHONG phang' $TG && grep -q 'flatten (mode early): DAT' $TG && [ ! -e $C3/FAKE_NOT_FLAT ]"
echo "-- 17e khung gio khong mo trong CL_WAIT_MAX_S => DUNG, khong SETUP/K0"
fresh; echo "10 50" > $W/hm
OUT=$(printf 'YES\n' | ca CL_WAIT_MAX_S=9 bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: cho qua han => DUNG, Telegram LOI, chi co keycheck (kiem phang lai trong luc cho)" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'cho khung gio qua' && [ -z \"\$(callsN $C3/run/canary/fake_calls.log)\" ] && [ \$(grep -c '^keycheck' $C3/run/canary/fake_calls.log) -ge 3 ] && grep -q '^CANARY-EARLY LOI' $TG"
echo "-- 17f K3 TRUOT trong phien => phien flatten + cleanup; Telegram TRUOT + file ket qua"
fresh; touch $C3/FAKE_TRUOT_K3
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?; RES=$(lastres)
chk "all: K3 TRUOT => rc 3, KHONG K4, Telegram TRUOT + duong dan file ket qua" "[ $RC = 3 ] && [ \"\$(callsN $C3/run/canary/fake_calls.log)\" = 'status preflight status K1 K2 K3 flatten cleanup' ] && grep -q '^CANARY-EARLY TRUOT' $TG && grep -qF \"File ket qua: $RES\" $TG && grep -q '^KET QUA PHIEN: TRUOT' \"$RES\""
echo "-- 17g phien cu co giao dich, khong CANARY_RESET => TU CHOI"
rm -f $TG
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: phien cu TRADE => DUNG (can CANARY_RESET=1), khong K0 moi" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'CANARY_RESET=1' && [ \$(grep -c '^preflight' $C3/run/canary/fake_calls.log) = 1 ] && grep -q '^CANARY-EARLY LOI' $TG"
chk "all: [3g MIN-5] phien cu => KHONG kiem phang/flatten (JAR_READY sau kiem phien cu)" "! echo \"\$OUT\" | grep -q -- '--> JVM canary: flatten' && grep -q 'khong flatten (chua qua kiem chuan bi' $TG"
echo "-- 17h K0 TRUOT vi ly do khac SETUP => DUNG, khong SETUP, Telegram TRUOT"
fresh; touch $C3/FAKE_TRUOT_K0
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: K0 TRUOT (khong phai SETUP) => rc 3, 1 preflight, khong setup, khong run" "[ $RC = 3 ] && [ \"\$(callsN $C3/run/canary/fake_calls.log)\" = 'status preflight' ] && grep -q '^CANARY-EARLY TRUOT' $TG"
echo "-- 17i co file CANARY_STOP => tu choi ngay"
fresh; touch $W/canarylog/CANARY_STOP
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
rm -f $W/canarylog/CANARY_STOP
chk "all: co CANARY_STOP => TU_CHOI, khong JVM" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'CANARY_STOP' && [ ! -e $C3/run/canary/fake_calls.log ]"
echo "-- 17j [3d] cl_run: lenh ssh khoi dong JVM tra ve NGAY (khong giu kenh ssh toi khi JVM xong); poll van lay du ket qua"
cat > $W/fakessh.sh <<'EOF'
# ssh GIA: nhu ssh that, chi tra ve khi MOI fd stdout cua lenh tu xa dong (| cat)
bash -c "$1" | cat
echo "RET $(date +%s%3N)" >> "$FAKESSH_LOG"
EOF
fresh; touch $C3/FAKE_SLOW; rm -f $W/fakessh.log $C3/FAKE_SLOW.log
OUT=$(ce CANARY_MODE=early SSH_242="bash $W/fakessh.sh" FAKESSH_LOG=$W/fakessh.log bash -c ". $CN/canary_lib.sh; T0=\$(date +%s%3N); cl_run '' keycheck; echo RC=\$? T0=\$T0" 2>&1)
R1=$(awk '/^RET/ {print $2; exit}' $W/fakessh.log); E1=$(awk '/^END/ {print $2; exit}' $C3/FAKE_SLOW.log); T0J=$(echo "$OUT" | sed -n 's/.*T0=\([0-9]*\).*/\1/p')
chk "cl_run: ssh khoi dong tra ve < 3 s (truoc khi JVM 6 s xong), van DAT + doc du dong KEYCHECK" "[ -n \"$R1\" ] && [ -n \"$E1\" ] && [ $(( ${R1:-0} - ${T0J:-0} )) -lt 3000 ] && [ ${R1:-0} -lt ${E1:-0} ] && echo \"\$OUT\" | grep -q 'RC=0' && echo \"\$OUT\" | grep -q '| KEYCHECK serverTime=1'"
rm -f $C3/FAKE_SLOW $C3/FAKE_SLOW.log
echo "== 18. [V12 3f §ADD-4 J] canary_set_key.sh MOT lenh: key RIENG tai khoan chinh, read -s, 600, khong in key"
FK2="MAINKEY$(date +%s%N | md5sum | cut -c1-32)abcdefghijklmnopqrstuv"; FS2="MAINSEC$(date +%N%s | md5sum | cut -c1-32)ABCDEFGHIJKLMNOPQRSTUV"
OUT=$(printf 'no\n%s\n%s\n' "$FK2" "$FS2" | ce bash $CN/canary_set_key.sh 2>&1); RC=$?
chk "set_key: khong go YES => TU_CHOI, khong ghi" "[ $RC = 2 ] && ! grep -qF \"$FK2\" $W/keys/c3live/keys.env"
OUT=$(printf 'YES\n%s\n%s\n' "$FK2" "$FS2" | ce bash $CN/canary_set_key.sh 2>&1); RC=$?; echo "$OUT" | grep -a 'GHI_XONG\|KET QUA' | head -3
chk "set_key: YES => ghi 600 + thu muc 700 + 2 dong dung key moi + backup ban cu (600)" "[ $RC = 0 ] && [ \$(stat -c %a $W/keys/c3live/keys.env) = 600 ] && [ \$(stat -c %a $W/keys/c3live) = 700 ] && grep -qxF \"C3_LIVE_API_KEY=$FK2\" $W/keys/c3live/keys.env && grep -qxF \"C3_LIVE_API_SECRET=$FS2\" $W/keys/c3live/keys.env && [ \$(ls $W/keys/c3live/keys.env.bak_* | wc -l) -ge 2 ]"
chk "set_key: keycheck chi doc (jar pin da tren 242 gia), KHONG lo key/secret ra output/log, KHONG in so du" "echo \"\$OUT\" | grep -q 'KET QUA: DAT' && ! echo \"\$OUT\" | grep -qF \"$FK2\" && ! echo \"\$OUT\" | grep -qF \"$FS2\" && ! grep -rqF \"$FK2\" $W/canarylog && ! grep -rqF \"$FS2\" $W/canarylog && ! echo \"\$OUT\" | grep -q 'keycheck (chi doc): .*tmb='"
OUT=$(printf 'YES\nabc\nxyz\n' | ce bash $CN/canary_set_key.sh 2>&1); RC=$?
chk "set_key: key sai dinh dang => TU_CHOI, giu key cu" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'sai dinh dang' && grep -qxF \"C3_LIVE_API_KEY=$FK2\" $W/keys/c3live/keys.env"
echo "== 19. [V12 3g] MIN-8 legacy_symbols.csv rong/thieu => TU CHOI; MIN-3 tran phien <= 0,10 => TU CHOI"
fresh; mv $F/run/legacy_symbols.csv $W/legacy.bak
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: thieu legacy_symbols.csv => DUNG truoc K0" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'legacy_symbols.csv RONG hoac THIEU' && ! grep -q '^preflight' $C3/run/canary/fake_calls.log"
fresh; : > $F/run/legacy_symbols.csv
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: legacy_symbols.csv rong => DUNG truoc K0" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'legacy_symbols.csv RONG hoac THIEU' && ! grep -q '^preflight' $C3/run/canary/fake_calls.log"
mv -f $W/legacy.bak $F/run/legacy_symbols.csv
fresh; mkdir -p $C3/run/canary_prev_29990102_000000
echo '{"symMain":"C00USDT","symAux":"C01USDT","cumFeeStable":0.45,"cumRealized":-3.5,"cumFunding":0.0,"steps":{}}' > $C3/run/canary_prev_29990102_000000/canary_state.json
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: lo cong don 3.95 => tran phien 0.05 <= 0.10 => DUNG truoc K0" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'tran lo phien min(2, 4 - lo cong don 3.9500) = 0.0500' && ! grep -q '^preflight' $C3/run/canary/fake_calls.log"
rm -rf $C3/run/canary_prev_29990102_000000
echo "== 20. [V12 3i] guard IP LEGACY: keycheck loi tam thoi luc cho khung gio => thu lai (DUNG sau 10 lan lien tiep); CANARY_IP_WEIGHT_CAP"
echo "-- 20a keycheck TRUOT (guard IP) 2 lan luc vao cho => KHONG dung; doc lai duoc => phien DAT"
fresh; echo 2 > $C3/FAKE_KC_FAIL
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: keycheck loi 2 lan => thu lai o lan poll sau, KHONG dung; phang => phien DAT" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'keycheck chua doc duoc (vao cho SETUP/K0, lan 1/10' && echo \"\$OUT\" | grep -q 'keycheck chua doc duoc (doc lai SETUP/K0, lan 2/10' && echo \"\$OUT\" | grep -q 'pham vi canary phang (doc lai SETUP/K0' && grep -q '^CANARY-EARLY DAT' $TG"
echo "-- 20b keycheck loi lien tiep => DUNG sau dung 10 lan, khong SETUP/K0"
fresh; echo 99 > $C3/FAKE_KC_FAIL
OUT=$(printf 'YES\n' | ca bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "all: keycheck loi 10 lan lien tiep => DUNG (rc 2), khong preflight/setup, Telegram LOI" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'khong doc duoc trang thai pham vi canary 10 lan lien tiep' && echo \"\$OUT\" | grep -q 'lan 9/10' && ! echo \"\$OUT\" | grep -q 'lan 10/10' && ! grep -qE '^(preflight|setup)' $C3/run/canary/fake_calls.log && [ \$(grep -c '^keycheck' $C3/run/canary/fake_calls.log) -ge 10 ] && grep -q '^CANARY-EARLY LOI' $TG"
echo "-- 20c CANARY_IP_WEIGHT_CAP (khong can file gate) qua env -i cua cl_run; sai dinh dang => DUNG truoc JVM"
fresh
OUT=$(ce CANARY_MODE=early CANARY_IP_WEIGHT_CAP=1700 bash -c ". $CN/canary_lib.sh; cl_run '' keycheck; echo RC=\$?" 2>&1)
chk "cl_run: CANARY_IP_WEIGHT_CAP=1700 toi JVM canary" "echo \"\$OUT\" | grep -q 'RC=0' && grep -qx 'keycheck IPCAP=1700' $C3/run/canary/fake_env.log"
OUT=$(ce CANARY_MODE=early CANARY_IP_WEIGHT_CAP=17x0 bash -c ". $CN/canary_lib.sh; cl_run '' keycheck; echo RC=\$?" 2>&1)
chk "cl_run: CANARY_IP_WEIGHT_CAP sai dinh dang => DUNG, khong chay JVM" "! echo \"\$OUT\" | grep -q 'RC=' && echo \"\$OUT\" | grep -q 'CANARY_IP_WEIGHT_CAP=.17x0. khong phai so nguyen' && [ \$(grep -c . $C3/run/canary/fake_env.log) = 1 ]"
fresh
chk "v_t_m KHONG doi qua muc 17" "[ \"\$(vmd5)\" = $V0 ] && [ ! -e $F/run/canary ]"
echo "== 21. [V12 3k R2] CANARY_PRIOR_LOSS_USDT phai TINH LAI ngay sau CANARY_RESET (moi lan goi JVM)"
fresh; rm -rf $C3/run/canary_prev_*
mkdir -p $C3/run/canary $C3/run/canary_prev_29990101_000000
echo '{"symMain":"C00USDT","symAux":"C01USDT","cumFeeStable":0.0201,"cumRealized":0.0,"cumFunding":0.0,"steps":{"K1":{"result":"DAT"}}}' > $C3/run/canary/canary_state.json
echo '{"symMain":"C00USDT","symAux":"C01USDT","cumFeeStable":0.0195,"cumRealized":0.0,"cumFunding":0.0,"steps":{"K1":{"result":"DAT"}}}' > $C3/run/canary_prev_29990101_000000/canary_state.json
OUT=$(printf 'YES\n' | ca CANARY_RESET=1 bash $CN/canary_early_all.sh 2>&1); RC=$?
chk "prior: truoc reset = 0.0195 (phien hien tai chua tinh), JVM cleanup thay 0.0195" "echo \"\$OUT\" | grep -q 'PRIOR_USED cmd=cleanup prior=0.0195'"
chk "prior: SAU reset tinh lai = 0.0396 cho preflight/status/step (khong con 0.0195)" "echo \"\$OUT\" | grep -q 'PRIOR_USED cmd=preflight prior=0.0396' && echo \"\$OUT\" | grep -q 'prior sau reset = 0.0396 USDT' && ! echo \"\$OUT\" | grep -qE 'PRIOR_USED cmd=(preflight|status|setup|step) prior=0.0195'"
chk "prior: JVM nhan dung CANARY_PRIOR_LOSS_USDT=0.0396 sau reset (fake_prior.log cua phien)" "D=\$(ls -td $C3/run/canary_done_* $C3/run/canary 2>/dev/null | head -1); grep -q 'PRIOR=0.0396' \"\$D/fake_prior.log\" && ! grep -qE '^(preflight|status|step).*PRIOR=0.0195' \"\$D/fake_prior.log\""
chk "prior: file ket qua ghi prior dung cho phien + luc tinh" "RES=\$(lastres); grep -q 'prior dung cho phien (CANARY_PRIOR_LOSS_USDT): 0.0396 USDT' \"\$RES\""
rm -rf $C3/run/canary_prev_29990101_000000
echo "== 22. [V12 R4b] deploy_v12_dry_r4.sh (dry tai khoan chinh, jar R4b) tren 242 gia RIENG"
(cd "$F" && bin/daemon.sh stop); sleep 1
F4=$W/v_t_m_r4; rm -rf "$F4"; mkdir -p "$F4/conf" "$F4/bin" "$F4/logs" "$F4/run" "$F4/target"
cat > "$F4/conf/env.sh" <<'EOF'
export LIVE_PROFILE=c3_shadow
export SHADOW_NO_PUSH=true
export LIVE_TS_MKT_EXT=1
export LIVE_HEARTBEAT=1
export LIVE_KILLSW_MODE=log
export LIVE_PERIODIC_RESET_HOURS=0
export LIVE_EXEC_PROBE=1
EOF
cp "$F/bin/start.sh" "$F/bin/daemon.sh" "$F4/bin/"
printf 'fake-old-jar-dcae' > "$F4/target/binance-java-sdk-1.2.4.jar"
printf 'fake-new-jar-v12r4b' > "$W/new_r4.jar"
NEW4=$(md5sum < "$W/new_r4.jar" | cut -c1-32)
python3 - "$W/exinfo_r4.json" <<'EOF'
import json, sys
s = [{"symbol": "S%03dUSDT" % i, "contractType": "PERPETUAL", "underlyingType": "COIN"} for i in range(160)]
s += [{"symbol": "T%03dUSDT" % i, "contractType": "TRADIFI_PERPETUAL", "underlyingType": "EQUITY"} for i in range(60)]
json.dump({"symbols": s}, open(sys.argv[1], "w"), separators=(",", ":"))
EOF
(cd "$F4" && bin/daemon.sh start)
D4=$HERE/deploy_v12_dry_r4.sh
r4() { env APP_DIR=$F4 NJ=$W/new_r4.jar NJ_MD5=$NEW4 EXINFO_CMD="cat $W/exinfo_r4.json" "$@"; }
p4env() { tr '\0' '\n' < /proc/$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ; }
OUT=$(r4 DRY=1 bash "$D4" 2>&1); echo "$OUT" | tail -2
chk "r4 DRY PASS, in C3_CAPITAL=10000, khong doi env" "echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'export C3_CAPITAL=10000' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh"
OUT=$(r4 NJ_MD5=__R4B_MD5__ DRY=1 bash "$D4" 2>&1)
chk "r4 NJ_MD5 chua pin => DUNG" "echo \"\$OUT\" | grep -q 'NJ_MD5 chua pin'"
if [ "$(date +%s)" -lt "$(date -d '2026-11-18 07:54 +07' +%s)" ]; then
  OUT=$(echo YES | r4 FORCE_TIME=1 bash "$D4" 2>&1)
  chk "r4 tu choi truoc 2026-11-18 07:54 (khong FORCE)" "echo \"\$OUT\" | grep -q 'truoc 2026-11-18 07:54' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh"
fi
OUT=$(r4 OLD_MD5=00000000000000000000000000000000 DRY=1 bash "$D4" 2>&1)
chk "r4 jar dang chay khac OLD_MD5 => TU CHOI" "echo \"\$OUT\" | grep -q 'kiem 242 co muc FAIL' && echo \"\$OUT\" | grep -q 'FAIL jar_dang_chay'"
for f in run/c3live_merged.txt run/c3live_equity_c3.json run/killsw_latch.json run/c3live_killsw_peak; do
  echo x > "$F4/$f"
  OUT=$(r4 DRY=1 bash "$D4" 2>&1)
  chk "r4 PRE: co $f cu => TU CHOI" "echo \"\$OUT\" | grep -q \"FAIL da_co_$f\""
  rm -f "$F4/$f"
done
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 EXINFO_CMD="cat $W/exinfo.json" bash "$D4" 2>&1); RC=$?; echo "$OUT" | grep -a 'exchangeInfo\|DUNG' | head -3
chk "r4 exchangeInfo thieu contractType/underlyingType/TradFi => DUNG, env khoi phuc, jar cu" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'FAIL exchangeInfo' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $OLD ]"
chk "r4 exchangeInfo xau: process van c3_shadow" "p4env | grep -qx 'LIVE_PROFILE=c3_shadow'"
touch "$F4/FAKE_R4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?; echo "$OUT" | tail -4
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4 deploy XONG (YES 1 lan)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=== XONG' && echo \"\$OUT\" | grep -q 'OK R4_LEGACY_scope' && echo \"\$OUT\" | grep -q 'OK exchangeInfo_hop_le'"
chk "r4 env: C3_CAPITAL=10000 + LIVE_ADAPTER=dry + SHADOW_NO_PUSH=true" "grep -qx 'export C3_CAPITAL=10000' $F4/conf/env.sh && grep -qx 'export LIVE_ADAPTER=dry' $F4/conf/env.sh && grep -qx 'export SHADOW_NO_PUSH=true' $F4/conf/env.sh"
chk "r4 process moi: C3_CAPITAL=10000, dry, jar R4b" "p4env | grep -qx 'C3_CAPITAL=10000' && p4env | grep -qx 'LIVE_ADAPTER=dry' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEW4 ]"
chk "r4 exchangeInfo tho dat vao run/ (du TradFi)" "[ \$(grep -o 'TRADIFI_PERPETUAL' $F4/run/c3live_exchangeInfo.json | wc -l) = 60 ]"
chk "r4 PAUSE watchdog da xoa" "[ ! -f $W/PAUSE ]"
OUT=$(echo YES | APP_DIR=$F4 DRY=0 bash "$HERE/c3live_reanchor.sh" 2>&1); RC=$?
chk "reanchor TU CHOI o qty mode (R4+), khong ghi yeu cau" "[ $RC = 4 ] && echo \"\$OUT\" | grep -q 'TU CHOI' && [ ! -f $F4/run/c3live_reanchor.req ]"
echo x > "$F4/run/c3live_merged.txt"; echo x > "$F4/run/c3live_equity_c3.json"
OUT=$(echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" 2>&1); echo "$OUT" | tail -2
chk "r4 rollback: env c3_shadow, jar cu, file R4 doi ten .rb_TS" "echo \"\$OUT\" | grep -q 'Rollback xong' && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $OLD ] && [ -f $F4/run/c3live_merged.txt.rb_$TS4 ] && [ -f $F4/run/c3live_equity_c3.json.rb_$TS4 ]"
touch "$F4/FAKE_EXBAD"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?; echo "$OUT" | grep -a 'KHONG hop le\|DEPLOY FAIL' | head -2
chk "r4 sau start log 'exchangeInfo KHONG hop le' => ROLLBACK TU DONG" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'FAIL exchangeInfo_KHONG_hop_le' && echo \"\$OUT\" | grep -q 'Rollback xong' && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh && [ ! -f $W/PAUSE ]"
rm -f "$F4/FAKE_EXBAD" "$F4/FAKE_R4"
rm -f "$F4/run/c3live_book.json"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4 jar khong in dong R4 (LEGACY tren tai khoan chinh) => WAIT qua han => ROLLBACK TU DONG" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'WAIT R4_LEGACY_scope' && echo \"\$OUT\" | grep -q 'Rollback xong'"
pkill -f 'BinanceOrderTradingManager fake242'
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
