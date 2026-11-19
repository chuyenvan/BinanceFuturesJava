#!/usr/bin/env bash
# =============================================================================
# test_gridtest.sh - [GRIDTEST] chay THU goi ops/c3live/gridtest/ tren "242 GIA" (thu muc tam tren Oracle, process ten RIENG gt_<pid>).
#   KHONG ssh 242, KHONG goi Binance (curl gia + gia mark gia), Telegram GIA (DEPLOY_TG_SINK), crontab GIA. ssh gia tiem loi theo LOAI lenh.
#   bash ops/c3live/test/test_gridtest.sh <thu_muc_tam>     => "TEST PASS n/n" | "TEST FAIL ..."
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd); G=$HERE/gridtest
W=${1:?"thieu thu muc tam"}
case "$W" in *gt_*) ;; *) W=${W%/}_gt_$$;; esac
rm -rf "$W"; mkdir -p "$W"
git -C "$HERE" diff --quiet HEAD -- . || { echo "TEST FAIL: $HERE co sua CHUA commit (m1)"; exit 1; }
export A1_APPROVED_OPS=$W/a1_approved_ops.commit; git -C "$HERE" rev-parse HEAD > "$A1_APPROVED_OPS"
PN="BinanceOrderTradingManager gt_$$"
cleanup() { pkill -9 -f "$PN" 2>/dev/null; pkill -9 -f "gtw_$$" 2>/dev/null; pkill -9 -f "$W/" 2>/dev/null; :; }
trap cleanup EXIT
trap 'exit 130' INT TERM
F=$W/v_t_m; mkdir -p "$F/conf" "$F/bin" "$F/logs" "$F/run" "$F/target" "$W/deploylog" "$W/gates" "$W/locks" "$W/fk"
printf 'C3_LIVE_API_KEY=gtfakekey0123456789abcdef\nC3_LIVE_API_SECRET=gtfakesecret0123456789\n' > $W/keys_sub.env; chmod 600 $W/keys_sub.env
SK8=$(printf %s gtfakekey0123456789abcdef | sha256sum | cut -c1-8)
cat > $W/env0.sh <<EOF
export LIVE_PROFILE=c3_live
export LIVE_KILLSW_MODE=act
export LIVE_GATE_ROLLING_MODE=ratio
export LIVE_GATE_ROLLING_PCT=0.999950829
export SELECTOR_RANK_TOPK=24
# [v1.2 golive_micro_on 20261119_093053] MICRO-LIVE
export LIVE_ADAPTER=live
export C3_CAPITAL=1000
export SHADOW_NO_PUSH=false
export LIVE_ENTRY_ENABLED=true
export LIVE_C3_KEYS_FILE=$W/keys_sub.env
export C3_EXCLUDE_LEGACY_HELD=false
export LIVE_APPLY_GRID_RATIO=true
export LIVE_DCA_GRID_ENABLED=true
EOF
chmod 640 $W/env0.sh; cp -p $W/env0.sh $F/conf/env.sh; E0=$(md5sum < $W/env0.sh | cut -c1-32)
echo 'NEWJAR hotfixks gt' > $W/new.jar; echo 'OLDJAR r4u3fin2 gt' > $W/old.jar; chmod 600 $W/*.jar
NEW=$(md5sum < $W/new.jar | cut -c1-32); cp -p $W/new.jar $F/target/binance-java-sdk-1.2.4.jar
cat > "$F/bin/daemon.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")/.."
PN=$(cat FAKE_PN)
case "$1" in
  stop) [ -f FAKE_NOSTOP ] && exit 0; pkill -f "$PN"; pkill -f "gtw_$(cat FAKE_TID)"; sleep 0.3; pkill -9 -f "$PN"; pkill -9 -f "gtw_$(cat FAKE_TID)"; : ;;
  start)
    ISTEST=0; grep -q '^export LIVE_GATE_ROLLING_PCT=0.99$' conf/env.sh && ISTEST=1
    [ "$ISTEST" = 1 ] && [ -f FAKE_NOSTART_IF_TEST ] && exit 0
    set -a; . conf/env.sh; set +a; export PN; FDJ=target/binance-java-sdk-1.2.4.jar; export FDJ
    nohup bash -c 'exec 3<"$FDJ"; exec -a "$PN" sleep 900' >/dev/null 2>&1 &
    sleep 1
    D=$(date '+%d/%m/%Y %H:%M:%S.000')
    LV=${DCA_GRID_LEVELS:-"-0.5,-0.75,-0.9"}; LV="[$(echo "$LV" | sed 's/,/, /g')]"
    PUSHV=OFF; [ ! -e run/KILL_SWITCH ] && PUSHV=ON
    {
      echo "$D INFO [main] x: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager"
      echo "$D WARN [main] x: [LIVE_PROFILE=c3_live] BAT PUSH=$PUSHV"
      echo "$D WARN [main] c.b.c.a.o.e.LiveGateRollingRatio: *** [GATE-RATIO] LIVE BAT: mode=ratio pct=$(printf '%.8f' "$LIVE_GATE_ROLLING_PCT") window=90d file=run/gate_ratio_live.bin ***"
      echo "$D INFO [x] x: [LIVE-DCA-GRID] LIVE_DCA_GRID_ENABLED=true profileC3=true levels=$LV legs=3 weights=[1.0, 1.0, 1.0, 1.0] scale=6.0 applyRatio=true"
      echo "$D WARN [x] x: [C3-LIVE] khoi dong adapter=LIVE gateway=c3scope(live) book=run/c3live_book.json cum=0 c3_capital=${C3_CAPITAL:-?}.0 tai_khoan=CHINH(pham vi c3) killSwitchArmed=true"
      echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-SCOPE] LEGACY tren tai khoan chinh: 0 vi the (foreign DA BIET)"
      echo "$D INFO [C3LIVE-STREAM] x: [C3-LIVE-STREAM] da ket noi"
      echo "$D INFO [main] x: [C3-LIVE-RECON] khoi dong: ok=true closedWhileDown=[]"
      echo "$D INFO [pool-3-thread-1] x: [LEGACY] managed 44: AAAUSDT,BBBUSDT"
      [ "$ISTEST" = 1 ] && [ -f FAKE_KHAN_IF_TEST ] && echo "$D ERROR [x] x: [C3-LIVE] KHAN gia 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef012 signature=deadbeef01"
    } >> logs/full.log
    if [ "$PUSHV" = OFF ] && [ ! -f FAKE_NOPUSHON ]; then
      nohup bash -c 'echo gtw_$(cat FAKE_TID) >/dev/null; for i in $(seq 1 300); do sleep 1; [ -e run/KILL_SWITCH ] || { echo "$(date "+%d/%m/%Y %H:%M:%S.000") WARN [x] x: [C3-LIVE] PUSH doi trang thai -> ON (x)" >> logs/full.log; exit 0; }; done' "gtw_$(cat FAKE_TID)" >/dev/null 2>&1 &
    fi ;;
esac
EOF
chmod +x "$F/bin/daemon.sh"; echo "$PN" > "$F/FAKE_PN"; echo "$$" > "$F/FAKE_TID"
cat > $W/fakessh.sh <<'EOF'
#!/usr/bin/env bash
T=$(mktemp "$FAKESSH_PLAN.cmd.XXXXXX"); printf '%s' "$*" > "$T"; exec bash "${FAKESSH_PLAN%/*}/fakessh2.sh" "$T"
EOF
cat > $W/fakessh2.sh <<'EOF'
#!/usr/bin/env bash
CF=$1; CMD=$(cat "$CF"); rm -f "$CF"; IN=""; [ -t 0 ] || IN=$(cat)
C=OTHER
case "$IN" in *END_RS*) C=RESTART;; *END_RB*) C=RESTORE;; *END_CHK*) C=CHK;; *END_STATE*) C=STATE;; *END_GX*) C=GX;; *END_API*) C=API;; *END_W*) C=WATCH;; *END_R*) C=REPORT;; esac
[ "$C" = OTHER ] && case "$CMD" in *END_PHASE*) C=PHASE;; *gridtest_base_*) C=BASE;; *"base64 -d"*) C=NEWMD5;; *"PUSH doi trang thai"*) C=PUSHWAIT;; *KILL_SWITCH.ok_*) C=KSOFF;; *"gridtest_watch "*) C=BRAKE;; esac
echo "$C" >> "${FAKESSH_PLAN}.log"
M=""; if [ -f "$FAKESSH_PLAN" ]; then
  L=$(grep -m1 "^$C " "$FAKESSH_PLAN"); if [ -n "$L" ]; then set -- $L; n=$3
    if [ "$n" -gt 0 ]; then M=$2; sed -i "0,/^$C .*/s//$C $2 $((n - 1))/" "$FAKESSH_PLAN"; fi; fi; fi
