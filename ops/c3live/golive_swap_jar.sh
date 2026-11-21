#!/usr/bin/env bash
# =============================================================================
# golive_swap_jar.sh - [HOTFIX-KS 2026-11-19] DOI JAR v_t_m khi DANG MICRO-LIVE: r4u3fin2 (6418..) -> hotfix-ks (01cfbb43..)
#   = jar live + DUY NHAT ban va deadlock KillSwitchEngine<->C3MainEquity (commit 4fdda6f8). KHONG doi env, KHONG doi trang thai/so.
#   Chay tren ORACLE (owner), 1 lenh ($OPS = thu muc chua script nay, HEAD co trong deploy/gates/A1_APPROVED_OPS.commit):
#     DRY=1 bash $OPS/golive_swap_jar.sh           # chi kiem (Oracle + 242 CHI DOC) + in ke hoach, KHONG ghi gi len 242
#     bash $OPS/golive_swap_jar.sh                 # go YES (khung :10-:44) => doi jar
#     MODE=rollback bash $OPS/golive_swap_jar.sh   # quay ve jar cu r4u3fin2 (cung quy trinh, chieu nguoc)
# Kiem truoc (sai => TU CHOI, khong doi gi): pin m1 + manifest M5; jar dich tren Oracle dung md5 ghim; 242: 1 process, jar DANG chay =
#   jar nguon (= jar dich => "DA XONG", exit 0), adapter=live (process + env.sh), c3_live, C3_CAPITAL process = env.sh, latch NONE,
#   KHONG run/KILL_SWITCH, KHONG PAUSE watchdog, khong canary/soak (242 + Oracle), RAM/dia, C3_ACCOUNT=SUB: file key 600 + sha8 dang ky,
#   process LIVE_C3_KEYS_FILE = file key, C3_EXCLUDE_LEGACY_HELD=false, 2 co sizing/DCA = true.
# Trinh tu: chep jar dich len 242 (.hfks_<TS>, kiem md5, chmod 600) TRUOC khi dung bot -> [1 ssh] dat run/KILL_SWITCH (token rieng,
#   KHONG ghi de KILL_SWITCH nguoi khac) -> PAUSE watchdog (token, tu go sau WD_PAUSE_MAX_S) -> stop -> backup jar (.bak_<NM>_<TS> + .md5)
#   -> cai jar dich (kiem md5) -> start -> hau kiem (nhu golive_micro_on): 1 process, jar = dich, env live/C3_CAPITAL/push/key/EXCL,
#   adapter=LIVE + c3_capital trong log JVM moi, user stream, recon khoi dong ok, latch NONE, 0 KHAN, runtime, scope tk con 0 vi the ngoai c3,
#   0 C3-EXCL-FORCE, [LIVE-SIZING]/[LIVE-DCA-GRID]/[MINUTE-FIN] BAT, LEGACY managed khong doi, file key 600 + sha8, KILL_SWITCH cua minh con,
#   chua PUSH ON -> go KILL_SWITCH cua minh -> cho "PUSH doi trang thai -> ON" -> go PAUSE.
# Buoc nao TRUOT sau khi dung bot => ROLLBACK TU DONG ve jar nguon (backup) + start + hau kiem lai: DAT => go KILL_SWITCH cua minh
#   (exit 1); TRUOT / khong xac nhan => GIU run/KILL_SWITCH + KHAN Telegram (exit 2). Vi the dang mo KHONG bi dong (chi dung mo MOI).
#   Moi buoc co tac dung phu chay 1 lan + doc lai 242 khi ssh dut (gl_once_resume, marker pha run/.golive_<NM>_<TS>.phase|.rbphase).
#   SIGHUP (dong terminal / rot ssh toi Oracle) bi bo qua tu dau; sau YES bo qua ca INT/TERM => script chay toi trang thai cuoi.
# Ma thoat: 0 XONG / DA XONG / DRY PASS | 1 TU CHOI / da rollback ve jar nguon (DAT) | 2 KHAN (can owner/MASTER).
# Bien (test): SJ_OLD_MD5 SJ_NEW_MD5 SJ_OLD_JAR SJ_NEW_JAR SCP_242 RHOST + bien golive_lib.sh
# [OPS6 T3/H1] run/KILL_SWITCH ghi THEO DONG: script CHI them dong token "<NM> <TS> ..." cua minh (>>, khong ghi de) va CHI go file khi MOI dong
#   la cua minh; co dong nguoi khac (owner drain / autodrain / monitor KHAN) => GIU NGUYEN ca file (ke ca dong cua minh), bao KHAN (bot DRAIN).
# [OPS6 T4] MODE=rollback ve jar cu r4u3fin2 (SJ_OLD_MD5 64180356) => jar != NJ_MD5 (golive_lib) => micro_on/pilot_on/make_gate_pilot TU CHOI.
# =============================================================================
set -uo pipefail
trap '' HUP
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
SJ_OLD_MD5=${SJ_OLD_MD5:-641803565297d4065d90245e04a00f11}   # r4u3fin2 (5e10325b) - jar micro-live tu 19/11 09:31
SJ_NEW_MD5=${SJ_NEW_MD5:-01cfbb4324fb4a10b615dc3c976ddc73}   # r4u3fin2 + KillSwitchEngine 4fdda6f8 (v1.2/hotfix-ks)
SJ_OLD_JAR=${SJ_OLD_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2}
SJ_NEW_JAR=${SJ_NEW_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2_hotfixks}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
SJ_WD_LOCK_WAIT_S=${SJ_WD_LOCK_WAIT_S:-300}   # [A1 MAJOR 1a] cho luot watchdog h242 dang chay (flock .lock canh PAUSE) toi da (s)
MODE=${MODE:-swap}
case "$MODE" in
  swap)     FROM_MD5=$SJ_OLD_MD5; TO_MD5=$SJ_NEW_MD5; TO_JAR=$SJ_NEW_JAR; DIRTXT="r4u3fin2 -> hotfix-ks" ;;
  rollback) FROM_MD5=$SJ_NEW_MD5; TO_MD5=$SJ_OLD_MD5; TO_JAR=$SJ_OLD_JAR; DIRTXT="hotfix-ks -> r4u3fin2 (ROLLBACK)" ;;
  *) echo "MODE phai la swap | rollback"; exit 1 ;;
