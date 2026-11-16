#!/usr/bin/env bash
# =============================================================================
# golive_pilot_on.sh — [V12 R4o/ADD4] MICRO (C3_CAPITAL=1000) -> PILOT (C3_CAPITAL=<size>) (GOLIVE_SCENARIO ADD1 §4 / ADD4).
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/golive_pilot_on.sh   # chi kiem
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_pilot_on.sh         # SUB: go 'YES PILOT' | MAIN: 'YES DA CAT LEGACY' (khung :10-:44)
# C3_ACCOUNT=SUB (mac dinh, ADD4 tk con) | MAIN (ADD1 tk chinh — chi khi chi dinh ro).
# Kiem: gate G-PILOT (jar_md5 + size= + g_exec= [ADD2] + g_exit= DAT|Q4_OWNER [ADD3]), dang chay LIVE push ON, C3_CAPITAL hien tai < size,
#   latch NONE, khong KILL_SWITCH, RAM, khong PAUSE/canary/soak.
#   MAIN: + LEGACY_CUT_VERIFIED.ok (golive_legacy_verify.sh DAT <= 24 h) + LEGACY managed 0.
#   [ADD4 SUB] BO LEGACY_CUT_VERIFIED / legacy_verify / LEGACY 0 (§3, chi ghi log); thay bang: bot live dung LIVE_C3_KEYS_FILE = file key
#   tk con, key van dat (§2: IP-only, khong rut, futures, sha8 != tk chinh, dualSide=false, BFUSD), tk con 0 vi the / lenh / algo NGOAI c3 (§4).
# Lam: env +C3_CAPITAL=<size> ; PAUSE token ; restart (so live + vi the c3 GIU NGUYEN; adapter khong doi) ; hau kiem env, c3_capital,
#   PUSH=ON, stream, recon ok, latch NONE, 0 KHAN (MAIN: LEGACY 0). TRUOT => rollback: env.sh ve ban truoc (C3_CAPITAL cu), restart.
# [A1 ADD4] SUB: doi cron golive_monitor da cai (C-1), dam bao co monitor; MIN-2: co tien trinh canary_early* tren Oracle => TU CHOI.
# [ADD4 ERRATA 2] SUB: tu PIN lai cron monitor + ghi lai moc tmb0 (doc san lai sau YES) / C3_CAPITAL=<size>; rollback => tra moc cu.
#   Hau kiem: 0 leg mang cid so dry .dry_<dry_ts> (TS micro_on ghi trong co micro; thieu => TU CHOI) trong so live.
#   [A1 errata2] pin chi khi md5 monitor+lib co trong deploy/gates/A1_APPROVED_MONITOR.md5; pilot RESET dinh eq co chu dich (log + Telegram).
# [WAVE1 16/11] B-01 pin jar r4u3fin2 (lib); A-03 file key 600 + sha8 = SUB_KEY_SHA8 + key doc san = SUB_KEY_SHA8; A-08 tmb tk con
#   >= size (kiem truoc + sau YES); D-01 env +2 co sizing/DCA neu env.sh chua co + hau kiem log [LIVE-SIZING]/[LIVE-DCA-GRID] BAT;
#   B-02 rollback idempotent + KIEM adapter=live va C3_CAPITAL cu that (sai => KILL_SWITCH + KHAN).
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
LEGACY_OK_MAX_AGE_S=${LEGACY_OK_MAX_AGE_S:-86400}
gl_init golive_pilot_on
[ "$C3_ACCOUNT" = MAIN ] && { gl_read_state; gl_excl_guard; }   # [A1 r4u2 C-1]
[ "$C3_ACCOUNT" = SUB ] && ACCT_TXT="tai khoan CON (ADD4)" || ACCT_TXT="tai khoan CHINH (ADD1)"
say "tai khoan c3: C3_ACCOUNT=$C3_ACCOUNT — $ACCT_TXT, file key $KEYS_FILE"
G=$GATE_DIR/GOLIVE_GATE_PILOT.ok
GR=$(gl_gate "$G"); echo "$GR"; echo "$GR" | grep -q '^OK' || die "chua co cong G-PILOT hop le (MASTER tao $G voi jar_md5=$NJ_MD5 + size=)"
SIZE=$(gl_gate_val "$G" size)
[[ "$SIZE" =~ ^[0-9]+$ ]] && [ "$SIZE" -ge 1000 ] && [ "$SIZE" -le 100000 ] || die "size='$SIZE' trong $G khong hop le (1000..100000)"
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
  [ -s "$LV" ] && grep -q 'KET QUA: DAT' "$LV" || die "chua co $LV DAT (owner cat LEGACY roi chay golive_legacy_verify.sh)"
  AGE=$(( $(date +%s) - $(stat -c %Y "$LV") )); [ "$AGE" -le "$LEGACY_OK_MAX_AGE_S" ] || die "$LV cu ${AGE}s > ${LEGACY_OK_MAX_AGE_S}s — chay lai golive_legacy_verify.sh"
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
chk "khong co run/KILL_SWITCH" "[ '$(sv KILLSW_FILE)' = 0 ]"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
chk "Oracle: khong co tien trinh $CANARY_PAT dang chay (A1 ADD4 MIN-2; co $(pgrep -fc "$CANARY_PAT" 2>/dev/null))" "gl_no_canary"
DTS=$(sed -n 's/^dry_ts=//p' "$GL_MON_FLAG" 2>/dev/null | head -1)   # [A1 errata2 MIN-2] so dry .dry_<TS> do micro_on ghi
chk "co micro/pilot co dry_ts (so dry .dry_<TS> cua micro_on: ${DTS:-THIEU})" "[ -n '$DTS' ]"
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
trap 'say "BI DUNG (tin hieu) — kiem golive_monitor.sh"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "" none
if gl_restart_unknown; then   # [WAVE1 B-02]
  s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo 'golive_pilot_on $TS ssh_restart_khong_ro' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]" && say "run/KILL_SWITCH DANG DAT" || say "!! KHONG dat duoc run/KILL_SWITCH (ssh?)"
  M="restart pilot: ssh dut, KHONG doc duoc trang thai that tren 242 => KHONG ket luan. Owner/MASTER: golive_monitor.sh; env backup GOC $A/conf/env.sh.bak_golive_pilot_on_$TS"
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
[ "$(T "PUSH=ON")" -ge 1 ] && echo "OK PUSH_ON" || echo "WAIT PUSH_ON"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"'"$PCHK"; }
if ! echo "$RS" | grep -q '^FAIL' && gl_postloop CHK; then
  trap - INT TERM HUP
  gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
  say "=== XONG: PILOT C3_CAPITAL=$SIZE ($ACCT_TXT). Theo doi: golive_monitor.sh"
  [ "$C3_ACCOUNT" = SUB ] && say "INFO lop phu monitor: moc tmb0 moi, RESET dinh eq co chu dich (pilot_on)"
  tg "[golive] PILOT BAT TS=$TS C3_ACCOUNT=$C3_ACCOUNT C3_CAPITAL=$SIZE (truoc $C0)$([ "$C3_ACCOUNT" = SUB ] && echo '; lop phu monitor: moc tmb0 moi, RESET dinh eq co chu dich'). Log $LOG"; exit 0
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)
say "hau kiem TRUOT ($WHY) => ROLLBACK ve C3_CAPITAL=$C0 (adapter live, so + vi the giu nguyen)"
if gl_rollback none live "$C0"; then
  [ -f "$SUB_BASE_FILE.bak_$TS" ] && mv -f "$SUB_BASE_FILE.bak_$TS" "$SUB_BASE_FILE" && say "OK moc tmb0 tra lai ban truoc pilot"
  say "Da ROLLBACK xong: live C3_CAPITAL=$C0."; tg "[golive] pilot_on FAIL TS=$TS: $WHY => ROLLBACK ve $C0 XONG. Log $LOG"; exit 1
fi
s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo 'golive_pilot_on $TS rollback_loi' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]" && say "run/KILL_SWITCH DANG DAT" || say "!! KHONG dat duoc run/KILL_SWITCH (ssh?)"
M="ROLLBACK LOI / khong xac nhan adapter=live C3_CAPITAL=$C0 ($(echo "$RB" | grep '^FAIL' | head -2 | tr '\n' ' ')) => run/KILL_SWITCH; kiem golive_monitor.sh; env backup GOC $A/conf/env.sh.bak_golive_pilot_on_$TS"
say "KHAN: $M"; tg "[golive] KHAN TS=$TS pilot_on TRUOT ($WHY) VA $M | log $LOG"; exit 2
