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
chmod -R u+w "$W" 2>/dev/null; rm -rf "$W"; mkdir -p "$W"   # [delta MIN-4] pin chi doc
# [A1 ADD4] trap: ket thuc / loi / ngat => don MOI tien trinh con cua bo test (ke ca setsid / nohup / mo coi): nhan dien bang duong dan
#   "$W/" trong cmdline / cwd / environ. KHONG dong tien trinh ngoai $W (vd mo coi cua lan test khac), khong dong bo test + to tien.
f242_cleanup() {
  local p q=$$ anc=" $$ " L sig
  while [ -n "$q" ] && [ "$q" != 0 ] && [ "$q" != 1 ]; do q=$(ps -o ppid= -p "$q" 2>/dev/null | tr -d ' '); anc="$anc$q "; done
  for sig in TERM KILL; do
    for p in $(ls /proc | grep -E '^[0-9]+$'); do
      case "$anc" in *" $p "*) continue;; esac
      [ -O "/proc/$p" ] || continue
      L=$( { tr '\0' '\n' < /proc/$p/cmdline; echo; readlink /proc/$p/cwd; tr '\0' '\n' < /proc/$p/environ; } 2>/dev/null)
      if printf '%s\n' "$L" | grep -qF "$W/" || printf '%s\n' "$L" | grep -qxF "$W"; then kill -$sig "$p" 2>/dev/null; fi
    done
    [ $sig = TERM ] && sleep 1
  done
}
trap 'f242_cleanup' EXIT
trap 'exit 130' INT TERM HUP
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
  stop) pkill -f 'BinanceOrderTradingManager fake242'; [ -f run/slow.pid ] && kill "$(cat run/slow.pid)" 2>/dev/null; rm -f run/slow.pid ;;
  start)
    set -a; . conf/env.sh; set +a
    if [ -f FAKE_SLOWSTART ]; then   # [R4q] JVM len CHAM (1 lan): process xuat hien sau 12 s
      rm -f FAKE_SLOWSTART
      nohup bash -c 'sleep 12; N=BinanceOrderTradingManager; exec -a "$N fake242" sleep 900' >/dev/null 2>&1 & echo $! > run/slow.pid
    else
      nohup bash -c 'exec -a "BinanceOrderTradingManager fake242" sleep 900' >/dev/null 2>&1 &
    fi
    sleep 1
    [ -f FAKE_APIHOOK ] && { bash FAKE_APIHOOK; rm -f FAKE_APIHOOK; }   # [R4q] doi fixture san NGAY sau start (1 lan)
    D=$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000')   # log 242 that ghi gio +07
    {
      echo "$D INFO [main] x: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager"
      echo "$D INFO [main] x: [HEARTBEAT] BAT file=run/heartbeat"
      echo "$D INFO [main] x: [TS-EXT] BAT LIVE_TS_MKT_EXT=1 profile=c3_shadow|c3_live"
      if [ "$LIVE_PROFILE" = c3_live ]; then
        # [V12 R4o] PUSH nhu LiveProfileC3.decideNoPush: ON chi khi SHADOW_NO_PUSH=false + LIVE_ENTRY_ENABLED=true + khong run/KILL_SWITCH
        PUSHV=OFF; [ "${SHADOW_NO_PUSH:-}" = false ] && [ "${LIVE_ENTRY_ENABLED:-}" = true ] && [ ! -e run/KILL_SWITCH ] && PUSHV=ON
        R4Q=0; grep -q r4q target/binance-java-sdk-1.2.4.jar 2>/dev/null && R4Q=1   # [R4q] jar gia r4q => dong log moi
        echo "$D WARN [main] x: 🟠 [LIVE_PROFILE=c3_live] BAT — hanh vi C3 day du PUSH=$PUSHV (SHADOW_NO_PUSH=${SHADOW_NO_PUSH:-})$([ $R4Q = 1 ] && echo ' LEGACY_QUEUE_LIVE_BLOCK=true')"
        [ $R4Q = 1 ] && echo "$D INFO [pool-1-thread-1] x: [GATE-PRE] 2026-11-05 13:00 nguon=C3_LIVE_BOOK bo_dang_giu=0 legacy_qua_gate_khong_vao=0 a1_bo=0 premarket_bo=1"
        if grep -q r4r target/binance-java-sdk-1.2.4.jar 2>/dev/null; then   # [R4r] jar gia r4r => dong [MINUTE-GUARD] nhu start()
          MGS=BAT; { [ -f FAKE_MGTAT ] || [ "${LIVE_MINUTE_GUARD:-1}" = 0 ]; } && MGS="TAT (LIVE_MINUTE_GUARD=0)"
          echo "$D INFO [main] x: [MINUTE-GUARD] $MGS — phut du <=> so symbol >= 99% trung vi 60' truoc [CHI live]"
        fi
        # [R4q] nhu LiveProfileC3.forceNoPush moi 10 s: KILL_SWITCH bi go => log "PUSH doi trang thai -> ON"
        if [ "$PUSHV" = OFF ] && [ "${SHADOW_NO_PUSH:-}" = false ] && [ "${LIVE_ENTRY_ENABLED:-}" = true ] && [ ! -f FAKE_NOPUSHON ]; then
          nohup bash -c 'for i in $(seq 1 300); do sleep 1; [ -e run/KILL_SWITCH ] || { echo "$(TZ=Asia/Ho_Chi_Minh date "+%d/%m/%Y %H:%M:%S.000") WARN [x] x: [C3-LIVE] PUSH doi trang thai -> ON (SHADOW_NO_PUSH=false LIVE_ENTRY_ENABLED=true killSwitch=run/KILL_SWITCH exists=false)" >> logs/full.log; exit 0; }; done' >/dev/null 2>&1 &
        fi
        echo "$D WARN [main] x: [KILLSW] BAT mode=act (c3_live): ..."
        FLN=$(cat FAKE_LEGACY_N 2>/dev/null || echo 44)
        FSN=$(cat FAKE_SCOPE_N 2>/dev/null || echo $FLN)   # [ADD4] scope jar: vi the NGOAI c3 tren tk cua key c3 (tk con: phai 0)
        if [ "${LIVE_ADAPTER:-}" = live ]; then
          echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=LIVE gateway=c3scope(live) book=run/c3live_book.json cum=0 c3_capital=${C3_CAPITAL:-?}.0 tai_khoan=CHINH(pham vi c3) killSwitchArmed=true X14=true stream=ws"
          echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-SCOPE] LEGACY tren tai khoan chinh: $FSN vi the (foreign DA BIET, khong phai cum ma, khong chan (A)); LEGACY-busy=$FSN symbol"
          echo "$D INFO [C3LIVE-STREAM] x: [C3-LIVE-STREAM] da ket noi"
          [ -f FAKE_C3EXEC ] && echo "$D INFO [C3LIVE-OPS] x: [C3-LIVE-ORDER] ts=1 cid=c3-C01USDT-1-0 oid=1 sym=C01USDT side=BUY type=MARKET qty=1 px=1 status=FILLED lat_ms=5 err=- reason=-"
        else
          echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=DRY gateway=dry book=run/c3live_book.json cum=0 killSwitchArmed=true X14=true"
        fi
        echo "$D INFO [main] x: [C5] GLOBAL OK"
        echo "$D INFO [main] x: [UNIVERSE] listed=640 alive=600 tradable=480 buyable=470 +0 -0 tradfi_excl=110"
        echo "$D INFO [main] x: [C3-LIVE-RECON] khoi dong: ok=true closedWhileDown=[]"
        # [V12 R4o] JVM gia: C11 / LEGACY / gate tick / nap seed gate (GATE_BUFFER_SEED) nhu LiveGateRollingRatio
        [ "${LIVE_SEED_EXCLUDE_DECISION_MIN:-0}" = 1 ] || echo "$D WARN [main] x: [FEAT-PIPE] LIVE_PROFILE=c3_live nhung LIVE_SEED_EXCLUDE_DECISION_MIN=0 => race seed/tick dau sau restart (C11) VAN CON"
        echo "$D INFO [pool-3-thread-1] x: [LEGACY] managed $(cat FAKE_LEGACY_N 2>/dev/null || echo 44): AAAUSDT,BBBUSDT"
        echo "$D INFO [pool-1-thread-1] x: [GATE] scale=1.5500 topk=24 base=0.00800 n_cand=3 n_rej=3 n_pass=0"
        if [ -n "${GATE_BUFFER_SEED:-}" ]; then
          if [ -f run/gate_ratio_live.bin.seeded ]; then echo "$D WARN [main] x: [GATE-SEED] persist da nap seed truoc do (x) => BO QUA seed $GATE_BUFFER_SEED (persist thang), chay tiep"
          elif [ -f FAKE_SEEDKHAN ] || [ "$(md5sum < "$GATE_BUFFER_SEED" 2>/dev/null | cut -c1-32)" != "${GATE_BUFFER_SEED_MD5:-}" ]; then
            echo "$D ERROR [main] x: [GATE-SEED] KHAN: seed $GATE_BUFFER_SEED HONG (gia lap) — CHAN VAO LENH MOI"
          else
            echo "$D WARN [main] x: *** [GATE-SEED] nap seed $GATE_BUFFER_SEED md5=$GATE_BUFFER_SEED_MD5 n=10 [a .. b] + persist sau seed 0 (bo 3 ban ghi persist <= cuoi seed) => buffer 10 ***"
            echo "md5=$GATE_BUFFER_SEED_MD5 seedLast=1 appliedAt=2" > run/gate_ratio_live.bin.seeded
          fi
        fi
        # [V12 R4b] dong cua jar R4b (chi khi co FAKE_R4) / exchangeInfo xau (FAKE_EXBAD)
        [ -f FAKE_R4 ] && [ "${LIVE_ADAPTER:-}" != live ] && echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=DRY gateway=c3scope(dry) cum=0 c3_capital=10000.0 tai_khoan=CHINH(pham vi c3) killSwitchArmed=true"
        [ -f FAKE_R4 ] && [ "${LIVE_ADAPTER:-}" != live ] && echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-SCOPE] LEGACY tren tai khoan chinh: 0 vi the (foreign DA BIET, khong phai cum ma, khong chan (A)); LEGACY-busy=0 symbol"
        [ -f FAKE_EXBAD ] && echo "$D ERROR [C3LIVE-OPS] x: [C3-LIVE UNIVERSE] exchangeInfo KHONG hop le (R7 fail-fast): gia lap"
        [ -f FAKE_LATCH ] && echo "$D WARN [main] x: [KILLSW] LATCH action=FLATTEN (truoc NONE) code=C6 codes=[C6] detail=dd=-0.7144"
        # [V12 R4c D3] dong VO HAI (khong duoc gay FAIL) / CO HAI (phai FAIL + rollback)
        [ -f FAKE_HARMLESS ] && echo "$D WARN [pool-1] x: [OI-GUARD-2] oi_feat pipeline STALE age=130m > 120m (Oracle/compute down?)"
        [ -f FAKE_SCOPE ] && echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-SCOPE] TU CHOI newMarketOrder C30USDT: LEGACY-busy vi the 100"
        [ -f FAKE_HARMLESS ] && echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-RECON] TU CHOI yeu cau reanchor: c3_live doi chieu theo QTY c3"
        [ -f FAKE_STALE ] && echo "$D INFO [C3LIVE-OPS] x: [C3-LIVE] S001USDT NOT_BUYABLE STALE snapshot=1792900020000"
        [ -f FAKE_NORUNTIME ] && echo "$D ERROR [main] x: [C3-LIVE] KHONG tao duoc runtime (gia lap) => TU CHOI push c3_live; vi the cu (neu co) CHI con stop"
        # [V12 R4d] JVM gia DOC file A1 nhu that: UNIVERSE_A1=1 => dong init (TradFi dem tu file) / thieu file => exception
        if [ "${UNIVERSE_A1:-0}" = 1 ] && [ ! -f FAKE_NOA1 ]; then
          if [ -s run/c3live_exchangeInfo.json ]; then
            TFN=$(grep -o TRADIFI_PERPETUAL run/c3live_exchangeInfo.json | wc -l); [ -f FAKE_A1LOW ] && TFN=10
            IXN=$(grep -o '"underlyingType":"INDEX"' run/c3live_exchangeInfo.json | wc -l)
            PMX=""; grep -q r4q target/binance-java-sdk-1.2.4.jar 2>/dev/null && PMX=", PREMARKET=1"
            echo "$D WARN [main] x: [UNIVERSE-A1] BAT — loai $((TFN + IXN)) symbol (TradFi=$TFN, INDEX=$IXN$PMX) / 0 symbol tu run/c3live_exchangeInfo.json sha256=fake serverTime=1 unclassified=0"
          else
            echo "$D ERROR [main] x: java.lang.IllegalStateException: [UNIVERSE-A1] BAT nhung KHONG thay exchangeInfo: run/c3live_exchangeInfo.json"
          fi
        fi
      else
        echo "$D INFO [main] x: 🟡 [LIVE_PROFILE=c3_shadow] BAT"
      fi
    } >> logs/full.log
    # [2d] log xoay ngay sau start (dong start + LATCH nam o full.log.1) / mat log
    [ -f FAKE_ROTATE ] && { mv -f logs/full.log logs/full.log.1; echo "$D INFO [main] x: (sau xoay log)" > logs/full.log; }
    [ -f FAKE_NOLOG ] && rm -f logs/full.log logs/full.log.*
    # [V12 R4c C] mat ket noi 242 ngay sau start (ssh GIA doc file nay)
    [ -f FAKE_SSHDROP ] && touch "$(cat FAKE_SSHDROP)"
    [ -f FAKE_EXOLD ] && touch -d '-40 min' run/c3live_exchangeInfo.json
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

# [R4e] crontab GIA (file $W/crontab.txt; KHONG dung crontab that cua Oracle); dong cron khac phai duoc giu nguyen
cat > "$W/fakecrontab.sh" <<EOF
case "\$1" in
  -l) if [ -f "$W/crontab.txt" ]; then cat "$W/crontab.txt"; else echo "no crontab for root" >&2; exit 1; fi ;;
  -) cat > "$W/crontab.txt" ;;
  *) exit 2 ;;
esac
EOF
echo "*/5 * * * * /bin/bash /root/h242_watchdog.sh # WATCHDOG" > "$W/crontab.txt"
export CRONTAB_CMD="bash $W/fakecrontab.sh" SSH_RETRY_S=0
export PROC_PAT="BinanceOrderTradingManager fake242" SSH_242="bash -c" SCP_242=cp RHOST="" APP_DIR=$F LOGDIR=$W/deploylog WD_PAUSE=$W/PAUSE OLD_MD5=$OLD NJ=$W/new.jar \
  NJ_MD5=$NEW KILLSW_SH=$REPO/ops/killsw_reset.sh EXINFO_CMD="cat $W/exinfo.json" POST_WAIT_S=2 POST_ROUNDS=2 WAIT_S=3 \
  REANCHOR_WAIT=2 LATCH_WAIT_S=2
# KILLSW_MD5 KHONG dat => dung md5 pin mac dinh trong deploy_v12_dry.sh (kiem pin khop ops/killsw_reset.sh cua repo)
PASS=0; FAILN=0; SKIPN=0
skp() { SKIPN=$((SKIPN+1)); echo "  [SKIP] $1"; }   # chk phu thuoc gio/ngay chay: dem rieng => tong co dinh
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
else
  skp "tu choi truoc 11-18 (da qua ngay)"
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
  skp "rollback tu choi ngoai khung gio (dang trong khung $HH:$MM)"
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
else
  skp "preflight: ngoai khung gio => TU_CHOI (dang trong khung / sat bien phut)"
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
s = [{"symbol": "S%03dUSDT" % i, "contractType": "PERPETUAL", "underlyingType": "COIN", "onboardDate": 1600000000000} for i in range(160)]
s += [{"symbol": "T%03dUSDT" % i, "contractType": "TRADIFI_PERPETUAL", "underlyingType": "EQUITY", "onboardDate": 1780000000000} for i in range(60)]
s += [{"symbol": x, "contractType": "PERPETUAL", "underlyingType": "INDEX", "onboardDate": 1600000000000} for x in ("ALLUSDT", "BTCDOMUSDT", "DEFIUSDT")]
json.dump({"serverTime": 1793072475507, "symbols": s}, open(sys.argv[1], "w"), separators=(",", ":"))   # [R4d] raw: serverTime + onboardDate
json.dump({"symbols": s}, open(sys.argv[1] + ".nost", "w"), separators=(",", ":"))
json.dump({"serverTime": 1793072475507, "symbols": [{k: v for k, v in x.items() if k != "onboardDate"} for x in s]}, open(sys.argv[1] + ".noob", "w"), separators=(",", ":"))
EOF
(cd "$F4" && bin/daemon.sh start)
D4=$HERE/deploy_v12_dry_r4.sh
export DEPLOY_TG_SINK=$W/tg_r4.txt   # [R4c] job nen gui Telegram => test LUON ghi file, KHONG gui that
cat > "$W/exgen.py" <<'EOF'
# [R4f] nguon gia: exinfo_r4.json voi serverTime = bay gio (nhu san that: moi lan doc moi hon)
import json, sys, time
d = json.load(open(sys.argv[1]))
d["serverTime"] = int(time.time() * 1000)
sys.stdout.write(json.dumps(d, separators=(",", ":")))
EOF
# [R4k] 242 that KHONG co python3 (CentOS 7, chi python2.7): moi lenh "tren 242" cua deploy/cron chay voi PATH co python3/python GIA
# (in "command not found", rc 127); python3 RIENG = $W/c3py_t/python/bin/python3 (nhu /opt/c3py do c3py_install_242.sh cai).
REALPY=$(command -v python3); ln -sf "$REALPY" "$W/realpy"
export WD_PAUSE_MAX_S=300   # [R4m] bo tu go PAUSE (moi deploy 1 tien trinh canh) — test: 5 phut
mkdir -p "$W/nopy" "$W/c3py_t/python/bin"
printf '#!/bin/sh\necho "bash: $(basename "$0"): command not found" >&2\nexit 127\n' > "$W/nopy/python3"; cp "$W/nopy/python3" "$W/nopy/python"; chmod +x "$W/nopy/python3" "$W/nopy/python"
printf '#!/bin/sh\nexec %s "$@"\n' "$REALPY" > "$W/c3py_t/python/bin/python3"; chmod +x "$W/c3py_t/python/bin/python3"
r4() { env PATH="$W/nopy:$PATH" PY242=$W/c3py_t/python/bin/python3 APP_DIR=$F4 NJ=$W/new_r4.jar NJ_MD5=$NEW4 EXINFO_CMD="$W/realpy $W/exgen.py $W/exinfo_r4.json" DEPLOY_TG_SINK=$W/tg_r4.txt "$@"; }
p4env() { tr '\0' '\n' < /proc/$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ; }
OUT=$(r4 DRY=1 bash "$D4" 2>&1); echo "$OUT" | tail -2
chk "r4 DRY PASS, in C3_CAPITAL=10000, khong doi env" "echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'export C3_CAPITAL=10000' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh"
OUT=$(r4 NJ_MD5=__R4B_MD5__ DRY=1 bash "$D4" 2>&1)
chk "r4 NJ_MD5 chua pin => DUNG" "echo \"\$OUT\" | grep -q 'NJ_MD5 chua pin'"
if [ "$(date +%s)" -lt "$(date -d '2026-11-18 07:54 +07' +%s)" ]; then
  OUT=$(echo YES | r4 FORCE_TIME=1 bash "$D4" 2>&1)
  chk "r4 tu choi truoc 2026-11-18 07:54 (khong FORCE)" "echo \"\$OUT\" | grep -q 'truoc 2026-11-18 07:54' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh"
