#!/usr/bin/env bash
# =============================================================================
# golive_pilot_on.sh — [V12 R4o/ADD4] MICRO (C3_CAPITAL=1000) -> PILOT (C3_CAPITAL=<size>) (GOLIVE_SCENARIO ADD1 §4 / ADD4).
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit; MASTER cap duong dan)
#   DRY=1 bash $OPS/golive_pilot_on.sh   # chi kiem
#   bash $OPS/golive_pilot_on.sh         # SUB: go 'YES PILOT' | MAIN: 'YES DA CAT LEGACY' (khung :10-:44)
# C3_ACCOUNT=SUB (mac dinh, ADD4 tk con) | MAIN (ADD1 tk chinh — chi khi chi dinh ro).
# Kiem: gate G-PILOT (jar_md5 + size= + g_exec= [ADD2] + g_exit= DAT|Q4_OWNER [ADD3]), dang chay LIVE push ON, C3_CAPITAL hien tai < size,
#   latch NONE, khong KILL_SWITCH, RAM, khong PAUSE/canary/soak.
#   MAIN: + LEGACY_CUT_VERIFIED.ok (golive_legacy_verify.sh DAT <= 24 h) + LEGACY managed 0.
#   [ADD4 SUB] BO LEGACY_CUT_VERIFIED / legacy_verify / LEGACY 0 (§3, chi ghi log); thay bang: bot live dung LIVE_C3_KEYS_FILE = file key
#   tk con, key van dat (§2: IP-only, khong rut, futures, sha8 != tk chinh, dualSide=false, BFUSD), tk con 0 vi the / lenh / algo NGOAI c3 (§4).
# [VONG3 F2] restart ks=1 (KS token golive_pilot_on TRUOC stop, ban cu .prev_<TS>) + hau kiem 2 pha nhu micro_on (KS con => kiem => go => cho PUSH ON);
#   rollback => KS ve nhu truoc pilot (gl_ks_restore_prev). Precheck chap nhan KS token c3live_boot/c3_autodrain chuan (gl_ks_boot_ok).
# Lam: env +C3_CAPITAL=<size> ; PAUSE token ; restart (so live + vi the c3 GIU NGUYEN; adapter khong doi) ; hau kiem env, c3_capital,
#   PUSH=ON, stream, recon ok, latch NONE, 0 KHAN (MAIN: LEGACY 0). TRUOT => rollback: env.sh ve ban truoc (C3_CAPITAL cu), restart.
# [A1 ADD4] SUB: doi cron golive_monitor da cai (C-1), dam bao co monitor; MIN-2: co tien trinh canary_early* tren Oracle => TU CHOI.
# [ADD4 ERRATA 2] SUB: tu PIN lai cron monitor + ghi lai moc tmb0 (doc san lai sau YES) / C3_CAPITAL=<size>; rollback => tra moc cu.
#   Hau kiem: 0 leg mang cid so dry .dry_<dry_ts> (TS micro_on ghi trong co micro; thieu => TU CHOI) trong so live.
#   [A1 errata2] pin chi khi md5 monitor+lib co trong deploy/gates/A1_APPROVED_MONITOR.md5; pilot RESET dinh eq co chu dich (log + Telegram).
# [WAVE1 16/11] B-01 pin jar r4u3fin2 (lib); A-03 file key 600 + sha8 = SUB_KEY_SHA8 + key doc san = SUB_KEY_SHA8; A-08 tmb tk con
#   >= size (kiem truoc + sau YES); D-01 env +2 co sizing/DCA neu env.sh chua co + hau kiem log [LIVE-SIZING]/[LIVE-DCA-GRID] BAT;
#   B-02 rollback idempotent + KIEM adapter=live va C3_CAPITAL cu that (sai => KILL_SWITCH + KHAN).
# [OPS6 2026-11-21] T12b gate PILOT kiem day du bang gl_gate_pilot (body_sha256, han 48 h, size 5000|10000, g_exec/g_exit, mien X14/B2/C1,
#   boot_guard=CAI, owner_decision; MASTER tao bang golive_make_gate_pilot.sh). T20 boot guard 242 phai DA CAI (doc lai luc precheck).
#   T5/A-02 doi von (pilot 1000 -> size: "dinh tinh tu luc pilot bat"; rollback HA von sau khi JVM von moi da chay) => dat lai dinh C6/A40
#   jar TRUOC start (lib a02_reset) - precheck: python 242 + duong dan dinh/latch/KS mac dinh.
#   T2/N1 ssh dut sau khi bot DA dung + KS nguoi khac => env ve von cu, di nhanh rollback (khong bao sai "bot KHONG dung").
# =============================================================================
set -uo pipefail
# [WAVE1c m1] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_manifest_check "$0" || exit 1   # [WAVE1b M5] script + lib + manifest khop md5 da commit, lech => TU CHOI truoc moi viec
LEGACY_OK_MAX_AGE_S=${LEGACY_OK_MAX_AGE_S:-86400}
gl_init golive_pilot_on
[ "$C3_ACCOUNT" = MAIN ] && { gl_read_state; gl_excl_guard; }   # [A1 r4u2 C-1]
[ "$C3_ACCOUNT" = SUB ] && ACCT_TXT="tai khoan CON (ADD4)" || ACCT_TXT="tai khoan CHINH (ADD1)"
say "tai khoan c3: C3_ACCOUNT=$C3_ACCOUNT — $ACCT_TXT, file key $KEYS_FILE"
G=$GATE_DIR/GOLIVE_GATE_PILOT.ok
GR=$(gl_gate_pilot "$G"); echo "$GR"; echo "$GR" | grep -q '^OK' || die "chua co cong G-PILOT hop le (MASTER tao $G bang golive_make_gate_pilot.sh; jar_md5=$NJ_MD5)"
SIZE=$(gl_gate_val "$G" size)
[[ "$SIZE" =~ ^[0-9]+$ ]] && case " $GL_PILOT_SIZES " in *" $SIZE "*) true;; *) false;; esac || die "size='$SIZE' trong $G khong hop le (chi nhan: $GL_PILOT_SIZES)"
# [R4p ADD2] G-EXEC chuyen sang G-PILOT: gate phai co g_exec=<GREEN|AMBER|RED_SIZE|Q4_OWNER> <dan chung>
GX=$(gl_gate_val "$G" g_exec)
[[ "$GX" =~ ^(GREEN|AMBER|RED_SIZE|Q4_OWNER) ]] || die "$G thieu dong g_exec=<GREEN|AMBER|RED_SIZE|Q4_OWNER> <dan chung> (GOLIVE ADD2: G-PILOT muc 6)"
echo "OK g_exec=$GX"
# [R4q ADD3] G-EXIT (truot THOAT + PnL/leg rong >= 80 % sim): DAT | Q4_OWNER; TRUOT / thieu => khong pilot
GE=$(gl_gate_val "$G" g_exit)
[[ "$GE" =~ ^(DAT|Q4_OWNER) ]] || die "$G: g_exit='$GE' — can g_exit=<DAT|Q4_OWNER> <median_bps> <R> <n> <dan chung> (GOLIVE ADD3: G-PILOT muc 7; TRUOT => khong pilot)"
echo "OK g_exit=$GE"
if [ "$C3_ACCOUNT" = SUB ]; then
  say "INFO ADD4 §3: tk con — BO dieu kien LEGACY_CUT_VERIFIED / golive_legacy_verify / LEGACY managed 0"
