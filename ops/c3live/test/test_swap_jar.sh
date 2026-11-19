#!/usr/bin/env bash
# =============================================================================
# test_swap_jar.sh - [HOTFIX-KS] chay THU golive_swap_jar.sh tren "242 GIA" (thu muc tam tren Oracle, process ten RIENG hfx_<pid>).
#   KHONG ssh 242, KHONG goi Binance, Telegram GIA (DEPLOY_TG_SINK). ssh gia co tiem loi theo LOAI lenh (fakessh.sh + PLAN).
#   bash ops/c3live/test/test_swap_jar.sh <thu_muc_tam>     => "TEST PASS n/n" | "TEST FAIL ..."
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
W=${1:?"thieu thu muc tam"}
case "$W" in *hfx_*) ;; *) W=${W%/}_hfx_$$;; esac
rm -rf "$W"; mkdir -p "$W"
git -C "$HERE" diff --quiet HEAD -- . || { echo "TEST FAIL: $HERE co sua CHUA commit (m1)"; exit 1; }
export A1_APPROVED_OPS=$W/a1_approved_ops.commit; git -C "$HERE" rev-parse HEAD > "$A1_APPROVED_OPS"
PN="BinanceOrderTradingManager hfx_$$"
cleanup() { pkill -9 -f "$PN" 2>/dev/null; pkill -9 -f "hfxw_$$" 2>/dev/null; pkill -9 -f "$W/" 2>/dev/null; :; }
trap cleanup EXIT
trap 'exit 130' INT TERM
F=$W/v_t_m; mkdir -p "$F/conf" "$F/bin" "$F/logs" "$F/run" "$F/target" "$W/deploylog" "$W/gates"
printf 'C3_LIVE_API_KEY=hfxfakekey0123456789abcdef\nC3_LIVE_API_SECRET=hfxfakesecret0123456789\n' > $W/keys_sub.env; chmod 600 $W/keys_sub.env
SK8=$(printf %s hfxfakekey0123456789abcdef | sha256sum | cut -c1-8)
cat > "$F/conf/env.sh" <<EOF
export LIVE_PROFILE=c3_live
export LIVE_KILLSW_MODE=act
# [v1.2 golive_micro_on 20261119_093053] MICRO-LIVE
export LIVE_ADAPTER=live
export C3_CAPITAL=1000
export SHADOW_NO_PUSH=false
export LIVE_ENTRY_ENABLED=true
export LIVE_C3_KEYS_FILE=$W/keys_sub.env
export C3_EXCLUDE_LEGACY_HELD=false
export LIVE_APPLY_GRID_RATIO=true
export LIVE_DCA_GRID_ENABLED=true
export LIVE_SEED_EXCLUDE_DECISION_MIN=1
EOF
echo '{"latch":"NONE"}' > "$F/run/killsw_latch.json"
echo 'OLDJAR r4u3fin2 hfx MINUTE-FIN' > $W/old.jar; echo 'NEWJAR hotfixks hfx MINUTE-FIN' > $W/new.jar; chmod 600 $W/old.jar $W/new.jar
OLD=$(md5sum < $W/old.jar | cut -c1-32); NEW=$(md5sum < $W/new.jar | cut -c1-32)
cp $W/old.jar "$F/target/binance-java-sdk-1.2.4.jar"
echo "$NEW" > "$F/FAKE_NEWMD5"
cat > "$F/bin/daemon.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")/.."
PN=$(cat FAKE_PN)
case "$1" in
  stop) [ -f FAKE_NOSTOP ] && exit 0; pkill -f "$PN"; pkill -f "hfxw_$(cat FAKE_TID)"; sleep 0.5   # nhu daemon.sh that: TERM roi -9
        pkill -9 -f "$PN"; pkill -9 -f "hfxw_$(cat FAKE_TID)"; : ;;
  start)
    JM=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32); ISNEW=0; [ "$JM" = "$(cat FAKE_NEWMD5)" ] && ISNEW=1
    [ "$ISNEW" = 1 ] && [ -f FAKE_NOSTART_IF_NEW ] && exit 0
    set -a; . conf/env.sh; set +a; export PN
    nohup bash -c 'exec -a "$PN" sleep 900' >/dev/null 2>&1 &
    sleep 1
    D=$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000')
    PUSHV=OFF; [ ! -e run/KILL_SWITCH ] && PUSHV=ON
    {
      echo "$D INFO [main] x: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager"
      echo "$D WARN [main] x: [LIVE_PROFILE=c3_live] BAT - hanh vi C3 day du PUSH=$PUSHV (SHADOW_NO_PUSH=${SHADOW_NO_PUSH:-})"
      echo "$D INFO [main] x: [MINUTE-FIN] $([ -f FAKE_FINTAT ] && echo TAT || echo BAT) - phut DU"
      echo "$D INFO [x] x: [LIVE-DCA-GRID] LIVE_DCA_GRID_ENABLED=true profileC3=true levels=[-0.5] legs=3 weights=[1.0] scale=6.0 applyRatio=true"
      echo "$D INFO [x] x: [LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true - gia lap"
      echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=LIVE gateway=c3scope(live) book=run/c3live_book.json cum=2 c3_capital=${C3_CAPITAL:-?}.0 tai_khoan=CHINH(pham vi c3) killSwitchArmed=true"
      echo "$D WARN [C3LIVE-OPS] x: [C3-LIVE-SCOPE] LEGACY tren tai khoan chinh: 0 vi the (foreign DA BIET)"
      echo "$D INFO [C3LIVE-STREAM] x: [C3-LIVE-STREAM] da ket noi"
      echo "$D INFO [main] x: [C3-LIVE-RECON] khoi dong: ok=true closedWhileDown=[]"
      echo "$D INFO [pool-3-thread-1] x: [LEGACY] managed 44: AAAUSDT,BBBUSDT"
      { [ -f FAKE_KHAN_ALWAYS ] || { [ "$ISNEW" = 1 ] && [ -f FAKE_KHAN_IF_NEW ]; }; } && echo "$D ERROR [x] x: [C3-LIVE] KHAN gia lap"
    } >> logs/full.log
    [ "$ISNEW" = 1 ] && [ -f FAKE_DRAIN_IF_NEW ] && echo "golive_live_off drain 20990101_000000" > run/KILL_SWITCH
    if [ "$PUSHV" = OFF ] && [ ! -f FAKE_NOPUSHON ]; then
      nohup bash -c 'echo hfxw_$(cat FAKE_TID) >/dev/null; for i in $(seq 1 300); do sleep 1; [ -e run/KILL_SWITCH ] || { echo "$(TZ=Asia/Ho_Chi_Minh date "+%d/%m/%Y %H:%M:%S.000") WARN [x] x: [C3-LIVE] PUSH doi trang thai -> ON" >> logs/full.log; exit 0; }; done' "hfxw_$(cat FAKE_TID)" >/dev/null 2>&1 &
    fi ;;
