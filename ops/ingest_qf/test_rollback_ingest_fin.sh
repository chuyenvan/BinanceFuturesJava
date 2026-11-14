#!/usr/bin/env bash
# test_rollback_ingest_fin.sh - [A1-M4 2026-11-14] kiem chot chan cua rollback_ingest_fin.sh (CHI DRY=1, INGQF_SSH="bash -c",
#   thu muc gia; khong cham 242). v_t_m gia = process "java trading.BinanceOrderTradingManager <tag>" giu fd jar gia + env LIVE_FIN_GUARD.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd); RB=$H/rollback_ingest_fin.sh
W=$(mktemp -d /tmp/tst_rbfin.XXXXXX); TAG=rbfin$$
cleanup() { pkill -f "BinanceOrderTradingManager $TAG" 2>/dev/null; rm -rf "$W"; }; trap cleanup EXIT
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "PASS $1"; else FAILN=$((FAILN+1)); echo "FAIL $1"; fi; }
mkdir -p $W/ing/target $W/ing/conf $W/d; TS=20261115_1015
printf 'qf4b-old' > $W/ing/target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS; OLD=$(md5sum < $W/ing/target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS | cut -c1-32)
echo 'export X=1' > $W/ing/conf/env.sh.bak_ingqf_$TS
python3 -I - "$W/vfin/binance-java-sdk-1.2.4.jar" "$W/vold/binance-java-sdk-1.2.4.jar" <<'PYEOF'
import sys, os, zipfile
for p, cls in ((sys.argv[1], 'com/binance/chuyennd/aerospike/MinuteFin.class'), (sys.argv[2], 'com/binance/chuyennd/aerospike/Other.class')):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_STORED) as z: z.writestr(cls, b'x')
PYEOF
FINMD5=$(md5sum < $W/vfin/binance-java-sdk-1.2.4.jar | cut -c1-32)
vtm() {   # $1 = jar, $2 = LIVE_FIN_GUARD ("" = khong dat)
  pkill -f "BinanceOrderTradingManager $TAG" 2>/dev/null; sleep 0.3
  if [ -n "$2" ]; then env LIVE_FIN_GUARD="$2" setsid bash -c "exec 3<$1; exec -a 'java trading.BinanceOrderTradingManager $TAG' sleep 300" >/dev/null 2>&1 < /dev/null &
  else env -u LIVE_FIN_GUARD setsid bash -c "exec 3<$1; exec -a 'java trading.BinanceOrderTradingManager $TAG' sleep 300" >/dev/null 2>&1 < /dev/null & fi
  sleep 0.5; }
run() { env INGQF_SSH="bash -c" ING_DIR=$W/ing DEPLOY_DIR=$W/d OLD_MD5=$OLD VTM_PAT="trading[.]BinanceOrderTradingManager $TAG" DRY=1 "$@" bash $RB $TS 2>&1; }
vtm $W/vfin/binance-java-sdk-1.2.4.jar ""
OUT=$(run); RC=$?
chk "v_t_m jar fin (class MinuteFin) + guard BAT (vang) => TU CHOI rc=1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'REFUSE_VTM vtm_dang_chay_jar_fin_guard' && echo \"\$OUT\" | grep -q 'TU CHOI'"
vtm $W/vfin/binance-java-sdk-1.2.4.jar "1"
OUT=$(run); RC=$?
chk "guard =1 => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q REFUSE_VTM"
OUT=$(run FORCE=1); RC=$?
chk "FORCE=1 => bo qua, DRY dung rc=0" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'FORCE=1: BO QUA' && echo \"\$OUT\" | grep -q 'DRY=1: dung'"
for g in 0 false OFF No; do
  vtm $W/vfin/binance-java-sdk-1.2.4.jar "$g"
  OUT=$(run); RC=$?
  chk "jar fin nhung LIVE_FIN_GUARD=$g (tat) => cho phep (DRY rc=0)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'guard TAT' && ! echo \"\$OUT\" | grep -q REFUSE_VTM"
done
vtm $W/vold/binance-java-sdk-1.2.4.jar ""
OUT=$(run); RC=$?
chk "v_t_m jar cu (khong MinuteFin, md5 ngoai danh sach) => cho phep" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'OK vtm_khong_phai_jar_fin'"
OUT=$(run VTM_FIN_MD5S="$(md5sum < $W/vold/binance-java-sdk-1.2.4.jar | cut -c1-32)"); RC=$?
chk "md5 jar dang chay thuoc VTM_FIN_MD5S => TU CHOI (kiem md5)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q REFUSE_VTM"
pkill -f "BinanceOrderTradingManager $TAG"; sleep 0.3
OUT=$(run); RC=$?
chk "khong thay process v_t_m => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'REFUSE_VTM khong_thay_process_v_t_m'"
echo "TEST_ROLLBACK_INGEST_FIN PASS=$PASS FAIL=$FAILN"
[ $FAILN = 0 ]
