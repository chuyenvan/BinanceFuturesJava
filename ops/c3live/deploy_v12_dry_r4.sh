#!/usr/bin/env bash
# =============================================================================
# deploy_v12_dry_r4.sh — [V12 R4d] DRY-RUN 11-18 c3_live tren TAI KHOAN CHINH (jar R4d, LIVE_ADAPTER=dry, KHONG lenh that)
# [R4d] UNIVERSE_A1=1: phia tin hieu (S1/ung vien, breadth, ALT_EW, gate, funding/OI) loai TradFi + INDEX nhu backtest A1;
#   nguon = CUNG file raw exchangeInfo R7 (run/c3live_exchangeInfo.json, curl TREN 242 o buoc chuan bi; Oracle KHONG goi Binance).
# OWNER chay 1 LENH tren ORACLE (go YES 1 lan):
#     bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
# Chay thu (chi doc, khong doi gi):   DRY=1 bash .../deploy_v12_dry_r4.sh
# TU CHOI truoc 2026-11-18 07:54 +07 tru khi FORCE=1 (chi khi MASTER bao). Bo cho khung gio: FORCE_TIME=1 (chi khi MASTER bao).
# [R4c C] Foreground CHI: kiem (chi doc) + hoi YES + khoi dong JOB NEN (setsid nohup, log rieng) + tail log. Dong terminal /
#   mat ket noi toi Oracle KHONG dung job. Job: cho khung gio -> KIEM 242 LAI (R4c D1) -> chep/backup/env -> restart (PAUSE
#   watchdog) -> LATCH -> kiem R4 -> Telegram ket qua. FAIL / WAIT qua han => ROLLBACK TU DONG (rollback_v12.sh, md5 pin RB_MD5).
#   Rollback LOI => in + Telegram "PAUSE còn — chạy rollback tay: <lenh>" (exit 2).
# Ma thoat: 0 XONG | 1 DUNG (chua doi gi / env khoi phuc / da rollback xong) | 2 ROLLBACK LOI | 3 XONG nhung PAUSE con.
# Rollback tay: FORCE_TIME=1 bash .../rollback_v12.sh <TS>
# Script MOI (giu nguyen deploy_v12_dry.sh + pin cu cua no). Bien cho test (242 GIA): SSH_242, SCP_242, RHOST, APP_DIR,
#   LOGDIR, WD_PAUSE, NJ, NJ_MD5, OLD_MD5, KILLSW_SH, KILLSW_MD5, RB_SH, RB_MD5, LATCH_WAIT_S, EXINFO_CMD, POST_WAIT_S,
#   POST_ROUNDS, PROC_PAT, WINDOW_WAIT_MAX_S, MIN_TRADFI, DEPLOY_TG_ENV, DEPLOY_TG_SINK (test: ghi Telegram ra file, KHONG gui).
# =============================================================================
set -uo pipefail

SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
NJ=${NJ:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4d}
NJ_MD5=${NJ_MD5:-48260625c1f96627922d89aff3b9ef58}   # [V12 R4d] jar R4d (docs/c3live/ROUND4D.md)
# jar v_t_m dang chay (shadow v1.1 dcae2e2b): deploy_v12_dry.sh / rollback_v12.sh / fix_featdump_242 10-27 ("OK jar_dcae2e2b").
# Kiem lai tren 242 o buoc 2 — khac => TU CHOI.
OLD_MD5=${OLD_MD5:-dcae2e2bbb1a357bc15703b416d4dccb}
KILLSW_SH=${KILLSW_SH:-/home/ubuntu/claude_master/v12/c3live/ops/killsw_reset.sh}
KILLSW_MD5=${KILLSW_MD5:-6f8d83481904f91b3f92601b31720ace}
RB_SH=${RB_SH:-$(cd "$(dirname "$0")" && pwd)/rollback_v12.sh}
RB_MD5=${RB_MD5:-ae7a5a5f3704688677d5c0d28a358b80}   # [R4c D2] md5 rollback_v12.sh (kiem truoc khi dung, ca trong autorb)
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
R4_JOB=${R4_JOB:-0}   # 1 = job nen (CHI foreground khoi dong, kem R4_YES_FILE)
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
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
TS=${R4_TS:-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M)}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
if [ "$R4_JOB" = 1 ]; then
  LOG=${R4_JOBLOG:?"job nen thieu R4_JOBLOG"}   # stdout/stderr cua job da vao file nay (nohup)
