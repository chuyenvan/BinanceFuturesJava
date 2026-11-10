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
ing_start $W/ing_qf4.jar; { echo "XONG. collectData chay jar $Q4"; echo "Rollback 1 lenh: bash $W/rb.sh TSX"; } >> $W/d/deploy_ingest_qf4_x.log; exit 0
EOF
printf '#!/bin/bash\nexit 0\n' > $W/reg.sh
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
echo "\${7:-none}" >> $W/check_args
[ -f $W/OLD_SPIKE ] && { [ "\${7:-0}" -gt "\$(cat $W/OLD_SPIKE)" ] 2>/dev/null && echo "OK price_gap_tu_moc" || echo "FAIL price_gap_max_ms_sau_repair=12428 (spike cu)"; }
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
  PROC_PAT="BinanceOrderTradingManager $TAG" REG_JAR_SH=$W/reg.sh DLOCK=$W/d/.deploy.lock \
  PIN_QF4_SH=$(md5sum < $W/qf4.sh | cut -c1-32) PIN_CHECK_R=$(md5sum < $W/check.sh | cut -c1-32) \
  PIN_SWAP_SH=$(md5sum < $W/swap.sh | cut -c1-32) PIN_REG=$(md5sum < $W/reg.sh | cut -c1-32)
cp -p $W/swap.sh $W/swap.sh.orig
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
echo "== [A1 CHAIN] pin md5 / chay ban chep / stop giua hau kiem / khoa deploy / giu log"
reset; echo '# sua sau duyet' >> $W/swap.sh; P0=$(cat $W/d/.deploy_chain/pid)
OUT=$(echo YES | bash $CH qf4_then_r4t 2>&1); RC=$?
chk "script con LECH pin => TU CHOI, khong job, khong goi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'LECH swap_v12_dry_jar.sh' && echo \"\$OUT\" | grep -q 'TU CHOI' && [ \"\$(cat $W/d/.deploy_chain/pid)\" = \"$P0\" ] && [ ! -f $W/calls ]"
OUT=$(DRY=1 bash $CH qf4_then_r4t 2>&1); RC=$?
chk "DRY=1 cung bao LECH pin (DRY FAIL)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'DRY FAIL'"
cp -p $W/swap.sh.orig $W/swap.sh
reset; rm -f $W/tok
echo YES | FORCE_TIME=0 TIME_OK_FILE=$W/tok bash $CH qf4_then_r4t >/dev/null 2>&1
for i in $(seq 1 60); do JL 2>/dev/null | grep -q 'r4t: cho khung gio' && break; sleep 1; done
sed -i "2i echo MODIFIED >> $W/calls" $W/swap.sh; touch $W/tok; waitjob
chk "sua script goc SAU khi YES: job chay BAN CHEP (khong MODIFIED), XONG; thu muc job co md5.txt + chain.log" "grep -q swap $W/calls && ! grep -q MODIFIED $W/calls && JL | grep -q 'XONG CA CHUOI' && [ -s \"\$(cat $W/d/.deploy_chain/last)/md5.txt\" ]"
cp -p $W/swap.sh.orig $W/swap.sh
reset
echo YES | STABLE_S=40 bash $CH qf4_then_r4t >/dev/null 2>&1
for i in $(seq 1 60); do JL 2>/dev/null | grep -q 'qf4: hau kiem on dinh' && break; sleep 1; done
bash $CH stop >/dev/null; waitjob
chk "stop GIUA hau kiem => KHAN 'CHUA xac nhan on dinh' + lenh rollback, steps.txt ghi ro, KHONG swap" "grep -q 'KHAN.*STOP giua hau kiem' $W/tg.txt && grep -q 'CHUA xac nhan on dinh' $W/tg.txt && grep -q 'rb.sh TSX' $W/tg.txt && grep -q 'GIUA hau kiem qf4' \"\$(cat $W/d/.deploy_chain/last)/steps.txt\" && ! grep -q swap $W/calls"
reset
( flock $W/d/.deploy.lock sleep 8 ) & HL=$!; sleep 1
echo YES | bash $CH qf4_then_r4t >/dev/null 2>&1; waitjob; wait $HL 2>/dev/null
chk "khoa deploy dang bi giu => CHO (khong chay), nha khoa => chay tiep XONG" "JL | grep -q 'dang bi giu' && JL | grep -q 'XONG CA CHUOI'"
NJ=$(ls -d $W/d/.deploy_chain/jobs/*/ | wc -l); NL=$(ls $W/d/.deploy_chain/jobs/*/chain.log | wc -l)
chk "giu lau dai: moi lan YES 1 thu muc job ($NJ), co chain.log ($NL), ca lan TU CHOI" "[ $NJ -ge 11 ] && [ $NL -ge 10 ] && grep -rlq 'TU CHOI: lech pin' $W/d/.deploy_chain/jobs/*/steps.txt"
echo "== [V12 R4u] preset swap_r4u3: code [BIG_DOWN-SEL], LEGACY chup truoc swap, gmicro_target.json, hau kiem KHAN/RAM/LEGACY, lenh rollback ve r4t"
python3 - "$W/vtm_r4u.jar" "$W/vtm_r4u_bad.jar" <<'PYEOF'
import sys, zipfile
for p, body in ((sys.argv[1], b'vtm-r4u3 LOG.info("[BIG_DOWN-SEL] {}")'), (sys.argv[2], b'vtm-r4u3-khong-sel')):
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_STORED) as z:
        z.writestr('com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.class', body)
