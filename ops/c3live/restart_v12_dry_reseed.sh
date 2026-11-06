#!/usr/bin/env bash
# =============================================================================
# restart_v12_dry_reseed.sh — [V12 R4o] RESTART v_t_m dry v1.2 (c3_live, LIVE_ADAPTER=dry) 1 LAN de:
#   (a) nap seed gate buffer (PREREG_PARITY_V12_DRY ADD6 §2: CHI seed A∪C da DAT V-OVL) qua GATE_BUFFER_SEED + _MD5, VA
#   (b) bat C11: LIVE_SEED_EXCLUDE_DECISION_MIN=1 (race seed/tick dau sau restart).
#   SEED=none: CHI ap C11 (khi seed TRUOT) — van 1 lan restart.
# Chay tren ORACLE (owner), 1 lenh:
#   DRY=1 SEED=<file seed> SEED_MD5=<md5> bash ~/claude_master/v12/c3live/ops/c3live/restart_v12_dry_reseed.sh   # chi kiem
#   SEED=<file seed> SEED_MD5=<md5> bash ~/claude_master/v12/c3live/ops/c3live/restart_v12_dry_reseed.sh         # go YES
#   SEED=none bash .../restart_v12_dry_reseed.sh                                                                   # chi C11
# Thu tu: kiem Oracle (seed md5) -> kiem 242 CHI DOC (dry r4n dang chay, env, marker .seeded CHUA co, khong canary/soak/PAUSE,
#   RAM, 6 h truoc khong gate pass) -> khung gio :10-:44 -> YES -> chep seed + kiem md5 tren 242 -> backup env.sh -> them env ->
#   PAUSE token (+ tu go sau WD_PAUSE_MAX_S) -> stop -> backup gate_ratio_live.bin (+md5) -> start -> hau kiem (GATE-SEED OK,
#   .seeded md5, env process, LEGACY = truoc restart, latch NONE, 0 KHAN) -> go PAUSE. Hau kiem TRUOT => ROLLBACK TU DONG:
#   khoi phuc env.sh + gate_ratio_live.bin (md5) + xoa .seeded cua lan nay -> start lai dry nhu truoc.
# Ma thoat: 0 XONG | 1 DUNG/da rollback | 2 ROLLBACK LOI (PAUSE con — xem dong "PAUSE còn").
# Bien (test): SSH_242 SCP_242 RHOST APP_DIR PROC_PAT NJ_MD5 WD_PAUSE WD_PAUSE_MAX_S POST_WAIT_S POST_ROUNDS LOGDIR FORCE_TIME
#   DEPLOY_TG_ENV DEPLOY_TG_SINK SEED_MAX_LAG_H MIN_MEM_MB SSH_RETRY_S
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
NJ_MD5=${NJ_MD5:-304697108dbe6be639fad570e7b766b3}   # jar dry dang chay (r4s, ROUND4S) — khac => TU CHOI
SEED=${SEED:-}
SEED_MD5=${SEED_MD5:-}
SEED_MAX_LAG_H=${SEED_MAX_LAG_H:-}
WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}
WD_PAUSE_MAX_S=${WD_PAUSE_MAX_S:-1800}
POST_WAIT_S=${POST_WAIT_S:-60}
POST_ROUNDS=${POST_ROUNDS:-6}
MIN_MEM_MB=${MIN_MEM_MB:-1000}
DRY=${DRY:-0}
FORCE_TIME=${FORCE_TIME:-0}
SSH_RETRY_S=${SSH_RETRY_S:-10}
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
LOG=$LOGDIR/restart_v12_dry_reseed_${TS}.log
exec > >(tee -a "$LOG") 2>&1
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
die() { say "DUNG: $*"; say "KET QUA: TU_CHOI (khong doi gi). Log: $LOG"; exit 1; }
s242() {
  local i rc=255
  for i in 1 2 3; do
    $SSH_242 "$@" < /dev/null; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt 3 ] && { echo "[ssh 242 loi ket noi — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
s242in() {
  local in i rc=255
  in=$(cat)
  for i in 1 2 3; do
    printf '%s\n' "$in" | $SSH_242 "$@"; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt 3 ] && { echo "[ssh 242 loi ket noi — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
time_ok() {
  local H M
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1
  case "$H" in 7|19) return 1;; esac
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi
  return 0
}

say "=== restart_v12_dry_reseed TS=$TS SEED=${SEED:-?} DRY=$DRY ==="
# ---------------------------------------------------------------- 0. tham so + seed tren Oracle
[ -n "$SEED" ] || die "thieu SEED (duong dan file seed A∪C da DAT V-OVL, hoac SEED=none de chi ap C11)"
if [ "$SEED" = none ]; then
  MODE=c11
  [ -z "$SEED_MD5" ] || die "SEED=none nhung co SEED_MD5 — khong ro y dinh"
else
  MODE=seed
  [[ "$SEED_MD5" =~ ^[0-9a-f]{32}$ ]] || die "thieu/sai SEED_MD5 (32 hex, lay tu so C sau V-OVL DAT)"
  [ -f "$SEED" ] || die "khong thay file seed $SEED"
  GOT=$(md5sum < "$SEED" | cut -c1-32)
  [ "$GOT" = "$SEED_MD5" ] || die "md5 seed $GOT KHAC SEED_MD5 $SEED_MD5"
  [ -z "$SEED_MAX_LAG_H" ] || [[ "$SEED_MAX_LAG_H" =~ ^[0-9]+$ ]] || die "SEED_MAX_LAG_H khong phai so"
  say "OK seed $SEED md5=$SEED_MD5 ($(stat -c %s "$SEED") byte)"
fi
RSEED=$A/run/gate_seed_v12_${SEED_MD5:-none}.bin   # duong dan TUYET DOI tren 242 (env GATE_BUFFER_SEED)

# ---------------------------------------------------------------- 1. kiem 242 CHI DOC
pre242() {
  s242in "PP='$PROC_PAT' bash -s -- $A $NJ_MD5 $WD_PAUSE $MODE $MIN_MEM_MB" <<'EOF'
A=$1; NJM=$2; PAUSE=$3; MODE=$4; MINMEM=$5; cd "$A" || { echo "FAIL cd"; echo END_PRE; exit 0; }
N=$(pgrep -fc "$PP"); [ "$N" = 1 ] && echo "OK so_process=1" || echo "FAIL so_process=$N"
P=$(pgrep -f "$PP" | head -1)
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] && echo "OK jar_dry=$NJM" || echo "FAIL jar_dang_chay_khac_$NJM"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_PROFILE=c3_live LIVE_ADAPTER=dry SHADOW_NO_PUSH=true; do echo "$E" | grep -qx "$k" && echo "OK env_dang_chay $k" || echo "FAIL env_dang_chay $k"; done
grep -q '^export LIVE_ADAPTER=dry' conf/env.sh && echo "OK env.sh_dry" || echo "FAIL env.sh_khong_phai_dry"
grep -q '^export LIVE_ADAPTER=live' conf/env.sh && echo "FAIL env.sh_LIVE_ADAPTER=live"
HC=$(grep -c '^export LIVE_SEED_EXCLUDE_DECISION_MIN=1' conf/env.sh); HS=$(grep -c '^export GATE_BUFFER_SEED' conf/env.sh)
echo "INFO HAS_C11=$HC HAS_SEED_ENV=$HS"
[ "$HS" = 0 ] && echo "OK env.sh_chua_co_GATE_BUFFER_SEED" || echo "FAIL env.sh_da_co_GATE_BUFFER_SEED (da re-seed? MASTER xem)"
[ "$MODE" = c11 ] && { [ "$HC" = 0 ] && echo "OK chua_co_C11" || echo "FAIL C11_da_co (khong can restart)"; }
if [ "$MODE" = seed ]; then
  [ -f run/gate_ratio_live.bin.seeded ] && echo "FAIL da_co_run/gate_ratio_live.bin.seeded (seed se bi BO QUA)" || echo "OK chua_co_.seeded"
fi
[ -s run/gate_ratio_live.bin ] && echo "OK co_gate_ratio_live.bin md5=$(md5sum < run/gate_ratio_live.bin | cut -c1-32)" || echo "FAIL thieu_run/gate_ratio_live.bin"
[ -e "$PAUSE" ] && echo "FAIL PAUSE_watchdog_dang_co $(head -c 80 "$PAUSE" 2>/dev/null)" || echo "OK khong_PAUSE"
C=$(pgrep -fc 'C3LiveCanary|UserStreamSoak'); [ "$C" = 0 ] && echo "OK khong_canary_soak" || echo "FAIL canary/soak_dang_chay=$C"
M=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$M" -ge "$MINMEM" ] && echo "OK mem_avail=${M}MB" || echo "FAIL mem_avail=${M}MB < $MINMEM"
F=$(df -Pk . | awk 'NR==2{print $4}'); [ "${F:-0}" -gt 1048576 ] && echo "OK dia_trong=${F}k" || echo "FAIL dia_trong=${F}k"
L0=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')
[ -n "$L0" ] && echo "OK LEGACY_N=$L0" || echo "FAIL khong_doc_duoc_LEGACY_managed"
grep -q '"latch":"NONE"' run/killsw_latch.json 2>/dev/null && echo "OK latch_NONE" || echo "FAIL latch_khac_NONE"
if [ "$MODE" = seed ]; then   # ADD6 §2: khong re-seed khi co dot sap / gate PASS trong 6 h truoc (bao thu: 7 gio dong ho)
  PF=$(mktemp); for h in 0 1 2 3 4 5 6; do TZ=Asia/Ho_Chi_Minh date -d "-$h hour" '+%d/%m/%Y %H:'; done > $PF
  GP=$(tail -c 60000000 logs/full.log 2>/dev/null | grep -aF -f $PF | grep -a '\[GATE\] scale' | grep -avc 'n_pass=0')
  BD=$(tail -c 60000000 logs/full.log 2>/dev/null | grep -aF -f $PF | grep -a 'BIG_DOWN' | grep -avc 'CADENCE-SPLIT')
  rm -f $PF
  [ "$GP" = 0 ] && [ "$BD" = 0 ] && echo "OK khong_sap_6h (gate_pass=0 big_down=0)" || echo "FAIL dang_co_dot_sap_6h gate_pass=$GP big_down=$BD (ADD6: doi khung ke tiep)"
fi
echo END_PRE
EOF
}
PRE=$(pre242) || die "ssh toi 242 loi"
echo "$PRE"
echo "$PRE" | grep -qx END_PRE || die "kiem 242 khong tron ven (ssh dut?)"
echo "$PRE" | grep -q '^FAIL' && die "kiem 242 co muc FAIL (xem tren)"
L0=$(echo "$PRE" | sed -n 's/^OK LEGACY_N=//p'); HC=$(echo "$PRE" | sed -n 's/^INFO HAS_C11=\([0-9]*\).*/\1/p')
GR0=$(echo "$PRE" | sed -n 's/^OK co_gate_ratio_live.bin md5=//p')