else
  LOG=$LOGDIR/deploy_v12dry_r4_${TS}.log
  exec > >(tee -a "$LOG") 2>&1
fi

say()  { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
# [R4c C] Telegram nhu canary cl_tg: token doc tu file, KHONG in, KHONG nam tren dong lenh (curl -K -); test: DEPLOY_TG_SINK
tg() {
  local msg code tok chat
  msg=$(printf '%s' "$1" | sed -E 's/signature=[^ "]*/[CHE]/g; s/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g' | head -c 3500)
  if [ -n "${DEPLOY_TG_SINK:-}" ]; then
    { printf '%s\n' "$msg"; echo "----"; } >> "$DEPLOY_TG_SINK"; say "Telegram (test sink): da ghi $DEPLOY_TG_SINK"; return 0
  fi
  [ -r "$DEPLOY_TG_ENV" ] || { say "!! khong doc duoc $DEPLOY_TG_ENV — KHONG gui duoc Telegram"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || { say "!! $DEPLOY_TG_ENV thieu TG_TOKEN/TG_CHAT — KHONG gui duoc Telegram"; return 1; }
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null)
  tok=""
  if [ "$code" = 200 ]; then say "Telegram: da gui (HTTP 200)"; return 0; fi
  say "!! Telegram KHONG gui duoc (HTTP ${code:-loi})"; return 1
}
die()  { say "DUNG: $*"; say "Log: $LOG"; [ "$R4_JOB" = 1 ] && tg "[deploy dry R4d] DUNG TS=$TS: $* | log $LOG"; exit 1; }
ok()   { say "OK: $*"; }
# [R4c] khoa 1 job: file PID (KHONG dung flock: fd khoa se bi process con song lau ke thua)
LOCKF=$LOGDIR/.deploy_v12dry_r4.pid
lock_busy() {
  local p; p=$(cat "$LOCKF" 2>/dev/null)
  [ -n "$p" ] && [ "$p" != "$$" ] && kill -0 "$p" 2>/dev/null && tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q deploy_v12_dry_r4
}

say "=== deploy v1.2 R4d c3_live DRY (tai khoan chinh)  TS=$TS  DRY=$DRY  $([ "$R4_JOB" = 1 ] && echo "JOB_NEN pid=$$" || echo foreground) ==="

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
ok "jar R4d md5 $NJ_MD5"
[[ "$OLD_MD5" =~ ^[0-9a-f]{32}$ ]] || die "OLD_MD5 (jar dang chay) khong xac dinh => TU CHOI"
[ -f "$KILLSW_SH" ] || die "khong thay $KILLSW_SH"
bash -n "$KILLSW_SH" || die "cu phap killsw_reset.sh loi"
[ "$(md5sum < "$KILLSW_SH" | cut -c1-32)" = "$KILLSW_MD5" ] || die "md5 killsw_reset.sh sai (mong $KILLSW_MD5)"
[ -f "$RB_SH" ] && bash -n "$RB_SH" || die "khong thay/cu phap loi rollback $RB_SH (can cho rollback tu dong)"
[[ "$RB_MD5" =~ ^[0-9a-f]{32}$ ]] || die "RB_MD5 chua pin"
[ "$(md5sum < "$RB_SH" | cut -c1-32)" = "$RB_MD5" ] || die "md5 rollback_v12.sh sai (mong $RB_MD5) — KHONG deploy khi khong chac rollback dung ban"
ok "killsw_reset.sh + rollback san sang"

# ---------------------------------------------------------------- 2. kiem 242 (chi doc)
pre242() {
$SSH_242 "PP='$PROC_PAT' EXC='$EXINFO_CMD' bash -s -- $A $OLD_MD5 $MIN_TRADFI" <<'EOF'
A=$1; OLD=$2; MINTF=$3; cd "$A" || { echo "FAIL cd"; exit 0; }
J=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)
[ "$J" = "$OLD" ] && echo "OK jar_dang_chay=$J" || echo "FAIL jar_dang_chay=$J (mong doi $OLD) — khong xac dinh duoc ban dang chay => TU CHOI"
NP=$(pgrep -fc "$PP")
[ "$NP" = 1 ] && echo "OK so_process=1" || echo "FAIL so_process=$NP"
P=$(pgrep -f "$PP" | head -1)
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "$E" | grep -qx 'LIVE_PROFILE=c3_shadow' && echo "OK env_dang_chay LIVE_PROFILE=c3_shadow" || echo "FAIL env_dang_chay khong phai c3_shadow"
echo "$E" | grep -qx 'SHADOW_NO_PUSH=true' && echo "OK env_dang_chay SHADOW_NO_PUSH=true" || echo "FAIL SHADOW_NO_PUSH khac true"
C=$(grep -c '^export LIVE_ADAPTER\|^export LIVE_C3_\|^export C3_CAPITAL\|^export UNIVERSE_A1' conf/env.sh)
[ "$C" = 0 ] && echo "OK env.sh_chua_co_key_c3live" || echo "FAIL env.sh_da_co_${C}_dong_LIVE_ADAPTER/LIVE_C3_/C3_CAPITAL (da deploy?)"
grep -q '^export LIVE_ENTRY_ENABLED=true' conf/env.sh && echo "FAIL env.sh_co_LIVE_ENTRY_ENABLED=true" || echo "OK khong_LIVE_ENTRY_ENABLED"
grep -q '^export SHADOW_NO_PUSH=true' conf/env.sh && echo "OK env.sh_SHADOW_NO_PUSH=true" || echo "FAIL env.sh_thieu_SHADOW_NO_PUSH=true"
L=$(grep -c '^export JAVA_TOOL_OPTIONS=.*ExitOnOutOfMemoryError.*gc_%p_%t' bin/start.sh)
[ "$L" = 1 ] && echo "OK start.sh_dung_mau" || echo "FAIL start.sh_khong_dung_mau($L)"
[ -d run ] && echo "OK co_run/" || echo "FAIL thieu_run/"
# [R4b] trang thai cu cua c3_live => MASTER xem truoc (khong de dry moi ke thua so / MERGED / equity / latch / dinh cu)
for f in run/c3live_book.json run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/ts_ext_daily.csv.a1 run/killsw_latch.json run/c3live_killsw_peak; do
  [ -e "$f" ] && echo "FAIL da_co_$f (trang thai cu — MASTER xem; rollback_v12.sh doi ten .rb_TS)" || echo "OK chua_co_$f"
done
command -v curl >/dev/null && echo "OK curl" || echo "FAIL thieu_curl"
# [R4d] nguon raw exchangeInfo (UNIVERSE_A1 + R7): doc thu ra stdout TREN 242 (khong ghi file) — du truong + serverTime + onboardDate
XS=$(eval "$EXC" 2>/dev/null)
XN=$(printf '%s' "$XS" | grep -o '"symbol":"' | wc -l)
XT=$(printf '%s' "$XS" | grep -o '"contractType":"[A-Z_]*TRADI\{0,1\}FI[A-Z_]*"' | wc -l)
XO=$(printf '%s' "$XS" | grep -o '"onboardDate":[0-9]' | wc -l)
XU=$(printf '%s' "$XS" | grep -o '"underlyingType":"' | wc -l)
XST=$(printf '%s' "$XS" | grep -o '"serverTime":[0-9]*' | head -1 | cut -d: -f2)
if [ "$XN" -gt 100 ] && [ "$XT" -ge "$MINTF" ] && [ "$XO" -ge "$XN" ] && [ "$XU" -gt 0 ] && [ "${XST:-0}" -gt 0 ]; then
  echo "OK exchangeInfo_nguon symbols=$XN TradFi=$XT onboardDate=$XO underlyingType=$XU serverTime=$XST"
else
  echo "FAIL exchangeInfo_nguon symbols=$XN TradFi=$XT onboardDate=$XO underlyingType=$XU serverTime=${XST:-0} (UNIVERSE_A1 can raw /fapi/v1/exchangeInfo day du)"
fi
FREE=$(df -Pk . | awk 'NR==2{print $4}')
[ "${FREE:-0}" -gt 1048576 ] && echo "OK dia_trong=${FREE}k" || echo "FAIL dia_trong=${FREE}k < 1G"
EOF
}
run_pre() {   # [R4c D1] goi o foreground VA lai trong job ngay truoc khi doi gi (trang thai co the doi trong luc cho khung gio)
  say "--- kiem 242 (chi doc)$1"
  PRE=$(pre242) || die "ssh toi 242 loi (kiem 242$1)"
  echo "$PRE"
  echo "$PRE" | grep -q '^FAIL' && die "kiem 242 co muc FAIL (xem tren)$1. KHONG doi gi."
  echo "$PRE" | grep -q '^OK dia_trong' || die "kiem 242 khong tron ven (ssh dut?)$1. KHONG doi gi."
  ok "kiem 242 dat$1"
}

