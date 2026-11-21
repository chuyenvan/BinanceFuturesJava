# golive_lib.sh — [V12 R4o/ADD4] thu vien CHUNG cho script owner go-live (golive_*.sh). KHONG chay truc tiep.
# [ADD4] C3_ACCOUNT=SUB (MAC DINH: tai khoan CON rieng, key /root/.config/c3live/keys_sub.env) | MAIN (tk chinh keys.env, ADD1 —
#   chi khi chi dinh ro C3_ACCOUNT=MAIN). KEYS_FILE (neu dat) thang moi mac dinh.
# GOLIVE_SCENARIO ADDENDUM 1 (research/vz-e1 90cd2e77). Luat §4.1: DRY=1, YES 1 lan, khung :10-:44, PAUSE token, backup, hau kiem,
# tu rollback, Telegram (token doc tu file, khong in). Khong in key/secret.
# Bien (test): SSH_242 SCP_242 RHOST APP_DIR PROC_PAT NJ_MD5 WD_PAUSE WD_PAUSE_MAX_S POST_WAIT_S POST_ROUNDS MIN_MEM_MB LOGDIR GATE_DIR
#   FORCE_TIME DEPLOY_TG_ENV DEPLOY_TG_SINK SSH_RETRY_S PY242 CURL242 KEYS_FILE C3_ACCOUNT MAIN_KEY_SHA8 SUB_DD_LIMIT SUB_PEAK_FILE
# [WAVE1 B-10] ServerAlive: ket noi nua mo (NAT rot) => ssh tu thoat <= ~60 s thay vi treo vo han
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
NJ_MD5=${NJ_MD5:-01cfbb4324fb4a10b615dc3c976ddc73}   # [OPS6 T4] jar v1.2 DANG chay = r4u3fin2 + hotfix-ks (KillSwitchEngine 4fdda6f8, golive_swap_jar.sh 20/11); truoc: r4u3fin2 64180356 (WAVE1 B-01), r4u3 b1f12c3e, r4t 694b29b2
#   [OPS6 T4] jar CU r4u3fin2 64180356 con o: golive_swap_jar.sh SJ_OLD_MD5 (MODE=rollback ve jar cu - sau rollback jar != NJ_MD5 => micro_on/pilot_on/
#   make_gate_pilot TU CHOI, dung thiet ke), rollback_vtm_r4u3.sh FROM_MD5 + swap_v12_dry_jar.sh (CHI khi v_t_m DRY - khong dung cho live).
RB_JAR_MD5=${RB_JAR_MD5:-b1f12c3eeaeed72cb17afbe5b4da06cf}   # [WAVE1 B-01] dich rollback v_t_m DRY = r4u3 (rollback_vtm_r4u3.sh). [OPS6] KHONG script live nao dung bien nay
ING_FIN_MD5=${ING_FIN_MD5:-5e78ac0663b4a765551eac1c362bf194}   # [WAVE1 B-08] jar ingestor FIN dang chay (gate micro + kiem truoc)
ING_PAT=${ING_PAT:-websocket.BinanceDataIngestor}
SUB_KEY_SHA8=${SUB_KEY_SHA8:-43820b5b}   # [WAVE1 A-03] sha256(key tk con)[:8] da dang ky (KEY_CHECK_SUB 11-09) — key doc san PHAI = gia tri nay
GATE_MAX_AGE_S=${GATE_MAX_AGE_S:-172800}  # [WAVE1 B-08] gate G-MICRO het han 48 h
GL_GATE_FIELDS="gmicro_i gmicro_ii smoke replay_iii sizing_iv script_v"   # [WAVE1b M4] truong ADD22 §3 bat buoc trong gate G-MICRO (khong doi qua env)
GL_SSH_TRIES=${GL_SSH_TRIES:-3}            # [WAVE1 B-05] so lan thu ssh CHI DOC (cron monitor: 1)
GL_SSH_TIMEOUT_S=${GL_SSH_TIMEOUT_S:-0}    # [WAVE1 B-05] >0 => moi lenh ssh boc timeout (cron monitor: 25 s)
RB_LOG_WAIT_S=${RB_LOG_WAIT_S:-180}        # [WAVE1 B-02] rollback: cho dong "khoi dong adapter=" cua JVM moi toi da (s)
RB_LOG_POLL_S=${RB_LOG_POLL_S:-5}
MIN_LEG_BUDGET=${MIN_LEG_BUDGET:-5}        # [WAVE1 D-01] = C3LiveEntry minBudget 5 (C3LiveEntry:265) va min notional pho bien (516 coin)
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
GL_HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# [WAVE1b M5] manifest md5 da commit (GOLIVE_MANIFEST.md5 canh lib, dinh dang md5sum): script owner goi gl_manifest_check "$0" NGAY sau
#   khi source lib (truoc gl_init / doc 242 / ghi gi) — script + lib + moi file trong manifest phai khop md5; lech / thieu => TU CHOI exit 1.
#   KHONG co bien bo qua. Sua file nao trong manifest => cap nhat manifest CUNG commit (A1 duyet).
gl_manifest_check() {
  local mf=$GL_HERE/GOLIVE_MANIFEST.md5 self bad
  self=$(basename "$1")
  [ "$(cd "$(dirname "$1")" && pwd)" = "$GL_HERE" ] || { echo "TU CHOI [M5]: $1 khong cung thu muc voi golive_lib.sh ($GL_HERE)"; return 1; }
  [ -s "$mf" ] || { echo "TU CHOI [M5]: thieu manifest $mf — khong chay ban chua duoc pin"; return 1; }
  grep -qxE "[0-9a-f]{32}  $self" "$mf" && grep -qxE "[0-9a-f]{32}  golive_lib.sh" "$mf" \
    || { echo "TU CHOI [M5]: $self / golive_lib.sh KHONG co trong manifest $mf"; return 1; }
  bad=$(cd "$GL_HERE" && md5sum -c --strict "$mf" 2>&1 | grep -v ': OK$' | head -5 | tr '\n' ' ')
  if [ -n "$bad" ] || ! (cd "$GL_HERE" && md5sum -c --quiet --strict "$mf" >/dev/null 2>&1); then
    echo "TU CHOI [M5]: file go-live KHAC manifest da commit ($mf): ${bad:-loi md5sum} — sua ngoai quy trinh? KHONG lam gi."; return 1
  fi
  return 0
}
# [A1 ADD4 C-1] co micro/pilot dang bat (Oracle): micro_on/pilot_on/undrain tao, live_off MODE=dry + rollback micro_on xoa;
#   cron golive_monitor (install_cron_golive_monitor.sh) KHONG co co => thoat ngay, 0 call
GL_MON_FLAG=${GL_MON_FLAG:-$LOGDIR/golive_monitor.on}
SUB_FAIL_FILE=${SUB_FAIL_FILE:-$LOGDIR/c3sub_monitor_fail.txt}   # [A1 MIN-1] bo dem luot monitor doc san loi lien tiep
MON_FAIL_MAX=${MON_FAIL_MAX:-5}
CANARY_PAT=${CANARY_PAT:-canary_early}            # [A1 MIN-2] tien trinh canary tren Oracle => micro_on/pilot_on TU CHOI
ORA_CRONTAB_CMD=${ORA_CRONTAB_CMD:-crontab}       # crontab user ubuntu tren Oracle (test: crontab gia)
# [A1 delta MIN-3] heartbeat cron golive_monitor (Oracle): moi luot co co ghi; c3live_status KHAN neu > 6'; micro_on doi heartbeat moi
MON_HB_FILE=${MON_HB_FILE:-$LOGDIR/run/monitor_heartbeat}
MON_HB_MAX_AGE_S=${MON_HB_MAX_AGE_S:-360}
MON_HB_WAIT_S=${MON_HB_WAIT_S:-300}
HB_POLL_S=${HB_POLL_S:-10}
MON_CRON_TAG='# golive_monitor (ADD4 C-1)'
# [ADD4 ERRATA 2 §5] moc eq lop phu monitor: eq = C3_CAPITAL + (tmb - tmb0); micro_on / pilot_on / golive_rebase_equity ghi
SUB_BASE_FILE=${SUB_BASE_FILE:-$LOGDIR/c3sub_eq_base.txt}
SUB_HIST_FILE=${SUB_HIST_FILE:-$LOGDIR/c3sub_tmb_hist.txt}   # [A1 errata2 MIN-1] mau monitor: epoch tmb eq dinh base_id (rebase doi chieu delta)
A1_APPROVED_FILE=${A1_APPROVED_FILE:-$GATE_DIR/A1_APPROVED_MONITOR.md5}   # [A1 errata2 MIN-3] md5(monitor+lib)[:12] da qua A1 (1 dong / ban)
# so/trang thai c3 (doi ten khi doi adapter — so dry/live khong bao gio lan nhau)
GL_STATE_FILES="run/c3live_book.json run/c3live_dry_state.json run/c3live_ledger.csv run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/c3live_killsw_peak run/killsw_latch.json"
# [OPS6 T20] boot guard 242 = c3_autodrain_prestart.sh cai thanh $AD_SBIN/h242-prestart-c3.sh (install_242_autodrain.sh; duong dan nhu installer)
AD_SBIN=${AD_SBIN:-/usr/local/sbin}; AD_SYSTEMD_DIR=${AD_SYSTEMD_DIR:-/etc/systemd/system}; AD_CT242=${AD_CT242:-crontab}
GL_AD_RX='^c3_autodrain [0-9]{8}_[0-9]{6}( caller=[A-Za-z0-9_.-]*)?$'   # dong token RIENG cua boot guard (golive_boot_undrain.sh CHI go dong khop TRON)
GL_PILOT_SIZES="5000 10000"   # [OPS6 T12b] OWNER_DECISION_PILOT_1121 Q1: 10 000 (5 000 = muc giam nua) - gate PILOT chi nhan 2 gia tri nay
# [OPS6 T5/A-02] ham chay tren 242 (gui kem heredoc restart/rollback qua stdin). Jar hotfix (KillSwitchEngine b9e661db + 4fdda6f8) KHONG gan dinh
#   voi von: dinh C6 = run/c3live_killsw_peak ("<so> adapter=live_c3eq", loadPeak), dinh A40 = "acct_peak" trong run/killsw_latch.json (loadLatch),
#   ca 2 nap trong constructor KillSwitchEngine (loadPeak -> loadLatch -> checkResetRequest) TRUOC moi lan danh gia equity c3 (C3MainEquity:
#   C3_CAPITAL + realized + funding + upl). HA VON khi so live giu => equity/dinh - 1 ~ -90 % => C6/A40 FLATTEN GIA.
#   a02_reset (bot PHAI dang DUNG): dinh C6 -> doi ten .a02_<nhan>; acct_peak + acct_peak_adapter go khoi file latch bang python (latch, ma,
#   su kien C2 GIU NGUYEN); khong co python => CHI khi latch NONE: ghi run/killsw_reset.req reset_peak=1 (co che jar, dinh dang ops/killsw_reset.sh).
#   Ket qua: jar lay lai dinh tu equity c3 dau tien sau start (= RESET_PEAK co chu dich). Loi => return 1 (nguoi goi KHONG ha von).
read -r -d '' GL_A02_FN <<'A02EOF' || true
a02_reset() {
  local tg=$1 py=$2 LF=run/killsw_latch.json PF=run/c3live_killsw_peak RQ=run/killsw_reset.req k L r
  for k in LIVE_KILLSW_LATCH_FILE LIVE_C3_KILLSW_PEAK_FILE LIVE_KILLSW_RESET_FILE; do
    if grep -qE "^[[:space:]]*(export[[:space:]]+)?$k=" conf/env.sh 2>/dev/null; then echo "FAIL a02_env_sh_dat_$k (file dinh/latch khong mac dinh - khong biet file jar doc)"; return 1; fi
  done
  L=$(sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' "$LF" 2>/dev/null | head -1)
  if [ -f "$LF" ] && grep -q '"acct_peak' "$LF"; then
    r=""
    if [ -n "$py" ] && [ -x "$py" ] && cp -p "$LF" "$LF.a02_$tg"; then
      r=$("$py" -I - "$LF" 2>&1 <<'PYA'
import json, os, sys
p = sys.argv[1]
o = json.load(open(p))
l0 = o.get("latch")
o.pop("acct_peak", None)
o.pop("acct_peak_adapter", None)
t = p + ".a02tmp"
with open(t, "w") as f:
    f.write(json.dumps(o, separators=(",", ":")) + "\n")
os.replace(t, p)
o2 = json.load(open(p))
print("A02PY=" + ("OK" if ("acct_peak" not in o2 and o2.get("latch") == l0) else "FAIL") + " latch=" + str(l0))
PYA
)
    fi
    if printf '%s\n' "$r" | grep -q '^A02PY=OK' && ! grep -q '"acct_peak' "$LF"; then
      echo "OK a02_acct_peak_A40_go (latch giu nguyen=${L:-?}; ban cu $LF.a02_$tg)"
    else
      [ -f "$LF.a02_$tg" ] && cp -p "$LF.a02_$tg" "$LF"
      if [ "$L" = NONE ]; then
        printf '{"reset_at_ms":%s,"reset_by":"%s","reset_peak":1}\n' "$(( $(date +%s) * 1000 ))" "$tg" > "$RQ.a02tmp" && mv -f "$RQ.a02tmp" "$RQ" \
          && echo "OK a02_yeu_cau_reset_peak $RQ (python khong dung duoc: ${r:-khong chay}; jar ap dung trong constructor KillSwitchEngine TRUOC danh gia equity; latch NONE; xoa su kien C2)" \
          || { echo "FAIL a02_khong_ghi_duoc_$RQ"; return 1; }
      else echo "FAIL a02_khong_go_duoc_acct_peak (python: ${r:-khong chay}) va latch=${L:-?} != NONE (reset_peak se xoa latch => KHONG dung)"; return 1; fi
    fi
  else echo "OK a02_acct_peak_A40_khong_co (latch=${L:-khong_co_file})"; fi
  # dinh C6 SAU acct_peak: buoc A40 loi => chua doi gi (dinh van khop von dang co)
  if [ -e "$PF" ]; then
    mv -f "$PF" "$PF.a02_$tg" && [ ! -e "$PF" ] || { echo "FAIL a02_khong_go_duoc_$PF"; return 1; }
    echo "OK a02_dinh_C6_go (cu: $(head -c 60 "$PF.a02_$tg" | tr -cd '0-9.a-z_= ') -> $PF.a02_$tg)"
  else echo "OK a02_dinh_C6_chua_co_file"; fi
  return 0
}
A02EOF

gl_init() {   # $1 = ten script
  GL_NAME=$1
  TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
  mkdir -p "$LOGDIR"
  LOG=$LOGDIR/${GL_NAME}_${TS}.log
  exec > >(tee -a "$LOG") 2>&1
  say "=== $GL_NAME TS=$TS DRY=$DRY ==="
}
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
gl_mon_flag_set() {   # [C-1] bat cron monitor (ghi tai khoan + file key de monitor doc dung tk). Loi => return 1 (micro_on/pilot_on DUNG)
  [ "$DRY" = 1 ] && return 0
  GL_FLAG_T=$(date +%s)
  local dts=${GL_DRY_TS:-$(sed -n 's/^dry_ts=//p' "$GL_MON_FLAG" 2>/dev/null | head -1)}   # [A1 errata2 MIN-2] TS so dry cua micro_on (giu qua pilot/undrain)
  if mkdir -p "$(dirname "$GL_MON_FLAG")" 2>/dev/null \
     && printf 'C3_ACCOUNT=%s\nKEYS_FILE=%s\nby=%s TS=%s\ndry_ts=%s\n' "$C3_ACCOUNT" "$KEYS_FILE" "${GL_NAME:-?}" "${TS:-?}" "$dts" > "$GL_MON_FLAG.tmp" 2>/dev/null \
     && mv -f "$GL_MON_FLAG.tmp" "$GL_MON_FLAG" 2>/dev/null; then
    say "OK co monitor $GL_MON_FLAG (cron golive_monitor hoat dong)"; return 0
  fi
  say "!! KHONG ghi duoc co monitor $GL_MON_FLAG"; return 1
}
gl_mon_flag_clear() { [ "$DRY" = 1 ] && return 0; [ -e "$GL_MON_FLAG" ] && mv -f "$GL_MON_FLAG" "$GL_MON_FLAG.off_${TS:-x}" && say "OK go co monitor (cron monitor thoat ngay, 0 call)"; return 0; }
# gl_mon_cron_ok : crontab co DUNG 1 dong monitor (MONITOR_CRON=1 + nhan) tro ban PIN con nguyen (md5(monitor+lib)[:12] = ten thu muc)
gl_mon_cron_ok() {
  local ln d
  ln=$($ORA_CRONTAB_CMD -l 2>/dev/null | grep -v '^[[:space:]]*#' | grep -F 'MONITOR_CRON=1' | grep -F "$MON_CRON_TAG")
  [ "$(printf '%s\n' "$ln" | grep -c .)" = 1 ] || return 1
  d=$(printf '%s\n' "$ln" | grep -oE '/[^ ]*/golive_monitor_[0-9a-f]{12}/golive_monitor\.sh' | head -1); d=${d%/golive_monitor.sh}
  [ -n "$d" ] && [ -f "$d/golive_monitor.sh" ] && [ -f "$d/golive_lib.sh" ] || return 1
  [ "$(cat "$d/golive_monitor.sh" "$d/golive_lib.sh" | md5sum | cut -c1-12)" = "${d##*_}" ]
}
gl_mon_pin_cur() { $ORA_CRONTAB_CMD -l 2>/dev/null | grep -qF "golive_monitor_$(cat "$GL_HERE/golive_monitor.sh" "$GL_HERE/golive_lib.sh" | md5sum | cut -c1-12)/"; }
gl_hb_age() { local m; m=$(stat -c %Y "$MON_HB_FILE" 2>/dev/null) || { echo -1; return 0; }; echo $(( $(date +%s) - m )); }
# gl_hb_wait <epoch moc> : cho toi MON_HB_WAIT_S heartbeat cron monitor MOI hon moc (co monitor vua dat) va <= MON_HB_MAX_AGE_S
gl_hb_wait() {
  local t0=$1 end m now
  end=$(( $(date +%s) + MON_HB_WAIT_S ))
  while :; do
    now=$(date +%s); m=$(stat -c %Y "$MON_HB_FILE" 2>/dev/null || echo 0)
    if [ "$m" -ge "$t0" ] && [ $(( now - m )) -le "$MON_HB_MAX_AGE_S" ]; then say "OK heartbeat cron golive_monitor $(( now - m ))s (moi hon co monitor)"; return 0; fi
    [ "$now" -ge "$end" ] && return 1
    sleep "$HB_POLL_S"
  done
}
gl_no_canary() { local n; n=$(pgrep -fc "$CANARY_PAT" 2>/dev/null); [ "${n:-0}" = 0 ]; }
# gl_eq_base_set <tmb0> <c3_capital> <key_sha8> <ly do> [base_id giu] : [ERRATA 2] ghi moc eq (Oracle; ban cu => .bak_<TS>; log ly do). Loi => return 1
gl_eq_base_set() {
  if [ "$DRY" = 1 ]; then say "DRY=1: se ghi moc tmb0=$1 C3_CAPITAL=$2 vao $SUB_BASE_FILE"; return 0; fi
  { [[ "$1" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ "$2" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [ -n "$3" ]; } || { say "!! moc khong hop le: tmb0='$1' C3_CAPITAL='$2' key='$3'"; return 1; }
  mkdir -p "$(dirname "$SUB_BASE_FILE")" 2>/dev/null || return 1
  [ -f "$SUB_BASE_FILE" ] && cp -p "$SUB_BASE_FILE" "$SUB_BASE_FILE.bak_${TS:-x}"
  printf 'tmb0=%s\nc3_capital=%s\nkey_sha8=%s\nbase_id=%s\nrebase_t=%s\nreason=%s\n' "$1" "$2" "$3" "${5:-${TS:-x}_$$}" "$(date +%s)" "$4" > "$SUB_BASE_FILE.tmp" 2>/dev/null \
    && mv -f "$SUB_BASE_FILE.tmp" "$SUB_BASE_FILE" 2>/dev/null || { say "!! KHONG ghi duoc moc $SUB_BASE_FILE"; return 1; }
  echo "$(TZ=Asia/Ho_Chi_Minh date '+%F %T') tmb0=$1 c3_capital=$2 key_sha8=$3 base_id=${5:-${TS:-x}_$$} ly_do=$4" >> "${SUB_BASE_FILE%.txt}.log" 2>/dev/null
  say "OK moc eq: tmb0=$1 C3_CAPITAL=$2 ($SUB_BASE_FILE)"
}
# gl_mon_repin : [ERRATA 2] goi installer cron (idempotent) => cron chay ban PIN = monitor + lib repo hien tai; in md5 pin. Loi => return 1
gl_mon_m12() { cat "$GL_HERE/golive_monitor.sh" "$GL_HERE/golive_lib.sh" | md5sum | cut -c1-12; }
gl_mon_approved() { [ -f "$A1_APPROVED_FILE" ] && grep -qE "^$(gl_mon_m12)([[:space:]]|$)" "$A1_APPROVED_FILE"; }
gl_mon_repin() {
  local out rc m
  gl_mon_approved || { say "!! md5 monitor+lib $(gl_mon_m12) KHONG co trong $A1_APPROVED_FILE (ban chua qua A1) — khong pin"; return 1; }
  out=$(DRY=$DRY bash "$GL_HERE/install_cron_golive_monitor.sh" 2>&1); rc=$?
  echo "$out" | sed 's/^/   pin| /'
  [ "$rc" = 0 ] || return 1
  [ "$DRY" = 1 ] && return 0
  gl_mon_cron_ok && gl_mon_pin_cur || return 1
  m=$(cat "$GL_HERE/golive_monitor.sh" "$GL_HERE/golive_lib.sh" | md5sum | cut -c1-12)
  say "OK cron golive_monitor chay ban pin md5=$m"
}
# gl_tag_drybook : [ERRATA 2] adapter=dry => dong doi chieu SO (dry) gan nhan "chi ghi log" (khong tinh ket qua)
gl_tag_drybook() {
  if [ "$(sv ENV_LIVE_ADAPTER)" = dry ]; then sed -E 's/^((POS_C3_MISMATCH|C3_BOOK_SYMBOLS|C3_UNRESOLVED|POS_PENDING)=.*)$/\1   [so DRY — chi ghi log, khong tinh ket qua]/'; else cat; fi
}
tg() {
  local msg code tok chat
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g' | head -c 3500)
  if [ -n "${DEPLOY_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$DEPLOY_TG_SINK"; return 0; fi
  [ -r "$DEPLOY_TG_ENV" ] || { say "!! khong doc duoc $DEPLOY_TG_ENV — KHONG gui Telegram"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || return 1
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m "${GL_TG_TIMEOUT_S:-15}" -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null)
  tok=""; [ "$code" = 200 ]
}
die() { say "DUNG: $*"; say "KET QUA: TU_CHOI (khong doi gi). Log: $LOG"; exit 1; }
# [WAVE1 B-05] _ssh: boc timeout khi GL_SSH_TIMEOUT_S > 0 (cron monitor) — ssh treo khong an het "timeout 100" cua cron
# [WAVE1b M7] GL_SSH_DEADLINE (epoch, cron monitor dat): timeout moi lenh = min(GL_SSH_TIMEOUT_S, con lai); con < 3 s => KHONG ssh, rc 255
#   => TONG thoi gian ssh 1 luot <= ngan sach (+5 s kill), < "timeout 100" cua cron du 242 mat mang
_ssh() {
  local t=${GL_SSH_TIMEOUT_S:-0} rem
  if [ "${GL_SSH_DEADLINE:-0}" -gt 0 ] 2>/dev/null; then
    rem=$(( GL_SSH_DEADLINE - $(date +%s) ))
    [ "$rem" -ge 3 ] || { echo "[ssh 242 BO QUA: het ngan sach thoi gian luot (GL_SSH_DEADLINE)]" >&2; return 255; }
    { [ "$t" -gt 0 ] 2>/dev/null && [ "$t" -le "$rem" ]; } || t=$rem
  fi
  if [ "$t" -gt 0 ] 2>/dev/null; then timeout -k 5 "$t" $SSH_242 "$@"; else $SSH_242 "$@"; fi
}
# s242 / s242in : CHI cho lenh CHI DOC hoac IDEMPOTENT (dat KILL_SWITCH neu chua co, doc log...) — thu lai GL_SSH_TRIES lan khi rc=255
s242() {
  local i rc=255
  for i in $(seq 1 "$GL_SSH_TRIES"); do
    _ssh "$@" < /dev/null; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt "$GL_SSH_TRIES" ] && { echo "[ssh 242 loi ket noi — thu lai $i/$((GL_SSH_TRIES - 1)) sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
s242in() {
  local in i rc=255
  in=$(cat)
  for i in $(seq 1 "$GL_SSH_TRIES"); do
    printf '%s\n' "$in" | _ssh "$@"; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt "$GL_SSH_TRIES" ] && { echo "[ssh 242 loi ket noi — thu lai $i/$((GL_SSH_TRIES - 1)) sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
# [WAVE1 B-02] s242in_once : buoc CO TAC DUNG PHU (restart / rollback) — CHAY DUNG 1 LAN, KHONG tu chay lai khi rc=255.
#   Nguoi goi phai DOC trang thai that tren 242 (gl_phase242) roi moi quyet chay lai (heredoc idempotent theo marker pha).
s242in_once() { _ssh "$@"; }
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
# gl_gate <file> [strict] : file gate MASTER (khong rong) co dong jar_md5=<NJ_MD5>. In "OK"/"FAIL ...".
#   [WAVE1 B-08] strict=1 (G-MICRO): them ingestor_md5=<ING_FIN_MD5>, created_ms (tuoi <= GATE_MAX_AGE_S = 48 h, khong o tuong lai),
#   expires_ms (> bay gio), gmicro_i=DAT.., gmicro_ii=DAT.., smoke=DAT.., prereg_commit=<hex 7-40>. Thieu / sai / het han => FAIL.
#   MASTER tao bang golive_make_gate.sh (doc gmicro_target.json + report G-MICRO, tu choi neu chua DAT).
gl_gate() {
  local f=$1 st=${2:-0} why="" now c e x
  [ -s "$f" ] || { echo "FAIL thieu_file_gate $f"; return 1; }
  grep -qx "jar_md5=$NJ_MD5" "$f" || { echo "FAIL gate_$f khong co dong jar_md5=$NJ_MD5"; return 1; }
  if [ "$st" = 1 ]; then
    now=$(( $(date +%s) * 1000 ))
    grep -qx "ingestor_md5=$ING_FIN_MD5" "$f" || why="$why ingestor_md5!=$ING_FIN_MD5"
    c=$(gl_gate_val "$f" created_ms); e=$(gl_gate_val "$f" expires_ms)
    if ! [[ "$c" =~ ^[0-9]{13}$ ]]; then why="$why thieu_created_ms"
    elif [ $(( now - c )) -gt $(( GATE_MAX_AGE_S * 1000 )) ]; then why="$why gate_cu_$(( (now - c) / 1000 ))s>${GATE_MAX_AGE_S}s(het_han)"
    elif [ $(( c - now )) -gt 300000 ]; then why="$why created_ms_o_tuong_lai"; fi
    if ! [[ "$e" =~ ^[0-9]{13}$ ]]; then why="$why thieu_expires_ms"
    elif [ "$e" -le "$now" ]; then why="$why expires_ms_da_qua(het_han)"; fi
    # [WAVE1b M4] 6 truong ADD22 §3: DAT + ev=<file ton tai> | OVERRIDE (chi khi gate co override_by + override_why)
    local ovb ovw evf raw
    ovb=$(sed -n 's/^override_by=//p' "$f" | head -1); ovw=$(sed -n 's/^override_why=//p' "$f" | head -1)
    for x in $GL_GATE_FIELDS; do
      raw=$(sed -n "s/^$x=//p" "$f" | head -1)
      if [[ "$raw" =~ ^DAT ]]; then
        evf=$(printf '%s' "$raw" | grep -oE '(^| )ev=[^ ]+' | head -1 | sed 's/^ *ev=//')
        [ -n "$evf" ] && [ -s "$evf" ] || why="$why ${x}_DAT_thieu_file_bang_chung(${evf:-khong_co_ev})"
      elif [[ "$raw" =~ ^OVERRIDE ]] && [ -n "$ovb" ] && [ -n "$ovw" ]; then :
      else why="$why ${x}_khong_DAT"; fi
    done
    [[ "$(gl_gate_val "$f" prereg_commit)" =~ ^[0-9a-f]{7,40}$ ]] || why="$why thieu_prereg_commit"
    [ -z "$why" ] || { echo "FAIL gate $f:$why"; return 1; }
    echo "OK gate $f (jar_md5=$NJ_MD5 ingestor_md5=$ING_FIN_MD5 tuoi=$(( (now - c) / 1000 ))s het_han_sau=$(( (e - now) / 1000 ))s $(gl_gate_val "$f" gmicro_i | cut -c1-40) prereg=$(gl_gate_val "$f" prereg_commit))$([ -n "$ovb" ] && echo " OVERRIDE by=$ovb fields=$(sed -n 's/^override_fields=//p' "$f" | head -1)")"
    return 0
  fi
  echo "OK gate $f (jar_md5=$NJ_MD5)"
}
gl_gate_val() { sed -n "s/^$2=//p" "$1" | head -1 | tr -d '\r '; }
# [OPS6 T12b] gl_gate_pilot <file> : gate G-PILOT do golive_make_gate_pilot.sh ghi. In "OK ..." / "FAIL ...". Kiem: body_sha256 (dong cuoi = sha256
#   moi dong tren => sua tay bi bat), created_ms/expires_ms (tuoi <= GATE_MAX_AGE_S, chua het han), jar_md5=NJ_MD5, size thuoc GL_PILOT_SIZES,
#   g_exec / g_exit hop le, mien_x14 / mien_b2 / mien_c1 = MIEN|DA_SUA ref=<commit>, boot_guard=CAI, owner_decision=<commit 40 hex>, by=make_gate_pilot.
gl_gate_pilot() {
  local f=$1 why="" now c e n x v
  [ -s "$f" ] || { echo "FAIL thieu_file_gate $f"; return 1; }
  grep -qx "jar_md5=$NJ_MD5" "$f" || why="$why jar_md5!=$NJ_MD5"
  n=$(grep -c '' "$f"); x=$(tail -n 1 "$f" | sed -n 's/^body_sha256=//p'); v=$(head -n $(( n - 1 )) "$f" | sha256sum | cut -c1-64)
  [ -n "$x" ] && [ "$x" = "$v" ] || why="$why body_sha256_sai(gate_bi_sua_tay?)"
  now=$(( $(date +%s) * 1000 )); c=$(gl_gate_val "$f" created_ms); e=$(gl_gate_val "$f" expires_ms)
  if ! [[ "$c" =~ ^[0-9]{13}$ ]]; then why="$why thieu_created_ms"
  elif [ $(( now - c )) -gt $(( GATE_MAX_AGE_S * 1000 )) ]; then why="$why gate_cu_$(( (now - c) / 1000 ))s>${GATE_MAX_AGE_S}s(het_han)"
  elif [ $(( c - now )) -gt 300000 ]; then why="$why created_ms_o_tuong_lai"; fi
  if ! [[ "$e" =~ ^[0-9]{13}$ ]]; then why="$why thieu_expires_ms"
  elif [ "$e" -le "$now" ]; then why="$why expires_ms_da_qua(het_han)"; fi
  v=$(gl_gate_val "$f" size); case " $GL_PILOT_SIZES " in *" $v "*) [ -n "$v" ] || why="$why thieu_size";; *) why="$why size='$v'_ngoai_{${GL_PILOT_SIZES// /,}}";; esac
  grep -qE '^g_exec=(GREEN|AMBER|RED_SIZE|Q4_OWNER) [^ ]' "$f" || why="$why g_exec_thieu/sai"
  grep -qE '^g_exit=(DAT|Q4_OWNER) [^ ]' "$f" || why="$why g_exit_thieu/sai"
  for x in mien_x14 mien_b2 mien_c1; do grep -qE "^$x=(MIEN|DA_SUA) ref=[0-9a-f]{7,40}( |\$)" "$f" || why="$why thieu_$x"; done
  grep -qE '^boot_guard=CAI( |$)' "$f" || why="$why boot_guard_chua_CAI"
  grep -qE '^owner_decision=[0-9a-f]{40}( |$)' "$f" || why="$why thieu_owner_decision"
  grep -qE '^by=MASTER golive_make_gate_pilot\.sh( |$)' "$f" || why="$why khong_phai_golive_make_gate_pilot"
  [ -z "$why" ] || { echo "FAIL gate $f:$why"; return 1; }
  echo "OK gate PILOT $f (jar_md5=$NJ_MD5 size=$(gl_gate_val "$f" size) tuoi=$(( (now - c) / 1000 ))s het_han_sau=$(( (e - now) / 1000 ))s)"
}
# [OPS6 T20] gl_bootguard242 : CHI DOC 242 - boot guard (wrapper $AD_SBIN/h242-prestart-c3.sh = c3_autodrain_prestart.sh cua repo nay, cron watchdog
#   co WD_PRESTART=wrapper, drop-in systemd h242-trading ExecStartPre=wrapper). Dat BG=CAI|CHUA_CAI|LOI, BG_DETAIL. Lenh tren 242: md5sum file
#   wrapper, crontab -l (root), grep file drop-in - KHONG ghi gi.
gl_bootguard242() {
  local w5 o bw bh bd
  w5=$(md5sum < "$GL_HERE/c3_autodrain_prestart.sh" 2>/dev/null | cut -c1-32)
  o=$(s242 "WR=$AD_SBIN/h242-prestart-c3.sh; DF=$AD_SYSTEMD_DIR/h242-trading.service.d/c3-autodrain.conf; echo BG_WRAPPER_MD5=\$([ -f \"\$WR\" ] && md5sum < \"\$WR\" | cut -c1-32); echo BG_CRON_HOOK=\$($AD_CT242 -l 2>/dev/null | grep -v '^[[:space:]]*#' | grep -F 'h242_watchdog.sh' | grep -cF \"WD_PRESTART=\$WR \"); echo BG_DROPIN=\$(grep -qxF \"ExecStartPre=\$WR $A com.binance.chuyennd.trading.BinanceOrderTradingManager\" \"\$DF\" 2>/dev/null && echo 1 || echo 0); echo END_BG" 2>/dev/null)
  bw=$(printf '%s\n' "$o" | sed -n 's/^BG_WRAPPER_MD5=//p' | head -1); bh=$(printf '%s\n' "$o" | sed -n 's/^BG_CRON_HOOK=//p' | head -1)
  bd=$(printf '%s\n' "$o" | sed -n 's/^BG_DROPIN=//p' | head -1)
  BG_DETAIL="wrapper_md5=${bw:-khong_co} repo=$w5 cron_hook=${bh:-?} dropin=${bd:-?}"
  if ! printf '%s\n' "$o" | grep -qx END_BG; then BG=LOI; BG_DETAIL="doc 242 loi (ssh?)"
  elif [ -n "$w5" ] && [ "$bw" = "$w5" ] && [ "$bh" = 1 ] && [ "$bd" = 1 ]; then BG=CAI
  else BG=CHUA_CAI; fi
}

# gl_state242 : CHI DOC 242 -> dong KEY=VAL (de script kiem o Oracle). Ket thuc END_STATE.
gl_state242() {
  # [WAVE1] PP = mau [X]yz (gl_rx): pgrep KHONG dem chinh tien trinh boc lenh (timeout/ssh wrapper co chuoi PP trong cmdline)
  s242in "PP='$(gl_rx "$PROC_PAT")' IPAT='$ING_PAT' bash -s -- $A $WD_PAUSE $KEYS_FILE $PY242" <<'EOF'
A=$1; PAUSE=$2; KF=$3; PY=${4:-}; cd "$A" || { echo "ERR=cd"; echo END_STATE; exit 0; }
echo "NPROC=$(pgrep -fc "$PP")"
P=$(pgrep -f "$PP" | head -1)
echo "PID=$P"
echo "JAR_MD5=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_PROFILE LIVE_ADAPTER C3_CAPITAL TIER_FLAT SHADOW_NO_PUSH LIVE_ENTRY_ENABLED LIVE_SEED_EXCLUDE_DECISION_MIN LIVE_KILLSW_MODE GATE_BUFFER_SEED LIVE_C3_KEYS_FILE C3_EXCLUDE_LEGACY_HELD LIVE_APPLY_GRID_RATIO LIVE_DCA_GRID_ENABLED SIM_F_BASE DCA_GRID_WEIGHTS DCA_GRID_SCALE SIM_FIX_B2 SIM_U_MAX; do
  echo "ENV_$k=$(echo "$E" | sed -n "s/^$k=//p" | tail -1)"
done
for k in LIVE_ADAPTER C3_CAPITAL LIVE_SEED_EXCLUDE_DECISION_MIN C3_EXCLUDE_LEGACY_HELD LIVE_APPLY_GRID_RATIO LIVE_DCA_GRID_ENABLED SIM_F_BASE DCA_GRID_WEIGHTS DCA_GRID_SCALE DCA_GRID_LEVELS SIM_FIX_B2 SIM_U_MAX LIVE_C3_KEYS_FILE; do
  echo "ENVSH_$k=$(sed -n "s/^export $k=//p" conf/env.sh | tail -1)"
done
# [WAVE1 B-08] md5 jar ingestor DANG chay (fd cua process, nhu deploy_chain rstate)
IP=$(pgrep -f "${IPAT:-websocket.BinanceDataIngestor}" | head -1); IFD=$(find /proc/$IP/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
echo "ING_MD5=$( [ -n "$IP" ] && [ -n "$IFD" ] && md5sum < "$IFD" 2>/dev/null | cut -c1-32)"
L=$(sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' run/killsw_latch.json 2>/dev/null | head -1); echo "LATCH=${L:-NOFILE}"
[ -e "$PAUSE" ] && echo "PAUSE=1 $(head -c 60 "$PAUSE" 2>/dev/null | tr '\n' ' ')" || echo "PAUSE=0"
[ -e "$PAUSE" ] && echo "PAUSE_AGE=$(( $(date +%s) - $(stat -c %Y "$PAUSE" 2>/dev/null || echo 0) ))" || echo "PAUSE_AGE=-1"   # [WAVE1b M6]
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
# [OPS5_FIX 8b + VONG3 F1] KILLSW_TOK = c3live_boot | c3_autodrain CHI KHI file DUNG 1 dong va KHOP TRON dong token chuan (wrapper 242 /
#   jar C3BootLock nguyen van); moi truong hop khac (them dong, ky tu la, file rong) => rong => micro_on/pilot_on TU CHOI. KHONG in ca dong.
echo "KILLSW_TOK=$([ "$(grep -c '' run/KILL_SWITCH 2>/dev/null)" = 1 ] && grep -qxE '(c3_autodrain [0-9]{8}_[0-9]{6}( caller=[A-Za-z0-9_.-]*)?|c3live_boot [0-9]{8}_[0-9]{6}( B-09: JVM LIVE khoi dong KHONG qua script go-live \(crash/watchdog/reboot/restart tay\) => dung mo moi, vi the c3 van duoc quan ly\. Mo: MODE=undrain bash golive_live_off\.sh)?)' run/KILL_SWITCH && awk 'NR==1{print $1}' run/KILL_SWITCH)"
[ -f "$KF" ] && [ "$(stat -c %a "$KF")" = 600 ] && [ "$(grep -c '^C3_LIVE_API_\(KEY\|SECRET\)=' "$KF")" = 2 ] && echo "KEYS_OK=1" || echo "KEYS_OK=0"
# [WAVE1 A-03] sha8 key trong file (sha256 chuoi key, KHONG in key) + quyen — so voi SUB_KEY_SHA8 da dang ky o Oracle
[ -f "$KF" ] && echo "KEYS_PERM=$(stat -c %a "$KF")" || echo "KEYS_PERM=thieu"
[ -f "$KF" ] && echo "KEYS_FILE_SHA8=$(sed -n 's/^C3_LIVE_API_KEY=//p' "$KF" | head -1 | tr -d ' \t\r"' | tr -d '\n' | sha256sum | cut -c1-8)" || echo "KEYS_FILE_SHA8="
# [OPS6 T5/A-02] rollback/ha von can python 242 (go acct_peak) + duong dan file dinh/latch/reset/KS MAC DINH (env.sh khong ghi de) - CHI DOC
echo "PY_OK=$([ -n "$PY" ] && [ -x "$PY" ] && echo 1 || echo 0)"
echo "ENVSH_PATH_OVR=$(grep -oE '^[[:space:]]*(export[[:space:]]+)?(LIVE_KILLSW_LATCH_FILE|LIVE_C3_KILLSW_PEAK_FILE|LIVE_KILLSW_RESET_FILE|LIVE_KILL_SWITCH_FILE)=' conf/env.sh 2>/dev/null | sed -E 's/^[[:space:]]*(export[[:space:]]+)?//; s/=$//' | tr '\n' ',' | sed 's/,$//')"
echo END_STATE
EOF
}
gl_read_state() {
  ST=$(gl_state242) || die "ssh toi 242 loi"
  echo "$ST" | grep -qx END_STATE || die "doc trang thai 242 khong tron ven (ssh dut?)"
  echo "$ST" | grep -q '^ERR=' && die "doc trang thai 242 loi: $(echo "$ST" | grep '^ERR=')"
}
sv() { echo "$ST" | sed -n "s/^$1=//p" | head -1; }
# [OPS5_FIX 8b] precheck micro_on/pilot_on: KHONG co run/KILL_SWITCH, HOAC token bat dau c3live_boot / c3_autodrain (khoi dong ngoai quy trinh
#   da tu drain) => chap nhan (gl_restart ks=1 ghi de, ban cu -> run/KILL_SWITCH.prev_<TS>). Token khac (owner drain / monitor / script) => tu choi.
# [VONG3 F1] gl_ks_go_own <NM> : go run/KILL_SWITCH CUA MINH (token "<NM> $TS ") sau hau kiem DAT - CHI khi MOI dong la cua minh.
#   In OK (da go, idempotent) | KHAC (co dong/token khac: owner drain / monitor KHAN => GIU NGUYEN) | MAT (khong co file) | LOI.
gl_ks_go_own() {
  s242 "cd $A && if [ -e run/KILL_SWITCH.ok_$TS ] && [ ! -e run/KILL_SWITCH ]; then echo KSGO=OK; elif [ ! -e run/KILL_SWITCH ]; then echo KSGO=MAT; elif ! grep -q '^$1 $TS ' run/KILL_SWITCH || [ \"\$(grep -vc '^$1 $TS ' run/KILL_SWITCH)\" != 0 ]; then echo KSGO=KHAC; else mv -f run/KILL_SWITCH run/KILL_SWITCH.ok_$TS && [ ! -e run/KILL_SWITCH ] && echo KSGO=OK || echo KSGO=LOI; fi" 2>/dev/null | sed -n 's/^KSGO=//p' | tail -1
}
# [VONG3 F2] gl_ks_restore_prev <NM> : sau rollback (live) - go KS cua minh (chi khi MOI dong la cua minh) roi tra token cu .prev_$TS
#   (c3live_boot / c3_autodrain) neu co => trang thai PUSH nhu TRUOC script. In PUSH (khong con KS) | DRAIN (con KS).
gl_ks_restore_prev() {
  s242 "cd $A && { ! grep -q '^$1 $TS ' run/KILL_SWITCH 2>/dev/null || { [ \"\$(grep -vc '^$1 $TS ' run/KILL_SWITCH)\" = 0 ] && mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_$TS; }; }; { [ ! -e run/KILL_SWITCH.prev_$TS ] || [ -e run/KILL_SWITCH ] || cp -p run/KILL_SWITCH.prev_$TS run/KILL_SWITCH; }; [ -e run/KILL_SWITCH ] && echo KSR=DRAIN || echo KSR=PUSH" 2>/dev/null | sed -n 's/^KSR=//p' | tail -1
}
gl_ks_boot_ok() { [ "$(sv KILLSW_FILE)" = 0 ] && return 0; case "$(sv KILLSW_TOK)" in c3live_boot|c3_autodrain) return 0;; esac; return 1; }
# gl_excl_guard : [A1 r4u2 C-1] C3_ACCOUNT=MAIN + C3_EXCLUDE_LEGACY_HELD=false (process HOAC env.sh) => DUNG
gl_excl_guard() {
  if [ "$C3_ACCOUNT" = MAIN ] && { [ "$(sv ENV_C3_EXCLUDE_LEGACY_HELD)" = false ] || [ "$(sv ENVSH_C3_EXCLUDE_LEGACY_HELD)" = false ]; }; then
    die "C3_ACCOUNT=MAIN di voi C3_EXCLUDE_LEGACY_HELD=false — TU CHOI (A1 r4u2 C-1: vi the c3 that bi tinh la LEGACY)"
  fi
}

# [WAVE1 B-02] gl_phase242 <NM> : CHI DOC — trang thai THAT tren 242 cua lan chay TS nay (marker pha, process, env, KILL_SWITCH, backup).
#   Goi sau khi ssh rc=255 o buoc co tac dung phu, TRUOC khi quyet chay lai (heredoc restart/rollback idempotent theo marker).
gl_rx() { printf '[%s]%s' "${1:0:1}" "${1:1}"; }   # mau pgrep KHONG tu khop dong lenh bash -c chua chinh no
gl_phase242() {
  local PX; PX=$(gl_rx "$PROC_PAT")
  s242 "cd $A 2>/dev/null || exit 0; echo PHASE=\$(tr '\n' ' ' < run/.golive_${1}_$TS.phase 2>/dev/null); echo RBPHASE=\$(tr '\n' ' ' < run/.golive_${1}_$TS.rbphase 2>/dev/null); echo NPROC=\$(pgrep -fc '$PX'); P=\$(pgrep -f '$PX' | head -1); echo PADAPTER=\$(tr '\0' '\n' < /proc/\$P/environ 2>/dev/null | sed -n 's/^LIVE_ADAPTER=//p' | tail -1); echo ENVSH_ADAPTER=\$(sed -n 's/^export LIVE_ADAPTER=//p' conf/env.sh | tail -1); echo BAK=\$([ -f conf/env.sh.bak_${1}_$TS ] && echo co || echo khong); echo KS=\$(head -c 80 run/KILL_SWITCH 2>/dev/null | tr '\n' ' '); echo END_PHASE"
}
# gl_once_resume <ten buoc> <ham heredoc> <bien ket qua> <marker ket thuc> : chay buoc co tac dung phu 1 lan; rc=255 / thieu marker
#   => doc trang thai that (gl_phase242) => chay LAI heredoc (idempotent) toi da GL_RESUME_MAX lan; van loi => FAIL ..._trang_thai_khong_ro
GL_RESUME_MAX=${GL_RESUME_MAX:-2}
gl_once_resume() {
  local step=$1 fn=$2 out rc i=0 ph
  out=$($fn); rc=$?
  while [ "$rc" = 255 ] || ! printf '%s\n' "$out" | grep -qx "$4"; do
    i=$((i + 1))
    say "!! $step: ssh rc=$rc / ket qua khong tron ven (lan $i) — DOC trang thai that tren 242 truoc khi quyet"
    printf '%s\n' "$out" | sed 's/^/   (lan truoc) /'
    if [ "$i" -gt "$GL_RESUME_MAX" ]; then
      out="$out
FAIL ssh_${step}_loi_trang_thai_khong_ro (rc=$rc sau $GL_RESUME_MAX lan doc lai) — KHONG tu ket luan"
      break
    fi
    sleep "$SSH_RETRY_S"
    ph=$(gl_phase242 "$GL_NAME"); echo "$ph" | sed 's/^/   242 that: /'
    printf '%s\n' "$ph" | grep -qx END_PHASE || { rc=255; out="(doc trang thai 242 loi)"; continue; }
    say "   => chay LAI buoc $step (idempotent theo marker pha — buoc da xong KHONG lam lai, backup env KHONG ghi de)"
    out=$($fn); rc=$?
  done
  printf -v "$3" '%s' "$out"
}
# ---------------------------------------------------------------- restart co env moi + doi ten trang thai (tuy chon)
# gl_restart "<ENV_ADD>" "<files can doi ten>" <hau to> [ks] ; in RS (dong OK/FAIL, START_LINE=)
#   ks=1 [R4q MAJ-1]: dat run/KILL_SWITCH (token "<ten script> <TS> ", vd "golive_micro_on 20261105_101500 ") TRUOC khi dung bot => JVM moi len KHONG mo lenh moi toi khi
#   script go (sau hau kiem DAT). FAIL truoc khi dung bot => env + KILL_SWITCH cua minh duoc go lai.
#   [WAVE1 B-02] IDEMPOTENT: marker pha run/.golive_<NM>_<TS>.phase (env_ok/stopped/moved/START_LINE=/started); backup env tao 1 lan /
#   TS (KHONG ghi de); chay lai sau ssh dut => buoc da xong KHONG lam lai. Khong bao gio tu chay lai khi rc=255 ma khong doc 242.
_gl_restart_rx() {
  { printf '%s\n' "$GL_A02_FN"; cat <<EOF2
A=\$1; TS=\$2; EB=\$3; NADD=\$4; PAUSE=\$5; MAXS=\$6; JP=\$7; NM=\$8; SUF=\$9; KS=\${10:-0}; PY=\${11:-}; cd "\$A" || { echo "FAIL cd"; echo END_RS; exit 0; }
PH=run/.golive_\${NM}_\$TS.phase; BK=conf/env.sh.bak_\${NM}_\$TS
ph() { grep -qx "\$1" "\$PH" 2>/dev/null; }
mark() { echo "\$1" >> "\$PH"; }
ksoff() { grep -q "^\${NM} \$TS " run/KILL_SWITCH 2>/dev/null && [ "\$(grep -vc "^\${NM} \$TS " run/KILL_SWITCH)" = 0 ] && mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_\$TS && { [ ! -e run/KILL_SWITCH.prev_\$TS ] || cp -p run/KILL_SWITCH.prev_\$TS run/KILL_SWITCH; }; }   # [OPS5_FIX 8b] tra token cu (c3live_boot/c3_autodrain)
restore() { ph stopped || { \cp -f "\$BK" conf/env.sh; sed -i '/^env_ok\$/d' "\$PH" 2>/dev/null; }; }
if ph started; then
  echo "INFO pha_da_xong_truoc (chay lai sau ssh dut): KHONG stop/start lai"
  echo "OK env_them_\${NADD}_dong (pha truoc)"; echo "OK da_stop"; echo "START_LINE=\$(sed -n 's/^START_LINE=//p' "\$PH" | tail -1)"
  P=\$(pgrep -f "\$PP" | head -1)
  [ -n "\$P" ] && echo "OK started pid=\$P lstart=\$(ps -o lstart= -p \$P)" || echo "FAIL khong_thay_process_sau_start"
  echo END_RS; exit 0
fi
[ -e "\$BK" ] || \cp -p conf/env.sh "\$BK" || { echo "FAIL backup_env"; echo END_RS; exit 0; }
if ph env_ok; then echo "OK env_them_\${NADD}_dong (pha truoc)"
else
  D=\$(diff "\$BK" conf/env.sh | grep -c '^>')
  [ "\$D" = 0 ] && { echo "\$EB" | base64 -d >> conf/env.sh; D=\$(diff "\$BK" conf/env.sh | grep -c '^>'); }
  if [ "\$D" = "\$NADD" ] && [ "\$(tail -n "\$NADD" conf/env.sh | md5sum)" = "\$(echo "\$EB" | base64 -d | md5sum)" ]; then mark env_ok; echo "OK env_them_\${D}_dong"
  else \cp -f "\$BK" conf/env.sh; echo "FAIL env_diff=\$D (da khoi phuc)"; echo END_RS; exit 0; fi
fi
if [ "\$KS" = 1 ]; then
  # [VONG3 F3] kiem LAI ngay truoc khi dat: KS co san ma KHONG phai cua minh va KHONG phai 1 dong token boot/autodrain chuan
  #   (owner drain / monitor KHAN xuat hien SAU precheck) => KHONG ghi de, env khoi phuc, bot KHONG dung
  if [ -e run/KILL_SWITCH ] && ! grep -q "^\${NM} \$TS " run/KILL_SWITCH 2>/dev/null \
     && ! { [ "\$(grep -c '' run/KILL_SWITCH)" = 1 ] && grep -qxE '(c3_autodrain [0-9]{8}_[0-9]{6}( caller=[A-Za-z0-9_.-]*)?|c3live_boot [0-9]{8}_[0-9]{6}( B-09: JVM LIVE khoi dong KHONG qua script go-live \(crash/watchdog/reboot/restart tay\) => dung mo moi, vi the c3 van duoc quan ly\. Mo: MODE=undrain bash golive_live_off\.sh)?)' run/KILL_SWITCH; }; then
    if ph stopped; then
      # [OPS6 T2/N1] chay LAI sau ssh dut: bot DA DUNG o lan truoc (pha stopped, chua started) va KS nguoi khac xuat hien (owner drain ghi de /
      #   monitor KHAN) => KHONG start voi env MOI. env.sh VE backup GOC (von cu, khop dinh kill-switch), KS nguoi khac GIU NGUYEN (khong them/go),
      #   bot VAN DUNG (PAUSE cua script giu; het han => watchdog start voi env CU + KS drain). In 'OK da_stop' (SU THAT) => nguoi goi ROLLBACK.
      \cp -f "\$BK" conf/env.sh; sed -i '/^env_ok\$/d' "\$PH" 2>/dev/null; ph aborted_ks_khac || mark aborted_ks_khac
      echo "OK da_stop (bot DA DUNG o lan chay truoc - ssh dut giua chung)"
      echo "FAIL KILL_SWITCH_token_khac_sau_khi_bot_DA_DUNG (\$(head -c 60 run/KILL_SWITCH | tr -cd 'A-Za-z0-9_ .=:-')) - env.sh DA VE backup goc (von cu), KS nguoi khac GIU NGUYEN, bot DANG DUNG => nguoi goi ROLLBACK (start env cu + kiem)"
      echo "INFO trang_thai_242: env.sh C3_CAPITAL=\$(sed -n 's/^export C3_CAPITAL=//p' conf/env.sh | tail -1) process=\$(pgrep -fc "\$PP") KILL_SWITCH=\$(grep -c '' run/KILL_SWITCH)_dong PAUSE=\$([ -e "\$PAUSE" ] && head -c 50 "\$PAUSE" | tr -cd 'A-Za-z0-9_ .=:-' || echo khong)"
      echo END_RS; exit 0
    fi
    restore; echo "FAIL KILL_SWITCH_token_khac_luc_restart (owner drain / monitor KHAN xuat hien sau precheck: \$(head -c 60 run/KILL_SWITCH | tr -cd 'A-Za-z0-9_ .=:-')) - KHONG ghi de, env khoi phuc, bot KHONG dung"; echo END_RS; exit 0
  fi
  { grep -q "^\${NM} \$TS " run/KILL_SWITCH 2>/dev/null || { { [ ! -e run/KILL_SWITCH ] || [ -e run/KILL_SWITCH.prev_\$TS ] || cp -p run/KILL_SWITCH run/KILL_SWITCH.prev_\$TS; } && echo "\${NM} \$TS hau_kiem: dung mo moi toi khi hau kiem DAT" > run/KILL_SWITCH; }; } && grep -q "^\${NM} \$TS " run/KILL_SWITCH \
    && echo "OK KILL_SWITCH_dat_truoc_start" || { restore; echo "FAIL khong_dat_duoc_KILL_SWITCH (env khoi phuc, bot KHONG dung)"; echo END_RS; exit 0; }
fi
TOK="C3GOLIVE_\${NM} TS=\$TS pid=\$JP"
mkdir -p "\$(dirname "\$PAUSE")" 2>/dev/null; echo "\$TOK t=\$(date +%s)" > "\$PAUSE" && echo "OK watchdog_PAUSE token='\$TOK'" || echo "WARN khong_tao_duoc_PAUSE"
if ! ph pause_timer; then
  setsid nohup bash -c "sleep \$MAXS; grep -q '^\$TOK ' '\$PAUSE' 2>/dev/null && rm -f '\$PAUSE'" > /dev/null 2>&1 < /dev/null &
  mark pause_timer
fi
if ! ph stopped; then
  echo "LEGACY_TRUOC_STOP=\$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print \$2}')"   # [R4r] chup NGAY truoc stop
  bin/daemon.sh stop
  for i in \$(seq 1 30); do pgrep -f "\$PP" >/dev/null || break; sleep 2; done
  if pgrep -f "\$PP" >/dev/null; then \cp -f "\$BK" conf/env.sh; sed -i '/^env_ok\$/d' "\$PH"; ksoff; echo "FAIL van_con_process_sau_stop (env khoi phuc)"; echo END_RS; exit 0; fi
  mark stopped
fi
echo "OK da_stop"
[ -e run/.golive_\${NM}_\$TS.moved ] || : > run/.golive_\${NM}_\$TS.moved
if [ "\$SUF" != none ] && ! ph moved; then
  for f in $GLR_FILES; do [ -e "\$f" ] && [ ! -e "\$f.\${SUF}_\$TS" ] && mv -f "\$f" "\$f.\${SUF}_\$TS" && echo "\$f" >> run/.golive_\${NM}_\$TS.moved; done
  mark moved
  echo "OK doi_ten_trang_thai .\${SUF}_\$TS: \$(tr '\n' ' ' < run/.golive_\${NM}_\$TS.moved)"
fi
# [OPS6 T5/A-02] DOI VON qua gl_restart (so live giu, C3_CAPITAL moi != cu): dat lai dinh C6/A40 TRUOC start (HA von: bat buoc, tranh DD gia
#   -> FLATTEN gia; TANG von: "dinh tinh tu luc pilot bat" GOLIVE_SCENARIO s5.2 - dinh cu cao hon von moi se lam DD am gia). Loi => env VE von cu
if [ "\$SUF" = none ] && ! ph a02_ok && ! ph a02_fail; then
  CB=\$(sed -n 's/^export C3_CAPITAL=//p' "\$BK" | tail -1); CN=\$(sed -n 's/^export C3_CAPITAL=//p' conf/env.sh | tail -1)
  if awk -v b="\$CB" -v n="\$CN" 'BEGIN{exit !(b ~ /^[0-9]+(\.[0-9]+)?\$/ && n ~ /^[0-9]+(\.[0-9]+)?\$/ && n+0 != b+0)}'; then
    echo "INFO a02: DOI VON C3_CAPITAL \$CB -> \$CN => dat lai dinh C6/A40 TRUOC start"
    if a02_reset "\${NM}_\$TS" "\$PY"; then mark a02_ok
    else \cp -f "\$BK" conf/env.sh; sed -i '/^env_ok\$/d' "\$PH"; mark a02_fail; echo "FAIL a02_doi_von_khong_dat_lai_duoc_dinh (C3_CAPITAL \$CB -> \$CN) => env.sh VE backup GOC (von cu \$CB, khop dinh), start lai von cu"; fi
  fi
fi
ph "START_LINE=.*" || mark "START_LINE=\$(( \$(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
echo "START_LINE=\$(sed -n 's/^START_LINE=//p' "\$PH" | tail -1)"
pgrep -f "\$PP" >/dev/null || bin/daemon.sh start
mark started
sleep 8
P=\$(pgrep -f "\$PP" | head -1)
[ -n "\$P" ] && echo "OK started pid=\$P lstart=\$(ps -o lstart= -p \$P)" || echo "FAIL khong_thay_process_sau_start"
echo END_RS
EOF2
  } | s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $GLR_EB $GLR_NADD $WD_PAUSE $WD_PAUSE_MAX_S $$ $GL_NAME ${GLR_SUF:-none} $GLR_KS $PY242"
}
gl_restart() {
  local envadd=$1 suf=$3 ks=${4:-0}
  GLR_FILES=$2
  GLR_NADD=$(echo "$envadd" | wc -l); GLR_EB=$(echo "$envadd" | base64 -w0); GLR_SUF=$suf; GLR_KS=$ks
  PAUSE_TOK="C3GOLIVE_${GL_NAME} TS=$TS pid=$$"
  gl_once_resume restart _gl_restart_rx RS END_RS
  RS=$(printf '%s\n' "$RS" | grep -vx END_RS)
  echo "$RS"
  SL=$(echo "$RS" | sed -n 's/^START_LINE=//p' | tail -1); SL=${SL:-1}
  local lb; lb=$(echo "$RS" | sed -n 's/^LEGACY_TRUOC_STOP=\([0-9][0-9]*\)$/\1/p' | tail -1)   # [R4r] so LEGACY NGAY truoc stop
  if [ -n "$lb" ] && [ -n "${L0:-}" ] && [ "${L0:-}" != SKIP ]; then [ "$lb" != "$L0" ] && say "INFO LEGACY truoc stop=$lb (luc kiem truoc: $L0) => hau kiem so voi $lb"; L0=$lb; fi
}
# gl_restart_unknown : [WAVE1 B-02] RS bao trang thai KHONG RO (ssh dut, doc lai khong duoc) => KHONG duoc noi "khong doi gi"
gl_restart_unknown() { echo "$RS" | grep -q '^FAIL ssh_restart_loi_trang_thai_khong_ro'; }
# gl_rollback <hau to> [dry|live] [C3_CAPITAL ky vong] : stop, env.sh ve ban backup GOC cua TS, trang thai doi ten tra lai (ban moi ->
#   .rbnew_TS), start. In RB. [WAVE1 B-02] IDEMPOTENT (marker run/.golive_<NM>_<TS>.rbphase); sau start KIEM THAT: process env
#   LIVE_ADAPTER + env.sh + dong log "khoi dong adapter=" cua JVM moi (cho toi RB_LOG_WAIT_S) = ky vong (+ C3_CAPITAL neu cho).
#   Dung => go KILL_SWITCH cua minh (micro: dry). SAI / khong xac nhan duoc => GIU/DAT run/KILL_SWITCH + "FAIL adapter_sau_rollback"
#   (nguoi goi: KHAN, KHONG go co monitor). Tra 0 chi khi END_RB va khong FAIL.
_gl_rollback_rx() {
  { printf '%s\n' "$GL_A02_FN"; cat <<'EOF'
A=$1; TS=$2; PAUSE=$3; NM=$4; SUF=$5; EXP=$6; ECAP=$7; LW=$8; LP=$9; PY=${10:-}; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
RP=run/.golive_${NM}_$TS.rbphase; BK=conf/env.sh.bak_${NM}_$TS
ph() { grep -qx "$1" "$RP" 2>/dev/null; }
mark() { echo "$1" >> "$RP"; }
[ -f "$BK" ] || { echo "FAIL thieu_backup_env"; echo END_RB; exit 0; }
if ! ph rb_started; then
  bin/daemon.sh stop
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
  # [OPS6 T5/A-02] rollback DOI VON (C3_CAPITAL backup != env.sh hien tai; thuong la HA von) SAU KHI JVM von moi DA start (pha 'started'
  #   cua restart cung TS): dinh C6/A40 dang theo von MOI => dat lai TRUOC start. Khong dat lai duoc => KHONG doi von: env.sh GIU von moi
  #   (khop dinh) + KS cua minh.
  A02F=0
  if [ "$SUF" = none ] && ! ph rb_a02; then
    CN=$(sed -n 's/^export C3_CAPITAL=//p' conf/env.sh | tail -1); CB=$(sed -n 's/^export C3_CAPITAL=//p' "$BK" | tail -1)
    if grep -qx started "run/.golive_${NM}_$TS.phase" 2>/dev/null \
       && awk -v b="$CB" -v n="$CN" 'BEGIN{exit !(b ~ /^[0-9]+(\.[0-9]+)?$/ && n ~ /^[0-9]+(\.[0-9]+)?$/ && b+0 != n+0)}'; then
      echo "INFO a02: rollback DOI VON C3_CAPITAL $CN -> $CB sau khi JVM von moi DA chay => dat lai dinh C6/A40 TRUOC start"
      if a02_reset "${NM}_$TS" "$PY"; then mark rb_a02
      else
        A02F=1; echo "${NM} $TS a02_khong_dat_lai_dinh: dung mo moi" >> run/KILL_SWITCH
        echo "FAIL a02_rollback_khong_dat_lai_duoc_dinh => KHONG doi von: env.sh GIU C3_CAPITAL=$CN (khop dinh hien tai), start lai duoi run/KILL_SWITCH (khong mo moi) - owner/MASTER xu ly"
      fi
    else echo "INFO a02: khong can dat lai dinh (JVM von moi chua chay / von khong doi: env.sh $CN -> backup $CB)"; fi
  fi
  if [ "$A02F" = 1 ]; then echo "WARN env_KHONG_khoi_phuc (A-02: giu von moi)"; else \cp -f "$BK" conf/env.sh && echo "OK env_khoi_phuc (backup GOC $BK)"; fi
  if [ "$SUF" != none ] && [ -f run/.golive_${NM}_$TS.moved ] && ! ph rb_files; then
    for f in run/c3live_book.json run/c3live_dry_state.json run/c3live_ledger.csv run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/c3live_killsw_peak run/killsw_latch.json; do
      [ -e "$f" ] && mv -f "$f" "$f.rbnew_$TS"
    done
    for f in $(cat run/.golive_${NM}_$TS.moved); do [ -e "$f.${SUF}_$TS" ] && mv -f "$f.${SUF}_$TS" "$f"; done
    mark rb_files
    echo "OK trang_thai_tra_lai ($(tr '\n' ' ' < run/.golive_${NM}_$TS.moved))"
  fi
  ph "RB_START_LINE=.*" || mark "RB_START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
  bin/daemon.sh start; mark rb_started; sleep 8
else
  echo "INFO rollback da start o lan truoc (chay lai sau ssh dut) — chi KIEM"
  pgrep -f "$PP" >/dev/null || { bin/daemon.sh start; sleep 8; }
fi
SL=$(sed -n 's/^RB_START_LINE=//p' "$RP" | tail -1); SL=${SL:-1}
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
PA=$(echo "$E" | sed -n 's/^LIVE_ADAPTER=//p' | tail -1); PC=$(echo "$E" | sed -n 's/^C3_CAPITAL=//p' | tail -1)
SA=$(sed -n 's/^export LIVE_ADAPTER=//p' conf/env.sh | tail -1)
echo "ENV_LIVE_ADAPTER=$PA ENV_C3_CAPITAL=$PC ENVSH_LIVE_ADAPTER=$SA"
W=0; AL=""
while :; do
  AL=$(tail -n +$SL logs/full.log 2>/dev/null | grep -a 'khoi dong adapter=' | tail -1 | grep -aoE 'adapter=(LIVE|DRY)' | cut -d= -f2)
  [ -n "$AL" ] || [ "$W" -ge "$LW" ] && break
  sleep "$LP"; W=$((W + LP))
done
echo "LOG_ADAPTER=${AL:-chua_thay_sau_${W}s}"
EU=$(echo "$EXP" | tr 'a-z' 'A-Z'); OKA=1
[ -n "$P" ] && [ "$PA" = "$EXP" ] && [ "$SA" = "$EXP" ] && [ "$AL" = "$EU" ] || OKA=0
[ "$ECAP" = none ] || [ "$PC" = "$ECAP" ] || OKA=0
if [ "$OKA" = 1 ]; then
  echo "OK adapter_sau_rollback=$EXP (process + env.sh + log JVM moi)"
  [ "$EXP" = dry ] && grep -q "^${NM} $TS " run/KILL_SWITCH 2>/dev/null && [ "$(grep -vc "^${NM} $TS " run/KILL_SWITCH)" = 0 ] && mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_$TS && echo "OK KILL_SWITCH_cua_minh_go"
else
  echo "${NM} $TS rollback_adapter_sai: dung mo moi" >> run/KILL_SWITCH   # [VONG3 F1] APPEND: khong bao gio nuot/ghi de dong KS khac
  echo "FAIL adapter_sau_rollback (ky vong $EXP${ECAP:+/$ECAP}: process=$PA cap=$PC env.sh=$SA log=${AL:-?}) — run/KILL_SWITCH $([ -e run/KILL_SWITCH ] && echo DANG_DAT || echo KHONG_DAT_DUOC)"
fi
grep -q "^C3GOLIVE_${NM} TS=$TS " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"
[ -e "$PAUSE" ] && echo "WARN PAUSE_con (token khac)" || echo "OK PAUSE_go"
echo END_RB
EOF
  } | s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $WD_PAUSE $GL_NAME $GLB_SUF $GLB_EXP ${GLB_CAP:-none} $RB_LOG_WAIT_S $RB_LOG_POLL_S $PY242"
}
gl_rollback() {
  GLB_SUF=${1:-none}; GLB_EXP=${2:-dry}; GLB_CAP=${3:-}
  gl_once_resume rollback _gl_rollback_rx RB END_RB
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
# [A1 C-1] mon = v3/account + scope (khong sapi / multiAssets / dual): 5 + 5 + 40 + 40 = 90 weight IP / luot (golive_monitor).
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
def call(base, path, w=0, qs=''):
    q = (qs + '&' if qs else '') + 'timestamp=%d&recvWindow=10000' % int(time.time() * 1000)
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
def readarmed():
    # [OPS5 muc 1] cum c3 DA arm (armed=true) trong so - doi chieu lenh stop/trailing c3 tren san
    try:
        bk = json.load(open(bookf, encoding='utf-8'))
    except FileNotFoundError:
        return []
    except Exception:
        return None
    cl = (bk.get('clusters') or []) if isinstance(bk, dict) else []
    return sorted({c['symbol'] for c in cl if isinstance(c, dict) and isinstance(c.get('symbol'), str) and c.get('armed') is True})
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
if mode in ('sub', 'mon'):
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
        if bw is not None and bw != 0:   # [A1 errata2 MIN-4] gia BFUSD (Multi-Assets asset index, weight 1) — chi ghi log
            ci, ji = call(FAPI, '/fapi/v1/assetIndex', 1, 'symbol=BFUSDUSD')
            if isinstance(ji, list) and ji: ji = ji[0]
            if ci == '200' and isinstance(ji, dict):
                print('BFUSD_INDEX=%s' % ji.get('index')); print('BFUSD_BIDRATE=%s' % ji.get('bidRate'))
            else: print('BFUSD_INDEX=?_HTTP%s' % ci)
    if mode == 'sub':
        code, j = call(FAPI, '/fapi/v1/multiAssetsMargin', 30)
        if code == '200' and isinstance(j, dict) and 'multiAssetsMargin' in j: print('MULTI=' + b(j['multiAssetsMargin']))
        else: ok = False; print('ERR_MULTI=HTTP%s' % code)
        code, j = call(FAPI, '/fapi/v1/positionSide/dual', 30)
        if code == '200' and isinstance(j, dict) and 'dualSidePosition' in j: print('DUAL=' + b(j['dualSidePosition']))
        else: ok = False; print('ERR_DUAL=HTTP%s' % code)
if mode in ('scope', 'sub', 'mon'):
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
    ar = readarmed()   # [OPS5 muc 1]
    print('C3_BOOK_LIST=' + ','.join(sorted(sy for sy, q in c3.items() if q > 0 or sy in unres)))
    print('C3_ARMED_SYMS=' + ('?' if ar is None else ','.join(ar)))
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
        print('ORD_C3_SYMS=' + ','.join(sorted({str(o.get('symbol')) for o in oo if str(o.get('clientOrderId', '')).startswith(CIDOK)})))   # [OPS5 muc 1]
    code, ao = call(FAPI, '/fapi/v1/openAlgoOrders', 40)
    if isinstance(ao, dict): ao = ao.get('orders', ao.get('rows', []))
    if code != '200' or not isinstance(ao, list): ok = False; print('ERR_ALGO=HTTP%s' % code)
    else:
        non = [o.get('symbol') for o in ao if not str(o.get('clientAlgoId', '')).startswith(CIDOK)]
        print('ALGO_TOTAL=%d' % len(ao)); print('ALGO_NONC3=%d %s' % (len(non), ','.join(non[:8])))
        print('ALGO_C3=%d' % (len(ao) - len(non)))
        print('ALGO_C3_SYMS=' + ','.join(sorted({str(o.get('symbol')) for o in ao if str(o.get('clientAlgoId', '')).startswith(CIDOK)})))   # [OPS5 muc 1]
    print('API_OK=%d' % (1 if ok else 0))
if mode == 'lev':
    # [OPS5 muc 3] CHI DOC: v3/account (5) + v1/symbolConfig (5, moi symbol) = 10 weight IP. Universe = run/c3live_exchangeInfo.json
    #   (TRADING, USDT, PERPETUAL); thieu file => moi symbol symbolConfig tra ve.
    code, ac = call(FAPI, '/fapi/v3/account', 5)
    print('ACC_HTTP=' + code)
    if code == '200' and isinstance(ac, dict):
        print('TMB=%s' % ac.get('totalMarginBalance')); print('AVAIL=%s' % ac.get('availableBalance'))
    else:
        ok = False; print('ERR_ACC=HTTP%s' % code)
    uni = None
    try:
        ex = json.load(open('run/c3live_exchangeInfo.json', encoding='utf-8'))
        sl = ex.get('symbols') if isinstance(ex, dict) else None
        uni = sorted(x['symbol'] for x in (sl or []) if isinstance(x, dict) and isinstance(x.get('symbol'), str)
                     and x.get('status') == 'TRADING' and x.get('quoteAsset') == 'USDT' and x.get('contractType') == 'PERPETUAL')
    except Exception as e:
        print('LEV_UNI_ERR=' + type(e).__name__)
    code, sc = call(FAPI, '/fapi/v1/symbolConfig', 5)
    print('LEV_HTTP=' + code)
    if code != '200' or not isinstance(sc, list):
        ok = False; print('ERR_LEV=HTTP%s' % code)
    else:
        m = {x['symbol']: x for x in sc if isinstance(x, dict) and isinstance(x.get('symbol'), str)}
        u = uni if uni else sorted(m)
        print('LEV_UNI=%d %s' % (len(u), 'exchangeInfo' if uni else 'symbolConfig'))
        miss = [sy for sy in u if sy not in m]
        print('LEV_MISS=%d %s' % (len(miss), ','.join(miss[:8])))
        for sy in u:
            if sy in m:
                x = m[sy]; print('LEVSYM=%s:%s:%s:%s' % (sy, x.get('leverage'), x.get('marginType'), x.get('maxNotionalValue')))
    print('API_OK=%d' % (1 if ok else 0))
if mode in ('sub', 'mon', 'lev'):
    print('W_NOMINAL=%d' % W['n']); print('W_USED_1M=%s' % (W['used'] or '?'))
k = s = None
print('END_API')
PYEOF
EOF
}
av() { echo "$API" | sed -n "s/^$1=//p" | head -1; }

# gl_sub_eval <can_sach 1|0> : [ADD4 §2] danh gia $API (gl_api242 sub) => SUBV=DAT|TRUOT, SUBWHY (ly do). can_sach=1: them 0 vi the,
#   0 lenh mo, 0 algo (luc micro_on). multiAssetsMargin CHI ghi lai (jar r4t/r4u3: AccountModeGuard.globalPolicy(false,false) khong doi hoi).
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
  [ "$C3_ACCOUNT" != SUB ] || [ "$x" = "$SUB_KEY_SHA8" ] || _sf "key_sha8=${x:-?}_KHAC_key_tk_con_da_dang_ky_${SUB_KEY_SHA8}"   # [WAVE1 A-03]
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

# gl_c3_seen <SL> <POS_SIG truoc restart> [TS: leg cua so .dry_TS khong tinh] : [R4q MAJ-1] doc LAI 242 NGAY luc quyet (so + audit lenh c3 + san qua duong chi doc).
#   In dong + "VERDICT=NONE" CHI khi MOI nguon doc duoc tron ven va: so 0 cum, 0 dong [C3-LIVE-ORDER] (tru SKIP) tu START_LINE
#   (log chua xoay), san 0 lenh/algo c3, chu ky vi the = truoc restart. Thieu/khong chac => UNKNOWN (coi nhu DA co lenh); co => SEEN.
gl_c3_seen() {
  local R why="" unk=""
  R=$(s242in "bash -s -- $A $1 ${3:-none}" <<'EOF'
A=$1; SL=$2; TSD=${3:-none}; cd "$A" || { echo "ERR=cd"; echo END_SEEN; exit 0; }
L=logs/full.log; N=$(wc -l < $L 2>/dev/null || echo 0)
[ "$N" -ge "$SL" ] && echo "LOG_OK=1" || echo "LOG_OK=0"
echo "AUDIT_C3=$(tail -n +$SL $L 2>/dev/null | grep -a '\[C3-LIVE-ORDER\]' | grep -avc 'status=SKIP')"
B=run/c3live_book.json
DB=run/c3live_book.json.dry_$TSD
if [ ! -e $B ]; then echo "BOOK_CUM=0"
elif [ ! -r $B ]; then echo "ERR=book_khong_doc_duoc"
elif [ "$TSD" != none ] && [ -f $DB ]; then   # [ERRATA 2] leg mang cid cua so dry (.dry_<TS>) KHONG tinh la lenh c3 live
  NC=$(grep -o '"cid":"[^"]*"' $B | sort -u | grep -vxFf <(grep -o '"cid":"[^"]*"' $DB | sort -u) | grep -c .)
  [ "$(grep -o '"cid":"' $B | wc -l)" = 0 ] && NC=$(grep -o '"symbol":"' $B | wc -l)
  echo "BOOK_CUM=$NC"; echo "BOOK_CUM_GOM_DRY=$(grep -o '"symbol":"' $B | wc -l)"
else echo "BOOK_CUM=$(grep -o '"symbol":"' $B | wc -l)"; fi
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

# ---------------------------------------------------------------- [WAVE1 D-01] co sizing + DCA grid (LIVE_APPLY_GRID_RATIO / LIVE_DCA_GRID_ENABLED)
# gl_d01_plan <von C3_CAPITAL> : tu $ST (gl_state242: env.sh, thieu => env process, thieu => mac dinh code Configs) tinh budget TUNG leg
#   o U=0 dung cong thuc sim/live khi 2 co BAT: leg_i = von x F_BASE / sum(w) x ratio(i), ratio = w[i] x SCALE (FIX_B2) | w[i]/sum(w) x SCALE,
#   tran 4,5 % von (LiveProfileC3.SIZE_CAP_OF_EQUITY); throttle (1 - U/U_MAX) chi GIAM tiep. In bang D01_LEG<i> + tom tat D01_L0 / D01_MINLEG / D01_MINCAP.
#   Tra 1 khi leg0 < MIN_LEG_BUDGET (=> C3LiveEntry BUDGET_SMALL: 0 lenh, im lang) — nguoi goi TU CHOI kem von toi thieu.
gl_d01_v() { local v; v=$(sv "ENVSH_$1"); [ -n "$v" ] || v=$(sv "ENV_$1"); [ -n "$v" ] || v=$2; echo "$v"; }
gl_d01_plan() {
  local cap=$1 fb w sc fx lv out rc
  local um; um=$(gl_d01_v SIM_U_MAX 0.60)
  fb=$(gl_d01_v SIM_F_BASE 0.03); w=$(gl_d01_v DCA_GRID_WEIGHTS 1,1,3,8); sc=$(gl_d01_v DCA_GRID_SCALE 1.0)
  fx=$(gl_d01_v SIM_FIX_B2 true); lv=$(gl_d01_v DCA_GRID_LEVELS -0.50,-0.75,-0.90)
  out=$(awk -v C="$cap" -v FB="$fb" -v W="$w" -v SC="$sc" -v FX="$fx" -v LV="$lv" -v MB="$MIN_LEG_BUDGET" -v UM="$um" 'BEGIN{
    n=split(W,w,","); m=split(LV,l,","); t=0; for(i=1;i<=n;i++) t+=w[i]; if (t<=0) t=1
    fixb2=(tolower(FX)!="false"); capamt=0.045*C; mn=1e18
    printf "D01_THAMSO=von=%s F_BASE=%s weights=%s sum=%s SCALE=%s FIX_B2=%s levels=%s tran_4.5%%=%.2f\n", C, FB, W, t, SC, (fixb2?"true":"false"), LV, capamt
    for(i=0;i<=m;i++){ wi=(i+1<=n)?w[i+1]:0; r=(wi<=0)?0:(fixb2?wi*SC:wi/t*SC); b=C*FB/t*r; if (b>capamt) b=capamt
      lvl=(i==0)?"mo_cum":sprintf("DCA%d@%s",i,l[i]); printf "D01_LEG%d=%.2f (%s ratio=%s, U=0)\n", i, b, lvl, r
      if (i==0) l0=b; if (b>0 && b<mn) mn=b }
    if (mn==1e18) mn=0
    ml=(mn>0)?MB/mn*C:0
    printf "D01_L0=%.2f\nD01_MINLEG=%.2f\nD01_MINCAP=%d\n", l0, mn, int(ml+0.999)
    printf "D01_UCAO=U_MAX=%s leg0 x (1-U/U_MAX): U=0.30 => %.2f | U=0.45 => %.2f | U=0.55 => %.2f; BUDGET_SMALL (<%s) khi U > %.3f\n", UM, l0*(1-0.30/UM), l0*(1-0.45/UM), l0*(1-0.55/UM), MB, (l0>MB)?UM*(1-MB/l0):0
    printf "D01_NOTIONAL=U=0, moi leg: >= 5 can von >= %d; >= 20 (ETH/BCH/LTC/ETC/LINK) can >= %d; >= 50 (BTC) can >= %d; throttle (1-U/U_MAX) giam tiep\n", (mn>0)?int(5/mn*C+0.999):0, (mn>0)?int(20/mn*C+0.999):0, (mn>0)?int(50/mn*C+0.999):0
    exit (l0+1e-9 < MB) ? 1 : 0 }'); rc=$?
  D01=$out
  echo "$out"
  return $rc
}
# [WAVE1 D-01] doan hau kiem (chay tren 242 trong gl_chk_common): process env + log khoi dong JVM moi co 2 co BAT (static init
#   LiveDcaGridC3 chay luc C3LiveRuntime dung entry => in ngay luc start) + khong co canh bao "TAT".
GL_D01_CHK='envk LIVE_APPLY_GRID_RATIO=true; envk LIVE_DCA_GRID_ENABLED=true
[ "$(T "\[LIVE-SIZING\] LIVE_APPLY_GRID_RATIO=true")" -ge 1 ] && echo "OK LIVE-SIZING_BAT" || echo "WAIT LIVE-SIZING_BAT (chua thay log [LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true)"
[ "$(T "\[LIVE-DCA-GRID\] LIVE_DCA_GRID_ENABLED=true profileC3=true .*applyRatio=true")" -ge 1 ] && echo "OK LIVE-DCA-GRID_BAT" || echo "WAIT LIVE-DCA-GRID_BAT (chua thay log [LIVE-DCA-GRID] ...=true profileC3=true ... applyRatio=true)"
[ "$(T "\[LIVE-DCA-GRID\] LIVE_APPLY_GRID_RATIO TAT")" = 0 ] || echo "FAIL LIVE-DCA-GRID_sizing_TAT"
[ "$(T "\[LIVE-DCA-GRID\] profile C3 TAT")" = 0 ] || echo "FAIL LIVE-DCA-GRID_profile_C3_TAT"'
