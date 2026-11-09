# golive_lib.sh — [V12 R4o/ADD4] thu vien CHUNG cho script owner go-live (golive_*.sh). KHONG chay truc tiep.
# [ADD4] C3_ACCOUNT=SUB (MAC DINH: tai khoan CON rieng, key /root/.config/c3live/keys_sub.env) | MAIN (tk chinh keys.env, ADD1 —
#   chi khi chi dinh ro C3_ACCOUNT=MAIN). KEYS_FILE (neu dat) thang moi mac dinh.
# GOLIVE_SCENARIO ADDENDUM 1 (research/vz-e1 90cd2e77). Luat §4.1: DRY=1, YES 1 lan, khung :10-:44, PAUSE token, backup, hau kiem,
# tu rollback, Telegram (token doc tu file, khong in). Khong in key/secret.
# Bien (test): SSH_242 SCP_242 RHOST APP_DIR PROC_PAT NJ_MD5 WD_PAUSE WD_PAUSE_MAX_S POST_WAIT_S POST_ROUNDS MIN_MEM_MB LOGDIR GATE_DIR
#   FORCE_TIME DEPLOY_TG_ENV DEPLOY_TG_SINK SSH_RETRY_S PY242 CURL242 KEYS_FILE C3_ACCOUNT MAIN_KEY_SHA8 SUB_DD_LIMIT SUB_PEAK_FILE
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
NJ_MD5=${NJ_MD5:-694b29b2e5be32b537ca6c38557e64db}   # jar v1.2 dang chay (r4t, ROUND4T; dua len bang swap_v12_dry_jar.sh; truoc: r4q 8c81e6b5)
WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}
WD_PAUSE_MAX_S=${WD_PAUSE_MAX_S:-1800}
POST_WAIT_S=${POST_WAIT_S:-60}
POST_ROUNDS=${POST_ROUNDS:-8}
MIN_MEM_MB=${MIN_MEM_MB:-1000}
DRY=${DRY:-0}
FORCE_TIME=${FORCE_TIME:-0}
SSH_RETRY_S=${SSH_RETRY_S:-10}
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
GATE_DIR=${GATE_DIR:-/home/ubuntu/claude_master/deploy/gates}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
PY242=${PY242:-/opt/c3py/python/bin/python3}
CURL242=${CURL242:-curl}
C3_ACCOUNT=${C3_ACCOUNT:-SUB}
case "$C3_ACCOUNT" in
  SUB)  KEYS_FILE=${KEYS_FILE:-/root/.config/c3live/keys_sub.env} ;;
  MAIN) KEYS_FILE=${KEYS_FILE:-/root/.config/c3live/keys.env} ;;
  *) echo "C3_ACCOUNT='$C3_ACCOUNT' khong hop le (SUB | MAIN)" >&2; exit 1 ;;
esac
MAIN_KEY_SHA8=${MAIN_KEY_SHA8:-3ef771e0}   # sha256(key tk chinh)[:8] — key tk con PHAI khac (ADD4 §2)
SUB_DD_LIMIT=${SUB_DD_LIMIT:-0.40}         # ADD4 §5: A40/C6 -40 % (nguong giu nguyen) — lop ops tren totalMarginBalance tk con
SUB_PEAK_FILE=${SUB_PEAK_FILE:-$LOGDIR/c3sub_tmb_peak.txt}   # dinh tmb tk con (Oracle; golive_monitor ghi; SUB_PEAK_RESET=1 dat lai)
# so/trang thai c3 (doi ten khi doi adapter — so dry/live khong bao gio lan nhau)
GL_STATE_FILES="run/c3live_book.json run/c3live_dry_state.json run/c3live_ledger.csv run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/c3live_killsw_peak run/killsw_latch.json"

gl_init() {   # $1 = ten script
  GL_NAME=$1
  TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
  mkdir -p "$LOGDIR"
  LOG=$LOGDIR/${GL_NAME}_${TS}.log
  exec > >(tee -a "$LOG") 2>&1
  say "=== $GL_NAME TS=$TS DRY=$DRY ==="
}
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
gl_time() {
  [ "$FORCE_TIME" = 1 ] || time_ok || die "gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) khong hop le (phut :10-:44, tranh 07/19h, 00:50-01:20, 12:50-13:20)"
}
gl_yes() {   # $1 = cau hoi; $2 = chuoi phai go (mac dinh YES)
  local want=${2:-YES} ans
  say ">>> $1 Go '$want' de tiep tuc:"
  read -r ans || ans=""
  [ "$ans" = "$want" ] || { say "Huy. Khong doi gi."; exit 0; }
}
# gl_gate <file> : file gate MASTER (khong rong) co dong jar_md5=<NJ_MD5>. In "OK"/"FAIL ..."
gl_gate() {
  local f=$1
  [ -s "$f" ] || { echo "FAIL thieu_file_gate $f"; return 1; }
  grep -qx "jar_md5=$NJ_MD5" "$f" || { echo "FAIL gate_$f khong co dong jar_md5=$NJ_MD5"; return 1; }
  echo "OK gate $f (jar_md5=$NJ_MD5)"
}
gl_gate_val() { sed -n "s/^$2=//p" "$1" | head -1 | tr -d '\r '; }

