#!/usr/bin/env bash
# =============================================================================
# deploy_v12_dry.sh — deploy jar v1.2 (c3_live) len 242 o che do c3_live + LIVE_ADAPTER=dry (KHONG lenh that)
# Chay tren ORACLE:   bash ~/claude_master/deploy/deploy_v12_dry.sh
# Chay thu (chi doc, khong doi gi):   DRY=1 bash ~/claude_master/deploy/deploy_v12_dry.sh
# Bo chot gio (chi khi MASTER bao):   FORCE_TIME=1 ...      Bo chot ngay (chi khi MASTER bao): FORCE_DATE=1 ...
# !! Thay jar shadow dang chay (dcae2e2b) => TU CHOI chay truoc 2026-11-18 08:00 +07 (het cua so shadow) tru khi FORCE_DATE=1.
# Script tu dung o moi buoc sai; hoi YES (in hoa) truoc khi restart. Log: ~/claude_master/deploy/deploy_v12dry_<TS>.log
# Rollback: bash ~/claude_master/deploy/rollback_v12.sh <TS>
# Bien cho test (Oracle, server 242 GIA): SSH_242, SCP_242, RHOST, APP_DIR, LOGDIR, WD_PAUSE, NJ, NJ_MD5, OLD_MD5,
#   KILLSW_SH, EXINFO_CMD, POST_WAIT_S, POST_ROUNDS.
# =============================================================================
set -uo pipefail

SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}   # mau nhan dien process app (test: process gia)
NJ=${NJ:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry}
NJ_MD5=${NJ_MD5:-a55be721e574217c852beebcc07e6dc3}
OLD_MD5=${OLD_MD5:-dcae2e2bbb1a357bc15703b416d4dccb}
KILLSW_SH=${KILLSW_SH:-/home/ubuntu/claude_master/v12/c3live/ops/killsw_reset.sh}
WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}
EXINFO_CMD=${EXINFO_CMD:-"curl -s --max-time 30 https://fapi.binance.com/fapi/v1/exchangeInfo"}
POST_WAIT_S=${POST_WAIT_S:-120}
POST_ROUNDS=${POST_ROUNDS:-5}
DRY=${DRY:-0}
FORCE_TIME=${FORCE_TIME:-0}
FORCE_DATE=${FORCE_DATE:-0}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M)
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
LOG=$LOGDIR/deploy_v12dry_${TS}.log
exec > >(tee -a "$LOG") 2>&1

say()  { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die()  { say "DUNG: $*"; say "Log: $LOG"; exit 1; }
ok()   { say "OK: $*"; }

say "=== deploy v1.2 c3_live DRY  TS=$TS  DRY=$DRY ==="

# ---------------------------------------------------------------- 0. chot ngay + gio
NOT_BEFORE=$(date -d '2026-11-18 08:00 +07' +%s)
if [ "$(date +%s)" -lt "$NOT_BEFORE" ] && [ "$FORCE_DATE" != 1 ]; then
  [ "$DRY" = 1 ] && say "CANH BAO: truoc 2026-11-18 08:00 +07 (cua so shadow) — ban that se TU CHOI (DRY van chay kiem tra)." \
                 || die "truoc 2026-11-18 08:00 +07: deploy se thay jar shadow dang danh gia. Chi chay sau ngay do (hoac FORCE_DATE=1 khi MASTER bao)."
fi
H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
time_ok() {
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1          # chi phut :10-:44
  case "$H" in 7|19) return 1;; esac                       # 07:xx/19:xx
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi   # tranh 00:50-01:20, 12:50-13:20
  return 0
}
if [ "$DRY" != 1 ] && [ "$FORCE_TIME" != 1 ]; then
  time_ok || die "Gio hien tai $H:$M (+07) khong hop le. Chay lai trong phut :10-:44, tranh 07:xx, 19:xx, 00:50-01:20, 12:50-13:20."
  ok "gio $H:$M hop le"