else
  LV=$GATE_DIR/LEGACY_CUT_VERIFIED.ok
  [ -s "$LV" ] && grep -q 'KET QUA: DAT' "$LV" || die "chua co $LV DAT (owner cat LEGACY roi chay bash $GL_HERE/golive_legacy_verify.sh)"
  AGE=$(( $(date +%s) - $(stat -c %Y "$LV") )); [ "$AGE" -le "$LEGACY_OK_MAX_AGE_S" ] || die "$LV cu ${AGE}s > ${LEGACY_OK_MAX_AGE_S}s — chay lai bash $GL_HERE/golive_legacy_verify.sh"
  say "OK LEGACY_CUT_VERIFIED ${AGE}s truoc: $(head -1 "$LV")"
fi
gl_read_state
echo "$ST" | grep -v '^END_STATE$' | sed 's/^/   242: /'
F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
C0=$(sv ENV_C3_CAPITAL)
chk "1 process bot" "[ '$(sv NPROC)' = 1 ]"
chk "jar dang chay = pin $NJ_MD5" "[ '$(sv JAR_MD5)' = '$NJ_MD5' ]"
chk "dang chay c3_live LIVE, push mo (SHADOW_NO_PUSH=false, LIVE_ENTRY_ENABLED=true)" "[ '$(sv ENV_LIVE_PROFILE)' = c3_live ] && [ '$(sv ENV_LIVE_ADAPTER)' = live ] && [ '$(sv ENVSH_LIVE_ADAPTER)' = live ] && [ '$(sv ENV_SHADOW_NO_PUSH)' = false ] && [ '$(sv ENV_LIVE_ENTRY_ENABLED)' = true ]"
chk "C3_CAPITAL hien tai ($C0) < size $SIZE" "[[ '$C0' =~ ^[0-9]+$ ]] && [ '$C0' -lt $SIZE ]"
chk "latch kill-switch NONE" "[ '$(sv LATCH)' = NONE ] || [ '$(sv LATCH)' = NOFILE ]"
chk "khong co run/KILL_SWITCH, hoac token c3live_boot/c3_autodrain (co: $(sv KILLSW_FILE) token: $(sv KILLSW_TOK))" "gl_ks_boot_ok"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
chk "Oracle: khong co tien trinh $CANARY_PAT dang chay (A1 ADD4 MIN-2; co $(pgrep -fc "$CANARY_PAT" 2>/dev/null))" "gl_no_canary"
DTS=$(sed -n 's/^dry_ts=//p' "$GL_MON_FLAG" 2>/dev/null | head -1)   # [A1 errata2 MIN-2] so dry .dry_<TS> do micro_on ghi
chk "co micro/pilot co dry_ts (so dry .dry_<TS> cua micro_on: ${DTS:-THIEU})" "[ -n '$DTS' ]"
gl_bootguard242   # [OPS6 T20] OWNER_DECISION_PILOT_1121 Q4: boot guard BAT BUOC truoc pilot (CHI DOC 242)
chk "boot guard 242 DA CAI (T20; $BG_DETAIL; owner: bash $GL_HERE/install_242_autodrain.sh)" "[ '$BG' = CAI ]"
chk "A-02: rollback ha von dat lai duoc dinh (python 242 $PY242 co=$(sv PY_OK); env.sh ghi de duong dan dinh/latch/KS='$(sv ENVSH_PATH_OVR)')" "[ '$(sv PY_OK)' = 1 ] && [ -z '$(sv ENVSH_PATH_OVR)' ]"
if [ "$C3_ACCOUNT" = SUB ]; then
  L0=SKIP; YESW="YES PILOT"
  say "INFO LEGACY managed=$(sv LEGACY_N) (tk chinh) — chi ghi log"
  chk "bot live dung key tk con (LIVE_C3_KEYS_FILE=$KEYS_FILE; co: $(sv ENV_LIVE_C3_KEYS_FILE))" "[ '$(sv ENV_LIVE_C3_KEYS_FILE)' = '$KEYS_FILE' ]"
  chk "file key $KEYS_FILE (600, 2 dong)" "[ '$(sv KEYS_OK)' = 1 ]"
  chk "file key tk con: quyen $(sv KEYS_PERM) = 600, sha8 key $(sv KEYS_FILE_SHA8) = da dang ky $SUB_KEY_SHA8 (A-03)" "[ '$(sv KEYS_PERM)' = 600 ] && [ '$(sv KEYS_FILE_SHA8)' = '$SUB_KEY_SHA8' ]"
  chk "cron golive_monitor da cai, ban pin con nguyen (A1 ADD4 C-1; owner: bash $GL_HERE/install_cron_golive_monitor.sh)" "gl_mon_cron_ok"
  HBA=$(gl_hb_age)
  chk "heartbeat cron golive_monitor ${HBA}s <= ${MON_HB_MAX_AGE_S}s (A1 delta MIN-3; $MON_HB_FILE)" "[ $HBA -ge 0 ] && [ $HBA -le $MON_HB_MAX_AGE_S ]"
  chk "md5 monitor+lib $(gl_mon_m12) da qua A1 ($A1_APPROVED_FILE)" "gl_mon_approved"
  API=$(gl_api242 sub) || die "ssh toi 242 loi (doc tk con)"
  echo "$API" | grep -v '^END_API$' | sed 's/^/   tk con: /'
  gl_sub_eval 0
  chk "key tk con dat (ADD4 §2)${SUBWHY:+ —$SUBWHY}" "[ '$SUBV' = DAT ]"
  chk "A-08 tmb tk con $(av TMB) >= size $SIZE" "awk -v t='$(av TMB)' -v c='$SIZE' 'BEGIN{exit !(t+0 >= c+0 && t ~ /^[0-9.]+\$/)}'"
  NC=""; for k in POS_NONC3 ORD_NONC3 ALGO_NONC3; do n=$(av $k | awk '{print $1}'); [ "$n" = 0 ] || NC="$NC $k=$(av $k)"; done
  NCOK=0; [ -z "$NC" ] && NCOK=1
  chk "tk con: 0 vi the / lenh / algo NGOAI c3 (ADD4 §4)${NC:+ —$NC}" "[ $NCOK = 1 ]"
  KEYCHK="envk LIVE_C3_KEYS_FILE=$KEYS_FILE; envk C3_EXCLUDE_LEGACY_HELD=false; [ \"\$(T '\\[C3-EXCL-FORCE\\]')\" = 0 ] && echo 'OK 0_C3-EXCL-FORCE' || echo 'FAIL C3-EXCL-FORCE (SUB: env key sai)'"
  chk "process env C3_EXCLUDE_LEGACY_HELD=false (tk con; co: $(sv ENV_C3_EXCLUDE_LEGACY_HELD))" "[ '$(sv ENV_C3_EXCLUDE_LEGACY_HELD)' = false ]"