esac
# gl_init voi tee BEN (bo qua HUP, loi ghi terminal khong lam chet script)
GL_NAME=golive_swap_jar; NM=$GL_NAME
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
mkdir -p "$LOGDIR"; LOG=$LOGDIR/${GL_NAME}_${TS}.log
PAUSE_TOK="C3GOLIVE_${NM} TS=$TS pid=$$"   # = TOK trong _sj_restart_rx (gl_pause_clear chi go PAUSE cua lan nay)
exec > >(trap '' HUP INT TERM PIPE; exec tee --output-error=warn -a "$LOG") 2>&1
say "=== $GL_NAME TS=$TS MODE=$MODE ($DIRTXT) DRY=$DRY nguon=$FROM_MD5 dich=$TO_MD5 ==="
[ "$C3_ACCOUNT" = SUB ] || die "chi ho tro C3_ACCOUNT=SUB (micro tk con)"
[[ "$FROM_MD5" =~ ^[0-9a-f]{32}$ ]] && [[ "$TO_MD5" =~ ^[0-9a-f]{32}$ ]] && [ "$FROM_MD5" != "$TO_MD5" ] || die "pin md5 khong hop le"
[ -f "$TO_JAR" ] || die "khong thay jar dich $TO_JAR"
[ "$(md5sum < "$TO_JAR" | cut -c1-32)" = "$TO_MD5" ] || die "md5 jar dich $TO_JAR KHAC pin $TO_MD5"
say "OK jar dich tren Oracle $TO_JAR md5=$TO_MD5 ($(stat -c %s "$TO_JAR") byte)"
LOCKD=$LOGDIR/.golive_swap_jar.lock.d
if ! mkdir "$LOCKD" 2>/dev/null; then
  _lp=$(cat "$LOCKD/pid" 2>/dev/null)
  if [ -n "$_lp" ] && kill -0 "$_lp" 2>/dev/null; then die "dang co 1 golive_swap_jar khac chay (pid $_lp)"; fi
  rm -rf "$LOCKD"; mkdir "$LOCKD" 2>/dev/null || die "khong lay duoc khoa $LOCKD"