# gl_state242 : CHI DOC 242 -> dong KEY=VAL (de script kiem o Oracle). Ket thuc END_STATE.
gl_state242() {
  s242in "PP='$PROC_PAT' bash -s -- $A $WD_PAUSE $KEYS_FILE" <<'EOF'
A=$1; PAUSE=$2; KF=$3; cd "$A" || { echo "ERR=cd"; echo END_STATE; exit 0; }
echo "NPROC=$(pgrep -fc "$PP")"
P=$(pgrep -f "$PP" | head -1)
echo "PID=$P"
echo "JAR_MD5=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_PROFILE LIVE_ADAPTER C3_CAPITAL SHADOW_NO_PUSH LIVE_ENTRY_ENABLED LIVE_SEED_EXCLUDE_DECISION_MIN LIVE_KILLSW_MODE GATE_BUFFER_SEED LIVE_C3_KEYS_FILE; do
  echo "ENV_$k=$(echo "$E" | sed -n "s/^$k=//p" | tail -1)"
done
for k in LIVE_ADAPTER C3_CAPITAL LIVE_SEED_EXCLUDE_DECISION_MIN; do
  echo "ENVSH_$k=$(sed -n "s/^export $k=//p" conf/env.sh | tail -1)"
done
L=$(sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' run/killsw_latch.json 2>/dev/null | head -1); echo "LATCH=${L:-NOFILE}"
[ -e "$PAUSE" ] && echo "PAUSE=1 $(head -c 60 "$PAUSE" 2>/dev/null | tr '\n' ' ')" || echo "PAUSE=0"
echo "CANARY_SOAK=$(pgrep -fc 'C3LiveCanary|UserStreamSoak')"
echo "MEM=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
echo "DISK_K=$(df -Pk . | awk 'NR==2{print $4}')"
LL=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1)
echo "LEGACY_N=$(echo "$LL" | grep -aoE 'managed [0-9]+' | awk '{print $2}')"
echo "LEGACY_SYMS=$(echo "$LL" | sed -n 's/.*\[LEGACY\] managed [0-9]*: *//p' | tr -d ' \r')"
echo "LEDGER_SYMS=$(tail -n +2 run/c3live_ledger.csv 2>/dev/null | cut -d, -f1 | sort -u | tr '\n' ',' | sed 's/,$//')"
LT=$(echo "$LL" | awk '{split($1,d,"/"); print d[3]"-"d[2]"-"d[1]" "substr($2,1,8)}')
T=$(TZ=Asia/Ho_Chi_Minh date -d "$LT" +%s 2>/dev/null) && echo "LEGACY_AGE=$(( $(date +%s) - T ))" || echo "LEGACY_AGE=-1"
B=run/c3live_book.json; [ -f $B ] && echo "BOOK_CUM=$(grep -o '"symbol":"' $B | wc -l)" || echo "BOOK_CUM=0"
[ -e run/KILL_SWITCH ] && echo "KILLSW_FILE=1" || echo "KILLSW_FILE=0"
[ -f "$KF" ] && [ "$(stat -c %a "$KF")" = 600 ] && [ "$(grep -c '^C3_LIVE_API_\(KEY\|SECRET\)=' "$KF")" = 2 ] && echo "KEYS_OK=1" || echo "KEYS_OK=0"
echo END_STATE
EOF
}
gl_read_state() {
  ST=$(gl_state242) || die "ssh toi 242 loi"
  echo "$ST" | grep -qx END_STATE || die "doc trang thai 242 khong tron ven (ssh dut?)"
  echo "$ST" | grep -q '^ERR=' && die "doc trang thai 242 loi: $(echo "$ST" | grep '^ERR=')"
}
sv() { echo "$ST" | sed -n "s/^$1=//p" | head -1; }