fi

# ---------------------------------------------------------------- 1. kiem cuc bo
[ -f "$NJ" ] || die "khong thay jar $NJ"
[ "$(md5sum < "$NJ" | cut -c1-32)" = "$NJ_MD5" ] || die "md5 jar moi sai (mong $NJ_MD5)"
ok "jar moi md5 $NJ_MD5"
[ -f "$KILLSW_SH" ] || die "khong thay $KILLSW_SH"
bash -n "$KILLSW_SH" || die "cu phap killsw_reset.sh loi"
ok "killsw_reset.sh co, cu phap OK"

# ---------------------------------------------------------------- 2. kiem 242 (chi doc)
say "--- kiem 242 (chi doc)"
PRE=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $OLD_MD5" <<'EOF'
A=$1; OLD=$2; cd "$A" || { echo "FAIL cd"; exit 0; }
J=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)
[ "$J" = "$OLD" ] && echo "OK jar_dang_chay=$J (dcae2e2b)" || echo "FAIL jar_dang_chay=$J (mong doi $OLD)"
NP=$(pgrep -fc "$PP")
[ "$NP" = 1 ] && echo "OK so_process=1" || echo "FAIL so_process=$NP"
P=$(pgrep -f "$PP" | head -1)
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "$E" | grep -qx 'LIVE_PROFILE=c3_shadow' && echo "OK env_dang_chay LIVE_PROFILE=c3_shadow" || echo "FAIL env_dang_chay khong phai c3_shadow"
echo "$E" | grep -qx 'LIVE_KILLSW_MODE=log' && echo "OK env_dang_chay LIVE_KILLSW_MODE=log" || echo "FAIL env_dang_chay LIVE_KILLSW_MODE khac log"
echo "$E" | grep -qx 'SHADOW_NO_PUSH=true' && echo "OK env_dang_chay SHADOW_NO_PUSH=true" || echo "FAIL SHADOW_NO_PUSH khac true"
C=$(grep -c '^export LIVE_ADAPTER\|^export LIVE_C3_' conf/env.sh)
[ "$C" = 0 ] && echo "OK env.sh_chua_co_key_c3live" || echo "FAIL env.sh_da_co_${C}_dong_LIVE_ADAPTER/LIVE_C3_ (da deploy?)"
grep -q '^export LIVE_ENTRY_ENABLED=true' conf/env.sh && echo "FAIL env.sh_co_LIVE_ENTRY_ENABLED=true" || echo "OK khong_LIVE_ENTRY_ENABLED"
L=$(grep -c '^export JAVA_TOOL_OPTIONS=.*ExitOnOutOfMemoryError.*gc_%p_%t' bin/start.sh)
[ "$L" = 1 ] && echo "OK start.sh_dung_mau" || echo "FAIL start.sh_khong_dung_mau($L)"
[ -d run ] && echo "OK co_run/" || echo "FAIL thieu_run/"
[ -f run/c3live_book.json ] && echo "FAIL da_co_run/c3live_book.json (so cu — MASTER xem)" || echo "OK chua_co_so_c3live"
command -v curl >/dev/null && echo "OK curl" || echo "FAIL thieu_curl"
FREE=$(df -Pk . | awk 'NR==2{print $4}')
[ "${FREE:-0}" -gt 1048576 ] && echo "OK dia_trong=${FREE}k" || echo "FAIL dia_trong=${FREE}k < 1G"
EOF
) || die "ssh toi 242 loi"
echo "$PRE"
echo "$PRE" | grep -q '^FAIL' && die "kiem 242 co muc FAIL (xem tren). KHONG doi gi."
ok "kiem 242 dat"