ENV_ADD=$(cat <<EOV
# [v1.2 R4d c3_live DRY $TS] (deploy_v12_dry_r4.sh) — tai khoan chinh, KHONG lenh that: adapter dry, push tat (SHADOW_NO_PUSH=true giu nguyen)
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
export UNIVERSE_A1=1
export UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json
EOV
)
NADD=$(echo "$ENV_ADD" | wc -l)
if [ "$R4_JOB" != 1 ]; then
  run_pre ""
  say "--- se THEM vao conf/env.sh ($NADD dong, export sau ghi de gia tri cu):"
  echo "$ENV_ADD" | sed 's/^/   + /'
  if [ "$DRY" = 1 ]; then say "DRY=1: dung o day, khong doi gi. (DRY PASS)"; exit 0; fi

  # -------------------------------------------------------------- 3. YES 1 lan -> JOB NEN (setsid nohup) + tail log
  lock_busy && die "dang co 1 job deploy_v12_dry_r4 khac chay (pid $(cat "$LOCKF"), $LOCKF). Khong doi gi."
  echo
  say ">>> Se deploy jar R4d (c3_live DRY tai khoan chinh) len 242 trong khung gio hop le ke tiep (JOB NEN: dong terminal khong sao). Go YES (in hoa) de tiep tuc:"
  read -r ANS
  [ "$ANS" = "YES" ] || { say "Huy. Khong doi gi."; exit 0; }
  JOBLOG=$LOGDIR/deploy_v12dry_r4_${TS}_job_$$.log
  YESF=$LOGDIR/.deploy_v12dry_r4_${TS}_$$.yes
  ( umask 077; echo "$TS" > "$YESF" ) || die "khong ghi duoc $YESF"
  : > "$JOBLOG"
  R4_JOB=1 R4_TS=$TS R4_JOBLOG=$JOBLOG R4_YES_FILE=$YESF setsid nohup bash "$SELF" >> "$JOBLOG" 2>&1 < /dev/null &
  BG=$!
  say "job NEN pid=$BG job_log=$JOBLOG"
  say "Dong terminal / mat ket noi KHONG dung job. Xem lai: tail -f $JOBLOG   (ket qua gui Telegram)"
  tail --pid="$BG" -n +1 -f "$JOBLOG" &
  TP=$!
  wait "$BG"; RC=$?
  wait "$TP" 2>/dev/null
  say "job ket thuc rc=$RC (0 XONG | 1 DUNG/da rollback | 2 ROLLBACK LOI: PAUSE con | 3 XONG nhung PAUSE con). Log job: $JOBLOG"
  exit "$RC"
