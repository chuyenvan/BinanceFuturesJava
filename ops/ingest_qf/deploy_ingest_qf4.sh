#!/usr/bin/env bash
# =============================================================================
# deploy_ingest_qf4.sh — QF4 collectData 242 (REST bu mat WS +2 s, thieu_luc_chot; prereg ADDENDUM 3/3b), chay tren ORACLE:
#   DRY=1 bash ~/claude_master/deploy/deploy_ingest_qf4.sh     # CHI DOC, khong doi gi
#   bash ~/claude_master/deploy/deploy_ingest_qf4.sh            # go YES 1 lan
#   FORCE_TIME=1 ...                                           # bo khung gio (chi khi MASTER bao)
# Doi: CHI jar collectData (md5 OLD_MD5=QF3 -> JAR_MD5=QF4); env GIU NGUYEN (QF3 da co restart lich 0, cap 300, -Xmx2g).
#      CHI restart collectData; KHONG dung v_t_m/LEGACY. Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md (+ADD1/1b/1c).
# Ma thoat: 0 xong | 1 dung truoc khi doi HOAC da tu khoi phuc OK | 2 khoi phuc LOI (bao MASTER ngay).
# Rollback sau nay: bash ~/claude_master/deploy/rollback_ingest_qf4.sh <TS>
# =============================================================================
set -uo pipefail
JAR_SRC=/home/ubuntu/claude_master/ing1030/jar/binance-java-sdk-1.2.4.jar_ingqf4_f84cf2d7
JAR_MD5=6b55dd17b92c66075ff0f08b185b8ca9
OLD_MD5=a31fdd6caf12ce35c12b839a3cced929
# INGQF_SSH / INGQF_SCP chi de TEST (test_pause_trap.sh); prod de mac dinh
S=${INGQF_SSH:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP=${INGQF_SCP:-"scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
PF=/var/lib/h242_watchdog/PAUSE
C=/home/chuyennd/java/collectData
A=/home/chuyennd/java/v_t_m
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M)
D=/home/ubuntu/claude_master/deploy
RESTART_R=$D/ingqf_restart_remote.sh
CHECK_R=$D/ingqf4_check_remote.sh
DRY=${DRY:-0}
LOG=$D/deploy_ingest_qf4_${TS}$([ "$DRY" = 1 ] && echo _dry).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die() { say "DUNG (khong doi gi): $*"; say "Log: $LOG"; exit 1; }
# [QF3, A1_QF2 MAJ-B] PAUSE watchdog mang TOKEN cua lan chay nay; trap CHI dat khi chinh script bat dau restart (OWN_PAUSE=1)
# va CHI go PAUSE neu noi dung = TOKEN. DRY=1 khong bao gio dat trap, khong ghi gi len 242.
TOKEN="ingqf_${TS}_$$"
OWN_PAUSE=0
own_pause_cleanup() {
  [ "$OWN_PAUSE" = 1 ] || return 0
  $S "f=$PF; c=\$(cat \$f 2>/dev/null); { [ \"\$c\" = '$TOKEN' ] || [ \"\$c\" = '${TOKEN}_rb' ]; } && rm -f \$f && echo PAUSE_cua_minh_da_go || true" < /dev/null 2>/dev/null
}
say "=== deploy_ingest_qf4 (QF4) TS=$TS DRY=$DRY jar=$JAR_MD5 token=$TOKEN ==="
[ -f "$RESTART_R" ] && [ -f "$CHECK_R" ] || die "thieu $RESTART_R / $CHECK_R"
[ "$(md5sum < "$RESTART_R" | cut -c1-32)" = "35f60aff9b319346a28e3c10c91f9df8" ] || die "md5 $RESTART_R sai"
[ "$(md5sum < "$CHECK_R" | cut -c1-32)" = "0afe05bf06b4224f271febf0b64477cd" ] || die "md5 $CHECK_R sai"

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
[ "$JM" = "$OLD" ] && echo "OK jar_dang_chay_md5=$JM (QF3 3dd53a91)" || { [ "$JM" = "$NEW" ] && echo "FAIL da_la_jar_moi (da deploy?)" || echo "FAIL jar_dang_chay_md5_la=$JM"; }
[ "$J" = "$C/target/binance-java-sdk-1.2.4.jar" ] && echo "OK duong_jar" || echo "FAIL duong_jar_khac=$J"
[ -x bin/daemon.sh ] && echo "OK bin/daemon.sh" || echo "FAIL khong_co_bin/daemon.sh"
[ -f conf/env.sh ] && echo "OK conf/env.sh" || echo "FAIL khong_co_conf/env.sh"
grep -E '^export (INGEST_|KLINE_INGEST_MODE|JAVA_TOOL_OPTIONS)' conf/env.sh | sed 's/^/INFO env: /'
grep -q '^export KLINE_INGEST_MODE=ws_settle' conf/env.sh && echo "OK mode_ws_settle" || echo "FAIL mode_khong_phai_ws_settle"
grep -q '^export JAVA_TOOL_OPTIONS=.*-Xmx2g' conf/env.sh && echo "OK env_co_Xmx2g" || echo "FAIL env_thieu_JAVA_TOOL_OPTIONS_Xmx2g (QF3 chua cai?)"
grep -q '^export INGEST_SCHEDULED_RESTART_HOURS=0' conf/env.sh && echo "OK env_restart_lich_0" || echo "FAIL env_restart_lich_khac_0"
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

say ">>> Sap: copy jar QF4 (env GIU NGUYEN) + RESTART RIENG collectData (~30 s gian doan; v_t_m/LEGACY khong dung). Go YES:"
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
  if [ "${1:-}" = no_restart ]; then   # process CHUA restart (van chay jar cu tu inode cu) => chi tra file, khong restart
    echo "$RB" | grep -q '^FAIL' && { say "KHOI PHUC FILE LOI — bao MASTER NGAY. Log: $LOG"; exit 2; }
    say "Da tra jar/env ve ban cu, collectData KHONG bi restart (van chay ban cu). Log: $LOG"; exit 1
  fi
  OWN_PAUSE=1
  R2=$($S "bash -s -- $C ${TOKEN}_rb" < "$RESTART_R"); echo "$R2"
  sleep 60
  K2=$($S "bash -s -- $C $A $OLD_MD5 ${PRE_LEG:-0} old ${TOKEN}_rb" < "$CHECK_R"); echo "$K2"
  if echo "$RB$R2" | grep -q '^FAIL' || ! echo "$K2" | grep -q '^OK jar_md5'; then
    say "KHOI PHUC LOI — bao MASTER NGAY. Log: $LOG"; exit 2
  fi
  say "Da khoi phuc ban cu (md5 $OLD_MD5). Log: $LOG"; exit 1
}

