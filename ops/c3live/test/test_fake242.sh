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
    D=$(date '+%d/%m/%Y %H:%M:%S.000')
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
pkill -f 'BinanceOrderTradingManager fake242'
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