else
  skp "r4 tu choi truoc 2026-11-18 07:54 (da qua ngay)"
fi
OUT=$(r4 OLD_MD5=00000000000000000000000000000000 DRY=1 bash "$D4" 2>&1)
chk "r4 jar dang chay khac OLD_MD5 => TU CHOI" "echo \"\$OUT\" | grep -q 'kiem 242 co muc FAIL' && echo \"\$OUT\" | grep -q 'FAIL jar_dang_chay'"
for f in run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/ts_ext_daily.csv.a1 run/killsw_latch.json run/c3live_killsw_peak; do
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
echo "== 23. [V12 R4c] deploy_v12_dry_r4.sh: job NEN + Telegram, PRE lan 2, md5 rollback, mau CHK cu the, ssh dut, dong terminal"
TG4=$W/tg_r4.txt
OUT=$(r4 RB_MD5=00000000000000000000000000000000 DRY=1 bash "$D4" 2>&1)
chk "r4c md5 rollback_v12.sh khac pin => DUNG truoc khi doi gi" "echo \"\$OUT\" | grep -q 'md5 rollback_v12.sh sai'"
chk "r4c RB_MD5 mac dinh = md5 rollback_v12.sh cua repo" "grep -q \"RB_MD5:-\$(md5sum < $HERE/rollback_v12.sh | cut -c1-32)}\" $D4"
OUT=$(r4 FORCE=1 FORCE_TIME=1 R4_JOB=1 R4_JOBLOG=$W/fakejob.log bash "$D4" 2>&1); RC=$?
chk "r4c R4_JOB=1 khong co file YES cua foreground => TU CHOI, khong doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG co xac nhan YES' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh"
TSX=20990101_0000; LKD=$W/deploylog/.deploy_v12dry_r4.lock.d; mkdir -p $LKD; echo $TSX > $LKD/yes; echo x > $F4/run/c3live_lost.txt; rm -f "$TG4"
OUT=$(r4 FORCE=1 FORCE_TIME=1 R4_JOB=1 R4_TS=$TSX R4_JOBLOG=$W/fakejob.log R4_YES_FILE=$LKD/yes bash "$D4" 2>&1); RC=$?
chk "r4c job KIEM 242 LAI ngay truoc khi doi gi (D1): trang thai moi => DUNG + Telegram, khong doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'lan 2: ngay truoc khi doi gi' && echo \"\$OUT\" | grep -q 'FAIL da_co_run/c3live_lost.txt' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh && [ ! -e $LKD ] && grep -q 'DUNG TS=$TSX' $TG4"
rm -f $F4/run/c3live_lost.txt
touch "$F4/FAKE_R4" "$F4/FAKE_HARMLESS"; rm -f "$TG4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?; echo "$OUT" | tail -3
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4c dong vo hai (reanchor TU CHOI, '[OI-GUARD-2] ... STALE') KHONG gay FAIL => XONG" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=== XONG' && echo \"\$OUT\" | grep -q 'INFO TU_CHOI_vo_hai=1 OI_STALE=1' && grep -qx 'export LIVE_ADAPTER=dry' $F4/conf/env.sh"
chk "r4c foreground: YES -> job NEN (pid, job_log) -> tail -> rc cua job" "echo \"\$OUT\" | grep -q 'job NEN pid=[0-9]* job_log=' && echo \"\$OUT\" | grep -q 'job ket thuc rc=0'"
chk "r4c Telegram: job bat dau + XONG" "grep -q 'job NEN bat dau TS=$TS4' $TG4 && grep -q 'XONG TS=$TS4' $TG4"
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" >/dev/null 2>&1
rm -f "$F4/FAKE_HARMLESS"; touch "$F4/FAKE_STALE"; rm -f "$TG4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4c dong co hai 'STALE snapshot=' => FAIL + ROLLBACK TU DONG + Telegram" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL universe_STALE=1' && echo \"\$OUT\" | grep -q 'Rollback xong' && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh && [ ! -f $W/PAUSE ] && grep -q 'ROLLBACK TU DONG XONG' $TG4"
rm -f "$F4/FAKE_STALE"; touch "$F4/FAKE_SCOPE"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4e dry: '[C3-LIVE-SCOPE] TU CHOI' (DryGateway khong co LEGACY => loi c3) => FAIL + ROLLBACK TU DONG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL SCOPE_TU_CHOI_trong_dry=1' && echo \"\$OUT\" | grep -q 'Rollback xong'"
rm -f "$F4/FAKE_SCOPE"; touch "$F4/FAKE_NORUNTIME"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4c 'KHONG tao duoc runtime' => FAIL + ROLLBACK TU DONG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"FAIL co 'KHONG tao duoc runtime'\" && echo \"\$OUT\" | grep -q 'Rollback xong' && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
rm -f "$F4/FAKE_NORUNTIME"
cat > "$W/fakessh.sh" <<EOF
#!/usr/bin/env bash
# ssh GIA: file SSH_DOWN ton tai => nhu mat ket noi (rc 255)
[ -f "$W/SSH_DOWN" ] && { echo "ssh: connect to host 103.157.218.242 port 2222: Connection timed out" >&2; exit 255; }
exec bash -c "\$1"
EOF
echo "$W/SSH_DOWN" > "$F4/FAKE_SSHDROP"; rm -f "$TG4" "$W/SSH_DOWN"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 SSH_242="bash $W/fakessh.sh" bash "$D4" 2>&1); RC=$?; echo "$OUT" | grep -a 'PAUSE còn\|ROLLBACK TU DONG LOI' | head -2
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
RBC="FORCE_TIME=1 bash $HERE/rollback_v12.sh $TS4"
chk "r4c ssh DUT giua chung (sau restart) => rollback tu dong LOI => rc=2 + in 'PAUSE còn — chạy rollback tay: <lenh>'" "[ $RC = 2 ] && [ -f $W/SSH_DOWN ] && echo \"\$OUT\" | grep -qF \"PAUSE còn — chạy rollback tay: \$RBC\""
chk "r4c ssh dut: Telegram KHAN co dung lenh rollback tay" "grep -qF \"PAUSE còn — chạy rollback tay: \$RBC\" $TG4"
chk "r4c ssh dut: PAUSE watchdog VAN CON (khong bao xong gia)" "[ -f $W/PAUSE ] && ! echo \"\$OUT\" | grep -q '=== XONG'"
rm -f "$F4/FAKE_SSHDROP" "$W/SSH_DOWN"
OUT=$(echo YES | APP_DIR=$F4 SSH_242="bash $W/fakessh.sh" FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" 2>&1)
chk "r4c chay dung lenh rollback tay sau khi ssh lai => xong, PAUSE xoa, c3_shadow" "echo \"\$OUT\" | grep -q 'Rollback xong' && [ ! -f $W/PAUSE ] && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
rm -f "$TG4" "$W/fg.out"
setsid bash -c "echo YES | env APP_DIR=$F4 NJ=$W/new_r4.jar NJ_MD5=$NEW4 PATH=$W/nopy:$PATH PY242=$W/c3py_t/python/bin/python3 EXINFO_CMD='$W/realpy $W/exgen.py $W/exinfo_r4.json' DEPLOY_TG_SINK=$TG4 FORCE=1 FORCE_TIME=1 LATCH_WAIT_S=6 bash $D4" > "$W/fg.out" 2>&1 < /dev/null &
FGP=$!
for i in $(seq 1 60); do grep -q 'job NEN pid=' "$W/fg.out" 2>/dev/null && break; sleep 0.5; done
JP=$(grep -o 'job NEN pid=[0-9]*' "$W/fg.out" | head -1 | cut -d= -f2)
JL=$(grep -o 'job_log=[^ ]*' "$W/fg.out" | head -1 | cut -d= -f2)
kill -HUP -- -$FGP 2>/dev/null; sleep 1; kill -KILL -- -$FGP 2>/dev/null; wait $FGP 2>/dev/null
chk "r4c dong terminal (HUP/KILL ca nhom foreground): job NEN van song" "! kill -0 $FGP 2>/dev/null && [ -n \"$JP\" ] && kill -0 $JP 2>/dev/null"
for i in $(seq 1 120); do kill -0 "$JP" 2>/dev/null || break; sleep 1; done
TS4=$(grep -o 'TS=[0-9_]*' "$JL" | head -1 | cut -d= -f2)
chk "r4c dong terminal: job NEN van chay toi '=== XONG' + Telegram XONG" "grep -q '=== XONG' $JL && grep -q 'XONG TS=$TS4' $TG4"
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" >/dev/null 2>&1
chk "r4c don: 242 gia ve c3_shadow" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
rm -f "$F4/FAKE_R4"
echo "== 24. [V12 R4d] UNIVERSE_A1: env + PRE nguon + PREP + kiem file truoc restart + dong init A1 / so TF trong CHK"
TG4=$W/tg_r4.txt
touch "$F4/FAKE_R4"
OUT=$(r4 DRY=1 bash "$D4" 2>&1)
chk "r4d DRY: ENV_ADD UNIVERSE_A1=1 + UNIVERSE_A1_EXCHANGE_INFO = LIVE_C3_EXCHANGEINFO_FILE; PRE doc nguon du truong" "echo \"\$OUT\" | grep -q 'export UNIVERSE_A1=1' && echo \"\$OUT\" | grep -q 'export UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json' && echo \"\$OUT\" | grep -q 'export LIVE_C3_EXCHANGEINFO_FILE=run/c3live_exchangeInfo.json' && echo \"\$OUT\" | grep -q 'OK exchangeInfo_nguon symbols=223 TradFi=60 onboardDate=223'"
OUT=$(r4 DRY=1 EXINFO_CMD="cat $W/exinfo_r4.json.noob" bash "$D4" 2>&1)
chk "r4d PRE: nguon thieu onboardDate => TU CHOI truoc YES" "echo \"\$OUT\" | grep -q 'FAIL exchangeInfo_nguon' && echo \"\$OUT\" | grep -q 'kiem 242 co muc FAIL' && ! echo \"\$OUT\" | grep -q 'DRY PASS'"
OUT=$(r4 DRY=1 EXINFO_CMD="cat $W/exinfo_r4.json.nost" bash "$D4" 2>&1)
chk "r4d PRE: nguon thieu serverTime => TU CHOI truoc YES" "echo \"\$OUT\" | grep -q 'FAIL exchangeInfo_nguon thieu serverTime'"
cat > "$W/exflaky.sh" <<'EOF'
# nguon gia: 2 lan doc dau (PRE foreground + PRE job) tot, lan 3 (buoc chuan bi) thieu serverTime
n=$(cat "$1/exflaky.n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$1/exflaky.n"
if [ $n -le 2 ]; then "$1/realpy" "$1/exgen.py" "$1/exinfo_r4.json"; else cat "$1/exinfo_r4.json.nost"; fi
EOF
rm -f "$W/exflaky.n"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 EXINFO_CMD="bash $W/exflaky.sh $W" bash "$D4" 2>&1); RC=$?
chk "r4d PREP: exchangeInfo tai ve thieu serverTime => DUNG, env khoi phuc, jar cu, process c3_shadow" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL exchangeInfo thieu serverTime' && ! grep -q UNIVERSE_A1 $F4/conf/env.sh && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $OLD ] && p4env | grep -qx 'LIVE_PROFILE=c3_shadow'"
cat > "$W/fakessh_a1.sh" <<EOF
# ssh GIA: xoa file A1 ngay o buoc kiem truoc restart (gia lap file mat/hong giua chung)
case "\$1" in *PRE_RESTART_A1*) [ -f "$W/A1_GONE" ] && rm -f "$F4/run/c3live_exchangeInfo.json";; esac
exec bash -c "\$1"
EOF
touch "$W/A1_GONE"; P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 SSH_242="bash $W/fakessh_a1.sh" bash "$D4" 2>&1); RC=$?
chk "r4d file A1 mat ngay truoc restart => DUNG TRUOC khi dung bot cu (cung pid), env khoi phuc, khong PAUSE" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL a1_file_thieu' && echo \"\$OUT\" | grep -q 'kiem file A1 truoc restart FAIL (env.sh da khoi phuc)' && ! grep -q UNIVERSE_A1 $F4/conf/env.sh && [ \"\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)\" = \"$P0\" ] && [ ! -f $W/PAUSE ]"
rm -f "$W/A1_GONE"
rm -f "$TG4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?; echo "$OUT" | grep -a 'UNIVERSE_A1\|a1_' | head -4
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4d XONG: kiem truoc restart OK (cung file R7) + CHK thay dong init UNIVERSE_A1 TradFi=60 INDEX=3; process co UNIVERSE_A1=1" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK a1_file symbols=223 TradFi=60' && echo \"\$OUT\" | grep -q 'OK a1_env_cung_file_R7' && echo \"\$OUT\" | grep -q 'OK UNIVERSE_A1 TradFi=60 INDEX=3' && p4env | grep -qx 'UNIVERSE_A1=1' && p4env | grep -qx 'UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json'"
echo x > "$F4/run/ts_ext_daily.csv.a1"
OUT=$(echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" 2>&1)
chk "r4d rollback: env khong con UNIVERSE_A1, file ALT_EW A1 (.a1) doi ten .rb_TS" "echo \"\$OUT\" | grep -q 'Rollback xong' && ! grep -q UNIVERSE_A1 $F4/conf/env.sh && [ -f $F4/run/ts_ext_daily.csv.a1.rb_$TS4 ] && [ ! -f $F4/run/ts_ext_daily.csv.a1 ]"
touch "$F4/FAKE_NOA1"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4d JVM khong in dong init UNIVERSE_A1 => WAIT qua han => ROLLBACK TU DONG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'WAIT UNIVERSE_A1_chua_co_dong_init' && echo \"\$OUT\" | grep -q 'Rollback xong' && ! grep -q UNIVERSE_A1 $F4/conf/env.sh"
rm -f "$F4/FAKE_NOA1"; touch "$F4/FAKE_A1LOW"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4d dong init UNIVERSE_A1 TradFi < 50 => FAIL + ROLLBACK TU DONG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL UNIVERSE_A1 TradFi=10 < 50' && echo \"\$OUT\" | grep -q 'Rollback xong'"
rm -f "$F4/FAKE_A1LOW" "$F4/FAKE_R4"
echo "== 25. [V12 R4e] cron lam moi exchangeInfo (cai / lam moi / hong giu cu / Telegram / CHK file cu / rollback go) + khoa nguyen tu + ssh thu lai"
EXR=$HERE/exinfo_refresh_242.sh
python3 - "$W" <<'EOF'
import json, sys
w = sys.argv[1]
b = json.load(open(w + '/exinfo_r4.json'))
s, st = b['symbols'], b['serverTime']
def dump(n, t, sy):
    json.dump({'serverTime': t, 'symbols': sy}, open(w + '/' + n, 'w'), separators=(',', ':'))
nw = {'symbol': 'NEW1USDT', 'contractType': 'PERPETUAL', 'underlyingType': 'COIN', 'onboardDate': st}
dump('ex_new.json', st + 900000, s + [nw])
dump('ex_noob.json', st + 1800000, [{k: v for k, v in x.items() if k != 'onboardDate'} for x in s])
dump('ex_notnewer.json', st + 900000, s + [nw])
dump('ex_few.json', st + 900000, s[:50])   # [R4n] thay ca 'KHONG moi hon' (R4n bo cong serverTime)
dump('ex_drop.json', st + 2700000, s[:130] + [x for x in s if 'TRADIFI' in x['contractType']])
dump('ex_new2.json', st + 3600000, s + [nw])
EOF
cp "$W/exinfo_r4.json" "$F4/run/c3live_exchangeInfo.json"; rm -f "$F4/run/c3live_exinfo_refresh.state" "$W/tg_exr.txt"
rf() { env PATH="$W/nopy:$PATH" C3PY=$W/c3py_t/python/bin/python3 APP_DIR=$F4 EXR_TG_SINK=$W/tg_exr.txt EXINFO_CMD="cat $1" bash "$EXR" 2>&1; }
XF=$F4/run/c3live_exchangeInfo.json
OUT=$(rf "$W/ex_new.json"); RC=$?
chk "r4e lam moi hop le (serverTime moi hon, listing moi NEW1USDT) => thay file nguyen tu + .lastgood, fails=0" "[ $RC = 0 ] && grep -q NEW1USDT $XF && cmp -s $XF $XF.lastgood && grep -qx 'fails=0' $F4/run/c3live_exinfo_refresh.state && [ ! -f $XF.new ]"
M0=$(md5sum < $XF)
OUT=$(rf "$W/ex_noob.json"); RC=$?
chk "r4e lam moi thieu onboardDate => GIU file cu, fails=1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'thieu onboardDate/underlyingType' && [ \"\$(md5sum < $XF)\" = \"$M0\" ] && grep -qx 'fails=1' $F4/run/c3live_exinfo_refresh.state"
OUT=$(rf "$W/ex_few.json"); RC=$?
chk "r4e lam moi chi 50 symbol => GIU file cu" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'chi 50 symbol' && [ \"\$(md5sum < $XF)\" = \"$M0\" ] && [ ! -f $W/tg_exr.txt ]"
OUT=$(rf "$W/ex_drop.json"); RC=$?
chk "r4e so symbol giam > 10 % => GIU file cu; loi thu 3 lien tiep => Telegram KHAN" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'so symbol giam 224 -> 190' && [ \"\$(md5sum < $XF)\" = \"$M0\" ] && grep -qx 'fails=3' $F4/run/c3live_exinfo_refresh.state && [ \$(grep -c 'KHAN: lam moi exchangeInfo LOI 3 lan' $W/tg_exr.txt) = 1 ]"
OUT=$(rf "$W/khong_co.json"); RC=$?
chk "r4e curl loi / JSON hong lan 4 => giu file cu, KHONG spam Telegram (lan 3, 7, ...)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'JSON hong' && [ \$(grep -c KHAN $W/tg_exr.txt) = 1 ] && [ \"\$(md5sum < $XF)\" = \"$M0\" ]"
OUT=$(rf "$W/ex_new2.json"); RC=$?
chk "r4e hoi phuc => thay file, fails=0, Telegram DA HOI PHUC" "[ $RC = 0 ] && grep -qx 'fails=0' $F4/run/c3live_exinfo_refresh.state && grep -q 'DA HOI PHUC sau 4 lan' $W/tg_exr.txt"
cp "$W/exinfo_r4.json" "$F4/run/c3live_exchangeInfo.json"
touch "$F4/FAKE_R4"; rm -f "$TG4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?; echo "$OUT" | grep -a 'cron\|exchangeInfo_tuoi' | head -4
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4e deploy XONG: cai cron (marker, phut 3,18,41,48, giu dong cron cu), script tren 242 dung md5; CHK file moi < 30' + cron" "[ $RC = 0 ] && grep -q '^3,18,41,48 \* \* \* \* cd $F4 && C3PY=$W/c3py_t/python/bin/python3 /bin/bash $F4/ops/exinfo_refresh_242.sh >> $F4/logs/exinfo_refresh.log 2>&1 # C3LIVE_EXINFO_REFRESH\$' $W/crontab.txt && grep -q '# WATCHDOG' $W/crontab.txt && cmp -s $EXR $F4/ops/exinfo_refresh_242.sh && echo \"\$OUT\" | grep -q 'OK exchangeInfo_tuoi=' && echo \"\$OUT\" | grep -q 'OK cron_lam_moi'"
OUT=$(APP_DIR=$F4 bash "$HERE/c3live_status.sh" 2>&1)
chk "r4e status: tuoi exchangeInfo + trang thai lam moi + cron + [OI-GUARD-2] STALE (INFO)" "echo \"\$OUT\" | grep -q '== exchangeInfo: tuoi=' && echo \"\$OUT\" | grep -q '== cron lam moi: 1 dong' && echo \"\$OUT\" | grep -q 'OI-GUARD-2'"
OUT=$(r4 DRY=1 bash "$D4" 2>&1)
chk "r4e PRE: cron lam moi DA cai => TU CHOI deploy lan 2" "echo \"\$OUT\" | grep -q 'FAIL cron_lam_moi_DA_CO'"
cat > "$W/fakessh_drop.sh" <<EOF
# ssh GIA: N lan dau (file DROPN) loi ket noi rc 255, sau do binh thuong
n=\$(cat "$W/DROPN" 2>/dev/null || echo 0)
if [ "\$n" -gt 0 ]; then echo \$((n - 1)) > "$W/DROPN"; echo "ssh: Connection reset" >&2; exit 255; fi
exec bash -c "\$1"
EOF
echo 2 > "$W/DROPN"
OUT=$(echo YES | APP_DIR=$F4 FORCE_TIME=1 SSH_242="bash $W/fakessh_drop.sh" bash "$HERE/rollback_v12.sh" "$TS4" 2>&1)
chk "r4e rollback: ssh rot 2 lan => thu lai (3 lan) => xong; cron lam moi GO theo marker, dong cron khac GIU" "echo \"\$OUT\" | grep -q 'thu lai' && echo \"\$OUT\" | grep -q 'Rollback xong' && echo \"\$OUT\" | grep -q 'OK cron_lam_moi_da_go' && ! grep -q C3LIVE_EXINFO_REFRESH $W/crontab.txt && grep -q '# WATCHDOG' $W/crontab.txt && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
touch "$F4/FAKE_EXOLD"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4e CHK: file exchangeInfo cu > 30' => FAIL + ROLLBACK TU DONG, cron go" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL exchangeInfo_cu=' && echo \"\$OUT\" | grep -q 'Rollback xong' && ! grep -q C3LIVE_EXINFO_REFRESH $W/crontab.txt"
rm -f "$F4/FAKE_EXOLD" "$F4/FAKE_R4"
LKD=$W/deploylog/.deploy_v12dry_r4.lock.d
bash -c 'exec -a deploy_v12_dry_r4_gia sleep 60' & LP=$!
mkdir -p "$LKD"; echo $LP > "$LKD/pid"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4e khoa nguyen tu: job khac dang giu (pid song) => TU CHOI truoc YES, khong doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'dang co 1 job deploy_v12_dry_r4 khac chay' && ! grep -q LIVE_ADAPTER $F4/conf/env.sh && [ \"\$(cat $LKD/pid)\" = $LP ]"
kill $LP 2>/dev/null; wait $LP 2>/dev/null
OUT=$(echo NO | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4e khoa mo coi (pid chet) => lay lai; tra loi khac YES => huy, khoa duoc xoa" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'khoa mo coi' && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.' && [ ! -e $LKD ]"
echo "== 26. [V12 R4f] MINOR-2: 1 bo kiem exchangeInfo chung (PRE + chuan bi + cron) + lam moi lan dau bat buoc trong buoc 4c"
python3 - "$W" <<'EOF'
import json, sys
w = sys.argv[1]
b = json.load(open(w + '/exinfo_r4.json'))
del b['symbols'][5]['underlyingType']
json.dump(b, open(w + '/ex_1nout.json', 'w'), separators=(',', ':'))
EOF
OUT=$(r4 DRY=1 EXINFO_CMD="cat $W/ex_1nout.json" bash "$D4" 2>&1)
chk "r4f PRE dung bo kiem chung: 1 symbol thieu underlyingType (truoc: NU>0 cho qua) => TU CHOI" "echo \"\$OUT\" | grep -q 'FAIL exchangeInfo_nguon 1 symbol thieu onboardDate/underlyingType' && echo \"\$OUT\" | grep -q 'kiem 242 co muc FAIL'"
OUT=$(r4 DRY=1 EXV_MD5=00000000000000000000000000000000 bash "$D4" 2>&1)
chk "r4f md5 exinfo_validate.py sai => DUNG" "echo \"\$OUT\" | grep -q 'md5 exinfo_validate.py sai'"
chk "r4f exinfo_refresh_242.sh + deploy dung CHUNG exinfo_validate.py (khong con python rieng)" "grep -q 'exinfo_validate.py' $HERE/exinfo_refresh_242.sh && ! grep -q \"<<'PY'\" $HERE/exinfo_refresh_242.sh && grep -qF '\$PY242 -I ops/exinfo_validate.py' $D4"
cat > "$W/exflaky4.sh" <<'EOF'
# nguon gia: 3 lan dau (PRE fg, PRE job, chuan bi) tot; lan 4 (lam moi lan dau trong 4c) thieu serverTime
n=$(cat "$1/exflaky4.n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$1/exflaky4.n"
if [ $n -le 3 ]; then "$1/realpy" "$1/exgen.py" "$1/exinfo_r4.json"; else cat "$1/exinfo_r4.json.nost"; fi
EOF
rm -f "$W/exflaky4.n"; P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 EXINFO_CMD="bash $W/exflaky4.sh $W" bash "$D4" 2>&1); RC=$?
chk "r4f lam moi lan dau trong 4c FAIL => DUNG truoc restart: env khoi phuc, cron go, bot cu giu (cung pid)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL lam_moi_lan_dau rc=1' && ! grep -q UNIVERSE_A1 $F4/conf/env.sh && ! grep -q C3LIVE_EXINFO_REFRESH $W/crontab.txt && grep -q '# WATCHDOG' $W/crontab.txt && [ \"\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)\" = \"$P0\" ]"
touch "$F4/FAKE_R4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4f XONG: lam moi lan dau rc 0 + fails=0, CHK file moi + cron" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK lam_moi_lan_dau rc=0 fails=0' && echo \"\$OUT\" | grep -q 'OK exchangeInfo symbols=223' && grep -qx 'fails=0' $F4/run/c3live_exinfo_refresh.state && cmp -s $HERE/exinfo_validate.py $F4/ops/exinfo_validate.py"
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" >/dev/null 2>&1
chk "r4f rollback: cron go, c3_shadow" "! grep -q C3LIVE_EXINFO_REFRESH $W/crontab.txt && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
rm -f "$F4/FAKE_R4"
echo "== 27. [V12 R4k] 242 KHONG co python3 he thong (CentOS 7): python RIENG /opt/c3py (c3py_install_242.sh) + deploy/cron chi dung duong dan tuyet doi"
CI=$HERE/c3py_install_242.sh
rm -rf "$W/pbs" "$W/opt" "$W/pbscache" "$W/pbscache_x"; mkdir -p "$W/pbs/python/bin" "$W/opt"
printf '#!/bin/sh\nexec %s "$@"\n' "$REALPY" > "$W/pbs/python/bin/python3"; chmod +x "$W/pbs/python/bin/python3"
tar -czf "$W/pbs.tgz" -C "$W/pbs" python
PSHA=$(sha256sum < "$W/pbs.tgz" | cut -c1-64); PVER=$("$REALPY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')
cp "$W/crontab.txt" "$W/crontab.bak27" 2>/dev/null || : > "$W/crontab.bak27"
ci() { env PATH="$W/nopy:$PATH" C3PY_DIR=$W/opt/c3py PBS_URL="file://$W/pbs.tgz" PBS_SHA256=$PSHA PBS_VER=$PVER PBS_CACHE=$W/pbscache EXPECT_ARCH=$(uname -m) "$@"; }
OUT=$(ci DRY=1 bash "$CI" 2>&1); RC=$?
chk "r4k c3py DRY: chua cai => ke hoach, KHONG ghi gi len 242" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'STATE chua_cai' && echo \"\$OUT\" | grep -q 'KET QUA: DRY PASS' && [ -z \"\$(ls -A $W/opt)\" ]"
OUT=$(echo YES | ci PBS_SHA256=1111111111111111111111111111111111111111111111111111111111111111 PBS_CACHE=$W/pbscache_x bash "$CI" 2>&1); RC=$?
chk "r4k c3py sha256 tarball sai => TU CHOI, khong ghi gi len 242" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'sha256 tarball sai' && [ -z \"\$(ls -A $W/opt)\" ] && [ ! -e $W/pbscache_x/pbs.tgz ]"
OUT=$(echo NO | ci bash "$CI" 2>&1); RC=$?
chk "r4k c3py khong go YES => huy, khong ghi gi len 242" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.' && [ -z \"\$(ls -A $W/opt)\" ]"
OUT=$(echo YES | ci bash "$CI" 2>&1); RC=$?; echo "$OUT" | tail -2
chk "r4k c3py cai: sha256 kiem tren 242, python moi chay, marker, doi ten nguyen tu, khong con file tam" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK sha256_tren_242' && echo \"\$OUT\" | grep -q \"OK da_cai $W/opt/c3py ver=$PVER\" && grep -qx \"sha256=$PSHA\" $W/opt/c3py/C3PY_INSTALLED && [ \"\$(ls -A $W/opt)\" = c3py ]"
OUT=$(echo YES | ci bash "$CI" 2>&1); RC=$?
chk "r4k c3py chay lai => DA CAI, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'STATE da_cai' && echo \"\$OUT\" | grep -q 'DA CAI dung ban pin'"
OUT=$(r4 DRY=1 PY242=$W/khong_co/python3 bash "$D4" 2>&1)
chk "r4k PRE: 242 chua co python rieng (PATH khong co python3) => FAIL thieu_python3_rieng, TU CHOI" "echo \"\$OUT\" | grep -q 'FAIL thieu_python3_rieng' && echo \"\$OUT\" | grep -q 'kiem 242 co muc FAIL' && ! echo \"\$OUT\" | grep -q 'DRY PASS'"
OUT=$(r4 DRY=1 PY242=$W/opt/c3py/python/bin/python3 bash "$D4" 2>&1)
chk "r4k PRE: python rieng do c3py_install_242.sh cai, PATH khong co python3 => qua buoc kiem, DRY PASS" "echo \"\$OUT\" | grep -q \"OK python3_rieng $W/opt/c3py/python/bin/python3 $PVER\" && echo \"\$OUT\" | grep -q 'OK exchangeInfo_nguon' && echo \"\$OUT\" | grep -q 'DRY PASS'"
echo "$OUT" | grep -q 'DRY PASS' || echo "$OUT" | grep -a 'FAIL\|DUNG' | head -5
XF=$F4/run/c3live_exchangeInfo.json; cp "$W/exinfo_r4.json" "$XF"; rm -f "$F4/run/c3live_exinfo_refresh.state"; M0=$(md5sum < $XF)
OUT=$(env PATH="$W/nopy:$PATH" C3PY=$W/khong_co/python3 APP_DIR=$F4 EXR_TG_SINK=$W/tg_exr2.txt EXINFO_CMD="cat $W/ex_new.json" bash "$EXR" 2>&1); RC=$?
chk "r4k cron lam moi: python rieng mat => GIU file cu, tinh 1 lan loi (fails=1), khong goi python3 he thong" "[ $RC = 1 ] && [ \"\$(md5sum < $XF)\" = \"$M0\" ] && grep -qx 'fails=1' $F4/run/c3live_exinfo_refresh.state && ! echo \"\$OUT\" | grep -q 'command not found'"
OUT=$(env PATH="$W/nopy:$PATH" C3PY=$W/opt/c3py/python/bin/python3 APP_DIR=$F4 EXR_TG_SINK=$W/tg_exr2.txt EXINFO_CMD="cat $W/ex_new.json" bash "$EXR" 2>&1); RC=$?
chk "r4k cron lam moi: python rieng co => lam moi hop le, fails=0" "[ $RC = 0 ] && grep -q NEW1USDT $XF && grep -qx 'fails=0' $F4/run/c3live_exinfo_refresh.state"
NPC=$(cat "$D4" "$EXR" | grep -v '^[[:space:]]*#' | grep -nE '(^|[^A-Za-z0-9_/.-])python3?([^A-Za-z0-9_.]|$)')
chk "r4k deploy + cron lam moi KHONG goi python theo PATH (chi PY242 / C3PY tuyet doi)" "[ -z \"\$NPC\" ]"
[ -n "$NPC" ] && echo "$NPC" | head -3
printf '3 * * * * x # C3LIVE_EXINFO_REFRESH\n' >> "$W/crontab.txt"
OUT=$(echo YES | ci MODE=remove bash "$CI" 2>&1); RC=$?
chk "r4k c3py go: cron lam moi con cai => TU CHOI, giu nguyen" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'cron lam moi exchangeInfo con cai' && [ -x $W/opt/c3py/python/bin/python3 ]"
cp "$W/crontab.bak27" "$W/crontab.txt"
OUT=$(echo YES | ci MODE=remove bash "$CI" 2>&1); RC=$?
OUT2=$(ci MODE=status bash "$CI" 2>&1)
chk "r4k c3py go (marker cua script) => xoa sach, MODE=status chua_cai" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK da_go' && [ -z \"\$(ls -A $W/opt)\" ] && echo \"\$OUT2\" | grep -q 'STATE chua_cai'"
mkdir -p "$W/opt/c3py"
OUT=$(echo YES | ci MODE=remove bash "$CI" 2>&1); RC=$?
chk "r4k c3py go: thu muc KHONG co marker => KHONG xoa" "[ $RC = 1 ] && [ -d $W/opt/c3py ] && echo \"\$OUT\" | grep -q 'KHONG xoa'"
rm -rf "$W/opt/c3py"
echo "== 28. [V12 R4l] ws_soak_242.sh bai thu ket noi lai cuong buc: jar soak rieng, kiem SOAK_HOURS/FCM, chan song song canary/deploy (DRY)"
WSK=$HERE/ws_soak_242.sh
printf 'fake-soak-r4l' > "$W/fs.jar"; FSM=$(md5sum < "$W/fs.jar" | cut -c1-32); : > "$W/keys.env"; rm -rf "$W/soakrd"
sk() { env SSH_242="bash -c" KEYS_FILE=$W/keys.env JAVA_BIN=true RD=$W/soakrd VTM=$F4 SJ_FC=$W/fs.jar SJ_FC_MD5=$FSM DEPLOY_LOCKD=$W/nolock.d "$@"; }
OUT=$(sk DRY=1 SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 bash "$WSK" 2>&1); RC=$?
chk "r4l soak DRY che do cuong buc: jar soak RIENG (SJ_FC), env SOAK_FORCE_CLOSE_MIN=10 vao lenh chay, KHONG ghi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q \"OK   jar soak $W/fs.jar md5=$FSM\" && echo \"\$OUT\" | grep -q 'SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 LIVE_C3_KEYS_FILE' && echo \"\$OUT\" | grep -q 'DRY=1: chi kiem' && [ ! -e $W/soakrd ]"
OUT=$(sk DRY=1 bash "$WSK" 2>&1)
chk "r4l soak thuong (khong FCM) van dung jar r4j pin + SOAK_FORCE_CLOSE_MIN=0" "echo \"\$OUT\" | grep -q 'jar soak .*_v12_r4j' && echo \"\$OUT\" | grep -q 'SOAK_FORCE_CLOSE_MIN=0 '"
OUT=$(sk DRY=1 SOAK_HOURS=1 SOAK_FORCE_CLOSE_MIN=10 bash "$WSK" 2>&1); RC=$?
chk "r4l SOAK_HOURS=1 < 1.05 h cho 6 lan moi 10' => DUNG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL SOAK_HOURS=1 du cho 6 lan'"
OUT=$(sk DRY=1 SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=abc bash "$WSK" 2>&1); RC=$?
chk "r4l SOAK_FORCE_CLOSE_MIN khong hop le => DUNG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'SOAK_FORCE_CLOSE_MIN=abc khong hop le'"
bash -c 'exec -a deploy_v12_dry_r4_gia sleep 30' & DP=$!
OUT=$(sk DRY=1 SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 bash "$WSK" 2>&1); RC=$?
chk "r4l job deploy dang chay tren Oracle => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL Oracle: khong co job deploy/rollback dang chay (1)'"
kill $DP 2>/dev/null; wait $DP 2>/dev/null
bash -c 'exec -a canary_early_all_gia sleep 30' & CP=$!
OUT=$(sk DRY=1 SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 bash "$WSK" 2>&1); RC=$?
chk "r4l canary dang dieu phoi tren Oracle (cho khung gio, chua co JVM tren 242) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL Oracle: khong co script canary dang chay (1)'"
kill $CP 2>/dev/null; wait $CP 2>/dev/null
mkdir -p "$W/lk.d"; bash -c 'exec -a khoa_deploy_gia sleep 30' & LP=$!; echo $LP > "$W/lk.d/pid"
OUT=$(sk DRY=1 SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 DEPLOY_LOCKD=$W/lk.d bash "$WSK" 2>&1); RC=$?
chk "r4l khoa deploy dry con pid song => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL Oracle: khong co job deploy/rollback dang chay (1)'"
kill $LP 2>/dev/null; wait $LP 2>/dev/null
echo "== 29. [V12 R4m] A1 R4K MIN-1 gate_ratio_live.bin backup/khoi phuc cung TS + MIN-2 PAUSE token cua job tu go (trap / het han)"
GRF=$F4/run/gate_ratio_live.bin
printf 'v11-buffer-quy-uoc-cu' > "$GRF"; G0=$(md5sum < "$GRF" | cut -c1-32)
touch "$F4/FAKE_R4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4m deploy XONG: backup gate_ratio_live.bin NGAY SAU stop v1.1 (md5 ghi kem), PAUSE token cua job, tu go dat lich" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q \"OK backup_gate_ratio md5=$G0\" && [ \"\$(cat $GRF.bak_v12pre_$TS4.md5)\" = $G0 ] && echo \"\$OUT\" | grep -q \"OK watchdog_PAUSE token='C3DEPLOY_V12 TS=$TS4 pid=\" && echo \"\$OUT\" | grep -q 'OK PAUSE_tu_go_sau=' && [ ! -f $W/PAUSE ]"
printf 'v12-dry-quy-uoc-moi' > "$GRF"; G1=$(md5sum < "$GRF" | cut -c1-32)
printf 'hong' > "$GRF.bak_v12pre_$TS4"
OUT=$(APP_DIR=$F4 DRY=1 bash "$HERE/rollback_v12.sh" "$TS4" 2>&1); RC=$?
chk "r4m rollback: backup gate_ratio sai md5 => DUNG, khong doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL gate_ratio_backup_md5=' && [ \"\$(md5sum < $GRF | cut -c1-32)\" = $G1 ] && grep -q LIVE_ADAPTER $F4/conf/env.sh"
printf 'v11-buffer-quy-uoc-cu' > "$GRF.bak_v12pre_$TS4"
OUT=$(echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" 2>&1); RC=$?
chk "r4m rollback: khoi phuc DUNG ban v1.1 (md5 = luc stop v1.1), ban dry doi ten .rb_TS, c3_shadow" "echo \"\$OUT\" | grep -q \"OK gate_ratio_khoi_phuc md5=$G0\" && [ \"\$(md5sum < $GRF | cut -c1-32)\" = $G0 ] && [ \"\$(md5sum < $GRF.rb_$TS4 | cut -c1-32)\" = $G1 ] && echo \"\$OUT\" | grep -q 'Rollback xong' && grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
rm -f "$GRF"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
printf 'v12-dry-moi' > "$GRF"
OUT2=$(echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" 2>&1)
chk "r4m truoc deploy CHUA co gate_ratio => marker NONE; rollback: v1.1 KHONG thay file cua dry (doi ten .rb_TS)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK gate_ratio_chua_co (marker NONE)' && echo \"\$OUT2\" | grep -q 'Rollback xong' && [ ! -f $GRF ] && [ -f $GRF.rb_$TS4 ]"
LKD=$W/deploylog/.deploy_v12dry_r4.lock.d
m2start() {   # deploy that o job NEN, cho LATCH dai de kip giet giua chung
  rm -f "$W/PAUSE"
  setsid bash -c "echo YES | env APP_DIR=$F4 NJ=$W/new_r4.jar NJ_MD5=$NEW4 PATH=$W/nopy:$PATH PY242=$W/c3py_t/python/bin/python3 EXINFO_CMD='$W/realpy $W/exgen.py $W/exinfo_r4.json' DEPLOY_TG_SINK=$TG4 FORCE=1 FORCE_TIME=1 LATCH_WAIT_S=40 WD_PAUSE_MAX_S=$1 bash $D4" > "$W/m2.out" 2>&1 < /dev/null &
  for i in $(seq 1 120); do grep -q '^C3DEPLOY_V12 TS=' "$W/PAUSE" 2>/dev/null && break; sleep 1; done
  sleep 2; JP=$(cat "$LKD/pid" 2>/dev/null)
}
m2start 600
chk "r4m PAUSE mang token CUA job (pid job)" "[ -n \"$JP\" ] && grep -q \"^C3DEPLOY_V12 TS=[0-9_]* pid=$JP \" $W/PAUSE"
kill -TERM -- -"$JP" 2>/dev/null
for i in $(seq 1 30); do kill -0 "$JP" 2>/dev/null || break; sleep 1; done
chk "r4m job bi giet (TERM) giua chung => trap go PAUSE cua job ngay, khoa duoc tra" "! kill -0 $JP 2>/dev/null && [ ! -f $W/PAUSE ] && grep -q 'da go watchdog PAUSE cua job' $W/deploylog/deploy_v12dry_r4_*_job_*.log && [ ! -e $LKD ]"
TSM=$(grep -ho 'TS=[0-9_]*' "$W/m2.out" | head -1 | cut -d= -f2)
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TSM" > /dev/null 2>&1
m2start 8
kill -KILL -- -"$JP" 2>/dev/null; sleep 1
chk "r4m job chet cung (kill -9 / Oracle reboot) => PAUSE con ngay sau do" "! kill -0 $JP 2>/dev/null && grep -q '^C3DEPLOY_V12 TS=' $W/PAUSE"
sleep 12
chk "r4m PAUSE token cua job tu go sau WD_PAUSE_MAX_S (canh tren 242) => watchdog cuu duoc v_t_m" "[ ! -f $W/PAUSE ]"
TSM=$(grep -ho 'TS=[0-9_]*' "$W/m2.out" | head -1 | cut -d= -f2); rm -rf "$LKD"
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TSM" > /dev/null 2>&1
m2start 8
kill -KILL -- -"$JP" 2>/dev/null; sleep 1
echo "C3ROLLBACK_V12 TS=tay t=1" > "$W/PAUSE"   # rollback / nguoi van hanh nhan PAUSE truoc khi het han
sleep 12
chk "r4m PAUSE KHONG con la token cua job (rollback da ghi de) => bo tu go KHONG dung toi" "[ -f $W/PAUSE ] && grep -q '^C3ROLLBACK_V12' $W/PAUSE"
TSM=$(grep -ho 'TS=[0-9_]*' "$W/m2.out" | head -1 | cut -d= -f2); rm -rf "$LKD"
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TSM" > /dev/null 2>&1
rm -f "$W/PAUSE" "$F4/FAKE_R4"
chk "r4m sau MIN-1/2: env c3_shadow" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
echo "== 30. [V12 R4n] A1 R4M MAJ-X: tuoi exchangeInfo theo LUC TAI (sidecar .meta); serverTime cache cu / lui KHONG chan"
python3 - "$W" <<'EOF'
import json, sys, time
w = sys.argv[1]
b = json.load(open(w + '/exinfo_r4.json'))
now = int(time.time() * 1000)
def dump(n, t):
    json.dump({'serverTime': t, 'symbols': b['symbols']}, open(w + '/' + n, 'w'), separators=(',', ':'))
dump('ex_cur80.json', now - 80 * 60000)
dump('ex_old88.json', now - 88 * 60000)
dump('ex_back6.json', now - 88 * 60000 - 6)
dump('ex_30h.json', now - 30 * 3600000)
EOF
XF=$F4/run/c3live_exchangeInfo.json; cp "$W/ex_cur80.json" "$XF"; rm -f "$XF.meta" "$F4/run/c3live_exinfo_refresh.state"
mfa() { sed -n 's/.*"fetchedAtMs":\([0-9]*\).*/\1/p' "$XF.meta"; }
msha() { sed -n 's/.*"sha256":"\([0-9a-f]*\)".*/\1/p' "$XF.meta"; }
mns() { sed -n 's/.*"n_symbols":\([0-9]*\).*/\1/p' "$XF.meta"; }
T0=$(date +%s%3N)
OUT=$(rf "$W/ex_old88.json"); RC=$?
chk "r4n lam moi: serverTime cu 88' (cu hon file hien tai 80') nhung vua tai => DAT; sidecar fetchedAtMs = luc tai, sha256 + n_symbols khop" "[ $RC = 0 ] && cmp -s $XF $W/ex_old88.json && [ \"\$(mfa)\" -ge $T0 ] && [ \"\$(msha)\" = \"\$(sha256sum < $XF | cut -c1-64)\" ] && [ \"\$(mns)\" = 223 ] && ! echo \"\$OUT\" | grep -q CANH_BAO"
OUT=$(rf "$W/ex_back6.json"); RC=$?
chk "r4n lam moi: serverTime LUI 6 ms => DAT (truoc R4n: TRUOT 'KHONG moi hon')" "[ $RC = 0 ] && cmp -s $XF $W/ex_back6.json && [ \"\$(msha)\" = \"\$(sha256sum < $XF | cut -c1-64)\" ] && grep -qx 'fails=0' $F4/run/c3live_exinfo_refresh.state"
OUT=$(rf "$W/ex_30h.json"); RC=$?
chk "r4n serverTime lech 30 h => DAT, CHI canh bao" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'CANH_BAO_serverTime_lech=30'"
M0=$(cat "$XF.meta"); X0=$(md5sum < $XF)
OUT=$(rf "$W/khong_co.json"); RC=$?
chk "r4n lam moi loi => GIU file + sidecar cu (khop nhau), khong de .meta.tmp" "[ $RC = 1 ] && [ \"\$(cat $XF.meta)\" = '$M0' ] && [ \"\$(md5sum < $XF)\" = \"$X0\" ] && [ ! -f $XF.meta.tmp ]"
cat > "$W/fakessh_meta.sh" <<EOF
# ssh GIA: lam lech sidecar ngay o buoc kiem truoc restart
case "\$1" in *PRE_RESTART_A1*) printf '{"fetchedAtMs":1,"sha256":"%064d","n_symbols":1}\n' 0 > "$XF.meta";; esac
exec bash -c "\$1"
EOF
touch "$F4/FAKE_R4"; P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 SSH_242="bash $W/fakessh_meta.sh" bash "$D4" 2>&1); RC=$?
chk "r4n sidecar lech file ngay truoc restart => DUNG truoc khi dung bot cu (env khoi phuc, cung pid)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL a1_meta_thieu_hoac_lech' && ! grep -q UNIVERSE_A1 $F4/conf/env.sh && [ \"\$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)\" = \"$P0\" ]"
rm -f "$XF.meta"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4n deploy XONG: buoc chuan bi ghi sidecar, kiem truoc restart sidecar khop, lam moi lan dau DAT" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK exchangeInfo symbols=223 .*fetchedAtMs=' && echo \"\$OUT\" | grep -q 'OK a1_meta_khop' && echo \"\$OUT\" | grep -q 'OK lam_moi_lan_dau rc=0 fails=0' && [ \"\$(msha)\" = \"\$(sha256sum < $XF | cut -c1-64)\" ]"
OUT=$(APP_DIR=$F4 bash "$HERE/c3live_status.sh" 2>&1)
chk "r4n status in sidecar" "echo \"\$OUT\" | grep -q '== exchangeInfo sidecar (R4n luc tai): {\"fetchedAtMs\"'"
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" > /dev/null 2>&1
rm -f "$F4/FAKE_R4"
chk "r4n rollback xong: c3_shadow" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
echo "== 31. [V12 R4o] C11 (LIVE_SEED_EXCLUDE_DECISION_MIN=1) trong deploy + restart_v12_dry_reseed.sh (seed ADD6 / SEED=none)"
RSH=$HERE/restart_v12_dry_reseed.sh
GRF=$F4/run/gate_ratio_live.bin; printf 'buffer-v11-cu' > "$GRF"
touch "$F4/FAKE_R4"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4o deploy XONG voi env C11: env.sh + process co LIVE_SEED_EXCLUDE_DECISION_MIN=1, khong canh bao race" "[ $RC = 0 ] && grep -qx 'export LIVE_SEED_EXCLUDE_DECISION_MIN=1' $F4/conf/env.sh && echo \"\$OUT\" | grep -q 'OK env LIVE_SEED_EXCLUDE_DECISION_MIN=1'"
# gia lap dry dang chay tren 242 that (deploy 11-03 CHUA co C11): bo dong C11, restart
sed -i '/LIVE_SEED_EXCLUDE_DECISION_MIN/d' $F4/conf/env.sh; (cd $F4 && bin/daemon.sh stop; sleep 1; bin/daemon.sh start)
echo '{"version":1,"latch":"NONE","codes":[]}' > $F4/run/killsw_latch.json
printf 'seed-A-uC-gia' > "$W/seed.bin"; SM=$(md5sum < $W/seed.bin | cut -c1-32); G0=$(md5sum < $GRF | cut -c1-32); E0=$(md5sum < $F4/conf/env.sh)
rs() { env APP_DIR=$F4 NJ_MD5=$NEW4 DEPLOY_TG_SINK=$W/tg_rs.txt POST_WAIT_S=1 POST_ROUNDS=4 WD_PAUSE_MAX_S=300 MIN_MEM_MB=100 "$@"; }
penv() { tr '\0' '\n' < /proc/$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ; }
OUT=$(rs DRY=1 SEED=$W/seed.bin SEED_MD5=$SM bash "$RSH" 2>&1); RC=$?
chk "r4o reseed DRY: ke hoach 4 dong env (C11 + seed tuyet doi + md5), KHONG doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'se THEM vao .* (4 dong)' && echo \"\$OUT\" | grep -q \"export GATE_BUFFER_SEED=$F4/run/gate_seed_v12_$SM.bin\" && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && [ ! -f $F4/run/gate_seed_v12_$SM.bin ]"
OUT=$(rs DRY=1 SEED=$W/seed.bin SEED_MD5=00000000000000000000000000000000 bash "$RSH" 2>&1); RC=$?
chk "r4o seed md5 khac SEED_MD5 => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'md5 seed .* KHAC SEED_MD5'"
OUT=$(rs DRY=1 bash "$RSH" 2>&1); RC=$?
chk "r4o thieu SEED => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'thieu SEED'"
OUT=$(rs DRY=1 NJ_MD5=00000000000000000000000000000000 SEED=none bash "$RSH" 2>&1); RC=$?
chk "r4o jar dang chay khac r4n pin => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL jar_dang_chay_khac'"
echo "$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000') INFO [pool-1] x: [GATE] scale=1.55 n_cand=3 n_rej=2 n_pass=1 FAKEPASS" >> $F4/logs/full.log
OUT=$(rs DRY=1 SEED=$W/seed.bin SEED_MD5=$SM bash "$RSH" 2>&1); RC=$?
chk "r4o ADD6: gate PASS trong 6 h truoc => TU CHOI re-seed (SEED=none van duoc)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL dang_co_dot_sap_6h gate_pass=1' && rs DRY=1 SEED=none bash $RSH 2>&1 | grep -q 'DRY PASS'"
sed -i '/FAKEPASS/d' $F4/logs/full.log
OUT=$(echo NO | rs FORCE_TIME=1 SEED=$W/seed.bin SEED_MD5=$SM bash "$RSH" 2>&1); RC=$?
chk "r4o khong go YES => huy, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ]"
touch $F4/FAKE_SEEDKHAN; P0=$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)
OUT=$(echo YES | rs FORCE_TIME=1 SEED=$W/seed.bin SEED_MD5=$SM bash "$RSH" 2>&1); RC=$?
chk "r4o JVM bao [GATE-SEED] KHAN => ROLLBACK TU DONG: env.sh + gate_ratio (md5) nhu truoc, .seeded doi ten, PAUSE go, dry chay lai khong seed" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL GATE-SEED_KHAN' && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && [ \"\$(md5sum < $GRF | cut -c1-32)\" = $G0 ] && [ ! -f $GRF.seeded ] && [ ! -f $W/PAUSE ] && ! penv | grep -q '^GATE_BUFFER_SEED=' && penv | grep -qx LIVE_ADAPTER=dry"
chk "r4o rollback: Telegram FAIL + ROLLBACK XONG" "grep -q 'ROLLBACK TU DONG XONG' $W/tg_rs.txt"
rm -f $F4/FAKE_SEEDKHAN
OUT=$(echo YES | rs FORCE_TIME=1 SEED=none bash "$RSH" 2>&1); RC=$?
chk "r4o SEED=none: chi them C11 (2 dong), process co C11, khong GATE_BUFFER_SEED, het canh bao race, PAUSE go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK env_them_2_dong' && echo \"\$OUT\" | grep -q 'OK C11_khong_canh_bao_race' && penv | grep -qx LIVE_SEED_EXCLUDE_DECISION_MIN=1 && ! penv | grep -q '^GATE_BUFFER_SEED' && [ ! -f $W/PAUSE ] && echo \"\$OUT\" | grep -q '=== XONG (c11)'"
OUT=$(rs DRY=1 SEED=none bash "$RSH" 2>&1); RC=$?
chk "r4o SEED=none lan 2 (C11 da co) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL C11_da_co'"
G1=$(md5sum < $GRF | cut -c1-32)
OUT=$(echo YES | rs FORCE_TIME=1 SEED=$W/seed.bin SEED_MD5=$SM bash "$RSH" 2>&1); RC=$?
chk "r4o re-seed XONG (C11 da co => chi 3 dong seed): seed md5 tren 242, [GATE-SEED] nap, .seeded md5, env process, backup gate_ratio md5, LEGACY 44, PAUSE go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK env_them_3_dong' && echo \"\$OUT\" | grep -q \"OK seed tren 242 md5=$SM\" && echo \"\$OUT\" | grep -q \"OK GATE-SEED_nap md5=$SM\" && grep -q \"md5=$SM\" $GRF.seeded && penv | grep -qx \"GATE_BUFFER_SEED_MD5=$SM\" && penv | grep -qx LIVE_SEED_EXCLUDE_DECISION_MIN=1 && echo \"\$OUT\" | grep -q 'OK LEGACY_managed=44' && [ \"\$(cat $GRF.bak_reseed_*.md5 | tail -1)\" = $G1 ] && [ ! -f $W/PAUSE ] && grep -q 'XONG .* MODE=seed' $W/tg_rs.txt"
OUT=$(rs DRY=1 SEED=$W/seed.bin SEED_MD5=$SM bash "$RSH" 2>&1); RC=$?
chk "r4o re-seed lan 2 => TU CHOI (env.sh da co GATE_BUFFER_SEED / .seeded)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL env.sh_da_co_GATE_BUFFER_SEED' && echo \"\$OUT\" | grep -q 'FAIL da_co_run/gate_ratio_live.bin.seeded'"
rm -f $F4/FAKE_R4 $F4/run/killsw_latch.json
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" > /dev/null 2>&1
chk "r4o don dep: rollback v1.2 -> c3_shadow" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh && ! grep -q 'GATE_BUFFER_SEED\|LIVE_SEED_EXCLUDE' $F4/conf/env.sh"
echo "== 32. [V12 R4o] go-live tai khoan chinh: golive_check_key / micro_on / pilot_on / legacy_verify / monitor / live_off (GOLIVE_SCENARIO ADD1)"
GD=$W/gates; rm -rf "$GD" "$W/api"; mkdir -p "$GD" "$W/api"
printf 'C3_LIVE_API_KEY=fakekey_%040d\nC3_LIVE_API_SECRET=fakesecret_%040d\n' 1 2 > "$W/keys_c3.env"; chmod 600 "$W/keys_c3.env"
cat > "$W/fakecurl.sh" <<EOF
#!/bin/bash
# curl GIA: doc cau hinh -K - tu stdin, tra fixture theo ten endpoint (khong mang)
cfg=\$(cat); u=\$(printf '%s' "\$cfg" | sed -n 's/^url = "\([^"?]*\).*/\1/p'); n=\${u##*/}
p=\${u%/*}; n2=\${p##*/}_\$n; [ -f "$W/api/\$n2.json" ] && n=\$n2   # [ADD4] fixture theo phien ban (vd v2_account)
printf '%s' "\$cfg" | grep -q 'X-MBX-APIKEY: fakekey_' || { printf '{"code":-2015}\nHTTP=401'; exit 0; }
c=200; [ -f "$W/api/\$n.code" ] && c=\$(cat "$W/api/\$n.code")
printf 'HTTP/1.1 %s\r\nx-mbx-used-weight-1m: %s\r\n\r\n' "\$c" "\$(cat $W/api/weight 2>/dev/null || echo 77)" >&2   # [ADD4] header weight (-D /dev/stderr)
cat "$W/api/\$n.json" 2>/dev/null; printf '\nHTTP=%s' "\$c"
EOF
chmod +x "$W/fakecurl.sh"
api() { printf '%s' "$2" > "$W/api/$1.json"; }
api apiRestrictions '{"ipRestrict":true,"createTime":1,"enableWithdrawals":false,"enableInternalTransfer":false,"permitsUniversalTransfer":false,"enableVanillaOptions":false,"enableReading":true,"enableFutures":true,"enableMargin":false,"enableSpotAndMarginTrading":false}'
POS_LEG='[{"symbol":"AAAUSDT","positionAmt":"10"},{"symbol":"BBBUSDT","positionAmt":"5"},{"symbol":"Z0USDT","positionAmt":"0"}]'
api positionRisk "$POS_LEG"
cat > "$W/fakessh_q.sh" <<'EOF'
#!/bin/bash
# [R4q] ssh GIA: mat ket noi (exit 255) khi co file $SSHQ_DOWN
[ -n "${SSHQ_DOWN:-}" ] && [ -e "$SSHQ_DOWN" ] && { cat > /dev/null; exit 255; }
exec bash -c "$1"
EOF
chmod +x "$W/fakessh_q.sh"
api openOrders '[]'; api openAlgoOrders '[]'
GL() { env C3_ACCOUNT=MAIN CANARY_PAT=canary_early_fake242_NONE APP_DIR=$F4 NJ_MD5=$NEW4 GATE_DIR=$GD KEYS_FILE=$W/keys_c3.env PY242=$W/c3py_t/python/bin/python3 CURL242=$W/fakecurl.sh \
  DEPLOY_TG_SINK=$W/tg_gl.txt POST_WAIT_S=1 POST_ROUNDS=4 MIN_MEM_MB=100 FORCE_TIME=1 WD_PAUSE_MAX_S=300 "$@"; }
penv() { tr '\0' '\n' < /proc/$(pgrep -f 'BinanceOrderTradingManager fake242' | head -1)/environ; }
lgnow() { local l=AAAUSDT,BBBUSDT; [ "$1" = 0 ] && l=""; echo "$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000') INFO [pool-3-thread-1] x: [LEGACY] managed $1: $l" >> $F4/logs/full.log; }
touch "$F4/FAKE_R4"; echo 44 > "$F4/FAKE_LEGACY_N"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?; TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "r4p chuan bi: deploy dry XONG (PUSH=OFF dry giu nguyen)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK push_OFF'"
OUT=$(GL DRY=1 bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "r4p check_key DRY: kiem file key + python, KHONG goi san" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && ! ls $GD/KEY_CHECK_* >/dev/null 2>&1"
OUT=$(GL bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "r4p check_key DAT: enableWithdrawals=false ipRestrict=true enableFutures=true, file ket qua, KHONG in key/secret" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT' && grep -q 'KET QUA: DAT' $GD/KEY_CHECK_*.txt && ! grep -rq 'fakekey_\|fakesecret_' $W/deploylog/golive_check_key_*.log $GD && ! echo \"\$OUT\" | grep -q 'fakesecret_'"
api apiRestrictions '{"ipRestrict":false,"enableWithdrawals":true,"enableFutures":true}'
OUT=$(GL bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "r4p check_key: rut tien BAT + khong gioi han IP => TRUOT (exit 3)" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'KET QUA: TRUOT' && echo \"\$OUT\" | grep -q 'enableWithdrawals=true' && echo \"\$OUT\" | grep -q 'ipRestrict=false'"
echo '{"clusters":[{"symbol":"D01USDT","legs":[1]}]}' > $F4/run/c3live_book.json; BK0=$(md5sum < $F4/run/c3live_book.json)
OUT=$(GL DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on: chua co gate G-MICRO => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'chua co cong G-MICRO'"
printf 'G-MICRO test\njar_md5=00000000000000000000000000000000\n' > $GD/GOLIVE_GATE_MICRO.ok
OUT=$(GL DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on: gate co jar_md5 KHAC jar dang chay => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khong co dong jar_md5'"
printf 'G-MICRO test\njar_md5=%s\n' $NEW4 > $GD/GOLIVE_GATE_MICRO.ok
echo x > $F4/run/KILL_SWITCH
OUT=$(GL DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on: run/KILL_SWITCH dang co => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL khong co run/KILL_SWITCH'"
rm -f $F4/run/KILL_SWITCH; E0=$(md5sum < $F4/conf/env.sh)
OUT=$(GL DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on DRY: ke hoach env live/1000/push/key, KHONG doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'export LIVE_ADAPTER=live' && echo \"\$OUT\" | grep -q 'export C3_CAPITAL=1000' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ]"
touch $F4/FAKE_NORUNTIME
OUT=$(echo YES | GL bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on hau kiem TRUOT, c3 chua co lenh => ROLLBACK ve dry: env.sh + so dry tra lai, PAUSE go" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && [ \"\$(md5sum < $F4/run/c3live_book.json)\" = \"$BK0\" ] && penv | grep -qx LIVE_ADAPTER=dry && [ ! -f $W/PAUSE ]"
chk "r4q micro_on rollback: doc lai 242+san VERDICT=NONE, KILL_SWITCH cua script DAT truoc start roi GO khi rollback" "echo \"\$OUT\" | grep -q 'OK KILL_SWITCH_dat_truoc_start' && echo \"\$OUT\" | grep -q 'VERDICT=NONE' && [ ! -e $F4/run/KILL_SWITCH ]"
rm -f $F4/FAKE_NORUNTIME
lgnow 44; touch $F4/FAKE_SLOWSTART
OUT=$(echo YES | GL bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4q micro_on JVM len CHAM (khong thay process sau start): doc lai sach => ROLLBACK an toan (KILL_SWITCH chan tu dau), 1 process dry" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khong_thay_process_sau_start' && echo \"\$OUT\" | grep -q 'VERDICT=NONE' && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && sleep 13 && [ \"\$(pgrep -fc 'BinanceOrderTradingManager fake242')\" = 1 ] && penv | grep -qx LIVE_ADAPTER=dry && [ ! -e $F4/run/KILL_SWITCH ]"
lgnow 44; touch $F4/FAKE_NORUNTIME; echo "$W/SSHQ_DOWN" > $F4/FAKE_SSHDROP; rm -f $W/SSHQ_DOWN
OUT=$(echo YES | GL SSH_242="bash $W/fakessh_q.sh" SSHQ_DOWN=$W/SSHQ_DOWN SSH_RETRY_S=0 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4q micro_on: ssh 242 MAT sau start + hau kiem truot => khong doc lai duoc => VERDICT=UNKNOWN, KHONG rollback, KILL_SWITCH (dat truoc start) GIU, KHAN exit 2" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'VERDICT=UNKNOWN' && ! echo \"\$OUT\" | grep -q 'ROLLBACK xong' && grep -q '^golive_micro_on ' $F4/run/KILL_SWITCH && penv | grep -qx LIVE_ADAPTER=live && grep -q 'KHAN TS=.* micro_on TRUOT' $W/tg_gl.txt"
rm -f $W/SSHQ_DOWN $F4/FAKE_SSHDROP $F4/FAKE_NORUNTIME $W/PAUSE; lgnow 44
OUT=$(echo YES | GL MODE=dry bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4q don dep sau ssh mat: live_off MODE=dry (vi the chi LEGACY AAA/BBB) ve dry" "[ $RC = 0 ] && penv | grep -qx LIVE_ADAPTER=dry"
rm -f $F4/run/KILL_SWITCH; lgnow 44; touch $F4/FAKE_NORUNTIME
echo "printf '%s' '[{\"symbol\":\"AAAUSDT\",\"positionAmt\":\"10\"},{\"symbol\":\"BBBUSDT\",\"positionAmt\":\"5\"},{\"symbol\":\"C07USDT\",\"positionAmt\":\"3\"}]' > $W/api/positionRisk.json" > $F4/FAKE_APIHOOK
OUT=$(echo YES | GL bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4q micro_on: log/so sach NHUNG vi the san doi sau start => VERDICT=SEEN, KHONG rollback, KILL_SWITCH giu, exit 2" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'VERDICT=SEEN.*vi_the_san_doi' && [ -e $F4/run/KILL_SWITCH ] && penv | grep -qx LIVE_ADAPTER=live"
rm -f $F4/FAKE_NORUNTIME; lgnow 44
OUT=$(GL MODE=dry DRY=1 bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4q live_off MODE=dry: san con vi the C07USDT NGOAI danh sach LEGACY => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL san: 0 vi the ngoai danh sach LEGACY — CO: C07USDT'"
printf 'sym,ts_first_leg\nAAAUSDT,1\n' > $F4/run/c3live_ledger.csv
OUT=$(GL MODE=dry DRY=1 bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4q live_off MODE=dry: vi the tren symbol c3 tung giao dich (ledger, MERGED) => TU CHOI; LIVE_OFF_ACK_SYMS=AAAUSDT,C07USDT => qua" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'CO: AAAUSDT' && GL MODE=dry DRY=1 LIVE_OFF_ACK_SYMS=AAAUSDT,C07USDT bash $HERE/golive_live_off.sh 2>&1 | grep -q 'DRY PASS'"
rm -f $F4/run/c3live_ledger.csv; api positionRisk "$POS_LEG"; lgnow 44
OUT=$(echo YES | GL MODE=dry bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4q don dep: live_off MODE=dry ve dry" "[ $RC = 0 ] && penv | grep -qx LIVE_ADAPTER=dry"
rm -f $F4/run/KILL_SWITCH; lgnow 44; E0=$(md5sum < $F4/conf/env.sh)
OUT=$(echo NO | GL bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on khong go YES => huy" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ]"
OUT=$(echo YES | GL bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on XONG: process live/1000/push/key/C11, so dry doi ten .dry_TS (live bat dau sach), stream + recon + LEGACY 44, PAUSE go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: MICRO-LIVE' && penv | grep -qx LIVE_ADAPTER=live && penv | grep -qx C3_CAPITAL=1000 && penv | grep -qx SHADOW_NO_PUSH=false && penv | grep -qx LIVE_ENTRY_ENABLED=true && penv | grep -qx LIVE_SEED_EXCLUDE_DECISION_MIN=1 && penv | grep -qx LIVE_C3_KEYS_FILE=$W/keys_c3.env && [ ! -f $F4/run/c3live_book.json ] && ls $F4/run/c3live_book.json.dry_* >/dev/null && echo \"\$OUT\" | grep -q 'OK LEGACY_managed=44' && echo \"\$OUT\" | grep -q 'OK user_stream' && [ ! -f $W/PAUSE ] && echo \"\$OUT\" | grep -q 'OK KILL_SWITCH_con' && echo \"\$OUT\" | grep -q 'OK chua_PUSH_ON' && [ ! -e $F4/run/KILL_SWITCH ] && grep -q 'PUSH doi trang thai -> ON' $F4/logs/full.log"
OUT=$(GL bash "$HERE/golive_monitor.sh" 2>&1)
chk "r4p monitor: 1 lenh in TOM TAT adapter=live C3_CAPITAL=1000 push=ON, latch, so c3, RAM" "echo \"\$OUT\" | grep -q 'TOM TAT: adapter=live C3_CAPITAL=1000 push=ON' && echo \"\$OUT\" | grep -q '== may: MemAvailable='"
OUT=$(GL DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4p pilot_on: chua co gate G-PILOT => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'chua co cong G-PILOT'"
printf 'G-PILOT test\njar_md5=%s\nsize=10000\n' $NEW4 > $GD/GOLIVE_GATE_PILOT.ok
OUT=$(GL DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4p pilot_on: gate thieu dong g_exec= (ADD2 G-EXEC o G-PILOT) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'thieu dong g_exec='"
printf 'G-PILOT test\njar_md5=%s\nsize=10000\ng_exec=GREEN test\ng_exit=TRUOT 41 0.6 25/12 test\n' $NEW4 > $GD/GOLIVE_GATE_PILOT.ok
OUT=$(GL DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4q pilot_on: g_exit=TRUOT (ADD3 G-EXIT) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"g_exit='TRUOT\""
printf 'G-PILOT test\njar_md5=%s\nsize=10000\ng_exec=GREEN test\ng_exit=DAT 18 0.92 25/12 test\n' $NEW4 > $GD/GOLIVE_GATE_PILOT.ok
OUT=$(GL DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4p pilot_on: chua co LEGACY_CUT_VERIFIED => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'LEGACY_CUT_VERIFIED.ok DAT'"
OUT=$(GL bash "$HERE/golive_legacy_verify.sh" 2>&1); RC=$?
chk "r4p legacy_verify: con 2 vi the + log managed 44 => TRUOT, khong ghi file" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'POS_NONC3=2' && echo \"\$OUT\" | grep -q 'log_LEGACY_managed=44' && [ ! -f $GD/LEGACY_CUT_VERIFIED.ok ]"
api positionRisk '[{"symbol":"Z0USDT","positionAmt":"0"}]'; api openAlgoOrders '[{"symbol":"L03USDT","clientAlgoId":"web_x1"}]'; lgnow 0
OUT=$(GL bash "$HERE/golive_legacy_verify.sh" 2>&1); RC=$?
chk "r4p legacy_verify: con 1 algo LEGACY => TRUOT" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'ALGO_NONC3=1'"
api openAlgoOrders '[]'
echo '{"clusters":[{"symbol":"C01USDT","legs":[{"cid":"c3-C01USDT-1-0","state":"CONFIRMED","exec_qty":"10"},{"cid":"c3-C01USDT-1-1","state":"CANCELLED","exec_qty":"0"}],"exit_qty":"0"}]}' > $F4/run/c3live_book.json
api positionRisk '[{"symbol":"C01USDT","positionAmt":"15"},{"symbol":"Z0USDT","positionAmt":"0"}]'
OUT=$(GL bash "$HERE/golive_legacy_verify.sh" 2>&1); RC=$?
chk "r4q legacy_verify: LEGACY 5 con sot TREN symbol c3 dang giu (san 15, c3 10) => TRUOT POS_NONC3=1 C01USDT:+5" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'POS_NONC3=1 C01USDT:+5' && [ ! -f $GD/LEGACY_CUT_VERIFIED.ok ]"
api positionRisk '[{"symbol":"C01USDT","positionAmt":"8"}]'
OUT=$(GL bash "$HERE/golive_legacy_verify.sh" 2>&1); RC=$?
chk "r4q legacy_verify: qty c3 VUOT san (so 10, san 8) => TRUOT POS_C3_MISMATCH" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'POS_C3_MISMATCH=1 C01USDT:-2'"
api positionRisk '[{"symbol":"C01USDT","positionAmt":"10"},{"symbol":"Z0USDT","positionAmt":"0"}]'
OUT=$(GL bash "$HERE/golive_legacy_verify.sh" 2>&1); RC=$?
chk "r4p legacy_verify DAT: qty san = qty c3 (C01 10) + 0 lenh/algo ngoai c3 + log managed 0 => ghi LEGACY_CUT_VERIFIED.ok" "[ $RC = 0 ] && grep -q 'KET QUA: DAT' $GD/LEGACY_CUT_VERIFIED.ok"
rm -f $F4/run/c3live_book.json; api positionRisk '[{"symbol":"Z0USDT","positionAmt":"0"}]'
echo 0 > $F4/FAKE_LEGACY_N
OUT=$(echo YES | GL bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4p pilot_on: go YES (khong phai 'YES DA CAT LEGACY') => huy" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.'"
OUT=$(echo 'YES DA CAT LEGACY' | GL bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4p pilot_on XONG: C3_CAPITAL 1000 -> 10000, adapter live giu, so live giu, PAUSE go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: PILOT C3_CAPITAL=10000' && penv | grep -qx C3_CAPITAL=10000 && penv | grep -qx LIVE_ADAPTER=live && [ ! -f $W/PAUSE ]"
printf 'G-PILOT test\njar_md5=%s\nsize=20000\ng_exec=Q4_OWNER test\ng_exit=Q4_OWNER test\n' $NEW4 > $GD/GOLIVE_GATE_PILOT.ok; touch $F4/FAKE_NORUNTIME
OUT=$(echo 'YES DA CAT LEGACY' | GL bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "r4p pilot_on hau kiem TRUOT => ROLLBACK ve C3_CAPITAL cu (10000), adapter live" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong: live C3_CAPITAL=10000' && penv | grep -qx C3_CAPITAL=10000 && penv | grep -qx LIVE_ADAPTER=live"
rm -f $F4/FAKE_NORUNTIME
OUT=$(GL MODE=dry DRY=1 bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4p live_off MODE=dry khi CHUA drain => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL da drain'"
OUT=$(echo YES | GL MODE=drain bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4p live_off drain: dat run/KILL_SWITCH, KHONG restart" "[ $RC = 0 ] && [ -f $F4/run/KILL_SWITCH ] && penv | grep -qx LIVE_ADAPTER=live"
chk "r4p monitor sau drain: push=OFF" "GL bash $HERE/golive_monitor.sh 2>&1 | grep -q 'push=OFF'"
echo '{"clusters":[{"symbol":"C01USDT"}]}' > $F4/run/c3live_book.json
OUT=$(GL MODE=dry DRY=1 bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4p live_off MODE=dry: so c3 con cum => TU CHOI (khong doi adapter khi con vi the)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL so c3 = 0 cum'"
echo '{"clusters":[]}' > $F4/run/c3live_book.json; api openAlgoOrders '[{"symbol":"C01USDT","clientAlgoId":"c3s-C01-1"}]'
OUT=$(GL MODE=dry DRY=1 bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4p live_off MODE=dry: san con algo c3 => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL san: 0 lenh c3'"
api openAlgoOrders '[]'
OUT=$(echo YES | GL MODE=dry bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4p live_off MODE=dry XONG: env dry, so live doi ten .live_TS, KILL_SWITCH giu" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: c3_live ve DRY' && penv | grep -qx LIVE_ADAPTER=dry && ls $F4/run/c3live_book.json.live_* >/dev/null && [ -f $F4/run/KILL_SWITCH ] && [ ! -f $W/PAUSE ]"
echo 44 > $F4/FAKE_LEGACY_N; lgnow 44
OUT=$(GL DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on lan 2: KILL_SWITCH con (tu drain) => TU CHOI cho toi khi go co chu dich" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL khong co run/KILL_SWITCH'"
rm -f $F4/run/KILL_SWITCH; touch $F4/FAKE_NORUNTIME $F4/FAKE_C3EXEC
OUT=$(echo YES | GL bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "r4p micro_on TRUOT khi c3 DA co lenh (audit [C3-LIVE-ORDER]) => VERDICT=SEEN, KHONG ve dry, KILL_SWITCH, KHAN, exit 2" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'VERDICT=SEEN.*audit_lenh_c3=1' && echo \"\$OUT\" | grep -q 'KHONG ve dry' && [ -f $F4/run/KILL_SWITCH ] && penv | grep -qx LIVE_ADAPTER=live && grep -q 'KHAN TS=.* micro_on TRUOT' $W/tg_gl.txt"
rm -f $F4/FAKE_NORUNTIME $F4/FAKE_C3EXEC
OUT=$(echo YES | GL MODE=dry bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "r4p don dep: live_off MODE=dry ve dry" "[ $RC = 0 ] && penv | grep -qx LIVE_ADAPTER=dry"
rm -f $F4/FAKE_R4 $F4/FAKE_LEGACY_N $F4/run/KILL_SWITCH
echo YES | APP_DIR=$F4 FORCE_TIME=1 bash "$HERE/rollback_v12.sh" "$TS4" > /dev/null 2>&1
chk "r4p don dep: rollback v1.2 -> c3_shadow" "grep -qx 'export LIVE_PROFILE=c3_shadow' $F4/conf/env.sh"
echo "== 33. [V12 R4q] swap_v12_dry_jar.sh: thay jar dry r4n -> r4q (C11, khong seed, hau kiem PREMARKET/LEGACY_QUEUE, rollback)"
SW=$HERE/swap_v12_dry_jar.sh
printf 'fake-new-jar-v12r4q' > "$W/new_r4q.jar"; NEWQ=$(md5sum < "$W/new_r4q.jar" | cut -c1-32)
printf '#!/bin/bash\necho "$*" >> %s/reg_calls.txt\n[ -f %s/REG_FAIL ] && exit 3\nexit 0\n' $W $W > $W/fake_register.sh; rm -f $W/reg_calls.txt $W/REG_FAIL
sw() { env OLD_TAG=r4n NEW_TAG=r4q NEED_MGUARD=0 APP_DIR=$F4 OLD_MD5=$NEW4 NJ=$W/new_r4q.jar NJ_MD5=$NEWQ DEPLOY_TG_SINK=$W/tg_sw.txt POST_WAIT_S=1 POST_ROUNDS=4 MIN_MEM_MB=100 FORCE_TIME=1 WD_PAUSE_MAX_S=300 REG_JAR_SH=$W/fake_register.sh "$@"; }
touch "$F4/FAKE_R4"; echo 44 > "$F4/FAKE_LEGACY_N"
OUT=$(echo YES | r4 FORCE=1 FORCE_TIME=1 bash "$D4" 2>&1); RC=$?
chk "r4q swap chuan bi: deploy dry r4n (gia) XONG" "[ $RC = 0 ]"
sed -i '/^export LIVE_SEED_EXCLUDE_DECISION_MIN=1$/d' $F4/conf/env.sh
echo '{"latch":"NONE"}' > $F4/run/killsw_latch.json; [ -s $F4/run/gate_ratio_live.bin ] || printf 'gate0' > $F4/run/gate_ratio_live.bin
J0=$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32); E0=$(md5sum < $F4/conf/env.sh); G0=$(md5sum < $F4/run/gate_ratio_live.bin)
OUT=$(sw DRY=1 bash "$SW" 2>&1); RC=$?
chk "r4q swap DRY=1: kiem 242 chi doc + ke hoach (them C11), KHONG doi jar/env" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'export LIVE_SEED_EXCLUDE_DECISION_MIN=1' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $J0 ] && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ]"
OUT=$(sw OLD_MD5=00000000000000000000000000000000 DRY=1 bash "$SW" 2>&1); RC=$?
chk "r4q swap: jar dang chay KHAC r4n => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL jar_dang_chay'"
OUT=$(sw NJ_MD5=$OLD DRY=1 bash "$SW" 2>&1); RC=$?
chk "r4q swap: md5 jar moi KHAC pin => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHAC pin'"
OUT=$(sw SW_JOB=1 SW_JOBLOG=$W/swjob_fake.log bash "$SW" 2>&1); RC=$?
chk "r4q swap SW_JOB=1 khong co file YES cua foreground => TU CHOI, khong doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG co xac nhan YES' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $J0 ]"
rm -f $W/tok
OUT=$(echo YES | sw FORCE_TIME=0 TIME_OK_FILE=$W/tok WINDOW_WAIT_MAX_S=3 WINDOW_POLL_S=1 bash "$SW" 2>&1); RC=$?
chk "r4q swap: YES -> JOB NEN (job_log + lenh xem tien do); ngoai khung qua tran cho => DUNG, bot KHONG dung, jar/env giu, khoa tra" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'job NEN pid=[0-9]* job_log=' && echo \"\$OUT\" | grep -q 'Xem tien do: tail -f' && echo \"\$OUT\" | grep -q 'cho khung gio qua 3s' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $J0 ] && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && [ ! -e $W/deploylog/.swap_v12_dry_jar.lock.d ]"
touch $F4/FAKE_NORUNTIME
OUT=$(echo YES | sw bash "$SW" 2>&1); RC=$?
chk "r4q swap hau kiem TRUOT => ROLLBACK: jar r4n (md5) + env.sh + gate_ratio khoi phuc, PAUSE go, KHONG dang ky jar parity" "[ $RC = 1 ] && [ ! -e $W/reg_calls.txt ] && echo \"\$OUT\" | grep -q 'ROLLBACK xong' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $J0 ] && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && [ \"\$(md5sum < $F4/run/gate_ratio_live.bin)\" = \"$G0\" ] && [ ! -f $W/PAUSE ] && penv | grep -qx LIVE_ADAPTER=dry"
rm -f $F4/FAKE_NORUNTIME
OUT=$(echo NO | sw bash "$SW" 2>&1); RC=$?
chk "r4q swap khong go YES => huy" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ]"
touch $W/REG_FAIL
OUT=$(echo YES | sw bash "$SW" 2>&1); RC=$?
chk "r4q swap XONG + dang ky jar parity LOI => chi WARN (exit 0, dry r4q giu, KHONG rollback), dang ky dung tham so r4q <jar> <md5> <start_ms 13 so> 1" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'WARN dang ky jar parity LOI rc=3' && ! echo \"\$OUT\" | grep -q 'ROLLBACK TU DONG' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEWQ ] && grep -qE \"^r4q $W/new_r4q.jar $NEWQ [0-9]{13} 1\$\" $W/reg_calls.txt"
# don: ve r4n de chay lai swap XONG (dang ky OK)
(cd $F4 && bin/daemon.sh stop; B=$(ls target/binance-java-sdk-1.2.4.jar.bak_swap_* | grep -v 'md5$' | tail -1); cp -f $B target/binance-java-sdk-1.2.4.jar; F=$(ls conf/env.sh.bak_swap_* | tail -1); cp -f $F conf/env.sh; bin/daemon.sh start) > /dev/null 2>&1
rm -f $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_* $W/REG_FAIL $W/reg_calls.txt; sleep 2
OUT=$(echo YES | sw bash "$SW" 2>&1); RC=$?
chk "r4q swap XONG: jar r4q, backup r4n .bak_swap (md5), C11 trong env process, dry giu, PREMARKET + premarket_bo + LEGACY_QUEUE_LIVE_BLOCK=true, PAUSE go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: dry chay r4q' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEWQ ] && cat $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_*.md5 | grep -qx $J0 && penv | grep -qx LIVE_SEED_EXCLUDE_DECISION_MIN=1 && penv | grep -qx LIVE_ADAPTER=dry && echo \"\$OUT\" | grep -q 'OK GATE-PRE_premarket_bo=1' && echo \"\$OUT\" | grep -q 'OK UNIVERSE-A1_PREMARKET=1' && echo \"\$OUT\" | grep -q 'OK LEGACY_QUEUE_LIVE_BLOCK=true' && [ ! -f $W/PAUSE ] && grep -q 'swap jar dry\] XONG' $W/tg_sw.txt && echo \"\$OUT\" | grep -q 'OK dang ky jar parity r4q start_ms=' && [ \"\$(wc -l < $W/reg_calls.txt)\" = 1 ]"
OUT=$(sw DRY=1 bash "$SW" 2>&1); RC=$?
chk "r4q swap lan 2: jar dang chay DA la r4q => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'DA_LA_moi'"
(cd $F4 && bin/daemon.sh stop; B=$(ls target/binance-java-sdk-1.2.4.jar.bak_swap_* | grep -v 'md5$' | tail -1); cp -f $B target/binance-java-sdk-1.2.4.jar; F=$(ls conf/env.sh.bak_swap_* | tail -1); cp -f $F conf/env.sh; bin/daemon.sh start) > /dev/null 2>&1
rm -f $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_* $W/tok; sleep 2
setsid bash -c "echo YES | env OLD_TAG=r4n NEW_TAG=r4q NEED_MGUARD=0 APP_DIR=$F4 OLD_MD5=$NEW4 NJ=$W/new_r4q.jar NJ_MD5=$NEWQ DEPLOY_TG_SINK=$W/tg_sw.txt POST_WAIT_S=1 POST_ROUNDS=4 MIN_MEM_MB=100 WD_PAUSE_MAX_S=300 REG_JAR_SH=$W/fake_register.sh FORCE_TIME=0 TIME_OK_FILE=$W/tok WINDOW_WAIT_MAX_S=120 WINDOW_POLL_S=1 bash $SW" > "$W/swfg.out" 2>&1 < /dev/null &
FGP=$!
for i in $(seq 1 20); do grep -q 'job_log=' $W/swfg.out 2>/dev/null && break; sleep 1; done
sleep 2; kill -HUP -$FGP 2>/dev/null; kill -KILL -$FGP 2>/dev/null; sleep 1
SJL=$(grep -o 'job_log=[^ ]*' $W/swfg.out | head -1 | cut -d= -f2)
chk "r4q swap dong terminal (HUP/KILL nhom foreground) khi job dang CHO khung gio: job NEN van song" "! kill -0 $FGP 2>/dev/null && [ -n \"$SJL\" ] && grep -q 'cho khung gio hop le' $SJL"
touch $W/tok
for i in $(seq 1 90); do grep -q '=== XONG' $SJL 2>/dev/null && break; sleep 1; done
sleep 1
chk "r4q swap: vao khung => job tu chay tiep (kiem 242 lan 2 + kiem khung NGAY TRUOC stop) toi XONG, jar r4q, khoa tra" "grep -q '=== XONG' $SJL && grep -q 'ngay truoc stop' $SJL && grep -q 'lan 2: OK jar_dang_chay' $SJL && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEWQ ] && [ ! -e $W/deploylog/.swap_v12_dry_jar.lock.d ]"
echo "== 34. [V12 R4r] swap_v12_dry_jar.sh r4q -> r4t (tag mac dinh, hau kiem [MINUTE-GUARD] BAT, rollback khi TAT)"
printf 'fake-new-jar-v12r4q-r4r-r4s-r4t' > "$W/new_r4r.jar"; NEWR=$(md5sum < "$W/new_r4r.jar" | cut -c1-32)
swr() { env APP_DIR=$F4 OLD_MD5=$NEWQ NJ=$W/new_r4r.jar NJ_MD5=$NEWR DEPLOY_TG_SINK=$W/tg_sw.txt POST_WAIT_S=1 POST_ROUNDS=4 MIN_MEM_MB=100 FORCE_TIME=1 WD_PAUSE_MAX_S=300 REG_JAR_SH=$W/fake_register.sh "$@"; }
rm -f $W/reg_calls.txt $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_*; sleep 2
JQ=$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32); EQ=$(md5sum < $F4/conf/env.sh)
OUT=$(swr DRY=1 bash "$SW" 2>&1); RC=$?
chk "r4r swap DRY=1 (tag mac dinh r4q -> r4t): DRY PASS, ke hoach co [MINUTE-GUARD] BAT, khong doi jar/env" "[ $RC = 0 ] && [ $JQ = $NEWQ ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'jar r4q -> r4t' && echo \"\$OUT\" | grep -q '0 KHAN, \[MINUTE-GUARD\] BAT' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $JQ ] && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$EQ\" ]"
echo 'export LIVE_MINUTE_GUARD=0' >> $F4/conf/env.sh
OUT=$(swr DRY=1 bash "$SW" 2>&1); RC=$?
chk "r4r swap: env.sh co LIVE_MINUTE_GUARD=0 => TU CHOI truoc khi dung bot" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL env.sh_LIVE_MINUTE_GUARD=0'"
sed -i '/^export LIVE_MINUTE_GUARD=0$/d' $F4/conf/env.sh
touch $F4/FAKE_MGTAT
OUT=$(echo YES | swr bash "$SW" 2>&1); RC=$?
chk "r4r swap: JVM moi log [MINUTE-GUARD] TAT => FAIL => ROLLBACK ve r4q (md5) + env.sh, KHONG dang ky" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL MINUTE-GUARD_TAT' && echo \"\$OUT\" | grep -q 'ROLLBACK xong' && [ ! -e $W/reg_calls.txt ] && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $JQ ] && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$EQ\" ] && penv | grep -qx LIVE_ADAPTER=dry"
rm -f $F4/FAKE_MGTAT $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_*; sleep 2
echo 45 > $F4/FAKE_LEGACY_N
OUT=$(echo YES | swr bash "$SW" 2>&1); RC=$?
chk "r4r swap: LEGACY TANG sau restart (44 truoc stop -> 45) => FAIL => ROLLBACK, KHONG dang ky" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'LEGACY_TRUOC_STOP=44' && echo \"\$OUT\" | grep -q 'FAIL LEGACY_managed=45 > truoc stop 44' && echo \"\$OUT\" | grep -q 'ROLLBACK xong' && [ ! -e $W/reg_calls.txt ] && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $JQ ]"
rm -f $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_*; echo 43 > $F4/FAKE_LEGACY_N; sleep 2
OUT=$(echo YES | swr bash "$SW" 2>&1); RC=$?
chk "r4r swap XONG (LEGACY truoc stop 45 = log cuoi sau rollback; JVM moi 43 => chi WARN giam): jar r4t, OK MINUTE-GUARD_BAT, backup r4q (md5), dang ky parity 'r4t <jar> <md5> <start_ms> 1', dry giu" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: dry chay r4t' && echo \"\$OUT\" | grep -q 'OK MINUTE-GUARD_BAT' && [ \"\$(md5sum < $F4/target/binance-java-sdk-1.2.4.jar | cut -c1-32)\" = $NEWR ] && cat $F4/target/binance-java-sdk-1.2.4.jar.bak_swap_*.md5 | grep -qx $JQ && grep -qE \"^r4t $W/new_r4r.jar $NEWR [0-9]{13} 1\$\" $W/reg_calls.txt && penv | grep -qx LIVE_ADAPTER=dry && grep -q 'r4q -> r4t' $W/tg_sw.txt && echo \"\$OUT\" | grep -q 'LEGACY_TRUOC_STOP=45' && echo \"\$OUT\" | grep -q 'WARN LEGACY_managed=43 < truoc stop 45'"
echo 44 > $F4/FAKE_LEGACY_N
echo "== 35. [V12 ADD4] TAI KHOAN CON: golive_use_sub_key / check_key SUB / micro_on SUB / pilot_on SUB / monitor SUB (§4 ngoai c3, §5 DD tmb) / live_off SUB / legacy_verify"
GD=$W/gates5; rm -rf "$GD"; mkdir -p "$GD"
cat $HERE/golive_monitor.sh $HERE/golive_lib.sh | md5sum | cut -c1-12 | sed 's/$/ test_fake242 (repo hien tai)/' > $GD/A1_APPROVED_MONITOR.md5
SKEY=fakekey_sub_$(printf '%036d' 7); SK8=$(printf '%s' "$SKEY" | sha256sum | cut -c1-8)
printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=fakesecret_sub_%036d\n' "$SKEY" 9 > $W/sub_src.env; chmod 600 $W/sub_src.env
rm -f $W/keys_sub.env $W/sub_peak.txt $W/tg_sub.txt $F4/run/KILL_SWITCH $F4/run/c3live_book.json $W/PAUSE $F4/FAKE_SCOPE_N
MK0=$(stat -c '%Y %s' $W/keys_c3.env)
GS() { env C3_ACCOUNT=SUB CANARY_PAT=canary_early_fake242_NONE ORA_CRONTAB_CMD="bash $W/oracron.sh" MON_PIN_ROOT=$W/pinned MON_LOCK=$W/locks/golive_monitor.lock APP_DIR=$F4 NJ_MD5=$NEWR GATE_DIR=$GD KEYS_FILE=$W/keys_sub.env PY242=$W/c3py_t/python/bin/python3 CURL242=$W/fakecurl.sh \
  DEPLOY_TG_SINK=$W/tg_sub.txt POST_WAIT_S=1 POST_ROUNDS=4 MIN_MEM_MB=100 FORCE_TIME=1 WD_PAUSE_MAX_S=300 SUB_PEAK_FILE=$W/sub_peak.txt "$@"; }
US() { GS SUB_SRC=$W/sub_src.env SUB_KEY_SHA8=$SK8 MAIN_KEYS_FILE=$W/keys_c3.env KEY_UID=$(id -u) "$@"; }
nosec() { ! echo "$1" | grep -q "$SKEY\|fakesecret_sub" && ! grep -rqs "$SKEY\|fakesecret_sub" $W/deploylog $GD $W/tg_sub.txt; }
ACC_OK='{"totalMarginBalance":"1000.00","availableBalance":"1000.00","assets":[{"asset":"USDT","walletBalance":"1000.00","marginBalance":"1000.00","marginAvailable":true},{"asset":"BTC","walletBalance":"0","marginAvailable":true}]}'
clean() { api account "$ACC_OK"; rm -f $W/api/v2_account.json; api multiAssetsMargin '{"multiAssetsMargin":true}'; api dual '{"dualSidePosition":false}'
  api positionRisk '[{"symbol":"Z0USDT","positionAmt":"0"}]'; api openOrders '[]'; api openAlgoOrders '[]'
  api apiRestrictions '{"ipRestrict":true,"enableWithdrawals":false,"enableFutures":true,"enableReading":true}'; }
clean
OUT=$(US DRY=1 bash "$HERE/golive_use_sub_key.sh" 2>&1); RC=$?
chk "add4 use_sub_key DRY: nguon dat (sha8 khop, 600), in sha8/quyen/mtime, KHONG tao file dich, KHONG lo key/secret" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q \"key_sha8=$SK8\" && [ ! -e $W/keys_sub.env ] && nosec \"\$OUT\""
OUT=$(US SUB_KEY_SHA8=deadbeef DRY=1 bash "$HERE/golive_use_sub_key.sh" 2>&1); RC=$?
chk "add4 use_sub_key: sha8 nguon KHONG khop => DUNG, khong tao dich" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'nguon KHONG dat' && [ ! -e $W/keys_sub.env ]"
OUT=$(echo YES | US bash "$HERE/golive_use_sub_key.sh" 2>&1); RC=$?
chk "add4 use_sub_key: copy -> keys_sub.env (600, giong nguon), keys.env tk chinh KHONG doi, roi check_key SUB DAT (file KEY_CHECK_SUB), khong lo secret" "[ $RC = 0 ] && [ \"\$(stat -c %a $W/keys_sub.env)\" = 600 ] && cmp -s $W/sub_src.env $W/keys_sub.env && [ \"\$(stat -c '%Y %s' $W/keys_c3.env)\" = '$MK0' ] && echo \"\$OUT\" | grep -q 'OK file tk chinh khong doi' && echo \"\$OUT\" | grep -q 'KET QUA: DAT' && grep -q \"KET QUA: DAT\" $GD/KEY_CHECK_SUB_*.txt && grep -q \"key_sha8=$SK8\" $GD/KEY_CHECK_SUB_*.txt && ! ls $W/keys_sub.env.tmp_* >/dev/null 2>&1 && nosec \"\$OUT\""
chk "add4 check_key SUB ghi lai multiAssetsMargin / so du / tai san margin / weight (W_NOMINAL=150, header X-MBX-USED-WEIGHT-1M)" "echo \"\$OUT\" | grep -q 'multiAssetsMargin=true' && echo \"\$OUT\" | grep -q 'so_du=\[USDT:1000.00' && echo \"\$OUT\" | grep -q 'tai_san_margin=\[BTC,USDT\]' && echo \"\$OUT\" | grep -q 'weight fapi danh nghia=150 X-MBX-USED-WEIGHT-1M cuoi=77'"
OUT=$(echo YES | US bash "$HERE/golive_use_sub_key.sh" 2>&1); RC=$?
chk "add4 use_sub_key lan 2: dich da co dung key => KHONG ghi lai, van kiem DAT" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KHONG ghi lai' && cmp -s $W/sub_src.env $W/keys_sub.env"
printf 'C3_LIVE_API_KEY=fakekey_other\nC3_LIVE_API_SECRET=x\n' > $W/keys_sub_o.env; chmod 600 $W/keys_sub_o.env
OUT=$(US KEYS_FILE=$W/keys_sub_o.env DRY=1 bash "$HERE/golive_use_sub_key.sh" 2>&1); RC=$?
chk "add4 use_sub_key: dich DA TON TAI voi key khac => TU CHOI, khong ghi de" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG ghi de' && grep -q fakekey_other $W/keys_sub_o.env"
api positionRisk '[{"symbol":"Q1USDT","positionAmt":"3"},{"symbol":"Z0USDT","positionAmt":"0"}]'; api openOrders '[{"symbol":"Q1USDT","clientOrderId":"web_1"}]'; api openAlgoOrders '[{"symbol":"Q1USDT","clientAlgoId":"c3s-Q1-1"}]'
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: tk con BAN (1 vi the, 1 lenh, 1 algo) => TRUOT exit 3" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'KET QUA: TRUOT' && echo \"\$OUT\" | grep -q 'POS_TOTAL=1' && echo \"\$OUT\" | grep -q 'ORD_TOTAL=1' && echo \"\$OUT\" | grep -q 'ALGO_TOTAL=1'"
clean
printf 'C3_LIVE_API_KEY=badkey_%036d\nC3_LIVE_API_SECRET=badsec\n' 3 > $W/keys_bad.env; chmod 600 $W/keys_bad.env
OUT=$(GS KEYS_FILE=$W/keys_bad.env bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: key SAI (san tra 401) => TRUOT" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'KET QUA: TRUOT' && echo \"\$OUT\" | grep -q 'apiRestrictions_HTTP=401'"
OUT=$(GS MAIN_KEY_SHA8=$SK8 bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: sha8 key = key tk chinh => TRUOT" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'TRUNG_key_tk_chinh'"
api apiRestrictions '{"ipRestrict":false,"enableWithdrawals":true,"enableFutures":false}'
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: khong gioi han IP + rut tien + khong futures => TRUOT ca 3" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'ipRestrict=false' && echo \"\$OUT\" | grep -q 'enableWithdrawals=true' && echo \"\$OUT\" | grep -q 'enableFutures=false'"
clean; api account '{"totalMarginBalance":"999.5","availableBalance":"990","assets":[{"asset":"USDT","walletBalance":"0","marginAvailable":true},{"asset":"BFUSD","walletBalance":"1000.1","marginBalance":"999.5","marginAvailable":false}]}'
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: von BFUSD nhung marginAvailable=false => TRUOT" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'BFUSD=1000.1_marginAvailable=false'"
api account '{"totalMarginBalance":"999.5","availableBalance":"990","assets":[{"asset":"USDT","walletBalance":"0"},{"asset":"BFUSD","walletBalance":"1000.1","marginBalance":"999.5"}]}'
api v2_account '{"assets":[{"asset":"USDT","marginAvailable":true},{"asset":"BFUSD","marginAvailable":true}]}'
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: v3/account thieu marginAvailable => doc them v2/account: BFUSD marginAvailable=true => DAT (weight 155)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'ACC_V2_HTTP=200' && echo \"\$OUT\" | grep -q 'BFUSD=1000.1 marginAvailable=true' && echo \"\$OUT\" | grep -q 'danh nghia=156'"
api v2_account '{"assets":[{"asset":"USDT","marginAvailable":true}]}'
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: BFUSD khong ro marginAvailable (unknown) => TRUOT" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'marginAvailable=unknown'"
clean; api dual '{"dualSidePosition":true}'; api multiAssetsMargin '{"multiAssetsMargin":false}'
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "add4 check_key SUB: dualSidePosition=true => TRUOT; multiAssetsMargin=false CHI ghi lai" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'KET QUA: TRUOT — dualSidePosition=true\. File' && echo \"\$OUT\" | grep -q 'multiAssetsMargin=false'"
clean
cat > $W/oracron.sh <<EOF
# crontab GIA cua user ubuntu tren Oracle (file $W/oracron.txt) — KHONG dung crontab that
case "\$1" in -l) [ -f $W/oracron.txt ] && cat $W/oracron.txt || { echo "no crontab for ubuntu" >&2; exit 1; } ;; -) cat > $W/oracron.txt ;; *) exit 2 ;; esac
EOF
echo '*/5 * * * * /home/ubuntu/ops/health_242.sh # HEALTH' > $W/oracron.txt; rm -f $W/deploylog/golive_monitor.on $W/deploylog/c3sub_monitor_fail.txt
IC() { env ORA_CRONTAB_CMD="bash $W/oracron.sh" MON_LOCK=$W/locks/golive_monitor.lock MON_PIN_ROOT=$W/pinned "$@"; }
printf 'G-MICRO test\njar_md5=%s\n' $NEWR > $GD/GOLIVE_GATE_MICRO.ok
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "C-1 micro_on SUB: CHUA cai cron golive_monitor => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL cron golive_monitor da cai'"
OUT=$(IC DRY=1 bash "$HERE/install_cron_golive_monitor.sh" 2>&1); RC=$?
chk "C-1 install_cron DRY=1: in truoc + sau du kien, KHONG ghi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'crontab TRUOC' && echo \"\$OUT\" | grep -q 'DRY=1: crontab SAU' && ! grep -q golive_monitor $W/oracron.txt"
OUT=$(IC bash "$HERE/install_cron_golive_monitor.sh" 2>&1); RC=$?
chk "C-1 install_cron: 1 dong */2 + flock -n khoa rieng + MONITOR_CRON=1, dong cron khac giu, in truoc/sau" "[ $RC = 0 ] && [ \"\$(grep -c 'golive_monitor (ADD4 C-1)' $W/oracron.txt)\" = 1 ] && grep -qE \"^\*/2 \* \* \* \* /usr/bin/flock -n $W/locks/golive_monitor.lock /usr/bin/timeout -k 10 100 /usr/bin/env MONITOR_CRON=1 /bin/bash $W/pinned/golive_monitor_[0-9a-f]{12}/golive_monitor.sh \" $W/oracron.txt && grep -q '# HEALTH' $W/oracron.txt && ! grep -q oracle_heavy $W/oracron.txt && echo \"\$OUT\" | grep -q 'crontab SAU' && echo \"\$OUT\" | grep -q 'XONG: cai cron'"
C1=$(md5sum < $W/oracron.txt); OUT=$(IC bash "$HERE/install_cron_golive_monitor.sh" 2>&1); RC=$?
chk "C-1 install_cron lan 2: idempotent (KHONG DOI)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KHONG DOI' && [ \"\$(md5sum < $W/oracron.txt)\" = \"$C1\" ]"
PIN1=$(grep -oE "$W/pinned/golive_monitor_[0-9a-f]{12}" $W/oracron.txt | head -1)
chk "delta MIN-4 pin: ban chep monitor + lib = repo, chi doc (444), ten = md5(monitor+lib)[:12]" "[ -n '$PIN1' ] && cmp -s $PIN1/golive_monitor.sh $HERE/golive_monitor.sh && cmp -s $PIN1/golive_lib.sh $HERE/golive_lib.sh && [ \"\$(stat -c %a $PIN1/golive_lib.sh)\" = 444 ] && [ \"\$(cat $HERE/golive_monitor.sh $HERE/golive_lib.sh | md5sum | cut -c1-12)\" = '${PIN1##*_}' ]"
rm -rf $W/monsrc; mkdir -p $W/monsrc; cp $HERE/golive_monitor.sh $HERE/golive_lib.sh $W/monsrc/; echo '# sua thu' >> $W/monsrc/golive_lib.sh
OUT=$(IC MON_SRC=$W/monsrc bash "$HERE/install_cron_golive_monitor.sh" 2>&1); RC=$?
PIN2=$(grep -oE "$W/pinned/golive_monitor_[0-9a-f]{12}" $W/oracron.txt | head -1)
chk "delta MIN-4 chay lai installer sau khi nguon doi => pin MOI, cron tro pin moi (van 1 dong), pin cu giu" "[ $RC = 0 ] && [ -n '$PIN2' ] && [ '$PIN2' != '$PIN1' ] && [ \"\$(grep -c 'golive_monitor (ADD4 C-1)' $W/oracron.txt)\" = 1 ] && [ -d '$PIN1' ] && grep -q '# sua thu' $PIN2/golive_lib.sh"
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1)
chk "delta MIN-4 micro_on: cron chay pin khac repo => WARN cap nhat pin" "echo \"\$OUT\" | grep -q 'WARN cron golive_monitor chay ban pin KHAC repo'"
chmod u+w $PIN2 $PIN2/golive_lib.sh; echo '# hong' >> $PIN2/golive_lib.sh
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "delta MIN-4 micro_on: ban pin bi sua (md5 lech ten) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL cron golive_monitor da cai, ban pin con nguyen'"
IC bash "$HERE/install_cron_golive_monitor.sh" > /dev/null 2>&1
chk "delta MIN-4 cai lai tu repo => cron tro lai pin repo" "grep -qF '$PIN1/golive_monitor.sh' $W/oracron.txt"
OUT=$(IC bash "$HERE/install_cron_golive_monitor.sh" --remove 2>&1); RC=$?
chk "C-1 install_cron --remove: go dong monitor, giu dong khac; --remove lan 2 KHONG DOI" "[ $RC = 0 ] && ! grep -q golive_monitor $W/oracron.txt && grep -q '# HEALTH' $W/oracron.txt && IC bash $HERE/install_cron_golive_monitor.sh --remove 2>&1 | grep -q 'KHONG DOI'"
IC bash "$HERE/install_cron_golive_monitor.sh" > /dev/null 2>&1
mv $GD/A1_APPROVED_MONITOR.md5 $W/appr.bak; echo '000000000000 khac' > $GD/A1_APPROVED_MONITOR.md5
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "A1 errata2 MIN-3 micro_on: md5 monitor+lib KHONG co trong A1_APPROVED_MONITOR.md5 => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL md5 monitor+lib .* da qua A1'"
mv $W/appr.bak $GD/A1_APPROVED_MONITOR.md5
bash -c 'exec -a canary_early_fake242_NONE_run sleep 60' & CPX=$!; sleep 0.3
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "MIN-2 micro_on: co tien trinh canary_early* tren Oracle => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL Oracle: khong co tien trinh canary_early_fake242_NONE dang chay'"
kill $CPX 2>/dev/null; wait $CPX 2>/dev/null
E0=$(md5sum < $F4/conf/env.sh)
OUT=$(echo YES | GS GL_MON_FLAG=/proc/golive_monitor.on bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "delta MIN-2 micro_on: KHONG ghi duoc co monitor => DUNG truoc restart, env khong doi, van dry" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG ghi duoc co monitor' && ! echo \"\$OUT\" | grep -q 'OK da_stop' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && penv | grep -qx LIVE_ADAPTER=dry"
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "add4 micro_on SUB DRY: tk con sach => DRY PASS, env LIVE_C3_KEYS_FILE=keys_sub.env, LEGACY CHI ghi log (khong la dieu kien), khong doi env" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q \"export LIVE_C3_KEYS_FILE=$W/keys_sub.env\" && echo \"\$OUT\" | grep -q 'INFO LEGACY managed=' && ! echo \"\$OUT\" | grep -q 'LEGACY managed doc duoc' && echo \"\$OUT\" | grep -q 'OK   tk con SACH' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && nosec \"\$OUT\""
api positionRisk '[{"symbol":"XYZUSDT","positionAmt":"5"}]'
OUT=$(GS DRY=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "add4 micro_on SUB: tk con co vi the la => TU CHOI truoc khi doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL tk con SACH.*POS_TOTAL=1' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ]"
clean; echo 2 > $F4/FAKE_SCOPE_N
OUT=$(echo YES | GS bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "add4 micro_on SUB: JVM live bao 2 vi the NGOAI c3 tren tk con (scope) => hau kiem FAIL => doc lai NONE => ROLLBACK ve dry" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL scope_tk_con_2_vi_the_ngoai_c3' && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && [ \"\$(md5sum < $F4/conf/env.sh)\" = \"$E0\" ] && penv | grep -qx LIVE_ADAPTER=dry && [ ! -e $F4/run/KILL_SWITCH ]"
chk "C-1 micro_on rollback ve dry => go co monitor" "[ ! -e $W/deploylog/golive_monitor.on ]"
echo 0 > $F4/FAKE_SCOPE_N
rm -f $W/deploylog/run/monitor_heartbeat
OUT=$(echo YES | GS MON_HB_WAIT_S=4 HB_POLL_S=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "delta MIN-3 micro_on: hau kiem DAT nhung KHONG co heartbeat cron monitor trong han => TRUOT => ROLLBACK ve dry, go co" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL monitor_heartbeat_khong_co_trong_4s' && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && penv | grep -qx LIVE_ADAPTER=dry && [ ! -e $W/deploylog/golive_monitor.on ] && [ ! -e $F4/run/KILL_SWITCH ]"
touch -d '1 min ago' $W/deploylog/run/monitor_heartbeat 2>/dev/null || { mkdir -p $W/deploylog/run; touch -d '1 min ago' $W/deploylog/run/monitor_heartbeat; }
OUT=$(echo YES | GS MON_HB_WAIT_S=3 HB_POLL_S=1 bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "delta MIN-3 micro_on: heartbeat CU hon co monitor (khong phai luot cron moi) => khong tinh => TRUOT, rollback" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL monitor_heartbeat_khong_co' && penv | grep -qx LIVE_ADAPTER=dry"
echo '{"clusters":[{"symbol":"D01USDT","legs":[{"cid":"c3-D01USDT-1-0","state":"CONFIRMED","exec_qty":"1"}],"exit_qty":"0"}]}' > $F4/run/c3live_book.json; BKD=$(md5sum < $F4/run/c3live_book.json)
OUT=$(GS bash "$HERE/golive_check_key.sh" 2>&1); RC=$?
chk "errata2 check_key SUB khi adapter=dry: MISMATCH so dry CHI ghi log (gan nhan), ket qua van DAT" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'POS_C3_MISMATCH=1 D01USDT:-1 .*so DRY' && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
echo 'cp "$(ls -t run/c3live_book.json.dry_* | head -1)" run/c3live_book.json' > $F4/FAKE_APIHOOK
OUT=$(echo YES | GS bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "errata2 micro_on: JVM live van mang so dry (leg c3-D01USDT-1-0) => hau kiem FAIL so live khong rong => doc lai NONE (leg cua so dry) => ROLLBACK, so dry tra lai" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL so_live_1_cum' && echo \"\$OUT\" | grep -q 'FAIL 1_leg_so_dry_trong_so_live' && echo \"\$OUT\" | grep -q 'VERDICT=NONE' && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && [ \"\$(md5sum < $F4/run/c3live_book.json)\" = \"$BKD\" ] && penv | grep -qx LIVE_ADAPTER=dry"
rm -f $F4/FAKE_APIHOOK
rm -rf $W/monsrc2; mkdir -p $W/monsrc2; cp $HERE/golive_monitor.sh $HERE/golive_lib.sh $W/monsrc2/; echo '# ban cu (test)' >> $W/monsrc2/golive_monitor.sh
IC MON_SRC=$W/monsrc2 bash "$HERE/install_cron_golive_monitor.sh" > /dev/null 2>&1
( while sleep 1; do [ -f $W/deploylog/golive_monitor.on ] && { mkdir -p $W/deploylog/run; touch $W/deploylog/run/monitor_heartbeat; }; done ) > /dev/null 2>&1 & HBW=$!
OUT=$(echo YES | GS bash "$HERE/golive_micro_on.sh" 2>&1); RC=$?
chk "add4 micro_on SUB XONG: live/1000/push, process doc key keys_sub.env, scope tk con 0, LEGACY 44 chi INFO, KILL_SWITCH go, PUSH ON" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: MICRO-LIVE c3 tai khoan CON' && penv | grep -qx LIVE_ADAPTER=live && penv | grep -qx C3_CAPITAL=1000 && penv | grep -qx LIVE_C3_KEYS_FILE=$W/keys_sub.env && echo \"\$OUT\" | grep -q 'OK env LIVE_C3_KEYS_FILE=' && echo \"\$OUT\" | grep -q 'OK scope_tk_con_0_vi_the_ngoai_c3' && echo \"\$OUT\" | grep -q 'INFO LEGACY_managed=44' && [ ! -e $F4/run/KILL_SWITCH ] && nosec \"\$OUT\""
chk "errata2 micro_on tu PIN lai monitor (cron dang chay ban khac repo) => cron tro ban pin repo, in md5" "grep -qF '$PIN1/golive_monitor.sh' $W/oracron.txt && echo \"\$OUT\" | grep -q 'OK cron golive_monitor chay ban pin md5=${PIN1##*_}'"
chk "errata2 micro_on ghi moc tmb0 = tmb luc bat (1000.00) + C3_CAPITAL=1000; so live rong, 0 leg so dry" "grep -qx 'tmb0=1000.00' $W/deploylog/c3sub_eq_base.txt && grep -qx 'c3_capital=1000' $W/deploylog/c3sub_eq_base.txt && echo \"\$OUT\" | grep -q 'OK so_live_rong' && echo \"\$OUT\" | grep -q 'OK 0_leg_so_dry_trong_so_live'"
chk "A1 errata2 MIN-2 micro_on ghi dry_ts=<TS> vao co micro (pilot_on dung dung so .dry_<TS>)" "grep -q '^dry_ts=[0-9_]*$' $W/deploylog/golive_monitor.on && ls $F4/run/c3live_book.json.dry_\$(sed -n 's/^dry_ts=//p' $W/deploylog/golive_monitor.on) >/dev/null"
chk "C-1 micro_on XONG => co monitor (C3_ACCOUNT=SUB + KEYS_FILE tk con)" "grep -qx C3_ACCOUNT=SUB $W/deploylog/golive_monitor.on && grep -qx KEYS_FILE=$W/keys_sub.env $W/deploylog/golive_monitor.on"
kill $HBW 2>/dev/null; wait $HBW 2>/dev/null; rm -f $W/deploylog/run/monitor_heartbeat
printf '#!/bin/bash\necho x >> %s/sshcnt.log\nexec bash -c "$1"\n' $W > $W/sshcnt.sh; rm -f $W/sshcnt.log $W/moncron.log
mv $W/deploylog/golive_monitor.on $W/mon_on.bak
OUT=$(GS MONITOR_CRON=1 MON_CRON_LOG=$W/moncron.log SSH_242="bash $W/sshcnt.sh" bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "C-1 cron monitor KHONG co co micro/pilot => thoat ngay: 0 ssh (0 call san), khong ghi log" "[ $RC = 0 ] && [ -z \"\$OUT\" ] && [ ! -e $W/sshcnt.log ] && [ ! -e $W/moncron.log ]"
chk "delta MIN-3 cron monitor KHONG co co => KHONG ghi heartbeat" "[ ! -e $W/deploylog/run/monitor_heartbeat ]"
mv $W/mon_on.bak $W/deploylog/golive_monitor.on
PMON=$(grep -oE "$W/pinned/golive_monitor_[0-9a-f]{12}/golive_monitor.sh" $W/oracron.txt | head -1)
OUT=$(GS C3_ACCOUNT=MAIN KEYS_FILE=/khong/co MONITOR_CRON=1 MON_CRON_LOG=$W/moncron.log SSH_242="bash $W/sshcnt.sh" bash "$PMON" 2>&1); RC=$?
chk "C-1 cron monitor CO co: chay, tai khoan + file key lay tu co (SUB, keys_sub), ghi log cron, mon = 90 weight" "[ $RC = 0 ] && [ -z \"\$OUT\" ] && [ -s $W/sshcnt.log ] && grep -q \"TOM TAT: .* tk=SUB key=$SK8 \" $W/moncron.log && grep -q 'W_NOMINAL=90' $W/moncron.log"
chk "delta MIN-3 cron monitor (ban PIN) co co => ghi heartbeat moi" "[ -f $W/deploylog/run/monitor_heartbeat ] && [ \$(( \$(date +%s) - \$(stat -c %Y $W/deploylog/run/monitor_heartbeat) )) -le 30 ]"
OUT=$(APP_DIR=$F4 bash "$HERE/c3live_status.sh" 2>&1); RC=$?
chk "delta MIN-3 c3live_status: co BAT + heartbeat moi => OK" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'monitor ADD4: co BAT, heartbeat'"
touch -d '7 min ago' $W/deploylog/run/monitor_heartbeat
OUT=$(APP_DIR=$F4 bash "$HERE/c3live_status.sh" 2>&1); RC=$?
chk "delta MIN-3 c3live_status: co BAT + heartbeat cu > 6' => KHAN, exit 2" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'KHAN monitor ADD4: .* cu 4[0-9][0-9]s > 360s'"
touch $W/deploylog/run/monitor_heartbeat
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB sach: TOM TAT tk=SUB tmb=1000 dd=0, dinh tmb luu Oracle, KHONG dat KILL_SWITCH" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q \"TOM TAT: adapter=live C3_CAPITAL=1000 push=ON.* tk=SUB key=$SK8 tmb=1000.00 dd=0.0000 khan=0\" && grep -qx 'peak=1000.00' $W/sub_peak.txt && [ ! -e $F4/run/KILL_SWITCH ]"
api account '{"totalMarginBalance":"650","availableBalance":"600","assets":[{"asset":"USDT","walletBalance":"650","marginAvailable":true}]}'
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB DD -35 % (< 40 %): chi in, khong KHAN" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'dd=-0.3500' && [ ! -e $F4/run/KILL_SWITCH ]"
api account '{"totalMarginBalance":"590","availableBalance":"500","assets":[{"asset":"USDT","walletBalance":"590","marginAvailable":true}]}'
OUT=$(GS DRY=1 bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB DRY=1 DD -41 %: KHAN nhung KHONG dat co" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'DRY=1: KHONG dat run/KILL_SWITCH' && [ ! -e $F4/run/KILL_SWITCH ]"
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB DD -41 % cham nguong A40/C6: KHAN + run/KILL_SWITCH (token golive_monitor), Telegram, KHONG dong vi the, push=OFF" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'KHAN (ADD4 tk con): DD_eq=-0.4100' && grep -q '^golive_monitor .* KHAN DD_eq' $F4/run/KILL_SWITCH && grep -q 'KHAN tk con' $W/tg_sub.txt && echo \"\$OUT\" | grep -q 'push=OFF'"
rm -f $F4/run/KILL_SWITCH
BID0=$(sed -n 's/^base_id=//p' $W/deploylog/c3sub_eq_base.txt)
echo 'golive_monitor 1 KHAN DD_eq=-0.4100' > $F4/run/KILL_SWITCH
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" -410 "rut 410 USDT (test)" 2>&1); RC=$?
chk "A1 errata2 MIN-1 rebase: run/KILL_SWITCH do golive_monitor dat => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'do golive_monitor dat' && grep -qx 'tmb0=1000.00' $W/deploylog/c3sub_eq_base.txt"
rm -f $F4/run/KILL_SWITCH
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" -410 2>&1); RC=$?
chk "rebase thieu ly do => DUNG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'can ly do'"
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" "rut 410" 2>&1); RC=$?
chk "rebase thieu / sai so tien delta => DUNG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'can so tien delta'"
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" -300 "rut 300 (khai sai)" 2>&1); RC=$?
chk "A1 errata2 MIN-1 rebase: delta -300 KHONG khop bien dong tmb that (-410, lech > 2 %) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG khop bien dong tmb that' && grep -qx 'tmb0=1000.00' $W/deploylog/c3sub_eq_base.txt"
OUT=$(GS DRY=1 bash "$HERE/golive_rebase_equity.sh" -410 "thu" 2>&1); RC=$?
chk "rebase DRY=1: in moc moi, KHONG ghi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && grep -qx 'tmb0=1000.00' $W/deploylog/c3sub_eq_base.txt"
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" -410 "rut 410 USDT (test)" 2>&1); RC=$?
chk "A1 errata2 MIN-1 rebase -410 (khop tmb 1000 -> 590): tmb0 += delta = 590, base_id + dinh eq GIU (1000), log ly do" "[ $RC = 0 ] && grep -qx 'tmb0=590.00' $W/deploylog/c3sub_eq_base.txt && grep -qx 'c3_capital=1000' $W/deploylog/c3sub_eq_base.txt && grep -qx \"base_id=$BID0\" $W/deploylog/c3sub_eq_base.txt && grep -qx 'peak=1000.00' $W/sub_peak.txt && grep -q 'rut 410 USDT (test)' $W/deploylog/c3sub_eq_base.log"
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "sau rebase: eq = 1000 + (590 - 590) = 1000, dinh giu 1000, het KHAN" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'eq=1000.00 dinh=1000.00 dd=0.0000' && [ ! -e $F4/run/KILL_SWITCH ]"
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" -410 "rut 410 lan 2 (trung)" 2>&1); RC=$?
chk "A1 errata2 MIN-1 rebase lap lai cung delta (khong co bien dong moi sau lan rebase) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG khop' && grep -qx 'tmb0=590.00' $W/deploylog/c3sub_eq_base.txt"
api account '{"totalMarginBalance":"10976.22","availableBalance":"10976.22","assets":[{"asset":"USDT","walletBalance":"1000","marginAvailable":true},{"asset":"BFUSD","walletBalance":"10000","marginAvailable":true}]}'
api assetIndex '{"symbol":"BFUSDUSD","index":"0.99930000","bidRate":"0.95","askRate":"1.05"}'
OUT=$(echo YES | GS bash "$HERE/golive_rebase_equity.sh" 10386.22 "nap BFUSD 10000 + 386 USDT (test)" 2>&1); RC=$?
chk "rebase +10386.22 (nap BFUSD, khop tmb 590 -> 10976.22): tmb0 = 10976.22" "[ $RC = 0 ] && grep -qx 'tmb0=10976.22' $W/deploylog/c3sub_eq_base.txt"
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "errata2 tk con tmb 10976 (BFUSD), C3_CAPITAL 1000: eq = 1000; A1 MIN-4 log gia BFUSD moi luot" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'eq=1000.00 dinh=1000.00 dd=0.0000' && echo \"\$OUT\" | grep -q '== BFUSD: so_du=10000 index=0.99930000 bidRate=0.95'"
api account '{"totalMarginBalance":"10576.22","availableBalance":"10576.22","assets":[{"asset":"USDT","walletBalance":"600","marginAvailable":true},{"asset":"BFUSD","walletBalance":"10000","marginAvailable":true}]}'
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "errata2 c3 lo 400 (tmb chi -3.6 %): eq 600 = -40 % dinh => KHAN + KILL_SWITCH" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'eq=600.00 dinh=1000.00 dd=-0.4000' && echo \"\$OUT\" | grep -q 'KHAN (ADD4 tk con): DD_eq=-0.4000' && grep -q '^golive_monitor .* KHAN DD_eq' $F4/run/KILL_SWITCH"
rm -f $F4/run/KILL_SWITCH; api account '{"totalMarginBalance":"590","availableBalance":"500","assets":[{"asset":"USDT","walletBalance":"590","marginAvailable":true}]}'
printf 'tmb0=590\nc3_capital=1000\nkey_sha8=%s\nbase_id=test_reset_1\nrebase_t=%s\nreason=test dat lai trang thai\n' $SK8 $(date +%s) > $W/deploylog/c3sub_eq_base.txt; rm -f $W/sub_peak.txt
api positionRisk '[{"symbol":"XYZUSDT","positionAmt":"5"},{"symbol":"Z0USDT","positionAmt":"0"}]'
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB: vi the NGOAI c3 tren tk con (khong co trong so) => KHAN + KILL_SWITCH, KHONG tu dong" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'KHAN (ADD4 tk con): POS_NONC3=1:XYZUSDT:+5' && grep -q '^golive_monitor .* KHAN POS_NONC3' $F4/run/KILL_SWITCH"
rm -f $F4/run/KILL_SWITCH; api positionRisk '[{"symbol":"C01USDT","positionAmt":"10"}]'
echo '{"clusters":[{"symbol":"C01USDT","legs":[{"cid":"c3-C01USDT-1-0","state":"SENDING","exec_qty":"0"}],"exit_qty":"0"}]}' > $F4/run/c3live_book.json
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB: vi the c3 dang khop (leg SENDING trong so) => POS_PENDING, KHONG KHAN" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'POS_PENDING=1 C01USDT:+10' && [ ! -e $F4/run/KILL_SWITCH ]"
rm -f $F4/run/c3live_book.json; clean; api account "$ACC_OK"; api openAlgoOrders '[{"symbol":"Q2USDT","clientAlgoId":"web_9"},{"symbol":"C01USDT","clientAlgoId":"c3s-C01-1"}]'
api openOrders '[{"symbol":"C02USDT","clientOrderId":"c3x-C02-1"},{"symbol":"C03USDT","clientOrderId":"c3live-x"}]'
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor SUB: algo cid web_ + lenh cid c3live- (khong phai c3-/c3x-/c3s-) => KHAN; c3s-/c3x- la c3" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'ORD_NONC3=1:C03USDT' && echo \"\$OUT\" | grep -q 'ALGO_NONC3=1:Q2USDT' && echo \"\$OUT\" | grep -q 'ORD_C3=1' && [ -e $F4/run/KILL_SWITCH ]"
rm -f $F4/run/KILL_SWITCH; clean; rm -f $W/sub_peak.txt
printf 500 > $W/api/positionRisk.code; rm -f $W/deploylog/c3sub_monitor_fail.txt $W/mon_frc.txt
for i in 1 2 3 4; do GS bash "$HERE/golive_monitor.sh" > $W/mon_f$i.txt 2>&1; echo $? >> $W/mon_frc.txt; done
chk "MIN-1 monitor doc san loi 4 luot lien tiep: chi CANH BAO, KHONG KILL_SWITCH" "grep -q 'luot loi lien tiep 4/5' $W/mon_f4.txt && [ ! -e $F4/run/KILL_SWITCH ] && [ \"\$(sort -u $W/mon_frc.txt)\" = 0 ]"
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "MIN-1 luot loi thu 5 lien tiep => KHAN + run/KILL_SWITCH + Telegram" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'doc_san_loi_5_luot_lien_tiep' && grep -q '^golive_monitor .* KHAN doc_san_loi_5' $F4/run/KILL_SWITCH && grep -q 'doc_san_loi_5' $W/tg_sub.txt"
rm -f $W/api/positionRisk.code $F4/run/KILL_SWITCH
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "MIN-1 doc lai duoc => bo dem ve 0, khong KHAN" "[ $RC = 0 ] && grep -qx 'n=0' $W/deploylog/c3sub_monitor_fail.txt && [ ! -e $F4/run/KILL_SWITCH ]"
OUT=$(GS MAIN_KEY_SHA8=$SK8 bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "add4 monitor: key doc san co sha8 = key tk chinh => KHAN + KILL_SWITCH" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'key_doc_san_LA_KEY_TK_CHINH' && [ -e $F4/run/KILL_SWITCH ]"
rm -f $F4/run/KILL_SWITCH $W/sub_peak.txt
mv $W/deploylog/c3sub_eq_base.txt $W/eqbase.bak
OUT=$(GS bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "errata2 co micro/pilot BAT ma KHONG co tmb0 => fail-closed: KHAN + KILL_SWITCH" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'KHAN (ADD4 tk con):.*thieu_tmb0' && grep -q '^golive_monitor .* KHAN .*thieu_tmb0' $F4/run/KILL_SWITCH"
mv $W/eqbase.bak $W/deploylog/c3sub_eq_base.txt; rm -f $F4/run/KILL_SWITCH
OUT=$(GS bash "$HERE/golive_legacy_verify.sh" 2>&1); RC=$?
chk "add4 legacy_verify o che do SUB => TU CHOI (ADD4 §3 bo)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'ADD4 §3'"
touch $W/deploylog/run/monitor_heartbeat
printf 'G-PILOT test\njar_md5=%s\nsize=10000\ng_exec=GREEN test\ng_exit=DAT 18 0.92 25/12 test\n' $NEWR > $GD/GOLIVE_GATE_PILOT.ok; echo 44 > $F4/FAKE_LEGACY_N
OUT=$(GS DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "add4 pilot_on SUB DRY: KHONG can LEGACY_CUT_VERIFIED / LEGACY 0 (managed 44), bot dung key tk con, tk con 0 ngoai c3 => DRY PASS" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'BO dieu kien LEGACY_CUT_VERIFIED' && echo \"\$OUT\" | grep -q 'OK   bot live dung key tk con' && [ ! -e $GD/LEGACY_CUT_VERIFIED.ok ]"
bash -c 'exec -a canary_early_fake242_NONE_all sleep 60' & CPX=$!; sleep 0.3
OUT=$(GS DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "MIN-2 pilot_on: co tien trinh canary_early* tren Oracle => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL Oracle: khong co tien trinh canary_early_fake242_NONE'"
kill $CPX 2>/dev/null; wait $CPX 2>/dev/null
touch -d '7 min ago' $W/deploylog/run/monitor_heartbeat
OUT=$(GS DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "delta MIN-3 pilot_on SUB: heartbeat cron monitor cu > 6' => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL heartbeat cron golive_monitor'"
touch $W/deploylog/run/monitor_heartbeat
rm -rf $W/roflag; mkdir -p $W/roflag; cp $W/deploylog/golive_monitor.on $W/roflag/; chmod 555 $W/roflag   # co doc duoc (dry_ts) nhung KHONG ghi duoc
OUT=$(echo 'YES PILOT' | GS GL_MON_FLAG=$W/roflag/golive_monitor.on bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chmod 755 $W/roflag
chk "delta MIN-2 pilot_on: KHONG ghi duoc co monitor => DUNG truoc restart, C3_CAPITAL giu 1000" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG ghi duoc co monitor' && penv | grep -qx C3_CAPITAL=1000"
cp $W/deploylog/golive_monitor.on $W/monon.bak; sed -i '/^dry_ts=/d' $W/deploylog/golive_monitor.on
OUT=$(GS DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "A1 errata2 MIN-2 pilot_on: co micro KHONG co dry_ts => TU CHOI (khong doan so dry bang ls -t)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL co micro/pilot co dry_ts'"
cp $W/monon.bak $W/deploylog/golive_monitor.on
api openOrders '[{"symbol":"Q3USDT","clientOrderId":"web_2"}]'
OUT=$(GS DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "add4 pilot_on SUB: lenh NGOAI c3 tren tk con => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL tk con: 0 vi the / lenh / algo NGOAI c3.*ORD_NONC3=1'"
clean
OUT=$(echo YES | GS bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "add4 pilot_on SUB: go YES (khong phai 'YES PILOT') => huy" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy. Khong doi gi.'"
OUT=$(echo 'YES PILOT' | GS bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "add4 pilot_on SUB XONG: C3_CAPITAL 1000 -> 10000, key tk con giu, LEGACY chi INFO" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: PILOT C3_CAPITAL=10000' && penv | grep -qx C3_CAPITAL=10000 && penv | grep -qx LIVE_C3_KEYS_FILE=$W/keys_sub.env && echo \"\$OUT\" | grep -q 'INFO LEGACY_managed=44'"
chk "errata2 pilot_on ghi lai moc tmb0 + C3_CAPITAL=10000; 0 leg so dry trong so live" "grep -qx 'c3_capital=10000' $W/deploylog/c3sub_eq_base.txt && grep -q 'golive_pilot_on' $W/deploylog/c3sub_eq_base.txt && echo \"\$OUT\" | grep -q 'OK 0_leg_so_dry_trong_so_live'"
chk "A1 errata2 MIN-1 pilot_on reset dinh eq CO CHU DICH: ghi ro trong log moc + Telegram" "grep -q 'RESET dinh eq co chu dich' $W/deploylog/c3sub_eq_base.txt && grep -q 'RESET dinh eq co chu dich' $W/tg_sub.txt"
OUT=$(echo YES | GS MODE=drain bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "add4 live_off SUB drain: dat run/KILL_SWITCH" "[ $RC = 0 ] && [ -e $F4/run/KILL_SWITCH ]"
api positionRisk '[{"symbol":"C05USDT","positionAmt":"2"}]'
OUT=$(GS MODE=dry DRY=1 bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "add4 live_off SUB MODE=dry: tk con con vi the => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL san tk con: 0 vi the (co 1: C05USDT)'"
clean
OUT=$(echo YES | GS MODE=dry bash "$HERE/golive_live_off.sh" 2>&1); RC=$?
chk "add4 live_off SUB MODE=dry XONG: tk con phang => ve DRY (khong can log LEGACY moi / danh sach LEGACY)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG: c3_live ve DRY' && penv | grep -qx LIVE_ADAPTER=dry && ! echo \"\$OUT\" | grep -q 'log \[LEGACY\] managed moi'"
chk "C-1 live_off MODE=dry XONG => go co monitor (cron thoat ngay)" "[ ! -e $W/deploylog/golive_monitor.on ] && ls $W/deploylog/golive_monitor.on.off_* >/dev/null"
chk "add4 khong lo key/secret tk con trong log / gate / Telegram" "nosec ''"
rm -f $F4/run/KILL_SWITCH $F4/FAKE_SCOPE_N
pkill -f 'BinanceOrderTradingManager fake242'
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN)) SKIP=$SKIPN (tong PASS+FAIL+SKIP=$((PASS+FAILN+SKIPN)) co dinh)"
[ $FAILN = 0 ]