[ "$M" = before ] && exit 255
if [ "$M" = hup ]; then
  printf '%s' "$IN" > "$CF.in"; setsid bash -c "bash -c \"\$0\" < \"\$1\" > /dev/null 2>&1" "$CMD" "$CF.in" & HP=$!
  sleep 3; kill -HUP -- -$HP 2>/dev/null; exit 255
fi
printf '%s' "$IN" | bash -c "$CMD"; rc=$?
[ "$M" = after ] && exit 255
exit $rc
EOF
cat > $W/fakecurl.sh <<'EOF'
#!/usr/bin/env bash
cfg=$(cat); url=$(printf '%s\n' "$cfg" | sed -n 's/^url = "\(.*\)"$/\1/p'); p=${url#https://*/}; p=/${p%%\?*}
case "$p" in
  /fapi/v3/account) echo '{"totalMarginBalance":"1000.0","availableBalance":"1000.0","assets":[{"asset":"BFUSD","walletBalance":"1000","marginBalance":"999","marginAvailable":true}]}';;
  /fapi/v3/positionRisk) cat "$FAKE_DIR/pos.json";;
  /fapi/v1/openOrders) cat "$FAKE_DIR/ord.json";;
  /fapi/v1/openAlgoOrders) cat "$FAKE_DIR/algo.json";;
  /fapi/v1/multiAssetsMargin) echo '{"multiAssetsMargin":true}';;
  /fapi/v1/positionSide/dual) echo '{"dualSidePosition":false}';;
  /fapi/v1/assetIndex) echo '[{"index":"0.999","bidRate":"0.99"}]';;
  *) echo '{}';;
