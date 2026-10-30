#!/usr/bin/env bash
# =============================================================================
# deploy_ingest_qf.sh — VA NHANH collectData 242 (giai doan 2a INGEST-QF), chay tren ORACLE:
#   DRY=1 bash ~/claude_master/deploy/deploy_ingest_qf.sh     # CHI DOC, khong doi gi
#   bash ~/claude_master/deploy/deploy_ingest_qf.sh            # go YES 1 lan
#   FORCE_TIME=1 ...                                           # bo khung gio (chi khi MASTER bao)
# Doi: jar collectData (md5 cb02d85e -> JAR_MD5 duoi) + env them INGEST_SCHEDULED_RESTART_HOURS=0, INGEST_REST_WEIGHT_CAP=300.
# KHONG dung v_t_m/LEGACY. Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md (f18c2c9e). Code 088f53d6 (nhanh fix/ingest-quickfix).
# Ma thoat: 0 xong | 1 dung truoc khi doi HOAC da tu khoi phuc OK | 2 khoi phuc LOI (bao MASTER ngay).
# Rollback sau nay: bash ~/claude_master/deploy/rollback_ingest_qf.sh <TS>
# =============================================================================
set -uo pipefail
JAR_SRC=/home/ubuntu/claude_master/ing1030/jar/binance-java-sdk-1.2.4.jar_ingqf_088f53d6
JAR_MD5=e75c4a65bc5ebb448e9fea92308a64f4
OLD_MD5=cb02d85e4f045c6cbdc8d94c18e188f1
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"
C=/home/chuyennd/java/collectData
A=/home/chuyennd/java/v_t_m
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M)
D=/home/ubuntu/claude_master/deploy
DRY=${DRY:-0}
LOG=$D/deploy_ingest_qf_${TS}$([ "$DRY" = 1 ] && echo _dry).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die() { say "DUNG (khong doi gi): $*"; say "Log: $LOG"; exit 1; }
say "=== deploy_ingest_qf TS=$TS DRY=$DRY ==="

# ---- khung gio: phut :10-:44, tranh gio 07/19, tranh 00:50-01:20 va 12:50-13:20 (+07); cho toi da 90'
if [ "${FORCE_TIME:-0}" != 1 ] && [ "$DRY" != 1 ]; then
  for i in $(seq 1 540); do
    H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
    ok=1; case "$H" in 7|19) ok=0;; esac
    [ "$M" -lt 10 ] || [ "$M" -gt 44 ] && ok=0
    { [ "$H" = 0 ] && [ "$M" -ge 50 ]; } || { [ "$H" = 1 ] && [ "$M" -le 20 ]; } && ok=0
    { [ "$H" = 12 ] && [ "$M" -ge 50 ]; } || { [ "$H" = 13 ] && [ "$M" -le 20 ]; } && ok=0
    [ $ok = 1 ] && break
    [ $i = 1 ] && say "ngoai khung gio ($H:$M) — cho (toi da 90')..."
    sleep 10
  done
  [ $ok = 1 ] || die "het 90' van ngoai khung gio"
fi

say "--- 0. jar tren Oracle"
[ -f "$JAR_SRC" ] || die "khong co $JAR_SRC"
[ "$(md5sum < "$JAR_SRC" | cut -c1-32)" = "$JAR_MD5" ] || die "md5 jar nguon sai"
say "OK jar nguon md5 $JAR_MD5"