ENV_ADD=$(cat <<EOV
# [v1.2 c3_live DRY $TS] (deploy_v12_dry.sh) — KHONG lenh that: adapter dry, push tat (SHADOW_NO_PUSH=true giu nguyen)
export LIVE_PROFILE=c3_live
export LIVE_ADAPTER=dry
export LIVE_KILLSW_MODE=act
export LIVE_KILLSW_C2_SIGNED=1
export LIVE_C3_BOOK_FILE=run/c3live_book.json
export LIVE_C3_EXCHANGEINFO_FILE=run/c3live_exchangeInfo.json
export LIVE_C3_DRY_STATE_FILE=run/c3live_dry_state.json
export LIVE_C3_EXCLUDE_TRADFI_FEATURES=1
EOV
)
NADD=$(echo "$ENV_ADD" | wc -l)
say "--- se THEM vao conf/env.sh ($NADD dong, export sau ghi de gia tri cu):"
echo "$ENV_ADD" | sed 's/^/   + /'

if [ "$DRY" = 1 ]; then say "DRY=1: dung o day, khong doi gi. (DRY PASS)"; exit 0; fi

# ---------------------------------------------------------------- 3. chep jar + backup + env + exchangeInfo
say "--- chep jar + killsw_reset.sh sang 242 (canh jar cu, chua ghi de)"
$SCP_242 "$NJ" "${RHOST}$A/target/binance-java-sdk-1.2.4.jar.v12dry" || die "scp jar loi"
$SSH_242 "mkdir -p $A/ops" || die "mkdir ops loi"
$SCP_242 "$KILLSW_SH" "${RHOST}$A/ops/killsw_reset.sh" || die "scp killsw_reset.sh loi"

say "--- backup + exchangeInfo + sua env.sh"
ENV_B64=$(echo "$ENV_ADD" | base64 -w0)
PREP=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $TS $NJ_MD5 $ENV_B64 $NADD" <<EOF
A=\$1; TS=\$2; NJM=\$3; EB=\$4; NADD=\$5; cd "\$A" || { echo "FAIL cd"; exit 0; }
[ "\$(md5sum < target/binance-java-sdk-1.2.4.jar.v12dry | cut -c1-32)" = "\$NJM" ] || { echo "FAIL md5_jar_tren_242"; exit 0; }
echo "OK md5_jar_tren_242"
\cp -fp target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_v12pre_\$TS || { echo "FAIL backup_jar"; exit 0; }
\cp -fp conf/env.sh conf/env.sh.bak_v12pre_\$TS || { echo "FAIL backup_env"; exit 0; }
\cp -fp bin/start.sh bin/start.sh.bak_v12pre_\$TS || { echo "FAIL backup_start"; exit 0; }
echo "OK backup TS=\$TS"
restore() { \cp -f conf/env.sh.bak_v12pre_\$TS conf/env.sh; echo "DA_KHOI_PHUC env.sh"; }
$EXINFO_CMD > run/c3live_exchangeInfo.json.tmp 2>/dev/null
N=\$(grep -o '"symbol":"' run/c3live_exchangeInfo.json.tmp | wc -l)
if [ "\$N" -gt 100 ]; then mv -f run/c3live_exchangeInfo.json.tmp run/c3live_exchangeInfo.json; echo "OK exchangeInfo so_symbol=\$N"; \
else rm -f run/c3live_exchangeInfo.json.tmp; echo "FAIL exchangeInfo so_symbol=\$N"; exit 0; fi
echo "\$EB" | base64 -d >> conf/env.sh
D=\$(diff conf/env.sh.bak_v12pre_\$TS conf/env.sh | grep -c '^>')
[ "\$D" = "\$NADD" ] && echo "OK env_them_\${D}_dong" || { echo "FAIL env_diff=\$D"; restore; exit 0; }
DS=\$(diff bin/start.sh.bak_v12pre_\$TS bin/start.sh | grep -c '^[<>]')
[ "\$DS" = 0 ] && echo "OK start.sh_khong_doi" || { echo "FAIL start.sh_doi=\$DS"; restore; exit 0; }
EOF
) || die "ssh buoc chuan bi loi"
echo "$PREP"
echo "$PREP" | grep -q '^FAIL' && die "buoc chuan bi co FAIL (env.sh da khoi phuc neu can). Jar cu van chay, khong co gi bi doi."
ok "chuan bi xong (jar cu van dang chay)"