say "--- 3. cai jar (env giu nguyen)"
EN=$($S "bash -s -- $C $TS $JAR_MD5" <<'EOF'
C=$1; TS=$2; NEW=$3; cd "$C" || { echo "FAIL cd"; exit 0; }
cmp -s conf/env.sh.bak_ingqf_$TS conf/env.sh && echo "OK env_khong_doi" || echo "FAIL env_bi_doi_ngoai_y_muon"
# mv (inode moi): JVM cu dang mo jar cu van doc inode cu toi khi restart — KHONG cp de len file dang mo
\cp -fp target/binance-java-sdk-1.2.4.jar.new_ingqf_$TS target/.jar_new_tmp_$TS && mv -f target/.jar_new_tmp_$TS target/binance-java-sdk-1.2.4.jar || echo "FAIL cai_jar"
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NEW" ] && echo "OK jar_moi_tai_cho" || echo "FAIL md5_jar_sau_cp"
EOF
) || { say "ssh env/jar loi"; rollback; }
echo "$EN"; echo "$EN" | grep -q '^FAIL' && rollback

say "--- 4. restart collectData (giay 08-20; PAUSE watchdog co TOKEN; chay tach khoi ssh)"
OWN_PAUSE=1
trap own_pause_cleanup EXIT   # [QF3] chi tu day: chi go PAUSE mang TOKEN cua chinh lan chay nay
RS=$($S "bash -s -- $C $TOKEN" < "$RESTART_R") || { say "ssh restart loi"; rollback; }
echo "$RS"
if echo "$RS" | grep -q 'PAUSE_cua_nguoi_khac'; then
  say "Co nguoi khac dang PAUSE watchdog (dang thao tac 242) — KHONG restart, tra file ve cu"; rollback no_restart
fi
echo "$RS" | grep -q '^FAIL' && rollback

say "--- 5. kiem on dinh (moi 30 s): repair khoi dong (con tien thi cho, toi da 60'; dung tien 5' = ket); sau repair toi da 14'"
K=""; LASTP=-1; STALL=0; AFTER=0
for i in $(seq 1 150); do
  sleep 30
  K=$($S "bash -s -- $C $A $JAR_MD5 ${PRE_LEG:-0} new $TOKEN" < "$CHECK_R") || { say "ssh kiem loi (lan $i)"; continue; }
  if echo "$K" | grep -q '^FAIL'; then echo "$K"; say "Co FAIL sau deploy"; rollback; fi
  echo "$K" | grep -q '^WAIT' || break
  RP=$(echo "$K" | grep -o 'REPAIR_PROGRESS=[0-9]*' | tr -dc 0-9)
  if [ -n "$RP" ]; then   # [QF3, MIN-D] dang repair: tien do con tang => cho; dung 10 lan kiem (5') => ket
    [ "$RP" -gt "$LASTP" ] && { STALL=0; LASTP=$RP; } || STALL=$((STALL + 1))
    [ $STALL -ge 10 ] && { echo "$K"; say "Repair khoi dong KET (tien do $RP khong tang 5')"; rollback; }
    [ $i -ge 120 ] && { echo "$K"; say "Repair khoi dong qua 60'"; rollback; }
  else
    AFTER=$((AFTER + 1))
    [ $AFTER -ge 28 ] && break
  fi
  say "cho: $(echo "$K" | grep '^WAIT' | tr '\n' ' ')"
done
echo "$K"
echo "$K" | grep -q '^WAIT' && { say "Het thoi gian van chua du dieu kien on dinh"; rollback; }
echo "$K" | grep -q '^OK kline_phu_phut_da_chot' || { say "khong doc duoc ket qua kiem"; rollback; }

say "XONG. collectData chay jar $JAR_MD5. Backup TS=$TS (jar .bak_ingqf_$TS, env .bak_ingqf_$TS)."
say "Rollback 1 lenh: bash $D/rollback_ingest_qf4.sh $TS"
say "Bao MASTER 'deploy_ingest_qf4 xong TS=$TS' — MASTER cham 72h theo PREREG_INGEST_QUICKFIX. Log: $LOG"
exit 0