else
  L0=0; YESW="YES DA CAT LEGACY"; KEYCHK=""
  chk "LEGACY managed = 0 (da cat), moi" "[ '$(sv LEGACY_N)' = 0 ] && [ '$(sv LEGACY_AGE)' -ge 0 ] && [ '$(sv LEGACY_AGE)' -le 600 ] 2>/dev/null"
fi
say "--- [D-01] budget leg du kien (2 co sizing/DCA BAT) voi C3_CAPITAL=$SIZE:"
D01=$(gl_d01_plan "$SIZE"); D01RC=$?; echo "$D01" | sed 's/^/   /'
chk "D-01 leg0 du kien >= $MIN_LEG_BUDGET (von toi thieu $(echo "$D01" | sed -n 's/^D01_MINCAP=//p'))" "[ '$D01RC' = 0 ]"
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
say "INFO [T10] LEV_CLUSTER_MAX voi von $SIZE = $(awk -v c="$SIZE" 'BEGIN{printf "%.0f", 4*0.0225*c}') USDT/cum (golive_check_lev.sh mac dinh dung von PROCESS $C0 => kiem cho pilot: LEV_CAP=$SIZE bash $GL_HERE/golive_check_lev.sh)"
ENV_ADD="# [v1.2 R4o/ADD4 golive_pilot_on $TS] PILOT $ACCT_TXT size=$SIZE (truoc $C0)
export C3_CAPITAL=$SIZE"
[ "$(sv ENVSH_LIVE_APPLY_GRID_RATIO)" = true ] || ENV_ADD="$ENV_ADD
export LIVE_APPLY_GRID_RATIO=true"
[ "$(sv ENVSH_LIVE_DCA_GRID_ENABLED)" = true ] || ENV_ADD="$ENV_ADD
export LIVE_DCA_GRID_ENABLED=true"
say "--- se THEM vao $A/conf/env.sh:"; echo "$ENV_ADD" | sed 's/^/   + /'
say "--- so live / vi the c3 ($(sv BOOK_CUM) cum) GIU NGUYEN qua restart; hau kiem c3_capital=$SIZE, PUSH=ON, stream, recon ok$([ "$C3_ACCOUNT" = SUB ] || echo ', LEGACY 0')"
[ "$C3_ACCOUNT" = SUB ] && [ "$DRY" = 1 ] && { gl_mon_repin || say "!! installer cron (DRY) loi"; }
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
if [ "$C3_ACCOUNT" = SUB ]; then
  gl_yes "PILOT: C3_CAPITAL $C0 -> $SIZE tren $ACCT_TXT. Owner XAC NHAN da nap du von vao tk con." "$YESW"
