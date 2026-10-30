#!/usr/bin/env bash
# =============================================================================
# deploy_ingest_qf.sh — VA NHANH collectData 242 (INGEST-QF2), chay tren ORACLE:
#   DRY=1 bash ~/claude_master/deploy/deploy_ingest_qf.sh     # CHI DOC, khong doi gi
#   bash ~/claude_master/deploy/deploy_ingest_qf.sh            # go YES 1 lan
#   FORCE_TIME=1 ...                                           # bo khung gio (chi khi MASTER bao)
# Doi: jar collectData (md5 OLD_MD5 -> JAR_MD5) + env: INGEST_SCHEDULED_RESTART_HOURS=0, INGEST_REST_WEIGHT_CAP=300,
#      JAVA_TOOL_OPTIONS=-Xmx2g. KHONG dung v_t_m/LEGACY. Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md (+ADD1/1b/1c).
# Ma thoat: 0 xong | 1 dung truoc khi doi HOAC da tu khoi phuc OK | 2 khoi phuc LOI (bao MASTER ngay).
# Rollback sau nay: bash ~/claude_master/deploy/rollback_ingest_qf.sh <TS>
# =============================================================================
set -uo pipefail
JAR_SRC=/home/ubuntu/claude_master/ing1030/jar/binance-java-sdk-1.2.4.jar_ingqf2_69e36d03
JAR_MD5=2e0a3676bd8eafdbef2a374a69ba9bee
OLD_MD5=cb02d85e4f045c6cbdc8d94c18e188f1
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"
C=/home/chuyennd/java/collectData
A=/home/chuyennd/java/v_t_m
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M)
D=/home/ubuntu/claude_master/deploy
RESTART_R=$D/ingqf_restart_remote.sh
CHECK_R=$D/ingqf_check_remote.sh
DRY=${DRY:-0}
LOG=$D/deploy_ingest_qf_${TS}$([ "$DRY" = 1 ] && echo _dry).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die() { say "DUNG (khong doi gi): $*"; say "Log: $LOG"; exit 1; }
# MIN-4: du script chet o dau, PAUSE watchdog LEGACY tren 242 LUON duoc go
trap '$S "rm -f /var/lib/h242_watchdog/PAUSE" < /dev/null > /dev/null 2>&1' EXIT
say "=== deploy_ingest_qf (QF2) TS=$TS DRY=$DRY jar=$JAR_MD5 ==="
[ -f "$RESTART_R" ] && [ -f "$CHECK_R" ] || die "thieu $RESTART_R / $CHECK_R"
[ "$(md5sum < "$RESTART_R" | cut -c1-32)" = "6c50666d2072827343f7022434f22239" ] || die "md5 $RESTART_R sai"
[ "$(md5sum < "$CHECK_R" | cut -c1-32)" = "b6ab182d8b44381120726aa32327d7ca" ] || die "md5 $CHECK_R sai"