PYEOF
RU=$(md5sum < $W/vtm_r4u.jar | cut -c1-32); RUB=$(md5sum < $W/vtm_r4u_bad.jar | cut -c1-32)
mkswapu() {   # $1 = file, $2 = jar, $3 = md5
cat > $1 <<EOF
#!/usr/bin/env bash
NJ=\${NJ:-$2}
NJ_MD5=\${NJ_MD5:-$3}   # jar r4u3
OLD_TAG=\${OLD_TAG:-r4t}
NEW_TAG=\${NEW_TAG:-r4u3}
if [ "\${DRY:-0}" = 1 ]; then echo "OK jar moi"; echo "DRY PASS"; exit 0; fi
read -r A; [ "\$A" = YES ] || exit 1
echo swapu >> $W/calls
[ -f $W/SWAP_FAIL ] && { echo "ROLLBACK TU DONG"; exit 1; }
. $W/lib.sh
vtm_start $2; echo "x INFO [pool-3-thread-1] x: [LEGACY] managed \$(cat $W/LEG_AFTER 2>/dev/null || echo 44): A,B" >> $W/vtm/logs/full.log
[ -f $W/KHAN_AFTER ] && echo "x WARN [x] x: [C3-LIVE] KHAN gia sau swap" >> $W/vtm/logs/full.log
[ -f $W/FORCE_AFTER ] && echo "x WARN [main] x: [C3-EXCL-FORCE] C3_EXCLUDE_LEGACY_HELD=false bi EP ve true: gia" >> $W/vtm/logs/full.log
exit 0
EOF
}
mkswapu $W/swapu.sh $W/vtm_r4u.jar $RU; mkswapu $W/swapu_bad.sh $W/vtm_r4u_bad.jar $RUB
resetu() { reset; vtm_start $W/vtm_r4t.jar; echo "x INFO [pool-3-thread-1] x: [LEGACY] managed 44: A,B" >> $W/vtm/logs/full.log; rm -f $W/LEG_AFTER $W/KHAN_AFTER $W/FORCE_AFTER $W/calls
  echo '{"target_jar": "r4u3", "target_md5": "'$RU'", "smoke_start_ms": null}' > $W/gm.json; rm -f $W/gm.json.bak_*; }
