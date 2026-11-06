#!/usr/bin/env bash
# =============================================================================
# deploy_chain.sh — [V12 R4t] CHUOI deploy nhieu buoc = 1 LENH (Oracle): tu cho, tu kiem, tu chay buoc ke. Owner KHONG canh gio.
#   bash ~/claude_master/deploy/deploy_chain.sh qf4_then_r4t          # in ke hoach + trang thai, go YES 1 lan => JOB NEN
#   DRY=1 bash ~/claude_master/deploy/deploy_chain.sh qf4_then_r4t    # CHI DOC: ke hoach + trang thai tung buoc (+ DRY=1 cua buoc)
#   bash ~/claude_master/deploy/deploy_chain.sh status                # job dang o buoc nao + 25 dong log cuoi
#   bash ~/claude_master/deploy/deploy_chain.sh stop                  # dung chuoi TRUOC buoc ke (buoc dang chay chay tron, co rollback rieng)
# Preset qf4_then_r4t:
#   1. qf4 : collectData jar QF4 (deploy_ingest_qf4.sh). XONG neu jar ingestor dang chay = JAR_MD5 cua script. Dang co job QF4 chay
#            (owner chay tay) => CHO no ket thuc (khong chay song song); ket thuc ma khong XONG => DUNG CHUOI + KHAN.
#   2. r4t : v_t_m jar r4t (swap_v12_dry_jar.sh, NJ_MD5 pin). XONG neu jar v_t_m = NJ_MD5 va 1 process.
# Sau MOI buoc: chi di tiep khi rc=0 VA hau kiem on dinh >= STABLE_S (900 s) lien tuc:
#   collectData (ingqf4_check_remote.sh): 0 FAIL, khong WAIT — KLINE-COVER du, 0 http429/418, price_gap/price_age OK, 0 ban/restart;
#   v_t_m: 1 process, 0 dong ERROR tu moc buoc, latch NONE (+ [MINUTE-GUARD] BAT sau r4t). WAIT keo dai > STABLE_MAX_S => FAIL.
# Buoc ke chi bat dau trong KHUNG GIO hop le ke tiep (:10-:39 de con >= 5' trong khung :10-:44; tranh gio 07/19, 00:50-01:20,
#   12:50-13:20). Buoc FAIL / rollback / hau kiem TRUOT => DUNG CA CHUOI + Telegram KHAN; khong chay buoc sau.
# Idempotent: buoc da XONG (md5 tren 242) => bo qua (van kiem on dinh truoc buoc ke).
# Ma thoat job: 0 XONG ca chuoi | 1 DUNG (FAIL/stop/het gio). Bien test: SSH_242 APP_DIR ING_DIR QF4_SH SWAP_SH CHECK_R CHAIN_DIR
#   STABLE_S STABLE_MAX_S CHK_POLL_S WAIT_RUNNING_MAX_S WINDOW_WAIT_MAX_S FORCE_TIME TIME_OK_FILE DEPLOY_TG_SINK QF4_PAT
# =============================================================================
set -uo pipefail
D=${CHAIN_DIR:-/home/ubuntu/claude_master/deploy}
C3=${C3_OPS:-/home/ubuntu/claude_master/v12/c3live/ops/c3live}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
APP_DIR=${APP_DIR:-/home/chuyennd/java/v_t_m}
ING_DIR=${ING_DIR:-/home/chuyennd/java/collectData}
QF4_SH=${QF4_SH:-$D/deploy_ingest_qf4.sh}
SWAP_SH=${SWAP_SH:-$C3/swap_v12_dry_jar.sh}
CHECK_R=${CHECK_R:-$D/ingqf4_check_remote.sh}
QF4_PAT=${QF4_PAT:-deploy_ingest_qf4.sh}
STABLE_S=${STABLE_S:-900}
STABLE_MAX_S=${STABLE_MAX_S:-3600}
CHK_POLL_S=${CHK_POLL_S:-60}
WAIT_RUNNING_MAX_S=${WAIT_RUNNING_MAX_S:-10800}
WINDOW_WAIT_MAX_S=${WINDOW_WAIT_MAX_S:-10800}
FORCE_TIME=${FORCE_TIME:-0}
DRY=${DRY:-0}
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
ST=$D/.deploy_chain
mkdir -p "$ST"
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
tg() {
  local msg code tok chat
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g' | head -c 3500)
  if [ -n "${DEPLOY_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$DEPLOY_TG_SINK"; return 0; fi
  [ -r "$DEPLOY_TG_ENV" ] || { say "!! khong doc duoc $DEPLOY_TG_ENV — KHONG gui Telegram"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || return 1
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null)
  tok=""; [ "$code" = 200 ]
}
setst() { echo "$*" > "$ST/step"; }
# ------------------------------------------------------------------ status / stop
case "${1:-}" in
  status)
    P=$(cat "$ST/pid" 2>/dev/null); L=$(cat "$ST/log" 2>/dev/null)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then echo "JOB CHAY pid=$P preset=$(cat "$ST/preset" 2>/dev/null)"; else echo "KHONG co job chuoi dang chay (pid cu ${P:-none})"; fi
    echo "buoc: $(cat "$ST/step" 2>/dev/null)"; [ -f "$ST/STOP" ] && echo "DA YEU CAU STOP"
    [ -n "$L" ] && { echo "log: $L"; tail -n 25 "$L"; }
    exit 0;;
  stop)
    P=$(cat "$ST/pid" 2>/dev/null)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then touch "$ST/STOP"; echo "Da yeu cau STOP: job $P dung TRUOC buoc ke / trong luc cho (buoc dang chay neu co se chay tron)."
    else echo "Khong co job chuoi dang chay."; fi
    exit 0;;