# ---- khung gio: phut :10-:44, tranh gio 07/19, tranh 00:50-01:20 va 12:50-13:20 (+07); cho toi da 90'
if [ "${FORCE_TIME:-0}" != 1 ] && [ "$DRY" != 1 ]; then
  ok=0
  for i in $(seq 1 540); do
    H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
    ok=1; case "$H" in 7|19) ok=0;; esac
    { [ "$M" -lt 10 ] || [ "$M" -gt 44 ]; } && ok=0
    { [ "$H" = 0 ] && [ "$M" -ge 50 ]; } && ok=0
    { [ "$H" = 1 ] && [ "$M" -le 20 ]; } && ok=0
    { [ "$H" = 12 ] && [ "$M" -ge 50 ]; } && ok=0
    { [ "$H" = 13 ] && [ "$M" -le 20 ]; } && ok=0
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
PRE=$($S "bash -s -- $C $OLD_MD5 $JAR_MD5" <<'EOF'
C=$1; OLD=$2; NEW=$3
cd "$C" || { echo "FAIL cd_collectData"; exit 0; }
P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1); N=$(pgrep -fc 'websocket.BinanceDataIngestor')
[ "$N" = 1 ] && echo "OK ingest_pid=$P start=$(ps -o lstart= -p $P | xargs)" || echo "FAIL so_process_ingest=$N"
FD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1); J=$(readlink "$FD"); JM=$(md5sum < "$FD" 2>/dev/null | cut -c1-32)
[ "$JM" = "$OLD" ] && echo "OK jar_dang_chay_md5=$JM (ban goc 0a57ea3f)" || { [ "$JM" = "$NEW" ] && echo "FAIL da_la_jar_moi (da deploy?)" || echo "FAIL jar_dang_chay_md5_la=$JM"; }
[ "$J" = "$C/target/binance-java-sdk-1.2.4.jar" ] && echo "OK duong_jar" || echo "FAIL duong_jar_khac=$J"
[ -x bin/daemon.sh ] && echo "OK bin/daemon.sh" || echo "FAIL khong_co_bin/daemon.sh"
[ -f conf/env.sh ] && echo "OK conf/env.sh" || echo "FAIL khong_co_conf/env.sh"
grep -E '^export (INGEST_|KLINE_INGEST_MODE|JAVA_TOOL_OPTIONS)' conf/env.sh | sed 's/^/INFO env: /'
grep -q '^export KLINE_INGEST_MODE=ws_settle' conf/env.sh && echo "OK mode_ws_settle" || echo "FAIL mode_khong_phai_ws_settle"
grep -q '^export JAVA_TOOL_OPTIONS=' conf/env.sh && echo "FAIL env_da_co_JAVA_TOOL_OPTIONS (xem tay)" || echo "OK chua_co_JAVA_TOOL_OPTIONS"
F=$(df -BM --output=avail / | tail -1 | tr -dc 0-9); [ "$F" -ge 2000 ] && echo "OK dia_trong=${F}MB" || echo "FAIL dia_trong=${F}MB"
MA=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$MA" -ge 1000 ] && echo "OK mem_avail=${MA}MB" || echo "FAIL mem_avail=${MA}MB"
echo "INFO rss_ingest_MB=$(awk '/VmRSS/{print int($2/1024)}' /proc/$P/status)"
TP=$(pgrep -f 'trading.BinanceOrderTradingManager' | head -1); [ -n "$TP" ] && echo "OK legacy_pid=$TP" || echo "FAIL legacy_khong_chay"
[ -f /var/lib/h242_watchdog/PAUSE ] && echo "FAIL PAUSE_watchdog_dang_bat (ai do dang thao tac?)" || echo "OK khong_PAUSE"
echo "INFO restart_JVM_hom_nay=$(grep -a 'Restart: Reset' logs/nohup.out | grep -c "^$(date +%Y-%m-%d)")"
EOF
) || die "ssh kiem loi"
echo "$PRE"
echo "$PRE" | grep -q '^FAIL' && die "kiem chi doc FAIL (xem tren)"
PRE_LEG=$(echo "$PRE" | grep -o 'legacy_pid=[0-9]*' | tr -dc 0-9)
if [ "$DRY" = 1 ]; then say "DRY=1: dung o day (khong copy jar, khong doi env, khong restart)."; exit 0; fi

say ">>> Sap: copy jar moi + 3 dong env (restart lich TAT, cap 300, -Xmx2g) + RESTART collectData (~30 s gian doan; LEGACY khong dung). Go YES:"
read -r ANS
[ "$ANS" = "YES" ] || die "Huy."

say "--- 2. copy jar sang 242 + backup"
$SCP "$JAR_SRC" root@103.157.218.242:$C/target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS < /dev/null || die "scp jar loi"
BK=$($S "bash -s -- $C $TS $JAR_MD5" <<'EOF'
C=$1; TS=$2; NEW=$3; cd "$C" || { echo "FAIL cd"; exit 0; }
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS | cut -c1-32)" = "$NEW" ] || { echo "FAIL md5_jar_tren_242"; exit 0; }
\cp -fp target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS || { echo "FAIL backup_jar"; exit 0; }
\cp -fp conf/env.sh conf/env.sh.bak_ingqf_$TS || { echo "FAIL backup_env"; exit 0; }
echo "OK backup TS=$TS"
EOF
) || die "ssh backup loi"
echo "$BK"; echo "$BK" | grep -q '^FAIL' && die "backup FAIL"