else
  gl_yes "PILOT: C3_CAPITAL $C0 -> $SIZE tren $ACCT_TXT. Owner XAC NHAN da cat TOAN BO LEGACY." "$YESW"
fi
gl_no_canary || die "co tien trinh $CANARY_PAT tren Oracle (vua xuat hien) — khong pilot (A1 MIN-2)"
gl_mon_flag_set || die "KHONG ghi duoc co monitor $GL_MON_FLAG — khong pilot (A1 delta MIN-2)"
if [ "$C3_ACCOUNT" = SUB ]; then
  gl_mon_repin || die "pin lai cron golive_monitor LOI — khong pilot (ADD4 errata 2)"
  API=$(gl_api242 mon) || die "ssh toi 242 loi (doc tmb)"
  echo "$API" | grep -qx END_API || die "doc tmb tk con khong tron ven"
  awk -v t="$(av TMB)" -v c="$SIZE" 'BEGIN{exit !(t+0 >= c+0)}' || die "A-08 tmb tk con $(av TMB) < size $SIZE ngay truoc khi pilot (owner nap them von truoc)"
  gl_eq_base_set "$(av TMB)" "$SIZE" "$(av KEY_SHA8)" "golive_pilot_on $TS (C3_CAPITAL $C0 -> $SIZE) — RESET dinh eq co chu dich" || die "KHONG ghi duoc moc tmb0 — khong pilot (ADD4 errata 2 §5)"