ENV_ADD="# [v1.2 R4o reseed $TS] (restart_v12_dry_reseed.sh MODE=$MODE)"
[ "${HC:-0}" = 0 ] && ENV_ADD="$ENV_ADD
export LIVE_SEED_EXCLUDE_DECISION_MIN=1"
if [ "$MODE" = seed ]; then
  ENV_ADD="$ENV_ADD
export GATE_BUFFER_SEED=$RSEED
export GATE_BUFFER_SEED_MD5=$SEED_MD5"
  [ -n "$SEED_MAX_LAG_H" ] && ENV_ADD="$ENV_ADD
export GATE_BUFFER_SEED_MAX_LAG_H=$SEED_MAX_LAG_H"
fi
NADD=$(echo "$ENV_ADD" | wc -l)
say "--- se THEM vao $A/conf/env.sh ($NADD dong):"; echo "$ENV_ADD" | sed 's/^/   + /'
[ "$MODE" = seed ] && say "--- se chep seed -> 242:$RSEED (kiem md5 tren 242)"
say "--- hau kiem: $([ "$MODE" = seed ] && echo "[GATE-SEED] nap seed md5=$SEED_MD5 + .seeded, ")env process co LIVE_SEED_EXCLUDE_DECISION_MIN=1, LEGACY managed $L0, latch NONE, 0 KHAN"
if [ "$DRY" = 1 ]; then say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; fi
if [ "$FORCE_TIME" != 1 ] && ! time_ok; then
  die "gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) khong hop le (phut :10-:44, tranh 07/19h, 00:50-01:20, 12:50-13:20). Chay lai trong khung."
