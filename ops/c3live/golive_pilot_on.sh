#!/usr/bin/env bash
# =============================================================================
# golive_pilot_on.sh — [V12 R4o] MICRO (C3_CAPITAL=1000) -> PILOT (C3_CAPITAL=<size>) tren TAI KHOAN CHINH (GOLIVE_SCENARIO ADD1 §4).
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/golive_pilot_on.sh   # chi kiem
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_pilot_on.sh         # go 'YES DA CAT LEGACY' (khung :10-:44)
# Kiem: gate G-PILOT (jar_md5 + size= + g_exec= [ADD2] + g_exit= DAT|Q4_OWNER [ADD3]), LEGACY_CUT_VERIFIED.ok (golive_legacy_verify.sh DAT <= 24 h), dang chay LIVE push ON,
#   C3_CAPITAL hien tai < size, latch NONE, khong KILL_SWITCH, LEGACY managed 0, RAM, khong PAUSE/canary/soak.
# Lam: env +C3_CAPITAL=<size> ; PAUSE token ; restart (so live + vi the c3 GIU NGUYEN; adapter khong doi) ; hau kiem env, c3_capital,
#   PUSH=ON, stream, recon ok, LEGACY 0, latch NONE, 0 KHAN. TRUOT => rollback: env.sh ve ban truoc (C3_CAPITAL cu), restart.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
LEGACY_OK_MAX_AGE_S=${LEGACY_OK_MAX_AGE_S:-86400}
gl_init golive_pilot_on
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
LV=$GATE_DIR/LEGACY_CUT_VERIFIED.ok
[ -s "$LV" ] && grep -q 'KET QUA: DAT' "$LV" || die "chua co $LV DAT (owner cat LEGACY roi chay golive_legacy_verify.sh)"
AGE=$(( $(date +%s) - $(stat -c %Y "$LV") )); [ "$AGE" -le "$LEGACY_OK_MAX_AGE_S" ] || die "$LV cu ${AGE}s > ${LEGACY_OK_MAX_AGE_S}s — chay lai golive_legacy_verify.sh"
say "OK LEGACY_CUT_VERIFIED ${AGE}s truoc: $(head -1 "$LV")"
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
chk "LEGACY managed = 0 (da cat), moi" "[ '$(sv LEGACY_N)' = 0 ] && [ '$(sv LEGACY_AGE)' -ge 0 ] && [ '$(sv LEGACY_AGE)' -le 600 ] 2>/dev/null"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
ENV_ADD="# [v1.2 R4o golive_pilot_on $TS] PILOT tai khoan chinh size=$SIZE (truoc $C0)
export C3_CAPITAL=$SIZE"
say "--- se THEM vao $A/conf/env.sh:"; echo "$ENV_ADD" | sed 's/^/   + /'
say "--- so live / vi the c3 ($(sv BOOK_CUM) cum) GIU NGUYEN qua restart; hau kiem c3_capital=$SIZE, PUSH=ON, stream, recon ok, LEGACY 0"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "PILOT: C3_CAPITAL $C0 -> $SIZE tren tai khoan chinh. Owner XAC NHAN da cat 44 LEGACY." "YES DA CAT LEGACY"
trap 'say "BI DUNG (tin hieu) — kiem golive_monitor.sh"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "" none
if echo "$RS" | grep -q '^FAIL'; then
  echo "$RS" | grep -q '^OK da_stop' || { gl_pause_clear >/dev/null 2>&1; die "buoc env/stop FAIL truoc khi dung bot"; }
fi
CHK() { gl_chk_common "$SL" 0 '
envk LIVE_ADAPTER=live; envk C3_CAPITAL='"$SIZE"'; envk SHADOW_NO_PUSH=false; envk LIVE_ENTRY_ENABLED=true
[ "$(tail -n +$SL $L | grep -a "khoi dong adapter=LIVE" | grep -acE "c3_capital='"$SIZE"'(\.0)?( |$)")" -ge 1 ] && echo "OK c3_capital='"$SIZE"'" || echo "WAIT c3_capital"
[ "$(T "PUSH=ON")" -ge 1 ] && echo "OK PUSH_ON" || echo "WAIT PUSH_ON"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"'; }
if ! echo "$RS" | grep -q '^FAIL' && gl_postloop CHK; then
  trap - INT TERM HUP
  gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
  say "=== XONG: PILOT C3_CAPITAL=$SIZE. Theo doi: golive_monitor.sh"
  tg "[golive] PILOT BAT TS=$TS C3_CAPITAL=$SIZE (truoc $C0). Log $LOG"; exit 0
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)
say "hau kiem TRUOT ($WHY) => ROLLBACK ve C3_CAPITAL=$C0 (adapter live, so + vi the giu nguyen)"
if gl_rollback none && echo "$RB" | grep -q "ENV_C3_CAPITAL=$C0"; then
  say "Da ROLLBACK xong: live C3_CAPITAL=$C0."; tg "[golive] pilot_on FAIL TS=$TS: $WHY => ROLLBACK ve $C0 XONG. Log $LOG"; exit 1
fi
M="ROLLBACK LOI — PAUSE còn; kiem golive_monitor.sh; env backup $A/conf/env.sh.bak_golive_pilot_on_$TS"
say "KHAN: $M"; tg "[golive] KHAN TS=$TS pilot_on TRUOT ($WHY) VA $M | log $LOG"; exit 2