rollback() {   # khoi phuc jar + env tu backup TS (mv inode moi), restart, kiem jar cu dang chay
  say "!!! KHOI PHUC (rollback) TS=$TS"
  RB=$($S "bash -s -- $C $TS" <<'EOF'
C=$1; TS=$2; cd "$C" || { echo "FAIL cd"; exit 0; }
[ -f target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS ] && \cp -fp target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS target/.jar_rb_tmp_$TS && mv -f target/.jar_rb_tmp_$TS target/binance-java-sdk-1.2.4.jar || echo "FAIL khong_co_backup_jar"
[ -f conf/env.sh.bak_ingqf_$TS ] && \cp -fp conf/env.sh.bak_ingqf_$TS conf/env.sh || echo "FAIL khong_co_backup_env"
echo "OK da_chep_lai_backup"
EOF
)
  echo "$RB"
  R2=$($S "bash -s -- $C" < "$RESTART_R"); echo "$R2"
  sleep 60
  K2=$($S "bash -s -- $C $A $OLD_MD5 ${PRE_LEG:-0} old" < "$CHECK_R"); echo "$K2"
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
echo 'export JAVA_TOOL_OPTIONS="-Xmx2g"' >> conf/env.sh
N=$(diff conf/env.sh.bak_ingqf_$TS conf/env.sh | grep -c '^>')
[ "$N" -ge 1 ] && [ "$N" -le 3 ] && echo "OK env_doi_${N}_dong" || echo "FAIL env_diff=$N"
# mv (inode moi): JVM cu dang mo jar cu van doc inode cu toi khi restart — KHONG cp de len file dang mo
\cp -fp target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS target/.jar_new_tmp_$TS && mv -f target/.jar_new_tmp_$TS target/binance-java-sdk-1.2.4.jar || echo "FAIL cai_jar"
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NEW" ] && echo "OK jar_moi_tai_cho" || echo "FAIL md5_jar_sau_cp"
EOF
) || { say "ssh env/jar loi"; rollback; }
echo "$EN"; echo "$EN" | grep -q '^FAIL' && rollback

say "--- 4. restart collectData (giay 08-20; PAUSE watchdog; chay tach khoi ssh)"
RS=$($S "bash -s -- $C" < "$RESTART_R") || { say "ssh restart loi"; rollback; }
echo "$RS"; echo "$RS" | grep -q '^FAIL' && rollback

say "--- 5. kiem on dinh (moi 30 s, toi da 14'): repair khoi dong xong -> tuoi gia; 2 dong KLINE-COVER; 0 ban/429/418; LEGACY"
K=""
for i in $(seq 1 28); do
  sleep 30
  K=$($S "bash -s -- $C $A $JAR_MD5 ${PRE_LEG:-0} new" < "$CHECK_R") || { say "ssh kiem loi (lan $i)"; continue; }
  if echo "$K" | grep -q '^FAIL'; then echo "$K"; say "Co FAIL sau deploy"; rollback; fi
  echo "$K" | grep -q '^WAIT' || break
  say "cho: $(echo "$K" | grep '^WAIT' | tr '\n' ' ')"
done
echo "$K"
echo "$K" | grep -q '^WAIT' && { say "Het 14' van chua du dieu kien on dinh"; rollback; }
echo "$K" | grep -q '^OK kline_phu_phut_da_chot' || { say "khong doc duoc ket qua kiem"; rollback; }

say "XONG. collectData chay jar $JAR_MD5. Backup TS=$TS (jar .bak_ingqf_$TS, env .bak_ingqf_$TS)."
say "Rollback 1 lenh: bash $D/rollback_ingest_qf.sh $TS"
say "Bao MASTER 'deploy_ingest_qf xong TS=$TS' — MASTER cham 72h theo PREREG_INGEST_QUICKFIX. Log: $LOG"
exit 0
