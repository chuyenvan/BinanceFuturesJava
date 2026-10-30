#!/usr/bin/env bash
# =============================================================================
# deploy_v12_dry_r4.sh — [V12 R4b] DRY-RUN 11-18 c3_live tren TAI KHOAN CHINH (jar R4b, LIVE_ADAPTER=dry, KHONG lenh that)
# OWNER chay 1 LENH tren ORACLE (go YES 1 lan; script tu cho khung gio hop le roi moi doi gi tren 242):
#     bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
# Chay thu (chi doc, khong doi gi):   DRY=1 bash .../deploy_v12_dry_r4.sh
# TU CHOI truoc 2026-11-18 07:54 +07 tru khi FORCE=1 (chi khi MASTER bao). Bo cho khung gio: FORCE_TIME=1 (chi khi MASTER bao).
# Tu dung o moi buoc sai. Sau start: kiem LATCH + kiem R4 (LEGACY tren tai khoan chinh, exchangeInfo hop le, khong STALE);
# FAIL / WAIT qua han => ROLLBACK TU DONG (rollback_v12.sh). Rollback tay: bash .../rollback_v12.sh <TS>
# Script MOI (giu nguyen deploy_v12_dry.sh + pin cu cua no). Bien cho test (242 GIA): SSH_242, SCP_242, RHOST, APP_DIR,
#   LOGDIR, WD_PAUSE, NJ, NJ_MD5, OLD_MD5, KILLSW_SH, KILLSW_MD5, RB_SH, LATCH_WAIT_S, EXINFO_CMD, POST_WAIT_S, POST_ROUNDS,
#   PROC_PAT, WINDOW_WAIT_MAX_S, MIN_TRADFI.
# =============================================================================
set -uo pipefail

SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
NJ=${NJ:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4b}
NJ_MD5=${NJ_MD5:-7457200a70e55b202062492f07f0ae57}   # [V12 R4b] jar R4b (docs/c3live/ROUND4B.md)
# jar v_t_m dang chay (shadow v1.1 dcae2e2b): deploy_v12_dry.sh / rollback_v12.sh / fix_featdump_242 10-27 ("OK jar_dcae2e2b").
# Kiem lai tren 242 o buoc 2 — khac => TU CHOI.
OLD_MD5=${OLD_MD5:-dcae2e2bbb1a357bc15703b416d4dccb}
KILLSW_SH=${KILLSW_SH:-/home/ubuntu/claude_master/v12/c3live/ops/killsw_reset.sh}
KILLSW_MD5=${KILLSW_MD5:-6f8d83481904f91b3f92601b31720ace}
RB_SH=${RB_SH:-$(cd "$(dirname "$0")" && pwd)/rollback_v12.sh}
LATCH_WAIT_S=${LATCH_WAIT_S:-120}
WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}
EXINFO_CMD=${EXINFO_CMD:-"curl -s --max-time 30 https://fapi.binance.com/fapi/v1/exchangeInfo"}
MIN_TRADFI=${MIN_TRADFI:-50}   # = SymbolUniverseLive.MIN_TRADFI_IN_SOURCE
POST_WAIT_S=${POST_WAIT_S:-120}
POST_ROUNDS=${POST_ROUNDS:-5}
WINDOW_WAIT_MAX_S=${WINDOW_WAIT_MAX_S:-5400}
DRY=${DRY:-0}
FORCE=${FORCE:-0}
FORCE_TIME=${FORCE_TIME:-0}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M)
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
LOG=$LOGDIR/deploy_v12dry_r4_${TS}.log
exec > >(tee -a "$LOG") 2>&1

say()  { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die()  { say "DUNG: $*"; say "Log: $LOG"; exit 1; }
ok()   { say "OK: $*"; }

say "=== deploy v1.2 R4b c3_live DRY (tai khoan chinh)  TS=$TS  DRY=$DRY ==="

# ---------------------------------------------------------------- 0. chot ngay
NOT_BEFORE=$(date -d '2026-11-18 07:54 +07' +%s)
if [ "$(date +%s)" -lt "$NOT_BEFORE" ] && [ "$FORCE" != 1 ]; then
  [ "$DRY" = 1 ] && say "CANH BAO: truoc 2026-11-18 07:54 +07 — ban that se TU CHOI (DRY van chay kiem tra)." \
                 || die "truoc 2026-11-18 07:54 +07: TU CHOI (thay jar shadow dang danh gia). Chi chay sau moc do (hoac FORCE=1 khi MASTER bao)."
fi
time_ok() {
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1          # chi phut :10-:44
  case "$H" in 7|19) return 1;; esac                       # 07:xx/19:xx
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi
  return 0
}