fi

# ================================================================ JOB NEN (R4_JOB=1)
[ -n "${R4_YES_FILE:-}" ] && [ -f "$R4_YES_FILE" ] && [ "$(cat "$R4_YES_FILE" 2>/dev/null)" = "$TS" ] \
  || die "job nen KHONG co xac nhan YES tu foreground (R4_YES_FILE) => TU CHOI, khong doi gi"
rm -f "$R4_YES_FILE"
lock_busy && die "dang co job deploy_v12_dry_r4 khac chay (pid $(cat "$LOCKF")). Khong doi gi."
echo $$ > "$LOCKF"
trap 'rm -f "$LOCKF"' EXIT
tg "[deploy dry R4d] job NEN bat dau TS=$TS: cho khung gio -> kiem 242 lai -> deploy. Log: $LOG"
if [ "$FORCE_TIME" != 1 ]; then
  W=0
  until time_ok; do
    [ "$W" -ge "$WINDOW_WAIT_MAX_S" ] && die "cho khung gio qua ${WINDOW_WAIT_MAX_S}s. Khong doi gi. Chay lai sau."
    [ $((W % 300)) = 0 ] && say "cho khung gio hop le (phut :10-:44, tranh 07:xx/19:xx, 00:50-01:20, 12:50-13:20) — da cho ${W}s"
    sleep 30; W=$((W + 30))
  done
  ok "khung gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) hop le"