esac
EOF
chmod +x "$F/bin/daemon.sh"; echo "$PN" > "$F/FAKE_PN"; echo "$$" > "$F/FAKE_TID"
cat > $W/fakessh.sh <<'EOF'
#!/usr/bin/env bash
# launcher: ghi lenh ra file roi exec => cmdline KHONG chua mau PROC_PAT (nhu ssh that: lenh chay tren may khac)
T=$(mktemp "$FAKESSH_PLAN.cmd.XXXXXX"); printf '%s' "$*" > "$T"; exec bash "${FAKESSH_PLAN%/*}/fakessh2.sh" "$T"
EOF
cat > $W/fakessh2.sh <<'EOF'
#!/usr/bin/env bash
# ssh gia: chay cuc bo; PLAN (file $FAKESSH_PLAN): dong "<LOAI> before|after <so lan>" => tra 255 (truoc/sau khi chay)
CMD=$(cat "$1"); rm -f "$1"; IN=""; [ -t 0 ] || IN=$(cat)
C=OTHER
case "$IN" in *END_RS*) C=RESTART;; *END_RB*) C=ROLLBACK;; *END_CHK*) C=CHK;; *END_STATE*) C=STATE;; esac
case "$CMD" in *END_PHASE*) C=PHASE;; *"chmod 600"*hfks_*) C=STAGEMD5;; *"PUSH doi trang thai"*) C=PUSHWAIT;; *KILL_SWITCH.ok_*) C=KSOFF;; esac
echo "$C" >> "${FAKESSH_PLAN}.log"
M=""; if [ -f "$FAKESSH_PLAN" ]; then
  L=$(grep -m1 "^$C " "$FAKESSH_PLAN"); if [ -n "$L" ]; then set -- $L; n=$3
    if [ "$n" -gt 0 ]; then M=$2; sed -i "0,/^$C .*/s//$C $2 $((n - 1))/" "$FAKESSH_PLAN"; fi; fi; fi