esac
printf '\nHTTP=200'
EOF
cat > $W/fakecron.sh <<'EOF'
#!/usr/bin/env bash
case "$1" in -l) cat "$FAKE_DIR/crontab.txt" 2>/dev/null;; -) cat > "$FAKE_DIR/crontab.txt";; esac
EOF
chmod +x $W/fakecurl.sh $W/fakecron.sh
MP=$W/pinned; M12=$(cat $HERE/golive_monitor.sh $HERE/golive_lib.sh | md5sum | cut -c1-12); mkdir -p $MP/golive_monitor_$M12
cp $HERE/golive_monitor.sh $HERE/golive_lib.sh $MP/golive_monitor_$M12/
MONLINE="*/2 * * * * /usr/bin/flock -n /x/golive_monitor.lock /usr/bin/timeout -k 10 100 /usr/bin/env MONITOR_CRON=1 /bin/bash $MP/golive_monitor_$M12/golive_monitor.sh >/dev/null 2>&1 # golive_monitor (ADD4 C-1)"
touch $W/sshplan
export DEPLOY_TG_SINK=$W/tg.txt LOGDIR=$W/deploylog GATE_DIR=$W/gates APP_DIR=$F PROC_PAT="$PN" WD_PAUSE=$W/wd/PAUSE \
  SSH_242="bash $W/fakessh.sh" FAKESSH_PLAN=$W/sshplan KEYS_FILE=$W/keys_sub.env SUB_KEY_SHA8=$SK8 C3_ACCOUNT=SUB \
  CANARY_PAT=canary_early_gt_NONE_$$ ING_PAT=gt_no_ingestor_$$ POST_WAIT_S=1 POST_ROUNDS=5 SSH_RETRY_S=0 FORCE_TIME=1 \
  GL_MON_FLAG=$W/mon.on MON_HB_FILE=$W/hb ORA_CRONTAB_CMD=$W/fakecron.sh FAKE_DIR=$W/fk PY242=$(command -v python3) CURL242=$W/fakecurl.sh \
  GT_JAR_MD5=$NEW GT_MIN_UP_S=0 GT_SDIR=$W/gt GT_LOCKD=$W/locks GT_PRICE_CMD="cat $W/fk/prices.json" SJ_WD_LOCK_WAIT_S=20