fi
run_pre " (lan 2: ngay truoc khi doi gi)"

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
NO=\$(grep -o '"onboardDate":[0-9]' \$X | wc -l)
ST=\$(grep -o '"serverTime":[0-9]*' \$X | head -1 | cut -d: -f2)
if [ "\$N" -gt 100 ] && [ "\$NC" -gt 0 ] && [ "\$NU" -gt 0 ] && [ "\$NT" -ge "\$MINTF" ] && [ "\$NO" -ge "\$N" ] && [ "\${ST:-0}" -gt 0 ]; then
  mv -f \$X run/c3live_exchangeInfo.json; echo "OK exchangeInfo so_symbol=\$N contractType=\$NC underlyingType=\$NU TradFi=\$NT onboardDate=\$NO serverTime=\$ST"
else
  rm -f \$X; echo "FAIL exchangeInfo so_symbol=\$N contractType=\$NC underlyingType=\$NU TradFi=\$NT onboardDate=\$NO serverTime=\${ST:-0} (can >100 symbol, du truong, TradFi >= \$MINTF, serverTime, onboardDate moi symbol)"; exit 0
fi
echo "\$EB" | base64 -d >> conf/env.sh
D=\$(diff conf/env.sh.bak_v12pre_\$TS conf/env.sh | grep -c '^>')
[ "\$D" = "\$NADD" ] && echo "OK env_them_\${D}_dong" || { echo "FAIL env_diff=\$D"; restore; exit 0; }
grep -q '^export SHADOW_NO_PUSH=true' conf/env.sh && echo "OK SHADOW_NO_PUSH=true giu nguyen" || { echo "FAIL SHADOW_NO_PUSH"; restore; exit 0; }
DS=\$(diff bin/start.sh.bak_v12pre_\$TS bin/start.sh | grep -c '^[<>]')
[ "\$DS" = 0 ] && echo "OK start.sh_khong_doi" || { echo "FAIL start.sh_doi=\$DS"; restore; exit 0; }
EOF
) || PREP="$PREP
FAIL ssh_buoc_chuan_bi_loi"
echo "$PREP"
if echo "$PREP" | grep -q '^FAIL' || ! echo "$PREP" | grep -q '^OK start.sh_khong_doi'; then
  if $SSH_242 "cd $A && { [ ! -f conf/env.sh.bak_v12pre_$TS ] || \cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh; } && ! grep -q '^export LIVE_ADAPTER' conf/env.sh && echo env_sach"; then
    die "buoc chuan bi co FAIL / khong tron ven (env.sh sach). Jar cu van chay, khong co gi bi doi."
  fi
  die "buoc chuan bi FAIL VA khong xac nhan duoc env.sh (ssh?). KIEM TAY tren 242: cd $A && grep -n LIVE_ADAPTER conf/env.sh ; neu co: cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh"
fi
ok "chuan bi xong (jar cu van dang chay)"
time_ok || [ "$FORCE_TIME" = 1 ] || { $SSH_242 "cd $A && \cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh"; die "het khung gio trong luc chuan bi (env da khoi phuc). Chay lai."; }