fi
trap 'say "BI DUNG (tin hieu) giua restart: env.sh 242 CO THE da co C3_CAPITAL=$SIZE; run/KILL_SWITCH token golive_pilot_on $TS (neu da dat) giu => bot KHONG mo moi. Kiem bash $GL_HERE/golive_monitor.sh; env goc $A/conf/env.sh.bak_golive_pilot_on_$TS"; tg "[golive] KHAN TS=$TS pilot_on BI DUNG (tin hieu) giua restart: env.sh co the da C3_CAPITAL=$SIZE, KS script giu. Kiem golive_monitor.sh | log $LOG" >/dev/null 2>&1; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "" none 1   # [VONG3 F2] ks=1: dat KILL_SWITCH token golive_pilot_on TRUOC stop (ban cu -> .prev_<TS>), go sau hau kiem DAT
if gl_restart_unknown; then   # [WAVE1 B-02]
  s242 "cd $A && echo 'golive_pilot_on $TS ssh_restart_khong_ro' >> run/KILL_SWITCH && [ -e run/KILL_SWITCH ]" && say "run/KILL_SWITCH DANG DAT" || say "!! KHONG dat duoc run/KILL_SWITCH (ssh?)"
  M="restart pilot: ssh dut, KHONG doc duoc trang thai that tren 242 => KHONG ket luan. env.sh 242 CO THE da co C3_CAPITAL=$SIZE (von MOI) va bot co the dang DUNG: PAUSE het han sau ${WD_PAUSE_MAX_S}s => watchdog start voi env.sh HIEN TAI duoi run/KILL_SWITCH (khong mo moi). Owner/MASTER: bash $GL_HERE/golive_monitor.sh; env backup GOC $A/conf/env.sh.bak_golive_pilot_on_$TS"
  say "KHAN: $M"; tg "[golive] KHAN TS=$TS pilot_on: $M | log $LOG"; exit 2