[ "$M" = before ] && exit 255
printf '%s' "$IN" | bash -c "$CMD"; rc=$?
[ "$M" = after ] && exit 255
exit $rc
EOF
touch $W/sshplan
export DEPLOY_TG_SINK=$W/tg.txt LOGDIR=$W/deploylog GATE_DIR=$W/gates APP_DIR=$F PROC_PAT="$PN" WD_PAUSE=$W/PAUSE \
  SSH_242="bash $W/fakessh.sh" FAKESSH_PLAN=$W/sshplan SCP_242=cp RHOST="" KEYS_FILE=$W/keys_sub.env SUB_KEY_SHA8=$SK8 \
  C3_ACCOUNT=SUB CANARY_PAT=canary_early_hfx_NONE_$$ ING_PAT=hfx_no_ingestor_$$ SJ_OLD_MD5=$OLD SJ_NEW_MD5=$NEW \
  SJ_OLD_JAR=$W/old.jar SJ_NEW_JAR=$W/new.jar POST_WAIT_S=1 POST_ROUNDS=5 SSH_RETRY_S=0 FORCE_TIME=1 GL_MON_FLAG=$W/mon.on
S=$HERE/golive_swap_jar.sh
N=0; P=0; FAILS=""
chk() { N=$((N + 1)); if eval "$2"; then P=$((P + 1)); echo "PASS $N $1"; else FAILS="$FAILS #$N"; echo "FAIL $N $1"; echo "$OUT" | tail -25 | sed 's/^/     | /'; fi; }
jm() { md5sum < $F/target/binance-java-sdk-1.2.4.jar | cut -c1-32; }
np() { pgrep -fc "$PN"; }
pid() { pgrep -f "$PN" | head -1; }
penv() { tr '\0' '\n' < /proc/$(pid)/environ 2>/dev/null; }
reset_state() {   # bot chay jar $1, khong KS/PAUSE/plan/hook
  bash $F/bin/daemon.sh stop; sleep 1; rm -f $F/run/KILL_SWITCH $W/PAUSE $F/FAKE_* 2>/dev/null; echo "$PN" > "$F/FAKE_PN"; echo "$$" > "$F/FAKE_TID"; echo "$NEW" > "$F/FAKE_NEWMD5"
  cp "$1" $F/target/binance-java-sdk-1.2.4.jar; : > $W/sshplan; : > $W/tg.txt; bash $F/bin/daemon.sh start; sleep 1; }
nosec() { ! printf '%s' "$1" | grep -q 'hfxfakekey\|hfxfakesecret'; }
E0=$(md5sum < $F/conf/env.sh)
reset_state $W/old.jar
tree_sig() { (cd $F && find . -type f ! -path './logs/*' -printf '%p %s\n' | sort | md5sum); }
# 1 DRY
T0=$(tree_sig); P0=$(pid)
OUT=$(DRY=1 bash $S 2>&1); RC=$?
chk "DRY=1: DRY PASS, 242 khong doi (file, process, jar), khong PAUSE" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \"\$(tree_sig)\" = '$T0' ] && [ \"\$(pid)\" = '$P0' ] && [ ! -e $W/PAUSE ] && [ \"\$(jm)\" = $OLD ] && nosec \"\$OUT\""
# 2 thanh cong
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "swap XONG: jar=moi, 1 process env giu (C3_CAPITAL=1000 live key), backup jar cu md5, KS go (.ok_), PAUSE go, env.sh khong doi, PUSH ON, in thoi gian tat, Telegram XONG" \
 "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=== XONG' && [ \"\$(jm)\" = $NEW ] && [ \"\$(np)\" = 1 ] && penv | grep -qx C3_CAPITAL=1000 && penv | grep -qx LIVE_ADAPTER=live && penv | grep -qx LIVE_C3_KEYS_FILE=$W/keys_sub.env && ls $F/target/*.bak_golive_swap_jar_* >/dev/null 2>&1 && [ \"\$(md5sum < \$(ls $F/target/binance-java-sdk-1.2.4.jar.bak_golive_swap_jar_* | grep -v md5 | head -1) | cut -c1-32)\" = $OLD ] && [ ! -e $F/run/KILL_SWITCH ] && ls $F/run/KILL_SWITCH.ok_* >/dev/null && [ ! -e $W/PAUSE ] && [ \"\$(md5sum < $F/conf/env.sh)\" = '$E0' ] && grep -q 'PUSH doi trang thai -> ON' $F/logs/full.log && echo \"\$OUT\" | grep -q 'THOI GIAN BOT TAT (stop -> start): [0-9]*s' && grep -q 'XONG' $W/tg.txt && echo \"\$OUT\" | grep -q 'OK MINUTE-FIN_BAT' && echo \"\$OUT\" | grep -q 'OK scope_tk_con_0' && echo \"\$OUT\" | grep -q 'OK LEGACY_managed=44' && echo \"\$OUT\" | grep -q 'OK file_key_600_sha8' && nosec \"\$OUT\""