# ---------------------------------------------------------------- 1. kiem cuc bo
[[ "$NJ_MD5" =~ ^[0-9a-f]{32}$ ]] || die "NJ_MD5 chua pin"
[ -f "$NJ" ] || die "khong thay jar $NJ"
[ "$(md5sum < "$NJ" | cut -c1-32)" = "$NJ_MD5" ] || die "md5 jar moi sai (mong $NJ_MD5)"
ok "jar R4b md5 $NJ_MD5"
[[ "$OLD_MD5" =~ ^[0-9a-f]{32}$ ]] || die "OLD_MD5 (jar dang chay) khong xac dinh => TU CHOI"
[ -f "$KILLSW_SH" ] || die "khong thay $KILLSW_SH"
bash -n "$KILLSW_SH" || die "cu phap killsw_reset.sh loi"
[ "$(md5sum < "$KILLSW_SH" | cut -c1-32)" = "$KILLSW_MD5" ] || die "md5 killsw_reset.sh sai (mong $KILLSW_MD5)"
[ -f "$RB_SH" ] && bash -n "$RB_SH" || die "khong thay/cu phap loi rollback $RB_SH (can cho rollback tu dong)"
ok "killsw_reset.sh + rollback san sang"

# ---------------------------------------------------------------- 2. kiem 242 (chi doc)
say "--- kiem 242 (chi doc)"
PRE=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $OLD_MD5" <<'EOF'
A=$1; OLD=$2; cd "$A" || { echo "FAIL cd"; exit 0; }
J=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)
[ "$J" = "$OLD" ] && echo "OK jar_dang_chay=$J" || echo "FAIL jar_dang_chay=$J (mong doi $OLD) — khong xac dinh duoc ban dang chay => TU CHOI"
NP=$(pgrep -fc "$PP")
[ "$NP" = 1 ] && echo "OK so_process=1" || echo "FAIL so_process=$NP"
P=$(pgrep -f "$PP" | head -1)
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "$E" | grep -qx 'LIVE_PROFILE=c3_shadow' && echo "OK env_dang_chay LIVE_PROFILE=c3_shadow" || echo "FAIL env_dang_chay khong phai c3_shadow"
echo "$E" | grep -qx 'SHADOW_NO_PUSH=true' && echo "OK env_dang_chay SHADOW_NO_PUSH=true" || echo "FAIL SHADOW_NO_PUSH khac true"
C=$(grep -c '^export LIVE_ADAPTER\|^export LIVE_C3_\|^export C3_CAPITAL' conf/env.sh)
[ "$C" = 0 ] && echo "OK env.sh_chua_co_key_c3live" || echo "FAIL env.sh_da_co_${C}_dong_LIVE_ADAPTER/LIVE_C3_/C3_CAPITAL (da deploy?)"
grep -q '^export LIVE_ENTRY_ENABLED=true' conf/env.sh && echo "FAIL env.sh_co_LIVE_ENTRY_ENABLED=true" || echo "OK khong_LIVE_ENTRY_ENABLED"
grep -q '^export SHADOW_NO_PUSH=true' conf/env.sh && echo "OK env.sh_SHADOW_NO_PUSH=true" || echo "FAIL env.sh_thieu_SHADOW_NO_PUSH=true"
L=$(grep -c '^export JAVA_TOOL_OPTIONS=.*ExitOnOutOfMemoryError.*gc_%p_%t' bin/start.sh)
[ "$L" = 1 ] && echo "OK start.sh_dung_mau" || echo "FAIL start.sh_khong_dung_mau($L)"
[ -d run ] && echo "OK co_run/" || echo "FAIL thieu_run/"
# [R4b] trang thai cu cua c3_live => MASTER xem truoc (khong de dry moi ke thua so / MERGED / equity / latch / dinh cu)
for f in run/c3live_book.json run/c3live_merged.txt run/c3live_equity_c3.json run/killsw_latch.json run/c3live_killsw_peak; do
  [ -e "$f" ] && echo "FAIL da_co_$f (trang thai cu — MASTER xem; rollback_v12.sh doi ten .rb_TS)" || echo "OK chua_co_$f"