fi
if echo "$RS" | grep -q '^FAIL' && ! echo "$RS" | grep -q '^OK da_stop'; then
  gl_pause_clear >/dev/null 2>&1; [ -f "$SUB_BASE_FILE.bak_$TS" ] && mv -f "$SUB_BASE_FILE.bak_$TS" "$SUB_BASE_FILE"
  say "DUNG: buoc env/stop FAIL TRUOC khi dung bot: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ')"
  say "KET QUA: TU_CHOI — env.sh da tra ve backup goc, moc tmb0 tra lai, bot live KHONG bi dung. Log: $LOG"; exit 1
fi
# [ADD4 ERRATA 2 / A1 MIN-2] khong leg nao mang cid cua so dry .dry_<dry_ts trong co micro> trong so live
PCHK='
B=run/c3live_book.json; DB=run/c3live_book.json.dry_'"$DTS"'; DN=0
[ -f $B ] && [ -f $DB ] && DN=$(grep -o "\"cid\":\"[^\"]*\"" $DB | sort -u | grep -cxFf - <(grep -o "\"cid\":\"[^\"]*\"" $B | sort -u))
[ "${DN:-0}" = 0 ] && echo "OK 0_leg_so_dry_trong_so_live" || echo "FAIL ${DN}_leg_so_dry_trong_so_live"'
CHK() { gl_chk_common "$SL" "$L0" '
envk LIVE_ADAPTER=live; envk C3_CAPITAL='"$SIZE"'; envk SHADOW_NO_PUSH=false; envk LIVE_ENTRY_ENABLED=true; '"$KEYCHK"'
'"$GL_D01_CHK"'
[ "$(tail -n +$SL $L | grep -a "khoi dong adapter=LIVE" | grep -acE "c3_capital='"$SIZE"'(\.0)?( |$)")" -ge 1 ] && echo "OK c3_capital='"$SIZE"'" || echo "WAIT c3_capital"
grep -q "^golive_pilot_on '"$TS"' " run/KILL_SWITCH 2>/dev/null && echo "OK KILL_SWITCH_con (chua mo lenh moi)" || echo "FAIL KILL_SWITCH_cua_script_mat"
[ "$(T "PUSH=ON")" = 0 ] && echo "OK chua_PUSH_ON" || echo "FAIL PUSH_ON_khi_con_KILL_SWITCH"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"'"$PCHK"; }
if ! echo "$RS" | grep -q '^FAIL' && gl_postloop CHK; then
  # [VONG3 F2] hau kiem 2 pha (nhu micro_on): KS cua minh con => kiem DAT => go KS (chi khi MOI dong la cua minh) => cho PUSH ON
  KG=$(gl_ks_go_own golive_pilot_on); PON=0
  if [ "$KG" = OK ]; then
    say "OK go run/KILL_SWITCH (hau kiem DAT) - cho PUSH ON"
    for r in $(seq 1 "$POST_ROUNDS"); do
      sleep "$POST_WAIT_S"
      n=$(s242 "cd $A && tail -n +$SL logs/full.log 2>/dev/null | grep -ac 'PUSH doi trang thai -> ON'") || n=x
      [ "$n" != x ] && [ "$n" -ge 1 ] 2>/dev/null && { PON=1; break; }
    done
  fi
  if [ "$PON" = 1 ]; then
    trap - INT TERM HUP
    gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
    say "=== XONG: PILOT C3_CAPITAL=$SIZE ($ACCT_TXT). Theo doi: bash $GL_HERE/golive_monitor.sh"
    [ "$C3_ACCOUNT" = SUB ] && say "INFO lop phu monitor: moc tmb0 moi, RESET dinh eq co chu dich (pilot_on)"
    tg "[golive] PILOT BAT TS=$TS C3_ACCOUNT=$C3_ACCOUNT C3_CAPITAL=$SIZE (truoc $C0)$([ "$C3_ACCOUNT" = SUB ] && echo '; lop phu monitor: moc tmb0 moi, RESET dinh eq co chu dich'). Log $LOG"; exit 0
  fi
  gl_pause_clear >/dev/null 2>&1
  if [ "$KG" = OK ]; then
    if s242 "cd $A && echo 'golive_pilot_on $TS push_khong_ON' >> run/KILL_SWITCH && [ -e run/KILL_SWITCH ]"; then
      M="hau kiem DAT (C3_CAPITAL=$SIZE da ap dung) nhung KHONG thay 'PUSH doi trang thai -> ON' sau khi go KILL_SWITCH => DA DAT LAI KILL_SWITCH (xac nhan; an toan, khong mo moi). Owner/MASTER kiem bash $GL_HERE/golive_monitor.sh"
    else
      M="hau kiem DAT (C3_CAPITAL=$SIZE) nhung KHONG thay PUSH ON; DAT LAI KILL_SWITCH THAT BAI (ssh?) => KILL_SWITCH DA GO, CO THE MO LENH MOI. KHAN: owner chay NGAY MODE=drain bash $GL_HERE/golive_live_off.sh"
    fi
  elif [ "$KG" = KHAC ]; then
    M="hau kiem DAT (C3_CAPITAL=$SIZE) nhung run/KILL_SWITCH co dong/token KHAC (owner drain / monitor KHAN chen vao) => GIU NGUYEN, KHONG go: bot LIVE dang DRAIN. Owner/MASTER kiem noi dung KS roi moi MODE=undrain bash $GL_HERE/golive_live_off.sh"
  else
    M="hau kiem DAT (C3_CAPITAL=$SIZE) nhung KHONG XAC NHAN DUOC trang thai run/KILL_SWITCH (ssh) - co the da go. KHAN: owner kiem NGAY ls $A/run/KILL_SWITCH tren 242 / MODE=drain bash $GL_HERE/golive_live_off.sh"
  fi
  say "KHAN: $M"; tg "[golive] KHAN TS=$TS pilot_on: $M | log $LOG"; exit 2
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)
say "hau kiem TRUOT ($WHY) => ROLLBACK ve C3_CAPITAL=$C0 (adapter live, so + vi the giu nguyen)"
if gl_rollback none live "$C0"; then
  [ -f "$SUB_BASE_FILE.bak_$TS" ] && mv -f "$SUB_BASE_FILE.bak_$TS" "$SUB_BASE_FILE" && say "OK moc tmb0 tra lai ban truoc pilot"
  KR=$(gl_ks_restore_prev golive_pilot_on)   # [VONG3 F2] KS ve nhu truoc pilot (token cu .prev / khong KS); dong khac => giu (DRAIN)
  say "Da ROLLBACK xong: live C3_CAPITAL=$C0. run/KILL_SWITCH sau rollback: ${KR:-KHONG_RO} (PUSH = nhu truoc pilot; DRAIN = token cu / dong khac giu nguyen)"; tg "[golive] pilot_on FAIL TS=$TS: $WHY => ROLLBACK ve $C0 XONG, KS=${KR:-KHONG_RO}. Log $LOG"; exit 1
fi
s242 "cd $A && echo 'golive_pilot_on $TS rollback_loi' >> run/KILL_SWITCH && [ -e run/KILL_SWITCH ]" && say "run/KILL_SWITCH DANG DAT" || say "!! KHONG dat duoc run/KILL_SWITCH (ssh?)"
M="ROLLBACK LOI / khong xac nhan adapter=live C3_CAPITAL=$C0 ($(echo "$RB" | grep '^FAIL' | head -2 | tr '\n' ' ')) => run/KILL_SWITCH; kiem bash $GL_HERE/golive_monitor.sh; env backup GOC $A/conf/env.sh.bak_golive_pilot_on_$TS"
say "KHAN: $M"; tg "[golive] KHAN TS=$TS pilot_on TRUOT ($WHY) VA $M | log $LOG"; exit 2