# ---------------------------------------------------------------- 4b. [R4d] kiem file exchangeInfo A1 NGAY truoc restart (bot cu van chay)
say "--- [R4d] kiem file exchangeInfo (UNIVERSE_A1 + R7 cung file) ngay truoc restart"
A1C=$($SSH_242 "bash -s -- $A $MIN_TRADFI PRE_RESTART_A1" <<'EOF'
A=$1; MINTF=$2; cd "$A" || { echo "FAIL cd"; exit 0; }
X=run/c3live_exchangeInfo.json
[ -s "$X" ] || { echo "FAIL a1_file_thieu $X"; echo "END_A1"; exit 0; }
N=$(grep -o '"symbol":"' $X | wc -l)
NT=$(grep -o '"contractType":"[A-Z_]*TRADI\{0,1\}FI[A-Z_]*"' $X | wc -l)
NO=$(grep -o '"onboardDate":[0-9]' $X | wc -l)
ST=$(grep -o '"serverTime":[0-9]*' $X | head -1 | cut -d: -f2)
if [ "$N" -gt 100 ] && [ "$NT" -ge "$MINTF" ] && [ "$NO" -ge "$N" ] && [ "${ST:-0}" -gt 0 ]; then
  echo "OK a1_file symbols=$N TradFi=$NT onboardDate=$NO serverTime=$ST md5=$(md5sum < $X | cut -c1-32)"
else
  echo "FAIL a1_file symbols=$N TradFi=$NT onboardDate=$NO serverTime=${ST:-0}"
fi
grep -qx 'export UNIVERSE_A1=1' conf/env.sh && grep -qx 'export UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json' conf/env.sh \
  && grep -qx 'export LIVE_C3_EXCHANGEINFO_FILE=run/c3live_exchangeInfo.json' conf/env.sh && echo "OK a1_env_cung_file_R7" || echo "FAIL a1_env"
echo "END_A1"
EOF
) || A1C="$A1C
FAIL ssh_kiem_a1_loi"
echo "$A1C"
if echo "$A1C" | grep -q '^FAIL' || ! echo "$A1C" | grep -qx 'END_A1'; then
  if $SSH_242 "cd $A && \cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh && ! grep -q '^export LIVE_ADAPTER' conf/env.sh && echo env_sach"; then
    die "kiem file A1 truoc restart FAIL (env.sh da khoi phuc). Jar cu van chay, khong co gi bi doi."
  fi
  die "kiem file A1 truoc restart FAIL VA khong xac nhan duoc env.sh. KIEM TAY tren 242: cd $A && cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh"