say "--- 1. CHI DOC 242"
PRE=$($S "bash -s -- $C $A $OLD_MD5 $JAR_MD5" <<'EOF'
C=$1; A=$2; OLD=$3; NEW=$4
cd "$C" || { echo "FAIL cd_collectData"; exit 0; }
P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
N=$(pgrep -fc 'websocket.BinanceDataIngestor')
[ "$N" = 1 ] && echo "OK ingest_pid=$P start=$(ps -o lstart= -p $P | xargs)" || echo "FAIL so_process_ingest=$N"
FD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
J=$(readlink "$FD")
echo "INFO jar_dang_mo=$J"
JM=$(md5sum < "$FD" 2>/dev/null | cut -c1-32)
[ "$JM" = "$OLD" ] && echo "OK jar_dang_chay_md5=$JM (dung ban goc 0a57ea3f)" || { [ "$JM" = "$NEW" ] && echo "FAIL da_la_jar_moi (da deploy?)" || echo "FAIL jar_dang_chay_md5_la=$JM"; }
[ "$J" = "$C/target/binance-java-sdk-1.2.4.jar" ] && echo "OK duong_jar" || echo "FAIL duong_jar_khac=$J"
[ -x bin/daemon.sh ] && echo "OK bin/daemon.sh" || echo "FAIL khong_co_bin/daemon.sh"
[ -f conf/env.sh ] && echo "OK conf/env.sh" || echo "FAIL khong_co_conf/env.sh"
grep -E '^export (INGEST_|KLINE_INGEST_MODE)' conf/env.sh | sed 's/^/INFO env: /'
grep -q '^export KLINE_INGEST_MODE=ws_settle' conf/env.sh && echo "OK mode_ws_settle" || echo "FAIL mode_khong_phai_ws_settle"
F=$(df -BM --output=avail / | tail -1 | tr -dc 0-9); [ "$F" -ge 2000 ] && echo "OK dia_trong=${F}MB" || echo "FAIL dia_trong=${F}MB"
TP=$(pgrep -f 'trading.BinanceOrderTradingManager' | head -1)
[ -n "$TP" ] && echo "OK legacy_pid=$TP" || echo "FAIL legacy_khong_chay"
L=logs/nohup.out
T=$(grep -a 'Ch.t n.n ph.t' $L | tail -1 | grep -o 'Total: [0-9]*' | tr -dc 0-9)
echo "OK tong_symbol_chot_truoc=$T"
echo "INFO restart_JVM_hom_nay=$(grep -a 'Restart: Reset' $L | grep -c "^$(date +%Y-%m-%d)")"
command -v aql >/dev/null && echo "INFO co_aql" || echo "INFO khong_co_aql (bo kiem ts price bang aql, dung metric log)"
EOF
) || die "ssh kiem loi"
echo "$PRE"
echo "$PRE" | grep -q '^FAIL' && die "kiem chi doc FAIL (xem tren)"
PRE_TOTAL=$(echo "$PRE" | grep -o 'tong_symbol_chot_truoc=[0-9]*' | tr -dc 0-9)
PRE_LEG=$(echo "$PRE" | grep -o 'legacy_pid=[0-9]*' | tr -dc 0-9)
if [ "$DRY" = 1 ]; then say "DRY=1: dung o day (khong copy jar, khong doi env, khong restart)."; exit 0; fi

say ">>> Sap: copy jar moi + them 2 dong env + RESTART collectData (~20-40 s gian doan ingest; LEGACY khong dung). Go YES:"
read -r ANS
[ "$ANS" = "YES" ] || die "Huy."

say "--- 2. copy jar sang 242 + backup"
$SCP "$JAR_SRC" root@103.157.218.242:$C/target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS || die "scp jar loi"
BK=$($S "bash -s -- $C $TS $JAR_MD5" <<'EOF'
C=$1; TS=$2; NEW=$3; cd "$C" || { echo "FAIL cd"; exit 0; }
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS | cut -c1-32)" = "$NEW" ] || { echo "FAIL md5_jar_tren_242"; exit 0; }
\cp -fp target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS || { echo "FAIL backup_jar"; exit 0; }
\cp -fp conf/env.sh conf/env.sh.bak_ingqf_$TS || { echo "FAIL backup_env"; exit 0; }
echo "OK backup TS=$TS"
EOF
) || die "ssh backup loi"
echo "$BK"; echo "$BK" | grep -q '^FAIL' && die "backup FAIL"

RESTART_R=$D/ingqf_restart_remote.sh
CHECK_R=$D/ingqf_check_remote.sh
[ -f "$RESTART_R" ] && [ -f "$CHECK_R" ] || die "thieu $RESTART_R / $CHECK_R"