mkdir -p $W/wd
N=0; P=0; FAILS=""
chk() { N=$((N + 1)); if eval "$2"; then P=$((P + 1)); echo "PASS $N $1"; else FAILS="$FAILS #$N"; echo "FAIL $N $1"; echo "$OUT" | tail -30 | sed 's/^/     | /'; fi; }
np() { pgrep -fc "$PN"; }
pid() { pgrep -f "$PN" | head -1; }
penv() { tr '\0' '\n' < /proc/$(pid)/environ 2>/dev/null; }
em5() { md5sum < $F/conf/env.sh | cut -c1-32; }
nosec() { ! printf '%s' "$1" | grep -q 'gtfakekey\|gtfakesecret\|ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef012\|signature=deadbeef'; }
st() { sed -n "s/^$1=//p" $W/gt/state.env 2>/dev/null | tail -1; }
logl() { echo "$(date '+%d/%m/%Y %H:%M:%S.000') $*" >> $F/logs/full.log; }
submit() { logl "INFO [T] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT $1 $2 SUBMITTED cid=c3-$1-29900000-$3 qty=100 budget=$4 legIdx=$3 notional=$5 U_before=$6"; }
reset_all() {   # bot chay env goc, jar hotfix, khong KS/PAUSE/state/cum; crontab = monitor
  bash $F/bin/daemon.sh stop; sleep 0.5; rm -f $F/run/KILL_SWITCH* $W/wd/PAUSE $F/FAKE_* $F/run/c3live_book.json $F/run/.gridtest_* $F/conf/env.sh.* 2>/dev/null
  echo "$PN" > "$F/FAKE_PN"; echo "$$" > "$F/FAKE_TID"; cp -p $W/env0.sh $F/conf/env.sh; cp -p $W/new.jar $F/target/binance-java-sdk-1.2.4.jar
  echo '{"latch":"NONE"}' > "$F/run/killsw_latch.json"; rm -rf $W/gt; : > $W/sshplan; : > $W/tg.txt; : > $F/logs/full.log
  echo '[]' > $W/fk/pos.json; echo '[]' > $W/fk/ord.json; echo '[]' > $W/fk/algo.json; echo '[]' > $W/fk/prices.json
  echo "$MONLINE" > $W/fk/crontab.txt; touch $W/mon.on $W/hb
  bash $F/bin/daemon.sh start; sleep 1; }