done
command -v curl >/dev/null && echo "OK curl" || echo "FAIL thieu_curl"
FREE=$(df -Pk . | awk 'NR==2{print $4}')
[ "${FREE:-0}" -gt 1048576 ] && echo "OK dia_trong=${FREE}k" || echo "FAIL dia_trong=${FREE}k < 1G"
EOF
) || die "ssh toi 242 loi"
echo "$PRE"
echo "$PRE" | grep -q '^FAIL' && die "kiem 242 co muc FAIL (xem tren). KHONG doi gi."
ok "kiem 242 dat"

ENV_ADD=$(cat <<EOV
# [v1.2 R4b c3_live DRY $TS] (deploy_v12_dry_r4.sh) — tai khoan chinh, KHONG lenh that: adapter dry, push tat (SHADOW_NO_PUSH=true giu nguyen)
export LIVE_PROFILE=c3_live
export LIVE_ADAPTER=dry
export LIVE_KILLSW_MODE=act
export LIVE_KILLSW_C2_SIGNED=1
export C3_CAPITAL=10000
export LIVE_C3_BOOK_FILE=run/c3live_book.json
export LIVE_C3_EXCHANGEINFO_FILE=run/c3live_exchangeInfo.json
export LIVE_C3_DRY_STATE_FILE=run/c3live_dry_state.json
export LIVE_C3_MERGED_FILE=run/c3live_merged.txt
export LIVE_C3_EQUITY_FILE=run/c3live_equity_c3.json
export LIVE_C3_EXCLUDE_TRADFI_FEATURES=1
EOV
)
NADD=$(echo "$ENV_ADD" | wc -l)
say "--- se THEM vao conf/env.sh ($NADD dong, export sau ghi de gia tri cu):"
echo "$ENV_ADD" | sed 's/^/   + /'

if [ "$DRY" = 1 ]; then say "DRY=1: dung o day, khong doi gi. (DRY PASS)"; exit 0; fi

# ---------------------------------------------------------------- 3. YES 1 lan, roi cho khung gio (CHUA doi gi tren 242)
echo
say ">>> Se deploy jar R4b (c3_live DRY tai khoan chinh) len 242 trong khung gio hop le ke tiep. Go YES (in hoa) de tiep tuc:"
read -r ANS
[ "$ANS" = "YES" ] || { say "Huy. Khong doi gi."; exit 0; }
if [ "$FORCE_TIME" != 1 ]; then
  W=0
  until time_ok; do
    [ "$W" -ge "$WINDOW_WAIT_MAX_S" ] && die "cho khung gio qua ${WINDOW_WAIT_MAX_S}s. Khong doi gi. Chay lai sau."
    [ $((W % 300)) = 0 ] && say "cho khung gio hop le (phut :10-:44, tranh 07:xx/19:xx, 00:50-01:20, 12:50-13:20) — da cho ${W}s"
    sleep 30; W=$((W + 30))
  done
  ok "khung gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) hop le"
fi