fi
say ">>> RESTART v_t_m dry ($MODE). LEGACY ngung quan ly ~30-60 s (SL tren san giu nguyen). Go YES de tiep tuc:"
read -r ANS || ANS=""
[ "$ANS" = YES ] || { say "Huy. Khong doi gi."; exit 0; }

# ---------------------------------------------------------------- 2. chep seed
if [ "$MODE" = seed ]; then
  $SCP_242 "$SEED" "${RHOST}$RSEED" || die "chep seed len 242 loi"
  RM=$(s242 "md5sum < $RSEED | cut -c1-32") || die "ssh kiem md5 seed loi"
  [ "$RM" = "$SEED_MD5" ] || die "md5 seed tren 242 $RM KHAC $SEED_MD5"
  say "OK seed tren 242 md5=$RM"
fi

# ---------------------------------------------------------------- 3. env + PAUSE + stop + backup gate + start
PAUSE_TOK="C3RESEED_V12 TS=$TS pid=$$"
on_sig() {
  trap - INT TERM HUP
  s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE" >/dev/null 2>&1
  say "BI DUNG (tin hieu). PAUSE cua lan nay da go (neu con). KIEM: bash $(cd "$(dirname "$0")" && pwd)/c3live_status.sh"
  tg "[reseed dry] TS=$TS bi DUNG giua chung. Kiem c3live_status.sh. Log $LOG"; exit 130
}
trap on_sig INT TERM HUP
EB=$(echo "$ENV_ADD" | base64 -w0)
RS=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $EB $NADD $WD_PAUSE $WD_PAUSE_MAX_S $$ $NJ_MD5" <<'EOF'
A=$1; TS=$2; EB=$3; NADD=$4; PAUSE=$5; MAXS=$6; JP=$7; NJM=$8; cd "$A" || { echo "FAIL cd"; exit 0; }
\cp -fp conf/env.sh conf/env.sh.bak_reseed_$TS || { echo "FAIL backup_env"; exit 0; }
echo "$EB" | base64 -d >> conf/env.sh
D=$(diff conf/env.sh.bak_reseed_$TS conf/env.sh | grep -c '^>')
[ "$D" = "$NADD" ] && echo "OK env_them_${D}_dong" || { \cp -f conf/env.sh.bak_reseed_$TS conf/env.sh; echo "FAIL env_diff=$D (da khoi phuc)"; exit 0; }
TOK="C3RESEED_V12 TS=$TS pid=$JP"
mkdir -p "$(dirname "$PAUSE")" 2>/dev/null; echo "$TOK t=$(date +%s)" > "$PAUSE" && echo "OK watchdog_PAUSE token='$TOK'" || echo "WARN khong_tao_duoc_PAUSE"
setsid nohup bash -c "sleep $MAXS; grep -q '^$TOK ' '$PAUSE' 2>/dev/null && rm -f '$PAUSE'" > /dev/null 2>&1 < /dev/null &
echo "LEGACY_TRUOC_STOP=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')"   # [R4r] chup NGAY truoc stop
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
if pgrep -f "$PP" >/dev/null; then \cp -f conf/env.sh.bak_reseed_$TS conf/env.sh; echo "FAIL van_con_process_sau_stop (env khoi phuc)"; exit 0; fi
echo "OK da_stop"
GR=run/gate_ratio_live.bin; GB=$GR.bak_reseed_$TS
{ \cp -fp "$GR" "$GB" && GM=$(md5sum < "$GB" | cut -c1-32) && [ "$GM" = "$(md5sum < "$GR" | cut -c1-32)" ] && echo "$GM" > "$GB.md5"; } \
  && echo "OK backup_gate_ratio md5=$GM" || echo "FAIL backup_gate_ratio"
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] || echo "FAIL jar_doi"
L=logs/full.log; echo "START_LINE=$(( $(wc -l < $L 2>/dev/null || echo 0) + 1 ))"
bin/daemon.sh start
sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process_sau_start"
EOF
) || RS="FAIL ssh_restart_loi"
echo "$RS"