# ---------------------------------------------------------------- restart co env moi + doi ten trang thai (tuy chon)
# gl_restart "<ENV_ADD>" "<files can doi ten>" <hau to> [ks] ; in RS (dong OK/FAIL, START_LINE=)
#   ks=1 [R4q MAJ-1]: dat run/KILL_SWITCH (token "<ten script> <TS> ", vd "golive_micro_on 20261105_101500 ") TRUOC khi dung bot => JVM moi len KHONG mo lenh moi toi khi
#   script go (sau hau kiem DAT). FAIL truoc khi dung bot => env + KILL_SWITCH cua minh duoc go lai.
gl_restart() {
  local envadd=$1 files=$2 suf=$3 ks=${4:-0} nadd eb
  nadd=$(echo "$envadd" | wc -l); eb=$(echo "$envadd" | base64 -w0)
  PAUSE_TOK="C3GOLIVE_${GL_NAME} TS=$TS pid=$$"
  RS=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $eb $nadd $WD_PAUSE $WD_PAUSE_MAX_S $$ $GL_NAME ${suf:-none} $ks" <<EOF2
A=\$1; TS=\$2; EB=\$3; NADD=\$4; PAUSE=\$5; MAXS=\$6; JP=\$7; NM=\$8; SUF=\$9; KS=\${10:-0}; cd "\$A" || { echo "FAIL cd"; exit 0; }
ksoff() { grep -q "^\${NM} \$TS " run/KILL_SWITCH 2>/dev/null && mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_\$TS; }
\cp -fp conf/env.sh conf/env.sh.bak_\${NM}_\$TS || { echo "FAIL backup_env"; exit 0; }
echo "\$EB" | base64 -d >> conf/env.sh
D=\$(diff conf/env.sh.bak_\${NM}_\$TS conf/env.sh | grep -c '^>')
[ "\$D" = "\$NADD" ] && echo "OK env_them_\${D}_dong" || { \cp -f conf/env.sh.bak_\${NM}_\$TS conf/env.sh; echo "FAIL env_diff=\$D (da khoi phuc)"; exit 0; }
if [ "\$KS" = 1 ]; then
  echo "\${NM} \$TS hau_kiem: dung mo moi toi khi hau kiem DAT" > run/KILL_SWITCH && grep -q "^\${NM} \$TS " run/KILL_SWITCH \
    && echo "OK KILL_SWITCH_dat_truoc_start" || { \cp -f conf/env.sh.bak_\${NM}_\$TS conf/env.sh; echo "FAIL khong_dat_duoc_KILL_SWITCH (env khoi phuc, bot KHONG dung)"; exit 0; }
fi
TOK="C3GOLIVE_\${NM} TS=\$TS pid=\$JP"
mkdir -p "\$(dirname "\$PAUSE")" 2>/dev/null; echo "\$TOK t=\$(date +%s)" > "\$PAUSE" && echo "OK watchdog_PAUSE token='\$TOK'" || echo "WARN khong_tao_duoc_PAUSE"
setsid nohup bash -c "sleep \$MAXS; grep -q '^\$TOK ' '\$PAUSE' 2>/dev/null && rm -f '\$PAUSE'" > /dev/null 2>&1 < /dev/null &
echo "LEGACY_TRUOC_STOP=\$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print \$2}')"   # [R4r] chup NGAY truoc stop
bin/daemon.sh stop
for i in \$(seq 1 30); do pgrep -f "\$PP" >/dev/null || break; sleep 2; done
if pgrep -f "\$PP" >/dev/null; then \cp -f conf/env.sh.bak_\${NM}_\$TS conf/env.sh; ksoff; echo "FAIL van_con_process_sau_stop (env khoi phuc)"; exit 0; fi
echo "OK da_stop"
: > run/.golive_\${NM}_\$TS.moved
if [ "\$SUF" != none ]; then
  for f in $files; do [ -e "\$f" ] && mv -f "\$f" "\$f.\${SUF}_\$TS" && echo "\$f" >> run/.golive_\${NM}_\$TS.moved; done
  echo "OK doi_ten_trang_thai .\${SUF}_\$TS: \$(tr '\n' ' ' < run/.golive_\${NM}_\$TS.moved)"
fi
echo "START_LINE=\$(( \$(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
bin/daemon.sh start
sleep 8
P=\$(pgrep -f "\$PP" | head -1)
[ -n "\$P" ] && echo "OK started pid=\$P lstart=\$(ps -o lstart= -p \$P)" || echo "FAIL khong_thay_process_sau_start"
EOF2
) || RS="FAIL ssh_restart_loi"
  echo "$RS"
  SL=$(echo "$RS" | sed -n 's/^START_LINE=//p'); SL=${SL:-1}
  local lb; lb=$(echo "$RS" | sed -n 's/^LEGACY_TRUOC_STOP=\([0-9][0-9]*\)$/\1/p' | tail -1)   # [R4r] so LEGACY NGAY truoc stop
  if [ -n "$lb" ] && [ -n "${L0:-}" ] && [ "${L0:-}" != SKIP ]; then [ "$lb" != "$L0" ] && say "INFO LEGACY truoc stop=$lb (luc kiem truoc: $L0) => hau kiem so voi $lb"; L0=$lb; fi
}
# gl_rollback <hau to> : stop, env.sh ve ban backup, trang thai doi ten tra lai (ban moi -> .rbnew_TS), start. In RB.
gl_rollback() {
  local suf=${1:-none}
  RB=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $WD_PAUSE $GL_NAME $suf" <<'EOF'
A=$1; TS=$2; PAUSE=$3; NM=$4; SUF=$5; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
[ -f conf/env.sh.bak_${NM}_$TS ] || { echo "FAIL thieu_backup_env"; echo END_RB; exit 0; }
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
\cp -f conf/env.sh.bak_${NM}_$TS conf/env.sh && echo "OK env_khoi_phuc"
grep -q "^${NM} $TS " run/KILL_SWITCH 2>/dev/null && mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_$TS && echo "OK KILL_SWITCH_cua_minh_go"
if [ "$SUF" != none ] && [ -f run/.golive_${NM}_$TS.moved ]; then
  for f in run/c3live_book.json run/c3live_dry_state.json run/c3live_ledger.csv run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/c3live_killsw_peak run/killsw_latch.json; do
    [ -e "$f" ] && mv -f "$f" "$f.rbnew_$TS"
  done
  for f in $(cat run/.golive_${NM}_$TS.moved); do [ -e "$f.${SUF}_$TS" ] && mv -f "$f.${SUF}_$TS" "$f"; done
  echo "OK trang_thai_tra_lai ($(tr '\n' ' ' < run/.golive_${NM}_$TS.moved))"
fi
bin/daemon.sh start; sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "ENV_LIVE_ADAPTER=$(echo "$E" | sed -n 's/^LIVE_ADAPTER=//p' | tail -1) ENV_C3_CAPITAL=$(echo "$E" | sed -n 's/^C3_CAPITAL=//p' | tail -1)"
grep -q "^C3GOLIVE_${NM} TS=$TS " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"
[ -e "$PAUSE" ] && echo "WARN PAUSE_con (token khac)" || echo "OK PAUSE_go"
echo END_RB
EOF
) || RB="FAIL ssh_rollback_loi"
  echo "$RB"
  echo "$RB" | grep -qx END_RB && ! echo "$RB" | grep -q '^FAIL'
}
gl_pause_clear() { s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE; [ ! -e $WD_PAUSE ]"; }
# gl_postloop <ham CHK> : lap POST_ROUNDS lan; RESULT = lan cuoi; tra 0 khi DAT (khong FAIL/WAIT)
gl_postloop() {
  local r
  RESULT=""
  for r in $(seq 1 "$POST_ROUNDS"); do
    sleep "$POST_WAIT_S"
    RESULT=$($1) || RESULT="$RESULT
FAIL kiem_sau_start_ssh"
    echo "$RESULT" | grep -qx END_CHK || RESULT="$RESULT
FAIL kiem_sau_start_khong_tron_ven"
    say "--- hau kiem lan $r/$POST_ROUNDS"; echo "$RESULT"
    echo "$RESULT" | grep -q '^FAIL' && return 1
    echo "$RESULT" | grep -q '^WAIT' || return 0
  done
  return 1
}
# CHK chung sau start: in dong OK/FAIL/WAIT; $1=SL $2=L0 (LEGACY truoc) ; phan rieng them qua $3 (doan bash)
gl_chk_common() {
  s242in "PP='$PROC_PAT' bash -s -- $A $1 ${2:--1}" <<EOF3
A=\$1; SL=\$2; L0=\$3; cd "\$A"; L=logs/full.log
T() { tail -n +\$SL \$L 2>/dev/null | grep -a -c "\$1"; }
P=\$(pgrep -f "\$PP" | head -1)
[ "\$(pgrep -fc "\$PP")" = 1 ] && echo "OK 1_process" || echo "FAIL so_process"
E=\$(tr '\0' '\n' < /proc/\$P/environ 2>/dev/null)
envk() { echo "\$E" | grep -qx "\$1" && echo "OK env \$1" || echo "FAIL env \$1 (co: \$(echo "\$E" | grep "^\${1%%=*}=" | tail -1))"; }
[ "\$(T 'KHONG tao duoc runtime')" = 0 ] && echo "OK runtime" || echo "FAIL KHONG_tao_duoc_runtime"
[ "\$(T '\[KILLSW\] LATCH')" = 0 ] || echo "FAIL KILLSW_LATCH"
LT=\$(sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' run/killsw_latch.json 2>/dev/null | head -1)
[ -z "\$LT" ] || [ "\$LT" = NONE ] && echo "OK latch_\${LT:-chua_co_file}" || echo "FAIL latch=\$LT"
K=\$(tail -n +\$SL \$L 2>/dev/null | grep -a 'KHAN' | grep -av 'DRY tren tai khoan chinh' | head -1 | cut -c1-160)
[ -z "\$K" ] && echo "OK 0_KHAN" || echo "FAIL KHAN: \$K"
[ "\$(T 'RECON\] khoi dong: ok=true')" -ge 1 ] && echo "OK recon_khoi_dong" || echo "WAIT recon_khoi_dong"
[ "\$(T 'RECON\] khoi dong: ok=false')" = 0 ] || echo "FAIL recon_khoi_dong_ok=false"
LN=\$(tail -n +\$SL \$L 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print \$2}')
if [ "\$L0" = SKIP ]; then echo "INFO LEGACY_managed=\${LN:-chua_co} (ADD4 tk con: LEGACY o tk chinh, chi ghi log)"; elif [ -z "\$LN" ]; then echo "WAIT LEGACY_chua_co"; elif [ "\$L0" = -1 ] || [ "\$LN" = "\$L0" ]; then echo "OK LEGACY_managed=\$LN"; elif [ "\$LN" -lt "\$L0" ] 2>/dev/null; then echo "WARN LEGACY_managed=\$LN < truoc stop \$L0 (dong tu nhien luc dung? kiem tay)"; else echo "FAIL LEGACY_managed=\$LN > truoc stop \$L0 (TANG)"; fi
B=run/c3live_book.json; echo "INFO BOOK_CUM=\$([ -f \$B ] && grep -o '"symbol":"' \$B | wc -l || echo 0) AUDIT_C3=\$(tail -n +\$SL \$L 2>/dev/null | grep -a '\[C3-LIVE-ORDER\]' | grep -avc 'status=SKIP')"
$3
echo END_CHK
EOF3
}

# ---------------------------------------------------------------- goi API CHI DOC tu 242 bang key c3 (python /opt/c3py + curl)
# gl_api242 restrictions|scope|sub : in KEY=VAL + END_API. Key/secret CHI nam trong process python tren 242 (khong argv, khong in);
# curl nhan url + header qua stdin (-K -). scope: positionRisk v3 + openOrders + openAlgoOrders, so voi cum trong so c3 (doc so 2 lan:
#   truoc + sau positionRisk; symbol co leg chua xac dinh / so doi giua 2 lan => POS_PENDING, khong tinh NGOAI c3).
# [ADD4] sub = restrictions + GET /fapi/v3/account (tmb, so du, marginAvailable; v3 thieu truong => them /fapi/v2/account)
#   + multiAssetsMargin + positionSide/dual + scope. W_NOMINAL = weight fapi danh nghia, W_USED_1M = header X-MBX-USED-WEIGHT-1M cuoi
#   (weight IP dung chung LEGACY). cid c3 = c3- | c3x- | c3s- (ADD4 §4).
gl_api242() {
  s242in "bash -s -- $A $1 $KEYS_FILE $PY242 $CURL242" <<'EOF'
A=$1; MODE=$2; KF=$3; PY=$4; CU=$5; cd "$A" 2>/dev/null || { echo "ERR=cd"; echo END_API; exit 0; }
[ -x "$PY" ] || { echo "ERR=thieu_python_$PY"; echo END_API; exit 0; }
"$PY" -I - "$MODE" "$KF" "$CU" run/c3live_book.json <<'PYEOF'
import hashlib, hmac, json, subprocess, sys, time
from decimal import Decimal as Dd
mode, kf, cu, bookf = sys.argv[1:5]
FAPI = 'https://fapi.binance.com'
CIDOK = ('c3-', 'c3x-', 'c3s-')
k = s = None
try:
    for ln in open(kf, encoding='utf-8'):
        ln = ln.strip()
        if ln.startswith('C3_LIVE_API_KEY='): k = ln.split('=', 1)[1].strip().strip('"')
        if ln.startswith('C3_LIVE_API_SECRET='): s = ln.split('=', 1)[1].strip().strip('"')
except Exception as e:
    print('ERR=doc_keys_loi_' + type(e).__name__); print('END_API'); sys.exit(0)
if not k or not s:
    print('ERR=keys_thieu_dong'); print('END_API'); sys.exit(0)
print('KEY_SHA8=' + hashlib.sha256(k.encode()).hexdigest()[:8])
W = {'n': 0, 'used': ''}
def call(base, path, w=0):
    q = 'timestamp=%d&recvWindow=10000' % int(time.time() * 1000)
    sig = hmac.new(s.encode(), q.encode(), hashlib.sha256).hexdigest()
    cfg = 'url = "%s%s?%s&signature=%s"\nheader = "X-MBX-APIKEY: %s"\n' % (base, path, q, sig, k)
    r = subprocess.run([cu, '-s', '-m', '15', '-D', '/dev/stderr', '-w', '\nHTTP=%{http_code}', '-K', '-'], input=cfg.encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    W['n'] += w
    for hl in r.stderr.decode('utf-8', 'replace').splitlines():
        if hl.lower().startswith('x-mbx-used-weight-1m:'): W['used'] = hl.split(':', 1)[1].strip()
    out = r.stdout.decode('utf-8', 'replace')
    body, _, code = out.rpartition('\nHTTP=')
    try:
        return code.strip(), json.loads(body)
    except Exception:
        return code.strip(), None
def b(v): return str(v).lower()
def fq(d): return format(d.normalize(), 'f')   # 10 -> '10' (khong '1E+1')
def num(v):
    try: return Dd(str(v))
    except Exception: return None
def readbook():
    # [R4q MAJ-2] c3 = qty MO tung symbol tu CUM MO cua so (adj_qty | sum exec_qty leg CONFIRMED) - exit_qty
    c3 = {}; unres = set()
    try:
        bk = json.load(open(bookf, encoding='utf-8'))
    except FileNotFoundError:
        return c3, unres
    for c in (bk.get('clusters') or []) if isinstance(bk, dict) else []:
        if not isinstance(c, dict) or not isinstance(c.get('symbol'), str): continue
        sym = c['symbol']
        if c.get('adj_qty') not in (None, ''):
            q = Dd(str(c['adj_qty']))
        else:
            q = Dd(0)
            for l in c.get('legs') or []:
                if not isinstance(l, dict): continue
                st = l.get('state')
                if st == 'CONFIRMED': q += Dd(str(l.get('exec_qty') or '0'))
                elif st in ('SENDING', 'UNKNOWN'): unres.add(sym)
        q -= Dd(str(c.get('exit_qty') or '0'))
        c3[sym] = c3.get(sym, Dd(0)) + q
    return c3, unres
ok = True
if mode in ('restrictions', 'sub'):
    code, j = call('https://api.binance.com', '/sapi/v1/account/apiRestrictions')
    print('HTTP=' + code)
    if isinstance(j, dict) and code == '200':
        for f in ('ipRestrict', 'enableWithdrawals', 'enableFutures', 'enableReading', 'enableInternalTransfer',
                  'permitsUniversalTransfer', 'enableSpotAndMarginTrading', 'enableMargin', 'enableVanillaOptions'):
            if f in j: print('%s=%s' % (f, str(j[f]).lower()))
    elif isinstance(j, dict):
        print('API_ERR=%s %s' % (j.get('code'), str(j.get('msg'))[:80]))
if mode == 'sub':
    code, ac = call(FAPI, '/fapi/v3/account', 5)
    print('ACC_HTTP=' + code)
    if code != '200' or not isinstance(ac, dict):
        ok = False; print('ERR_ACC=HTTP%s' % code)
    else:
        print('TMB=%s' % ac.get('totalMarginBalance')); print('AVAIL=%s' % ac.get('availableBalance'))
        assets = [a for a in (ac.get('assets') or []) if isinstance(a, dict) and isinstance(a.get('asset'), str)]
        mav = {a['asset']: a['marginAvailable'] for a in assets if 'marginAvailable' in a}
        if any('marginAvailable' not in a for a in assets):
            c2, a2 = call(FAPI, '/fapi/v2/account', 5)
            print('ACC_V2_HTTP=' + c2)
            if c2 == '200' and isinstance(a2, dict):
                for a in a2.get('assets') or []:
                    if isinstance(a, dict) and isinstance(a.get('asset'), str) and 'marginAvailable' in a:
                        mav.setdefault(a['asset'], a['marginAvailable'])
        bal = []
        for a in assets:
            wb = num(a.get('walletBalance'))
            if wb is not None and wb != 0:
                bal.append('%s:%s:mb=%s:ma=%s' % (a['asset'], a.get('walletBalance'), a.get('marginBalance'), b(mav.get(a['asset'], '?'))))
        print('BAL=' + ','.join(bal[:20]))
        print('MARGIN_ASSETS=' + ','.join(sorted(x for x, v in mav.items() if b(v) == 'true')[:40]))
        bf = next((a for a in assets if a['asset'] == 'BFUSD'), None)
        bw = num(bf.get('walletBalance')) if bf else Dd(0)
        print('BFUSD_WALLET=%s' % ('?' if bw is None else ('0' if bw == 0 else str(bw))))
        print('BFUSD_MARGIN=%s' % (b(mav['BFUSD']) if 'BFUSD' in mav else 'unknown'))
    code, j = call(FAPI, '/fapi/v1/multiAssetsMargin', 30)
    if code == '200' and isinstance(j, dict) and 'multiAssetsMargin' in j: print('MULTI=' + b(j['multiAssetsMargin']))
    else: ok = False; print('ERR_MULTI=HTTP%s' % code)
    code, j = call(FAPI, '/fapi/v1/positionSide/dual', 30)
    if code == '200' and isinstance(j, dict) and 'dualSidePosition' in j: print('DUAL=' + b(j['dualSidePosition']))
    else: ok = False; print('ERR_DUAL=HTTP%s' % code)
if mode in ('scope', 'sub'):
    # vi the san vuot qty c3 => phan vuot = NGOAI c3 (LEGACY con sot / vi the la tren tk con). c3 > san => lech so.
    try:
        c3a, ua = readbook()
    except Exception as e:
        print('ERR=book_hong_' + type(e).__name__); print('END_API'); sys.exit(0)
    code, pr = call(FAPI, '/fapi/v3/positionRisk', 5)
    try:
        c3b, ub = readbook()
    except Exception as e:
        print('ERR=book_hong_' + type(e).__name__); print('END_API'); sys.exit(0)
    unres = ua | ub
    for sy in set(c3a) | set(c3b):
        if c3a.get(sy) != c3b.get(sy): unres.add(sy)
    c3 = {sy: max(c3a.get(sy, Dd(0)), c3b.get(sy, Dd(0))) for sy in set(c3a) | set(c3b)}
    print('C3_BOOK_SYMBOLS=%d' % len(c3))
    print('C3_UNRESOLVED=%d %s' % (len(unres), ','.join(sorted(unres)[:8])))
    if code != '200' or not isinstance(pr, list): ok = False; print('ERR_POS=HTTP%s' % code)
    else:
        pos = {}
        for p in pr:
            a = Dd(str(p.get('positionAmt') or '0'))
            if a != 0: pos[p['symbol']] = pos.get(p['symbol'], Dd(0)) + a
        non = []; mism = []; pend = []
        for sy, a in sorted(pos.items()):
            if a < 0: non.append('%s:%s' % (sy, a)); continue   # c3 chi long
            r = a - c3.get(sy, Dd(0))
            if r > 0: (pend if sy in unres else non).append('%s:+%s' % (sy, fq(r)))
            elif r < 0: mism.append('%s:%s' % (sy, fq(r)))
        for sy, m in sorted(c3.items()):
            if m > 0 and sy not in pos: mism.append('%s:-%s' % (sy, fq(m)))
        print('POS_TOTAL=%d' % len(pos)); print('POS_NONC3=%d %s' % (len(non), ','.join(non[:8])))
        print('POS_PENDING=%d %s' % (len(pend), ','.join(pend[:8])))
        print('POS_C3_MISMATCH=%d %s' % (len(mism), ','.join(mism[:8])))
        print('POS_LIST=' + ','.join(sorted(pos)))
        print('POS_SIG=' + hashlib.sha256(';'.join('%s=%s' % (sy, a.normalize()) for sy, a in sorted(pos.items())).encode()).hexdigest()[:16])
    code, oo = call(FAPI, '/fapi/v1/openOrders', 40)
    if code != '200' or not isinstance(oo, list): ok = False; print('ERR_ORD=HTTP%s' % code)
    else:
        non = [o.get('symbol') for o in oo if not str(o.get('clientOrderId', '')).startswith(CIDOK)]
        print('ORD_TOTAL=%d' % len(oo)); print('ORD_NONC3=%d %s' % (len(non), ','.join(non[:8])))
        print('ORD_C3=%d' % (len(oo) - len(non)))
    code, ao = call(FAPI, '/fapi/v1/openAlgoOrders', 40)
    if isinstance(ao, dict): ao = ao.get('orders', ao.get('rows', []))
    if code != '200' or not isinstance(ao, list): ok = False; print('ERR_ALGO=HTTP%s' % code)
    else:
        non = [o.get('symbol') for o in ao if not str(o.get('clientAlgoId', '')).startswith(CIDOK)]
        print('ALGO_TOTAL=%d' % len(ao)); print('ALGO_NONC3=%d %s' % (len(non), ','.join(non[:8])))
        print('ALGO_C3=%d' % (len(ao) - len(non)))
    print('API_OK=%d' % (1 if ok else 0))
if mode == 'sub':
    print('W_NOMINAL=%d' % W['n']); print('W_USED_1M=%s' % (W['used'] or '?'))
k = s = None
print('END_API')
PYEOF
EOF
}
av() { echo "$API" | sed -n "s/^$1=//p" | head -1; }

# gl_sub_eval <can_sach 1|0> : [ADD4 §2] danh gia $API (gl_api242 sub) => SUBV=DAT|TRUOT, SUBWHY (ly do). can_sach=1: them 0 vi the,
#   0 lenh mo, 0 algo (luc micro_on). multiAssetsMargin CHI ghi lai (jar r4t: AccountModeGuard.globalPolicy(false,false) khong doi hoi).
gl_sub_eval() {
  local n x
  SUBV=DAT; SUBWHY=""
  _sf() { SUBV=TRUOT; SUBWHY="$SUBWHY $1"; }
  echo "$API" | grep -qx END_API || _sf "goi_API_khong_tron_ven"
  echo "$API" | grep -q '^ERR' && _sf "$(echo "$API" | grep '^ERR' | head -3 | tr '\n' ' ' | sed 's/ $//')"
  [ "$(av HTTP)" = 200 ] || _sf "apiRestrictions_HTTP=$(av HTTP)$(x=$(av API_ERR); [ -n "$x" ] && echo "($x)")"
  [ "$(av ipRestrict)" = true ] || _sf "ipRestrict=$(av ipRestrict)"
  [ "$(av enableWithdrawals)" = false ] || _sf "enableWithdrawals=$(av enableWithdrawals)"
  [ "$(av enableFutures)" = true ] || _sf "enableFutures=$(av enableFutures)"
  x=$(av KEY_SHA8); { [ -n "$x" ] && [ "$x" != "$MAIN_KEY_SHA8" ]; } || _sf "key_sha8=${x:-?}_TRUNG_key_tk_chinh_hoac_thieu"
  [ "$(av DUAL)" = false ] || _sf "dualSidePosition=$(av DUAL)"
  [ "$(av API_OK)" = 1 ] || _sf "doc_san_loi"
  x=$(av BFUSD_WALLET)
  if [ "$x" = '?' ]; then _sf "BFUSD_walletBalance_khong_doc_duoc"
  elif [ -n "$x" ] && [ "$x" != 0 ]; then [ "$(av BFUSD_MARGIN)" = true ] || _sf "BFUSD=${x}_marginAvailable=$(av BFUSD_MARGIN)"; fi
  if [ "${1:-1}" = 1 ]; then
    for n in POS_TOTAL ORD_TOTAL ALGO_TOTAL; do x=$(av $n); [ "$x" = 0 ] || _sf "$n=${x:-?}"; done
  fi
  return 0
}

# gl_c3_seen <SL> <POS_SIG truoc restart> : [R4q MAJ-1] doc LAI 242 NGAY luc quyet (so + audit lenh c3 + san qua duong chi doc).
#   In dong + "VERDICT=NONE" CHI khi MOI nguon doc duoc tron ven va: so 0 cum, 0 dong [C3-LIVE-ORDER] (tru SKIP) tu START_LINE
#   (log chua xoay), san 0 lenh/algo c3, chu ky vi the = truoc restart. Thieu/khong chac => UNKNOWN (coi nhu DA co lenh); co => SEEN.
gl_c3_seen() {
  local R why="" unk=""
  R=$(s242in "bash -s -- $A $1" <<'EOF'
A=$1; SL=$2; cd "$A" || { echo "ERR=cd"; echo END_SEEN; exit 0; }
L=logs/full.log; N=$(wc -l < $L 2>/dev/null || echo 0)
[ "$N" -ge "$SL" ] && echo "LOG_OK=1" || echo "LOG_OK=0"
echo "AUDIT_C3=$(tail -n +$SL $L 2>/dev/null | grep -a '\[C3-LIVE-ORDER\]' | grep -avc 'status=SKIP')"
B=run/c3live_book.json
if [ ! -e $B ]; then echo "BOOK_CUM=0"; elif [ -r $B ]; then echo "BOOK_CUM=$(grep -o '"symbol":"' $B | wc -l)"; else echo "ERR=book_khong_doc_duoc"; fi
echo END_SEEN
EOF
) || R="ERR=ssh_doc_242"
  echo "$R" | grep -v '^END_SEEN$'
  API=$(gl_api242 scope) || API="ERR=ssh_api"
  echo "$API" | grep -E '^(API_OK|ORD_C3|ALGO_C3|POS_SIG|POS_TOTAL|ERR)'
  echo "$R" | grep -qx END_SEEN || unk="$unk doc_242_khong_tron_ven"
  echo "$R" | grep -q '^ERR=' && unk="$unk $(echo "$R" | grep '^ERR=' | head -1)"
  echo "$R" | grep -qx 'LOG_OK=1' || unk="$unk log_xoay_hoac_mat"
  echo "$API" | grep -qx END_API && ! echo "$API" | grep -q '^ERR' && [ "$(av API_OK)" = 1 ] || unk="$unk doc_san_loi"
  [ -n "$2" ] || unk="$unk thieu_chu_ky_vi_the_truoc"
  local au bc
  au=$(echo "$R" | sed -n 's/^AUDIT_C3=//p'); bc=$(echo "$R" | sed -n 's/^BOOK_CUM=//p')
  [ "${au:-x}" = 0 ] || why="$why audit_lenh_c3=${au:-?}"
  [ "${bc:-x}" = 0 ] || why="$why so_c3_cum=${bc:-?}"
  [ "$(av ORD_C3)" = 0 ] || why="$why san_lenh_c3=$(av ORD_C3)"
  [ "$(av ALGO_C3)" = 0 ] || why="$why san_algo_c3=$(av ALGO_C3)"
  [ "$(av POS_SIG)" = "$2" ] || why="$why vi_the_san_doi(truoc=$2 nay=$(av POS_SIG))"
  if [ -n "$unk" ]; then echo "VERDICT=UNKNOWN${unk}${why}"
  elif [ -n "$why" ]; then echo "VERDICT=SEEN${why}"
  else echo "VERDICT=NONE"; fi
}