esac
PRESET=${1:-}
case "$PRESET" in
  qf4_then_r4t) STEPS="qf4 r4t";;
  *) echo "Dung: $0 <preset>|status|stop — preset: qf4_then_r4t"; exit 1;;
esac
QF4_MD5=$(sed -n 's/^JAR_MD5=\([0-9a-f]\{32\}\).*/\1/p' "$QF4_SH" 2>/dev/null | head -1)
R4T_MD5=$(sed -n 's/^NJ_MD5=\${NJ_MD5:-\([0-9a-f]\{32\}\)}.*/\1/p' "$SWAP_SH" 2>/dev/null | head -1)
[ -n "$QF4_MD5" ] || { echo "khong doc duoc JAR_MD5 tu $QF4_SH"; exit 1; }
[ -n "$R4T_MD5" ] || { echo "khong doc duoc NJ_MD5 tu $SWAP_SH"; exit 1; }

# ------------------------------------------------------------------ doc 242 (CHI DOC)
rstate() {   # in KEY=VAL: ING_N ING_MD5 VTM_N VTM_MD5 VTM_PID LATCH LINES
  $SSH_242 "bash -s -- $ING_DIR $APP_DIR" <<'EOF'
C=$1; A=$2
N=$(pgrep -fc 'websocket.BinanceDataIngestor'); P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
FD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
echo "ING_N=$N"; echo "ING_MD5=$( [ -n "$FD" ] && md5sum < "$FD" 2>/dev/null | cut -c1-32)"
cd "$A" 2>/dev/null || { echo "VTM_N=0"; echo END_ST; exit 0; }
PP=${PROC_PAT:-BinanceOrderTradingManager}
echo "VTM_N=$(pgrep -fc "$PP")"; echo "VTM_PID=$(pgrep -f "$PP" | head -1)"
echo "VTM_MD5=$(md5sum < target/binance-java-sdk-1.2.4.jar 2>/dev/null | cut -c1-32)"
echo "LATCH=$(sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' run/killsw_latch.json 2>/dev/null | head -1)"
echo "LINES=$(wc -l < logs/full.log 2>/dev/null || echo 0)"
echo END_ST
EOF
}
kv() { echo "$RS" | sed -n "s/^$1=//p" | tail -1; }
read_state() { RS=$(rstate 2>/dev/null); echo "$RS" | grep -qx END_ST; }
OTHER_PAT=${OTHER_PAT:-'swap_v12_dry_jar.sh|deploy_v12_dry_r4.sh|restart_v12_dry_reseed.sh|golive_[a-z_]*\.sh|rollback_v12.sh|rollback_ingest_qf4.sh'}
qf4_running() {   # job QF4 THAT (bo qua DRY=1)
  local p
  for p in $(pgrep -f "$QF4_PAT"); do
    [ "$p" = "$$" ] && continue
    tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -qx 'DRY=1' && continue
    echo "$p"; return 0
  done
}
other_deploy() { pgrep -af "$OTHER_PAT" | grep -v "deploy_chain" | head -1; }
step_done() {   # $1 = buoc; dua tren RS
  case "$1" in
    qf4) [ "$(kv ING_MD5)" = "$QF4_MD5" ] && [ "$(kv ING_N)" = 1 ];;
    r4t) [ "$(kv VTM_MD5)" = "$R4T_MD5" ] && [ "$(kv VTM_N)" = 1 ];;
  esac
}
time_ok() {
  [ "$FORCE_TIME" = 1 ] && return 0
  if [ -n "${TIME_OK_FILE:-}" ]; then [ -f "$TIME_OK_FILE" ]; return; fi
  local H M; H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  case "$H" in 7|19) return 1;; esac
  { [ "$M" -lt 10 ] || [ "$M" -gt 39 ]; } && return 1
  { [ "$H" = 0 ] && [ "$M" -ge 50 ]; } && return 1
  { [ "$H" = 12 ] && [ "$M" -ge 50 ]; } && return 1
  { [ "$H" = 13 ] && [ "$M" -le 20 ]; } && return 1
  { [ "$H" = 1 ] && [ "$M" -le 20 ]; } && return 1
  return 0
}