# ---------------------------------------------------------------- 4. xac nhan + restart
echo
say ">>> Sap RESTART v_t_m tren 242 sang jar v1.2 (c3_live DRY). Go YES (in hoa) de tiep tuc, phim khac de huy:"
read -r ANS
if [ "$ANS" != "YES" ]; then
  say "Huy. Khoi phuc env.sh (jar cu van chay)."
  $SSH_242 "cd $A && \cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh && echo restored"
  exit 0
fi
time_ok || [ "$FORCE_TIME" = 1 ] || die "het khung gio hop le trong luc cho. Khoi phuc bang: bash $LOGDIR/rollback_v12.sh $TS"

say "--- restart (PAUSE watchdog truoc, xoa sau)"
RS=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $NJ_MD5 $WD_PAUSE" <<'EOF'
A=$1; NJM=$2; PAUSE=$3; cd "$A" || { echo "FAIL cd"; exit 0; }
touch "$PAUSE" 2>/dev/null && echo "OK watchdog_PAUSE" || echo "WARN khong_tao_duoc_PAUSE"
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
if pgrep -f "$PP" >/dev/null; then echo "FAIL van_con_process_sau_stop"; exit 0; fi
echo "OK da_stop"
\cp -f target/binance-java-sdk-1.2.4.jar.v12dry target/binance-java-sdk-1.2.4.jar
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] && echo "OK jar_da_thay" || echo "FAIL jar_thay_sai"
bin/daemon.sh start
sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process_sau_start"
EOF
) || die "ssh buoc restart loi — KIEM NGAY: bash $LOGDIR/rollback_v12.sh $TS"
echo "$RS"
if echo "$RS" | grep -q '^FAIL'; then
  say "Restart co FAIL. Chay rollback: bash $LOGDIR/rollback_v12.sh $TS"
  exit 1
fi
START_LINE=$(echo "$RS" | grep '^OK started')
ok "$START_LINE"

