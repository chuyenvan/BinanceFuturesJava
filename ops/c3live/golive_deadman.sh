#!/usr/bin/env bash
# =============================================================================
# golive_deadman.sh - [OPS5 muc 2a] DEAD-MAN doc lap cho giam sat (Oracle). KHONG source golive_lib.sh (lib loi khong keo theo).
#   cron rieng */2 (install_golive_deadman.sh, ban GHIM ~/claude_master/deploy/pinned/golive_deadman_<md5_12>/), flock -n + timeout 90.
#   DRY=1: chi in, KHONG Telegram, KHONG ghi state/heartbeat.
# Kiem (moi loai canh bao toi da 1 lan / DM_REMIND_S (1800 s) + tin "DA HOI PHUC" khi het):
#   mon_hb   heartbeat cron golive_monitor ($MON_HB_FILE) cu > DM_HB_MAX_S (600) - CHI khi co micro/pilot ($GL_MON_FLAG) [monitor chi chay khi co co]
#   ssh242   ssh 242 (CHI DOC) loi >= DM_SSH_FAIL_N (2) luot lien tiep
#   gate     dong "[GATE] " moi nhat log bot cu > DM_GATE_MAX_S (180 s) (bot treo / chet) hoac khong thay
#            [OPS5_FIX MINOR 2a] BO QUA khi PAUSE watchdog 242 ($DM_WD_PAUSE) con han (tuoi <= DM_PAUSE_MAX_S = WD_PAUSE_MAX_S 1800) - cung co che
#            monitor dung (moi script golive/deploy/rollback dat PAUSE truoc stop/start) => khong bao gia trong cua so deploy / restart co chu dich.
#   watcher  tien trinh parity watcher ($DM_WATCH_PAT) khong chay
#   disk     dia $DM_DF_PATH Oracle trong < DM_DISK_MIN_GB (10)
#   mem      MemAvailable Oracle < DM_MEM_MIN_MB (2000)
# 242 thay Oracle con song qua dong sshd "Accepted publickey ... from <Oracle>" do CHINH luot doc nay tao (xem c3_oracle_seen_242.sh, muc 2b).
# Ghi: $DM_DIR/state (khoa canh bao), $DM_DIR/heartbeat, $DM_DIR/deadman.log. Ma thoat 0 | 2 co canh bao dang mo.
# =============================================================================
set -uo pipefail
if [ -z "${_DM_MASKED:-}" ]; then export _DM_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
DRY=${DRY:-0}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
DM_DIR=${DM_DIR:-$LOGDIR/deadman}
MON_HB_FILE=${MON_HB_FILE:-$LOGDIR/run/monitor_heartbeat}
GL_MON_FLAG=${GL_MON_FLAG:-$LOGDIR/golive_monitor.on}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
APP_DIR=${APP_DIR:-/home/chuyennd/java/v_t_m}
DM_TAIL=${DM_TAIL:-2000000}
DM_SSH_TIMEOUT_S=${DM_SSH_TIMEOUT_S:-30}
DM_HB_MAX_S=${DM_HB_MAX_S:-600}
DM_GATE_MAX_S=${DM_GATE_MAX_S:-180}
DM_SSH_FAIL_N=${DM_SSH_FAIL_N:-2}
DM_WATCH_PAT=${DM_WATCH_PAT:-watch_daily_v12.sh}
DM_DF_PATH=${DM_DF_PATH:-/}
DM_DISK_MIN_GB=${DM_DISK_MIN_GB:-10}
DM_MEM_MIN_MB=${DM_MEM_MIN_MB:-2000}
DM_MEMINFO=${DM_MEMINFO:-/proc/meminfo}
DM_REMIND_S=${DM_REMIND_S:-1800}
DM_WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}; DM_PAUSE_MAX_S=${WD_PAUSE_MAX_S:-1800}
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
NOW=$(date +%s); TS=$(TZ=Asia/Ho_Chi_Minh date '+%F %T')
say() { echo "[$TS] $*"; }
mkdir -p "$DM_DIR" 2>/dev/null
if [ "$DRY" != 1 ]; then
  LF=$DM_DIR/deadman.log; [ "$(stat -c %s "$LF" 2>/dev/null || echo 0)" -gt 5000000 ] && mv -f "$LF" "$LF.1"
  exec > >(tee -a "$LF") 2>&1