# ---------------------------------------------------------------- 4. chep jar + backup + exchangeInfo (kiem truong) + env
say "--- chep jar + killsw_reset.sh sang 242 (canh jar cu, chua ghi de)"
$SCP_242 "$NJ" "${RHOST}$A/target/binance-java-sdk-1.2.4.jar.v12dry" || die "scp jar loi"
$SSH_242 "mkdir -p $A/ops" || die "mkdir ops loi"
$SCP_242 "$KILLSW_SH" "${RHOST}$A/ops/killsw_reset.sh" || die "scp killsw_reset.sh loi"
say "--- backup + exchangeInfo + sua env.sh"
ENV_B64=$(echo "$ENV_ADD" | base64 -w0)
PREP=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $TS $NJ_MD5 $ENV_B64 $NADD $MIN_TRADFI" <<EOF
A=\$1; TS=\$2; NJM=\$3; EB=\$4; NADD=\$5; MINTF=\$6; cd "\$A" || { echo "FAIL cd"; exit 0; }
[ "\$(md5sum < target/binance-java-sdk-1.2.4.jar.v12dry | cut -c1-32)" = "\$NJM" ] || { echo "FAIL md5_jar_tren_242"; exit 0; }
echo "OK md5_jar_tren_242"
\cp -fp target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_v12pre_\$TS || { echo "FAIL backup_jar"; exit 0; }
\cp -fp conf/env.sh conf/env.sh.bak_v12pre_\$TS || { echo "FAIL backup_env"; exit 0; }
\cp -fp bin/start.sh bin/start.sh.bak_v12pre_\$TS || { echo "FAIL backup_start"; exit 0; }
echo "OK backup TS=\$TS"
restore() { \cp -f conf/env.sh.bak_v12pre_\$TS conf/env.sh; echo "DA_KHOI_PHUC env.sh"; }
$EXINFO_CMD > run/c3live_exchangeInfo.json.tmp 2>/dev/null
X=run/c3live_exchangeInfo.json.tmp
N=\$(grep -o '"symbol":"' \$X | wc -l)
NC=\$(grep -o '"contractType":"' \$X | wc -l)
NU=\$(grep -o '"underlyingType":"' \$X | wc -l)
NT=\$(grep -o '"contractType":"[A-Z_]*TRADI\{0,1\}FI[A-Z_]*"' \$X | wc -l)
if [ "\$N" -gt 100 ] && [ "\$NC" -gt 0 ] && [ "\$NU" -gt 0 ] && [ "\$NT" -ge "\$MINTF" ]; then
  mv -f \$X run/c3live_exchangeInfo.json; echo "OK exchangeInfo so_symbol=\$N contractType=\$NC underlyingType=\$NU TradFi=\$NT"
else
  rm -f \$X; echo "FAIL exchangeInfo so_symbol=\$N contractType=\$NC underlyingType=\$NU TradFi=\$NT (can >100 symbol, du truong, TradFi >= \$MINTF)"; exit 0
fi
echo "\$EB" | base64 -d >> conf/env.sh
D=\$(diff conf/env.sh.bak_v12pre_\$TS conf/env.sh | grep -c '^>')
[ "\$D" = "\$NADD" ] && echo "OK env_them_\${D}_dong" || { echo "FAIL env_diff=\$D"; restore; exit 0; }
grep -q '^export SHADOW_NO_PUSH=true' conf/env.sh && echo "OK SHADOW_NO_PUSH=true giu nguyen" || { echo "FAIL SHADOW_NO_PUSH"; restore; exit 0; }
DS=\$(diff bin/start.sh.bak_v12pre_\$TS bin/start.sh | grep -c '^[<>]')
[ "\$DS" = 0 ] && echo "OK start.sh_khong_doi" || { echo "FAIL start.sh_doi=\$DS"; restore; exit 0; }
EOF
) || die "ssh buoc chuan bi loi"
echo "$PREP"
if echo "$PREP" | grep -q '^FAIL'; then
  $SSH_242 "cd $A && [ -f conf/env.sh.bak_v12pre_$TS ] && \cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh && echo env_da_khoi_phuc" || true
  die "buoc chuan bi co FAIL (env.sh da khoi phuc). Jar cu van chay, khong co gi bi doi."
fi
ok "chuan bi xong (jar cu van dang chay)"
time_ok || [ "$FORCE_TIME" = 1 ] || { $SSH_242 "cd $A && \cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh"; die "het khung gio trong luc chuan bi (env da khoi phuc). Chay lai."; }