U() { env SWAP_SH=$W/swapu.sh PIN_SWAP_SH=$(md5sum < $W/swapu.sh | cut -c1-32) GMICRO_TARGET=$W/gm.json JARS_JSON=$W/jars_none.json "$@"; }
resetu
OUT=$(U DRY=1 bash $CH swap_r4u3 2>&1); RC=$?
chk "swap_r4u3 DRY=1: ke hoach r4u3 CHUA, code [BIG_DOWN-SEL] OK, DRY PASS, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'r4u3: CHUA' && echo \"\$OUT\" | grep -q 'OK code \[BIG_DOWN-SEL\]' && echo \"\$OUT\" | grep -q 'DRY PASS' && [ ! -f $W/calls ] && [ \$(vtmmd5) = $RT ]"
OUT=$(env SWAP_SH=$W/swapu_bad.sh PIN_SWAP_SH=$(md5sum < $W/swapu_bad.sh | cut -c1-32) DRY=1 bash $CH swap_r4u3 2>&1); RC=$?
chk "swap_r4u3: jar KHONG co code [BIG_DOWN-SEL] => DRY FAIL; YES => TU CHOI, khong job" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG co code \[BIG_DOWN-SEL\]' && echo \"\$OUT\" | grep -q 'DRY FAIL' && echo YES | env SWAP_SH=$W/swapu_bad.sh PIN_SWAP_SH=$(md5sum < $W/swapu_bad.sh | cut -c1-32) bash $CH swap_r4u3 2>&1 | grep -q 'TU CHOI: jar' && [ ! -f $W/calls ]"
OUT=$(U bash $CH qf4_then_r4t 2>&1 < /dev/null); RC=$?
chk "preset cu qf4_then_r4t khi swap mac dinh NEW_TAG=r4u3 => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'can swap NEW_TAG=r4t'"
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob
chk "swap_r4u3 XONG: swap 1 lan, md5 r4u3, chup LEGACY 44 = sau, 0 KHAN, RAM OK, gmicro_target.json smoke_start_ms (13 so) + target r4u3, XONG ca chuoi" "[ \"\$(grep -c swapu $W/calls)\" = 1 ] && [ \$(vtmmd5) = $RU ] && JL | grep -q 'chup LEGACY managed truoc swap = 44' && JL | grep -q 'OK LEGACY_managed=44 (truoc swap 44)' && JL | grep -q 'OK vtm_0_KHAN' && JL | grep -q 'OK ram_MemAvailable_' && python3 -c \"import json,sys; d=json.load(open('$W/gm.json')); sys.exit(0 if d['target_jar']=='r4u3' and d['target_md5']=='$RU' and len(str(d['smoke_start_ms']))==13 else 1)\" && ls $W/gm.json.bak_* >/dev/null && JL | grep -q 'XONG CA CHUOI' && grep -q 'gmicro_target.json: r4u3 OK smoke_start_ms=' $W/tg.txt"
resetu; touch $W/KHAN_AFTER
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob
chk "swap_r4u3: KHAN sau start => hau kiem FAIL + Telegram KHAN kem lenh rollback ve r4t" "JL | grep -q 'r4u3: hau kiem FAIL' && JL | grep -q 'vtm_KHAN' && grep -q 'KHAN' $W/tg.txt && grep -q 'OLD_TAG=r4u3 NEW_TAG=r4t' $W/tg.txt && grep -q 'NJ_MD5=694b29b2e5be32b537ca6c38557e64db' $W/tg.txt"
resetu; echo 45 > $W/LEG_AFTER
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob
chk "swap_r4u3: LEGACY managed TANG (44 -> 45) => FAIL + lenh rollback" "JL | grep -q 'FAIL LEGACY_managed=45 > truoc swap 44' && grep -q 'OLD_TAG=r4u3 NEW_TAG=r4t' $W/tg.txt"
resetu; echo '{"target_jar": "r4u3", "target_md5": "00000000000000000000000000000000", "smoke_start_ms": null}' > $W/gm.json
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob
chk "swap_r4u3: gmicro_target.json target_md5 KHAC jar => KHAN, KHONG ghi (chuoi van hau kiem jar)" "grep -q 'KHAN.*gmicro_target.json KHONG ghi: ERR target_md5' $W/tg.txt && grep -q '\"smoke_start_ms\": null' $W/gm.json && JL | grep -q 'XONG CA CHUOI'"
OUT=$(U C3_ACCOUNT=MAIN EXCL_HELD=false bash $CH swap_r4u3 2>&1 < /dev/null); RC=$?
chk "A1 r4u2 C-1: C3_ACCOUNT=MAIN + EXCL_HELD=false => chain TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'C3_ACCOUNT=MAIN di voi C3_EXCLUDE_LEGACY_HELD=false'"
resetu; touch $W/FORCE_AFTER
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob
chk "A1 r4u2 C-1: SUB log co [C3-EXCL-FORCE] sau swap => hau kiem FAIL + lenh rollback ve r4t" "JL | grep -q 'FAIL C3-EXCL-FORCE' && grep -q 'OLD_TAG=r4u3 NEW_TAG=r4t' $W/tg.txt"
echo "== [11-10] hau kiem CHI tinh tu moc bat dau buoc (spike cu truoc moc)"
RCK=${REAL_CHECK:-/home/ubuntu/claude_master/ing1030/qf_wt/ops/ingest_qf/ingqf4_check_remote.sh}
mkdir -p $W/rc/ing/logs $W/rc/vtm/logs; : > $W/rc/vtm/logs/full.log
bash -c "exec -a 'websocket.BinanceDataIngestor rcktest_$TAG' sleep 120" & RCKP=$!; sleep 1
NOW=$(date +%s); ts() { date -d "@$1" '+%d/%m/%Y %H:%M:%S.000'; }
bud() { echo "$(ts $1) INFO  [ThreadAutoRestartProgram] c.b.c.w.BinanceDataIngestor: [REST-BUDGET] calls=47 weight=85 peak60s=$2 now60s=85 fdata=0 denied=0 http429=$3 http418=0 http4xx=0 hdr_max=90 | price_gap_max_ms=$4 price_age_ms=800 price_diff=10 loop_restarts=0 repair_xong=1 banned=0"; }
{ for p in $(pgrep -f 'websocket.BinanceDataIngestor'); do echo "$(ts $((NOW-200000))) INFO  [main] x: PID $p written"; done
  echo "$(ts $((NOW-200000))) INFO  [main] x: [REST-BUDGET] bat"; echo "$(ts $((NOW-199000))) INFO  [main] x: repair khoi dong xong"
  bud $((NOW-180000)) 85 0 3300; bud $((NOW-170000)) 410 3 12428
  echo "$(ts $((NOW-170000))) WARN  [x] x: Too many symbol price errors"; echo "$(ts $((NOW-160000))) WARN  [x] x: [PRICE-AGE] price_realtime dung 9s"
  for d in 300 200 100; do bud $((NOW-d)) 85 0 3300
    echo "$(ts $((NOW-d))) INFO  [Kline-Finalizer] x: [KLINE-COVER] phut=x chua_chot=0 chua_chot_truoc=0 bo_kiem=0 khoi_dong=0 thieu_luc_chot=0 thieu_do_mat_ws=0 "
    echo "$(ts $((NOW-d))) INFO  [Kline-Finalizer] x: Chot nen phut ok"; done; } > $W/rc/ing/logs/full.log
