#!/usr/bin/env bash
# test_deploy_chain.sh — [V12 R4t] test GIA cho deploy_chain.sh (khong cham 242): SSH_242="bash -c", process gia, script buoc gia.
# Chay: bash ops/c3live/test/test_deploy_chain.sh <thu_muc_tam>
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
CH=$HERE/deploy_chain.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W"/d "$W"/vtm/{logs,run,target} "$W"/ing
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
printf 'ing-old' > $W/ing_old.jar; printf 'ing-qf4' > $W/ing_qf4.jar; Q4=$(md5sum < $W/ing_qf4.jar | cut -c1-32)
printf 'vtm-r4q' > $W/vtm_r4q.jar; printf 'vtm-r4t' > $W/vtm_r4t.jar; RT=$(md5sum < $W/vtm_r4t.jar | cut -c1-32)
TAG=fakechain$$
ing_start() { pkill -f "websocket.BinanceDataIngestor $TAG" 2>/dev/null; cp -f $1 $W/ing/binance-java-sdk-1.2.4.jar
  setsid bash -c "exec 3<$W/ing/binance-java-sdk-1.2.4.jar; exec -a 'java websocket.BinanceDataIngestor $TAG' sleep 900" >/dev/null 2>&1 < /dev/null & sleep 0.5; }
vtm_start() { pkill -f "BinanceOrderTradingManager $TAG" 2>/dev/null; cp -f $1 $W/vtm/target/binance-java-sdk-1.2.4.jar
  echo "x INFO [main] x: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager" >> $W/vtm/logs/full.log
  [ "$1" = $W/vtm_r4t.jar ] && echo "x INFO [main] x: [MINUTE-GUARD] BAT" >> $W/vtm/logs/full.log
  setsid bash -c "exec -a 'BinanceOrderTradingManager $TAG' sleep 900" >/dev/null 2>&1 < /dev/null & sleep 0.5; }
reset() { ing_start $W/ing_old.jar; vtm_start $W/vtm_r4q.jar; echo '{"latch":"NONE"}' > $W/vtm/run/killsw_latch.json; rm -f $W/{ING_FAIL,ING_WAIT,QF4_FAIL,SWAP_FAIL,calls,tg.txt} $W/d/deploy_ingest_qf4_*.log; }
# script buoc gia (dung chung ham qua lib.sh)
{ echo "W=$W; TAG=$TAG"; declare -f ing_start vtm_start; } > $W/lib.sh
cat > $W/qf4.sh <<EOF
#!/usr/bin/env bash
JAR_MD5=$Q4
read -r A; [ "\$A" = YES ] || exit 1
echo qf4 >> $W/calls
[ -f $W/QF4_FAIL ] && { echo "rollback"; exit 1; }
. $W/lib.sh
ing_start $W/ing_qf4.jar; echo "XONG. collectData chay jar $Q4" >> $W/d/deploy_ingest_qf4_x.log; exit 0
EOF
cat > $W/swap.sh <<EOF
#!/usr/bin/env bash
NJ_MD5=\${NJ_MD5:-$RT}   # jar r4t
if [ "\${DRY:-0}" = 1 ]; then echo "OK jar moi"; echo "DRY PASS"; exit 0; fi
read -r A; [ "\$A" = YES ] || exit 1
echo swap >> $W/calls
[ -f $W/SWAP_FAIL ] && { echo "ROLLBACK TU DONG"; exit 1; }
. $W/lib.sh
vtm_start $W/vtm_r4t.jar; [ -f $W/ERR_AFTER ] && echo "x ERROR [main] x: loi gia" >> $W/vtm/logs/full.log; exit 0
EOF
cat > $W/check.sh <<EOF
[ -f $W/ING_FAIL ] && echo "FAIL http429=3"
[ -f $W/ING_WAIT ] && echo "WAIT kline_cover_sau_khoi_dong=0 (<2)"
echo "OK 0_http429_418"; echo "OK price_gap_max_ms_sau_repair=1200"; echo "OK kline_phu_phut_da_chot (gia)"
EOF
# job QF4 gia "dang chay" (owner chay tay)
cat > $W/fakeqf4_job_$TAG.sh <<EOF
sleep 6; bash $W/qf4.sh <<< YES
EOF
export SSH_242="bash -c" APP_DIR=$W/vtm ING_DIR=$W/ing QF4_SH=$W/qf4.sh SWAP_SH=$W/swap.sh CHECK_R=$W/check.sh CHAIN_DIR=$W/d \
  STABLE_S=3 STABLE_MAX_S=40 CHK_POLL_S=1 FORCE_TIME=1 DEPLOY_TG_SINK=$W/tg.txt QF4_PAT="fakeqf4_job_$TAG" OTHER_PAT="nomatch_$TAG" \
  PROC_PAT="BinanceOrderTradingManager $TAG"