# ---------------------------------------------------------------- 5. restart (watchdog PAUSE)
say "--- restart (PAUSE watchdog truoc, xoa sau kiem)"
RS=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $NJ_MD5 $WD_PAUSE" <<'EOF'
A=$1; NJM=$2; PAUSE=$3; cd "$A" || { echo "FAIL cd"; exit 0; }
mkdir -p "$(dirname "$PAUSE")" 2>/dev/null; touch "$PAUSE" 2>/dev/null && echo "OK watchdog_PAUSE" || echo "WARN khong_tao_duoc_PAUSE"
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
if pgrep -f "$PP" >/dev/null; then echo "FAIL van_con_process_sau_stop"; exit 0; fi
echo "OK da_stop"
\cp -f target/binance-java-sdk-1.2.4.jar.v12dry target/binance-java-sdk-1.2.4.jar
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] && echo "OK jar_da_thay" || echo "FAIL jar_thay_sai"
date +%s > run/.v12_start_epoch
echo "INFO tz_shell=$(date +%z) moc_start_+07=$(TZ=Asia/Ho_Chi_Minh date -d @$(cat run/.v12_start_epoch) '+%F %T')"
bin/daemon.sh start
sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process_sau_start"
EOF
) || RS="FAIL ssh_restart_loi"
echo "$RS"
autorb() {
  say "$1 => ROLLBACK TU DONG"
  YES_AUTO=1 FORCE_TIME=1 bash "$RB_SH" "$TS"
  $SSH_242 "rm -f $WD_PAUSE" || true
  say "DEPLOY FAIL ($1). Da chay rollback. Gui log cho MASTER: $LOG"
  exit 1
}
echo "$RS" | grep -q '^FAIL' && autorb "restart co FAIL"
START_LINE=$(echo "$RS" | grep '^OK started')
ok "$START_LINE"

# ---------------------------------------------------------------- 6. 0 dong [KILLSW] LATCH trong LATCH_WAIT_S dau
say "--- cho ${LATCH_WAIT_S}s roi kiem 0 dong '[KILLSW] LATCH' ke tu start"
sleep "$LATCH_WAIT_S"
LT=$($SSH_242 "bash -s -- $A" <<'EOF'
A=$1; cd "$A" || { echo "LATCH_COUNT=no_cd"; exit 0; }
ST=$(cat run/.v12_start_epoch 2>/dev/null)
case "$ST" in ''|*[!0-9]*) echo "LATCH_COUNT=no_start_mark"; exit 0;; esac
[ -r logs/full.log ] || { echo "LATCH_COUNT=no_log"; exit 0; }
K=$(TZ=Asia/Ho_Chi_Minh date -d "@$ST" +%Y%m%d%H%M%S)
FILES=$(find logs -maxdepth 1 -type f \( -name full.log -o -name 'full.log.*' -o -name 'full*.gz' \) -newermt "@$ST" 2>/dev/null)
[ -n "$FILES" ] || { echo "LATCH_COUNT=no_log_after_start"; exit 0; }
since() {
  for f in $FILES; do case "$f" in *.gz) zcat -f "$f" 2>/dev/null;; *) cat "$f" 2>/dev/null;; esac; done | awk -v K="$K" '
    { k = ""
      if ($0 ~ /^[0-9][0-9]\/[0-9][0-9]\/[0-9][0-9][0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]/) {
        k = substr($0,7,4) substr($0,4,2) substr($0,1,2) substr($0,12,2) substr($0,15,2) substr($0,18,2) }
      else if ($0 ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]/) {
        k = substr($0,1,4) substr($0,6,2) substr($0,9,2) substr($0,12,2) substr($0,15,2) substr($0,18,2) }
      if (k != "") cur = k
      if (cur != "" && cur >= K) print }'
}
SEEN=$(since | grep -a -c 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager')
[ "${SEEN:-0}" -ge 1 ] || { echo "LATCH_COUNT=no_start_line"; exit 0; }
C=$(since | grep -a -c '\[KILLSW\] LATCH\|\[KILLSW\] NAP LATCH\|\[KILLSW\] FAIL-CLOSED')
echo "LATCH_COUNT=$C files=$(echo $FILES | wc -w)"
EOF
) || LT="LATCH_COUNT=ssh_loi"
echo "$LT"
LC=$(echo "$LT" | grep -o 'LATCH_COUNT=[0-9a-z_]*' | cut -d= -f2)
[ "$LC" = 0 ] || autorb "hau kiem LATCH = '${LC}'"
ok "0 dong [KILLSW] LATCH trong ${LATCH_WAIT_S}s dau"

# ---------------------------------------------------------------- 7. kiem sau start (toi da POST_ROUNDS x POST_WAIT_S)
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
for k in 'LIVE_PROFILE=c3_live' 'LIVE_ADAPTER=dry' 'LIVE_KILLSW_MODE=act' 'SHADOW_NO_PUSH=true' 'C3_CAPITAL=10000' 'LIVE_TS_MKT_EXT=1' 'LIVE_HEARTBEAT=1'; do
  echo "$E" | grep -qx "$k" && echo "OK env $k" || echo "FAIL env $k"
