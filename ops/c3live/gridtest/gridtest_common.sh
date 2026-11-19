#!/usr/bin/env bash
# =============================================================================
# gridtest_common.sh - [GRIDTEST 2026-11-20] thu vien chung goi "thu luoi tren micro-live" (R1 hot window). Source boi gridtest_*.sh.
#   KHONG chay truc tiep. Dua tren golive_lib.sh (A1 da audit: s242, gl_read_state, gl_chk_common, gl_postloop, gl_api242, gl_yes,
#   gl_time, tg, gl_once_resume, gl_phase242 ...). Co che RIENG cua goi nay (tranh loi A1_HOTFIX_KS): restart doi env CHI bang 1 khoi
#   "# GRIDTEST <TS>" o CUOI conf/env.sh (khong doc/in noi dung file; backup + md5; file moi = BASE + khoi, cai bang mv nguyen tu);
#   KILL_SWITCH token rieng, KHONG ghi de / go KS nguoi khac; PAUSE watchdog fail-closed + CHO .lock cua watchdog; hau kiem theo process.
# Tham so CO DINH theo PREREG_GRID_LIVE_TEST_V2 (doi = sua prereg truoc).
# =============================================================================
set -uo pipefail
trap '' HUP
export DRY=${DRY:-1}                                     # MAC DINH DRY=1 (chi kiem + in ke hoach)
GT_HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
GT_OPS=$(cd "$GT_HERE/.." && pwd)
# ---- [m1] ghim HEAD da A1 duyet + khong sua chua commit (nhu golive_swap_jar.sh)
_GT_APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}
_gt_pw=""
_GT_HC=$(git -C "$GT_HERE" rev-parse --verify -q HEAD 2>/dev/null) || _gt_pw="$GT_HERE khong phai repo git"
[ -n "$_gt_pw" ] || { [ -f "$_GT_APO" ] && grep -qE "^$_GT_HC([[:space:]]|\$)" "$_GT_APO"; } || _gt_pw="HEAD $_GT_HC CHUA duoc A1 duyet (khong co trong $_GT_APO)"
[ -n "$_gt_pw" ] || git -C "$GT_OPS" diff --quiet HEAD -- . 2>/dev/null || _gt_pw="$GT_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_gt_pw" ] || { echo "TU CHOI [m1]: $_gt_pw - KHONG lam gi."; exit 1; }
. "$GT_OPS/golive_lib.sh"
# ---- [M5] manifest rieng (script nam o thu muc con, khong dung gl_manifest_check): gridtest_*.sh + ../golive_lib.sh + ghost_clear
gt_manifest_check() {
  local mf=$GT_HERE/GRIDTEST_MANIFEST.md5 self
  self=$(basename "$1")
  [ -s "$mf" ] || { echo "TU CHOI [M5]: thieu manifest $mf"; return 1; }
  grep -qxE "[0-9a-f]{32}  $self" "$mf" && grep -qxE "[0-9a-f]{32}  \.\./golive_lib\.sh" "$mf" \
    || { echo "TU CHOI [M5]: $self / ../golive_lib.sh KHONG co trong manifest"; return 1; }
  (cd "$GT_HERE" && md5sum -c --quiet --strict "$mf" >/dev/null 2>&1) \
    || { echo "TU CHOI [M5]: file KHAC manifest da commit: $(cd "$GT_HERE" && md5sum -c --strict "$mf" 2>&1 | grep -v ': OK$' | head -3 | tr '\n' ' ')"; return 1; }
}
# ---- hang so (prereg V2 muc 3/6) - KHONG doi sau khi thay ket qua
GT_JAR_MD5=${GT_JAR_MD5:-01cfbb4324fb4a10b615dc3c976ddc73}     # jar hotfix-ks (KHONG chay voi jar cu 6418.. - deadlock)
GT_OLD_JAR_MD5=641803565297d4065d90245e04a00f11
GT_CAP=1000                                                    # C3_CAPITAL bat buoc
GT_PCT_PROD=0.999950829; GT_TOPK_PROD=24                       # gia tri production bat buoc (env.sh = process)
GT_PCT_TEST=0.99; GT_TOPK_TEST=1; GT_LEVELS_TEST=-0.01,-0.02,-0.03
GT_LEVELS_LOG_TEST='levels=[-0.01, -0.02, -0.03]'              # Arrays.toString(float[]) (LiveDcaGridC3.java:49)
GT_LEVELS_LOG_PROD='levels=[-0.5, -0.75, -0.9]'
GT_N_LEG0=2                                                    # du leg0 => owner chay phase_b
GT_HARD_LEG0=${GT_HARD_LEG0:-3}; GT_HARD_SUBMIT=${GT_HARD_SUBMIT:-12}; GT_HARD_NOTIONAL=${GT_HARD_NOTIONAL:-300}; GT_HARD_UPNL=${GT_HARD_UPNL:--30}
GT_PHASE_A_MAX_H=24; GT_PHASE_B_MAX_H=24
GT_MIN_UP_S=${GT_MIN_UP_S:-21600}                              # jar hotfix chay on dinh >= 6 h (khong HB_STALE_KILL) truoc pha A
GT_SDIR=${GT_SDIR:-$LOGDIR/gridtest}; GT_STATE=$GT_SDIR/state.env
GT_LOCKD=${GT_LOCKD:-/home/ubuntu/claude_master/locks}
GT_CRON_TAG='# GRIDTEST_WATCH'
GT_PRICE_URL=${GT_PRICE_URL:-https://fapi.binance.com/fapi/v1/premiumIndex}   # CONG KHAI, khong ky
GT_SED='s/signature=[0-9a-f]+/signature=<SIG>/g; s/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'
SJ_WD_LOCK_WAIT_S=${SJ_WD_LOCK_WAIT_S:-300}
gt_init() {   # $1 ten script; log + loc moi output (signature / token)
  GL_NAME=$1; NM=$1
  TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
  mkdir -p "$GT_SDIR"; LOG=$GT_SDIR/${1}_$TS.log
  exec > >(trap '' HUP INT TERM PIPE; sed -u -E "$GT_SED" | tee --output-error=warn -a "$LOG") 2>&1
  say "=== $1 TS=$TS DRY=$DRY HEAD=$_GT_HC ==="
}
gt_sv() { sed -n "s/^$1=//p" "$GT_STATE" 2>/dev/null | tail -1; }
gt_state_set() {   # $1=KEY $2=VAL (ghi nguyen tu)
  mkdir -p "$GT_SDIR"; { grep -v "^$1=" "$GT_STATE" 2>/dev/null; echo "$1=$2"; } > "$GT_STATE.tmp" && mv -f "$GT_STATE.tmp" "$GT_STATE"
}
khan() { say "KHAN: $1"; tg "[gridtest] KHAN TS=$TS $NM: $1 | log $LOG" || say "!! Telegram KHONG gui duoc"; exit 2; }
# ---- doc them 242 (CHI DOC): jar PROCESS, uptime, 3 key (process + env.sh, chi 3 key nay), md5/so dong env.sh, khoi GRIDTEST, watchdog
gt_state_extra() {   # $1 = duong BASE tren 242 (hoac none)
  s242in "PP='$(gl_rx "$PROC_PAT")' bash -s -- $A $WD_PAUSE ${1:-none}" <<'EOF'
A=$1; PAUSE=$2; BASE=$3; cd "$A" || { echo "ERR=cd"; echo END_GX; exit 0; }
P=$(pgrep -f "$PP" | head -1)
JFD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
echo "PJAR_MD5=$( [ -n "$JFD" ] && md5sum < "$JFD" 2>/dev/null | cut -c1-32)"
echo "PUP_S=$(ps -o etimes= -p "$P" 2>/dev/null | tr -d ' ')"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_GATE_ROLLING_PCT SELECTOR_RANK_TOPK DCA_GRID_LEVELS; do
  echo "GP_$k=$(echo "$E" | grep -c "^$k=") $(echo "$E" | sed -n "s/^$k=//p" | tail -1)"
  echo "GS_$k=$(grep -c "^[[:space:]]*\(export[[:space:]]\+\)\?$k=" conf/env.sh) $(sed -n "s/^export $k=//p" conf/env.sh | tail -1)"
done
echo "ENVSH_MD5=$(md5sum < conf/env.sh | cut -c1-32)"
echo "ENVSH_LINES=$(wc -l < conf/env.sh)"
echo "ENVSH_LASTNL=$(tail -c 1 conf/env.sh | od -An -tx1 | tr -d ' ')"
echo "GT_BLOCKS=$(grep -c '^# GRIDTEST ' conf/env.sh)"
[ "$BASE" != none ] && echo "BASE_MD5=$( [ -f "$BASE" ] && md5sum < "$BASE" | cut -c1-32)"
echo "KS_HEAD=$( [ -e run/KILL_SWITCH ] && head -c 70 run/KILL_SWITCH | tr -c 'A-Za-z0-9_ .:=-' '_')"
WL=$(dirname "$PAUSE")/watchdog.log; echo "WD_HBSTALE=$(tail -n 400 "$WL" 2>/dev/null | grep -c 'HB_STALE')"
echo "NOW_KEY=$(date +%Y%m%d%H%M%S)"
echo END_GX
EOF
}
gt_read_extra() { GX=$(gt_state_extra "${1:-none}") || die "ssh 242 loi (doc them)"; echo "$GX" | grep -qx END_GX || die "doc them 242 khong tron ven"; echo "$GX" | grep -q '^ERR=' && die "doc 242 loi: $(echo "$GX" | grep '^ERR=')"; :; }
gx() { echo "$GX" | sed -n "s/^$1=//p" | head -1; }
# so dong + gia tri 1 key (dang "N val"): gk <GP|GS> <KEY> => in "N|val"
gk() { local v; v=$(gx "${1}_$2"); echo "${v%% *}|${v#* }"; }
# md5 noi dung BASE + khoi (khong doc file BASE o Oracle: tinh tren 242 khi can). Khoi = text (co \n cuoi moi dong)
gt_block_a() { printf '# GRIDTEST %s pha A (gridtest_on.sh) - xoa CA khoi = tra cau hinh production\nexport LIVE_GATE_ROLLING_PCT=%s\nexport SELECTOR_RANK_TOPK=%s\nexport DCA_GRID_LEVELS=%s\n' "$1" "$GT_PCT_TEST" "$GT_TOPK_TEST" "$GT_LEVELS_TEST"; }
gt_block_b() { printf '# GRIDTEST %s pha B %s (gridtest_phase_b.sh) - gate + K production, giu DCA nong; xoa CA khoi = tra cau hinh\nexport DCA_GRID_LEVELS=%s\n' "$1" "$2" "$GT_LEVELS_TEST"; }
# ---- md5 cua BASE + khoi, tinh TREN 242 (khong chep env.sh ve Oracle): $1 BASE  $2 khoi base64 (rong = BASE)
gt_newmd5() {
  s242 "cd $A && { cat '$1'; printf '%s' '$2' | base64 -d; } | md5sum | cut -c1-32"
}
# ---- monitor song: cron ghim + co + heartbeat
gt_mon_alive() {
  gl_mon_cron_ok || { echo "cron golive_monitor ghim KHONG co/sai"; return 1; }
  [ -f "$GL_MON_FLAG" ] || { echo "khong co co monitor $GL_MON_FLAG"; return 1; }
  local a; a=$(gl_hb_age); [ "$a" -ge 0 ] && [ "$a" -le "$MON_HB_MAX_AGE_S" ] || { echo "heartbeat monitor cu ${a}s > ${MON_HB_MAX_AGE_S}s"; return 1; }
  echo "monitor song (heartbeat ${a}s)"; return 0
}
# ---- cron watch (Oracle crontab user) cai/go - goi boi on/off
gt_watch_line() { echo "* * * * * /usr/bin/flock -n $GT_LOCKD/gridtest_watch.lock /usr/bin/timeout -k 5 55 /bin/bash $GT_HERE/gridtest_watch.sh >> $GT_SDIR/watch_cron.log 2>&1 $GT_CRON_TAG"; }
gt_watch_cron_has() { $ORA_CRONTAB_CMD -l 2>/dev/null | grep -qF "$GT_CRON_TAG"; }
gt_watch_cron_install() {
  local cur; cur=$($ORA_CRONTAB_CMD -l 2>/dev/null | grep -vF "$GT_CRON_TAG")
  { [ -n "$cur" ] && printf '%s\n' "$cur"; gt_watch_line; } | $ORA_CRONTAB_CMD - && [ "$($ORA_CRONTAB_CMD -l 2>/dev/null | grep -cF "$GT_CRON_TAG")" = 1 ]
}
gt_watch_cron_remove() {
  gt_watch_cron_has || return 0
  local cur; cur=$($ORA_CRONTAB_CMD -l 2>/dev/null | grep -vF "$GT_CRON_TAG")
  { [ -n "$cur" ] && printf '%s\n' "$cur"; } | $ORA_CRONTAB_CMD - && ! gt_watch_cron_has
}
# ---- KILL_SWITCH token rieng (KHONG ghi de KS co san)
gt_ks_ensure() {   # $1 token-ly do
  s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo '$NM $TS $1' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]" \
    && say "run/KILL_SWITCH DANG DAT (dung mo moi + DCA; vi the van duoc quan ly)" || say "!! KHONG xac nhan duoc run/KILL_SWITCH (ssh?) - owner: MODE=drain bash $GT_OPS/golive_live_off.sh"
}
gt_pause_clear() { gl_pause_clear >/dev/null 2>&1 || say "PAUSE con (ssh?) - tu go sau ${WD_PAUSE_MAX_S}s"; }
# =============================================================================
# RESTART doi env (1 lan, idempotent theo marker pha): KS(token) -> PAUSE (fail-closed) -> cho .lock watchdog -> kiem env.sh = CUR ->
#   backup -> dung file moi = BASE + khoi (md5 = NEW) -> stop -> mv file moi -> start -> 1 JVM. Bien: GTR_CUR GTR_NEW GTR_BASE GTR_BASEMD5
#   GTR_BLK(base64) GTR_KSP(strict|keep). In RS (OK/FAIL, START_LINE=, SINCE_KEY=, T_STOP=, T_START=, LEGACY_TRUOC_STOP=).
# =============================================================================
_gt_restart_rx() {
  s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $NM $WD_PAUSE $WD_PAUSE_MAX_S $$ $SJ_WD_LOCK_WAIT_S $GTR_KSP $GTR_CUR $GTR_NEW $GTR_BASE $GTR_BASEMD5 ${GTR_BLK:-none}" <<'EOF'
trap '' HUP PIPE
{
A=$1; TS=$2; NM=$3; PAUSE=$4; MAXS=$5; JP=$6; WLW=$7; KSP=$8; CUR=$9; NEW=${10}; BASE=${11}; BMD5=${12}; BLK=${13}
cd "$A" || { echo "FAIL cd"; echo END_RS; exit 0; }
exec 8>>"run/.gridtest_${NM}_$TS.lk"; flock -w 600 8 || { echo "FAIL lan_chay_truoc_cung_TS_van_dang_chay"; echo END_RS; exit 0; }
PH=run/.gridtest_${NM}_$TS.phase; BK=conf/env.sh.bak_${NM}_$TS; NF=conf/env.sh.new_${NM}_$TS
ph() { grep -qx "$1" "$PH" 2>/dev/null; }
pv() { sed -n "s/^$1=//p" "$PH" 2>/dev/null | tail -1; }
mark() { echo "$1" >> "$PH"; }
m5() { md5sum < "$1" 2>/dev/null | cut -c1-32; }
myks() { grep -q "^$NM $TS " run/KILL_SWITCH 2>/dev/null; }
ksoff() { myks && mv -f run/KILL_SWITCH run/KILL_SWITCH.rb_$TS; }
TOK="C3GOLIVE_${NM} TS=$TS pid=$JP"
pclr() { grep -q "^$TOK " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"; }
done_info() { echo "START_LINE=$(pv START_LINE)"; echo "SINCE_KEY=$(pv SINCE_KEY)"; echo "T_STOP=$(pv T_STOP)"; echo "T_START=$(pv T_START)"; }
if ph started; then
  echo "INFO pha_da_xong_truoc (chay lai sau ssh dut): KHONG stop/start lai"; echo "OK da_stop"; echo "OK env_moi md5=$NEW"; done_info
  P=$(pgrep -f "$PP" | head -1); [ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process_sau_start"
  [ "$(pgrep -fc "$PP")" = 1 ] && echo "OK dung_1_JVM" || echo "FAIL so_JVM_sau_start=$(pgrep -fc "$PP")"
  echo END_RS; exit 0
fi
if ! ph stopped; then
  [ "$(m5 conf/env.sh)" = "$CUR" ] || ph env_new || { echo "FAIL env_sh_khac_luc_kiem (md5 $(m5 conf/env.sh) != $CUR) - bot KHONG dung"; echo END_RS; exit 0; }
  [ "$(m5 "$BASE")" = "$BMD5" ] || { echo "FAIL BASE_${BASE}_sai_md5 - bot KHONG dung"; echo END_RS; exit 0; }
  if ! ph newf; then
    \cp -p conf/env.sh "$NF" && cat "$BASE" > "$NF" && { [ "$BLK" = none ] || printf '%s' "$BLK" | base64 -d >> "$NF"; } \
      && [ "$(m5 "$NF")" = "$NEW" ] && mark newf || { rm -f "$NF"; echo "FAIL dung_file_env_moi_sai_md5 - bot KHONG dung"; echo END_RS; exit 0; }
  fi
  [ -e "$BK" ] || { \cp -p conf/env.sh "$BK" && [ "$(m5 "$BK")" = "$CUR" ] && echo "$CUR" > "$BK.md5"; } || { echo "FAIL backup_env - bot KHONG dung"; echo END_RS; exit 0; }
  if ! myks; then
    if [ -e run/KILL_SWITCH ]; then
      if [ "$KSP" = keep ]; then echo "INFO KILL_SWITCH_khac_dang_dat ($(head -c 60 run/KILL_SWITCH | tr -c 'A-Za-z0-9_ .:=-' '_')) - GIU NGUYEN, khong dat token rieng"; mark ks_other
      else echo "FAIL KILL_SWITCH_khac_dang_dat ($(head -c 60 run/KILL_SWITCH | tr -c 'A-Za-z0-9_ .:=-' '_')) - bot KHONG dung"; echo END_RS; exit 0; fi
    else echo "$NM $TS hau_kiem: dung mo moi toi khi hau kiem env moi DAT" > run/KILL_SWITCH; fi
  fi
  { myks || ph ks_other; } && [ -e run/KILL_SWITCH ] && echo "OK KILL_SWITCH_dat_truoc_stop" || { echo "FAIL khong_dat_duoc_KILL_SWITCH (bot KHONG dung)"; echo END_RS; exit 0; }
  if [ -e "$PAUSE" ] && ! grep -q "^$TOK " "$PAUSE" 2>/dev/null; then ksoff; echo "FAIL PAUSE_khac_dang_co - bot KHONG dung"; echo END_RS; exit 0; fi
  mkdir -p "$(dirname "$PAUSE")" 2>/dev/null; echo "$TOK t=$(date +%s)" > "$PAUSE" && grep -q "^$TOK " "$PAUSE" 2>/dev/null && echo "OK watchdog_PAUSE" \
    || { ksoff; pclr; echo "FAIL khong_tao_duoc_PAUSE_watchdog (bot KHONG dung, KS cua minh da go)"; echo END_RS; exit 0; }
  if ! ph pause_timer; then setsid nohup bash -c "sleep $MAXS; grep -q '^$TOK ' '$PAUSE' 2>/dev/null && rm -f '$PAUSE'" > /dev/null 2>&1 < /dev/null 8>&- & mark pause_timer; fi
  WL="$(dirname "$PAUSE")/.lock"; W0=$(date +%s)
  if flock -w "$WLW" "$WL" true; then echo "OK watchdog_khong_con_luot_dang_chay (cho $(( $(date +%s) - W0 ))s)"
  else ksoff; pclr; echo "FAIL watchdog_giu_lock_qua_${WLW}s - bot KHONG dung, KS + PAUSE cua minh da go"; echo END_RS; exit 0; fi
  echo "LEGACY_TRUOC_STOP=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')"
  ph "T_STOP=.*" || mark "T_STOP=$(date +%s)"
  bin/daemon.sh stop 8>&-
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  if pgrep -f "$PP" >/dev/null; then ksoff; pclr; rm -f "$NF"; echo "FAIL van_con_process_sau_stop (env KHONG doi, KS + PAUSE cua minh da go)"; echo END_RS; exit 0; fi
  mark stopped
fi
echo "OK da_stop"
if ! ph env_new; then
  if [ "$(m5 conf/env.sh)" != "$NEW" ]; then
    [ "$(m5 "$NF")" = "$NEW" ] && chmod --reference=conf/env.sh "$NF" 2>/dev/null; chown --reference=conf/env.sh "$NF" 2>/dev/null
    [ "$(m5 "$NF")" = "$NEW" ] && mv -f "$NF" conf/env.sh || { echo "FAIL cai_env_moi (mv)"; echo END_RS; exit 0; }
  fi
  [ "$(m5 conf/env.sh)" = "$NEW" ] && mark env_new || { echo "FAIL env_moi_sai_md5"; echo END_RS; exit 0; }
fi
echo "OK env_moi md5=$NEW"
ph "START_LINE=.*" || mark "START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
ph "SINCE_KEY=.*" || mark "SINCE_KEY=$(date +%Y%m%d%H%M%S)"
pgrep -f "$PP" >/dev/null || bin/daemon.sh start 8>&-
ph "T_START=.*" || mark "T_START=$(date +%s)"
mark started
done_info
sleep 8
P=$(pgrep -f "$PP" | head -1); NJ=$(pgrep -fc "$PP")
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process_sau_start"
[ "$NJ" = 1 ] && echo "OK dung_1_JVM" || echo "FAIL so_JVM_sau_start=$NJ"
echo END_RS
}
EOF
}
# KHOI PHUC an toan: stop -> env.sh = BASE (md5) -> start; KS GIU (dat neu chua co). Bien GTR_BASE GTR_BASEMD5. In RB.
_gt_restore_rx() {
  s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $NM $GTR_BASE $GTR_BASEMD5" <<'EOF'
trap '' HUP PIPE
{
A=$1; TS=$2; NM=$3; BASE=$4; BMD5=$5; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
exec 8>>"run/.gridtest_${NM}_$TS.lk"; flock -w 600 8 || { echo "FAIL lan_chay_truoc_cung_TS_van_dang_chay"; echo END_RB; exit 0; }
RP=run/.gridtest_${NM}_$TS.rbphase
ph() { grep -qx "$1" "$RP" 2>/dev/null; }
mark() { echo "$1" >> "$RP"; }
m5() { md5sum < "$1" 2>/dev/null | cut -c1-32; }
[ -e run/KILL_SWITCH ] || echo "$NM $TS khoi_phuc: dung mo moi" > run/KILL_SWITCH
[ -e run/KILL_SWITCH ] && echo "OK KILL_SWITCH_dang_dat" || echo "WARN khong_dat_duoc_KILL_SWITCH"
if ! ph rb_started; then
  bin/daemon.sh stop 8>&-
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
  if [ "$(m5 conf/env.sh)" != "$BMD5" ] && [ "$(m5 "$BASE")" = "$BMD5" ]; then
    \cp -p "$BASE" conf/env.sh.rbtmp_$TS && [ "$(m5 conf/env.sh.rbtmp_$TS)" = "$BMD5" ] && mv -f conf/env.sh.rbtmp_$TS conf/env.sh; rm -f conf/env.sh.rbtmp_$TS
  fi
  [ "$(m5 conf/env.sh)" = "$BMD5" ] && echo "OK env_khoi_phuc_BASE md5=$BMD5" || echo "FAIL env_khong_khoi_phuc_duoc (md5 $(m5 conf/env.sh)) - VAN start (KS dat) de bot khong tat"
  grep -q '^RB_START_LINE=' "$RP" 2>/dev/null || mark "RB_START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
  bin/daemon.sh start 8>&-; mark rb_started; sleep 8
else
  echo "INFO khoi phuc da start o lan truoc - chi KIEM"; pgrep -f "$PP" >/dev/null || { bin/daemon.sh start 8>&-; sleep 8; }
fi
echo "RB_START_LINE=$(sed -n 's/^RB_START_LINE=//p' "$RP" | tail -1)"
P=$(pgrep -f "$PP" | head -1); [ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK dung_1_JVM" || echo "FAIL so_JVM_sau_start=$(pgrep -fc "$PP")"
echo END_RB
}
EOF
}
# ---- hau kiem: GTC_PCT GTC_TOPK GTC_LEV (gia tri | none) GTC_LEVLOG (chuoi log) GTC_KS (mine|other) ; SL L0
GT_CHK() { gl_chk_common "$SL" "$L0" '
envk LIVE_ADAPTER=live; envk C3_CAPITAL='"$GT_CAP"'; envk SHADOW_NO_PUSH=false; envk LIVE_ENTRY_ENABLED=true; envk LIVE_C3_KEYS_FILE='"$KEYS_FILE"'; envk C3_EXCLUDE_LEGACY_HELD=false
envk LIVE_APPLY_GRID_RATIO=true; envk LIVE_DCA_GRID_ENABLED=true
envk LIVE_GATE_ROLLING_PCT='"$GTC_PCT"'; envk SELECTOR_RANK_TOPK='"$GTC_TOPK"'
if [ '"$GTC_LEV"' = none ]; then echo "$E" | grep -q "^DCA_GRID_LEVELS=" && echo "FAIL env DCA_GRID_LEVELS_van_con" || echo "OK env DCA_GRID_LEVELS_khong_dat(mac_dinh)"; else envk DCA_GRID_LEVELS='"$GTC_LEV"'; fi
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = '"$GT_JAR_MD5"' ] && echo "OK file_jar_hotfix" || echo "FAIL file_jar_khac_hotfix"
JFD=$(find /proc/$P/fd -lname "*binance-java-sdk*.jar*" 2>/dev/null | head -1); JPM=$( [ -n "$JFD" ] && md5sum < "$JFD" 2>/dev/null | cut -c1-32)
if [ -z "$JPM" ]; then echo "WAIT jar_process_chua_thay"; elif [ "$JPM" = '"$GT_JAR_MD5"' ]; then echo "OK jar_PROCESS_hotfix"; else echo "FAIL jar_PROCESS=${JPM}"; fi
GR=$(tail -n +$SL $L 2>/dev/null | grep -a "GATE-RATIO\] LIVE BAT" | tail -1 | grep -aoE "pct=[0-9.]+" | cut -d= -f2)
if [ -z "$GR" ]; then echo "WAIT log_GATE-RATIO"; elif awk -v a="$GR" -v b='"$GTC_PCT"' "BEGIN{d=a-b; if(d<0)d=-d; exit !(d<1e-6)}"; then echo "OK log_GATE-RATIO_pct=$GR"; else echo "FAIL log_GATE-RATIO_pct=${GR}_khac_'"$GTC_PCT"'"; fi
DL=$(tail -n +$SL $L 2>/dev/null | grep -a "LIVE-DCA-GRID\] LIVE_DCA_GRID_ENABLED=true" | tail -1)
if [ -z "$DL" ]; then echo "WAIT log_LIVE-DCA-GRID"; elif echo "$DL" | grep -qF "'"$GTC_LEVLOG"'"; then echo "OK log_DCA_'"$(echo "$GTC_LEVLOG" | tr -d ' ')"'"; else echo "FAIL log_DCA_levels_khac"; fi
[ "$(T "khoi dong adapter=LIVE")" -ge 1 ] && echo "OK adapter_LIVE" || echo "WAIT adapter_LIVE"
[ "$(T "khoi dong adapter=DRY")" = 0 ] || echo "FAIL adapter_DRY"
[ "$(tail -n +$SL $L | grep -a "khoi dong adapter=LIVE" | grep -acE "c3_capital='"$GT_CAP"'(\.0)?( |$)")" -ge 1 ] && echo "OK c3_capital" || echo "WAIT c3_capital"
if [ '"$GTC_KS"' = mine ]; then grep -q "^'"$NM $TS"' " run/KILL_SWITCH 2>/dev/null && echo "OK KILL_SWITCH_cua_minh_con" || echo "FAIL KILL_SWITCH_cua_script_mat"; else [ -e run/KILL_SWITCH ] && echo "OK KILL_SWITCH_khac_van_giu" || echo "FAIL KILL_SWITCH_khac_bi_mat"; fi
[ "$(T "PUSH=ON")" = 0 ] && [ "$(T "PUSH doi trang thai -> ON")" = 0 ] && echo "OK chua_PUSH_ON" || echo "FAIL PUSH_ON_khi_con_KILL_SWITCH"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"
[ "$(T "\[C3-EXCL-FORCE\]")" = 0 ] && echo "OK 0_C3-EXCL-FORCE" || echo "FAIL C3-EXCL-FORCE"
LS=$(tail -n +$SL $L | grep -a "LEGACY tren tai khoan chinh:" | tail -1 | grep -aoE "chinh: [0-9]+" | awk "{print \$2}")
if [ -z "$LS" ]; then echo "WAIT scope_tk_con"; elif [ "$LS" = 0 ]; then echo "OK scope_tk_con_0_ngoai_c3"; else echo "FAIL scope_tk_con_${LS}_ngoai_c3"; fi
KF='"$KEYS_FILE"'
[ -f "$KF" ] && [ "$(stat -c %a "$KF")" = 600 ] && [ "$(sed -n "s/^C3_LIVE_API_KEY=//p" "$KF" | head -1 | tr -d " \t\r\"" | tr -d "\n" | sha256sum | cut -c1-8)" = '"$SUB_KEY_SHA8"' ] && echo "OK file_key_600_sha8" || echo "FAIL file_key"'; }
gt_downtime() { local a b; a=$(echo "$1" | sed -n 's/^T_STOP=//p' | tail -1); b=$(echo "$1" | sed -n 's/^T_START=//p' | tail -1)
  [[ "$a" =~ ^[0-9]+$ ]] && [[ "$b" =~ ^[0-9]+$ ]] && echo "$(( b - a ))s" || echo "?"; }
# ---- go KS cua minh + cho PUSH ON (chi khi KHONG co KS khac). rc 0 = PUSH ON; 1 = KS khac giu (khong cho); 2 = loi
gt_release_and_push() {
  s242 "cd $A && { grep -q '^$NM $TS ' run/KILL_SWITCH 2>/dev/null && mv -f run/KILL_SWITCH run/KILL_SWITCH.ok_$TS; [ ! -e run/KILL_SWITCH ] || ! grep -q '^$NM $TS ' run/KILL_SWITCH; }" \
    || { say "!! KHONG xac nhan go duoc KILL_SWITCH cua minh"; return 2; }
  if s242 "[ -e $A/run/KILL_SWITCH ]"; then say "INFO con KILL_SWITCH KHAC (owner/phanh) - GIU, bot van drain"; return 1; fi
  local r n
  for r in $(seq 1 "$POST_ROUNDS"); do
    sleep "$POST_WAIT_S"
    n=$(s242 "cd $A && tail -n +$SL logs/full.log 2>/dev/null | grep -ac 'PUSH doi trang thai -> ON'") || n=x
    [ "$n" != x ] && [ "$n" -ge 1 ] 2>/dev/null && { say "OK PUSH ON"; return 0; }
  done
  s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo '$NM $TS push_khong_ON' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]" >/dev/null 2>&1
  return 2
}
# =============================================================================
# kiem truoc chung (CHI DOC 242 + Oracle). $1 = on|b|off. Dat F=1 neu co muc FAIL. Dat L0, CURMD5.
# =============================================================================
chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
gt_pre_base() {
  local m=$1 cap pg sg
  gl_read_state; gt_read_extra "${GT_BASE_PATH:-none}"
  F=0
  chk "1 process bot (co $(sv NPROC))" '[ "$(sv NPROC)" = 1 ]'
  if [ "$m" != off ]; then
    chk "jar FILE $(sv JAR_MD5) = hotfix $GT_JAR_MD5 (jar cu $GT_OLD_JAR_MD5 = deadlock => TU CHOI)" '[ "$(sv JAR_MD5)" = "$GT_JAR_MD5" ]'
    chk "jar PROCESS dang mo $(gx PJAR_MD5) = hotfix" '[ "$(gx PJAR_MD5)" = "$GT_JAR_MD5" ]'
  else say "INFO jar file=$(sv JAR_MD5) process=$(gx PJAR_MD5) (off KHONG doi hoi jar)"; fi
  chk "c3_live + adapter=live (process + env.sh)" '[ "$(sv ENV_LIVE_PROFILE)" = c3_live ] && [ "$(sv ENV_LIVE_ADAPTER)" = live ] && [ "$(sv ENVSH_LIVE_ADAPTER)" = live ]'
  cap=$(sv ENV_C3_CAPITAL)
  chk "C3_CAPITAL process '$cap' = env.sh '$(sv ENVSH_C3_CAPITAL)' = $GT_CAP" '[ "$cap" = "$GT_CAP" ] && [ "$(sv ENVSH_C3_CAPITAL)" = "$GT_CAP" ]'
  chk "LIVE_KILLSW_MODE=act" '[ "$(sv ENV_LIVE_KILLSW_MODE)" = act ]'
  chk "latch kill-switch NONE (co: $(sv LATCH))" '[ "$(sv LATCH)" = NONE ] || [ "$(sv LATCH)" = NOFILE ]'
  if [ "$m" != off ]; then chk "KHONG co run/KILL_SWITCH (co: '$(gx KS_HEAD)')" '[ "$(sv KILLSW_FILE)" = 0 ]'
  else say "INFO run/KILL_SWITCH: $([ "$(sv KILLSW_FILE)" = 1 ] && echo "CO '$(gx KS_HEAD)' - off GIU NGUYEN, khong go" || echo khong)"; fi
  chk "KHONG PAUSE watchdog" '[ "$(sv PAUSE | cut -c1)" = 0 ]'
  chk "khong canary/soak tren 242" '[ "$(sv CANARY_SOAK)" = 0 ]'
  chk "Oracle: khong co tien trinh $CANARY_PAT" 'gl_no_canary'
  chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" '[ "$(sv MEM)" -ge "$MIN_MEM_MB" ] 2>/dev/null'
  chk "file key $KEYS_FILE 600 + sha8 = $SUB_KEY_SHA8 (tk con)" '[ "$(sv KEYS_OK)" = 1 ] && [ "$(sv KEYS_PERM)" = 600 ] && [ "$(sv KEYS_FILE_SHA8)" = "$SUB_KEY_SHA8" ]'
  chk "process LIVE_C3_KEYS_FILE = $KEYS_FILE" '[ "$(sv ENV_LIVE_C3_KEYS_FILE)" = "$KEYS_FILE" ]'
  chk "process C3_EXCLUDE_LEGACY_HELD=false" '[ "$(sv ENV_C3_EXCLUDE_LEGACY_HELD)" = false ]'
  chk "process LIVE_APPLY_GRID_RATIO=true + LIVE_DCA_GRID_ENABLED=true" '[ "$(sv ENV_LIVE_APPLY_GRID_RATIO)" = true ] && [ "$(sv ENV_LIVE_DCA_GRID_ENABLED)" = true ]'
  chk "conf/env.sh ket thuc bang xuong dong" '[ "$(gx ENVSH_LASTNL)" = 0a ]'
  if [ "$m" != off ]; then chk "golive_monitor song: $(gt_mon_alive)" 'gt_mon_alive >/dev/null'; fi
  L0=$(sv LEGACY_N); [ -n "$L0" ] || L0=-1
  CURMD5=$(gx ENVSH_MD5)
  [[ "$CURMD5" =~ ^[0-9a-f]{32}$ ]] || { say "FAIL md5 env.sh doc khong duoc"; F=1; }
  say "INFO env.sh ${CURMD5:0:12} $(gx ENVSH_LINES) dong, khoi GRIDTEST=$(gx GT_BLOCKS); process uptime $(gx PUP_S)s; LEGACY=$L0; watchdog log HB_STALE (400 dong cuoi)=$(gx WD_HBSTALE)"
}
# c3 FLAT tren so + san (gl_api242 mon, CHI DOC, da audit). In ly do; rc 0 = FLAT.
gt_flat() {
  API=$(gl_api242 mon) || API="ERR=ssh_api"
  echo "$API" | grep -E '^(KEY_SHA8|POS_TOTAL|POS_LIST|ORD_TOTAL|ALGO_TOTAL|C3_BOOK_SYMBOLS|API_OK|ERR)' | sed 's/^/   san: /'
  echo "$API" | grep -qx END_API || { echo "   doc san khong tron ven"; return 2; }
  [ "$(av API_OK)" = 1 ] && [ "$(av KEY_SHA8)" = "$SUB_KEY_SHA8" ] || { echo "   doc san loi / key khac tk con"; return 2; }
  [ "$(sv BOOK_CUM)" = 0 ] && [ "$(av C3_BOOK_SYMBOLS)" = 0 ] && [ "$(av POS_TOTAL)" = 0 ] && [ "$(av ORD_TOTAL)" = 0 ] && [ "$(av ALGO_TOTAL)" = 0 ]
}
# kiem 3 key: $1 = GP|GS ; $2 PCT  $3 TOPK  $4 LEV(none|gia tri). So dong process phai = 1 (none: 0); env.sh: gia tri cuoi + >=1 dong
gt_keys_ok() {
  local src=$1 v n
  v=$(gk "$src" LIVE_GATE_ROLLING_PCT); n=${v%%|*}; [ "${v#*|}" = "$2" ] && [ "$n" -ge 1 ] 2>/dev/null || return 1
  v=$(gk "$src" SELECTOR_RANK_TOPK); n=${v%%|*}; [ "${v#*|}" = "$3" ] && [ "$n" -ge 1 ] 2>/dev/null || return 1
  v=$(gk "$src" DCA_GRID_LEVELS); n=${v%%|*}
  if [ "$4" = none ]; then [ "$n" = 0 ]; else [ "${v#*|}" = "$4" ] && [ "$n" -ge 1 ] 2>/dev/null; fi
}
# =============================================================================
# chay restart; rc 0 = bot len (hau kiem tiep) | 3 = FAIL TRUOC khi dung bot (khong doi gi) | 4 = FAIL SAU khi dung bot
# =============================================================================
gt_run_restart() {
  gl_once_resume restart _gt_restart_rx RS END_RS
  RS=$(printf '%s\n' "$RS" | grep -vx END_RS); echo "$RS"
  if echo "$RS" | grep -q '^FAIL ssh_restart_loi_trang_thai_khong_ro'; then
    gt_ks_ensure ssh_restart_khong_ro
    khan "restart: ssh dut, KHONG doc duoc trang thai that 242 => KHONG ket luan (PAUSE tu het han ${WD_PAUSE_MAX_S}s). Kiem: bash $GT_OPS/golive_monitor.sh ; chay lai cung lenh (idempotent theo marker) hoac gridtest_off.sh"
  fi
  if echo "$RS" | grep -q '^FAIL' && ! echo "$RS" | grep -q '^OK da_stop'; then gt_pause_clear; return 3; fi
  SL=$(echo "$RS" | sed -n 's/^START_LINE=//p' | tail -1); SL=${SL:-1}
  SINCE=$(echo "$RS" | sed -n 's/^SINCE_KEY=//p' | tail -1)
  local lb; lb=$(echo "$RS" | sed -n 's/^LEGACY_TRUOC_STOP=\([0-9][0-9]*\)$/\1/p' | tail -1)
  [ -n "$lb" ] && [ "$lb" != "$L0" ] && { say "INFO LEGACY truoc stop=$lb (luc kiem: $L0) => hau kiem so voi $lb"; L0=$lb; }
  say "THOI GIAN BOT TAT: $(gt_downtime "$RS")"
  echo "$RS" | grep -q '^FAIL' && return 4
  return 0
}
gt_run_restore() {   # $1 ly do; rc 0 = bot len lai voi BASE
  say "$1 => KHOI PHUC env.sh = BASE (production) + start (KILL_SWITCH GIU)"
  GTR_BASE=$(gt_sv GT_BASE); GTR_BASEMD5=$(gt_sv GT_BASE_MD5)
  gl_once_resume restore _gt_restore_rx RB END_RB
  echo "$RB" | grep -vx END_RB
  echo "$RB" | grep -qx END_RB && ! echo "$RB" | grep -q '^FAIL' || return 1
  SL=$(echo "$RB" | sed -n 's/^RB_START_LINE=//p' | tail -1); SL=${SL:-1}; return 0
}
gt_set_prod_chk() { GTC_PCT=$GT_PCT_PROD; GTC_TOPK=$GT_TOPK_PROD; GTC_LEV=none; GTC_LEVLOG=$GT_LEVELS_LOG_PROD; GTC_KS=${1:-mine}; }
gt_op_lock() {
  GT_LOCKDIR=$GT_SDIR/.gt_op.lock.d; mkdir -p "$GT_SDIR"
  if ! mkdir "$GT_LOCKDIR" 2>/dev/null; then
    local lp; lp=$(cat "$GT_LOCKDIR/pid" 2>/dev/null)
    if [ -n "$lp" ] && kill -0 "$lp" 2>/dev/null; then die "dang co 1 script gridtest khac chay (pid $lp)"; fi
    rm -rf "$GT_LOCKDIR"; mkdir "$GT_LOCKDIR" 2>/dev/null || die "khong lay duoc khoa $GT_LOCKDIR"
  fi
  echo $$ > "$GT_LOCKDIR/pid"; trap 'rm -rf "$GT_LOCKDIR"' EXIT
}
gsn() { local v; v=$(gt_sv "$1"); [[ "$v" =~ ^[0-9]+$ ]] && echo "$v" || echo 0; }