waitjob() { local p; p=$(cat $W/d/.deploy_chain/pid 2>/dev/null); for i in $(seq 1 120); do kill -0 "$p" 2>/dev/null || return 0; sleep 1; done; return 1; }
JL() { cat "$(cat $W/d/.deploy_chain/log)"; }
ingmd5() { md5sum < $W/ing/binance-java-sdk-1.2.4.jar | cut -c1-32; }
vtmmd5() { md5sum < $W/vtm/target/binance-java-sdk-1.2.4.jar | cut -c1-32; }

echo "== deploy_chain: DRY / chuoi day du (QF4 dang chay) / idempotent / FAIL / hau kiem / stop"
reset
OUT=$(DRY=1 bash $CH qf4_then_r4t 2>&1); RC=$?
chk "DRY=1: ke hoach 2 buoc CHUA + DRY swap PASS, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'qf4: CHUA' && echo \"\$OUT\" | grep -q 'r4t: CHUA' && echo \"\$OUT\" | grep -q 'DRY PASS' && [ ! -f $W/calls ] && [ \$(vtmmd5) != $RT ]"
OUT=$(echo NO | bash $CH qf4_then_r4t 2>&1); RC=$?
chk "khong go YES => huy, khong job" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy' && [ ! -f $W/calls ]"
setsid bash $W/fakeqf4_job_$TAG.sh >/dev/null 2>&1 < /dev/null & sleep 1
OUT=$(echo YES | bash $CH qf4_then_r4t 2>&1); RC=$?
chk "QF4 dang chay: ke hoach bao DANG CHAY, YES => JOB NEN" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'qf4: DANG CHAY' && echo \"\$OUT\" | grep -q 'JOB NEN pid='"
waitjob
chk "chuoi: CHO job QF4 (khong chay QF4 lan 2), on dinh, swap r4t 1 lan, XONG ca chuoi + Telegram tung buoc" "JL | grep -q 'cho no xong' && [ \"\$(grep -c qf4 $W/calls)\" = 1 ] && [ \"\$(grep -c swap $W/calls)\" = 1 ] && [ \$(ingmd5) = $Q4 ] && [ \$(vtmmd5) = $RT ] && JL | grep -q 'XONG CA CHUOI' && grep -q 'BAT DAU' $W/tg.txt && grep -q 'r4t: BAT DAU' $W/tg.txt && grep -q 'XONG CA CHUOI' $W/tg.txt && JL | grep -q 'ON DINH'"
chk "status sau XONG" "bash $CH status | grep -q 'XONG ca chuoi'"
rm -f $W/calls $W/tg.txt
echo YES | bash $CH qf4_then_r4t >/dev/null 2>&1; waitjob
chk "idempotent: ca 2 da XONG => bo qua, KHONG goi script nao, XONG" "[ ! -f $W/calls ] && JL | grep -q 'qf4: DA XONG tu truoc' && JL | grep -q 'r4t: DA XONG tu truoc' && JL | grep -q 'XONG CA CHUOI'"
reset; vtm_start $W/vtm_r4q.jar; touch $W/QF4_FAIL
echo YES | bash $CH qf4_then_r4t >/dev/null 2>&1; waitjob
chk "qf4 FAIL/rollback => DUNG CA CHUOI + KHAN, KHONG swap" "! grep -q swap $W/calls && JL | grep -q 'DUNG CHUOI: qf4: script rc=1' && grep -q 'KHAN' $W/tg.txt && [ \$(vtmmd5) != $RT ]"
reset; touch $W/ING_FAIL
echo YES | bash $CH qf4_then_r4t >/dev/null 2>&1; waitjob
chk "hau kiem collectData FAIL (429) sau qf4 => DUNG, KHONG swap" "! grep -q swap $W/calls && JL | grep -q 'qf4: hau kiem FAIL' && grep -q KHAN $W/tg.txt"
reset; touch $W/ING_WAIT
echo YES | STABLE_MAX_S=5 bash $CH qf4_then_r4t >/dev/null 2>&1; waitjob
chk "WAIT keo dai qua STABLE_MAX_S => DUNG (khong coi la on dinh)" "! grep -q swap $W/calls && JL | grep -q 'khong on dinh sau 5s'"
reset; touch $W/ERR_AFTER
echo YES | bash $CH qf4_then_r4t >/dev/null 2>&1; waitjob; rm -f $W/ERR_AFTER
chk "sau swap v_t_m co ERROR => r4t hau kiem FAIL + KHAN" "JL | grep -q 'r4t: hau kiem FAIL' && JL | grep -q 'vtm_ERROR' && grep -q KHAN $W/tg.txt"
reset; rm -f $W/tok
echo YES | FORCE_TIME=0 TIME_OK_FILE=$W/tok bash $CH qf4_then_r4t >/dev/null 2>&1
for i in $(seq 1 60); do JL 2>/dev/null | grep -q 'r4t: cho khung gio' && break; sleep 1; done
bash $CH stop >/dev/null; waitjob
chk "r4t CHO khung gio ke tiep sau qf4; stop => dung TRUOC swap" "JL | grep -q 'qf4: ON DINH' && JL | grep -q 'STOP theo yeu cau' && ! grep -q swap $W/calls && [ \$(ingmd5) = $Q4 ]"
pkill -f "$TAG" 2>/dev/null
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