fi
ok "file exchangeInfo A1 hop le (cung file R7)"

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
  local RBCMD="FORCE_TIME=1 bash $RB_SH $TS" RRC M
  if [ "$(md5sum < "$RB_SH" 2>/dev/null | cut -c1-32)" != "$RB_MD5" ]; then
    say "!! md5 rollback_v12.sh KHAC pin $RB_MD5 => KHONG chay rollback tu dong"
    RRC=99
  else
    YES_AUTO=1 FORCE_TIME=1 bash "$RB_SH" "$TS"; RRC=$?
  fi
  if [ "$RRC" = 0 ]; then
    $SSH_242 "rm -f $WD_PAUSE" || say "CANH BAO: khong xoa duoc PAUSE lan nua (rollback da tu xoa khi xong)"
    say "DEPLOY FAIL ($1). Da ROLLBACK xong (242 ve c3_shadow). Gui log cho MASTER: $LOG"
    tg "[deploy dry R4d] FAIL TS=$TS: $1 => ROLLBACK TU DONG XONG (242 ve c3_shadow). Log: $LOG"
    exit 1
  fi
  M="PAUSE còn — chạy rollback tay: $RBCMD"
  say "DEPLOY FAIL ($1). ROLLBACK TU DONG LOI (rc=$RRC)."
  say "$M"
  tg "[deploy dry R4d] KHAN TS=$TS: deploy FAIL ($1) VA ROLLBACK TU DONG LOI (rc=$RRC). $M | log $LOG"
  exit 2
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
CHK() { $SSH_242 "PP='$PROC_PAT' bash -s -- $A $NJ_MD5 $MIN_TRADFI" <<'EOF'
A=$1; NJM=$2; MINTF=$3; cd "$A"
L=logs/full.log
N=$(grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' $L | tail -1 | cut -d: -f1)
N=${N:-1}
P=$(pgrep -f "$PP" | head -1)
T() { tail -n +$N $L | grep -a -c "$1"; }
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] && echo "OK jar" || echo "FAIL jar"
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK 1_process" || echo "FAIL so_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in 'LIVE_PROFILE=c3_live' 'LIVE_ADAPTER=dry' 'LIVE_KILLSW_MODE=act' 'SHADOW_NO_PUSH=true' 'C3_CAPITAL=10000' 'LIVE_TS_MKT_EXT=1' 'LIVE_HEARTBEAT=1' 'UNIVERSE_A1=1' 'UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json'; do
  echo "$E" | grep -qx "$k" && echo "OK env $k" || echo "FAIL env $k"
done
echo "$E" | grep -q '^LIVE_ENTRY_ENABLED=true' && echo "FAIL env LIVE_ENTRY_ENABLED=true" || echo "OK env khong_LIVE_ENTRY_ENABLED"
[ "$(T 'PUSH=OFF')" -ge 1 ]                             && echo "OK push_OFF"           || echo "WAIT push_OFF"
[ "$(T '\[KILLSW\] BAT mode=act')" -ge 1 ]              && echo "OK killsw_act_armed"   || echo "WAIT killsw_act_armed"
[ "$(T '\[C3-LIVE\] khoi dong adapter=DRY')" -ge 1 ]   && echo "OK c3live_DRY"         || echo "WAIT c3live_DRY"
[ "$(T 'killSwitchArmed=true')" -ge 1 ]                 && echo "OK killSwitchArmed"    || echo "WAIT killSwitchArmed"
[ "$(T 'LEGACY tren tai khoan chinh')" -ge 1 ]          && echo "OK R4_LEGACY_scope"    || echo "WAIT R4_LEGACY_scope"
[ "$(T 'exchangeInfo KHONG hop le')" = 0 ]              && echo "OK exchangeInfo_hop_le" || echo "FAIL exchangeInfo_KHONG_hop_le"
# [R4d] dong init UNIVERSE_A1 (TradFi >= nguong R4b); khong co => WAIT (qua han => rollback)
A1L=$(tail -n +$N $L | grep -a '\[UNIVERSE-A1\] BAT' | tail -1)
A1TF=$(echo "$A1L" | grep -o 'TradFi=[0-9]*' | head -1 | cut -d= -f2)
if [ -z "$A1L" ]; then echo "WAIT UNIVERSE_A1_chua_co_dong_init"
elif [ "${A1TF:-0}" -ge "$MINTF" ]; then echo "OK UNIVERSE_A1 TradFi=$A1TF $(echo "$A1L" | grep -o 'INDEX=[0-9]*' | head -1)"
else echo "FAIL UNIVERSE_A1 TradFi=${A1TF:-?} < $MINTF"; fi
[ "$(T '\[UNIVERSE-A1\] reload')" = 0 ]                 && echo "OK UNIVERSE_A1_khong_reload_loi" || echo "FAIL UNIVERSE_A1_reload_loi"
[ "$(T 'STALE snapshot=')" = 0 ]                        && echo "OK khong_universe_STALE" || echo "FAIL universe_STALE=$(T 'STALE snapshot=')"
U=$(tail -n +$N $L | grep -a -o '\[UNIVERSE\] listed=[0-9]* alive=[0-9]* tradable=[0-9]*' | tail -1)
UT=$(echo "$U" | grep -o 'tradable=[0-9]*' | cut -d= -f2)
[ "${UT:-0}" -gt 100 ] && echo "OK universe $U" || echo "WAIT universe ${U:-chua_co}"
[ "$(T '\[C3-LIVE-RECON\] khoi dong')" -ge 1 ]         && echo "OK reconcile_khoi_dong" || echo "WAIT reconcile_khoi_dong"
[ "$(T 'reconcile khoi dong LOI')" = 0 ]                && echo "OK reconcile_khong_loi" || echo "FAIL reconcile_LOI"
[ "$(T '\[C3-LIVE-ORDER\]')" = 0 ]                      && echo "OK 0_lenh_that"        || echo "FAIL co_dong_C3-LIVE-ORDER(lenh_that?)"
# [R4c D3] CHI cac dong TU CHOI co hai (runtime c3 khong tao duoc / moi leg bi tu choi / act bi ha / manage-only).
# "TU CHOI" cua lop pham vi c3 (ghi len symbol LEGACY), reanchor, "[OI-GUARD-2] ... STALE" la binh thuong => chi INFO.
for p in 'KHONG tao duoc runtime' 'moi leg c3_live bi TU CHOI' 'LIVE_KILLSW_MODE=act BI TU CHOI' 'MANAGE-ONLY'; do
  [ "$(T "$p")" = 0 ] && echo "OK khong '$p'" || echo "FAIL co '$p' x$(T "$p")"
done
echo "INFO TU_CHOI_vo_hai=$(T 'TU CHOI') OI_STALE=$(T 'oi_feat pipeline STALE') C5_GLOBAL_BLOCKED=$(T 'GLOBAL BLOCKED')"
[ "$(T '\[KILLSW\] LATCH')" = 0 ] && echo "OK 0_KILLSW_LATCH" || echo "FAIL KILLSW_LATCH"
if [ -f run/heartbeat ]; then AGE=$(( $(date +%s) - $(stat -c %Y run/heartbeat) )); [ $AGE -lt 180 ] && echo "OK heartbeat_tuoi=${AGE}s" || echo "WAIT heartbeat_tuoi=${AGE}s"; else echo "WAIT heartbeat_chua_co"; fi
X=$(tail -n +$N $L | grep -a -v 'Picked up' | grep -a -c 'Exception\|\[OPS\] loi hook\|\[C3-LIVE\] loi vong')
[ "$X" = 0 ] && echo "OK 0_exception" || echo "FAIL exception=$X"
echo "INFO so_dong_LIVE-DRY=$(T '\[LIVE-DRY\]')"
echo "END_CHK"
EOF
}
RESULT=""
for i in $(seq 1 "$POST_ROUNDS"); do
  say "--- kiem sau start lan $i/$POST_ROUNDS (cho ${POST_WAIT_S}s)"; sleep "$POST_WAIT_S"
  RESULT=$(CHK); CRC=$?
  # [R4c] ket qua rong / ssh dut / khong toi END_CHK => FAIL (khong duoc coi la DAT)
  { [ "$CRC" = 0 ] && echo "$RESULT" | grep -qx 'END_CHK'; } || RESULT="$RESULT