autorb() {
  say "$1 => ROLLBACK TU DONG (ve dry truoc restart: env.sh + gate_ratio_live.bin backup TS=$TS)"
  local R
  R=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $WD_PAUSE $MODE" <<'EOF'
A=$1; TS=$2; PAUSE=$3; MODE=$4; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
[ -f conf/env.sh.bak_reseed_$TS ] || { echo "FAIL thieu_backup_env"; echo END_RB; exit 0; }
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
\cp -f conf/env.sh.bak_reseed_$TS conf/env.sh && echo "OK env_khoi_phuc"
GR=run/gate_ratio_live.bin; GB=$GR.bak_reseed_$TS
if [ -f "$GB.md5" ]; then
  [ ! -f "$GR" ] || mv -f "$GR" "$GR.rb_reseed_$TS"
  \cp -fp "$GB" "$GR"; [ "$(md5sum < "$GR" | cut -c1-32)" = "$(cat "$GB.md5")" ] && echo "OK gate_ratio_khoi_phuc md5=$(cat "$GB.md5")" || echo "FAIL gate_ratio_khoi_phuc"
else
  echo "INFO gate_ratio_khong_co_backup (chua toi buoc stop) => giu nguyen"
fi
[ "$MODE" = seed ] && [ -f "$GR.seeded" ] && mv -f "$GR.seeded" "$GR.seeded.rb_reseed_$TS" && echo "OK .seeded_cua_lan_nay_doi_ten"
bin/daemon.sh start; sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "$E" | grep -qx LIVE_ADAPTER=dry && echo "OK env LIVE_ADAPTER=dry" || echo "FAIL env LIVE_ADAPTER"
echo "$E" | grep -q '^GATE_BUFFER_SEED=' && echo "FAIL env van co GATE_BUFFER_SEED" || echo "OK env khong GATE_BUFFER_SEED"
grep -q "^C3RESEED_V12 TS=$TS " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"
[ -e "$PAUSE" ] && echo "WARN PAUSE_con (token khac)" || echo "OK PAUSE_go"
echo END_RB
EOF
) || R="FAIL ssh_rollback_loi"
  echo "$R"
  if echo "$R" | grep -qx END_RB && ! echo "$R" | grep -q '^FAIL'; then
    say "RESTART FAIL ($1). Da ROLLBACK xong: dry chay lai nhu truoc (khong seed$([ "${HC:-0}" = 0 ] && echo ", C11 nhu cu"))."
    tg "[reseed dry] FAIL TS=$TS: $1 => ROLLBACK TU DONG XONG. Log $LOG"
    exit 1
  fi
  local M="PAUSE còn — kiem tay: bash $(cd "$(dirname "$0")" && pwd)/c3live_status.sh ; env backup $A/conf/env.sh.bak_reseed_$TS"
  say "RESTART FAIL ($1). ROLLBACK TU DONG LOI. $M"
  tg "[reseed dry] KHAN TS=$TS: restart FAIL ($1) VA ROLLBACK LOI. $M | log $LOG"
  exit 2
}
if echo "$RS" | grep -q '^FAIL'; then
  if echo "$RS" | grep -q '^OK da_stop'; then autorb "restart co FAIL"; fi
  s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE" >/dev/null 2>&1
  die "buoc env/stop FAIL truoc khi dung bot (env da khoi phuc neu da sua). Xem tren."