# ---------------------------------------------------------------- 5. kiem sau start (toi da ~10')
CHK() { $SSH_242 "PP='$PROC_PAT' bash -s -- $A $NJ_MD5" <<'EOF'
A=$1; NJM=$2; cd "$A"
L=logs/full.log
N=$(grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' $L | tail -1 | cut -d: -f1)
N=${N:-1}
P=$(pgrep -f "$PP" | head -1)
T() { tail -n +$N $L | grep -a -c "$1"; }
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] && echo "OK jar" || echo "FAIL jar"
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK 1_process" || echo "FAIL so_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in 'LIVE_PROFILE=c3_live' 'LIVE_ADAPTER=dry' 'LIVE_KILLSW_MODE=act' 'SHADOW_NO_PUSH=true' 'LIVE_TS_MKT_EXT=1' 'LIVE_HEARTBEAT=1'; do
  echo "$E" | grep -qx "$k" && echo "OK env $k" || echo "FAIL env $k"
done
echo "$E" | grep -q '^LIVE_ENTRY_ENABLED=true' && echo "FAIL env LIVE_ENTRY_ENABLED=true" || echo "OK env khong_LIVE_ENTRY_ENABLED"
[ "$(T 'LIVE_PROFILE=c3_live\] BAT')" -ge 1 ]          && echo "OK c3_live_BAT"        || echo "WAIT c3_live_BAT"
[ "$(T 'PUSH=OFF')" -ge 1 ]                             && echo "OK push_OFF"           || echo "WAIT push_OFF"
[ "$(T '\[KILLSW\] BAT mode=act')" -ge 1 ]              && echo "OK killsw_act_armed"   || echo "WAIT killsw_act_armed"
[ "$(T '\[C3-LIVE\] khoi dong adapter=DRY')" -ge 1 ]   && echo "OK c3live_DRY"         || echo "WAIT c3live_DRY"
[ "$(T 'killSwitchArmed=true')" -ge 1 ]                 && echo "OK killSwitchArmed"    || echo "WAIT killSwitchArmed"
[ "$(T '\[C5\] GLOBAL OK\|\[C5\] global OK\|\[C5\] .* OK')" -ge 1 ] && echo "OK AccountModeGuard" || echo "WAIT AccountModeGuard"
U=$(tail -n +$N $L | grep -a -o '\[UNIVERSE\] listed=[0-9]* alive=[0-9]* tradable=[0-9]*' | tail -1)
UT=$(echo "$U" | grep -o 'tradable=[0-9]*' | cut -d= -f2)
[ "${UT:-0}" -gt 100 ] && echo "OK universe $U" || echo "WAIT universe ${U:-chua_co}"
[ "$(T '\[C3-LIVE-RECON\] khoi dong')" -ge 1 ]         && echo "OK reconcile_khoi_dong" || echo "WAIT reconcile_khoi_dong"
[ "$(T 'reconcile khoi dong LOI')" = 0 ]                && echo "OK reconcile_khong_loi" || echo "FAIL reconcile_LOI"
[ "$(T '\[TS-EXT\] BAT')" -ge 1 ]                       && echo "OK TS_EXT(X14)"        || echo "WAIT TS_EXT"
[ "$(T '\[C3-LIVE-ORDER\]')" = 0 ]                      && echo "OK 0_lenh_that"        || echo "FAIL co_dong_C3-LIVE-ORDER(lenh_that?)"
[ "$(T 'TU CHOI')" = 0 ]                                && echo "OK khong_TU_CHOI"      || echo "FAIL co_TU_CHOI"
echo "INFO so_dong_LIVE-DRY=$(T '\[LIVE-DRY\]') (co the 0 neu chua co leg)"
if [ -f run/heartbeat ]; then AGE=$(( $(date +%s) - $(stat -c %Y run/heartbeat) )); [ $AGE -lt 180 ] && echo "OK heartbeat_tuoi=${AGE}s" || echo "WAIT heartbeat_tuoi=${AGE}s"; else echo "WAIT heartbeat_chua_co"; fi
X=$(tail -n +$N $L | grep -a -v 'Picked up' | grep -a -c 'Exception\|\[OPS\] loi hook\|\[C3-LIVE\] loi vong')
[ "$X" = 0 ] && echo "OK 0_exception" || echo "FAIL exception=$X"
EOF
}
RESULT=""
for i in $(seq 1 "$POST_ROUNDS"); do
  say "--- kiem sau start lan $i/$POST_ROUNDS (cho ${POST_WAIT_S}s)"; sleep "$POST_WAIT_S"
  RESULT=$(CHK) || true
  echo "$RESULT"
  echo "$RESULT" | grep -q '^FAIL' && break
  echo "$RESULT" | grep -q '^WAIT' || break
done
$SSH_242 "rm -f $WD_PAUSE" && say "xoa watchdog PAUSE"
if echo "$RESULT" | grep -q '^FAIL\|^WAIT'; then
  say "KIEM SAU START KHONG DAT. Muc FAIL/WAIT nghiem trong (jar/env/exception/lenh that) => chay: bash $LOGDIR/rollback_v12.sh $TS"
  say "Gui log nay cho MASTER: $LOG"
  exit 1
fi
ok "kiem sau start DAT"
say "=== XONG. $START_LINE"
say "Theo doi: bash $LOGDIR/c3live_status.sh   |   Rollback: bash $LOGDIR/rollback_v12.sh $TS"
say "Gui cho MASTER dong tren + file log: $LOG"