# 3 chay lai => DA XONG
P1=$(pid); OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "chay lai lan 2: DA XONG rc0, khong restart" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DA XONG' && [ \"\$(pid)\" = '$P1' ]"
# 4 MODE=rollback
rm -f $W/sshplan.log; OUT=$(echo YES | MODE=rollback bash $S 2>&1); RC=$?
chk "MODE=rollback: ve jar cu, XONG, KS/PAUSE go" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=== XONG' && [ \"\$(jm)\" = $OLD ] && [ \"\$(np)\" = 1 ] && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/PAUSE ]"
# 5 jar moi sai md5
reset_state $W/old.jar; P0=$(pid); echo 'NEWJAR hong' > $W/bad.jar
OUT=$(echo YES | SJ_NEW_JAR=$W/bad.jar bash $S 2>&1); RC=$?
chk "jar dich sai md5 => TU CHOI, bot khong dung" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHAC pin' && [ \"\$(pid)\" = '$P0' ] && [ \"\$(jm)\" = $OLD ]"
# 6 jar dang chay la
echo 'JAR LA' > $W/strange.jar; reset_state $W/strange.jar; P0=$(pid)
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "jar dang chay la => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL jar dang chay' && [ \"\$(pid)\" = '$P0' ] && [ ! -e $F/run/KILL_SWITCH ]"
# 7 KILL_SWITCH nguoi khac dang dat
reset_state $W/old.jar; echo 'golive_live_off drain 1' > $F/run/KILL_SWITCH; P0=$(pid)
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "KILL_SWITCH khac dang dat => TU CHOI, KS giu nguyen" "[ $RC = 1 ] && grep -q '^golive_live_off drain 1' $F/run/KILL_SWITCH && [ \"\$(pid)\" = '$P0' ]"
# 8 start that bai => rollback
reset_state $W/old.jar; touch $F/FAKE_NOSTART_IF_NEW
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "start jar moi that bai => ROLLBACK ve jar cu, hau kiem DAT, KS go, rc1, Telegram" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && [ \"\$(jm)\" = $OLD ] && [ \"\$(np)\" = 1 ] && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/PAUSE ] && grep -q 'ROLLBACK' $W/tg.txt"
# 9 hau kiem truot => rollback
reset_state $W/old.jar; touch $F/FAKE_KHAN_IF_NEW
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "hau kiem jar moi TRUOT (KHAN) => ROLLBACK DAT, rc1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'hau kiem jar dich TRUOT' && [ \"\$(jm)\" = $OLD ] && [ \"\$(np)\" = 1 ] && [ ! -e $F/run/KILL_SWITCH ]"
# 10 rollback cung truot => KS con + KHAN
reset_state $W/old.jar; touch $F/FAKE_KHAN_IF_NEW; OUT=$(echo YES | bash $S 2>&1 >/dev/null) ; reset_state $W/old.jar; touch $F/FAKE_KHAN_ALWAYS
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "hau kiem truot + hau kiem rollback TRUOT => rc2, KILL_SWITCH CON, bot chay (drain), KHAN Telegram" "[ $RC = 2 ] && [ -e $F/run/KILL_SWITCH ] && [ \"\$(np)\" = 1 ] && grep -q 'KHAN' $W/tg.txt && [ ! -e $W/PAUSE ]"
# 11 drain (live_off) chen giua: KS bi ghi de token drain => khong bao gio go drain
reset_state $W/old.jar; touch $F/FAKE_DRAIN_IF_NEW
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "live_off drain chen giua swap => KS drain GIU, bot chay, rc2 KHAN" "[ $RC = 2 ] && grep -q '^golive_live_off drain' $F/run/KILL_SWITCH && [ \"\$(np)\" = 1 ]"
# 12 stop that bai
reset_state $W/old.jar; touch $F/FAKE_NOSTOP; P0=$(pid)
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "stop khong duoc => TU CHOI rc1, jar khong doi, KS + PAUSE cua script go" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'van_con_process_sau_stop' && [ \"\$(jm)\" = $OLD ] && [ \"\$(pid)\" = '$P0' ] && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/PAUSE ]"
rm -f $F/FAKE_NOSTOP
# 13-19 mat ssh tung buoc
reset_state $W/old.jar; echo 'STATE before 99' > $W/sshplan; P0=$(pid)
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh mat luc kiem truoc => TU CHOI, khong doi" "[ $RC = 1 ] && [ \"\$(pid)\" = '$P0' ] && [ \"\$(jm)\" = $OLD ]"
reset_state $W/old.jar; echo 'STAGEMD5 before 99' > $W/sshplan; P0=$(pid)
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh mat luc kiem jar staging => TU CHOI, bot khong dung" "[ $RC = 1 ] && [ \"\$(pid)\" = '$P0' ] && [ \"\$(jm)\" = $OLD ] && [ ! -e $F/run/KILL_SWITCH ]"
reset_state $W/old.jar; echo 'RESTART after 1' > $W/sshplan
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh dut SAU buoc restart (1 lan) => doc lai pha, chay lai idempotent, XONG" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'pha_da_xong_truoc' && [ \"\$(jm)\" = $NEW ] && [ \"\$(np)\" = 1 ] && [ ! -e $F/run/KILL_SWITCH ]"
reset_state $W/old.jar; printf 'RESTART after 99\nPHASE before 99\n' > $W/sshplan
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh dut han o restart => KHAN rc2 'trang thai khong ro'; that: bot chay + KILL_SWITCH (drain)" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'KHONG ket luan' && [ \"\$(np)\" = 1 ] && [ -e $F/run/KILL_SWITCH ] && grep -q KHAN $W/tg.txt"
reset_state $W/old.jar; echo 'CHK before 99' > $W/sshplan
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh mat luc hau kiem => rollback, hau kiem rollback cung khong doc duoc => rc2, bot chay + KILL_SWITCH" "[ $RC = 2 ] && [ \"\$(np)\" = 1 ] && [ -e $F/run/KILL_SWITCH ] && [ \"\$(jm)\" = $OLD ]"
reset_state $W/old.jar; touch $F/FAKE_KHAN_IF_NEW; echo 'ROLLBACK after 1' > $W/sshplan
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh dut SAU buoc rollback (1 lan) => chay lai idempotent, rollback DAT rc1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'rollback da start o lan truoc' && [ \"\$(jm)\" = $OLD ] && [ \"\$(np)\" = 1 ] && [ ! -e $F/run/KILL_SWITCH ]"
reset_state $W/old.jar; echo 'KSOFF before 99' > $W/sshplan
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh mat luc go KILL_SWITCH => KHAN rc2, KS con (drain), bot chay jar moi" "[ $RC = 2 ] && [ -e $F/run/KILL_SWITCH ] && [ \"\$(np)\" = 1 ] && [ \"\$(jm)\" = $NEW ]"
reset_state $W/old.jar; echo 'PUSHWAIT before 99' > $W/sshplan
OUT=$(echo YES | bash $S 2>&1); RC=$?
chk "ssh mat luc cho PUSH ON => dat lai KILL_SWITCH (xac nhan) + KHAN rc2" "[ $RC = 2 ] && grep -q 'push_khong_ON' $F/run/KILL_SWITCH && [ \"\$(np)\" = 1 ]"
# 21 khong YES
reset_state $W/old.jar; P0=$(pid)
OUT=$(echo no | bash $S 2>&1); RC=$?
chk "khong go YES => Huy, khong doi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy' && [ \"\$(pid)\" = '$P0' ] && [ \"\$(jm)\" = $OLD ]"
# 22 manifest lech => TU CHOI (ban sao repo)
RC2=$(cd $W && rm -rf mrepo && cp -r $HERE mrepo 2>/dev/null && cd mrepo && git init -q && git -c user.name=t -c user.email=t@t add -A && git -c user.name=t -c user.email=t@t commit -qm x && git rev-parse HEAD >> $A1_APPROVED_OPS && echo '#' >> golive_swap_jar.sh && git -c user.name=t -c user.email=t@t commit -qam y && git rev-parse HEAD >> $A1_APPROVED_OPS && DRY=1 bash golive_swap_jar.sh > $W/m.out 2>&1; echo $?)
chk "script bi sua (khac manifest) => TU CHOI [M5]" "[ '$RC2' = 1 ] && grep -q 'TU CHOI \[M5\]' $W/m.out"
echo "TEST $([ -z "$FAILS" ] && echo PASS || echo "FAIL$FAILS") $P/$N"