done
echo "$E" | grep -q '^LIVE_ENTRY_ENABLED=true' && echo "FAIL env LIVE_ENTRY_ENABLED=true" || echo "OK env khong_LIVE_ENTRY_ENABLED"
[ "$(T 'PUSH=OFF')" -ge 1 ]                             && echo "OK push_OFF"           || echo "WAIT push_OFF"
[ "$(T '\[KILLSW\] BAT mode=act')" -ge 1 ]              && echo "OK killsw_act_armed"   || echo "WAIT killsw_act_armed"
[ "$(T '\[C3-LIVE\] khoi dong adapter=DRY')" -ge 1 ]   && echo "OK c3live_DRY"         || echo "WAIT c3live_DRY"
[ "$(T 'killSwitchArmed=true')" -ge 1 ]                 && echo "OK killSwitchArmed"    || echo "WAIT killSwitchArmed"
[ "$(T 'LEGACY tren tai khoan chinh')" -ge 1 ]          && echo "OK R4_LEGACY_scope"    || echo "WAIT R4_LEGACY_scope"
[ "$(T 'exchangeInfo KHONG hop le')" = 0 ]              && echo "OK exchangeInfo_hop_le" || echo "FAIL exchangeInfo_KHONG_hop_le"
[ "$(T 'STALE')" = 0 ]                                  && echo "OK khong_STALE"        || echo "FAIL STALE=$(T 'STALE')"
U=$(tail -n +$N $L | grep -a -o '\[UNIVERSE\] listed=[0-9]* alive=[0-9]* tradable=[0-9]*' | tail -1)
UT=$(echo "$U" | grep -o 'tradable=[0-9]*' | cut -d= -f2)
[ "${UT:-0}" -gt 100 ] && echo "OK universe $U" || echo "WAIT universe ${U:-chua_co}"
[ "$(T '\[C3-LIVE-RECON\] khoi dong')" -ge 1 ]         && echo "OK reconcile_khoi_dong" || echo "WAIT reconcile_khoi_dong"
[ "$(T 'reconcile khoi dong LOI')" = 0 ]                && echo "OK reconcile_khong_loi" || echo "FAIL reconcile_LOI"
[ "$(T '\[C3-LIVE-ORDER\]')" = 0 ]                      && echo "OK 0_lenh_that"        || echo "FAIL co_dong_C3-LIVE-ORDER(lenh_that?)"
[ "$(T 'TU CHOI')" = 0 ]                                && echo "OK khong_TU_CHOI"      || echo "FAIL co_TU_CHOI"
[ "$(T '\[KILLSW\] LATCH')" = 0 ] && echo "OK 0_KILLSW_LATCH" || echo "FAIL KILLSW_LATCH"
if [ -f run/heartbeat ]; then AGE=$(( $(date +%s) - $(stat -c %Y run/heartbeat) )); [ $AGE -lt 180 ] && echo "OK heartbeat_tuoi=${AGE}s" || echo "WAIT heartbeat_tuoi=${AGE}s"; else echo "WAIT heartbeat_chua_co"; fi
X=$(tail -n +$N $L | grep -a -v 'Picked up' | grep -a -c 'Exception\|\[OPS\] loi hook\|\[C3-LIVE\] loi vong')
[ "$X" = 0 ] && echo "OK 0_exception" || echo "FAIL exception=$X"
echo "INFO so_dong_LIVE-DRY=$(T '\[LIVE-DRY\]')"
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
if echo "$RESULT" | grep -q '^FAIL\|^WAIT'; then
  autorb "kiem sau start KHONG DAT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200))"
fi
$SSH_242 "rm -f $WD_PAUSE" && say "xoa watchdog PAUSE"
ok "kiem sau start DAT"
say "=== XONG. $START_LINE"
say "Theo doi: bash $(cd "$(dirname "$0")" && pwd)/c3live_status.sh   |   Rollback: bash $RB_SH $TS"
say "Gui cho MASTER dong tren + file log: $LOG"