FAIL kiem_sau_start_khong_tron_ven(ssh_rc=$CRC)"
  echo "$RESULT"
  echo "$RESULT" | grep -q '^FAIL' && break
  echo "$RESULT" | grep -q '^WAIT' || break
done
if echo "$RESULT" | grep -q '^FAIL\|^WAIT'; then
  autorb "kiem sau start KHONG DAT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200))"
fi
ok "kiem sau start DAT"
if ! $SSH_242 "rm -f $WD_PAUSE"; then
  M="PAUSE còn — xoa tay: $SSH_242 \"rm -f $WD_PAUSE\""
  say "deploy DAT nhung KHONG xoa duoc watchdog PAUSE (ssh?). $M"
  tg "[deploy dry R4d] TS=$TS deploy DAT nhung $M (watchdog dang tam dung). Log: $LOG"
  exit 3
fi
say "xoa watchdog PAUSE"
say "=== XONG. $START_LINE"
say "Theo doi: bash $(cd "$(dirname "$0")" && pwd)/c3live_status.sh   |   Rollback: FORCE_TIME=1 bash $RB_SH $TS"
say "Gui cho MASTER dong tren + file log: $LOG"
tg "[deploy dry R4d] XONG TS=$TS: c3_live DRY tai khoan chinh chay, kiem sau start DAT. $START_LINE | Rollback: FORCE_TIME=1 bash $RB_SH $TS"