fi
tgs() {   # gui Telegram (token/chat doc tu file, KHONG in); DEPLOY_TG_SINK (test) => ghi file
  local msg tok chat code
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/[CHE]/g' | head -c 3000)
  if [ "$DRY" = 1 ]; then say "DRY=1 (khong gui): $msg"; return 0; fi
  if [ -n "${DEPLOY_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$DEPLOY_TG_SINK"; return 0; fi
  [ -r "$DEPLOY_TG_ENV" ] || { say "!! khong doc duoc file Telegram - KHONG gui"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || { say "!! file Telegram thieu token/chat"; return 1; }
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 10 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null); tok=""; chat=""
  [ "$code" = 200 ] || { say "!! Telegram http=$code"; return 1; }
}
SF=$DM_DIR/state
declare -A ST_T ST_S
if [ -r "$SF" ]; then while IFS='=' read -r k v; do case "$k" in t_*) ST_T[${k#t_}]=${v//[^0-9]/};; s_*) ST_S[${k#s_}]=${v//[^0-9]/};; esac; done < "$SF"; fi
SSHF=$(sed -n 's/^sshfail=//p' "$SF" 2>/dev/null | head -1); [[ "$SSHF" =~ ^[0-9]+$ ]] || SSHF=0
declare -A AL
# ---- mon_hb
if [ -f "$GL_MON_FLAG" ]; then
  m=$(stat -c %Y "$MON_HB_FILE" 2>/dev/null || echo 0); a=$(( NOW - m ))
  if [ "$a" -gt "$DM_HB_MAX_S" ]; then AL[mon_hb]="heartbeat golive_monitor cu ${a}s > ${DM_HB_MAX_S}s (cron monitor chet/treo?) - kiem crontab + $LOGDIR/golive_monitor_cron.log"
  else say "OK mon_hb tuoi ${a}s"; fi
else say "INFO khong co co micro/pilot ($GL_MON_FLAG) - bo qua mon_hb (monitor cron khong chay)"; fi
# ---- ssh242 + gate (1 ssh CHI DOC)
G=$(timeout -k 5 "$DM_SSH_TIMEOUT_S" $SSH_242 "cd $APP_DIR && nice -n 19 tail -c $DM_TAIL logs/full.log 2>/dev/null | grep -a '\[GATE\] ' | tail -1 | cut -c1-23; [ -e $DM_WD_PAUSE ] && echo PAUSE_AGE=\$(( \$(date +%s) - \$(stat -c %Y $DM_WD_PAUSE 2>/dev/null || echo 0) )); echo END_DM" < /dev/null 2>/dev/null); rc=$?
if [ "$rc" != 0 ] || ! printf '%s\n' "$G" | grep -qx END_DM; then
  SSHF=$((SSHF + 1)); say "!! ssh 242 loi rc=$rc (luot loi lien tiep $SSHF/$DM_SSH_FAIL_N)"
  [ "$SSHF" -ge "$DM_SSH_FAIL_N" ] && AL[ssh242]="ssh 242 (chi doc) loi $SSHF luot lien tiep (rc=$rc) - 242 mat mang / sshd / Oracle mat mang?"
else
  SSHF=0; say "OK ssh242"
  GL=$(printf '%s\n' "$G" | grep -v '^END_DM$' | grep -v '^PAUSE_AGE=' | tail -1)
  PA=$(printf '%s\n' "$G" | sed -n 's/^PAUSE_AGE=//p' | head -1)
  if [[ "$PA" =~ ^[0-9]+$ ]] && [ "$PA" -le "$DM_PAUSE_MAX_S" ]; then say "INFO PAUSE watchdog 242 con han (${PA}s <= ${DM_PAUSE_MAX_S}s: deploy / restart co chu dich) - BO QUA kiem gate"
  elif [[ "$GL" =~ ^([0-9]{2})/([0-9]{2})/([0-9]{4})\ ([0-9:]{8}) ]]; then
    gt=$(TZ=Asia/Ho_Chi_Minh date -d "${BASH_REMATCH[3]}-${BASH_REMATCH[2]}-${BASH_REMATCH[1]} ${BASH_REMATCH[4]}" +%s 2>/dev/null || echo 0); ga=$(( NOW - gt ))
    if [ "$ga" -gt "$DM_GATE_MAX_S" ]; then AL[gate]="dong [GATE] moi nhat cu ${ga}s > ${DM_GATE_MAX_S}s ($GL) - bot treo / chet / dang khoi dong lai?"
    else say "OK gate tuoi ${ga}s"; fi
  else AL[gate]="khong thay dong [GATE] trong ${DM_TAIL} byte cuoi log bot - bot treo / chet?"; fi
fi
# ---- watcher parity
WP="[${DM_WATCH_PAT:0:1}]${DM_WATCH_PAT:1}"
NW=$(pgrep -fc -- "$WP" 2>/dev/null); if [ "${NW:-0}" -ge 1 ] 2>/dev/null; then say "OK watcher ($DM_WATCH_PAT)"; else AL[watcher]="watcher parity ($DM_WATCH_PAT) KHONG chay - nhan ngay khong ra"; fi
# ---- disk / mem Oracle
dk=$(df -Pk "$DM_DF_PATH" 2>/dev/null | awk 'NR==2{print int($4/1048576)}'); dk=${dk:-0}
[ "$dk" -lt "$DM_DISK_MIN_GB" ] && AL[disk]="dia Oracle $DM_DF_PATH con ${dk} GB < ${DM_DISK_MIN_GB} GB" || say "OK disk ${dk} GB"
mm=$(awk '/^MemAvailable:/{print int($2/1024)}' "$DM_MEMINFO" 2>/dev/null); mm=${mm:-0}
[ "$mm" -lt "$DM_MEM_MIN_MB" ] && AL[mem]="RAM Oracle available ${mm} MB < ${DM_MEM_MIN_MB} MB" || say "OK mem ${mm} MB"
# ---- chong spam + hoi phuc
RC=0
for k in mon_hb ssh242 gate watcher disk mem; do
  if [ -n "${AL[$k]:-}" ]; then
    RC=2; say "CANH BAO $k: ${AL[$k]}"
    if [ -z "${ST_T[$k]:-}" ]; then ST_T[$k]=$NOW; fi
    if [ $(( NOW - ${ST_S[$k]:-0} )) -ge "$DM_REMIND_S" ]; then
      tgs "[deadman Oracle] CANH BAO $k (tu $(TZ=Asia/Ho_Chi_Minh date -d @"${ST_T[$k]}" '+%d/%m %H:%M')): ${AL[$k]}" && ST_S[$k]=$NOW
    else say "($k da bao < ${DM_REMIND_S}s truoc - khong gui lai)"; fi
  elif [ -n "${ST_T[$k]:-}" ]; then
    tgs "[deadman Oracle] DA HOI PHUC $k (canh bao tu $(TZ=Asia/Ho_Chi_Minh date -d @"${ST_T[$k]}" '+%d/%m %H:%M'), $(( (NOW - ${ST_T[$k]}) / 60 )) phut)" && { unset 'ST_T[$k]'; unset 'ST_S[$k]'; }
  fi
done
if [ "$DRY" != 1 ]; then
  { echo "sshfail=$SSHF"; for k in "${!ST_T[@]}"; do echo "t_$k=${ST_T[$k]}"; echo "s_$k=${ST_S[$k]:-0}"; done; } > "$SF.tmp" && mv -f "$SF.tmp" "$SF"
  printf 'ts=%s rc=%s\n' "$NOW" "$RC" > "$DM_DIR/heartbeat.tmp" && mv -f "$DM_DIR/heartbeat.tmp" "$DM_DIR/heartbeat"
fi
say "TOM TAT deadman rc=$RC canh_bao=[${!AL[*]}]"
exit $RC