rollback() {   # khoi phuc jar + env tu backup TS, restart, kiem jar cu dang chay
  say "!!! KHOI PHUC (rollback) TS=$TS"
  RB=$($S "bash -s -- $C $TS" <<'EOF'
C=$1; TS=$2; cd "$C" || { echo "FAIL cd"; exit 0; }
# mv (inode moi) — KHONG cp de len jar JVM dang mo
[ -f target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS ] && \cp -fp target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS target/.jar_rb_tmp_$TS && mv -f target/.jar_rb_tmp_$TS target/binance-java-sdk-1.2.4.jar || echo "FAIL khong_co_backup_jar"
[ -f conf/env.sh.bak_ingqf_$TS ] && \cp -fp conf/env.sh.bak_ingqf_$TS conf/env.sh || echo "FAIL khong_co_backup_env"
echo "OK da_chep_lai_backup"
EOF
)
  echo "$RB"
  R2=$($S "bash -s -- $C" < "$RESTART_R"); echo "$R2"
  sleep 100
  K2=$($S "bash -s -- $C $A $OLD_MD5 ${PRE_TOTAL:-0} ${PRE_LEG:-0} old" < "$CHECK_R"); echo "$K2"
  if echo "$RB$R2" | grep -q '^FAIL' || ! echo "$K2" | grep -q '^OK jar_md5'; then
    say "KHOI PHUC LOI — bao MASTER NGAY. Log: $LOG"; exit 2
  fi
  say "Da khoi phuc ban cu (md5 $OLD_MD5). Log: $LOG"; exit 1
}

say "--- 3. env + cai jar"
EN=$($S "bash -s -- $C $TS $JAR_MD5" <<'EOF'
C=$1; TS=$2; NEW=$3; cd "$C" || { echo "FAIL cd"; exit 0; }
for kv in INGEST_SCHEDULED_RESTART_HOURS=0 INGEST_REST_WEIGHT_CAP=300; do
  k=${kv%%=*}
  if grep -q "^export $k=" conf/env.sh; then sed -i -E "s#^export $k=.*#export $kv#" conf/env.sh; else echo "export $kv" >> conf/env.sh; fi
done
N=$(diff conf/env.sh.bak_ingqf_$TS conf/env.sh | grep -c '^>')
[ "$N" -ge 1 ] && [ "$N" -le 2 ] && echo "OK env_doi_${N}_dong" || echo "FAIL env_diff=$N"
# mv (inode moi): JVM cu dang mo jar cu van doc inode cu cho toi khi restart — KHONG cp de len file dang mo
\cp -fp target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS target/.jar_new_tmp_$TS && mv -f target/.jar_new_tmp_$TS target/binance-java-sdk-1.2.4.jar || echo "FAIL cai_jar"
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NEW" ] && echo "OK jar_moi_tai_cho" || echo "FAIL md5_jar_sau_cp"
EOF
) || { say "ssh env/jar loi"; rollback; }
echo "$EN"; echo "$EN" | grep -q '^FAIL' && rollback

say "--- 4. restart collectData (giay 08-20; PAUSE watchdog)"
RS=$($S "bash -s -- $C" < "$RESTART_R") || { say "ssh restart loi"; rollback; }
echo "$RS"; echo "$RS" | grep -q '^FAIL' && rollback

say "--- 5. kiem sau ~150 s (>=2 dong [REST-BUDGET], chot nen phut moi, LEGACY, price)"
sleep 150
K=$($S "bash -s -- $C $A $JAR_MD5 ${PRE_TOTAL:-0} ${PRE_LEG:-0} new" < "$CHECK_R") || { say "ssh kiem loi"; rollback; }
echo "$K"
echo "$K" | grep -q '^FAIL' && { say "Co FAIL sau deploy"; rollback; }

say "XONG. collectData chay jar $JAR_MD5. Backup TS=$TS (jar .bak_ingqf_$TS, env .bak_ingqf_$TS)."
say "Rollback 1 lenh: bash $D/rollback_ingest_qf.sh $TS"
say "Bao MASTER 'deploy_ingest_qf xong TS=$TS' — MASTER cham 72h theo PREREG_INGEST_QUICKFIX. Log: $LOG"
exit 0