# ------------------------------------------------------------------ ke hoach + trang thai
plan() {
  say "=== deploy_chain preset=$PRESET (buoc: $STEPS) DRY=$DRY ==="
  echo "  1. qf4 : $QF4_SH (jar collectData $QF4_MD5) — dang co job QF4 => CHO no xong; XONG neu ingestor chay jar $QF4_MD5"
  echo "  2. r4t : $SWAP_SH (jar v_t_m $R4T_MD5) — XONG neu v_t_m chay jar $R4T_MD5"
  echo "  Qua buoc: rc=0 + hau kiem on dinh ${STABLE_S}s lien tuc (collectData: KLINE-COVER du, 0 429/418, price_gap OK; v_t_m: 0 ERROR, latch NONE)"
  echo "  Buoc ke: khung gio ke tiep :10-:39 (tranh 07/19h, 00:50-01:20, 12:50-13:20). FAIL/rollback => DUNG CA CHUOI + Telegram KHAN."
  if read_state; then
    echo "  242 hien tai: ingestor=$(kv ING_N) jar=$(kv ING_MD5) | v_t_m=$(kv VTM_N) jar=$(kv VTM_MD5) latch=$(kv LATCH)"
    for s in $STEPS; do
      if step_done "$s"; then echo "  - $s: DA XONG (se bo qua, van kiem on dinh)";
      elif [ "$s" = qf4 ] && [ -n "$(qf4_running)" ]; then echo "  - $s: DANG CHAY (job pid $(qf4_running)) => chuoi CHO no xong";
      else echo "  - $s: CHUA (se chay)"; fi
    done
  else
    echo "  !! khong doc duoc 242 (ssh)"; return 1
  fi
}

# ------------------------------------------------------------------ foreground
if [ "${CHAIN_JOB:-0}" != 1 ]; then
  plan || { say "DUNG: khong doc duoc 242"; exit 1; }
  P=$(cat "$ST/pid" 2>/dev/null)
  if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then say "DUNG: da co job chuoi pid $P dang chay (status/stop)."; exit 1; fi
  if [ "$DRY" = 1 ]; then
    read_state
    if ! step_done r4t; then say "--- DRY=1 cua swap (CHI DOC 242):"; DRY=1 bash "$SWAP_SH" 2>&1 | grep -E 'OK jar moi|jar_dang_chay|FAIL|DRY PASS|DUNG' | cut -c1-200; fi
    say "DRY=1: KHONG chay gi. (DRY PASS)"; exit 0
  fi
  say ">>> Go YES de chay CA CHUOI o JOB NEN (tu cho/kiem/chay buoc ke; khong can canh gio):"
  read -r ANS || ANS=""
  [ "$ANS" = YES ] || { say "Huy. Khong doi gi."; exit 0; }
  TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
  JL=$D/deploy_chain_${PRESET}_${TS}.log
  rm -f "$ST/STOP"; echo "$PRESET" > "$ST/preset"; echo "$JL" > "$ST/log"; setst "khoi dong"
  CHAIN_JOB=1 CHAIN_TS=$TS setsid nohup bash "$SELF" "$PRESET" >> "$JL" 2>&1 < /dev/null &
  echo $! > "$ST/pid"
  say "JOB NEN pid=$! log=$JL"
  say "Xem: bash $SELF status   | dung: bash $SELF stop   | tail -f $JL"
  exit 0
fi