fi
SL=$(echo "$RS" | sed -n 's/^START_LINE=//p'); SL=${SL:-1}
LB=$(echo "$RS" | sed -n 's/^LEGACY_TRUOC_STOP=\([0-9][0-9]*\)$/\1/p' | tail -1)   # [R4r] so LEGACY NGAY truoc stop (khong so cung)
if [ -n "$LB" ]; then [ "$LB" != "${L0:-}" ] && say "INFO LEGACY truoc stop=$LB (luc kiem truoc: ${L0:-?}) => hau kiem so voi $LB"; L0=$LB; fi

# ---------------------------------------------------------------- 4. hau kiem
CHK() {
  s242in "PP='$PROC_PAT' bash -s -- $A $SL $MODE ${SEED_MD5:-none} $RSEED ${L0:-0}" <<'EOF'
A=$1; SL=$2; MODE=$3; SM=$4; RSEED=$5; L0=$6; cd "$A"; L=logs/full.log
T() { tail -n +$SL $L 2>/dev/null | grep -a -c "$1"; }
P=$(pgrep -f "$PP" | head -1)
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK 1_process" || echo "FAIL so_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_PROFILE=c3_live LIVE_ADAPTER=dry SHADOW_NO_PUSH=true LIVE_SEED_EXCLUDE_DECISION_MIN=1; do
  echo "$E" | grep -qx "$k" && echo "OK env $k" || echo "FAIL env $k"
done
[ "$(T 'LIVE_SEED_EXCLUDE_DECISION_MIN=0 => race')" = 0 ] && echo "OK C11_khong_canh_bao_race" || echo "FAIL C11_van_canh_bao_race"
if [ "$MODE" = seed ]; then
  echo "$E" | grep -qx "GATE_BUFFER_SEED=$RSEED" && echo "$E" | grep -qx "GATE_BUFFER_SEED_MD5=$SM" && echo "OK env GATE_BUFFER_SEED" || echo "FAIL env GATE_BUFFER_SEED"
  [ "$(T '\[GATE-SEED\] KHAN')" = 0 ] || echo "FAIL GATE-SEED_KHAN"
  [ "$(T '\[GATE-SEED\] persist da nap seed truoc do')" = 0 ] || echo "FAIL GATE-SEED_BO_QUA"
  if [ "$(T "\[GATE-SEED\] nap seed .* md5=$SM")" -ge 1 ]; then echo "OK GATE-SEED_nap md5=$SM"; else echo "WAIT GATE-SEED_chua_nap"; fi
  grep -q "md5=$SM" run/gate_ratio_live.bin.seeded 2>/dev/null && echo "OK .seeded md5=$SM" || echo "WAIT .seeded_chua_co"
fi
[ "$(T '\[KILLSW\] LATCH')" = 0 ] && grep -q '"latch":"NONE"' run/killsw_latch.json 2>/dev/null && echo "OK latch_NONE" || echo "FAIL latch"
K=$(tail -n +$SL $L 2>/dev/null | grep -a 'KHAN' | grep -av 'DRY tren tai khoan chinh' | head -1 | cut -c1-160)
[ -z "$K" ] && echo "OK 0_KHAN" || echo "FAIL KHAN: $K"
[ "$(T 'KHONG tao duoc runtime')" = 0 ] && echo "OK runtime" || echo "FAIL KHONG_tao_duoc_runtime"
LN=$(tail -n +$SL $L 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')
# LEGACY khac truoc restart: SL tren san co the da khop trong luc dung => CANH BAO (rollback khong giup gi), owner kiem tay
if [ -z "$LN" ]; then echo "WAIT LEGACY_chua_co"; elif [ "$LN" = "$L0" ]; then echo "OK LEGACY_managed=$LN"; elif [ "$LN" -lt "$L0" ] 2>/dev/null; then echo "WARN LEGACY_managed=$LN < truoc stop $L0 (dong tu nhien luc dung? kiem tay)"; else echo "FAIL LEGACY_managed=$LN > truoc stop $L0 (TANG)"; fi
[ "$(T '\[GATE\] scale')" -ge 1 ] && echo "OK GATE_tick_chay" || echo "WAIT GATE_tick_chua_co"
echo END_CHK
EOF
}
RESULT=""
for r in $(seq 1 "$POST_ROUNDS"); do
  sleep "$POST_WAIT_S"
  RESULT=$(CHK) || RESULT="$RESULT
FAIL kiem_sau_start_ssh"
  echo "$RESULT" | grep -qx END_CHK || RESULT="$RESULT
FAIL kiem_sau_start_khong_tron_ven"
  say "--- hau kiem lan $r/$POST_ROUNDS"; echo "$RESULT"
  echo "$RESULT" | grep -q '^FAIL' && break
  echo "$RESULT" | grep -q '^WAIT' || break
done
if echo "$RESULT" | grep -q '^FAIL\|^WAIT'; then
  autorb "hau kiem KHONG DAT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200))"
fi
trap - INT TERM HUP
if ! s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE; [ ! -e $WD_PAUSE ]"; then
  say "XONG nhung PAUSE còn (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s neu van token lan nay"
fi
say "=== XONG ($MODE). $(echo "$RS" | grep '^OK started') | gate_ratio truoc=$GR0 (backup .bak_reseed_$TS)"
say "Ngay hom nay = XAM (ADD6 §2). P3: gio < restart dung buffer cu, gio >= restart dung seed + r live. Log: $LOG"
tg "[reseed dry] XONG TS=$TS MODE=$MODE$([ "$MODE" = seed ] && echo " seed md5=$SEED_MD5") C11=1. Log $LOG"
exit 0