tree_sig() { (cd $F && find . -type f ! -path './logs/*' -printf '%p %s %T@\n' | sort | md5sum); }
ON() { OUT=$(echo YES | DRY=0 bash $G/gridtest_on.sh 2>&1); RC=$?; }
book1() { printf '{"version":1,"clusters":[{"symbol":"AAAUSDT","ts_first_leg":1,"armed":%s,"exit_qty":"0","legs":[{"cid":"c3-AAAUSDT-29900000-0","leg_idx":0,"state":"CONFIRMED","exec_qty":"%s","avg_px":"%s"}]}]}' "${3:-false}" "$1" "$2" > $F/run/c3live_book.json; }
# ===================================================== 1 DRY on
reset_all; T0=$(tree_sig); P0=$(pid)
OUT=$(bash $G/gridtest_on.sh 2>&1); RC=$?
chk "on DRY mac dinh: DRY PASS, 242 khong doi (file/process/env), khong PAUSE, khong state, khong cron watch, khong lo key" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \"\$(tree_sig)\" = '$T0' ] && [ \"\$(pid)\" = '$P0' ] && [ ! -e $W/wd/PAUSE ] && [ \"\$(em5)\" = $E0 ] && [ -z \"\$(st GT_PHASE)\" ] && ! grep -q GRIDTEST_WATCH $W/fk/crontab.txt && nosec \"\$OUT\""
# ===================================================== 2-12 tu choi
refuse() {   # $1 mo ta  $2 lenh chuan bi  $3 grep thong diep
  reset_all; eval "$2"; local p0 e1; p0=$(pid); e1=$(em5)
  ON; chk "on TU CHOI: $1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q -- \"$3\" && [ \"\$(pid)\" = '$p0' ] && [ \"\$(em5)\" = '$e1' ] && [ ! -e $W/wd/PAUSE.x ] && ! grep -q GRIDTEST_WATCH $W/fk/crontab.txt && [ -z \"\$(ls $F/conf/env.sh.gridtest_base_* 2>/dev/null)\" ]"
}
refuse "jar dang chay = jar cu (deadlock)" "cp -p $W/old.jar $F/target/binance-java-sdk-1.2.4.jar; bash $F/bin/daemon.sh stop; sleep 0.3; bash $F/bin/daemon.sh start; sleep 1" "FAIL jar FILE"
refuse "process chay < 6 h" "export GT_MIN_UP_S=99999" "FAIL process chay"; export GT_MIN_UP_S=0
refuse "KILL_SWITCH cua owner dang dat (giu nguyen)" "echo 'golive_live_off drain 1' > $F/run/KILL_SWITCH" "FAIL KHONG co run/KILL_SWITCH"
N=$((N+1)); grep -q '^golive_live_off drain 1' $F/run/KILL_SWITCH && { P=$((P+1)); echo "PASS $N KS owner KHONG bi ghi de/go"; } || { FAILS="$FAILS #$N"; echo "FAIL $N KS owner bi doi"; }
refuse "PAUSE watchdog cua nguoi khac" "echo 'OTHER t=1' > $W/wd/PAUSE" "FAIL KHONG PAUSE"
rm -f $W/wd/PAUSE
refuse "latch FLATTEN" "echo '{\"latch\":\"FLATTEN\"}' > $F/run/killsw_latch.json" "FAIL latch"
refuse "adapter=dry" "sed -i 's/^export LIVE_ADAPTER=live/export LIVE_ADAPTER=dry/' $F/conf/env.sh; bash $F/bin/daemon.sh stop; bash $F/bin/daemon.sh start; sleep 1; cp -p $F/conf/env.sh $W/env_tmp" "FAIL c3_live + adapter"
refuse "C3_CAPITAL=2000" "sed -i 's/^export C3_CAPITAL=1000/export C3_CAPITAL=2000/' $F/conf/env.sh; bash $F/bin/daemon.sh stop; bash $F/bin/daemon.sh start; sleep 1" "FAIL C3_CAPITAL"
refuse "so c3 con 1 cum" "book1 100 0.5; echo '[{\"symbol\":\"AAAUSDT\",\"positionAmt\":\"100\"}]' > $W/fk/pos.json" "FAIL so + san c3 FLAT"
refuse "san con vi the (so rong)" "echo '[{\"symbol\":\"ZZZUSDT\",\"positionAmt\":\"5\"}]' > $W/fk/pos.json" "FAIL so + san c3 FLAT"
refuse "cron golive_monitor khong co" "echo '' > $W/fk/crontab.txt" "FAIL golive_monitor song"
refuse "TOPK env.sh != 24 (khong phai production)" "sed -i 's/^export SELECTOR_RANK_TOPK=24/export SELECTOR_RANK_TOPK=8/' $F/conf/env.sh; bash $F/bin/daemon.sh stop; bash $F/bin/daemon.sh start; sleep 1" "FAIL 3 key PROCESS"
refuse "env.sh da co khoi GRIDTEST" "printf '# GRIDTEST x pha A\nexport DCA_GRID_LEVELS=-0.01\n' >> $F/conf/env.sh" "FAIL 3 key env.sh\|FAIL env.sh CHUA co khoi"
reset_all; OUT=$(echo YES | A1_APPROVED_OPS=$W/none DRY=0 bash $G/gridtest_on.sh 2>&1); RC=$?
chk "m1: HEAD khong co trong A1_APPROVED_OPS => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'TU CHOI \[m1\]'"
# ===================================================== watchdog giu .lock => FAIL truoc khi dung bot
reset_all; P0=$(pid); flock -o $W/wd/.lock sleep 40 & LK=$!; sleep 0.5
OUT=$(echo YES | SJ_WD_LOCK_WAIT_S=2 DRY=0 bash $G/gridtest_on.sh 2>&1); RC=$?; kill $LK 2>/dev/null; wait $LK 2>/dev/null
chk "watchdog giu .lock: TU CHOI truoc khi dung bot, KS + PAUSE cua minh go, env khong doi, state NONE" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'watchdog_giu_lock' && [ \"\$(pid)\" = '$P0' ] && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/wd/PAUSE ] && [ \"\$(em5)\" = $E0 ] && [ \"\$(st GT_PHASE)\" = NONE ]"
# ===================================================== ssh mat o buoc doc trang thai
reset_all; echo "STATE before 3" > $W/sshplan; P0=$(pid); ON
chk "mat ssh luc doc trang thai: die, khong doi gi" "[ $RC = 1 ] && [ \"\$(pid)\" = '$P0' ] && [ \"\$(em5)\" = $E0 ] && [ ! -e $F/run/KILL_SWITCH ]"
# ===================================================== start that bai => khoi phuc
reset_all; touch $F/FAKE_NOSTART_IF_TEST; ON
chk "start voi env test THAT BAI => khoi phuc BASE (md5 = goc), bot chay env production, KS cua minh go, PUSH ON, exit 1, Telegram" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Da KHOI PHUC' && [ \"\$(em5)\" = $E0 ] && [ \"\$(np)\" = 1 ] && penv | grep -qx LIVE_GATE_ROLLING_PCT=0.999950829 && ! penv | grep -q '^DCA_GRID_LEVELS=' && [ ! -e $F/run/KILL_SWITCH ] && grep -q 'KHOI PHUC' $W/tg.txt && ! grep -q GRIDTEST_WATCH $W/fk/crontab.txt"
# ===================================================== hau kiem truot (KHAN + token trong log) => khoi phuc + loc output
reset_all; touch $F/FAKE_KHAN_IF_TEST; ON
chk "hau kiem truot (KHAN) => khoi phuc, exit 1; output loc token/signature" "[ $RC = 1 ] && [ \"\$(em5)\" = $E0 ] && [ ! -e $F/run/KILL_SWITCH ] && echo \"\$OUT\" | grep -q '<TOKEN>' && nosec \"\$OUT\" && nosec \"\$(cat $W/gt/gridtest_on_*.log)\""
# ===================================================== THANH CONG pha A (co ssh rot 1 lan o RESTART truoc khi chay)
reset_all; echo "RESTART before 1" > $W/sshplan; ON
B=$(ls $F/conf/env.sh.gridtest_base_* 2>/dev/null | grep -v md5 | head -1)
chk "PHA A XONG (ssh rot 1 lan truoc restart): env.sh = BASE + 4 dong khoi, process 3 key test, KS go, PAUSE go, PUSH ON, cron watch, state A, Telegram" \
 "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG PHA A' && [ \"\$(head -n $(wc -l < $W/env0.sh) $F/conf/env.sh | md5sum | cut -c1-32)\" = $E0 ] && [ \$(wc -l < $F/conf/env.sh) = \$(( \$(wc -l < $W/env0.sh) + 4 )) ] && tail -n 4 $F/conf/env.sh | head -1 | grep -q '^# GRIDTEST ' && penv | grep -qx LIVE_GATE_ROLLING_PCT=0.99 && penv | grep -qx SELECTOR_RANK_TOPK=1 && penv | grep -qx DCA_GRID_LEVELS=-0.01,-0.02,-0.03 && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/wd/PAUSE ] && grep -q 'PUSH doi trang thai -> ON' $F/logs/full.log && [ \$(grep -c GRIDTEST_WATCH $W/fk/crontab.txt) = 1 ] && grep -q 'golive_monitor' $W/fk/crontab.txt && [ \"\$(st GT_PHASE)\" = A ] && grep -q 'PHA A BAT' $W/tg.txt && [ -n '$B' ] && [ \"\$(md5sum < $B | cut -c1-32)\" = $E0 ] && nosec \"\$OUT\""
EA=$(em5)
OUT=$(echo YES | DRY=0 bash $G/gridtest_on.sh 2>&1); RC=$?
chk "chay on lan 2 khi dang pha A => TU CHOI, khong restart" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'dang co phien gridtest' && [ \"\$(em5)\" = $EA ]"
# ===================================================== WATCH
WT() { OUT=$(GT_WATCH_ONCE=1 bash $G/gridtest_watch.sh 2>&1); RC=$?; }
WT; chk "watch 0 SUBMIT: WATCH_OK, khong KS" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '^WATCH_OK pha=A leg0=0' && [ ! -e $F/run/KILL_SWITCH ]"
submit AAAUSDT PREDICT_SYMBOL_TRADE 0 22.5 22.4 0.0; submit BBBUSDT PREDICT_SYMBOL_TRADE 0 22.0 21.9 0.0224
book1 100 0.224; echo '[{"symbol":"AAAUSDT","markPrice":"0.22"}]' > $W/fk/prices.json
WT; chk "watch 2 leg0: nhac phase_b (Telegram 1 lan), KHONG phanh" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'leg0=2' && echo \"\$OUT\" | grep -q 'gridtest_phase_b.sh' && [ ! -e $F/run/KILL_SWITCH ] && [ \$(grep -c 'DU leg0' $W/tg.txt) = 1 ]"
WT; chk "watch lan 2: khong nhac lai" "[ \$(grep -c 'DU leg0' $W/tg.txt) = 1 ]"
submit CCCUSDT DCA_LEVEL1 1 22.0 21.9 0.04
WT; chk "watch dem DCA rieng (legIdx>=1)" "echo \"\$OUT\" | grep -q 'leg0=2 dca=1 submit=3'"
# ---- phase_b DRY / tu choi khi KS / thanh cong
OUT=$(bash $G/gridtest_phase_b.sh 2>&1); RC=$?
chk "phase_b DRY: DRY PASS, env khong doi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \"\$(em5)\" = $EA ]"
echo 'golive_live_off drain 9' > $F/run/KILL_SWITCH
OUT=$(echo YES | DRY=0 bash $G/gridtest_phase_b.sh 2>&1); RC=$?
chk "phase_b TU CHOI khi co KILL_SWITCH (giu nguyen)" "[ $RC = 1 ] && grep -q '^golive_live_off drain 9' $F/run/KILL_SWITCH && [ \"\$(em5)\" = $EA ]"
rm -f $F/run/KILL_SWITCH
echo "RESTART hup 1" > $W/sshplan
OUT=$(echo YES | DRY=0 bash $G/gridtest_phase_b.sh 2>&1); RC=$?
chk "PHA B XONG (ssh dut HUP giua restart): env = BASE + khoi B (2 dong), process PCT/TOPK production + DCA nong, PUSH ON, state B" \
 "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG PHA B' && [ \"\$(head -n $(wc -l < $W/env0.sh) $F/conf/env.sh | md5sum | cut -c1-32)\" = $E0 ] && [ \$(wc -l < $F/conf/env.sh) = \$(( \$(wc -l < $W/env0.sh) + 2 )) ] && penv | grep -qx LIVE_GATE_ROLLING_PCT=0.999950829 && penv | grep -qx SELECTOR_RANK_TOPK=24 && penv | grep -qx DCA_GRID_LEVELS=-0.01,-0.02,-0.03 && [ \"\$(np)\" = 1 ] && [ ! -e $F/run/KILL_SWITCH ] && [ \"\$(st GT_PHASE)\" = B ]"
# ---- phanh
WT; chk "watch notional 22.0 / lo -0.4: chua phanh" "[ ! -e $F/run/KILL_SWITCH ] && echo \"\$OUT\" | grep -q 'phanh=khong'"
book1 2000 0.2; echo '[{"symbol":"AAAUSDT","markPrice":"0.2"}]' > $W/fk/prices.json
WT; chk "watch notional 400 > 300 => PHANH: KS token gridtest_watch + Telegram KHAN" "grep -q '^gridtest_watch ' $F/run/KILL_SWITCH && grep -q 'notional' $F/run/KILL_SWITCH && grep -q 'KHAN PHANH' $W/tg.txt"
echo 'golive_live_off drain 7' > $F/run/KILL_SWITCH; book1 1000 0.2; echo '[{"symbol":"AAAUSDT","markPrice":"0.16"}]' > $W/fk/prices.json
WT; chk "watch lo -40 < -30 khi KS owner dang co => KHONG ghi de KS owner" "grep -q '^golive_live_off drain 7' $F/run/KILL_SWITCH && echo \"\$OUT\" | grep -q 'lo_'"
rm -f $F/run/KILL_SWITCH; sed -i '/^GT_BRAKE/d; /^GT_TG_BRAKE/d' $W/gt/state.env
WT; chk "watch lo -40 => PHANH" "grep -q '^gridtest_watch .*lo_' $F/run/KILL_SWITCH"
rm -f $F/run/KILL_SWITCH; book1 100 0.2; echo '[{"symbol":"AAAUSDT","markPrice":"0.2"}]' > $W/fk/prices.json
submit DDDUSDT PREDICT_SYMBOL_TRADE 0 20 20 0.1; submit EEEUSDT PREDICT_SYMBOL_TRADE 0 20 20 0.1
WT; chk "watch leg0=4 > 3 => PHANH" "grep -q '^gridtest_watch .*leg0_4' $F/run/KILL_SWITCH"
rm -f $F/run/KILL_SWITCH; logl "ERROR [x] x: [C3-LIVE] KHAN: XXXUSDT LOST_FOREIGN gia"
WT; chk "watch dong KHAN trong log => PHANH" "grep -q '^gridtest_watch .*KHAN' $F/run/KILL_SWITCH"
rm -f $F/run/KILL_SWITCH; echo "WATCH before 9" > $W/sshplan
for i in 1 2 3 4; do WT; done; R4=$(ls $F/run/KILL_SWITCH 2>/dev/null); WT
chk "watch doc 242 loi 5 luot lien tiep => phanh (lan 1-4 khong)" "[ -z '$R4' ] && echo \"\$OUT\" | grep -q 'WATCH_ERR' && grep -q 'doc_242_loi_5' $F/run/KILL_SWITCH"
: > $W/sshplan; rm -f $F/run/KILL_SWITCH
# ---- off: tu choi khi con cum ; FORCE_KEEP ; KS owner giu ; env byte-exact
OUT=$(echo YES | DRY=0 bash $G/gridtest_off.sh 2>&1); RC=$?
chk "off TU CHOI khi so con cum (mac dinh)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL so/san c3 CON cum' && [ \"\$(st GT_PHASE)\" = B ]"
echo 'golive_live_off drain 5' > $F/run/KILL_SWITCH
OUT=$(echo YES | GT_FORCE_KEEP=1 DRY=0 bash $G/gridtest_off.sh 2>&1); RC=$?
chk "off GT_FORCE_KEEP=1 + KS owner: env.sh = goc TUNG BYTE, process production (khong DCA_GRID_LEVELS), KS owner GIU, cron watch go, state OFF" \
 "[ $RC = 0 ] && cmp -s $F/conf/env.sh $W/env0.sh && [ \"\$(stat -c %a $F/conf/env.sh)\" = 640 ] && penv | grep -qx LIVE_GATE_ROLLING_PCT=0.999950829 && penv | grep -qx SELECTOR_RANK_TOPK=24 && ! penv | grep -q '^DCA_GRID_LEVELS=' && grep -q '^golive_live_off drain 5' $F/run/KILL_SWITCH && ! grep -q GRIDTEST_WATCH $W/fk/crontab.txt && grep -q golive_monitor $W/fk/crontab.txt && [ \"\$(st GT_PHASE)\" = OFF ] && echo \"\$OUT\" | grep -q 'KILL_SWITCH KHAC van GIU'"
OUT=$(echo YES | DRY=0 bash $G/gridtest_off.sh 2>&1); RC=$?
chk "off chay lan 2 => TU CHOI (khong co phien), khong doi gi" "[ $RC = 1 ] && cmp -s $F/conf/env.sh $W/env0.sh"
# ===================================================== chu ky 2: on -> off (flat, khong KS) => PUSH ON ; report
reset_all; ON; R1=$RC
submit AAAUSDT PREDICT_SYMBOL_TRADE 0 22.5 22.5 0.0
logl "INFO [x] c.b.c.c.f.FillAccounting: [C3-LIVE-FILL] xac nhan qua stream AAAUSDT c3-AAAUSDT-29900000-0 qty=100 avg=0.225 ref=0.2249"
submit AAAUSDT DCA_LEVEL1 1 22.125 22.1 0.0225
logl "INFO [x] c.b.c.c.f.FillAccounting: [C3-LIVE-FILL] xac nhan qua stream AAAUSDT c3-AAAUSDT-29900000-1 qty=100 avg=0.2220 ref=0.2221"
OUT=$(bash $G/gridtest_report.sh 2>&1); RC=$?
chk "report: bang T1-T10, T1 DAT, T2 bac OK (-1,29 % <= -1 %), file bao cao, khong lo key" "[ $R1 = 0 ] && [ $RC = 0 ] && echo \"\$OUT\" | grep -q '| T1 leg0 sizing | DAT' && echo \"\$OUT\" | grep -q 'leg1: .* OK' && echo \"\$OUT\" | grep -q '| T10 LEGACY' && ls $W/gt/GRIDTEST_REPORT_*.md >/dev/null && nosec \"\$OUT\""
OUT=$(echo YES | DRY=0 bash $G/gridtest_off.sh 2>&1); RC=$?
chk "chu ky 2: off flat khong KS => env goc tung byte, PUSH ON, KS go, cron go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG OFF: env production, PUSH ON' && cmp -s $F/conf/env.sh $W/env0.sh && [ ! -e $F/run/KILL_SWITCH ] && ! grep -q GRIDTEST_WATCH $W/fk/crontab.txt"
# ===================================================== off: start that bai sau dung bot => start lai BASE + KHAN
reset_all; ON
OUT=$(echo YES | DRY=0 bash $G/gridtest_off.sh 2>&1); RC=$?
chk "chu ky 3: off binh thuong lan nua (idempotent qua nhieu phien)" "[ $RC = 0 ] && cmp -s $F/conf/env.sh $W/env0.sh"
echo "TONG: $P/$N"
[ "$P" = "$N" ] && echo "TEST PASS $P/$N" || echo "TEST FAIL$FAILS ($P/$N)"