# ------------------------------------------------------------------ JOB NEN
TS=${CHAIN_TS:-$(date +%s)}
echo $$ > "$ST/pid"
fail() { setst "DUNG: $*"; say "DUNG CHUOI: $*"; tg "[deploy_chain $PRESET] KHAN TS=$TS: DUNG CHUOI — $*. Cac buoc sau KHONG chay. Log $(cat "$ST/log" 2>/dev/null)"; exit 1; }
chk_stop() { [ -f "$ST/STOP" ] && { rm -f "$ST/STOP"; setst "DUNG theo yeu cau stop"; say "STOP theo yeu cau owner"; tg "[deploy_chain $PRESET] DUNG theo yeu cau stop TS=$TS"; exit 1; }; return 0; }
sleep_chk() { local i; for i in $(seq 1 "$1"); do chk_stop; sleep 1; done; }

# hau kiem on dinh: $1 = buoc, $2 = dong log v_t_m moc (dem ERROR tu day)
stable() {
  local step=$1 base=$2 t0 ok_since=0 now K V lg lines err
  t0=$(date +%s); setst "$step: hau kiem on dinh (${STABLE_S}s)"
  say "--- $step: hau kiem on dinh ${STABLE_S}s (moi ${CHK_POLL_S}s), moc log v_t_m dong $base"
  while :; do
    chk_stop
    now=$(date +%s)
    [ $((now - t0)) -gt "$STABLE_MAX_S" ] && fail "$step: hau kiem khong on dinh sau ${STABLE_MAX_S}s"
    if ! read_state; then say "ssh doc 242 loi — thu lai"; ok_since=0; sleep_chk "$CHK_POLL_S"; continue; fi
    lg=$(kv VTM_PID)
    K=$($SSH_242 "bash -s -- $ING_DIR $APP_DIR $QF4_MD5 ${lg:-0} new none" < "$CHECK_R" 2>/dev/null) || K="FAIL ssh_check_collectData"
    lines=$(kv LINES); [ "${lines:-0}" -lt $((base - 1)) ] && base=1   # log xoay (file ngan hon moc)
    V=$($SSH_242 "bash -s -- $APP_DIR $base $step" <<'EOF'
A=$1; B=$2; S=$3; cd "$A" || { echo "FAIL cd_vtm"; exit 0; }
PP=${PROC_PAT:-BinanceOrderTradingManager}
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK vtm_1_process" || echo "FAIL vtm_so_process=$(pgrep -fc "$PP")"
E=$(tail -n +$B logs/full.log 2>/dev/null | grep -a ' ERROR ' | head -1 | cut -c1-160)
[ -z "$E" ] && echo "OK vtm_0_ERROR" || echo "FAIL vtm_ERROR: $E"
grep -q '"latch":"NONE"' run/killsw_latch.json 2>/dev/null && echo "OK latch_NONE" || echo "FAIL latch_khac_NONE"
if [ "$S" = r4t ]; then tail -n +$B logs/full.log | grep -a -q '\[MINUTE-GUARD\] TAT' && echo "FAIL MINUTE-GUARD_TAT"; fi
echo END_V
EOF
) || V="FAIL ssh_check_vtm"
    echo "$V" | grep -qx END_V || V="$V
FAIL vtm_check_khong_tron_ven"
    if echo "$K$V" | grep -q '^FAIL'; then
      echo "$K"; echo "$V"; fail "$step: hau kiem FAIL ($(echo "$K
$V" | grep '^FAIL' | head -3 | tr '\n' ' '))"
    fi
    if echo "$K" | grep -q '^WAIT' || ! echo "$K" | grep -q '^OK kline_phu_phut_da_chot'; then
      ok_since=0; say "$step: cho on dinh: $(echo "$K" | grep '^WAIT' | tr '\n' ' ' | cut -c1-200)"
    else
      [ "$ok_since" = 0 ] && ok_since=$now
      if [ $((now - ok_since)) -ge "$STABLE_S" ]; then
        say "$step: ON DINH ${STABLE_S}s: $(echo "$K" | grep -E '^OK (kline_phu|0_http|price_gap|price_age)' | tr '\n' ' ') | $(echo "$V" | grep '^OK' | tr '\n' ' ')"
        return 0
      fi
    fi
    sleep_chk "$CHK_POLL_S"
  done
}
wait_window() {   # $1 nhan
  local w=0; setst "$1: cho khung gio"
  until time_ok; do
    chk_stop
    [ $((w % 600)) = 0 ] && say "$1: cho khung gio ke tiep (:10-:39, tranh 07/19h...) — da cho ${w}s"
    [ "$w" -ge "$WINDOW_WAIT_MAX_S" ] && fail "$1: cho khung gio qua ${WINDOW_WAIT_MAX_S}s"
    sleep 10; w=$((w + 10))
  done
}
wait_no_deploy() {   # khong chay song song voi job deploy khac
  local w=0 p
  while :; do
    p=$(qf4_running); [ -z "$p" ] && p=$(other_deploy | awk '{print $1}')
    [ -z "$p" ] && return 0
    chk_stop
    [ $((w % 300)) = 0 ] && say "$1: dang co job deploy khac chay (pid $p) — cho no xong (da cho ${w}s)"
    [ "$w" -ge "$WAIT_RUNNING_MAX_S" ] && fail "$1: job deploy khac (pid $p) chay qua ${WAIT_RUNNING_MAX_S}s"
    sleep 10; w=$((w + 10))
  done
}
say "=== JOB deploy_chain $PRESET TS=$TS pid=$$ (buoc: $STEPS; QF4 $QF4_MD5, r4t $R4T_MD5) ==="
tg "[deploy_chain $PRESET] BAT DAU TS=$TS: buoc $STEPS (tu cho/kiem; FAIL => dung ca chuoi + KHAN)"
FIRST=1
for s in $STEPS; do
  chk_stop
  read_state || { sleep 30; read_state || fail "$s: khong doc duoc 242 (ssh)"; }
  if [ "$s" = qf4 ] && [ -n "$(qf4_running)" ]; then
    setst "qf4: cho job QF4 dang chay"; say "--- qf4: job QF4 DANG CHAY (pid $(qf4_running)) — cho no xong, khong chay song song"
    tg "[deploy_chain $PRESET] qf4: phat hien job QF4 dang chay — cho no xong roi kiem"
    wait_no_deploy qf4
    read_state || fail "qf4: khong doc duoc 242 sau job QF4"
    step_done qf4 || fail "qf4: job QF4 ket thuc nhung ingestor KHONG chay jar $QF4_MD5 (jar=$(kv ING_MD5)) — FAIL/rollback"
    L4=$(ls -t "$D"/deploy_ingest_qf4_*.log 2>/dev/null | grep -v '_dry.log' | head -1)
    if [ -n "$L4" ] && ! grep -q 'XONG. collectData chay jar' "$L4"; then fail "qf4: log job QF4 $L4 KHONG co dong XONG (rollback/dung?)"; fi
    say "qf4: job QF4 da XONG (jar $QF4_MD5)"; tg "[deploy_chain $PRESET] qf4 XONG (job owner) — kiem on dinh ${STABLE_S}s"
  elif step_done "$s"; then
    say "--- $s: DA XONG tu truoc (md5 tren 242 dung) => bo qua"
  else
    wait_no_deploy "$s"
    if [ "$FIRST" = 0 ] || [ "$s" = r4t ]; then wait_window "$s"; fi
    wait_no_deploy "$s"
    read_state || fail "$s: khong doc duoc 242 truoc khi chay"
    step_done "$s" && { say "$s: da XONG trong luc cho => bo qua"; continue; }
    setst "$s: DANG CHAY"; say "--- $s: CHAY"; tg "[deploy_chain $PRESET] $s: BAT DAU"
    case "$s" in
      qf4) echo YES | bash "$QF4_SH"; RC=$?;;
      r4t) echo YES | bash "$SWAP_SH"; RC=$?;;
    esac
    [ "$RC" = 0 ] || fail "$s: script rc=$RC (FAIL/rollback)"
    read_state || fail "$s: khong doc duoc 242 sau buoc"
    step_done "$s" || fail "$s: rc=0 nhung md5 tren 242 khong dung"
    tg "[deploy_chain $PRESET] $s: script XONG rc=0 — kiem on dinh ${STABLE_S}s"
  fi
  FIRST=0
  read_state || fail "$s: khong doc duoc 242"
  BASE=$(( $(kv LINES) + 1 ))
  if [ "$s" = r4t ]; then   # sau swap: 0 ERROR tinh tu dong khoi dong JVM moi nhat
    SB=$($SSH_242 "grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' $APP_DIR/logs/full.log | tail -1 | cut -d: -f1" 2>/dev/null)
    [[ "$SB" =~ ^[0-9]+$ ]] && BASE=$SB
  fi
  stable "$s" "$BASE"
  setst "$s: XONG + on dinh"; tg "[deploy_chain $PRESET] $s: XONG + on dinh ${STABLE_S}s"
done
setst "XONG ca chuoi"; say "=== XONG CA CHUOI $PRESET ==="
tg "[deploy_chain $PRESET] XONG CA CHUOI TS=$TS (QF4 $QF4_MD5 + r4t $R4T_MD5, on dinh)"
exit 0