O1=$(bash "$RCK" $W/rc/ing $W/rc/vtm x 0 new none $((NOW-400)) 2>&1 < /dev/null)
O0=$(bash "$RCK" $W/rc/ing $W/rc/vtm x 0 new none 2>&1 < /dev/null)
kill $RCKP 2>/dev/null
chk "ingqf4_check_remote THAT + moc buoc: spike cu TRUOC moc (gap 12428, http429=3, peak 410, restart JVM, PRICE-AGE) KHONG tinh => OK; budget_bat/repair van doc tu start; khong moc => FAIL 12428 nhu cu" "echo \"\$O1\" | grep -q 'OK price_gap_max_ms_sau_repair=3300' && echo \"\$O1\" | grep -q 'OK 0_http429_418' && echo \"\$O1\" | grep -q 'OK weight_peak=85' && echo \"\$O1\" | grep -q 'OK 0_restart' && echo \"\$O1\" | grep -q 'OK 0_PRICE-AGE' && echo \"\$O1\" | grep -q 'OK budget_bat' && echo \"\$O1\" | grep -q 'OK kline_phu_phut_da_chot' && echo \"\$O1\" | grep -q 'INFO moc_hau_kiem=' && echo \"\$O0\" | grep -q 'FAIL price_gap_max_ms_sau_repair=12428' && echo \"\$O0\" | grep -q 'FAIL co_restart_JVM'"
O2=$(bash "$RCK" $W/rc/ing $W/rc/vtm x 0 new none $((NOW-30)) 2>&1 < /dev/null)
chk "ingqf4_check_remote THAT: moc sau moi dong budget => WAIT (khong OK/FAIL gia)" "echo \"\$O2\" | grep -q 'WAIT budget_sau_repair=0' && ! echo \"\$O2\" | grep -q 'price_gap_max_ms_sau_repair'"
resetu; date -d '-2 day' +%s > $W/OLD_SPIKE; rm -f $W/check_args; T0=$(date +%s)
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob
chk "chain: check collectData nhan moc = luc bat dau buoc (arg 7) => spike cu truoc moc KHONG lam FAIL, XONG" "JL | grep -q 'XONG CA CHUOI' && JL | grep -q 'moc hau kiem = ' && A7=\$(head -1 $W/check_args) && [ \"\$A7\" -ge $T0 ] && [ \"\$A7\" -le \$(date +%s) ]"
echo "x ERROR [main] x: loi CU truoc buoc" >> $W/vtm/logs/full.log; rm -f $W/check_args; T1=$(date +%s)
( for i in $(seq 1 40); do sleep 1; echo "x INFO [pool-3-thread-1] x: [LEGACY] managed 44: A,B" >> $W/vtm/logs/full.log; done ) & LAP=$!   # LEGACY log moi phut (that) sau moc
echo YES | U bash $CH swap_r4u3 >/dev/null 2>&1; waitjob; kill $LAP 2>/dev/null
chk "chain: buoc da XONG tu truoc => moc = luc bat dau hau kiem: ERROR cu (sau dong khoi dong JVM, truoc moc) KHONG lam FAIL" "JL | grep -q 'XONG CA CHUOI' && ! JL | grep -q 'FAIL vtm_ERROR' && [ \"\$(head -1 $W/check_args)\" -ge $T1 ]"
rm -f $W/OLD_SPIKE
pkill -f "$TAG" 2>/dev/null
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