fi
echo $$ > "$LOCKD/pid"; trap 'rm -rf "$LOCKD"' EXIT
RJN=$A/target/binance-java-sdk-1.2.4.jar.hfks_$TS
EXW=false
# ---------------------------------------------------------------- kiem truoc (CHI DOC)
pre_check() {
  gl_read_state
  F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
  chk "1 process bot (co $(sv NPROC))" "[ '$(sv NPROC)' = 1 ]"
  if [ "$(sv JAR_MD5)" = "$TO_MD5" ] && [ "$(sv NPROC)" = 1 ]; then
    DONE_ALREADY=1
    if [ "$(sv KILLSW_FILE)" = 0 ]; then say "=== DA XONG: jar dang chay = dich $TO_MD5 ($DIRTXT da lam truoc do). Khong doi gi."
    else DONE_ALREADY=2; say "!! jar dang chay = dich $TO_MD5 (da doi) NHUNG run/KILL_SWITCH DANG DAT (bot drain, khong mo moi) - lan truoc dung giua chung? Kiem: bash $_OPS/golive_monitor.sh roi MODE=undrain bash $_OPS/golive_live_off.sh"; fi
    return 0
  fi
  chk "jar dang chay $(sv JAR_MD5) = nguon $FROM_MD5" "[ '$(sv JAR_MD5)' = '$FROM_MD5' ]"
  chk "dang MICRO-LIVE: c3_live adapter=live (process + env.sh)" "[ '$(sv ENV_LIVE_PROFILE)' = c3_live ] && [ '$(sv ENV_LIVE_ADAPTER)' = live ] && [ '$(sv ENVSH_LIVE_ADAPTER)' = live ]"
  CAP0=$(sv ENV_C3_CAPITAL)
  chk "C3_CAPITAL process '$CAP0' = env.sh '$(sv ENVSH_C3_CAPITAL)' (khong doi von)" "[[ '$CAP0' =~ ^[0-9]+(\.[0-9]+)?\$ ]] && [ '$CAP0' = '$(sv ENVSH_C3_CAPITAL)' ]"
  chk "LIVE_KILLSW_MODE=act" "[ '$(sv ENV_LIVE_KILLSW_MODE)' = act ]"
  chk "latch kill-switch NONE (co: $(sv LATCH))" "[ '$(sv LATCH)' = NONE ] || [ '$(sv LATCH)' = NOFILE ]"
  chk "KHONG co run/KILL_SWITCH (co = dang drain/KHAN: xu ly truoc, script KHONG ghi de)" "[ '$(sv KILLSW_FILE)' = 0 ]"
  chk "KHONG PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
  chk "khong canary/soak tren 242" "[ '$(sv CANARY_SOAK)' = 0 ]"
  chk "Oracle: khong co tien trinh $CANARY_PAT" "gl_no_canary"
  chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
  chk "dia trong 242 >= 1 GB (jar dich ~100 MB)" "[ '$(sv DISK_K)' -gt 1048576 ] 2>/dev/null"
  chk "file key $KEYS_FILE 600, 2 dong, sha8 $(sv KEYS_FILE_SHA8) = $SUB_KEY_SHA8" "[ '$(sv KEYS_OK)' = 1 ] && [ '$(sv KEYS_PERM)' = 600 ] && [ '$(sv KEYS_FILE_SHA8)' = '$SUB_KEY_SHA8' ]"
  chk "process LIVE_C3_KEYS_FILE = $KEYS_FILE" "[ '$(sv ENV_LIVE_C3_KEYS_FILE)' = '$KEYS_FILE' ]"
  chk "process C3_EXCLUDE_LEGACY_HELD=$EXW" "[ '$(sv ENV_C3_EXCLUDE_LEGACY_HELD)' = $EXW ]"
  chk "process LIVE_APPLY_GRID_RATIO=true + LIVE_DCA_GRID_ENABLED=true" "[ '$(sv ENV_LIVE_APPLY_GRID_RATIO)' = true ] && [ '$(sv ENV_LIVE_DCA_GRID_ENABLED)' = true ]"
  L0=$(sv LEGACY_N); [ -n "$L0" ] || L0=-1
  [ -f "$GL_MON_FLAG" ] && say "INFO co monitor $GL_MON_FLAG (cron golive_monitor dang theo doi; KHONG doi)" || say "WARN khong co co monitor $GL_MON_FLAG (micro_on chua bat? cron monitor khong chay)"
  return 0
}
DONE_ALREADY=0
pre_check
[ "$DONE_ALREADY" = 1 ] && exit 0
[ "$DONE_ALREADY" = 2 ] && { tg "[golive] KHAN TS=$TS swap_jar($MODE): jar da = $TO_MD5 nhung run/KILL_SWITCH DANG DAT (bot drain). Kiem golive_monitor.sh roi MODE=undrain golive_live_off.sh | log $LOG" || :; exit 2; }
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
say "--- se chep jar dich len 242: $RJN (kiem md5, chmod 600) TRUOC khi dung bot"
say "--- se dat run/KILL_SWITCH (token '$NM $TS') -> PAUSE watchdog -> stop -> backup jar (.bak_${NM}_$TS) -> cai jar $TO_MD5 -> start"
say "--- KHONG doi conf/env.sh, KHONG doi so/trang thai run/*, vi the dang mo KHONG bi dong (chi dung mo MOI ~2-8 phut toi khi hau kiem DAT)"
say "--- hau kiem: jar=$TO_MD5, adapter=LIVE c3_capital=$CAP0 key=$KEYS_FILE, stream, recon, latch NONE, 0 KHAN, scope tk con, sizing/DCA/MINUTE-FIN BAT, LEGACY=$L0 => go KILL_SWITCH => PUSH ON"
say "--- rollback 1 lenh sau nay: MODE=$([ "$MODE" = swap ] && echo rollback || echo swap) bash $_OPS/golive_swap_jar.sh"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "DOI JAR v_t_m DANG LIVE ($DIRTXT): $FROM_MD5 -> $TO_MD5. Bot dung ~20-90 s; KHONG mo lenh moi toi khi hau kiem DAT (vi the giu nguyen)."
trap '' INT TERM
gl_time
pre_check
[ "$DONE_ALREADY" = 1 ] && exit 0
[ "$DONE_ALREADY" = 2 ] && exit 2
[ "$F" = 0 ] || die "kiem lai sau YES co muc FAIL (trang thai doi) - khong doi gi"
# ---------------------------------------------------------------- chep jar dich (bot van chay)
$SCP_242 "$TO_JAR" "${RHOST}$RJN" || die "chep jar len 242 loi (bot KHONG dung)"
RM=$(s242 "chmod 600 $RJN && md5sum < $RJN | cut -c1-32") || die "ssh kiem md5 jar loi (bot KHONG dung)"
[ "$RM" = "$TO_MD5" ] || die "md5 jar tren 242 '$RM' KHAC $TO_MD5 (bot KHONG dung)"
say "OK jar dich tren 242 md5=$RM ($RJN, 600)"
# ---------------------------------------------------------------- KILL_SWITCH -> PAUSE -> stop -> backup -> cai -> start (1 lan, idempotent)
_sj_restart_rx() {
  s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $NM $FROM_MD5 $TO_MD5 $WD_PAUSE $WD_PAUSE_MAX_S $$ $RJN $SJ_WD_LOCK_WAIT_S" <<'EOF'
trap '' HUP PIPE   # [A1 m7] ssh dut giua chung: khoi nay VAN chay het (stop -> start), khong de bot tat im lang
{
A=$1; TS=$2; NM=$3; FM=$4; TM=$5; PAUSE=$6; MAXS=$7; JP=$8; RJN=$9; WLW=${10:-300}; cd "$A" || { echo "FAIL cd"; echo END_RS; exit 0; }
exec 8>>"run/.golive_${NM}_$TS.lk"; flock -w 600 8 || { echo "FAIL lan_chay_truoc_cung_TS_van_dang_chay"; echo END_RS; exit 0; }   # chay lai sau ssh dut: cho lan truoc xong
J=target/binance-java-sdk-1.2.4.jar; JB=$J.bak_${NM}_$TS; PH=run/.golive_${NM}_$TS.phase
ph() { grep -qx "$1" "$PH" 2>/dev/null; }
pv() { sed -n "s/^$1=//p" "$PH" 2>/dev/null | tail -1; }
mark() { echo "$1" >> "$PH"; }
m5() { md5sum < "$1" 2>/dev/null | cut -c1-32; }
myks() { grep -q "^$NM $TS " run/KILL_SWITCH 2>/dev/null; }
onlymine() { myks && [ "$(grep -vc "^$NM $TS " run/KILL_SWITCH)" = 0 ]; }
ksoff() { if onlymine; then mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_$TS; elif myks; then echo "WARN KILL_SWITCH_co_dong_nguoi_khac_GIU_NGUYEN (khong go dong cua script khi co dong khac)"; fi; }   # [OPS6 T3/H1]
TOK="C3GOLIVE_${NM} TS=$TS pid=$JP"
pclr() { grep -q "^$TOK " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"; }
if ph started; then
  echo "INFO pha_da_xong_truoc (chay lai sau ssh dut): KHONG stop/start lai"
  echo "OK da_stop"; echo "OK jar_da_thay md5=$TM"; echo "START_LINE=$(pv START_LINE)"; echo "T_STOP=$(pv T_STOP)"; echo "T_START=$(pv T_START)"
  P=$(pgrep -f "$PP" | head -1); [ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process_sau_start"
  [ "$(pgrep -fc "$PP")" = 1 ] && echo "OK dung_1_JVM" || echo "FAIL so_JVM_sau_start=$(pgrep -fc "$PP")"
  echo END_RS; exit 0
fi
if ! ph stopped; then
  if ! myks; then
    [ -e run/KILL_SWITCH ] && { echo "FAIL KILL_SWITCH_khac_dang_dat ($(head -c 60 run/KILL_SWITCH | tr '\n' ' ')) - bot KHONG dung"; echo END_RS; exit 0; }
    echo "$NM $TS hau_kiem: dung mo moi toi khi hau kiem jar moi DAT" >> run/KILL_SWITCH
  fi
  myks && echo "OK KILL_SWITCH_dat_truoc_stop" || { echo "FAIL khong_dat_duoc_KILL_SWITCH (bot KHONG dung)"; echo END_RS; exit 0; }
  if [ -e "$PAUSE" ] && ! grep -q "^$TOK " "$PAUSE" 2>/dev/null; then ksoff; echo "FAIL PAUSE_khac_dang_co ($(head -c 60 "$PAUSE" | tr '\n' ' ')) - bot KHONG dung"; echo END_RS; exit 0; fi
  mkdir -p "$(dirname "$PAUSE")" 2>/dev/null; echo "$TOK t=$(date +%s)" > "$PAUSE" && grep -q "^$TOK " "$PAUSE" 2>/dev/null && echo "OK watchdog_PAUSE token='$TOK'" \
    || { ksoff; pclr; echo "FAIL khong_tao_duoc_PAUSE_watchdog (bot KHONG dung, KILL_SWITCH cua minh da go)"; echo END_RS; exit 0; }   # [A1 m1] fail-closed
  if ! ph pause_timer; then setsid nohup bash -c "sleep $MAXS; grep -q '^$TOK ' '$PAUSE' 2>/dev/null && rm -f '$PAUSE'" > /dev/null 2>&1 < /dev/null 8>&- & mark pause_timer; fi
  # [A1 MAJOR 1a] watchdog chi xet PAUSE o DAU luot: CHO luot dang chay (giu .lock) xong roi moi dung bot
  WL="$(dirname "$PAUSE")/.lock"; W0=$(date +%s)
  if flock -w "$WLW" "$WL" true; then echo "OK watchdog_khong_con_luot_dang_chay (cho $(( $(date +%s) - W0 ))s, $WL)"
  else ksoff; pclr; echo "FAIL watchdog_dang_giu_lock_qua_${WLW}s ($WL) - bot KHONG dung, KILL_SWITCH + PAUSE cua minh da go"; echo END_RS; exit 0; fi
  [ "$(m5 "$RJN")" = "$TM" ] || { ksoff; pclr; echo "FAIL jar_dich_tren_242_sai_md5 (bot KHONG dung, KILL_SWITCH + PAUSE cua minh da go)"; echo END_RS; exit 0; }
  CUR=$(m5 $J); [ "$CUR" = "$FM" ] || { ksoff; pclr; echo "FAIL jar_dang_dung_${CUR}_khac_nguon_$FM (bot KHONG dung)"; echo END_RS; exit 0; }
  echo "LEGACY_TRUOC_STOP=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')"
  ph "T_STOP=.*" || mark "T_STOP=$(date +%s)"
  bin/daemon.sh stop 8>&-
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  if pgrep -f "$PP" >/dev/null; then ksoff; pclr; echo "FAIL van_con_process_sau_stop (jar KHONG doi, KILL_SWITCH + PAUSE cua minh da go)"; echo END_RS; exit 0; fi
  mark stopped
fi
echo "OK da_stop"
if ! ph jar_bak; then
  if [ "$(m5 $J)" = "$FM" ]; then
    { \cp -fp $J $JB && chmod 600 $JB && [ "$(m5 $JB)" = "$FM" ] && echo "$FM" > $JB.md5; } && mark jar_bak || { echo "FAIL backup_jar"; echo END_RS; exit 0; }
  else echo "FAIL jar_sau_stop_khac_nguon_va_chua_backup"; echo END_RS; exit 0; fi
fi
echo "OK backup_jar md5=$FM ($JB)"
if ! ph jar_new; then   # [A1 MAJOR 1b] KHONG ghi de inode jar cu: doi ten (rename nguyen tu) file dich da kiem md5
  if [ "$(m5 $J)" != "$TM" ]; then
    [ "$(m5 "$RJN")" = "$TM" ] && chmod --reference=$J "$RJN" 2>/dev/null; chown --reference=$J "$RJN" 2>/dev/null
    [ "$(m5 "$RJN")" = "$TM" ] && mv -f "$RJN" $J || { echo "FAIL jar_thay_sai (mv)"; echo END_RS; exit 0; }
  fi
  [ "$(m5 $J)" = "$TM" ] && mark jar_new || { echo "FAIL jar_thay_sai"; echo END_RS; exit 0; }
fi
echo "OK jar_da_thay md5=$TM"
ph "START_LINE=.*" || mark "START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
echo "START_LINE=$(pv START_LINE)"
pgrep -f "$PP" >/dev/null || bin/daemon.sh start 8>&-
ph "T_START=.*" || mark "T_START=$(date +%s)"
mark started
echo "T_STOP=$(pv T_STOP)"; echo "T_START=$(pv T_START)"
sleep 8
P=$(pgrep -f "$PP" | head -1); NJ=$(pgrep -fc "$PP")
[ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process_sau_start"
[ "$NJ" = 1 ] && echo "OK dung_1_JVM" || echo "FAIL so_JVM_sau_start=$NJ"   # [A1 MAJOR 1d]
echo END_RS
}
EOF
}
# ---------------------------------------------------------------- rollback ve jar nguon (1 lan, idempotent)
_sj_rollback_rx() {
  s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $NM $FROM_MD5 $TO_MD5" <<'EOF'
trap '' HUP PIPE   # [A1 m7]
{
A=$1; TS=$2; NM=$3; FM=$4; TM=$5; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
exec 8>>"run/.golive_${NM}_$TS.lk"; flock -w 600 8 || { echo "FAIL lan_chay_truoc_cung_TS_van_dang_chay"; echo END_RB; exit 0; }
J=target/binance-java-sdk-1.2.4.jar; JB=$J.bak_${NM}_$TS; RP=run/.golive_${NM}_$TS.rbphase
ph() { grep -qx "$1" "$RP" 2>/dev/null; }
mark() { echo "$1" >> "$RP"; }
m5() { md5sum < "$1" 2>/dev/null | cut -c1-32; }
grep -q "^$NM $TS " run/KILL_SWITCH 2>/dev/null || echo "$NM $TS rollback: dung mo moi" >> run/KILL_SWITCH   # [OPS6 T3/H1] APPEND dong cua minh (KS nguoi khac giu)
[ -e run/KILL_SWITCH ] && echo "OK KILL_SWITCH_dang_dat" || echo "WARN khong_dat_duoc_KILL_SWITCH"
if ! ph rb_started; then
  bin/daemon.sh stop 8>&-
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
  if [ "$(m5 $J)" != "$FM" ] && [ -f $JB ] && [ "$(m5 $JB)" = "$FM" ]; then   # [A1 1b] cp ra file tam roi mv (khong ghi de inode)
    \cp -p $JB $J.rbtmp_$TS && [ "$(m5 $J.rbtmp_$TS)" = "$FM" ] && mv -f $J.rbtmp_$TS $J; rm -f $J.rbtmp_$TS
  fi
  JN=$(m5 $J)
  if [ "$JN" = "$FM" ]; then echo "OK jar_khoi_phuc md5=$FM"
  elif [ "$JN" = "$TM" ]; then echo "FAIL jar_khong_khoi_phuc_duoc (van la $TM) - van START de bot khong tat (KILL_SWITCH dat)"
  else echo "FAIL jar_hong_md5=$JN - KHONG start"; echo END_RB; exit 0; fi
  grep -q '^RB_START_LINE=' "$RP" 2>/dev/null || mark "RB_START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
  bin/daemon.sh start 8>&-; mark rb_started; sleep 8
else
  echo "INFO rollback da start o lan truoc (chay lai sau ssh dut) - chi KIEM"
  pgrep -f "$PP" >/dev/null || { bin/daemon.sh start 8>&-; sleep 8; }
fi
echo "RB_START_LINE=$(sed -n 's/^RB_START_LINE=//p' "$RP" | tail -1)"
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
echo "JAR_NOW=$(m5 $J)"
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK dung_1_JVM" || echo "FAIL so_JVM_sau_start=$(pgrep -fc "$PP")"
echo END_RB
}
EOF
}
# ---------------------------------------------------------------- hau kiem (nhu golive_micro_on) voi jar ky vong $1, START_LINE $2
CHK_JAR=$TO_MD5
CHK() { gl_chk_common "$SL" "$L0" '
envk LIVE_ADAPTER=live; envk C3_CAPITAL='"$CAP0"'; envk SHADOW_NO_PUSH=false; envk LIVE_ENTRY_ENABLED=true; envk LIVE_C3_KEYS_FILE='"$KEYS_FILE"'; envk C3_EXCLUDE_LEGACY_HELD='"$EXW"'
'"$GL_D01_CHK"'
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = '"$CHK_JAR"' ] && echo "OK file_jar='"$CHK_JAR"'" || echo "FAIL file_jar_md5_khac_'"$CHK_JAR"'"
JFD=$(find /proc/$P/fd -lname "*binance-java-sdk*.jar*" 2>/dev/null | head -1); JPM=$( [ -n "$JFD" ] && md5sum < "$JFD" 2>/dev/null | cut -c1-32)
if [ -z "$JPM" ]; then echo "WAIT jar_process_mo_chua_thay (/proc/$P/fd)"; elif [ "$JPM" = '"$CHK_JAR"' ]; then echo "OK jar_PROCESS_dang_mo='"$CHK_JAR"'"; else echo "FAIL jar_PROCESS_dang_mo=${JPM}_khac_'"$CHK_JAR"'"; fi
EQV=$(echo "$E" | sed -n "s/^KILLSW_EQ_POLL_UNLOCKED=//p" | tail -1); TPF=$(echo "$E" | sed -n "s/^TRADING_PROFILE=//p" | tail -1)
EQL=$(printf %s "$EQV" | tr -d " \t" | tr "A-Z" "a-z")
if [ '"$CHK_JAR"' = '"$SJ_NEW_MD5"' ]; then
  case "$EQL" in 0|false) echo "FAIL ban_va_TAT (process KILLSW_EQ_POLL_UNLOCKED=$EQV)";; *) echo "OK ban_va_deadlock_BAT (process KILLSW_EQ_POLL_UNLOCKED=${EQV:-khong_dat=mac_dinh_BAT})";; esac
  [ -z "$TPF" ] || echo "WARN co TRADING_PROFILE=$TPF: Cfg doc KILLSW_EQ_POLL_UNLOCKED tu profile (khong kiem duoc qua env)"
else echo "INFO jar r4u3fin2 khong co ban va (KILLSW_EQ_POLL_UNLOCKED=${EQV:-khong_dat})"; fi
[ "$(T "khoi dong adapter=LIVE")" -ge 1 ] && echo "OK adapter_LIVE" || echo "WAIT adapter_LIVE"
[ "$(T "khoi dong adapter=DRY")" = 0 ] || echo "FAIL adapter_DRY_trong_log_JVM_moi"
[ "$(tail -n +$SL $L | grep -a "khoi dong adapter=LIVE" | grep -acE "c3_capital='"$CAP0"'(\.0)?( |$)")" -ge 1 ] && echo "OK c3_capital='"$CAP0"'" || echo "WAIT c3_capital"
grep -q "^'"$NM $TS"' " run/KILL_SWITCH 2>/dev/null && echo "OK KILL_SWITCH_con (chua mo lenh moi)" || echo "FAIL KILL_SWITCH_cua_script_mat"
[ "$(T "PUSH=ON")" = 0 ] && echo "OK chua_PUSH_ON" || echo "FAIL PUSH_ON_khi_con_KILL_SWITCH"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"
if [ "$(T "\[MINUTE-FIN\] TAT")" -ge 1 ]; then echo "FAIL MINUTE-FIN_TAT"; elif [ "$(T "\[MINUTE-FIN\] BAT")" -ge 1 ]; then echo "OK MINUTE-FIN_BAT"; else echo "WAIT MINUTE-FIN_BAT"; fi
[ "$(T "\[C3-EXCL-FORCE\]")" = 0 ] && echo "OK 0_C3-EXCL-FORCE" || echo "FAIL C3-EXCL-FORCE"
LS=$(tail -n +$SL $L | grep -a "LEGACY tren tai khoan chinh:" | tail -1 | grep -aoE "chinh: [0-9]+" | awk "{print \$2}")
if [ -z "$LS" ]; then echo "WAIT scope_tk_con"; elif [ "$LS" = 0 ]; then echo "OK scope_tk_con_0_vi_the_ngoai_c3"; else echo "FAIL scope_tk_con_${LS}_vi_the_ngoai_c3"; fi
KF='"$KEYS_FILE"'
[ -f "$KF" ] && [ "$(stat -c %a "$KF")" = 600 ] && [ "$(sed -n "s/^C3_LIVE_API_KEY=//p" "$KF" | head -1 | tr -d " \t\r\"" | tr -d "\n" | sha256sum | cut -c1-8)" = '"$SUB_KEY_SHA8"' ] && echo "OK file_key_600_sha8" || echo "FAIL file_key"'; }
ks_ensure() { s242 "cd $A && { grep -q '^$NM $TS ' run/KILL_SWITCH 2>/dev/null || echo '$NM $TS $1' >> run/KILL_SWITCH; } && grep -q '^$NM $TS ' run/KILL_SWITCH" \
  && say "run/KILL_SWITCH DANG DAT (dung mo moi; vi the van duoc quan ly)" || say "!! KHONG xac nhan duoc run/KILL_SWITCH (ssh?) - owner: MODE=drain bash $_OPS/golive_live_off.sh"; }
# [OPS6 T3/H1] sj_ks_go <hau to> : go run/KILL_SWITCH CHI khi MOI dong la cua minh. In OK (da go / da go o lan truoc) | KHAC (co dong nguoi khac
#   hoac KS khong con dong cua minh => GIU NGUYEN) | MAT (khong co KS) | LOI / rong (ssh)
sj_ks_go() { s242 "cd $A && if [ -e run/KILL_SWITCH.$1_$TS ] && [ ! -e run/KILL_SWITCH ]; then echo KSGO=OK; elif [ ! -e run/KILL_SWITCH ]; then echo KSGO=MAT; elif ! grep -q '^$NM $TS ' run/KILL_SWITCH || [ \"\$(grep -vc '^$NM $TS ' run/KILL_SWITCH)\" != 0 ]; then echo KSGO=KHAC; else mv -f run/KILL_SWITCH run/KILL_SWITCH.$1_$TS && [ ! -e run/KILL_SWITCH ] && echo KSGO=OK || echo KSGO=LOI; fi" 2>/dev/null | sed -n 's/^KSGO=//p' | tail -1; }
pause_clear() { gl_pause_clear >/dev/null 2>&1 || say "PAUSE con (ssh?) - tu go sau ${WD_PAUSE_MAX_S}s"; }
khan() { say "KHAN: $1"; tg "[golive] KHAN TS=$TS swap_jar($MODE): $1 | log $LOG" || say "!! Telegram KHONG gui duoc"; exit 2; }
downtime() { local a b; a=$(echo "$1" | sed -n 's/^T_STOP=//p' | tail -1); b=$(echo "$1" | sed -n 's/^T_START=//p' | tail -1)
  [[ "$a" =~ ^[0-9]+$ ]] && [[ "$b" =~ ^[0-9]+$ ]] && echo "$(( b - a ))s (stop $(TZ=Asia/Ho_Chi_Minh date -d @$a +%T) -> start $(TZ=Asia/Ho_Chi_Minh date -d @$b +%T) +07)" || echo "?"; }
do_rollback() {   # $1 = ly do. Ve jar nguon + start + hau kiem; DAT => go KS cua minh (exit 1); khong => GIU KS + KHAN (exit 2)
  say "$1 => ROLLBACK TU DONG ve jar nguon $FROM_MD5"
  gl_once_resume rollback _sj_rollback_rx RB END_RB
  echo "$RB" | grep -vx END_RB
  if ! echo "$RB" | grep -qx END_RB || echo "$RB" | grep -q '^FAIL'; then
    ks_ensure "rollback_loi"; pause_clear
    khan "$1 VA ROLLBACK LOI ($(echo "$RB" | grep '^FAIL' | head -2 | tr '\n' ' ')) => GIU run/KILL_SWITCH. Kiem: bash $_OPS/golive_monitor.sh ; jar backup $A/target/binance-java-sdk-1.2.4.jar.bak_${NM}_$TS"
  fi
  SL=$(echo "$RB" | sed -n 's/^RB_START_LINE=//p' | tail -1); SL=${SL:-1}; CHK_JAR=$FROM_MD5
  if gl_postloop CHK; then
    KG=$(sj_ks_go rbok)   # [OPS6 T3/H1] khong mv ca file khi co dong nguoi khac
    if [ "$KG" = OK ]; then
      pause_clear
      say "Da ROLLBACK xong: jar nguon $FROM_MD5 chay lai, hau kiem DAT, KILL_SWITCH cua script da go (KS khac neu co: giu)."
      tg "[golive] swap_jar($MODE) FAIL TS=$TS: $1 => ROLLBACK ve $FROM_MD5 XONG (hau kiem DAT). Log $LOG" || :
      exit 1
    fi
    pause_clear
    [ "$KG" = KHAC ] && khan "$1; rollback ve jar nguon $FROM_MD5 hau kiem DAT nhung run/KILL_SWITCH co dong NGUOI KHAC (owner drain / monitor KHAN) => GIU NGUYEN ca file, bot jar nguon DANG DRAIN. Owner/MASTER kiem noi dung roi MODE=undrain bash $_OPS/golive_live_off.sh"
    khan "$1; rollback hau kiem DAT nhung KHONG xac nhan go duoc KILL_SWITCH (${KG:-ssh?}) => co the van drain. Kiem golive_monitor.sh"
  fi
  ks_ensure "rollback_hau_kiem_truot"; pause_clear
  khan "$1 VA hau kiem SAU ROLLBACK TRUOT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)) => GIU run/KILL_SWITCH (dung mo moi). Kiem: bash $_OPS/golive_monitor.sh"
}
gl_once_resume restart _sj_restart_rx RS END_RS
RS=$(printf '%s\n' "$RS" | grep -vx END_RS); echo "$RS"
if echo "$RS" | grep -q '^FAIL ssh_restart_loi_trang_thai_khong_ro'; then
  ks_ensure "ssh_restart_khong_ro"
  khan "restart: ssh dut, KHONG doc duoc trang thai that tren 242 => KHONG ket luan (PAUSE tu het han sau ${WD_PAUSE_MAX_S}s => watchdog khoi dong lai bot neu tat). Kiem: bash $_OPS/golive_monitor.sh ; chay lai MODE=$MODE (idempotent: DA XONG neu jar da doi)"
fi
if echo "$RS" | grep -q '^FAIL' && ! echo "$RS" | grep -q '^OK da_stop'; then
  pause_clear
  say "DUNG: buoc truoc khi dung bot FAIL: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ')"
  say "KET QUA: TU_CHOI - bot KHONG bi dung, jar KHONG doi, KILL_SWITCH cua script da go. Log: $LOG"
  tg "[golive] swap_jar($MODE) TU CHOI TS=$TS truoc khi dung bot: $(echo "$RS" | grep '^FAIL' | head -1)" || :
  exit 1
fi
DT=$(downtime "$RS"); say "THOI GIAN BOT TAT (stop -> start): $DT"
SL=$(echo "$RS" | sed -n 's/^START_LINE=//p' | tail -1); SL=${SL:-1}
LB=$(echo "$RS" | sed -n 's/^LEGACY_TRUOC_STOP=\([0-9][0-9]*\)$/\1/p' | tail -1)
[ -n "$LB" ] && [ "$LB" != "$L0" ] && { say "INFO LEGACY truoc stop=$LB (luc kiem truoc: $L0) => hau kiem so voi $LB"; L0=$LB; }
echo "$RS" | grep -q '^FAIL' && do_rollback "buoc doi jar FAIL sau khi dung bot ($(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' '))"
CHK_JAR=$TO_MD5
gl_postloop CHK || do_rollback "hau kiem jar dich TRUOT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200))"
# ---------------------------------------------------------------- DAT => go KILL_SWITCH cua minh => cho PUSH ON
T_KS=$(date +%s)
KG=$(sj_ks_go ok)   # [OPS6 T3/H1]
if [ "$KG" = OK ]; then
  say "OK go run/KILL_SWITCH (hau kiem DAT) - cho PUSH ON"
  PON=0
  for r in $(seq 1 "$POST_ROUNDS"); do
    sleep "$POST_WAIT_S"
    n=$(s242 "cd $A && tail -n +$SL logs/full.log 2>/dev/null | grep -ac 'PUSH doi trang thai -> ON'") || n=x
    [ "$n" != x ] && [ "$n" -ge 1 ] 2>/dev/null && { PON=1; break; }
  done
  if [ "$PON" = 1 ]; then
    pause_clear
    T1=$(date +%s); T0=$(echo "$RS" | sed -n 's/^T_STOP=//p' | tail -1)
    say "=== XONG: v_t_m chay jar $TO_MD5 ($DIRTXT), MICRO-LIVE C3_CAPITAL=$CAP0 PUSH ON. Bot tat $DT; khong mo moi tong ~$(( T1 - ${T0:-$T1} ))s."
    say "Jar nguon backup tren 242: $A/target/binance-java-sdk-1.2.4.jar.bak_${NM}_$TS. Quay lai: MODE=$([ "$MODE" = swap ] && echo rollback || echo swap) bash $_OPS/golive_swap_jar.sh"
    say "Theo doi: bash $_OPS/golive_monitor.sh . Dung khan: MODE=drain bash $_OPS/golive_live_off.sh"
    tg "[golive] swap_jar($MODE) XONG TS=$TS: jar $TO_MD5, bot tat $DT, PUSH ON. Log $LOG" || :
    exit 0
  fi
  if s242 "cd $A && { grep -q '^$NM $TS ' run/KILL_SWITCH 2>/dev/null || echo '$NM $TS push_khong_ON' >> run/KILL_SWITCH; } && grep -q '^$NM $TS ' run/KILL_SWITCH"; then   # [A1 m2] KS nguoi khac (drain) => GIU
    M="hau kiem DAT nhung KHONG thay 'PUSH doi trang thai -> ON' sau khi go KILL_SWITCH => DA DAT LAI KILL_SWITCH (xac nhan; khong mo moi). Kiem bash $_OPS/golive_monitor.sh"
  else
    M="hau kiem DAT nhung KHONG thay PUSH ON; DAT LAI KILL_SWITCH THAT BAI (ssh?) => owner chay NGAY MODE=drain bash $_OPS/golive_live_off.sh"
  fi
  pause_clear; khan "$M"
fi
pause_clear
[ "$KG" = KHAC ] && khan "hau kiem jar $TO_MD5 DAT nhung run/KILL_SWITCH co dong NGUOI KHAC (owner drain / monitor KHAN) => GIU NGUYEN ca file, KHONG go: bot jar moi DANG DRAIN. Owner/MASTER kiem noi dung roi MODE=undrain bash $_OPS/golive_live_off.sh"
khan "hau kiem DAT nhung KHONG XAC NHAN go duoc run/KILL_SWITCH (ssh / KILL_SWITCH khac da ghi de) => bot jar $TO_MD5 CO THE van drain hoac da mo. Kiem: bash $_OPS/golive_monitor.sh ; dung khan: MODE=drain bash $_OPS/golive_live_off.sh"
